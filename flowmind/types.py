"""FlowMind AI - Core Enums and Data Models."""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class FailureClassification(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    FATAL = "FATAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class TaskResult:
    task_id: str
    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: float = 0.0
    is_idempotent: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status == TaskStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        return self.status == TaskStatus.SKIPPED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "output": str(self.output) if self.output is not None else None,
            "error": self.error,
            "error_type": self.error_type,
            "attempts": self.attempts,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 4),
            "is_idempotent": self.is_idempotent,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    message: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "message": self.message,
            "payload": self.payload,
        }
