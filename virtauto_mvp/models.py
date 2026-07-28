from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class DataQuality(BaseModel):
    rows: int
    columns: int
    missing_required_values: int
    duplicate_timestamps: int
    interval_minutes: float | None
    decision_readiness: Literal["READY", "LIMITED", "INSUFFICIENT"]
    issues: list[str] = Field(default_factory=list)


class PeakEvent(BaseModel):
    start: str
    end: str
    duration_minutes: int
    maximum_power_kw: float
    threshold_kw: float
    excess_kw: float


class IndustrialContext(BaseModel):
    context_id: str
    dataset_id: str
    site_id: str
    area_id: str
    line_id: str
    generated_at: str
    analysis_window: dict[str, str]
    data_quality: DataQuality
    trigger: dict[str, Any]
    energy: dict[str, Any]
    production: dict[str, Any]
    quality: dict[str, Any]
    material_flow: dict[str, Any]
    order: dict[str, Any]
    governance: dict[str, Any]
    uncertainties: list[str]
    context_confidence: Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
    context_summary: str


class DecisionOption(BaseModel):
    option_id: str
    option_type: str
    title: str
    expected_effects: dict[str, Any]
    risks: dict[str, str]
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    score: float | None = None
    status: str = "GENERATED"
    confidence: str = "MEDIUM"
    explanation: str


class DecisionEvaluation(BaseModel):
    decision_id: str
    context_id: str
    decision_type: str = "BIW_ENERGY_PEAK_MITIGATION"
    execution_mode: str = "PROPOSE_ONLY"
    baseline_option_id: str
    options: list[DecisionOption]
    recommendation: dict[str, Any]


class GovernanceResult(BaseModel):
    status: str
    decision_id: str
    recommended_option_id: str | None
    conditions: list[str]
    required_approvals: list[str]
    required_reviews: list[str]
    veto_roles: list[str]
    rule_results: list[dict[str, Any]]
    execution_mode: str
    valid_until: str | None


class DecisionReport(BaseModel):
    identity: dict[str, Any]
    executive_decision: dict[str, Any]
    situation: dict[str, Any]
    industrial_context: dict[str, Any]
    recommendation: dict[str, Any]
    expected_impact: dict[str, Any]
    alternatives: list[dict[str, Any]]
    governance: dict[str, Any]
    data_quality: dict[str, Any]
    assumptions: list[str]
    audit: dict[str, Any]
