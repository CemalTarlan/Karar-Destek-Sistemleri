"""Rule-engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from medsim.rules.engine import RuleEngine
from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import TriageColor


def test_rule_engine_loads_yaml(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    assert len(engine.rules) >= 5
    ids = {r.id for r in engine.rules}
    assert "TR-RED-01" in ids
    assert "TR-GRN-01" in ids


def test_rule_engine_lookup_by_id(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    rule = engine.get_rule_by_id("TR-RED-01")
    assert rule.color is TriageColor.KIRMIZI
    with pytest.raises(KeyError):
        engine.get_rule_by_id("DOES-NOT-EXIST")


def test_rule_engine_matches_green_for_simple_complaint(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    s = SymptomExtraction(
        chief_complaint="bogaz_agrisi",
        associated_symptoms=[],
    )
    rule = engine.match(s)
    assert rule is not None
    assert rule.color is TriageColor.YESIL


def test_rule_engine_red_takes_priority_over_green(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    s = SymptomExtraction(
        chief_complaint="gogus_agrisi",
        associated_symptoms=["nefes_darligi", "bogaz_agrisi"],
        patient_age=50,
    )
    rule = engine.match(s)
    assert rule is not None
    assert rule.color is TriageColor.KIRMIZI
    assert rule.id.startswith("TR-RED-")


def test_rule_engine_age_filter_blocks_match(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    # TR-RED-01 has age_filter ">=35"
    young = SymptomExtraction(
        chief_complaint="gogus_agrisi",
        associated_symptoms=["nefes_darligi"],
        patient_age=20,
    )
    rule = engine.match(young)
    assert rule is None or rule.id != "TR-RED-01"


def test_rule_engine_returns_none_for_unmatched_symptoms(rules_path: Path) -> None:
    engine = RuleEngine(rules_path=rules_path)
    s = SymptomExtraction(chief_complaint="tirnak_kirilmasi")
    assert engine.match(s) is None
