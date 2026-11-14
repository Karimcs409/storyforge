"""AI media picker: a vision model tags the club's photo library once; for every Story page an LLM picks
the best photo, and code guards the pick (e.g. never the other team's fans on your goal page).
Demo library = 20 Pexels photos (Pexels License); a real club would plug in its own media library."""
import base64, json
from pathlib import Path

from . import llm

DIR = Path(__file__).resolve().parent.parent / "data" / "media"
LIB = DIR / "library.json"
NATIONS = ["argentina", "france", "neutral"]
USES = ["cover", "goal", "red_card", "sub", "half_time", "full_time", "stat", "quote", "cta"]

TAG_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["description", "scene", "mood", "nation", "time_of_day", "good_for", "text_area"],
    "properties": {
        "description": {"type": "string", "description": "one factual sentence, max 25 words"},
        "scene": {"type": "string", "enum": ["street", "stadium", "pitch", "goal", "trophy", "other"]},
        "mood": {"type": "string", "enum": ["celebration", "tension", "calm", "anticipation"]},
        "nation": {"type": "string", "enum": NATIONS,
                   "description": "argentina only if Argentine flags/sky-blue-and-white shirts are clearly visible; "
                                  "france only if French flags/colours are clearly visible; otherwise neutral"},
        "time_of_day": {"type": "string", "enum": ["day", "night"]},
        "good_for": {"type": "array", "items": {"type": "string", "enum": USES}, "minItems": 1, "maxItems": 4},
        "text_area": {"type": "string", "enum": ["top", "bottom", "center"],
                      "description": "calmest area of the image where white text stays readable"},
    },
}


def load_library() -> list[dict]:
    return json.loads(LIB.read_text(encoding="utf-8")) if LIB.exists() else []


def tag_library(force=False, only: list[str] | None = None) -> tuple[list[dict], float]:
    """Vision-tag every photo once (cached in library.json). Returns (library, usd spent)."""
    sources = json.loads((DIR / "sources.json").read_text(encoding="utf-8"))
    done = {} if force else {p["id"]: p for p in load_library() if not only or p["id"] not in only}
    lib, usd = [], 0.0
    for s in sources:
        if s["id"] in done:
            lib.append(done[s["id"]]); continue
        b64 = base64.b64encode((DIR / s["file"]).read_bytes()).decode()
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "Tag this ONE photo for a football club's media library. Be literal: describe only "
                                     "what is visible in this single image (it is not a collage). Do not guess identities "
                                     "of people. nation: use argentina/france ONLY if that country's flag or kit colours "
                                     "are clearly visible; stadiums, balls and crowds without flags are neutral. "
                                     f"Existing library caption (may be incomplete): \"{s['pexels_alt']}\""},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
        tag, log = llm.call_json("vision_tag", msgs, TAG_SCHEMA, "photo_tag", model="vision", effort="medium", ref=s["id"])
        usd += log["usd"]
        lib.append({**s, **tag})
        print(f"tagged {s['id']}: {tag['nation']:9} {tag['scene']:8} {tag['mood']:12} {tag['description'][:70]}", flush=True)
    LIB.write_text(json.dumps(lib, indent=2, ensure_ascii=False), encoding="utf-8")
    return lib, usd


def nation_of(team_name: str | None) -> str:
    t = (team_name or "").lower()
    return next((n for n in ("argentina", "france") if n in t), "neutral")


def page_context(p: dict, i: int, match: dict | None) -> dict:
    """What the code knows for sure about a page: its event and which team it belongs to (from the data, not the LLM)."""
    ctx = {"page": i, "type": p["type"], "headline": p["headline"], "media_hint": p["media_hint"], "team_nation": "neutral",
           "event": None}
    if match and p.get("minute") is not None:
        ev = next((e for e in match["events"] if e["minute"] == p["minute"] and e["type"] != "half_time"), None)
        if ev:
            ctx["event"] = ev["type"]
            if ev.get("team"):
                ctx["team_nation"] = nation_of(match[ev["team"]]["name"])
    if match and p["type"] in ("cover", "cta"):  # winner's (or home side's) fans for the cover, home side for tickets
        h, a = match["score"]["home"], match["score"]["away"]
        side = "away" if (p["type"] == "cover" and a > h) else "home"
        ctx["team_nation"] = nation_of(match[side]["name"])
        if p["type"] == "cover" and h == a and match.get("penalties"):  # draw decided on penalties
            ctx["team_nation"] = nation_of(match["penalties"]["winner"])
    return ctx


def _guard(ctxs, picks, lib, exclude=()):
    """Code guard: a page tied to one team must not show the OTHER team's fans; no photo used twice."""
    by_id, used, out = {p["id"]: p for p in lib}, set(exclude), {}
    for c in ctxs:
        pk = picks.get(c["page"], {})
        ph = by_id.get(pk.get("photo"))
        bad = (not ph or ph["id"] in used or
               (ph["nation"] != "neutral" and ph["nation"] != c["team_nation"]))
        if bad:
            want = [c["team_nation"], "neutral"]
            alt = sorted((p for p in lib if p["id"] not in used and p["nation"] in want),
                         key=lambda p: (want.index(p["nation"]), c["type"] not in p["good_for"]))
            if not alt: continue
            ph = alt[0]
            pk = {"reason": " ".join(ph["description"].split()[:9]).rstrip(".,") + "…", "guarded": True}
        used.add(ph["id"])
        out[c["page"]] = {"id": ph["id"], "file": ph["file"], "reason": pk.get("reason", ""), "guarded": pk.get("guarded", False),
                          "text_area": ph["text_area"], "source": ph["source"]}
    return out


def pick_media(pages: list[dict], match: dict | None = None, ref="", exclude=()) -> tuple[dict, dict | None]:
    """One LLM call picks a photo per page (photo ids are an enum: it can't invent one). Returns ({page_idx: pick}, log)."""
    lib_all = load_library()
    lib = [p for p in lib_all if p["id"] not in exclude] or lib_all
    pages_ix = [(i, p) for i, p in enumerate(pages) if p["type"] in ("cover", "moment", "stat", "quote", "cta")]
    if not lib or not pages_ix:
        return {}, None
    ids = [p["id"] for p in lib]
    ctxs = [page_context(p, i, match) for i, p in pages_ix]
    schema = {"type": "object", "additionalProperties": False, "required": ["picks"], "properties": {"picks": {
        "type": "array", "minItems": len(ctxs), "maxItems": len(ctxs), "items": {
            "type": "object", "additionalProperties": False, "required": ["page", "photo", "reason"],
            "properties": {"page": {"type": "integer"}, "photo": {"type": "string", "enum": ids},
                           "reason": {"type": "string", "description": "max 10 words, plain English for an editor, no field names like good_for/team_nation"}}}}}}
    library = [{k: p[k] for k in ("id", "description", "scene", "mood", "nation", "time_of_day", "good_for")} for p in lib]
    msgs = [{"role": "system", "content": "You are a photo editor for a football club's Stories. Pick the best photo from "
             "the LIBRARY for each PAGE. Rules: a page whose team_nation is argentina/france should show THAT nation's fans "
             "if available, never the other nation's; goal pages want celebration; stat pages want stadium/pitch; "
             "use each photo at most once; prefer photos whose good_for includes the page type."},
            {"role": "user", "content": f"LIBRARY:\n{json.dumps(library, ensure_ascii=False)}\n\nPAGES:\n{json.dumps(ctxs, ensure_ascii=False)}"}]
    data, log = llm.call_json("media_pick", msgs, schema, "media_picks", ref=ref)
    picks = {pk["page"]: pk for pk in data["picks"]}
    return _guard(ctxs, picks, lib, exclude if len(lib) < len(lib_all) else ()), log


if __name__ == "__main__":  # python -m app.media [--force] [ids...]  -> tag the library once
    import sys
    args = [a for a in sys.argv[1:] if a != "--force"]
    lib, usd = tag_library(force="--force" in sys.argv, only=args or None)
    print(f"{len(lib)} photos tagged, ${usd:.4f}")
