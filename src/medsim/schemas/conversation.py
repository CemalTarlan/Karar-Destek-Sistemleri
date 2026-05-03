"""Conversation state schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import TriageDecision


class ConversationStep(str, Enum):
    """High-level state of an ongoing triage conversation."""

    INTAKE = "INTAKE"
    QUESTIONING = "QUESTIONING"
    DECIDED = "DECIDED"


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationState(BaseModel):
    conversation_id: str
    messages: list[Message] = Field(default_factory=list)
    extracted_symptoms: SymptomExtraction | None = None
    decision: TriageDecision | None = None
    step: ConversationStep = ConversationStep.INTAKE
    turn_count: int = 0


class AgentResponse(BaseModel):
    assistant_message: str
    state: ConversationState
    is_decided: bool
