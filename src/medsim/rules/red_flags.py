"""LLM-independent red-flag detector.

Pure-Python keyword/regex matching over Turkish-normalized free text.
Designed for ZERO false negatives on critical patterns; precision is a
secondary concern (false positives only escalate severity).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RedFlagPattern(BaseModel):
    """A red-flag pattern: list of OR-keyword groups, AND across groups."""

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    keyword_groups: list[list[str]] = Field(..., min_length=1)


_NON_LETTER_RE = re.compile(r"[^\w\sçğıöşüÇĞİÖŞÜ]+", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def _strip_diacritics(text: str) -> str:
    """Best-effort normalization: lowercase + strip combining marks.

    We *keep* a copy of the original lowercased text too, so callers can
    match either with or without diacritics. Turkish-specific letters
    (ç, ğ, ı, ö, ş, ü) become c/g/i/o/s/u after NFKD stripping, which
    matches the way YAML keywords are commonly authored.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _normalize(text: str) -> str:
    lowered = text.lower().replace("i̇", "i")
    cleaned = _NON_LETTER_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", cleaned).strip()


def _keyword_in(keyword: str, normalized: str, normalized_ascii: str) -> bool:
    """Match a keyword using simple substring containment.

    Works on both the diacritic-preserving and the ASCII-folded versions
    of the input, so a YAML keyword like `gogus` will catch `göğüs` and
    vice-versa.
    """
    kw = keyword.strip().lower()
    if not kw:
        return False
    kw_ascii = _strip_diacritics(kw)
    return kw in normalized or kw_ascii in normalized_ascii


class RedFlagDetector:
    """Scan free text for red-flag combinations."""

    def __init__(self, patterns_path: Path) -> None:
        self.patterns_path = Path(patterns_path)
        self.patterns: list[RedFlagPattern] = self._load(self.patterns_path)

    @staticmethod
    def _load(path: Path) -> list[RedFlagPattern]:
        with path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        raw_patterns = payload.get("patterns", [])
        if not isinstance(raw_patterns, list):
            raise ValueError(
                f"Expected 'patterns' list in {path}, got {type(raw_patterns)}"
            )
        patterns = [RedFlagPattern.model_validate(item) for item in raw_patterns]
        logger.info("Loaded %d red-flag patterns from %s", len(patterns), path)
        return patterns

    def scan(self, text: str) -> list[RedFlagPattern]:
        """Return every pattern whose AND-of-OR-groups condition fires on `text`."""
        if not text:
            return []
        normalized = _normalize(text)
        normalized_ascii = _strip_diacritics(normalized)
        hits: list[RedFlagPattern] = []
        for pattern in self.patterns:
            if all(
                any(
                    _keyword_in(kw, normalized, normalized_ascii) for kw in group
                )
                for group in pattern.keyword_groups
            ):
                hits.append(pattern)
        return hits
