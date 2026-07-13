"""Scenario loader and matcher.

Each scenario has trigger patterns, optional actions, and a hint
whether the LLM is still required.

A scenario fires when one of its patterns matches the user's message
case-insensitively. We always try simple scenarios before calling
the LLM — this both saves LLM tokens and gives us deterministic
answers for the most common questions.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).parents[3] / "data" / "charon" / "scenarios"


@dataclass
class ScenarioAction:
    type: str  # 'reply' | 'escalate' | 'tool'
    text: str | None = None
    tool_name: str | None = None
    tool_params: dict | None = None
    summary_template: str | None = None
    reason: str | None = None


@dataclass
class Scenario:
    id: str
    name: str
    patterns: list[re.Pattern] = field(default_factory=list)
    actions: list[ScenarioAction] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


_scenarios: list[Scenario] = []


def _load() -> None:
    if _scenarios:
        return
    if not SCENARIOS_DIR.exists():
        return
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            logger.error("Scenario %s failed to parse: %s", path, exc)
            continue

        patterns: list[re.Pattern] = []
        for raw in data.get("trigger", []):
            try:
                patterns.append(re.compile(raw, re.IGNORECASE | re.DOTALL))
            except re.error as exc:
                logger.error("Scenario %s has bad regex %r: %s", path.name, raw, exc)

        actions = [ScenarioAction(**a) for a in data.get("actions", [])]

        _scenarios.append(
            Scenario(
                id=data.get("id", path.stem),
                name=data.get("name", path.stem),
                patterns=patterns,
                actions=actions,
                raw=data,
            )
        )
    logger.info("Loaded %d scenarios", len(_scenarios))


def match(message: str) -> Scenario | None:
    """Return the first scenario whose pattern matches the message, or None."""
    _load()
    for s in _scenarios:
        for pattern in s.patterns:
            if pattern.search(message):
                return s
    return None


def all_scenarios() -> Iterable[Scenario]:
    _load()
    return tuple(_scenarios)
