"""StoryForge API. Run: uvicorn app.main:app --port 8300"""
import asyncio, json, time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import llm, factcheck, store, media, cms, analytics, content_bank
from .feeds import ADAPTERS, KEY_EVENTS
from .schemas import VOICES, LANGS, CATEGORIES

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="StoryForge")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def no_stale_ui(request, call_next):
    """Prototype under active development: never let the browser run an old copy of the UI."""
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp
app.mount("/media", StaticFiles(directory=media.DIR), name="media")


@app.get("/", response_class=HTMLResponse)
def index():
    """Asset URLs carry the files' modification time, so a browser can never keep running an old UI."""
    v = int(max((STATIC / n).stat().st_mtime for n in ("app.js", "style.css", "index.html")))
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = html.replace("/static/app.js", f"/static/app.js?v={v}").replace("/static/style.css", f"/static/style.css?v={v}")
    stamp = time.strftime("%d %b %H:%M", time.localtime(v))
    return html.replace("</small></div></div>", f"</small><small class=\"ver-tag\">UI build {stamp}</small></div></div>", 1)


@app.get("/api/config")
def config():
    return {"voices": list(VOICES), "langs": list(LANGS), "feeds": list(ADAPTERS), "models": llm.MODELS, "categories": CATEGORIES}


@app.get("/api/matches")
def matches(feed: str = "replay"):
    try:
        return ADAPTERS[feed].list_matches()
    except Exception as e:
        raise HTTPException(502, f"feed '{feed}' unavailable: {e}")


@app.get("/api/match/{feed}/{mid}")
def match(feed: str, mid: str):
    return ADAPTERS[feed].get_match(mid)


class GenReq(BaseModel):
    feed: str = "replay"
    match_id: str | None = None
    article: str | None = None
    voice: str = "official"
    lang: str = "en"
    short_title_max: int = 20   # the CMS sets this per category


def _title_flags(story, facts, lang):
    """Re-check the title pack (lengths + facts) whenever the Story is created or edited."""
    if not story.get("titles"):
        return {}
    return cms.check_titles(story["titles"], facts, lang, cms.limits(story.get("short_title_max")))


def _source(feed, match_id, article):
    if article:
        return None, article, factcheck.facts_from_article(article)
    m = ADAPTERS[feed].get_match(match_id)
    return m, None, factcheck.facts_from_match(m)


def _theme(m):
    if not m: return {"home": "Home", "away": "Away", "colors": ["#1f2a44", "#c9a227"], "score": None}
    return {"home": m["home"]["name"], "away": m["away"]["name"], "home_short": m["home"]["short"], "away_short": m["away"]["short"],
            "colors": m["home"]["colors"], "away_colors": m["away"]["colors"], "score": f"{m['score']['home']}-{m['score']['away']}",
            "credit": m.get("credit")}


@app.post("/api/story")
async def create_story(r: GenReq):
    m, art, facts = _source(r.feed, r.match_id, r.article)
    story, log = await asyncio.to_thread(llm.generate_story, m, art, r.voice, r.lang, r.match_id or "article")
    rep = factcheck.check_story(story, facts, r.lang)
    logs = [log]
    try:  # AI photo picker (separate call so its cost/latency shows on its own line)
        picks, mlog = await asyncio.to_thread(media.pick_media, story["pages"], m, r.match_id or "article")
        story["media"] = {str(k): v for k, v in picks.items()}
        if mlog: logs.append(mlog)
    except Exception as e:
        story["media"] = {}
        print("media pick failed:", e)
    try:  # CMS title pack: Long / Short (category max) / Eyebrow / SEO, fact-checked, retried until within limits
        story["short_title_max"] = r.short_title_max
        story["titles"], _, tlog = await asyncio.to_thread(cms.title_pack, story, m, art, r.voice, r.lang,
                                                             r.short_title_max, r.match_id or "article")
        logs.append(tlog)
    except Exception as e:
        print("title pack failed:", e)
    rep["title_flags"] = _title_flags(story, facts, r.lang)
    story["unit_backgrounds"] = cms.unit_backgrounds(story)  # quiz / poll backgrounds: same photos in the phone and the export
    data = {"story": story, "report": rep, "logs": logs, "voice": r.voice, "lang": r.lang, "theme": _theme(m),
            "src": {"feed": r.feed, "match_id": r.match_id, "article": art}, "approved": [False] * len(story["pages"])}
    sid = store.save_story(r.match_id or "article", r.voice, r.lang, data)
    return {"id": sid, **data}


@app.get("/api/story/{sid}")
def read_story(sid: int):
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    return s


@app.get("/api/story/{sid}/cms")
def cms_export(sid: int):
    """Titles, pages, categories and the Trivia Quiz / Poll as Engagement Units, ready to enter in the CMS."""
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    return cms.export(s)


class EditReq(BaseModel):
    story: dict
    approved: list[bool] | None = None
    status: str | None = None


@app.put("/api/story/{sid}")
def edit_story(sid: int, r: EditReq):
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    src = s["src"]
    _, _, facts = _source(src["feed"], src["match_id"], src["article"])
    s["story"] = r.story
    s["report"] = factcheck.check_story(r.story, facts, s["lang"])
    s["report"]["title_flags"] = _title_flags(r.story, facts, s["lang"])
    if r.approved is not None: s["approved"] = r.approved
    # a page with an open fact flag can't stay approved: the editor must fix or regenerate it first
    s["approved"] = [a and not s["report"]["page_flags"].get(i) for i, a in enumerate(s["approved"])]
    status = r.status or ("approved" if all(s["approved"]) else "draft")
    keys = ("story", "report", "logs", "voice", "lang", "theme", "src", "approved")
    store.save_story("", "", "", {k: s[k] for k in keys}, status=status, sid=sid)
    return {"id": sid, "status": status, **{k: s[k] for k in keys}}


class RegenReq(BaseModel):
    note: str = ""


@app.post("/api/story/{sid}/page/{i}/regenerate")
async def regen(sid: int, i: int, r: RegenReq):
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    src = s["src"]
    m, art, facts = _source(src["feed"], src["match_id"], src["article"])
    page, log = await asyncio.to_thread(llm.regenerate_page, s["story"], i, m, art, s["voice"], s["lang"], r.note, f"{sid}:{i}")
    s["story"]["pages"][i] = page
    s["approved"][i] = False
    s["story"], log = await asyncio.to_thread(llm.repair_lengths, s["story"], m, art, s["voice"], s["lang"], log, f"{sid}:{i}")
    page = s["story"]["pages"][i]
    s["logs"].append(log)
    s["report"] = factcheck.check_story(s["story"], facts, s["lang"])
    s["report"]["title_flags"] = _title_flags(s["story"], facts, s["lang"])
    keys = ("story", "report", "logs", "voice", "lang", "theme", "src", "approved")
    store.save_story("", "", "", {k: s[k] for k in keys}, sid=sid)
    return {"id": sid, "page": page, "log": log, **{k: s[k] for k in keys}}


# ---------------- editor-added moments (the feed or the AI missed one) ----------------
class EditorEvent(BaseModel):
    minute: int
    type: str = "other"            # goal / yellow_card / red_card / sub / other
    team: str | None = None        # home / away
    player: str | None = None      # scorer, carded player, player on
    player2: str | None = None     # assist (goal) or player off (sub)
    score_after: str | None = None # goal only, e.g. "2-1"
    note: str = ""


def _editor_page(ev: EditorEvent, mode: str, m, art, prior, voice, lang, ref):
    """AI-drafted or blank page for the editor's moment, marked as not in the feed. Returns (page, log)."""
    e = ev.model_dump()
    if mode == "ai":
        page, log = llm.editor_page(m, art, e, prior, voice, lang, ref)
    else:
        page, log = llm.blank_editor_page(e), None
    page["added_by_editor"] = True
    page["editor_event"] = e
    return page, log


def _roster(m, art):
    if m:
        return {side: {"name": m[side]["name"], "players": m[side]["lineup"] + m[side].get("bench", [])} for side in ("home", "away")}
    return {"home": {"name": "Players in the article", "players": sorted(factcheck.facts_from_article(art).names)}}


@app.get("/api/story/{sid}/roster")
def story_roster(sid: int):
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    m, art, _ = _source(s["src"]["feed"], s["src"]["match_id"], s["src"]["article"])
    return _roster(m, art)


@app.get("/api/roster/{feed}/{mid}")
def roster(feed: str, mid: str):
    return _roster(ADAPTERS[feed].get_match(mid), None)


class AddPageReq(BaseModel):
    event: EditorEvent
    mode: str = "ai"               # ai / manual
    position: int | None = None    # insert before this page index (default: before the CTA)


@app.post("/api/story/{sid}/page/add")
async def add_page(sid: int, r: AddPageReq):
    s = store.get_story(sid)
    if not s: raise HTTPException(404)
    src = s["src"]
    m, art, facts = _source(src["feed"], src["match_id"], src["article"])
    st = s["story"]
    page, log = await asyncio.to_thread(_editor_page, r.event, r.mode, m, art, st["pages"], s["voice"], s["lang"], f"{sid}:add")
    n = len(st["pages"])
    cta = next((i for i, p in enumerate(st["pages"]) if p["type"] == "cta"), n)
    pos = cta if r.position is None else max(0, min(r.position, n))
    st["pages"].insert(pos, page)
    s["approved"].insert(pos, False)
    # photos are keyed by page index: shift the ones after the new page
    st["media"] = {str(int(k) + (int(k) >= pos)): v for k, v in (st.get("media") or {}).items()}
    if log: s["logs"].append(log)
    s["report"] = factcheck.check_story(st, facts, s["lang"])
    s["report"]["title_flags"] = _title_flags(st, facts, s["lang"])
    keys = ("story", "report", "logs", "voice", "lang", "theme", "src", "approved")
    store.save_story("", "", "", {k: s[k] for k in keys}, sid=sid)
    return {"id": sid, "position": pos, "log": log, **{k: s[k] for k in keys}}


class LiveAddReq(BaseModel):
    feed: str = "replay"
    match_id: str
    event: EditorEvent
    mode: str = "ai"
    voice: str = "official"
    lang: str = "en"
    prior: list[str] = []          # headlines already in the live Story


@app.post("/api/live/add")
async def live_add(r: LiveAddReq):
    """'+ Add moment' in the Live approval queue: drafted only from the match as it stood at that minute."""
    m = await asyncio.to_thread(ADAPTERS[r.feed].get_match, r.match_id)
    part = _partial(m, [e for e in m["events"] if e["minute"] <= r.event.minute])
    t0 = time.perf_counter()
    prior = [{"headline": h} for h in r.prior]
    page, log = await asyncio.to_thread(_editor_page, r.event, r.mode, part, None, prior, r.voice, r.lang, f"live:{r.match_id}:add")
    flags = factcheck.check_page(page, factcheck.facts_from_match(part), r.lang)
    return {"page": page, "flags": flags, "log": log, "latency_ms": int((time.perf_counter() - t0) * 1000),
            "event": {"minute": r.event.minute, "type": r.event.type}}


# ---------------- Analytics explainer ----------------
class AnalyticsReq(BaseModel):
    csv: str | None = None    # an analytics export saved as CSV; None = the synthetic sample


@app.get("/api/analytics/sample.csv")
def analytics_sample():
    return FileResponse(analytics.SAMPLE, media_type="text/csv", filename="storyforge_sample_analytics_SYNTHETIC.csv")


@app.post("/api/analytics/explain")
async def analytics_explain(r: AnalyticsReq):
    """Code computes every number; the LLM explains; the number guard checks what it wrote."""
    try:
        rows = analytics.parse_csv(r.csv) if r.csv else analytics.load_sample()
    except ValueError as e:
        raise HTTPException(400, f"could not read the export: {e}")
    summary = analytics.summarize(rows)
    data, log = await asyncio.to_thread(analytics.explain, summary)
    return {"source": "upload" if r.csv else "sample (synthetic)", "summary": summary, **data,
            "flags": analytics.check_insights(data, summary), "log": log}


# ---------------- Content Bank auto-tagging ----------------
@app.get("/api/content-bank")
def content_bank_list(q: str = "", cat: str = ""):
    entries = content_bank.load()
    return {"total": len(entries), "items": content_bank.search(entries, q, cat), "events": content_bank.EVENTS}


@app.post("/api/content-bank/retag")
async def content_bank_retag():
    """Re-run the tagging call on the whole library (one text call) and save it."""
    entries, log = await asyncio.to_thread(content_bank.tag_bank)
    content_bank.OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"total": len(entries), "items": entries, "log": log}


class SaveReq(BaseModel):
    data: dict
    source: str = "live"


@app.post("/api/story/save")
def save(r: SaveReq):
    return {"id": store.save_story(r.source, r.data.get("voice", ""), r.data.get("lang", ""), r.data, status="approved")}


@app.get("/api/stories")
def stories():
    return store.list_stories()


# ---------------- Live mode (SSE) ----------------
class LiveCheckReq(BaseModel):
    feed: str = "replay"
    match_id: str
    event_minute: int
    page: dict
    lang: str = "en"


@app.post("/api/live/check")
def live_check(r: LiveCheckReq):
    """Re-run the fact guard on a live page the editor edited, against the match as it was at that minute."""
    m = ADAPTERS[r.feed].get_match(r.match_id)
    seen = [e for e in m["events"] if e["minute"] <= r.event_minute]
    return {"flags": factcheck.check_page(r.page, factcheck.facts_from_match(_partial(m, seen)), r.lang)}


def _partial(m, upto):
    p = {**m, "events": upto}
    s = "0-0"
    for e in upto:
        if e["type"] == "goal": s = e["score_after"]
    h, a = map(int, s.split("-"))
    p["score"] = {"home": h, "away": a}
    return p


def _sse(kind, data):
    return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/live/stream")
async def live(feed: str = "replay", match_id: str = "m01", voice: str = "official", lang: str = "en", interval: float = 3.0):
    adapter = ADAPTERS[feed]
    m = await asyncio.to_thread(adapter.get_match, match_id)

    async def gen():
        yield _sse("meta", {"theme": _theme(m), "voice": voice, "lang": lang})
        seen, pages, used_photos = [], [], set()
        for ev in adapter.events(match_id):
            seen.append(ev)
            yield _sse("event", ev)
            if ev["type"] in KEY_EVENTS:
                t0 = time.perf_counter()
                try:
                    page, log = await asyncio.to_thread(llm.live_page, m, ev, pages, voice, lang, f"live:{match_id}")
                except Exception as e:
                    yield _sse("error", {"msg": str(e)[:200]}); continue
                facts = factcheck.facts_from_match(_partial(m, seen))
                flags = factcheck.check_page(page, facts, lang)
                try:
                    pk, _ = await asyncio.to_thread(media.pick_media, [page], _partial(m, seen), f"live:{match_id}", used_photos)
                    if pk.get(0):
                        page["photo"] = pk[0]; used_photos.add(pk[0]["id"])
                except Exception as e:
                    print("live media pick failed:", e)
                pages.append(page)
                yield _sse("draft", {"page": page, "flags": flags, "log": log, "event": ev,
                                     "latency_ms": int((time.perf_counter() - t0) * 1000)})
                if ev["type"] == "full_time":
                    try:
                        ex, log2 = await asyncio.to_thread(llm.extras, m, voice, lang, f"live:{match_id}")
                        fx = factcheck.facts_from_match(m)
                        qf = {i: factcheck.check_quiz_item(q, fx, lang) for i, q in enumerate(ex["quiz"])}
                        # quiz / poll backgrounds: same picker as the Editor tab, skipping photos the live pages used
                        ex["unit_backgrounds"] = cms.unit_backgrounds({"media": {str(i): {"id": pid} for i, pid in enumerate(used_photos)}})
                        yield _sse("extras", {**ex, "quiz_flags": qf, "log": log2})
                    except Exception as e:
                        yield _sse("error", {"msg": str(e)[:200]})
            await asyncio.sleep(interval)
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
