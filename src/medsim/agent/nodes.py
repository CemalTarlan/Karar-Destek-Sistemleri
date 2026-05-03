"""LangGraph node functions for the triage agent."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from medsim.agent.state import AgentState
from medsim.guardrails.scope_filter import ScopeFilter
from medsim.llm.client import LMStudioClient, LMStudioConnectionError
from medsim.llm.prompts import (
    build_explanation_messages,
    build_extraction_messages,
    build_question_messages,
)
from medsim.rules.engine import Rule, RuleEngine
from medsim.rules.red_flags import RedFlagDetector
from medsim.schemas.conversation import ConversationStep
from medsim.schemas.symptoms import SymptomExtraction
from medsim.schemas.triage import DEFAULT_DISCLAIMER_TR, TriageColor, TriageDecision

logger = logging.getLogger(__name__)


_RED_FLAG_RECOMMENDATION_TR = (
    "Lütfen ŞİMDİ 112'yi arayın veya en yakın acil servise başvurun. "
    "Bu durum acil değerlendirme gerektirebilir."
)
_REQUIRED_FIELDS = ("location", "duration_hours", "severity_0_10")
_MAX_QUESTION_TURNS = 4


@dataclass
class AgentDependencies:
    """Bundle of services every node depends on."""

    llm: LMStudioClient
    rule_engine: RuleEngine
    red_flag_detector: RedFlagDetector
    scope_filter: ScopeFilter


NodeFn = Callable[[AgentState], AgentState]


def make_nodes(deps: AgentDependencies) -> dict[str, NodeFn]:
    """Return a dict of node_name -> node_callable, all closed over `deps`."""

    def red_flag_check_node(state: AgentState) -> AgentState:
        text = state.get("last_user_message", "") or ""
        hits = deps.red_flag_detector.scan(text)
        flag_descriptions = [h.description for h in hits]
        state["red_flags_detected"] = flag_descriptions
        if hits:
            logger.info("Red flags fired: %s", [h.id for h in hits])
            state["decision"] = TriageDecision(
                color=TriageColor.KIRMIZI,
                esi_level=1,
                rationale=(
                    "Mesajınızda acil değerlendirme gerektirebilecek kırmızı bayrak "
                    "kalıpları tespit edildi: " + "; ".join(flag_descriptions)
                ),
                triggered_rule_id=None,
                recommendation=_RED_FLAG_RECOMMENDATION_TR,
                confidence=0.9,
                red_flags=flag_descriptions,
                disclaimer=DEFAULT_DISCLAIMER_TR,
            )
            state["step"] = ConversationStep.DECIDED
        return state

    def scope_filter_node(state: AgentState) -> AgentState:
        is_oos, message = deps.scope_filter.is_out_of_scope(
            state.get("last_user_message", "") or ""
        )
        if is_oos and message:
            state["assistant_message"] = message
            # Mark as decided with a "no decision" sentinel so the graph exits.
            state["step"] = ConversationStep.DECIDED
            state["decision"] = None  # explicit
        return state

    def extract_symptoms_node(state: AgentState) -> AgentState:
        prior = _summarize_prior_symptoms(state.get("extracted_symptoms"))
        text = state.get("last_user_message", "") or ""
        messages = build_extraction_messages(text, prior_context=prior)
        try:
            extracted = deps.llm.complete_structured(messages, SymptomExtraction)
        except LMStudioConnectionError:
            raise
        state["extracted_symptoms"] = _merge_symptoms(state.get("extracted_symptoms"), extracted)
        state["step"] = ConversationStep.QUESTIONING
        return state

    def assess_sufficiency_node(state: AgentState) -> AgentState:
        symptoms = state.get("extracted_symptoms")
        if symptoms is None:
            state["current_question"] = None
            return state
        missing = _compute_missing(symptoms)
        symptoms.missing_info = missing
        state["extracted_symptoms"] = symptoms
        return state

    def ask_question_node(state: AgentState) -> AgentState:
        symptoms = state.get("extracted_symptoms")
        if symptoms is None:
            return state
        summary = _format_symptom_summary(symptoms)
        messages = build_question_messages(summary, symptoms.missing_info)
        question = deps.llm.complete_text(messages, temperature=0.3, max_tokens=120)
        state["current_question"] = question
        state["assistant_message"] = question
        state["step"] = ConversationStep.QUESTIONING
        return state

    def match_rule_node(state: AgentState) -> AgentState:
        symptoms = state.get("extracted_symptoms")
        if symptoms is None:
            return state
        rule = deps.rule_engine.match(symptoms)
        if rule is None:
            state["matched_rule_id"] = None
            state["decision"] = TriageDecision(
                color=TriageColor.YESIL,
                esi_level=5,
                rationale=(
                    "Verilen bilgilere göre acil bir kalıp tespit edilemedi. "
                    "Şikayet hafif kategoride değerlendirildi."
                ),
                triggered_rule_id=None,
                recommendation=(
                    "Şikayet sürerse veya kötüleşirse bir sağlık kuruluşuna başvurun. "
                    "Acil bir durum ortaya çıkarsa 112'yi arayın."
                ),
                confidence=0.4,
                red_flags=state.get("red_flags_detected") or [],
            )
        else:
            state["matched_rule_id"] = rule.id
            state["decision"] = _decision_from_rule(rule, state.get("red_flags_detected") or [])
        state["step"] = ConversationStep.DECIDED
        return state

    def compose_explanation_node(state: AgentState) -> AgentState:
        decision = state.get("decision")
        if decision is None:
            return state
        rule_id = state.get("matched_rule_id")
        rule_summary: str | None = None
        if rule_id is not None:
            try:
                rule = deps.rule_engine.get_rule_by_id(rule_id)
                rule_summary = (
                    f"Kural ID: {rule.id}\nBaşlık: {rule.title}\n"
                    f"Hedef değerlendirme süresi: {rule.target_minutes} dakika.\n"
                    f"Referans: {rule.source_reference}"
                )
            except KeyError:
                rule_summary = None
        decision_summary = (
            f"Renk: {decision.color.value}\nESI: {decision.esi_level}\n"
            f"Gerekçe: {decision.rationale}\nÖneri: {decision.recommendation}"
        )
        try:
            explanation = deps.llm.complete_text(
                build_explanation_messages(decision_summary, rule_summary),
                temperature=0.2,
                max_tokens=300,
            )
        except LMStudioConnectionError as exc:
            logger.warning("Açıklama üretilemedi (LLM hatası): %s", exc)
            explanation = (
                f"Triyaj sonucu: {decision.color.value}. {decision.recommendation}"
            )
        state["assistant_message"] = _compose_final_message(decision, explanation)
        return state

    def finalize_node(state: AgentState) -> AgentState:
        # No-op terminal node; preserved for graph clarity & future hooks.
        return state

    return {
        "red_flag_check": red_flag_check_node,
        "scope_filter": scope_filter_node,
        "extract_symptoms": extract_symptoms_node,
        "assess_sufficiency": assess_sufficiency_node,
        "ask_question": ask_question_node,
        "match_rule": match_rule_node,
        "compose_explanation": compose_explanation_node,
        "finalize": finalize_node,
    }


def _summarize_prior_symptoms(prior: SymptomExtraction | None) -> str | None:
    if prior is None:
        return None
    return _format_symptom_summary(prior)


def _format_symptom_summary(s: SymptomExtraction) -> str:
    lines = [f"Ana şikayet: {s.chief_complaint}"]
    if s.location:
        lines.append(f"Bölge: {s.location}")
    if s.duration_hours is not None:
        lines.append(f"Süre (saat): {s.duration_hours}")
    if s.severity_0_10 is not None:
        lines.append(f"Şiddet (0-10): {s.severity_0_10}")
    if s.associated_symptoms:
        lines.append("Eşlik eden: " + ", ".join(s.associated_symptoms))
    if s.patient_age is not None:
        lines.append(f"Yaş: {s.patient_age}")
    if s.is_pregnant is not None:
        lines.append(f"Gebelik: {'evet' if s.is_pregnant else 'hayır'}")
    return "\n".join(lines)


def _compute_missing(s: SymptomExtraction) -> list[str]:
    missing: list[str] = []
    if not s.location:
        missing.append("location")
    if s.duration_hours is None:
        missing.append("duration_hours")
    if s.severity_0_10 is None:
        missing.append("severity_0_10")
    return missing


def _merge_symptoms(
    existing: SymptomExtraction | None,
    incoming: SymptomExtraction,
) -> SymptomExtraction:
    """Merge incoming structured extraction over existing state.

    Non-null incoming fields win. Lists are unioned.
    """
    if existing is None:
        return incoming
    data = existing.model_dump()
    incoming_data = incoming.model_dump()
    for key, value in incoming_data.items():
        if key in {"associated_symptoms", "missing_info"}:
            merged = list({*data.get(key, []), *(value or [])})
            data[key] = merged
        elif value not in (None, "", []):
            data[key] = value
    return SymptomExtraction.model_validate(data)


def _decision_from_rule(rule: Rule, red_flags: list[str]) -> TriageDecision:
    color_to_esi = {
        TriageColor.KIRMIZI: 1,
        TriageColor.SARI: 3,
        TriageColor.YESIL: 5,
    }
    color_to_recommendation = {
        TriageColor.KIRMIZI: "Lütfen 112'yi arayın veya en yakın acil servise başvurun.",
        TriageColor.SARI: (
            "Bugün içinde bir sağlık kuruluşuna başvurmanız önerilir. "
            "Durum kötüleşirse 112'yi arayın."
        ),
        TriageColor.YESIL: (
            "Şikayet sürerse veya kötüleşirse bir sağlık kuruluşuna başvurun. "
            "Acil bir durum ortaya çıkarsa 112'yi arayın."
        ),
    }
    confidence = {
        TriageColor.KIRMIZI: 0.85,
        TriageColor.SARI: 0.7,
        TriageColor.YESIL: 0.6,
    }[rule.color]
    return TriageDecision(
        color=rule.color,
        esi_level=color_to_esi[rule.color],
        rationale=(
            f"Kural {rule.id} ({rule.title}) eşleşti. "
            f"Hedef değerlendirme süresi: {rule.target_minutes} dakika."
        ),
        triggered_rule_id=rule.id,
        recommendation=color_to_recommendation[rule.color],
        confidence=confidence,
        red_flags=red_flags,
    )


def _compose_final_message(decision: TriageDecision, explanation: str) -> str:
    header = {
        TriageColor.KIRMIZI: "🟥 KIRMIZI — Acil değerlendirme gerekebilir",
        TriageColor.SARI: "🟨 SARI — Hızlı değerlendirme önerilir",
        TriageColor.YESIL: "🟩 YEŞİL — Hafif/bekleyebilir",
    }[decision.color]
    parts = [header, "", explanation.strip()]
    if decision.color == TriageColor.KIRMIZI:
        parts.append("\n📞 Lütfen ŞİMDİ 112'yi arayın.")
    parts.append("\n— " + decision.disclaimer)
    return "\n".join(parts)


def needs_questions(state: AgentState, max_turns: int = _MAX_QUESTION_TURNS) -> bool:
    """Conditional-edge predicate: should we ask a follow-up?"""
    symptoms = state.get("extracted_symptoms")
    if symptoms is None:
        return False
    if not symptoms.missing_info:
        return False
    turn_count = sum(1 for m in state.get("messages", []) if m.role == "assistant")
    return turn_count < max_turns
