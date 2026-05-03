"""HTTP routes for MedSim Triage."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from medsim import __version__
from medsim.api.dependencies import (
    get_compiled_graph,
    get_conversation_store,
    get_llm_client,
)
from medsim.llm.client import LMStudioClient
from medsim.schemas.conversation import (
    AgentResponse,
    ConversationState,
    ConversationStep,
    Message,
)
from medsim.schemas.triage import DEFAULT_DISCLAIMER_TR

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    disclaimer: str = DEFAULT_DISCLAIMER_TR


class LMStudioHealthResponse(BaseModel):
    reachable: bool
    base_url: str
    disclaimer: str = DEFAULT_DISCLAIMER_TR


class StartTriageResponse(BaseModel):
    conversation_id: str
    state: ConversationState
    message: str = Field(
        default=(
            "Merhaba. Şikayetinizi mümkün olduğunca açık biçimde anlatın. "
            "Bu bir EĞİTİM ve SİMÜLASYON sistemidir; gerçek tıbbi tavsiye vermez."
        )
    )
    disclaimer: str = DEFAULT_DISCLAIMER_TR


class TurnRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=4000)


class TurnResponse(BaseModel):
    response: AgentResponse
    disclaimer: str = DEFAULT_DISCLAIMER_TR


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.get("/lm-studio/health", response_model=LMStudioHealthResponse)
def lm_studio_health(
    llm: LMStudioClient = Depends(get_llm_client),
) -> LMStudioHealthResponse:
    return LMStudioHealthResponse(
        reachable=llm.health_check(),
        base_url=llm.base_url,
    )


@router.post("/triage/start", response_model=StartTriageResponse)
def start_triage(
    store: dict[str, Any] = Depends(get_conversation_store),
) -> StartTriageResponse:
    conversation_id = str(uuid.uuid4())
    state = ConversationState(conversation_id=conversation_id)
    store[conversation_id] = state
    return StartTriageResponse(conversation_id=conversation_id, state=state)


@router.post("/triage/turn", response_model=TurnResponse)
def take_turn(
    body: TurnRequest,
    store: dict[str, Any] = Depends(get_conversation_store),
    graph: Any = Depends(get_compiled_graph),
) -> TurnResponse:
    state: ConversationState | None = store.get(body.conversation_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Konuşma bulunamadı. Lütfen önce /triage/start çağırın.",
        )
    if state.step == ConversationStep.DECIDED:
        raise HTTPException(
            status_code=409,
            detail="Bu konuşma için triyaj kararı zaten verildi. Yeni bir konuşma başlatın.",
        )

    user_msg = Message(role="user", content=body.message)
    state.messages.append(user_msg)
    state.turn_count += 1

    agent_state = {
        "conversation_id": state.conversation_id,
        "messages": state.messages,
        "last_user_message": body.message,
        "extracted_symptoms": state.extracted_symptoms,
        "current_question": None,
        "matched_rule_id": None,
        "decision": state.decision,
        "red_flags_detected": [],
        "step": state.step,
        "assistant_message": "",
    }

    final_state = graph.invoke(agent_state)

    assistant_text: str = final_state.get("assistant_message") or ""
    if not assistant_text:
        assistant_text = (
            "Bir yanıt üretemedim. Lütfen şikayetinizi farklı sözcüklerle tekrar anlatır mısınız?"
        )

    state.messages.append(Message(role="assistant", content=assistant_text))
    state.extracted_symptoms = final_state.get("extracted_symptoms")
    state.decision = final_state.get("decision")
    state.step = final_state.get("step", state.step)
    store[state.conversation_id] = state

    is_decided = state.step == ConversationStep.DECIDED
    return TurnResponse(
        response=AgentResponse(
            assistant_message=assistant_text,
            state=state,
            is_decided=is_decided,
        )
    )
