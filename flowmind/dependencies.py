"""FlowMind AI - Dependency Graph and DAG Engine."""

from collections import defaultdict, deque
from typing import Dict, List, Set

from flowmind.errors import CircularDependencyError, WorkflowValidationError
from flowmind.task import Task


class DependencyGraph:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._downstream: Dict[str, Set[str]] = defaultdict(set)
        self._upstream: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, task: Task) -> None:
        if task.id in self._tasks:
            raise WorkflowValidationError(f"Task with ID '{task.id}' is already registered in the workflow.")

        self._tasks[task.id] = task
        if task.id not in self._upstream:
            self._upstream[task.id] = set()
        if task.id not in self._downstream:
            self._downstream[task.id] = set()

        for dep_id in task.dependencies:
            self._upstream[task.id].add(dep_id)
            self._downstream[dep_id].add(task.id)

    def validate(self) -> None:
        # Synchronize edges from all tasks
        for task_id, task in self._tasks.items():
            for dep_id in task.dependencies:
                self._upstream[task_id].add(dep_id)
                self._downstream[dep_id].add(task_id)

        for task_id, deps in self._upstream.items():
            for dep_id in deps:
                if dep_id not in self._tasks:
                    raise WorkflowValidationError(
                        f"Task '{task_id}' depends on '{dep_id}', but '{dep_id}' is not "
                        f"registered in the workflow. Available tasks: {list(self._tasks.keys())}"
                    )
        self.get_execution_order()

    def get_execution_order(self) -> List[str]:
        in_degree: Dict[str, int] = {
            task_id: len(self._upstream[task_id])
            for task_id in self._tasks
        }
        zero_in_degree = deque([task_id for task_id, deg in in_degree.items() if deg == 0])
        ordered_ids: List[str] = []

        while zero_in_degree:
            curr = zero_in_degree.popleft()
            ordered_ids.append(curr)

            for downstream_id in self._downstream[curr]:
                in_degree[downstream_id] -= 1
                if in_degree[downstream_id] == 0:
                    zero_in_degree.append(downstream_id)

        if len(ordered_ids) != len(self._tasks):
            unresolved = [t for t, deg in in_degree.items() if deg > 0]
            cycle_path = self._find_cycle_path(unresolved)
            raise CircularDependencyError(cycle_path)

        return ordered_ids

    def get_parallel_batches(self) -> List[List[str]]:
        in_degree = {task_id: len(self._upstream[task_id]) for task_id in self._tasks}
        batches: List[List[str]] = []
        remaining = set(self._tasks.keys())

        while remaining:
            ready_batch = [t for t in remaining if in_degree[t] == 0]
            if not ready_batch:
                cycle_path = self._find_cycle_path(list(remaining))
                raise CircularDependencyError(cycle_path)

            batches.append(ready_batch)
            for t in ready_batch:
                remaining.remove(t)
                for downstream in self._downstream[t]:
                    if downstream in remaining:
                        in_degree[downstream] -= 1

        return batches

    def _find_cycle_path(self, candidate_nodes: List[str]) -> List[str]:
        visited: Dict[str, int] = {}
        parent: Dict[str, str] = {}
        path: List[str] = []

        def dfs(node: str) -> bool:
            visited[node] = 1
            for nxt in self._downstream.get(node, set()):
                if nxt not in candidate_nodes:
                    continue
                if visited.get(nxt, 0) == 1:
                    curr = node
                    path.append(nxt)
                    while curr != nxt:
                        path.append(curr)
                        curr = parent.get(curr, nxt)
                    path.append(nxt)
                    path.reverse()
                    return True
                if visited.get(nxt, 0) == 0:
                    parent[nxt] = node
                    if dfs(nxt):
                        return True
            visited[node] = 2
            return False

        for node in candidate_nodes:
            if visited.get(node, 0) == 0:
                if dfs(node):
                    return path

        return candidate_nodes

    def get_upstream_ids(self, task_id: str) -> Set[str]:
        return set(self._upstream.get(task_id, set()))

    def get_downstream_ids(self, task_id: str) -> Set[str]:
        return set(self._downstream.get(task_id, set()))

    def __len__(self) -> int:
        return len(self._tasks)
