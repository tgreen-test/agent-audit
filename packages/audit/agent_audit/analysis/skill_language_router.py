"""
Primary-language detector for SKILL.md descriptions (Layer 3 helper).

Routes a description string to one of the supported language codes
({en, zh, ja, ko, es, fr, de, pt}) or to ``unsupported``. The router uses
``langdetect`` plus a CJK Unicode-block correction (the poster's
correction: langdetect frequently mislabels ZH/JA/KO mixtures, but the
block counts disambiguate them deterministically).

The router never emits findings. It only labels. When detection cannot
make a confident call, it returns ``"unsupported"`` so the caller takes
the fail-closed NullJudge branch (PLAN §0 constraint #4).
"""

from __future__ import annotations

from typing import Optional


SUPPORTED_LANGUAGES = {"en", "zh", "ja", "ko", "es", "fr", "de", "pt"}

# Minimum number of CJK characters required to invoke block-based correction.
# Below this threshold, langdetect's verdict is trusted.
_CJK_OVERRIDE_THRESHOLD = 4

# Minimum total characters (after stripping) for any detection attempt.
# Shorter inputs cannot be reliably classified and route to "unsupported".
_MIN_LEN_FOR_DETECTION = 8


def _count_blocks(text: str) -> dict:
    """Count characters in the CJK script blocks that disambiguate JA / ZH / KO."""
    counts = {"hiragana": 0, "katakana": 0, "hangul": 0, "cjk_ideograph": 0}
    for ch in text:
        cp = ord(ch)
        if 0x3040 <= cp <= 0x309F:
            counts["hiragana"] += 1
        elif 0x30A0 <= cp <= 0x30FF:
            counts["katakana"] += 1
        elif 0xAC00 <= cp <= 0xD7AF:
            counts["hangul"] += 1
        elif 0x4E00 <= cp <= 0x9FFF:
            counts["cjk_ideograph"] += 1
    return counts


def _cjk_correction(text: str) -> Optional[str]:
    """Return ja|zh|ko if CJK script counts clearly identify the language."""
    counts = _count_blocks(text)
    total_cjk = sum(counts.values())
    if total_cjk < _CJK_OVERRIDE_THRESHOLD:
        return None
    # Hangul presence dominates → Korean
    if counts["hangul"] > 0 and counts["hangul"] >= max(counts["hiragana"], counts["katakana"]):
        return "ko"
    # Kana presence dominates → Japanese
    if counts["hiragana"] + counts["katakana"] > 0:
        return "ja"
    # Pure CJK ideographs without kana / hangul → Chinese
    if counts["cjk_ideograph"] > 0:
        return "zh"
    return None


def _normalize_declared(declared: Optional[str]) -> Optional[str]:
    if not declared:
        return None
    code = declared.strip().lower().replace("_", "-")
    head = code.split("-", 1)[0]
    aliases = {
        "english": "en",
        "chinese": "zh",
        "mandarin": "zh",
        "japanese": "ja",
        "korean": "ko",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "portuguese": "pt",
    }
    if head in SUPPORTED_LANGUAGES:
        return head
    return aliases.get(head)


def detect_language(text: str, declared: Optional[str] = None) -> str:
    """Detect primary language of ``text`` (with an optional declared hint).

    Returns one of the supported language codes or ``"unsupported"``.
    Declared hints from frontmatter are honored when they map cleanly onto a
    supported code; otherwise content-based detection runs.
    """
    declared_norm = _normalize_declared(declared)
    if declared_norm:
        return declared_norm

    if not text or len(text.strip()) < _MIN_LEN_FOR_DETECTION:
        return "unsupported"

    cjk = _cjk_correction(text)
    if cjk is not None:
        return cjk

    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        code = detect(text)
    except Exception:
        return "unsupported"

    head = code.split("-", 1)[0].lower()
    if head in SUPPORTED_LANGUAGES:
        return head
    return "unsupported"
