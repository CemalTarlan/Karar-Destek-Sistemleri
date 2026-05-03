"""LM Studio client with structured-output support.

LM Studio exposes an OpenAI-compatible HTTP API. This module wraps it for
the triage agent, enforcing Pydantic validation on every structured call.
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar, cast

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_CONNECTION_HINT_TR = (
    "LM Studio sunucusu çalışıyor mu? "
    "(LM Studio'yu açın → Developer sekmesi → Start Server)"
)


class LMStudioConnectionError(RuntimeError):
    """Raised when the LM Studio server is unreachable or returns an error."""


class LMStudioClient:
    """Thin wrapper around the OpenAI SDK pointed at a local LM Studio server."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        model_name: str = "local-model",
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout,
        )

    def health_check(self) -> bool:
        """Return True if the LM Studio `/models` endpoint responds."""
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError as exc:
            logger.warning("LM Studio health check failed: %s", exc)
            return False

    def complete_text(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> str:
        """Plain text completion."""
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=cast(Any, messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except (APIConnectionError, APITimeoutError) as exc:
            raise LMStudioConnectionError(
                f"LM Studio bağlantı hatası: {exc}. {_CONNECTION_HINT_TR}"
            ) from exc
        except APIError as exc:
            raise LMStudioConnectionError(
                f"LM Studio API hatası: {exc}. {_CONNECTION_HINT_TR}"
            ) from exc

        content: str = response.choices[0].message.content or ""
        return content.strip()

    def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> T:
        """Structured completion validated against a Pydantic schema.

        Uses LM Studio's OpenAI-compatible `response_format` with
        `json_schema`. Falls back to `json_object` if the server returns
        an unsupported-format error, then validates the parsed JSON
        against the provided schema.
        """
        json_schema = schema.model_json_schema()
        response_format: dict[str, Any] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": json_schema,
            },
        }
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=cast(Any, messages),
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=cast(Any, response_format),
            )
        except (APIConnectionError, APITimeoutError) as exc:
            raise LMStudioConnectionError(
                f"LM Studio bağlantı hatası: {exc}. {_CONNECTION_HINT_TR}"
            ) from exc
        except APIError as exc:
            logger.warning(
                "json_schema response_format rejected (%s); retrying with json_object.",
                exc,
            )
            try:
                response = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=cast(Any, messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=cast(Any, {"type": "json_object"}),
                )
            except (APIConnectionError, APITimeoutError, APIError) as exc2:
                raise LMStudioConnectionError(
                    f"LM Studio API hatası: {exc2}. {_CONNECTION_HINT_TR}"
                ) from exc2

        content: str = response.choices[0].message.content or ""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LMStudioConnectionError(
                "LM Studio yanıtı geçerli JSON değil: " + content[:200]
            ) from exc

        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise LMStudioConnectionError(
                f"LM Studio yanıtı şemayla uyumlu değil: {exc}"
            ) from exc
