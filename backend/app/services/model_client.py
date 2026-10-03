"""OpenAI-compatible transport, production parser and stateless interpreter."""

import asyncio
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from time import perf_counter
from typing import Annotated, Protocol, Self
from urllib.parse import urlsplit

import httpx
from pydantic import Field, SecretStr, field_validator

from app.schemas.inference import (
    CLARIFICATION_QUESTIONS, AllowedOption, FallbackReason, Identifier,
    InferenceOutcome, InferenceQuestion, InterpretationInput, ModelDecision,
    RetrievalResult, StrictContract,
)

_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "interpreter_v1.txt").read_text()
_MAX_RESPONSE_BYTES = 65_536
_MAX_DECISION_CHARS = 8192


class ModelConfigurationError(ValueError):
    """Invalid environment configuration; messages contain no supplied values."""


class ModelOutputError(ValueError):
    """Untrusted output failed parsing or deterministic validation."""


class ModelCallError(Exception):
    def __init__(self, reason: FallbackReason) -> None:
        self.reason = reason
        super().__init__(reason)


class ModelConfig(StrictContract):
    base_url: str = "http://127.0.0.1:8000/v1"
    model_id: Identifier | None = None
    api_key: SecretStr | None = Field(default=None, repr=False, exclude=True)
    timeout_seconds: Annotated[float, Field(gt=0, le=120, allow_inf_nan=False)] = 30.0
    json_mode: bool = False

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/v1"
                or any(c.isspace() for c in value)):
            raise ValueError("base URL must be an HTTP(S) /v1 URL without credentials or query")
        # Force invalid ports to fail configuration before any HTTP call.
        _ = parsed.port
        return value.rstrip("/")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Self:
        env = os.environ if environ is None else environ
        try:
            json_mode = env.get("MODEL_JSON_MODE", "false").lower().strip()
            if json_mode not in {"true", "false"}:
                raise ValueError("invalid boolean")
            key = env.get("MODEL_API_KEY", "")
            return cls(
                base_url=env.get("MODEL_BASE_URL", "http://127.0.0.1:8000/v1"),
                model_id=env.get("MODEL_ID", "").strip() or None,
                api_key=SecretStr(key) if key else None,
                timeout_seconds=float(env.get("MODEL_TIMEOUT_SECONDS", "30")),
                json_mode=json_mode == "true",
            )
        except (ValueError, TypeError):
            raise ModelConfigurationError("Invalid MODEL_* configuration; check backend/.env.example") from None


class ModelClient(Protocol):
    model_id: str | None

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Return assistant JSON content or raise ModelCallError."""
        ...


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-JSON number")


def _load_json(raw: str | bytes) -> object:
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)


def parse_decision(raw: str, *, context: InterpretationInput) -> ModelDecision:
    """Shared production/probe parser. Never include output or reply in errors."""
    try:
        if not isinstance(raw, str) or len(raw) > _MAX_DECISION_CHARS:
            raise ValueError("invalid content size")
        decision = ModelDecision.model_validate(_load_json(raw))
        if decision.action == "propose_option":
            active_ids = {o.option_id for o in context.question.options
                          if o.question_id == context.question.question_id}
            supplied_ids = {o.option_id for o in context.options}
            if decision.option_id not in active_ids & supplied_ids:
                raise ValueError("option outside active question")
            if decision.evidence_quote not in context.user_reply:
                raise ValueError("evidence is not literal user text")
        if not set(decision.explanation_content_ids) <= {s.content_id for s in context.retrieval.snippets}:
            raise ValueError("unknown explanation content")
        return decision
    except (ValueError, TypeError, RecursionError):
        raise ModelOutputError("Model response failed structured validation") from None


def build_messages(context: InterpretationInput) -> list[dict[str, str]]:
    policy = {
        "decision_schema": ModelDecision.model_json_schema(),
        "neutral_clarification_templates": CLARIFICATION_QUESTIONS,
    }
    # Options are included exactly once, in full, independent of retrieval.
    data = {
        "active_question": context.question.model_dump(exclude={"options"}),
        "allowed_options": [option.model_dump() for option in context.options],
        "retrieval": context.retrieval.model_dump(),
        "user_reply": context.user_reply,
    }
    return [
        {"role": "system", "content": _PROMPT + "\n" + json.dumps(policy, ensure_ascii=False)},
        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
    ]


class LocalModelClient:
    """Owns one reusable async HTTP client. Close with async with or aclose()."""

    def __init__(self, config: ModelConfig, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.config = config
        self.model_id = config.model_id
        headers = {}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key.get_secret_value()}"
        self._http = httpx.AsyncClient(
            base_url=config.base_url + "/", headers=headers,
            timeout=config.timeout_seconds, transport=transport,
            trust_env=False, follow_redirects=False,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: object) -> object:
        try:
            # HTTPX has per-operation timeouts; also bound total wall time.
            async with asyncio.timeout(self.config.timeout_seconds):
                async with self._http.stream(method, path, **kwargs) as response:
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > _MAX_RESPONSE_BYTES:
                            raise ModelCallError("invalid_model_output")
                    return _load_json(bytes(body))
        except (TimeoutError, httpx.TimeoutException):
            raise ModelCallError("model_timeout") from None
        except httpx.HTTPError:
            raise ModelCallError("model_unavailable") from None
        except (ValueError, TypeError, RecursionError):
            raise ModelCallError("invalid_model_output") from None

    async def list_models(self) -> list[str]:
        payload = await self._request("GET", "models")
        try:
            models = payload["data"]
            if not isinstance(models, list):
                raise ValueError("invalid discovery data")
            # Reuse identifier validation, without assuming any executable ID.
            configs = [ModelConfig(model_id=item["id"]) for item in models]
            if any(c.model_id is None for c in configs):
                raise ValueError("missing discovery ID")
            return sorted({c.model_id for c in configs})
        except (ValueError, TypeError, KeyError):
            raise ModelCallError("invalid_model_output") from None

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if self.model_id is None:
            raise ModelCallError("model_not_configured")
        payload = {
            "model": self.model_id, "messages": messages,
            "temperature": 0.0, "max_tokens": 512, "stream": False, "n": 1,
        }
        if self.config.json_mode:
            payload["response_format"] = {"type": "json_object"}
        envelope = await self._request("POST", "chat/completions", json=payload)
        try:
            choices = envelope["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError("expected one choice")
            choice = choices[0]
            message = choice["message"]
            if (choice["finish_reason"] != "stop" or message["role"] != "assistant"
                    or message.get("tool_calls") or message.get("function_call")
                    or message.get("refusal")):
                raise ValueError("incomplete or unsupported completion")
            content = message["content"]
            if not isinstance(content, str) or len(content) > _MAX_DECISION_CHARS:
                raise ValueError("invalid assistant content")
            # Never inspect, log or return any reasoning fields in the envelope.
            return content
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ModelCallError("invalid_model_output") from None


class MockModelClient:
    """Explicit scripted test/development adapter; stores no request content."""

    model_id = "mock-synthetic"

    def __init__(self, responses: Sequence[str | ModelCallError]) -> None:
        self._responses = iter(responses)
        self.call_count = 0

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.call_count += 1
        result = next(self._responses, ModelCallError("model_unavailable"))
        if isinstance(result, ModelCallError):
            raise result
        return result


class Interpreter:
    def __init__(self, client: ModelClient) -> None:
        self.client = client

    async def interpret(self, *, question: InferenceQuestion, options: list[AllowedOption],
                        user_reply: str, retrieval: RetrievalResult) -> InferenceOutcome:
        # Invalid caller/catalog input raises ValidationError before inference.
        # Pydantic revalidation also snapshots nested collections for the await.
        context = InterpretationInput(
            question=question, options=options, user_reply=user_reply, retrieval=retrieval,
        )
        started = perf_counter()
        messages = build_messages(context)
        decision = None
        reason: FallbackReason | None = None
        for attempt in range(2):
            try:
                raw = await self.client.complete(messages)
                decision = parse_decision(raw, context=context)
                reason = None
                break
            except ModelOutputError:
                reason = "invalid_model_output"
            except ModelCallError as error:
                reason = error.reason
            if reason != "invalid_model_output" or attempt == 1:
                break
            # Do not echo failed output, parser errors, or hidden reasoning.
            messages = [messages[0], {
                "role": "system",
                "content": "The previous attempt failed validation. Return only a valid decision; "
                           "use an allowed clarification template if uncertain.",
            }, messages[-1]]
        return InferenceOutcome(
            retrieval=context.retrieval, decision=decision, model_id=self.client.model_id,
            latency_ms=max(0, round((perf_counter() - started) * 1000)),
            fallback_reason=reason, retry_count=attempt,
        )
