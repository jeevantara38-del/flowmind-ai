"""FlowMind AI - AI Decision Support and Advisor."""

from typing import Any, Dict, Optional
from flowmind.ai.providers import BaseAIProvider, MockAIProvider
from flowmind.ai.schemas import (
    ExecutionSummary,
    FailureExplanation,
    RecoveryRecommendation,
    WorkflowSuggestion,
)
from flowmind.reporting import WorkflowResult
from flowmind.types import TaskResult


class AIAdvisor:
    def __init__(self, provider: Optional[BaseAIProvider] = None) -> None:
        self.provider = provider or MockAIProvider()

    def explain_failure(self, task_result: TaskResult) -> FailureExplanation:
        if task_result.is_success:
            return FailureExplanation(
                task_name=task_result.task_name,
                error_type="None",
                error_message="None",
                summary="Task completed successfully.",
                is_transient=False,
                recommended_action="None needed.",
            )

        system_prompt = (
            "You are an expert systems reliability engineer. Analyze the provided "
            "Python task failure and return structured JSON containing summary, "
            "possible_causes (list), is_transient (bool), recommended_action (str)."
        )
        user_prompt = (
            f"Task: {task_result.task_name} (ID: {task_result.task_id})\n"
            f"Error Type: {task_result.error_type}\n"
            f"Error Message: {task_result.error}\n"
            f"Attempts: {task_result.attempts}\n"
            f"Idempotent: {task_result.is_idempotent}"
        )

        raw = self.provider.generate(system_prompt, user_prompt)
        return FailureExplanation(
            task_name=task_result.task_name,
            error_type=task_result.error_type or "UnknownError",
            error_message=task_result.error or "",
            summary=raw.get("summary", "Task encountered an error."),
            possible_causes=raw.get("possible_causes", []),
            is_transient=raw.get("is_transient", False),
            recommended_action=raw.get("recommended_action", "Inspect logs for details."),
            confidence_score=raw.get("confidence_score", 0.9),
        )

    def recommend_recovery(self, task_result: TaskResult) -> RecoveryRecommendation:
        system_prompt = (
            "You are an AI recovery advisor for automation workflows. Suggest safe recovery steps. "
            "Never propose dangerous code execution. Set requires_approval to true for state modifications."
        )
        user_prompt = (
            f"Task: {task_result.task_name}\n"
            f"Status: {task_result.status.value}\n"
            f"Error: {task_result.error}\n"
            f"Is Idempotent: {task_result.is_idempotent}"
        )

        raw = self.provider.generate(system_prompt, user_prompt)
        return RecoveryRecommendation(
            action_type=raw.get("action_type", "MANUAL_FIX"),
            title=raw.get("title", "Review Task Error"),
            description=raw.get("description", "Inspect the failure and resolve root cause."),
            requires_approval=raw.get("requires_approval", True),
            suggested_fix=raw.get("suggested_fix"),
            parameters=raw.get("parameters", {}),
        )

    def suggest_workflow_improvements(self, workflow_result: WorkflowResult) -> WorkflowSuggestion:
        system_prompt = "Analyze workflow performance metrics and suggest optimizations in JSON."
        user_prompt = (
            f"Workflow: {workflow_result.workflow_name}\n"
            f"Duration: {workflow_result.duration}s\n"
            f"Tasks: {len(workflow_result.task_results)}\n"
            f"Status: {workflow_result.status.value}"
        )

        raw = self.provider.generate(system_prompt, user_prompt)
        return WorkflowSuggestion(
            workflow_name=workflow_result.workflow_name,
            summary=raw.get("summary", "Workflow analysis complete."),
            parallelism_opportunities=raw.get("parallelism_opportunities", []),
            reliability_improvements=raw.get("reliability_improvements", []),
            estimated_speedup=raw.get("estimated_speedup", "N/A"),
        )

    def summarize_execution(self, workflow_result: WorkflowResult) -> ExecutionSummary:
        system_prompt = "Generate an executive summary of the workflow run in JSON format."
        user_prompt = (
            f"Workflow: {workflow_result.workflow_name}\n"
            f"Status: {workflow_result.status.value}\n"
            f"Duration: {workflow_result.duration:.2f}s\n"
            f"Total tasks: {len(workflow_result.task_results)}\n"
            f"Failed: {len(workflow_result.failed_tasks())}"
        )

        raw = self.provider.generate(system_prompt, user_prompt)
        return ExecutionSummary(
            headline=raw.get("headline", f"Execution Report for {workflow_result.workflow_name}"),
            status=workflow_result.status.value,
            duration_seconds=workflow_result.duration,
            total_tasks=len(workflow_result.task_results),
            failed_tasks=len(workflow_result.failed_tasks()),
            key_findings=raw.get("key_findings", []),
        )
