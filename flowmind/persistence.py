"""FlowMind AI - State Checkpointing and Persistence."""

from dataclasses import dataclass, field
import json
import os
import tempfile
import time
from typing import Any, Dict, List, Optional, Set

from flowmind.errors import CheckpointError


@dataclass
class Checkpoint:
    workflow_id: str
    workflow_name: str
    timestamp: float = field(default_factory=time.time)
    completed_task_ids: List[str] = field(default_factory=list)
    task_outputs: Dict[str, Any] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "timestamp": self.timestamp,
            "completed_task_ids": self.completed_task_ids,
            "task_outputs": self.task_outputs,
            "context_data": self.context_data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            timestamp=data.get("timestamp", time.time()),
            completed_task_ids=data.get("completed_task_ids", []),
            task_outputs=data.get("task_outputs", {}),
            context_data=data.get("context_data", {}),
            metadata=data.get("metadata", {}),
        )


class CheckpointStore:
    def save(self, checkpoint: Checkpoint) -> None:
        raise NotImplementedError

    def load(self, workflow_id: str) -> Optional[Checkpoint]:
        raise NotImplementedError

    def delete(self, workflow_id: str) -> bool:
        raise NotImplementedError


class MemoryCheckpointStore(CheckpointStore):
    def __init__(self) -> None:
        self._checkpoints: Dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        self._checkpoints[checkpoint.workflow_id] = checkpoint

    def load(self, workflow_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(workflow_id)

    def delete(self, workflow_id: str) -> bool:
        return self._checkpoints.pop(workflow_id, None) is not None


class FileCheckpointStore(CheckpointStore):
    def __init__(self, directory: Optional[str] = None) -> None:
        self.directory = directory or tempfile.gettempdir()
        os.makedirs(self.directory, exist_ok=True)

    def _file_path(self, workflow_id: str) -> str:
        safe_id = "".join(c for c in workflow_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.directory, f"flowmind_ckpt_{safe_id}.json")

    def save(self, checkpoint: Checkpoint) -> None:
        target_path = self._file_path(checkpoint.workflow_id)
        temp_path = f"{target_path}.tmp.{os.getpid()}"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, indent=2, default=str)
            os.replace(temp_path, target_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise CheckpointError(f"Failed to save checkpoint for {checkpoint.workflow_id}: {e}")

    def load(self, workflow_id: str) -> Optional[Checkpoint]:
        target_path = self._file_path(workflow_id)
        if not os.path.exists(target_path):
            return None
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Checkpoint.from_dict(data)
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint for {workflow_id}: {e}")

    def delete(self, workflow_id: str) -> bool:
        target_path = self._file_path(workflow_id)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                return True
            except OSError:
                return False
        return False
