"""Triage decision schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

DEFAULT_DISCLAIMER_TR = (
    "Bu sistem yalnızca eğitim ve simülasyon amaçlıdır. Gerçek bir tıbbi "
    "değerlendirme, tanı veya tedavi önerisi sağlamaz. Acil bir durumda "
    "lütfen 112'yi arayın veya en yakın acil servise başvurun."
)


class TriageColor(str, Enum):
    """3-color triage categorization (Türkiye Sağlık Bakanlığı reference)."""

    KIRMIZI = "KIRMIZI"
    SARI = "SARI"
    YESIL = "YESIL"


class TriageDecision(BaseModel):
    """Final triage outcome produced by the rule engine (NOT the LLM)."""

    color: TriageColor
    esi_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Emergency Severity Index 1 (most acute) to 5 (least acute).",
    )
    rationale: str = Field(..., min_length=1)
    triggered_rule_id: str | None = None
    recommendation: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    red_flags: list[str] = Field(default_factory=list)
    disclaimer: str = Field(default=DEFAULT_DISCLAIMER_TR)

    @field_validator("esi_level")
    @classmethod
    def _esi_in_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("esi_level must be between 1 and 5")
        return v
