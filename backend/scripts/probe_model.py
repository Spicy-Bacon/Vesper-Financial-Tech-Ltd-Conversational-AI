#!/usr/bin/env python3
"""One synthetic completion after discovery; no production catalog or user data."""

import asyncio
import sys
from pathlib import Path
from time import perf_counter

# Support both `python scripts/probe_model.py` and module execution.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.schemas.inference import AllowedOption, InferenceQuestion, InterpretationInput
from app.services.model_client import (
    LocalModelClient, ModelCallError, ModelConfig, ModelConfigurationError,
    ModelOutputError, build_messages, parse_decision,
)
from app.services.retrieval import QuestionScopedRetriever


def synthetic_probe_context() -> InterpretationInput:
    """Fictional transport check, NOT finance policy or an approved catalog."""
    question = InferenceQuestion(
        catalog_version="SYNTHETIC-PROBE-NOT-A-RELEASE", question_id="Q4",
        text="SYNTHETIC transport test: which fictional statement did the speaker use?",
        options=[
            AllowedOption(question_id="Q4", option_id="SYNTHETIC_Q4_C",
                          label="SYNTHETIC: three months of essentials"),
            AllowedOption(question_id="Q4", option_id="SYNTHETIC_Q4_U",
                          label="SYNTHETIC: unsure", is_unsure=True),
        ],
    )
    reply = "Fictional example only: those savings cover three months of essentials."
    return InterpretationInput(
        question=question, options=question.options, user_reply=reply,
        retrieval=QuestionScopedRetriever([]).retrieve(
            catalog_version=question.catalog_version, question_id=question.question_id,
            user_reply=reply,
        ),
    )


async def run_probe(config: ModelConfig, *, transport: httpx.AsyncBaseTransport | None = None) -> int:
    print(f"Base URL: {config.base_url}")
    print(f"Selected model ID: {config.model_id or '(unset)'}")
    started = perf_counter()
    try:
        async with LocalModelClient(config, transport=transport) as client:
            ids = await client.list_models()
            print("Available model IDs: " + (", ".join(ids) or "(none)"))
            if config.model_id is None:
                print("FAILURE: Set MODEL_ID to an exact discovered ID, then run again. No completion sent.")
                return 2
            if config.model_id not in ids:
                print("FAILURE: MODEL_ID must match a discovered ID. No completion sent.")
                return 2
            context = synthetic_probe_context()
            # Intentionally bypass Interpreter's retry: the probe sends ONE request.
            raw = await client.complete(build_messages(context))
            decision = parse_decision(raw, context=context)
            print(f"SUCCESS: parsed structured action: {decision.action}")
            return 0
    except ModelCallError as error:
        print(f"FAILURE: {error.reason}; parsed structured action: (none)")
        return 1
    except ModelOutputError:
        print("FAILURE: invalid_model_output; parsed structured action: (none)")
        return 1
    finally:
        print(f"Latency (discovery + completion): {round((perf_counter() - started) * 1000)} ms")


def main() -> int:
    try:
        config = ModelConfig.from_env()
    except ModelConfigurationError as error:
        print(f"FAILURE: {error}")
        return 2
    return asyncio.run(run_probe(config))


if __name__ == "__main__":
    raise SystemExit(main())
