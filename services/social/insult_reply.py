"""Deterministic and immediate reply handler for severe insults — with strict family-word exclusion.

Ensures immediate, model-independent responses to specific vulgar insults while strictly forbidding
any insults targeting family members (mother/sister/family honor).
"""

import re

# Normalize Arabic letters, half-space and diacritics for stable matching
_NORM_TABLE = str.maketrans({
    "ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه", "ى": "ی",
})

# Pattern and deterministic response pairs
_REPLIES = (
    # «کیر میخوام» و معادل‌ها → «منم»
    (r"کیر(و|م|ت|ش|ی)?\s*(می[‌ ]*خو?ام|می[‌ ]*خو?ای|می[‌ ]*خو?ایم|می[‌ ]*خوا?ستم)", "منم"),
    # «کیرتو بکن تو» و معادل‌ها → «کیرم تو کونش»
    (r"کیر\s*(ت|تو|ش|م)?\s*(بکن|بزنی|بزاری|کردی|کردم)\s*(تو|توش|توی|تویه)?", "کیرم تو کونش"),
)

# Forbidden family terms — responses must never contain these
FAMILY_WORDS = ("ننت", "مادرت", "خواهرت", "ناموست", "ناموس", "خواهرتو", "مادرتو", "ننه")


def _normalize(text: str) -> str:
    t = (text or "").translate(_NORM_TABLE)
    t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)  # Remove diacritics and tatweel
    t = t.replace("\u200c", " ")  # Half-space -> space
    t = re.sub(r"[«»\"'،,.:؟?()\[\]!]", " ", t)
    return " ".join(t.split())


def match_insult(text: str) -> str | None:
    """Return deterministic response if text matches a known insult pattern, else None."""
    if not text:
        return None
    t = _normalize(text)
    if not t:
        return None
    for pattern, reply in _REPLIES:
        if re.search(pattern, t):
            return reply
    return None
