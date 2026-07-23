"""Q/A evaluation set derived from Scenarios + runner.

The eval set is a curated list of customer questions and the keywords that
should appear in Charon's answer (or the scenario id it should match).
This gives us a fast, deterministic smoke test for the RAG + scenario pipeline.

The set lives in code (not the LLM) so it never drifts and can be reviewed
in a PR. Each entry traces back to a Scenarios source file.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.schemas import EvalQuestion, EvalSetResponse, EvalResult, EvalRunResponse

logger = logging.getLogger(__name__)


# Hand-curated eval set. Each question is derived from a specific Scenarios
# file. Add new questions whenever a new scenario lands.
EVAL_QUESTIONS: list[EvalQuestion] = [
    EvalQuestion(
        id="first-time-greeting",
        question="Hi, I'm new here. How do I get started?",
        expected_keywords=["order", "proxy", "country"],
        expected_scenario=None,
        source="2026-06-26-first-time-order.md",
    ),
    EvalQuestion(
        id="free-trial",
        question="Is there a free trial I can try first?",
        expected_keywords=["trial", "free", "minutes"],
        expected_scenario=None,
        source="2026-06-26-free-trial.md",
    ),
    EvalQuestion(
        id="forgot-pin-recovery",
        question="I forgot my pin, what should I do?",
        expected_keywords=["pin", "reset", "support"],
        expected_scenario=None,
        source="2026-06-26-forgot-pin-recovery.md",
    ),
    EvalQuestion(
        id="provider-down",
        question="The proxy isn't working, what do I do?",
        expected_keywords=["support", "rotat", "refund"],
        expected_scenario=None,
        source="2026-06-26-provider-down-recovery.md",
    ),
    EvalQuestion(
        id="refund-request",
        question="I want a refund please.",
        expected_keywords=["refund", "order", "support"],
        expected_scenario=None,
        source="2026-06-26-admin-operations.md",
    ),
    EvalQuestion(
        id="greeting-casual",
        question="hello",
        expected_keywords=[],
        expected_scenario=None,
        source="2026-06-26-first-time-order.md",
    ),
    EvalQuestion(
        id="thanks",
        question="thank you so much",
        expected_keywords=[],
        expected_scenario=None,
        source="2026-06-27-complete-scenario-walkthrough.md",
    ),
    EvalQuestion(
        id="pricing-question",
        question="How much does your service cost?",
        expected_keywords=["price", "ngn", "plan"],
        expected_scenario=None,
        source="2026-06-27-admin-operations.md",
    ),
]


EVAL_SET = EvalSetResponse(
    name="Charon Q/A smoke test",
    description=(
        "Hand-curated test questions derived from /root/styxproxy/scenarios/*.md. "
        "Each question asserts that Charon's reply contains the expected keywords "
        "(case-insensitive substring match). Used to verify that the scenario "
        "loader + knowledge RAG + LLM pipeline is working end-to-end."
    ),
    questions=EVAL_QUESTIONS,
)


def get_eval_set() -> EvalSetResponse:
    """Return the eval set definition (questions only — no execution)."""
    return EVAL_SET


def _grade(answer: str, expected_keywords: list[str]) -> tuple[bool, list[str], list[str]]:
    """Check which expected keywords appear in the answer (case-insensitive)."""
    lower = answer.lower()
    matched = [k for k in expected_keywords if k.lower() in lower]
    missing = [k for k in expected_keywords if k.lower() not in lower]
    return (len(missing) == 0), matched, missing


async def run_eval_set() -> EvalRunResponse:
    """Run each eval question through the live Charon pipeline and grade the answer."""
    # Lazy imports to avoid circular deps
    from app.services.charon.scenarios import match, all_scenarios, ScenarioAction
    from app.services.charon.knowledge import search, format_context
    from app.services.charon.llm import call_llm

    results: list[EvalResult] = []

    for q in EVAL_QUESTIONS:
        t0 = time.monotonic()
        answer = ""
        matched_scenario_id: Optional[str] = None
        try:
            scenario = match(q.question)
            if scenario is not None:
                matched_scenario_id = scenario.id
                for action in scenario.actions:
                    if isinstance(action, ScenarioAction) and action.type == "reply" and action.text:
                        answer = action.text
                        break
            if not answer:
                chunks = search(q.question, top_k=4)
                context = format_context(chunks)
                # Build a minimal messages list (eval is single-turn, no history)
                system_prompt = (
                    "You are Charon, the Styxproxy customer support assistant. "
                    "Answer concisely using the provided context. "
                    "If you don't know, say so and offer to escalate."
                )
                user_content = f"Context:\n{context}\n\nCustomer: {q.question}" if context else f"Customer: {q.question}"
                resp = call_llm(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=300,
                )
                answer = resp.content or ""
        except Exception as exc:  # pragma: no cover — surface error to caller
            logger.exception("eval run failed for %s", q.id)
            answer = f"[error: {exc}]"

        passed, matched, missing = _grade(answer, q.expected_keywords)
        # If the eval question requires a specific scenario, gate on that too
        if q.expected_scenario is not None:
            passed = passed and matched_scenario_id == q.expected_scenario

        latency_ms = int((time.monotonic() - t0) * 1000)
        results.append(
            EvalResult(
                id=q.id,
                question=q.question,
                answer=answer,
                passed=passed,
                matched_keywords=matched,
                missing_keywords=missing,
                expected_scenario=q.expected_scenario,
                matched_scenario=matched_scenario_id,
                latency_ms=latency_ms,
            )
        )

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count
    pass_rate = (passed_count / total) if total else 0.0
    return EvalRunResponse(
        total=total,
        passed=passed_count,
        failed=failed_count,
        pass_rate=pass_rate,
        results=results,
        ran_at=datetime.now(timezone.utc),
    )