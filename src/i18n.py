"""Localization: Punjabi (pa) + English (en).

Punjabi is the primary farmer-facing language for Punjab and has good LLM
quality, so both languages are treated as reliable. Handles UI strings and
localization of the final checklist text.

TODO (Day 8):
- t(key, lang) for static UI strings
- localize(text, lang) for dynamic LLM output
"""
from __future__ import annotations

SUPPORTED = ("pa", "en")
DEFAULT_LANG = "pa"

LANG_NAMES = {"pa": "ਪੰਜਾਬੀ (Punjabi)", "en": "English"}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Static UI string lookup. TODO: implement."""
    raise NotImplementedError


def localize(text: str, lang: str = DEFAULT_LANG) -> str:
    """Localize dynamic output to the target language. TODO: implement."""
    raise NotImplementedError
