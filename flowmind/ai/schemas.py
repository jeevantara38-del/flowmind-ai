"""FlowMind AI - Structured Schemas for AI Decision Engine."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FailureExplanation:
    task_name: str
    error_type: str
    error_message: str
    summary: str
    possible_causes: List[str] = field(default_factory=list)
    is_transient: bool = False
    recommended_action: str = ""
    confidence_score: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_name": self.task_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "summary": self.summary,
            "possible_causes": self.possible_causes,
            "is_transient": self.is_transient,
            "recommended_action": self.recommended_action,
            "confidence_score": round(self.confidence_score, 2),
        }


@dataclass
class RecoveryRecommendation:
    action_type: str
    title: str
    description: str
    requires_approval: bool = True
    suggested_fix: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "title": self.title,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "suggested_fix": self.suggested_fix,
            "parameters": self.parameters,
        }


@dataclass
class WorkflowSuggestion:
    workflow_name: str
    summary: str
    parallelism_opportunities: List[str] = field(default_factory=list)
    reliability_improvements: List[str] = field(default_factory=list)
    estimated_speedup: str = "N/A"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "summary": self.summary,
            "parallelism_opportunities": self.parallelism_opportunities,
            "reliability_improvements": self.reliability_improvements,
            "estimated_speedup": self.estimated_speedup,
        }


@dataclass
class ExecutionSummary:
    headline: str
    status: str
    duration_seconds: float
    total_tasks: int
    failed_tasks: int
    key_findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "total_tasks": self.total_tasks,
            "failed_tasks": self.failed_tasks,
            "key_findings": self.key_findings,
        }
