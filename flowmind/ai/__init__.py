"""FlowMind AI - AI Integration Package."""
from flowmind.ai.advisor import AIAdvisor
from flowmind.ai.providers import BaseAIProvider, MockAIProvider, OpenAIAdapter
from flowmind.ai.schemas import (
    ExecutionSummary,
    FailureExplanation,
    RecoveryRecommendation,
    WorkflowSuggestion,
)

__all__ = [
    "AIAdvisor",
    "BaseAIProvider",
    "MockAIProvider",
    "OpenAIAdapter",
    "FailureExplanation",
    "RecoveryRecommendation",
    "WorkflowSuggestion",
    "ExecutionSummary",
]
