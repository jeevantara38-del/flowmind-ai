"""FlowMind AI - Plugin Interface."""

from typing import Any, Dict, Optional
from flowmind.context import ExecutionContext
from flowmind.reporting import WorkflowResult
from flowmind.task import Task
from flowmind.types import TaskResult


class BasePlugin:
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = "Base FlowMind plugin interface."

    def on_workflow_start(self, workflow_id: str, metadata: Dict[str, Any]) -> None:
        pass

    def on_task_start(self, task: Task, context: ExecutionContext) -> None:
        pass

    def on_task_complete(self, task: Task, result: TaskResult, context: ExecutionContext) -> None:
        pass

    def on_task_failure(self, task: Task, result: TaskResult, error: Exception, context: ExecutionContext) -> None:
        pass

    def on_task_retry(self, task: Task, attempt: int, error: Exception, delay_seconds: float) -> None:
        pass

    def on_task_skipped(self, task: Task, context: ExecutionContext) -> None:
        pass

    def on_workflow_complete(self, workflow_id: str, result: WorkflowResult) -> None:
        pass
