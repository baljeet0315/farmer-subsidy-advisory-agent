"""Localization: Punjabi (pa) + English (en).

Two parts:
- t(key, lang): static UI strings (app labels/buttons).
- lang_instruction(lang): a sentence appended to LLM prompts so dynamic output
  (explanations, chat answers) comes back in the farmer's chosen language.
Both languages are treated as reliable; Punjabi has good LLM quality.
"""
from __future__ import annotations

SUPPORTED = ("pa", "en")
DEFAULT_LANG = "en"
LANG_NAMES = {"pa": "Punjabi", "en": "English"}

_STRINGS = {
    "title": {
        "en": "Punjab Farmer Subsidy & Advisory Navigator",
        "pa": "ਪੰਜਾਬ ਕਿਸਾਨ ਸਬਸਿਡੀ ਅਤੇ ਸਲਾਹ ਨੈਵੀਗੇਟਰ",
    },
    "find_button": {"en": "Find my schemes", "pa": "ਮੇਰੀਆਂ ਸਕੀਮਾਂ ਲੱਭੋ"},
    "documents": {"en": "Documents needed", "pa": "ਲੋੜੀਂਦੇ ਦਸਤਾਵੇਜ਼"},
    "what_you_get": {"en": "What you get", "pa": "ਤੁਹਾਨੂੰ ਕੀ ਮਿਲਦਾ ਹੈ"},
    "next_step": {"en": "Next step", "pa": "ਅਗਲਾ ਕਦਮ"},
    "ask_followup": {"en": "Ask a follow-up", "pa": "ਹੋਰ ਸਵਾਲ ਪੁੱਛੋ"},
    "no_match": {
        "en": "No schemes matched your profile. Please check with your local agriculture office / CSC.",
        "pa": "ਤੁਹਾਡੇ ਵੇਰਵਿਆਂ ਨਾਲ ਕੋਈ ਸਕੀਮ ਮੇਲ ਨਹੀਂ ਖਾਂਦੀ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਸਥਾਨਕ ਖੇਤੀਬਾੜੀ ਦਫ਼ਤਰ / CSC ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    },
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    lang = lang if lang in SUPPORTED else DEFAULT_LANG
    entry = _STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get(DEFAULT_LANG, key))


def lang_instruction(lang: str) -> str:
    """Prompt fragment telling the model which language to write prose in."""
    if lang == "pa":
        return " Write the human-readable text (explanation, next_step, answers) in Punjabi (Gurmukhi script). Keep any JSON keys in English."
    return " Write in clear, simple English."
