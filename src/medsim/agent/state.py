"""LangGraph agent state."""

from __future__ import annotations

from typing import TypedDict

from medsim.schemas.conversation import ConversationStep, Message
from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import TriageDecision


class AgentState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes."""

    conversation_id: str
    messages: list[Message]
    last_user_message: str
    extracted_symptoms: SymptomExtraction | None
    current_question: str | None
    matched_rule_id: str | None
    decision: TriageDecision | None
    red_flags_detected: list[str]
    step: ConversationStep
    assistant_message: str
