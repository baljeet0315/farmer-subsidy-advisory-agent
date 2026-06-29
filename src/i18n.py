"""Localization: Hindi (hi) + English (en) + Chhattisgarhi (cg).

Hindi and English are reliable; Chhattisgarhi is best-effort and always
delivered with a disclaimer. Handles UI strings and translation/localization
of the final checklist text.

TODO (Day 8):
- t(key, lang) for static UI strings
- localize(text, lang) for dynamic LLM output (with cg disclaimer)
"""
from __future__ import annotations

SUPPORTED = ("hi", "en", "cg")
CG_DISCLAIMER = "(छत्तीसगढ़ी अनुवाद अनुमानित है — कृपया सत्यापित करें।)"


def t(key: str, lang: str = "hi") -> str:
    """Static UI string lookup. TODO: implement."""
    raise NotImplementedError


def localize(text: str, lang: str = "hi") -> str:
    """Localize dynamic output; append disclaimer for cg. TODO: implement."""
    raise NotImplementedError
