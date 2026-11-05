"""FlowMind AI - Result Reporting and Analytics."""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, List, Optional

from flowmind.monitoring import ExecutionMetrics
from flowmind.types import TaskResult, TaskStatus, WorkflowStatus


@dataclass
class WorkflowResult:
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[ExecutionMetrics] = None
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status in (WorkflowStatus.FAILED, WorkflowStatus.TIMED_OUT, WorkflowStatus.CANCELLED)

    def get_output(self, task_id: str, default: Any = None) -> Any:
        res = self.task_results.get(task_id)
        if res and res.status == TaskStatus.SUCCESS:
            return res.output
        return default

    def successful_tasks(self) -> List[TaskResult]:
        return [r for r in self.task_results.values() if r.status == TaskStatus.SUCCESS]

    def failed_tasks(self) -> List[TaskResult]:
        return [r for r in self.task_results.values() if r.status == TaskStatus.FAILED]

    def skipped_tasks(self) -> List[TaskResult]:
        return [r for r in self.task_results.values() if r.status == TaskStatus.SKIPPED]

    def summary(self) -> str:
        total = len(self.task_results)
        succeeded = len(self.successful_tasks())
        failed = len(self.failed_tasks())
        skipped = len(self.skipped_tasks())
        total_retries = self.metrics.total_retries if self.metrics else 0

        lines = [
            "=" * 60,
            f" FLOWMIND WORKFLOW REPORT: {self.workflow_name}",
            "=" * 60,
            f" Status:       {self.status.value}",
            f" Duration:     {self.duration:.3f}s",
            f" Tasks Total:  {total} (Success: {succeeded}, Failed: {failed}, Skipped: {skipped})",
            f" Retries:      {total_retries}",
        ]

        if self.error:
            lines.append(f" Root Error:   {self.error}")

        lines.append("-" * 60)
        lines.append(f" {'TASK NAME':<25} | {'STATUS':<10} | {'ATTEMPTS':<8} | {'DURATION'}")
        lines.append("-" * 60)

        for res in self.task_results.values():
            status_display = res.status.value
            lines.append(
                f" {res.task_name:<25} | {status_display:<10} | {res.attempts:<8} | {res.duration:.3f}s"
            )
            if res.error:
                lines.append(f"   └── Error: {res.error}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 4),
            "counts": {
                "total": len(self.task_results),
                "success": len(self.successful_tasks()),
                "failed": len(self.failed_tasks()),
                "skipped": len(self.skipped_tasks()),
                "retries": self.metrics.total_retries if self.metrics else 0,
            },
            "error": self.error,
            "tasks": {t_id: res.to_dict() for t_id, res in self.task_results.items()},
            "context_data": self.context_data,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
