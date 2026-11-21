"""CMS-ready output: the title pack a Story needs and the Trivia Quiz / Poll as Engagement Units,
shaped like the fields an editor fills in by hand in a Stories CMS (titles with length rules,
quiz questions with a correct-answer toggle, poll answers, backgrounds).

Rules follow a public Stories-CMS user guide where it states them (eyebrow soft limit 20,
Short Display Title max length set per category, Clip internal title max 250, quiz <=4 answers,
poll 2-4 answers, two short poll answers shown side by side when each is under 7 chars).
Limits the guide doesn't state (long title, SEO fields) are our own defaults and labelled as such."""
import json

from . import llm, factcheck, media

# limit, source of the rule
TITLE_RULES = {
    "internal_title": (250, "guide (Clip internal title max)"),
    "long_display_title": (60, "StoryForge default"),
    "short_display_title": (20, "set per category in the CMS (default here)"),
    "eyebrow": (20, "guide (soft limit)"),
    "seo_title": (60, "StoryForge default (search snippet)"),
    "seo_description": (155, "StoryForge default (search snippet)"),
}
AI_FIELDS = ["long_display_title", "short_display_title", "eyebrow", "seo_title", "seo_description"]


def internal_title(match: dict | None, voice: str, lang: str) -> str:
    """Built in code, not by the model: it is an identifier, so it must be exact and consistent."""
    if not match:
        return f"Article Story · {lang.upper()} · {voice}"
    return f"{match['home']['name']} v {match['away']['name']} · {match.get('date', '')} · {lang.upper()} · {voice}"


def limits(short_max: int | None = None) -> dict:
    lim = {k: v[0] for k, v in TITLE_RULES.items()}
    if short_max:
        lim["short_display_title"] = short_max
    return lim


def _schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": AI_FIELDS,
            "properties": {k: {"type": "string", "description": f"max {TITLE_RULES[k][0]} characters"} for k in AI_FIELDS}}


def title_pack(story: dict, match=None, article=None, voice="official", lang="en", short_max=None, ref=""):
    """One small LLM call writes the user-facing titles; code checks lengths and facts and retries what fails."""
    lim = limits(short_max)
    pages = [{k: p[k] for k in ("type", "headline", "caption")} for p in story["pages"]]
    base = (f"Here is the drafted Story:\nTITLE: {story['title']}\nPAGES: {json.dumps(pages, ensure_ascii=False)}\n\n"
            "Write the CMS titles for this Story:\n"
            f"- long_display_title (max {lim['long_display_title']}): shown on rectangular thumbnails\n"
            f"- short_display_title (max {lim['short_display_title']}): shown under circular thumbnails, must not be cut off\n"
            f"- eyebrow (max {lim['eyebrow']}): short tagline above the title, e.g. competition or round\n"
            f"- seo_title (max {lim['seo_title']}) and seo_description (max {lim['seo_description']}): for Google Web Stories\n"
            "Every character limit is strict: aim for about 80% of each limit. Use only facts from SOURCE and the Story.")
    note, logs = "", []
    for attempt in range(3):
        msgs = [{"role": "system", "content": llm.SYSTEM},
                {"role": "user", "content": f"{llm.source_block(match, article)}\n\n{llm._voice_lang(voice, lang)}\n\n{base}{note}"}]
        data, log = llm.call_json("title_pack", msgs, _schema(), "titles", ref=ref)
        logs.append(log)
        titles = {"internal_title": internal_title(match, voice, lang), **{k: data[k].strip() for k in AI_FIELDS}}
        flags = check_titles(titles, _facts(match, article), lang, lim)
        bad = {k: v for k, v in flags.items() if v}
        if not bad:
            break
        note = "\n\nYour previous answer broke these rules, fix them:\n" + "\n".join(f"- {k}: {'; '.join(v)}" for k, v in bad.items())
    # last resort for the long free-text field: cut at the last full sentence inside the limit (normal for meta descriptions)
    if len(titles["seo_description"]) > lim["seo_description"]:
        titles["seo_description"] = trim_to_sentence(titles["seo_description"], lim["seo_description"])
        flags = check_titles(titles, _facts(match, article), lang, lim)
    usage = {"task": "title_pack", "model": logs[-1]["model"], "calls": len(logs), "ms": sum(l["ms"] for l in logs),
             "usd": round(sum(l["usd"] for l in logs), 6),
             "tokens_in": sum(l["tokens_in"] for l in logs), "tokens_out": sum(l["tokens_out"] for l in logs)}
    return titles, flags, usage


def trim_to_sentence(text: str, limit: int) -> str:
    """Cut at the last '.', '!' or '?' within the limit; if there is none, at the last word plus an ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if end >= limit * 0.5:
        return cut[:end + 1].strip()
    return cut[:cut.rfind(" ")].rstrip(" ,;:") + "…"


def _facts(match, article):
    return factcheck.facts_from_match(match) if match else factcheck.facts_from_article(article or "")


def check_titles(titles: dict, facts, lang="en", lim=None) -> dict:
    """Length rule + the same fact guard as pages (scores, minutes, %; names on the longer free-text fields)."""
    lim = lim or limits()
    out = {}
    for k, v in titles.items():
        issues = []
        if not v.strip():
            issues.append("empty")
        if len(v) > lim[k]:
            issues.append(f"{len(v)}>{lim[k]} chars")
        if k != "internal_title":
            issues += factcheck.check_text(v, facts, lang, names=(k == "seo_description"))
        out[k] = sorted(set(issues))
    return out


# ---------------- Engagement Units ----------------

def _backgrounds(story: dict, n: int) -> list[dict]:
    """Pick neutral library photos not already used on Story pages (quiz/poll pages carry text, so calm images)."""
    used = {m["id"] for m in (story.get("media") or {}).values()}
    lib = [p for p in media.load_library() if p["id"] not in used]
    lib.sort(key=lambda p: (p["nation"] != "neutral", p["mood"] != "calm",
                            not any(g in p["good_for"] for g in ("stat", "full_time", "cover"))))
    return [{"id": p["id"], "file": p["file"], "source": p["source"]} for p in lib[:n]]


def unit_backgrounds(story: dict) -> dict:
    """Quiz default, quiz results and poll backgrounds, picked once and stored on the Story so the phone preview
    and the CMS export always show the same photos."""
    if story.get("unit_backgrounds"):
        return story["unit_backgrounds"]
    bg = _backgrounds(story, 3)
    pick = lambda i: bg[i] if len(bg) > i else (bg[0] if bg else None)
    return {"quiz": pick(0), "quiz_results": pick(1), "poll": pick(2)}


def quiz_unit(story: dict, quiz_flags: dict) -> dict:
    """Trivia Quiz as an editor would build it: title, default background, questions (<=4 answers, one correct), results page."""
    ub = unit_backgrounds(story)
    qs = []
    for i, q in enumerate(story["quiz"]):
        flags = quiz_flags.get(i) or quiz_flags.get(str(i)) or []
        qs.append({"title": q["question"],
                   "answers": [{"text": o, "correct": j == q["correct_index"]} for j, o in enumerate(q["options"])],
                   "verified_in_code": not flags, "check": f"{q['kind']}: {q['answer_canonical']}", "flags": flags})
    unit = {"type": "trivia_quiz", "title": f"{story['title']} – Quiz"[:120],
            "default_background": ub["quiz"], "questions": qs, "results_background": ub["quiz_results"]}
    unit["rule_issues"] = quiz_rules(unit)
    return unit


def quiz_rules(unit: dict) -> list[str]:
    issues = []
    if not unit["questions"]:
        issues.append("needs at least one question")
    for i, q in enumerate(unit["questions"], 1):
        n = len(q["answers"])
        if n < 2 or n > 4:
            issues.append(f"Q{i}: {n} answers (2-4 allowed)")
        if sum(a["correct"] for a in q["answers"]) != 1:
            issues.append(f"Q{i}: exactly one answer must be marked correct")
        if not q["verified_in_code"]:
            issues.append(f"Q{i}: correct answer not provable from the source")
    return issues


def poll_unit(story: dict) -> dict:
    poll = story["poll"]
    answers = [a.strip() for a in poll["options"]]
    unit = {"type": "poll", "question": poll["question"], "answer_type": "text", "answers": answers,
            "add_question_text_to_background": True,
            "side_by_side": len(answers) == 2 and all(len(a) < 7 for a in answers),
            "background": unit_backgrounds(story)["poll"]}
    unit["rule_issues"] = [] if 2 <= len(answers) <= 4 else [f"{len(answers)} answers (2-4 allowed)"]
    return unit


def export(data: dict) -> dict:
    """Everything an editor would otherwise type into the CMS, in one object."""
    st, rep = data["story"], data["report"]
    return {
        "titles": st.get("titles", {}),
        "categories": st.get("categories", []), "tags": st.get("tags", []),
        "pages": [{"order": i + 1, "type": p["type"], "template": p["template"], "headline": p["headline"],
                   "caption": p["caption"], "added_by_editor": bool(p.get("added_by_editor")), "photo": (st.get("media") or {}).get(str(i), {}).get("file"),
                   "cta": {"text": p["cta_text"], "url": p["cta_url"]} if p.get("cta_url") else None}
                  for i, p in enumerate(st["pages"])],
        "engagement_units": [quiz_unit(st, rep.get("quiz_flags", {})), poll_unit(st)],
    }
