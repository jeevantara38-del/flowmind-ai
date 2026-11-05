"""FlowMind AI - Built-in Plugins."""

import time
from typing import Any, Dict, List
from flowmind.context import ExecutionContext
from flowmind.plugins.base import BasePlugin
from flowmind.reporting import WorkflowResult
from flowmind.task import Task
from flowmind.types import TaskResult


class ConsoleLoggerPlugin(BasePlugin):
    name: str = "ConsoleLogger"

    def on_workflow_start(self, workflow_id: str, metadata: Dict[str, Any]) -> None:
        print(f"▶ [Workflow Start] {metadata.get('name', workflow_id)} (Tasks: {metadata.get('task_count')})")

    def on_task_start(self, task: Task, context: ExecutionContext) -> None:
        print(f"  ⏳ [Task Start] {task.name}")

    def on_task_complete(self, task: Task, result: TaskResult, context: ExecutionContext) -> None:
        print(f"  ✅ [Task Success] {task.name} ({result.duration:.3f}s)")

    def on_task_retry(self, task: Task, attempt: int, error: Exception, delay_seconds: float) -> None:
        print(f"  🔄 [Task Retry] {task.name} attempt #{attempt} failed: {error}. Retrying in {delay_seconds:.2f}s...")

    def on_task_failure(self, task: Task, result: TaskResult, error: Exception, context: ExecutionContext) -> None:
        print(f"  ❌ [Task Failed] {task.name}: {error}")

    def on_task_skipped(self, task: Task, context: ExecutionContext) -> None:
        print(f"  ⏭️ [Task Skipped] {task.name}")

    def on_workflow_complete(self, workflow_id: str, result: WorkflowResult) -> None:
        print(f"⏹ [Workflow Finished] Status: {result.status.value} (Duration: {result.duration:.3f}s)")


class AuditLogPlugin(BasePlugin):
    name: str = "AuditLog"

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def _record(self, action: str, details: Dict[str, Any]) -> None:
        self.entries.append({
            "timestamp": time.time(),
            "action": action,
            "details": details,
        })

    def on_workflow_start(self, workflow_id: str, metadata: Dict[str, Any]) -> None:
        self._record("WORKFLOW_START", {"workflow_id": workflow_id, **metadata})

    def on_task_start(self, task: Task, context: ExecutionContext) -> None:
        self._record("TASK_START", {"task_id": task.id, "task_name": task.name})

    def on_task_complete(self, task: Task, result: TaskResult, context: ExecutionContext) -> None:
        self._record("TASK_COMPLETE", {"task_id": task.id, "duration": result.duration})

    def on_task_failure(self, task: Task, result: TaskResult, error: Exception, context: ExecutionContext) -> None:
        self._record("TASK_FAILURE", {"task_id": task.id, "error": str(error)})

    def on_workflow_complete(self, workflow_id: str, result: WorkflowResult) -> None:
        self._record("WORKFLOW_COMPLETE", {"status": result.status.value, "duration": result.duration})
