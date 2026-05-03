"""Symptom extraction schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SymptomExtraction(BaseModel):
    """Structured symptom data extracted from a free-text user message."""

    chief_complaint: str = Field(
        ...,
        min_length=1,
        description="Primary complaint stated by the user (Turkish).",
    )
    location: str | None = Field(
        default=None,
        description="Anatomical location of the complaint, if any.",
    )
    duration_hours: float | None = Field(
        default=None,
        ge=0.0,
        description="How long the symptom has lasted, in hours.",
    )
    severity_0_10: int | None = Field(
        default=None,
        ge=0,
        le=10,
        description="Patient-reported severity on a 0-10 scale.",
    )
    associated_symptoms: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(
        default_factory=list,
        description="Important fields the agent still needs to ask about.",
    )
    patient_age: int | None = Field(default=None, ge=0, le=130)
    is_pregnant: bool | None = None

    @field_validator("chief_complaint")
    @classmethod
    def _strip_complaint(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("chief_complaint cannot be empty")
        return v
