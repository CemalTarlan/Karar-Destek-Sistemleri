"""LangGraph orchestration: wire nodes into a state machine."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from medsim.agent.nodes import AgentDependencies, make_nodes, needs_questions
from medsim.agent.state import AgentState
from medsim.schemas.conversation import ConversationStep


def build_graph(deps: AgentDependencies) -> Any:
    """Construct and compile the triage agent's LangGraph."""
    nodes = make_nodes(deps)
    graph: StateGraph[AgentState, None, AgentState, AgentState] = StateGraph(AgentState)

    for name, fn in nodes.items():
        graph.add_node(name, fn)  # type: ignore[call-overload]

    graph.set_entry_point("scope_filter")

    # Scope filter: if out-of-scope, jump straight to finalize.
    graph.add_conditional_edges(
        "scope_filter",
        _branch_after_scope,
        {"red_flag_check": "red_flag_check", "finalize": "finalize"},
    )

    # Red flag check: if a flag fired, the decision is set; jump to explanation.
    graph.add_conditional_edges(
        "red_flag_check",
        _branch_after_red_flag,
        {
            "extract_symptoms": "extract_symptoms",
            "compose_explanation": "compose_explanation",
        },
    )

    graph.add_edge("extract_symptoms", "assess_sufficiency")

    # Sufficiency: ask another question, or move to rule matching.
    graph.add_conditional_edges(
        "assess_sufficiency",
        _branch_after_sufficiency,
        {"ask_question": "ask_question", "match_rule": "match_rule"},
    )

    graph.add_edge("ask_question", "finalize")
    graph.add_edge("match_rule", "compose_explanation")
    graph.add_edge("compose_explanation", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def _branch_after_scope(state: AgentState) -> str:
    if state.get("step") == ConversationStep.DECIDED and state.get("decision") is None:
        # Out-of-scope refusal already populated assistant_message.
        return "finalize"
    return "red_flag_check"


def _branch_after_red_flag(state: AgentState) -> str:
    if state.get("decision") is not None:
        return "compose_explanation"
    return "extract_symptoms"


def _branch_after_sufficiency(state: AgentState) -> str:
    return "ask_question" if needs_questions(state) else "match_rule"
