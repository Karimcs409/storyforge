"""Pydantic models + the strict JSON schemas sent to the LLM."""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

PAGE_TYPES = ["cover", "moment", "stat", "quote", "cta"]
TEMPLATES = ["cover-score", "moment", "stat-card", "quote", "cta"]
ICONS = ["ball", "card-yellow", "card-red", "whistle", "swap", "stat", "quote", "ticket", "none"]
CATEGORIES = ["match-report", "goals", "red-card", "comeback", "clean-sheet", "derby", "transfer", "injury",
              "youth", "womens-team", "fan-zone", "post-match-quotes", "stats"]
VOICES = {
    "official": "Official club channel: formal, factual, confident, no slang, no emojis.",
    "fan": "Fan zone: playful, energetic, short punchy lines, light banter, up to one emoji per page.",
}
LANGS = {"en": "English", "ar": "Modern Standard Arabic (natural, as used by Arab sports media)", "es": "Spanish"}

HEADLINE_MAX, CAPTION_MAX = 40, 140


class Page(BaseModel):
    type: Literal["cover", "moment", "stat", "quote", "cta"]
    template: Literal["cover-score", "moment", "stat-card", "quote", "cta"]
    icon: Literal["ball", "card-yellow", "card-red", "whistle", "swap", "stat", "quote", "ticket", "none"] = "none"
    headline: str
    caption: str
    media_hint: str
    minute: Optional[int] = None
    players_mentioned: list[str] = Field(default_factory=list)
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None


class QuizItem(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    kind: Literal["final_score", "first_scorer", "scorer", "goal_minute", "red_card", "yellow_card", "stat", "venue", "assist", "other"]
    answer_canonical: str  # the answer exactly as written in the source data (English names/numbers)
    stat_key: Literal["possession", "shots", "shots_on_target", "corners", "fouls", "none"] = "none"


class Poll(BaseModel):
    question: str
    options: list[str]


class Story(BaseModel):
    title: str
    pages: list[Page]
    quiz: list[QuizItem]
    poll: Poll
    categories: list[str]
    tags: list[str]

    @field_validator("categories")
    @classmethod
    def known_categories(cls, v):
        return [c for c in v if c in CATEGORIES]


class Extras(BaseModel):
    quiz: list[QuizItem]
    poll: Poll
    categories: list[str]
    tags: list[str]


# ---------- strict JSON schemas (all props required, nullable for optional) ----------
def _s(t, **kw):
    return {"type": t, **kw}


PAGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["type", "template", "icon", "headline", "caption", "media_hint", "minute", "players_mentioned", "cta_text", "cta_url"],
    "properties": {
        "type": _s("string", enum=PAGE_TYPES),
        "template": _s("string", enum=TEMPLATES),
        "icon": _s("string", enum=ICONS),
        "headline": _s("string", description=f"max {HEADLINE_MAX} characters"),
        "caption": _s("string", description=f"max {CAPTION_MAX} characters"),
        "media_hint": _s("string", description="which real photo/clip an editor should drop in (English)"),
        "minute": {"type": ["integer", "null"]},
        "players_mentioned": {"type": "array", "items": _s("string"),
                              "description": "every player/coach named on this page, spelled exactly as in the source"},
        "cta_text": {"type": ["string", "null"]},
        "cta_url": {"type": ["string", "null"]},
    },
}
QUIZ_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["question", "options", "correct_index", "kind", "answer_canonical", "stat_key"],
    "properties": {
        "question": _s("string"), "options": {"type": "array", "items": _s("string"), "minItems": 3, "maxItems": 4},
        "correct_index": _s("integer"),
        "kind": _s("string", enum=["final_score", "first_scorer", "scorer", "goal_minute", "red_card", "yellow_card", "stat", "venue", "assist", "other"]),
        "answer_canonical": _s("string", description="correct answer exactly as in source data: English name, number, or score like 2-1"),
        "stat_key": _s("string", enum=["possession", "shots", "shots_on_target", "corners", "fouls", "none"],
                       description="for kind=stat: which stat the question is about, else none"),
    },
}
POLL_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["question", "options"],
               "properties": {"question": _s("string"), "options": {"type": "array", "items": _s("string"), "minItems": 2, "maxItems": 4}}}
EXTRAS_PROPS = {
    "quiz": {"type": "array", "items": QUIZ_SCHEMA, "minItems": 3, "maxItems": 5},
    "poll": POLL_SCHEMA,
    "categories": {"type": "array", "items": _s("string", enum=CATEGORIES)},
    "tags": {"type": "array", "items": _s("string")},
}
STORY_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["title", "pages", "quiz", "poll", "categories", "tags"],
    "properties": {"title": _s("string"), "pages": {"type": "array", "items": PAGE_SCHEMA, "minItems": 5, "maxItems": 7}, **EXTRAS_PROPS},
}
EXTRAS_SCHEMA = {"type": "object", "additionalProperties": False, "required": list(EXTRAS_PROPS), "properties": EXTRAS_PROPS}
