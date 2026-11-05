"""FlowMind AI - Execution Context."""

from copy import deepcopy
import json
import threading
from typing import Any, Dict, Iterator, Optional, Set


class ExecutionContext:
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = deepcopy(initial_data) if initial_data else {}
        self._task_outputs: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}
        self._redacted_keys: Set[str] = {
            "password", "secret", "token", "api_key", "apikey",
            "access_token", "private_key", "authorization",
        }

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def set_task_output(self, task_id: str, output: Any) -> None:
        with self._lock:
            self._task_outputs[task_id] = output

    def get_task_output(self, task_id: str, default: Any = None) -> Any:
        with self._lock:
            return self._task_outputs.get(task_id, default)

    def get_all_task_outputs(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._task_outputs)

    def to_dict(self, redact_secrets: bool = True) -> Dict[str, Any]:
        with self._lock:
            exported = deepcopy(self._data)
            if redact_secrets:
                for k in list(exported.keys()):
                    if any(sensitive in k.lower() for sensitive in self._redacted_keys):
                        exported[k] = "[REDACTED]"
            return {
                "variables": exported,
                "task_outputs": {
                    k: ("[COMPLEX_OBJECT]" if not isinstance(v, (int, float, str, bool, list, dict, type(None))) else v)
                    for k, v in self._task_outputs.items()
                },
                "metadata": deepcopy(self._metadata),
            }

    def update(self, other: Dict[str, Any]) -> None:
        with self._lock:
            self._data.update(deepcopy(other))

    def copy(self) -> "ExecutionContext":
        with self._lock:
            new_ctx = ExecutionContext()
            new_ctx._data = deepcopy(self._data)
            new_ctx._task_outputs = deepcopy(self._task_outputs)
            new_ctx._metadata = deepcopy(self._metadata)
            return new_ctx

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None and not self.contains(key):
            raise KeyError(f"Key '{key}' not found in ExecutionContext")
        return val

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._data.keys()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
