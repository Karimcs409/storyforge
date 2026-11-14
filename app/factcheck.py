"""Fact guard: deterministic code (no LLM) that checks every score, minute, number and name
in a generated Story / page / quiz against the input data."""
import re, unicodedata
from dataclasses import dataclass, field

from .schemas import HEADLINE_MAX, CAPTION_MAX

# Arabic-Indic digits -> 0-9, and every dash/hyphen variant (models love U+2011) -> "-"
AR_DIGITS = str.maketrans({**{c: str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}, **{c: "-" for c in "‐‑‒–—−"}})
SCORE_RE = re.compile(r"(?<![\d.])(\d{1,2})\s*[-–:]\s*(\d{1,2})(?![\d.])")
MINUTE_RE = re.compile(r"(\d{1,3})\s*(?:'|’|′|\+\d+'|(?:st|nd|rd|th)?\s*(?:min\b|minute))|(?:minute|min\.?|الدقيقة|دقيقة)\s*(\d{1,3})", re.I)
PCT_RE = re.compile(r"(\d{1,3})\s*%")
NAME_RE = re.compile(r"\b([A-Z][a-zà-ÿ]+(?:[ ]+(?:[A-Z][a-zà-ÿ]+|Jr|FC))+)\b")
COMMON = {"Full", "Time", "Half", "Match", "Day", "Matchday", "Game", "Goal", "Final", "Whistle", "Man", "The", "What",
          "Player", "Of", "Get", "Tickets", "Next", "Home", "Away", "Who", "Big", "Red", "Card", "Yellow", "Kick", "Off",
          "League", "Premier", "Continental", "Fan", "Zone", "Club", "Official", "Story", "Stats", "Watch", "Highlights",
          "Back", "Three", "Points", "Clean", "Sheet", "Late", "Drama", "Late", "Super", "Sub", "First", "Second", "Our",
          "Their", "Comeback", "Win", "Victory", "Draw", "Defeat", "Hero", "Heroes", "Moment", "Night", "Magic", "Boss",
          "Coach", "Head", "Snapshot", "Recap", "Report", "Stay", "Updated", "Support", "Shock", "Follow", "Tune", "Share", "Vote", "Defender", "Midfielder", "Striker", "Forward", "Goalkeeper", "Keeper", "Captain", "Winger",
          "Substitute", "Skipper", "Manager", "Fans", "Supporters", "Kickoff", "Interval", "Break", "Penalty", "Header", "Buy", "Now", "Book", "Your", "Seat", "Join", "Us", "See", "You", "There", "Vs", "And", "In"}


def fold(s: str) -> str:
    """accent- and case-insensitive letters only: 'Ángel Di María' -> 'angel di maria'"""
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z ]+", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").translate(AR_DIGITS)).strip().lower()


@dataclass
class Facts:
    names: set = field(default_factory=set)       # people
    entities: set = field(default_factory=set)    # people + teams + venue + competition
    minutes: set = field(default_factory=set)
    scores: set = field(default_factory=set)      # "h-a" strings, both orientations
    numbers: set = field(default_factory=set)
    stat_pairs: set = field(default_factory=set)  # "14-7" style stat comparisons, home-away order
    stat_pairs_rev: set = field(default_factory=set)  # same pairs in away-home order
    home: str = ""
    away: str = ""
    yellow_cards: set = field(default_factory=set)
    card_minutes: dict = field(default_factory=dict)  # "red"/"yellow" -> {minutes}
    final_score: str | None = None
    scorers: list = field(default_factory=list)   # in order
    goal_minutes: set = field(default_factory=set)
    red_cards: set = field(default_factory=set)
    assists: set = field(default_factory=set)
    venue: str | None = None
    stats: dict = field(default_factory=dict)     # stat_key -> {team name: value}
    events_at: dict = field(default_factory=dict) # minute -> [(event type, [players involved])]
    source: str = "match"


def facts_from_match(m: dict) -> Facts:
    f = Facts(home=m["home"]["name"], away=m["away"]["name"])
    for side in ("home", "away"):
        t = m[side]
        f.names.update(t["lineup"] + t.get("bench", []) + [t["coach"]])
        f.entities.update([t["name"], t["short"]])
    for q in m.get("quotes", []):
        f.names.add(q["speaker"])
    f.venue = m.get("venue")
    f.entities.update(f.names | {m.get("venue", ""), m.get("competition", "")})
    hs = as_ = 0
    f.scores.add("0-0")
    for e in m["events"]:
        f.minutes.add(e["minute"])
        who = [x for x in (e.get("player"), e.get("player_in"), e.get("player_out"), e.get("assist")) if x and x != "own goal"]
        if who:
            f.events_at.setdefault(e["minute"], []).append((e["type"], who))
        if e["type"] == "goal":
            hs, as_ = map(int, e["score_after"].split("-"))
            f.scores.update({f"{hs}-{as_}", f"{as_}-{hs}"})
            f.scorers.append(e["player"]); f.goal_minutes.add(e["minute"])
            if e.get("assist"): f.assists.add(e["assist"])
        if e["type"] in ("red_card", "yellow_card"):
            col = e["type"].split("_")[0]
            (f.red_cards if col == "red" else f.yellow_cards).add(e["player"])
            f.card_minutes.setdefault(col, set()).add(e["minute"])
    h, a = m["score"]["home"], m["score"]["away"]
    f.final_score = f"{h}-{a}"
    f.scores.update({f"{h}-{a}", f"{a}-{h}"})
    if m.get("penalties"):  # shoot-out result is a valid score to mention
        ph, pa = m["penalties"]["score"].split("-")
        f.scores.update({f"{ph}-{pa}", f"{pa}-{ph}"})
    for key, vals in m.get("stats", {}).items():
        f.stats[key] = {m["home"]["name"]: vals[0], m["away"]["name"]: vals[1]}
        f.numbers.update(vals)
        f.stat_pairs.add(f"{vals[0]}-{vals[1]}")
        if vals[0] != vals[1]: f.stat_pairs_rev.add(f"{vals[1]}-{vals[0]}")
    f.numbers.update(f.minutes | {h, a, m.get("matchday", 0)} | set(range(0, 12)))
    return f


def facts_from_article(text: str) -> Facts:
    t = text.translate(AR_DIGITS)
    f = Facts(source="article")
    f.names = set(NAME_RE.findall(t))
    f.entities = set(f.names)
    for a, b in SCORE_RE.findall(t):
        f.scores.update({f"{a}-{b}", f"{b}-{a}"})
    for g in MINUTE_RE.findall(t):
        f.minutes.add(int(g[0] or g[1]))
    f.numbers = {int(n) for n in re.findall(r"\d+", t)} | set(range(0, 12))
    f.minutes |= {n for n in f.numbers if n <= 120}
    return f


def _in(name: str, pool: set) -> bool:
    n = norm(name)
    return any(n == norm(p) for p in pool) or any(n and n in norm(p) for p in pool)


def check_text(text: str, f: Facts, lang: str = "en", names: bool = True) -> list[str]:
    issues, t = [], (text or "").translate(AR_DIGITS)
    away_first = bool(f.away) and 0 <= t.lower().find(f.away.lower()) < (t.lower().find(f.home.lower()) % 10**6)
    for a, b in SCORE_RE.findall(re.sub(r"(\d)\s*%", r"\1", t)):  # "57%-43%" is a pair too
        pair = f"{int(a)}-{int(b)}"
        if pair in f.scores or pair in f.stat_pairs:
            continue
        if pair in f.stat_pairs_rev:
            if not away_first:  # e.g. "Possession 57%-43%" when home had 43%: reads as the wrong team's number
                issues.append(f"stat {a}-{b} is in away-home order without naming the away team first")
            continue
        issues.append(f"score {a}-{b} not in source")
    for g in MINUTE_RE.findall(t):
        mi = int(g[0] or g[1])
        if mi not in f.minutes:
            issues.append(f"minute {mi}' not in source")
    for p in PCT_RE.findall(t):
        if int(p) not in f.numbers:
            issues.append(f"{p}% not in source")
    if lang == "en" and names:
        # Title-case headlines produce many capitalised phrases, so names are checked on captions only:
        # remove known entities, then flag 2+ consecutive capitalised words that match nothing in the source.
        rest = t
        for e in sorted(f.entities, key=len, reverse=True):
            if e: rest = re.sub(re.escape(e), " ", rest, flags=re.I)
        for cand in NAME_RE.findall(rest):
            words = [w for w in cand.split() if w not in COMMON]
            if len(words) >= 2 and not any(any(norm(w) in norm(e).split() for e in f.entities) for w in words):
                issues.append(f"unknown name '{cand}'")
    return issues


def check_page(p: dict, f: Facts, lang: str = "en") -> list[str]:
    issues = []
    if len(p.get("headline", "")) > HEADLINE_MAX:
        issues.append(f"headline {len(p['headline'])}>{HEADLINE_MAX} chars")
    if len(p.get("caption", "")) > CAPTION_MAX:
        issues.append(f"caption {len(p['caption'])}>{CAPTION_MAX} chars")
    if p.get("minute") is not None and p["minute"] not in f.minutes:
        issues.append(f"minute field {p['minute']} not in source")
    for name in p.get("players_mentioned", []):
        if not _in(name, f.names):
            issues.append(f"player '{name}' not in source")
    issues += check_text(p.get("headline", ""), f, lang, names=False)  # headlines are Title Case: numbers only
    issues += check_text(p.get("caption", ""), f, lang)
    issues += check_attribution(p, f, lang)
    if p.get("type") == "cta" and not (p.get("cta_text") and p.get("cta_url")):
        issues.append("cta page without cta_text/cta_url")
    return sorted(set(issues))


def check_attribution(p: dict, f: Facts, lang: str = "en") -> list[str]:
    """Right name on the right event: a page tied to minute X must name the player who actually did the
    key thing at X (e.g. 22' goal -> Messi, not Di María, even though both names exist in the source)."""
    evs = f.events_at.get(p.get("minute"))
    if f.source != "match" or not evs or p.get("type") != "moment":
        return []
    key = [(t, who) for t, who in evs if t in ("goal", "red_card", "sub")] or evs
    involved = {w for _, who in key for w in who}
    if lang == "en":
        text = fold(f"{p.get('headline', '')} {p.get('caption', '')}")
        squashed = text.replace(" ", "")
        ok = any(tok in text.split() or (len(tok) > 4 and tok in squashed)
                 for w in involved for tok in fold(w).split() if len(tok) > 2)
    else:  # Arabic text: rely on the source-spelled players_mentioned list
        ok = bool({fold(x) for x in p.get("players_mentioned", [])} & {fold(w) for w in involved})
    what = "; ".join(f"{t.replace('_', ' ')}: {', '.join(who)}" for t, who in key)
    issues = [] if ok else [f"{p['minute']}' is {what}, but the page doesn't name them"]
    if lang == "en":  # the headline must not credit someone who had no part in this minute's event
        head = fold(p.get("headline", ""))
        mine = {tok for w in involved for tok in fold(w).split()}
        for name in f.names - involved:
            toks = [t for t in fold(name).split() if len(t) > 3 and t not in mine]
            last = fold(name).split()[-1] if fold(name).split() else ""
            hit = (last in toks and (last in head.split() or last in head.replace(" ", ""))) or                   (len(fold(name).replace(" ", "")) > 5 and fold(name).replace(" ", "") in head.replace(" ", ""))
            if hit:
                issues.append(f"headline credits {name}, but {p['minute']}' is {what}")
                break
    return issues


def _num(s):
    m = re.search(r"\d+", norm(s))
    return int(m.group()) if m else None


WORDNUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def _stat_ok(q, canon, f: Facts) -> bool:
    """Numeric answer: value must exist for that stat. Team answer: that team must have the value named in the
    question, or (no number in question) the higher value for stat_key."""
    key, vals = q.get("stat_key", "none"), None
    vals = f.stats.get(key)
    n = _num(canon)
    if n is not None:
        return n in (vals.values() if vals else f.numbers)
    if not vals:
        return False
    team = next((t for t in vals if norm(t) == norm(canon) or norm(canon) in norm(t)), None)
    if not team:
        return False
    qt = norm(q.get("question", ""))
    asked = _num(qt)
    if asked is None:
        asked = next((v for w, v in WORDNUM.items() if re.search(rf"{w}", qt)), None)
    if asked is not None:
        return vals[team] == asked and list(vals.values()).count(asked) == 1
    other = [v for t, v in vals.items() if t != team][0]
    return vals[team] > other


def check_quiz_item(q: dict, f: Facts, lang: str = "en") -> list[str]:
    issues, opts = [], q.get("options", [])
    if not 3 <= len(opts) <= 4: issues.append(f"{len(opts)} options (need 3-4)")
    if len({norm(o) for o in opts}) != len(opts): issues.append("duplicate options")
    ci = q.get("correct_index", -1)
    if not 0 <= ci < len(opts):
        return issues + ["correct_index out of range"]
    canon, kind = q.get("answer_canonical", ""), q.get("kind")
    cn = norm(canon).replace(" ", "").replace("–", "-")
    ok = {
        "final_score": lambda: f.final_score and cn in {f.final_score, "-".join(reversed(f.final_score.split("-")))},
        "first_scorer": lambda: bool(f.scorers) and norm(canon) == norm(f.scorers[0]),
        "scorer": lambda: _in(canon, set(f.scorers)),
        "goal_minute": lambda: _num(canon) in f.goal_minutes,
        "red_card": lambda: _in(canon, f.red_cards) or _num(canon) in f.card_minutes.get("red", set()),
        "yellow_card": lambda: _in(canon, f.yellow_cards) or _num(canon) in f.card_minutes.get("yellow", set()),
        "assist": lambda: _in(canon, f.assists),
        "stat": lambda: _stat_ok(q, canon, f),
        "venue": lambda: bool(f.venue) and norm(canon) == norm(f.venue),
        "other": lambda: _in(canon, f.entities) or (_num(canon) is not None and _num(canon) in f.numbers),
    }
    if f.source == "article":  # no structured events: only check the answer appears in the article
        valid = _in(canon, f.entities) or (_num(canon) is not None and _num(canon) in f.numbers) or cn in f.scores
    else:
        valid = ok.get(kind, ok["other"])()
    if not valid:
        issues.append(f"answer '{canon}' ({kind}) not provable from source")
    correct = norm(opts[ci]).replace(" ", "")
    if lang == "en":
        if norm(canon).replace(" ", "") not in correct:
            issues.append("correct option does not match answer_canonical")
    elif _num(canon) is not None and _num(opts[ci]) != _num(canon):
        issues.append("correct option number does not match answer_canonical")
    for i, o in enumerate(opts):
        if i != ci and norm(o).replace(" ", "") == correct:
            issues.append("another option equals the correct answer")
    return issues


def check_story(story: dict, f: Facts, lang: str = "en") -> dict:
    pages = story.get("pages", [])
    page_flags = {i: check_page(p, f, lang) for i, p in enumerate(pages)}
    story_flags = []
    if not 5 <= len(pages) <= 7: story_flags.append(f"{len(pages)} pages (need 5-7)")
    if pages and pages[0].get("type") != "cover": story_flags.append("first page is not a cover")
    if not any(p.get("type") == "cta" and p.get("cta_url") for p in pages): story_flags.append("no CTA page")
    quiz = story.get("quiz", [])
    quiz_flags = {i: check_quiz_item(q, f, lang) for i, q in enumerate(quiz)}
    if not 3 <= len(quiz) <= 5: story_flags.append(f"{len(quiz)} quiz questions (need 3-5)")
    po = story.get("poll", {}).get("options", [])
    if not 2 <= len(po) <= 4: story_flags.append(f"poll has {len(po)} options (need 2-4)")
    if not 3 <= len(story.get("categories", [])) + len(story.get("tags", [])): story_flags.append("too few categories/tags")
    n_flag = sum(1 for v in page_flags.values() if v) + sum(1 for v in quiz_flags.values() if v) + len(story_flags)
    return {"ok": n_flag == 0, "page_flags": page_flags, "quiz_flags": quiz_flags, "story_flags": story_flags,
            "quiz_verified": sum(1 for v in quiz_flags.values() if not v), "quiz_total": len(quiz)}
