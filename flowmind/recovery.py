"""FlowMind AI - Recovery and Fault Tolerance Engine."""

from typing import Any, Dict, List, Optional, Set, Tuple

from flowmind.persistence import Checkpoint, CheckpointStore
from flowmind.types import FailureClassification, TaskResult, TaskStatus


class FailureClassifier:
    TRANSIENT_TYPES = (
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        BrokenPipeError,
        OSError,
    )

    PERMANENT_TYPES = (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        AssertionError,
    )

    FATAL_TYPES = (
        KeyboardInterrupt,
        SystemExit,
        MemoryError,
    )

    @classmethod
    def classify(cls, error: Exception) -> FailureClassification:
        if isinstance(error, cls.FATAL_TYPES):
            return FailureClassification.FATAL
        if isinstance(error, cls.PERMANENT_TYPES):
            return FailureClassification.PERMANENT
        if isinstance(error, cls.TRANSIENT_TYPES):
            return FailureClassification.TRANSIENT

        err_name = type(error).__name__.lower()
        if any(t in err_name for t in ("timeout", "connection", "network", "ratelimit", "retry")):
            return FailureClassification.TRANSIENT
        if any(p in err_name for p in ("validation", "value", "key", "type", "syntax", "schema")):
            return FailureClassification.PERMANENT

        return FailureClassification.UNKNOWN


class RecoveryManager:
    def __init__(self, store: Optional[CheckpointStore] = None) -> None:
        self.store = store

    def prepare_resumption(
        self,
        workflow_id: str,
        all_task_ids: List[str],
    ) -> Tuple[Set[str], Dict[str, Any]]:
        if not self.store:
            return set(), {}

        checkpoint = self.store.load(workflow_id)
        if not checkpoint:
            return set(), {}

        completed = set(t for t in checkpoint.completed_task_ids if t in all_task_ids)
        outputs = {k: v for k, v in checkpoint.task_outputs.items() if k in completed}
        return completed, outputs

    def get_recovery_recommendation(self, task_result: TaskResult) -> Dict[str, Any]:
        if task_result.is_success:
            return {"action": "NONE", "message": "Task succeeded. No recovery needed."}

        if not task_result.is_idempotent:
            return {
                "action": "MANUAL_INTERVENTION_REQUIRED",
                "classification": FailureClassification.PERMANENT.value,
                "reason": (
                    f"Task '{task_result.task_name}' is marked non-idempotent. Automatic retries "
                    f"were suppressed to avoid duplicate side effects. Inspect state and re-trigger manually."
                ),
            }

        return {
            "action": "RESUME_OR_RETRY",
            "task_id": task_result.task_id,
            "attempts": task_result.attempts,
            "reason": f"Review task error: {task_result.error}. Checkpoint can be resumed once root cause is addressed.",
        }
