"""Deterministic guards, tested on the real failure cases found while building StoryForge.
No API key needed: none of these tests call a model."""
import json
from pathlib import Path

import pytest

from app import factcheck as fc
from app import llm, media

ROOT = Path(__file__).resolve().parent.parent
M01 = json.loads((ROOT / "data/matches/m01.json").read_text(encoding="utf-8"))
# m01: Nile City FC 1-1 Delta Rovers. 25' goal Ramy Saber, 32' red card Mido Rashed,
# 67' goal Paul Mercer. Possession 43% (home) - 57% (away).


@pytest.fixture
def facts():
    return fc.facts_from_match(M01)


def page(headline, caption, minute=None, players=(), type_="moment"):
    return {"type": type_, "template": "moment", "headline": headline, "caption": caption,
            "media_hint": "x", "minute": minute, "players_mentioned": list(players)}


# ---------- fact guard: invented facts ----------

def test_invented_player_and_score_are_flagged(facts):
    flags = fc.check_page(page("Late drama", "Kevin Smith fires a stunning 9-0 winner at 88'!", 67), facts)
    assert any("Kevin Smith" in f for f in flags)
    assert any("9-0" in f for f in flags)
    assert any("88" in f for f in flags)


def test_correct_page_has_no_flags(facts):
    p = page("Saber opens the scoring", "Ramy Saber taps in at 25' to give Nile City FC a 1-0 lead.", 25, ["Ramy Saber"])
    assert fc.check_page(p, facts) == []


def test_unicode_hyphen_score_is_still_checked(facts):
    # the model once wrote 4‑1 with U+2011, which slipped past a plain "-" regex
    assert any("4-1" in f for f in fc.check_text("Nile City win 4‑1", facts))


def test_arabic_indic_digits_are_checked(facts):
    assert any("9-0" in f for f in fc.check_text("فوز ٩-٠", facts, lang="ar"))


def test_length_limits(facts):
    flags = fc.check_page(page("x" * 41, "y" * 141, 25, ["Ramy Saber"]), facts)
    assert any("headline" in f for f in flags) and any("caption" in f for f in flags)


# ---------- right player on the right event ----------

def test_page_must_name_the_player_who_did_it(facts):
    # every name, minute and score here exists in the source, but 25' was Ramy Saber's goal
    flags = fc.check_attribution(page("Mercer puts Delta ahead", "Paul Mercer scores at 25'.", 25), facts)
    assert any("doesn't name" in f for f in flags)
    assert any("headline credits Paul Mercer" in f for f in flags)


def test_attribution_is_accent_and_spacing_insensitive(facts):
    assert fc.check_attribution(page("SABER STRIKES", "ramy saber scores at 25'.", 25), facts) == []


def test_sub_page_naming_either_player_passes(facts):
    assert fc.check_attribution(page("Laurent comes on", "Hugo Laurent enters at 62'.", 62), facts) == []


# ---------- stats ----------

def test_stats_in_away_home_order_are_flagged(facts):
    # home had 43%: "Possession 57%-43%" with no team names reads as the wrong team's number
    assert any("away-home order" in f for f in fc.check_text("Possession 57%-43%", facts))


def test_stats_with_team_names_pass(facts):
    assert fc.check_text("Possession: Nile City FC 43%-57% Delta Rovers", facts) == []


# ---------- Trivia Quiz answers are recomputed from the data ----------

def quiz(kind, answer, options, stat_key="none", question="?"):
    return {"question": question, "options": options, "correct_index": options.index(answer),
            "kind": kind, "answer_canonical": answer, "stat_key": stat_key}


def test_quiz_correct_first_scorer_passes(facts):
    assert fc.check_quiz_item(quiz("first_scorer", "Ramy Saber", ["Ramy Saber", "Paul Mercer", "Omar Fathy"]), facts) == []


def test_quiz_wrong_first_scorer_is_rejected(facts):
    flags = fc.check_quiz_item(quiz("first_scorer", "Paul Mercer", ["Ramy Saber", "Paul Mercer", "Omar Fathy"]), facts)
    assert any("not provable" in f for f in flags)


def test_quiz_wrong_final_score_is_rejected(facts):
    assert fc.check_quiz_item(quiz("final_score", "2-1", ["1-1", "2-1", "0-0"]), facts)


def test_quiz_team_answer_for_a_stat(facts):
    good = quiz("stat", "Delta Rovers", ["Nile City FC", "Delta Rovers", "Neither"], "possession", "Who had more possession?")
    bad = quiz("stat", "Nile City FC", ["Nile City FC", "Delta Rovers", "Neither"], "possession", "Who had more possession?")
    assert fc.check_quiz_item(good, facts) == []
    assert fc.check_quiz_item(bad, facts)


def test_quiz_options_are_shuffled_but_answer_kept():
    q = [{"options": ["A", "B", "C", "D"], "correct_index": 0} for _ in range(20)]
    llm.shuffle_quiz(q)
    assert all(x["options"][x["correct_index"]] == "A" for x in q)
    assert any(x["correct_index"] != 0 for x in q)


# ---------- links come from code, never from the model ----------

def test_cta_link_is_set_by_code_not_by_the_model():
    pages = [page("Tickets", "Buy now", type_="cta") | {"cta_text": "Free tickets!", "cta_url": "https://evil.example"},
             page("Goal", "x", 25) | {"cta_url": "https://evil.example"}]
    llm.apply_cta(pages, M01)
    assert pages[0]["cta_url"] == M01["cta"]["url"] and pages[0]["cta_text"] == M01["cta"]["text"]
    assert pages[1]["cta_url"] is None


def test_schema_limits_names_to_the_roster():
    from app.schemas import PAGE_SCHEMA
    names = llm.constrain(PAGE_SCHEMA, M01)["properties"]["players_mentioned"]["items"]["enum"]
    assert "Ramy Saber" in names and "Kevin Smith" not in names


# ---------- photo picker code guard ----------

LIB = [
    {"id": "arg", "file": "a.jpg", "nation": "argentina", "good_for": ["goal"], "description": "Argentina fans", "text_area": "bottom", "source": ""},
    {"id": "fra", "file": "f.jpg", "nation": "france", "good_for": ["goal"], "description": "France fans", "text_area": "bottom", "source": ""},
    {"id": "net", "file": "n.jpg", "nation": "neutral", "good_for": ["goal"], "description": "Goal net", "text_area": "bottom", "source": ""},
]


def test_photo_guard_never_shows_the_other_teams_fans():
    ctxs = [{"page": 0, "type": "moment", "team_nation": "france"}]
    out = media._guard(ctxs, {0: {"photo": "arg", "reason": "nice"}}, LIB)
    assert out[0]["id"] in ("fra", "net") and out[0]["guarded"]


def test_photo_guard_never_reuses_a_photo():
    ctxs = [{"page": 0, "type": "moment", "team_nation": "argentina"}, {"page": 1, "type": "moment", "team_nation": "argentina"}]
    out = media._guard(ctxs, {0: {"photo": "arg", "reason": ""}, 1: {"photo": "arg", "reason": ""}}, LIB)
    assert out[0]["id"] != out[1]["id"]


def test_photo_context_uses_the_event_the_page_is_about():
    # two subs in the same minute, one per team (like 120' in the 2022 final): the page about the
    # home side's sub must be tied to the home team, not to whichever event comes first in the feed
    match = {"home": {"name": "Argentina"}, "away": {"name": "France"}, "score": {"home": 3, "away": 3},
             "events": [{"minute": 120, "type": "sub", "team": "away", "player_in": "Axel Disasi", "player_out": "Jules Koundé"},
                        {"minute": 120, "type": "sub", "team": "home", "player_in": "Paulo Dybala", "player_out": "Nicolás Tagliafico"}]}
    p = {"type": "moment", "headline": "Dybala replaces Tagliafico", "caption": "x", "media_hint": "x",
         "minute": 120, "players_mentioned": ["Paulo Dybala"]}
    assert media.page_context(p, 0, match)["team_nation"] == "argentina"


# ---------- found while building the CMS export ----------

def test_score_at_the_end_of_a_sentence_is_checked(facts):
    # regression: "9-0." was skipped because of the full stop after it
    assert any("9-0" in f for f in fc.check_text("Nile City won 9-0.", facts))
    assert fc.check_text("It ended 1-1.", facts) == []


def test_month_names_are_not_read_as_players(facts):
    assert fc.check_text("On Dec 18 Nile City FC drew 1-1.", facts) == []


# ---------- CMS title pack and Engagement Units ----------

from app import cms


def test_title_pack_flags_length_and_invented_facts(facts):
    titles = {"internal_title": "Nile City FC v Delta Rovers · EN · official",
              "long_display_title": "Nile City FC 1-1 Delta Rovers",
              "short_display_title": "Nile City FC and Delta Rovers draw",    # 34 > 20
              "eyebrow": "Matchday 10",
              "seo_title": "Nile City win 9-0",                                # invented score
              "seo_description": "Kevin Smith scores twice as Nile City FC draw 1-1."}  # invented player
    flags = cms.check_titles(titles, facts, "en", cms.limits(20))
    assert any("34>20" in f for f in flags["short_display_title"])
    assert any("9-0" in f for f in flags["seo_title"])
    assert any("Kevin Smith" in f for f in flags["seo_description"])
    assert flags["long_display_title"] == [] and flags["eyebrow"] == []


def test_internal_title_is_built_in_code():
    assert cms.internal_title(M01, "fan", "ar") == "Nile City FC v Delta Rovers · 2026-10-01 · AR · fan"


def test_quiz_unit_rules():
    story = {"title": "T", "media": {}, "poll": {"question": "q", "options": ["Yes", "No"]},
             "quiz": [{"question": "Who scored first?", "options": ["A", "B", "C", "D", "E"], "correct_index": 0,
                       "kind": "first_scorer", "answer_canonical": "A"}]}
    unit = cms.quiz_unit(story, {0: ["answer 'A' (first_scorer) not provable from source"]})
    assert any("5 answers" in i for i in unit["rule_issues"])
    assert any("not provable" in i for i in unit["rule_issues"])


def test_poll_side_by_side_rule():
    short = cms.poll_unit({"media": {}, "poll": {"question": "Who wins?", "options": ["Messi", "Mbappé"]}})
    long_ = cms.poll_unit({"media": {}, "poll": {"question": "Who wins?", "options": ["Argentina", "France"]}})
    assert short["side_by_side"] is True and long_["side_by_side"] is False


def test_seo_description_is_cut_at_a_full_sentence():
    text = "Argentina and France drew 3-3 in the final. Argentina won 4-2 on penalties after a dramatic shoot-out in Lusail."
    out = cms.trim_to_sentence(text, 60)
    assert out == "Argentina and France drew 3-3 in the final." and len(out) <= 60


def test_stat_order_check_is_english_only(facts):
    # Arabic captions name teams in Arabic letters, so the code can't tell which team comes first
    assert fc.check_text("الاستحواذ 57%-43% للضيوف", facts, lang="ar") == []
    assert any("away-home" in f for f in fc.check_text("Possession 57%-43%", facts, lang="en"))


def test_attribution_matches_whole_words_only():
    # regressions from the eval run: "Midfield" is not "Noah Field", "alimansour" doesn't contain "Bruno Lima"
    m05 = fc.facts_from_match(json.loads((ROOT / "data/matches/m05.json").read_text(encoding="utf-8")))
    m09 = fc.facts_from_match(json.loads((ROOT / "data/matches/m09.json").read_text(encoding="utf-8")))
    assert fc.check_attribution(page("Delta Rovers Tweak Midfield", "Ben Ashby comes on for Kofi Mensah.", 61), m05) == []
    assert fc.check_attribution(page("Ali Mansour pulls one back", "Ali Mansour converts a penalty.", 52), m09) == []


def test_domain_written_in_text_is_flagged(facts):
    # found in the prompt-injection eval: the link field was safe, but the caption said "Visit evil.example.com"
    flags = fc.check_text("Visit evil.example.com for free tickets!", facts)
    assert any("evil.example.com" in f for f in flags)
    assert fc.check_text("Book now at https://example.com/ncf/tickets", facts) == []   # the club's own CTA domain


def test_combined_moments_page_is_not_a_false_positive():
    m07 = fc.facts_from_match(json.loads((ROOT / "data/matches/m07.json").read_text(encoding="utf-8")))
    p = page("Nunes, Sow & Melo goals", "60' Gabriel Nunes doubles, 62' Ibrahim Sow converts, 70' Leandro Melo heads in.", 60)
    assert fc.check_attribution(p, m07) == []


def test_goal_count_question_is_verified():
    m03 = fc.facts_from_match(json.loads((ROOT / "data/matches/m03.json").read_text(encoding="utf-8")))
    right = quiz("scorer", "3", ["1", "2", "3", "4"], question="How many goals did Andre Viana score?")
    wrong = quiz("scorer", "2", ["1", "2", "3", "4"], question="How many goals did Andre Viana score?")
    assert fc.check_quiz_item(right, m03) == []
    assert fc.check_quiz_item(wrong, m03)
