"""FlowMind AI - Workflow Orchestrator."""

import time
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

from flowmind.context import ExecutionContext
from flowmind.dependencies import DependencyGraph
from flowmind.errors import WorkflowCancelledError, WorkflowError, WorkflowTimeoutError, WorkflowValidationError
from flowmind.executor import BaseExecutor, ParallelExecutor, SequentialExecutor
from flowmind.monitoring import EventBus, ExecutionMetrics, get_logger
from flowmind.persistence import CheckpointStore
from flowmind.recovery import RecoveryManager
from flowmind.reporting import WorkflowResult
from flowmind.retry import RetryPolicy, STANDARD_RETRY
from flowmind.task import Task
from flowmind.types import ExecutionEvent, TaskResult, TaskStatus, WorkflowStatus


class Workflow:
    def __init__(
        self,
        name: str = "FlowMind Workflow",
        workflow_id: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None,
        stop_on_first_error: bool = True,
        checkpoint_store: Optional[CheckpointStore] = None,
        description: Optional[str] = None,
    ) -> None:
        self.name = name
        self.id = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"
        self.timeout = timeout
        self.stop_on_first_error = stop_on_first_error
        self.checkpoint_store = checkpoint_store
        self.description = description or ""
        self.default_retry_policy = (
            RetryPolicy(max_retries=max_retries) if max_retries is not None else STANDARD_RETRY
        )

        self._tasks: Dict[str, Task] = {}
        self._graph = DependencyGraph()
        self._event_bus = EventBus()
        self._plugins: List[Any] = []
        self._context = ExecutionContext()
        self._logger = get_logger(f"flowmind.{self.name.lower().replace(' ', '_')}")
        self._current_executor: Optional[BaseExecutor] = None
        self._is_cancelled: bool = False

    @property
    def tasks(self) -> Dict[str, Task]:
        return dict(self._tasks)

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def context(self) -> ExecutionContext:
        return self._context

    def add_task(
        self,
        task_or_fn: Union[Task, Callable],
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        dependencies: Optional[List[Union[Task, str]]] = None,
        retries: Optional[int] = None,
        timeout: Optional[float] = None,
        is_idempotent: bool = True,
        condition: Optional[Callable[[ExecutionContext], bool]] = None,
        fallback_fn: Optional[Callable] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        if isinstance(task_or_fn, Task):
            task_instance = task_or_fn
            if task_id:
                task_instance.id = task_id
            if name:
                task_instance.name = name
            if dependencies:
                task_instance.depends_on(*dependencies)
        else:
            policy = (
                RetryPolicy(max_retries=retries)
                if retries is not None
                else self.default_retry_policy
            )
            task_instance = Task(
                fn=task_or_fn,
                name=name or task_or_fn.__name__,
                task_id=task_id,
                dependencies=dependencies,
                retry_policy=policy,
                timeout=timeout,
                is_idempotent=is_idempotent,
                condition=condition,
                fallback_fn=fallback_fn,
                params=params,
                tags=tags,
            )

        self._tasks[task_instance.id] = task_instance
        self._graph.add_task(task_instance)
        return task_instance

    def register_plugin(self, plugin: Any) -> None:
        self._plugins.append(plugin)

    def validate(self) -> None:
        self._graph.validate()

    def cancel(self) -> None:
        self._is_cancelled = True
        if self._current_executor:
            self._current_executor.cancel()

    def run(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        executor_type: str = "sequential",
        max_workers: int = 4,
        resume_from_checkpoint: bool = False,
    ) -> WorkflowResult:
        self.validate()

        if initial_context:
            self._context.update(initial_context)

        completed_ids: Set[str] = set()
        cached_outputs: Dict[str, Any] = {}
        if resume_from_checkpoint and self.checkpoint_store:
            recovery_mgr = RecoveryManager(self.checkpoint_store)
            completed_ids, cached_outputs = recovery_mgr.prepare_resumption(
                self.id, list(self._tasks.keys())
            )

        if executor_type.lower() == "parallel":
            executor = ParallelExecutor(
                max_workers=max_workers,
                event_bus=self._event_bus,
                checkpoint_store=self.checkpoint_store,
                plugins=self._plugins,
            )
        else:
            executor = SequentialExecutor(
                event_bus=self._event_bus,
                checkpoint_store=self.checkpoint_store,
                plugins=self._plugins,
            )
        if self._is_cancelled:
            executor.cancel()
        self._current_executor = executor

        metrics = ExecutionMetrics()
        metrics.mark_start()
        start_time = time.time()

        self._event_bus.emit(ExecutionEvent(
            event_type="WORKFLOW_STARTED",
            workflow_id=self.id,
            message=f"Workflow '{self.name}' started execution.",
            payload={"task_count": len(self._tasks), "executor": executor_type},
        ))
        for p in self._plugins:
            hook = getattr(p, "on_workflow_start", None)
            if callable(hook):
                try:
                    hook(self.id, {"name": self.name, "task_count": len(self._tasks)})
                except Exception as e:
                    self._logger.warning(f"Plugin error on workflow start: {e}")

        workflow_status = WorkflowStatus.RUNNING
        root_error: Optional[str] = None
        task_results: Dict[str, TaskResult] = {}

        try:
            task_results = executor.run(
                tasks=self._tasks,
                graph=self._graph,
                context=self._context,
                workflow_id=self.id,
                workflow_name=self.name,
                stop_on_first_error=self.stop_on_first_error,
                completed_task_ids=completed_ids,
                cached_outputs=cached_outputs,
                timeout=self.timeout,
            )
        except WorkflowTimeoutError as te:
            workflow_status = WorkflowStatus.TIMED_OUT
            root_error = str(te)
        except WorkflowCancelledError as ce:
            workflow_status = WorkflowStatus.CANCELLED
            root_error = str(ce)
        except Exception as e:
            workflow_status = WorkflowStatus.FAILED
            root_error = str(e)

        metrics.mark_end()
        end_time = time.time()

        for res in task_results.values():
            metrics.record_task_result(res)

        if workflow_status == WorkflowStatus.RUNNING:
            has_failed_task = any(r.status == TaskStatus.FAILED for r in task_results.values())
            has_cancelled = executor.is_cancelled or any(r.status == TaskStatus.CANCELLED for r in task_results.values())

            if has_cancelled:
                workflow_status = WorkflowStatus.CANCELLED
            elif has_failed_task:
                workflow_status = WorkflowStatus.FAILED
                failed_res = next(r for r in task_results.values() if r.status == TaskStatus.FAILED)
                root_error = f"Task '{failed_res.task_name}' failed: {failed_res.error}"
            else:
                workflow_status = WorkflowStatus.COMPLETED

        result = WorkflowResult(
            workflow_id=self.id,
            workflow_name=self.name,
            status=workflow_status,
            start_time=start_time,
            end_time=end_time,
            duration=round(end_time - start_time, 4),
            task_results=task_results,
            context_data=self._context.to_dict(),
            metrics=metrics,
            error=root_error,
        )

        self._event_bus.emit(ExecutionEvent(
            event_type="WORKFLOW_FINISHED",
            workflow_id=self.id,
            message=f"Workflow '{self.name}' finished with status {workflow_status.value}.",
            payload={"status": workflow_status.value, "duration": result.duration},
        ))

        for p in self._plugins:
            hook = getattr(p, "on_workflow_complete", None)
            if callable(hook):
                try:
                    hook(self.id, result)
                except Exception as e:
                    self._logger.warning(f"Plugin error on workflow complete: {e}")

        return result
