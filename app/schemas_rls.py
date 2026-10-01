"""Sprint 15 — RLS policy Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RlsPolicyResponse(BaseModel):
    """One row in rls_policy — what table currently has which RLS state."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    table_name: str
    policy_name: str
    policy_enabled: bool
    description: Optional[str] = None
    notes: Optional[str] = None
    using_clause: str = "true"
    with_check: str = "true"
    role_name: str = "styxproxy_app"
    policy_status: str = "not_started"
    created_by: Optional[str] = None
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    last_audit: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RlsPolicyListResponse(BaseModel):
    policies: list[RlsPolicyResponse]
    total: int
    enabled_count: int
    not_started_count: int


class RlsPolicyToggleRequest(BaseModel):
    """Toggle RLS on a single table."""

    table_name: str = Field(..., min_length=1, max_length=64)
    enable: bool
    using_clause: Optional[str] = Field(None, max_length=1000)
    with_check: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=500)


class RlsPolicyToggleResponse(BaseModel):
    table_name: str
    policy_enabled: bool
    policy_status: str
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    pg_rls_state: str  # 'enabled' | 'disabled'
    pg_policy_count: int


class RlsRolloutPhase(BaseModel):
    """Phase 2a-2h of the Sprint 15 rollout."""

    phase: str  # '2a', '2b', etc.
    table_name: str
    rationale: str
    risk: str  # 'low', 'medium', 'high'
    completed: bool
    enabled_at: Optional[datetime] = None


class RlsRolloutPlanResponse(BaseModel):
    phases: list[RlsRolloutPhase]
    next_phase: Optional[str]
    connection_string_pinned: bool


class RlsSafeStatus(BaseModel):
    """Snapshot of RLS state across all tables — for /api/admin/rls/status."""

    total_tables: int
    rls_enabled_count: int
    rls_disabled_count: int
    policies: list[RlsPolicyResponse]
    bypass_role_exists: bool
    current_user_role: str
    bypass_role_attr_present: bool
