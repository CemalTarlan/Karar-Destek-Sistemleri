"""Output validator — sanity-checks a finalized triage decision."""

from __future__ import annotations

from dataclasses import dataclass, field

from medsim.rules.engine import Rule
from medsim.schemas.triage import TriageDecision


@dataclass
class ValidationResult:
    """Outcome of validating a `TriageDecision`."""

    is_valid: bool
    issues: list[str] = field(default_factory=list)


class OutputValidator:
    """Light structural validator over `TriageDecision` instances.

    Current checks:
      - If `triggered_rule_id` is set, it must match the rule passed in.
      - The decision color must match the rule's color (when a rule exists).
      - `recommendation` and `rationale` must be non-empty.
    Semantic similarity between rationale and rule is intentionally
    deferred — see TODO below.
    """

    def validate(
        self,
        decision: TriageDecision,
        rule: Rule | None,
    ) -> ValidationResult:
        issues: list[str] = []

        if not decision.rationale.strip():
            issues.append("rationale boş.")
        if not decision.recommendation.strip():
            issues.append("recommendation boş.")

        if rule is not None:
            if (
                decision.triggered_rule_id is not None
                and decision.triggered_rule_id != rule.id
            ):
                issues.append(
                    f"triggered_rule_id={decision.triggered_rule_id!r} "
                    f"ile sağlanan kural {rule.id!r} eşleşmiyor."
                )
            if decision.color != rule.color:
                issues.append(
                    f"Karar rengi {decision.color.value} ile kural rengi "
                    f"{rule.color.value} uyumsuz."
                )

        # TODO: gerçek tıbbi referansla genişletilecek — rationale ile kural
        # metni arasında semantik benzerlik kontrolü (örn. embedding tabanlı).

        return ValidationResult(is_valid=not issues, issues=issues)
