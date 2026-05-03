"""Scope filter — refuses out-of-scope user requests early.

The triage agent must NEVER answer requests for: medication doses,
definitive diagnoses, prescriptions, legal advice, or financial advice.
This filter is keyword/regex-based and runs before the LLM is invoked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Each entry: (category_id, refusal_message_TR, [pattern_strings...])
_OUT_OF_SCOPE_PATTERNS: list[tuple[str, str, list[str]]] = [
    (
        "medication_dose",
        "Üzgünüm, ilaç adı, dozaj veya tedavi önerisi veremem. Bu bilgiler "
        "için lütfen bir hekime veya eczacıya danışın.",
        [
            r"\b(ka[çc]\s*mg)\b",
            r"\b(do[zs]aj|do[zs]u)\b",
            r"\b(ka[çc]\s*tablet|ka[çc]\s*hap)\b",
            r"\b(ila[çc]\s+([oö]ner|tavsi|yaz))",
            r"\b(re[çc]ete)\b",
            r"\b(antibiyotik\s+(yaz|[oö]ner))",
        ],
    ),
    (
        "definitive_diagnosis",
        "Bu sistem kesin tanı koymaz; yalnızca aciliyet düzeyini değerlendirmeye "
        "yönelik eğitim amaçlı bir simülasyondur. Kesin tanı için bir hekime başvurun.",
        [
            r"\b(kesin\s*tan[ıi])\b",
            r"\b(bende\s+(ne|hangi)\s+hastal[ıi]k)\b",
            r"\b(hangi\s+hastal[ıi]k)\b",
            r"\b(kanser\s*m[ıi]y[ıi]m)\b",
        ],
    ),
    (
        "legal_advice",
        "Hukuki tavsiye veremem. Lütfen bir avukata danışın.",
        [
            r"\b(hukuki|yasal)\s+(tavsi|dan[ıi][şs]|g[oö]r[üu][şs])",
            r"\b(dava\s+(a[çc]|edebilir))",
        ],
    ),
    (
        "financial_advice",
        "Finansal tavsiye veremem. Lütfen yetkili bir mali müşavire danışın.",
        [
            r"\b(yat[ıi]r[ıi]m\s+tavsi)",
            r"\b(hisse\s+(al|sat))",
            r"\b(kripto)\b",
        ],
    ),
]


@dataclass(frozen=True)
class _CompiledRule:
    category: str
    message: str
    regex: re.Pattern[str]


class ScopeFilter:
    """Reject queries that fall outside the triage agent's competence."""

    def __init__(self) -> None:
        self._rules: list[_CompiledRule] = [
            _CompiledRule(
                category=cat,
                message=msg,
                regex=re.compile("|".join(patterns), flags=re.IGNORECASE),
            )
            for cat, msg, patterns in _OUT_OF_SCOPE_PATTERNS
        ]

    def is_out_of_scope(self, text: str) -> tuple[bool, str | None]:
        """Return (True, refusal_message) if `text` is out of scope, else (False, None)."""
        if not text or not text.strip():
            return False, None
        for rule in self._rules:
            if rule.regex.search(text):
                return True, rule.message
        return False, None
