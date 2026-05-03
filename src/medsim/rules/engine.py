"""Rule-based triage decision engine.

The rule engine — NOT the LLM — is the sole authority for triage colors.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import TriageColor

logger = logging.getLogger(__name__)

_COLOR_PRIORITY: dict[TriageColor, int] = {
    TriageColor.KIRMIZI: 0,
    TriageColor.SARI: 1,
    TriageColor.YESIL: 2,
}

_AGE_FILTER_RE = re.compile(r"^\s*(>=|<=|>|<|==|=)\s*(\d{1,3})\s*$")


class Rule(BaseModel):
    """A single triage rule loaded from YAML."""

    id: str = Field(..., min_length=1)
    color: TriageColor
    title: str = Field(..., min_length=1)
    trigger_symptoms: list[str] = Field(default_factory=list)
    required_combinations: list[list[str]] | None = None
    age_filter: str | None = None
    target_minutes: int = Field(..., ge=0)
    source_reference: str = ""

    @field_validator("age_filter")
    @classmethod
    def _validate_age_filter(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _AGE_FILTER_RE.match(v):
            raise ValueError(
                f"age_filter '{v}' is not in the form '<op><age>' (e.g., '>=35')"
            )
        return v


def _age_satisfies(filter_expr: str | None, patient_age: int | None) -> bool:
    """Return True if the patient's age satisfies the filter expression.

    A None filter always matches. A None patient age fails any non-None filter.
    """
    if filter_expr is None:
        return True
    if patient_age is None:
        return False
    match = _AGE_FILTER_RE.match(filter_expr)
    if match is None:
        return False
    op, value = match.group(1), int(match.group(2))
    if op in (">=",):
        return patient_age >= value
    if op == "<=":
        return patient_age <= value
    if op == ">":
        return patient_age > value
    if op == "<":
        return patient_age < value
    if op in ("==", "="):
        return patient_age == value
    return False


def _all_present(combo: list[str], symptom_set: set[str]) -> bool:
    return all(item in symptom_set for item in combo)


class RuleEngine:
    """Loads rules from YAML and matches them against extracted symptoms."""

    def __init__(self, rules_path: Path) -> None:
        self.rules_path = Path(rules_path)
        self.rules: list[Rule] = self._load(self.rules_path)
        self._by_id: dict[str, Rule] = {r.id: r for r in self.rules}

    @staticmethod
    def _load(path: Path) -> list[Rule]:
        with path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        raw_rules = payload.get("rules", [])
        if not isinstance(raw_rules, list):
            raise ValueError(f"Expected 'rules' list in {path}, got {type(raw_rules)}")
        rules = [Rule.model_validate(item) for item in raw_rules]
        logger.info("Loaded %d triage rules from %s", len(rules), path)
        return rules

    def get_rule_by_id(self, rule_id: str) -> Rule:
        try:
            return self._by_id[rule_id]
        except KeyError as exc:
            raise KeyError(f"No rule with id={rule_id!r}") from exc

    def match(self, symptoms: SymptomExtraction) -> Rule | None:
        """Return the most specific matching rule, or None.

        Priority order:
          1. Color (KIRMIZI > SARI > YESIL).
          2. Number of `trigger_symptoms` actually matched (more = more specific).
          3. Whether `required_combinations` was used (combination match wins
             over a single-keyword match).
        """
        symptom_set = self._symptom_set(symptoms)

        candidates: list[tuple[Rule, int, int]] = []
        for rule in self.rules:
            if not _age_satisfies(rule.age_filter, symptoms.patient_age):
                continue

            matched_triggers = sum(1 for s in rule.trigger_symptoms if s in symptom_set)
            combo_matched = 0
            if rule.required_combinations:
                # At least one combination must be fully present.
                if not any(
                    _all_present(combo, symptom_set) for combo in rule.required_combinations
                ):
                    continue
                combo_matched = 1
            elif matched_triggers == 0:
                # No combination requirement and no trigger hit → not a match.
                continue

            candidates.append((rule, matched_triggers, combo_matched))

        if not candidates:
            return None

        # Lower priority value = higher precedence. Tie-breakers prefer
        # higher trigger-match count and combination-driven matches.
        candidates.sort(
            key=lambda item: (
                _COLOR_PRIORITY[item[0].color],
                -item[1],
                -item[2],
            )
        )
        return candidates[0][0]

    @staticmethod
    def _symptom_set(symptoms: SymptomExtraction) -> set[str]:
        items: set[str] = set()
        if symptoms.chief_complaint:
            items.add(symptoms.chief_complaint.strip().lower())
        for s in symptoms.associated_symptoms:
            items.add(s.strip().lower())
        return items
