"""In-process Charon runtime stats.

A lightweight counter store for observability. Reset only on process restart
(unlike Prometheus). Exposed via /api/v1/charon/health (cheap) and
/api/admin/charon/stats (superadmin only).

Numbers here are best-effort operational signals, not analytics-grade
counters. Use the JSONL log for fine-grained analysis.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CharonStats:
    """Aggregate counters since process start."""

    started_at: float = field(default_factory=time.time)

    # Request counters
    total_requests: int = 0
    requests_last_minute: int = 0
    successful_replies: int = 0
    escalated_replies: int = 0
    llm_errors: int = 0
    rate_limited: int = 0
    tokens_used_total: int = 0

    # Latency tracking (running aggregates)
    latency_samples: int = 0
    latency_sum_ms: float = 0.0
    latency_max_ms: float = 0.0

    # Per-channel and per-outcome (last N per bucket)
    by_channel: dict = field(default_factory=lambda: defaultdict(int))
    by_outcome: dict = field(default_factory=lambda: defaultdict(int))

    # Recent failures (capped at N) for debugging
    recent_errors: list = field(default_factory=list)

    # LLM state
    llm_last_success_at: Optional[float] = None
    llm_last_error_at: Optional[float] = None
    llm_last_error: Optional[str] = None
    llm_configured: bool = False

    def to_dict(self) -> dict:
        now = time.time()
        uptime_s = int(now - self.started_at)
        avg_latency_ms = (
            round(self.latency_sum_ms / self.latency_samples, 1)
            if self.latency_samples
            else 0.0
        )
        return {
            "uptime_seconds": uptime_s,
            "llm_configured": self.llm_configured,
            "llm_last_success_at": self.llm_last_success_at,
            "llm_last_error_at": self.llm_last_error_at,
            "llm_last_error": self.llm_last_error,
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_replies,
                "escalated": self.escalated_replies,
                "llm_errors": self.llm_errors,
                "rate_limited": self.rate_limited,
            },
            "tokens_used_total": self.tokens_used_total,
            "latency_ms": {
                "samples": self.latency_samples,
                "avg": avg_latency_ms,
                "max": round(self.latency_max_ms, 1),
            },
            "by_channel": dict(self.by_channel),
            "by_outcome": dict(self.by_outcome),
            "recent_errors": list(self.recent_errors),
        }


class CharonMetrics:
    """Thread-safe singleton for Charon stats."""

    _lock = threading.Lock()
    _stats = CharonStats()
    _MAX_RECENT_ERRORS = 20

    @classmethod
    def get(cls) -> CharonStats:
        return cls._stats

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._stats = CharonStats()

    @classmethod
    def mark_request(cls, channel: str = "web") -> None:
        with cls._lock:
            s = cls._stats
            s.total_requests += 1
            s.by_channel[channel or "unknown"] += 1

    @classmethod
    def mark_success(cls, tokens_used: int = 0, latency_ms: float = 0.0) -> None:
        with cls._lock:
            s = cls._stats
            s.successful_replies += 1
            s.tokens_used_total += int(tokens_used or 0)
            s.by_outcome["success"] += 1
            s.llm_last_success_at = time.time()
            s.latency_samples += 1
            s.latency_sum_ms += latency_ms
            if latency_ms > s.latency_max_ms:
                s.latency_max_ms = latency_ms

    @classmethod
    def mark_escalated(cls, reason: str = "unknown") -> None:
        with cls._lock:
            s = cls._stats
            s.escalated_replies += 1
            s.by_outcome["escalated"] += 1
            s.by_outcome[f"escalated:{reason}"] += 1

    @classmethod
    def mark_llm_error(cls, error: str) -> None:
        with cls._lock:
            s = cls._stats
            s.llm_errors += 1
            s.by_outcome["llm_error"] += 1
            s.llm_last_error_at = time.time()
            s.llm_last_error = error[:300]
            s.recent_errors.append(
                {
                    "ts": time.time(),
                    "kind": "llm_error",
                    "error": error[:300],
                }
            )
            if len(s.recent_errors) > cls._MAX_RECENT_ERRORS:
                s.recent_errors = s.recent_errors[-cls._MAX_RECENT_ERRORS:]

    @classmethod
    def mark_rate_limited(cls) -> None:
        with cls._lock:
            s = cls._stats
            s.rate_limited += 1
            s.by_outcome["rate_limited"] += 1

    @classmethod
    def mark_scenario_hit(cls, scenario_id: str) -> None:
        with cls._lock:
            s = cls._stats
            s.by_outcome[f"scenario:{scenario_id}"] += 1
            s.by_outcome["scenario_hit"] += 1

    @classmethod
    def record_latency(cls, latency_ms: float) -> None:
        with cls._lock:
            s = cls._stats
            s.latency_samples += 1
            s.latency_sum_ms += latency_ms
            if latency_ms > s.latency_max_ms:
                s.latency_max_ms = latency_ms

    @classmethod
    def llm_configured(cls, configured: bool) -> None:
        with cls._lock:
            cls._stats.llm_configured = configured
