"""Schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import DEFAULT_DISCLAIMER_TR, TriageColor, TriageDecision


def test_triage_color_enum_values() -> None:
    assert TriageColor("KIRMIZI") is TriageColor.KIRMIZI
    assert TriageColor("SARI") is TriageColor.SARI
    assert TriageColor("YESIL") is TriageColor.YESIL
    with pytest.raises(ValueError):
        TriageColor("RED")


def test_triage_decision_valid() -> None:
    decision = TriageDecision(
        color=TriageColor.SARI,
        esi_level=3,
        rationale="Test gerekçesi",
        triggered_rule_id="TR-YEL-01",
        recommendation="Bugün başvurun.",
        confidence=0.7,
        red_flags=[],
    )
    assert decision.color is TriageColor.SARI
    assert decision.esi_level == 3
    assert decision.disclaimer == DEFAULT_DISCLAIMER_TR


@pytest.mark.parametrize("bad_esi", [0, 6, -1, 100])
def test_triage_decision_rejects_invalid_esi(bad_esi: int) -> None:
    with pytest.raises(ValidationError):
        TriageDecision(
            color=TriageColor.YESIL,
            esi_level=bad_esi,
            rationale="x",
            recommendation="y",
            confidence=0.5,
        )


@pytest.mark.parametrize("bad_conf", [-0.1, 1.1, 2.0])
def test_triage_decision_rejects_invalid_confidence(bad_conf: float) -> None:
    with pytest.raises(ValidationError):
        TriageDecision(
            color=TriageColor.YESIL,
            esi_level=5,
            rationale="x",
            recommendation="y",
            confidence=bad_conf,
        )


def test_symptom_extraction_minimal() -> None:
    s = SymptomExtraction(chief_complaint="bas_agrisi")
    assert s.chief_complaint == "bas_agrisi"
    assert s.associated_symptoms == []
    assert s.missing_info == []
    assert s.location is None


def test_symptom_extraction_strips_chief_complaint() -> None:
    s = SymptomExtraction(chief_complaint="   karin_agrisi   ")
    assert s.chief_complaint == "karin_agrisi"


def test_symptom_extraction_rejects_empty_chief_complaint() -> None:
    with pytest.raises(ValidationError):
        SymptomExtraction(chief_complaint="   ")


@pytest.mark.parametrize("severity", [-1, 11, 100])
def test_symptom_extraction_rejects_severity_out_of_range(severity: int) -> None:
    with pytest.raises(ValidationError):
        SymptomExtraction(chief_complaint="x", severity_0_10=severity)


def test_symptom_extraction_age_bounds() -> None:
    s = SymptomExtraction(chief_complaint="x", patient_age=65)
    assert s.patient_age == 65
    with pytest.raises(ValidationError):
        SymptomExtraction(chief_complaint="x", patient_age=131)
