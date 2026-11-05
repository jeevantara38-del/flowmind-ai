"""FlowMind AI - Exception Hierarchy.

Defines all custom exceptions used throughout the FlowMind AI library.
"""

from typing import Any, List, Optional


class FlowMindError(Exception):
    """Base exception for all FlowMind AI errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class WorkflowError(FlowMindError):
    """Base exception for workflow-related failures."""
    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails (e.g., missing dependencies)."""
    pass


class CircularDependencyError(WorkflowValidationError):
    """Raised when a circular dependency (cycle) is detected in the DAG."""

    def __init__(self, cycle_path: List[str]) -> None:
        path_str = " -> ".join(cycle_path)
        message = f"Circular dependency detected in workflow: {path_str}"
        super().__init__(message, details={"cycle_path": cycle_path})
        self.cycle_path = cycle_path


class WorkflowTimeoutError(WorkflowError):
    """Raised when an entire workflow exceeds its configured timeout."""
    pass


class WorkflowCancelledError(WorkflowError):
    """Raised when a workflow execution is cancelled by the user or system."""
    pass


class TaskError(FlowMindError):
    """Base exception for task-related failures."""

    def __init__(self, task_id: str, message: str, details: Optional[dict] = None) -> None:
        self.task_id = task_id
        super().__init__(f"Task '{task_id}': {message}", details=details)


class TaskExecutionError(TaskError):
    """Raised when a task fails during function execution."""

    def __init__(self, task_id: str, original_error: Exception, details: Optional[dict] = None) -> None:
        self.original_error = original_error
        details = details or {}
        details["original_error"] = str(original_error)
        details["error_type"] = type(original_error).__name__
        super().__init__(task_id, f"Execution failed: {original_error}", details=details)


class TaskTimeoutError(TaskError):
    """Raised when a task exceeds its configured execution timeout."""

    def __init__(self, task_id: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            task_id,
            f"Timed out after {timeout_seconds} seconds",
            details={"timeout_seconds": timeout_seconds},
        )


class TaskCancelledError(TaskError):
    """Raised when an individual task execution is cancelled."""
    pass


class MaxRetriesExceededError(TaskError):
    """Raised when a task has exhausted all configured retry attempts."""

    def __init__(self, task_id: str, attempts: int, last_error: Exception) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            task_id,
            f"Exhausted all {attempts} retry attempts. Last error: {last_error}",
            details={"attempts": attempts, "last_error": str(last_error)},
        )


class NonIdempotentRetryError(TaskError):
    """Raised when a non-idempotent task fails and retries are prevented for safety."""

    def __init__(self, task_id: str) -> None:
        super().__init__(
            task_id,
            "Cannot retry non-idempotent task automatically. Retrying non-idempotent "
            "operations risks duplicate side effects. Mark is_idempotent=True if safe.",
            details={"is_idempotent": False},
        )


class ConditionEvaluationError(TaskError):
    """Raised when evaluating a conditional branch predicate fails."""
    pass


class CheckpointError(FlowMindError):
    """Raised when creating, saving, or restoring a workflow checkpoint fails."""
    pass


class PluginError(FlowMindError):
    """Raised when a plugin hook encounters an error."""
    pass


class AIProviderError(FlowMindError):
    """Raised when an AI provider call fails or returns an invalid schema."""
    pass


class SecurityError(FlowMindError):
    """Raised when a security validation or boundary check fails."""
    pass
