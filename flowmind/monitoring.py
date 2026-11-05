"""FlowMind AI - Monitoring, Metrics, Event Bus, and Secret-Redacting Logging."""

from collections import defaultdict
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from flowmind.types import ExecutionEvent, TaskResult, TaskStatus, WorkflowStatus


class SecretRedactingFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r'(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{8,}'), r'\1[REDACTED]'),
        (re.compile(r'(?i)(api[_-]?key[\s:=]+)[a-zA-Z0-9_\-\.]{8,}'), r'\1[REDACTED]'),
        (re.compile(r'(?i)(password[\s:=]+)[^\s,;&]+'), r'\1[REDACTED]'),
        (re.compile(r'(?i)(secret[\s:=]+)[^\s,;&]+'), r'\1[REDACTED]'),
        (re.compile(r'(?i)(private[_-]?key[\s:=]+)[^\s,;&]+'), r'\1[REDACTED]'),
        (re.compile(r'(?i)(token[\s:=]+)[a-zA-Z0-9_\-\.]{8,}'), r'\1[REDACTED]'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def get_logger(name: str = "flowmind") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listeners: Dict[str, List[Callable[[ExecutionEvent], None]]] = defaultdict(list)
        self._global_listeners: List[Callable[[ExecutionEvent], None]] = []
        self._history: List[ExecutionEvent] = []

    def subscribe(self, event_type: str, callback: Callable[[ExecutionEvent], None]) -> None:
        with self._lock:
            self._listeners[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[ExecutionEvent], None]) -> None:
        with self._lock:
            self._global_listeners.append(callback)

    def emit(self, event: ExecutionEvent) -> None:
        with self._lock:
            self._history.append(event)
            callbacks = list(self._listeners.get(event.event_type, [])) + list(self._global_listeners)

        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                get_logger().warning(f"Error in event listener for '{event.event_type}': {e}")

    def get_history(self) -> List[ExecutionEvent]:
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


class ExecutionMetrics:
    def __init__(self) -> None:
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_retries: int = 0
        self.task_metrics: Dict[str, Dict[str, Any]] = {}

    def mark_start(self) -> None:
        self.start_time = time.time()

    def mark_end(self) -> None:
        self.end_time = time.time()

    @property
    def total_duration(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return round(end - self.start_time, 4)

    def record_task_result(self, result: TaskResult) -> None:
        self.total_retries += max(0, result.attempts - 1)
        self.task_metrics[result.task_id] = {
            "name": result.task_name,
            "status": result.status.value,
            "duration": result.duration,
            "attempts": result.attempts,
            "is_idempotent": result.is_idempotent,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration_seconds": self.total_duration,
            "total_retries": self.total_retries,
            "task_metrics": self.task_metrics,
        }
