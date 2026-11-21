"""Synthetic Story analytics export (SYNTHETIC DATA, for the Analytics explainer demo).

Shaped like a Stories CMS "export to Excel" saved as CSV: one row per page of each Story, with viewers,
shares, swipe ups, poll votes and quiz answers. A few patterns are planted on purpose so the explainer has
something real to find (and the tests can check it does):
  - stat pages lose far more viewers than other pages,
  - evening Stories (17-22h) reach more viewers than morning ones,
  - transfer and goals Stories reach the most viewers,
  - one quiz question (first quiz after S012) has a suspiciously low correct rate (a wrong answer key looks exactly like this).
Run: python data/make_analytics.py  -> data/analytics/sample_export.csv"""
import csv, random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "analytics" / "sample_export.csv"
COLS = ["story_id", "story_title", "category", "published_at", "page", "page_type", "viewers", "shares",
        "swipe_ups", "votes", "quiz_question", "quiz_answers", "quiz_correct"]
CLUBS = ["Nile City FC", "Delta Rovers", "Harbor Town United", "Sahara Falcons", "Alpine Wanderers",
         "Coral Bay Athletic", "Riverside Phoenix", "Granite Hill FC"]
CATEGORY_REACH = {"match-report": 1.0, "goals": 1.3, "transfer": 1.5, "injury": 0.8, "stats": 0.7, "fan-zone": 1.1}
RETAIN = {"moment": 0.91, "stat": 0.70, "quote": 0.88, "quiz": 0.95, "poll": 0.93, "cta": 0.86}
QUIZ_Q = ["Who scored the opening goal?", "What was the final score?", "Who was sent off?",
          "In which minute was the equaliser?", "Which team had more possession?"]


def slot_reach(hour):
    return 0.7 if hour < 12 else 1.1 if hour < 17 else 1.6 if hour < 23 else 0.6


def pages_for(cat, rnd):
    p = ["cover", "moment", "moment"]
    if cat in ("match-report", "stats") or rnd.random() < 0.4: p.append("stat")
    if cat == "stats": p.append("stat")
    if rnd.random() < 0.5: p.append("quote")
    if cat in ("match-report", "goals") or rnd.random() < 0.3: p.append("quiz")
    if rnd.random() < 0.7: p.append("poll")
    return p + ["cta"]


def make(seed=7, n=40):
    rnd, rows, planted = random.Random(seed), [], False
    start = datetime(2026, 10, 1)
    for k in range(n):
        cat = list(CATEGORY_REACH)[k % len(CATEGORY_REACH)]
        home, away = rnd.sample(CLUBS, 2)
        title = {"transfer": f"{home} sign a new striker", "injury": f"{home} injury update",
                 "stats": f"{home} v {away}: the numbers", "fan-zone": f"{home} fans take over"}.get(cat, f"{home} v {away}")
        when = start + timedelta(days=k * 3 // 4, hours=rnd.choice([8, 9, 10, 13, 14, 15, 18, 19, 20, 21]), minutes=rnd.choice([0, 15, 30, 45]))
        viewers = 4000 * CATEGORY_REACH[cat] * slot_reach(when.hour) * rnd.uniform(0.85, 1.15)
        for i, t in enumerate(pages_for(cat, rnd)):
            if i: viewers *= RETAIN[t] * rnd.uniform(0.97, 1.03)
            v = int(viewers)
            row = {c: "" for c in COLS} | {"story_id": f"S{k + 1:03d}", "story_title": title, "category": cat,
                   "published_at": when.strftime("%Y-%m-%d %H:%M"), "page": i + 1, "page_type": t, "viewers": v,
                   "shares": int(v * (0.03 if (t == "moment" and cat == "goals") else 0.008) * rnd.uniform(0.8, 1.2)),
                   "swipe_ups": int(v * 0.12 * rnd.uniform(0.8, 1.2)) if t == "cta" else 0,
                   "votes": int(v * 0.4 * rnd.uniform(0.85, 1.15)) if t == "poll" else 0}
            if t == "quiz":
                answers = int(v * 0.5 * rnd.uniform(0.9, 1.1))
                wrong_key = not planted and k >= 12  # planted once: a wrong answer key looks like this
                rate, planted = (0.07, True) if wrong_key else (rnd.uniform(0.55, 0.8), planted)
                row |= {"quiz_question": QUIZ_Q[k % len(QUIZ_Q)], "quiz_answers": answers, "quiz_correct": int(answers * rate)}
            else:
                row |= {"quiz_answers": 0, "quiz_correct": 0}
            rows.append(row)
    return rows


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = make()
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} rows, {len({r['story_id'] for r in rows})} Stories -> {OUT}")
