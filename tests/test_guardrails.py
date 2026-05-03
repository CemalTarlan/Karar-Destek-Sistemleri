"""Guardrails tests."""

from __future__ import annotations

from medsim.guardrails.output_validator import OutputValidator
from medsim.guardrails.scope_filter import ScopeFilter
from medsim.rules.engine import Rule
from medsim.schemas.triage import TriageColor, TriageDecision


def test_scope_filter_passes_normal_complaint() -> None:
    sf = ScopeFilter()
    is_oos, msg = sf.is_out_of_scope("Karnım ağrıyor, dün akşamdan beri.")
    assert is_oos is False
    assert msg is None


def test_scope_filter_blocks_dose_question() -> None:
    sf = ScopeFilter()
    is_oos, msg = sf.is_out_of_scope("Bana parol kaç mg vereyim söyler misin?")
    assert is_oos is True
    assert msg is not None
    assert "ilaç" in msg.lower() or "doz" in msg.lower()


def test_scope_filter_blocks_diagnosis_request() -> None:
    sf = ScopeFilter()
    is_oos, _ = sf.is_out_of_scope("Bende kesin tanı koy lütfen.")
    assert is_oos is True


def test_scope_filter_blocks_legal_advice() -> None:
    sf = ScopeFilter()
    is_oos, msg = sf.is_out_of_scope("Hastaneye karşı dava açabilir miyim?")
    assert is_oos is True
    assert msg is not None


def test_output_validator_accepts_consistent_decision() -> None:
    rule = Rule(
        id="TR-YEL-01",
        color=TriageColor.SARI,
        title="x",
        trigger_symptoms=["karin_agrisi"],
        target_minutes=60,
    )
    decision = TriageDecision(
        color=TriageColor.SARI,
        esi_level=3,
        rationale="ok",
        triggered_rule_id="TR-YEL-01",
        recommendation="bugün başvurun",
        confidence=0.7,
    )
    result = OutputValidator().validate(decision, rule)
    assert result.is_valid is True
    assert result.issues == []


def test_output_validator_flags_color_mismatch() -> None:
    rule = Rule(
        id="TR-YEL-01",
        color=TriageColor.SARI,
        title="x",
        trigger_symptoms=["karin_agrisi"],
        target_minutes=60,
    )
    decision = TriageDecision(
        color=TriageColor.YESIL,  # WRONG: should match rule.color
        esi_level=5,
        rationale="ok",
        triggered_rule_id="TR-YEL-01",
        recommendation="öneri",
        confidence=0.7,
    )
    result = OutputValidator().validate(decision, rule)
    assert result.is_valid is False
    assert any("renk" in issue.lower() or "uyumsuz" in issue.lower() for issue in result.issues)


def test_output_validator_flags_id_mismatch() -> None:
    rule = Rule(
        id="TR-YEL-01",
        color=TriageColor.SARI,
        title="x",
        trigger_symptoms=["karin_agrisi"],
        target_minutes=60,
    )
    decision = TriageDecision(
        color=TriageColor.SARI,
        esi_level=3,
        rationale="ok",
        triggered_rule_id="TR-RED-99",  # WRONG: doesn't match rule.id
        recommendation="öneri",
        confidence=0.7,
    )
    result = OutputValidator().validate(decision, rule)
    assert result.is_valid is False
