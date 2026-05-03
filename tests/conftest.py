"""Shared pytest fixtures.

Notably, this conftest mocks the LM Studio client so tests can run
*without* a live LM Studio server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from medsim.api import dependencies as deps_module
from medsim.api.main import create_app
from medsim.config import get_settings
from medsim.llm.client import LMStudioClient
from medsim.schemas.symptoms import SymptomExtraction


@pytest.fixture
def rules_path() -> Path:
    return get_settings().rules_path


@pytest.fixture
def red_flags_path() -> Path:
    return get_settings().red_flags_path


class _FakeLMClient:
    """Drop-in replacement for `LMStudioClient` used in unit tests.

    `complete_structured` always returns a minimal valid `SymptomExtraction`.
    `complete_text` returns a fixed Turkish string.
    """

    base_url = "http://localhost:1234/v1"
    model_name = "fake-model"

    def health_check(self) -> bool:
        return True

    def complete_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        return "Test yanıtı: lütfen şikayetinizi biraz daha açar mısınız?"

    def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Any:
        if schema is SymptomExtraction:
            return SymptomExtraction(
                chief_complaint="bogaz_agrisi",
                location=None,
                duration_hours=None,
                severity_0_10=None,
                associated_symptoms=[],
                missing_info=["location", "duration_hours", "severity_0_10"],
            )
        return schema()  # pragma: no cover


@pytest.fixture
def fake_llm() -> _FakeLMClient:
    return _FakeLMClient()


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, fake_llm: _FakeLMClient) -> Any:
    """FastAPI app with the LLM dependency replaced by `_FakeLMClient`."""
    deps_module.reset_dependency_caches()

    def _fake_llm_factory() -> LMStudioClient:
        return fake_llm  # type: ignore[return-value]

    monkeypatch.setattr(deps_module, "get_llm_client", _fake_llm_factory)
    application = create_app()
    application.dependency_overrides[deps_module.get_llm_client] = _fake_llm_factory
    yield application
    application.dependency_overrides.clear()
    deps_module.reset_dependency_caches()


@pytest.fixture
def mock_lmstudio_client() -> MagicMock:
    """Generic MagicMock for callers wanting full control."""
    return MagicMock(spec=LMStudioClient)
