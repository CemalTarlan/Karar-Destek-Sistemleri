"""Rule-based triage engine and red-flag detection."""

from medsim.rules.engine import Rule, RuleEngine
from medsim.rules.red_flags import RedFlagDetector, RedFlagPattern

__all__ = ["RedFlagDetector", "RedFlagPattern", "Rule", "RuleEngine"]
