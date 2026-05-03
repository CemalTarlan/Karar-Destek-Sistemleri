"""FastAPI dependency providers (singletons constructed lazily)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from medsim.agent.graph import build_graph
from medsim.agent.nodes import AgentDependencies
from medsim.config import Settings, get_settings
from medsim.guardrails.scope_filter import ScopeFilter
from medsim.llm.client import LMStudioClient
from medsim.rules.engine import RuleEngine
from medsim.rules.red_flags import RedFlagDetector

# In-memory conversation store. Keyed by conversation_id.
# TODO: production için kalıcı store (örn. Redis veya Postgres) eklenecek.
_CONVERSATIONS: dict[str, Any] = {}


def get_conversation_store() -> dict[str, Any]:
    return _CONVERSATIONS


@lru_cache(maxsize=1)
def get_llm_client() -> LMStudioClient:
    settings = get_settings()
    return LMStudioClient(
        base_url=settings.lm_studio_base_url,
        model_name=settings.lm_studio_model,
        timeout=settings.lm_studio_timeout,
    )


@lru_cache(maxsize=1)
def get_rule_engine() -> RuleEngine:
    return RuleEngine(rules_path=get_settings().rules_path)


@lru_cache(maxsize=1)
def get_red_flag_detector() -> RedFlagDetector:
    return RedFlagDetector(patterns_path=get_settings().red_flags_path)


@lru_cache(maxsize=1)
def get_scope_filter() -> ScopeFilter:
    return ScopeFilter()


@lru_cache(maxsize=1)
def get_agent_dependencies() -> AgentDependencies:
    return AgentDependencies(
        llm=get_llm_client(),
        rule_engine=get_rule_engine(),
        red_flag_detector=get_red_flag_detector(),
        scope_filter=get_scope_filter(),
    )


@lru_cache(maxsize=1)
def get_compiled_graph() -> Any:
    return build_graph(get_agent_dependencies())


def get_app_settings() -> Settings:
    return get_settings()


def reset_dependency_caches() -> None:
    """Test/maintenance helper: clear all `lru_cache` singletons.

    Tolerates the case where a name has been monkey-patched to a plain
    function (e.g. by a pytest fixture); such names simply have no cache
    to clear and are skipped.
    """
    for fn in (
        get_llm_client,
        get_rule_engine,
        get_red_flag_detector,
        get_scope_filter,
        get_agent_dependencies,
        get_compiled_graph,
    ):
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()
    _CONVERSATIONS.clear()
