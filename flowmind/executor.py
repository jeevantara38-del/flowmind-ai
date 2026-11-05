"""FlowMind AI - Execution Engines."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from flowmind.context import ExecutionContext
from flowmind.dependencies import DependencyGraph
from flowmind.errors import (
    NonIdempotentRetryError,
    TaskCancelledError,
    TaskExecutionError,
    TaskTimeoutError,
    WorkflowCancelledError,
    WorkflowTimeoutError,
)
from flowmind.monitoring import EventBus, ExecutionMetrics, get_logger
from flowmind.persistence import Checkpoint, CheckpointStore
from flowmind.recovery import FailureClassifier
from flowmind.task import Task
from flowmind.types import ExecutionEvent, TaskResult, TaskStatus, WorkflowStatus


class BaseExecutor:
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        plugins: Optional[List[Any]] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.checkpoint_store = checkpoint_store
        self.plugins = plugins or []
        self.logger = get_logger("flowmind.executor")
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _notify_plugins(self, hook_name: str, *args, **kwargs) -> None:
        for plugin in self.plugins:
            hook = getattr(plugin, hook_name, None)
            if callable(hook):
                try:
                    hook(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(f"Plugin error in '{hook_name}': {e}")

    def execute_task_with_retries(
        self,
        task: Task,
        context: ExecutionContext,
        upstream_outputs: Dict[str, Any],
        workflow_id: str,
    ) -> TaskResult:
        task_result = TaskResult(
            task_id=task.id,
            task_name=task.name,
            is_idempotent=task.is_idempotent,
            start_time=time.time(),
        )

        if self.is_cancelled:
            task_result.status = TaskStatus.CANCELLED
            task_result.error = "Workflow was cancelled before task execution started."
            task_result.end_time = time.time()
            task_result.duration = task_result.end_time - task_result.start_time
            return task_result

        if task.condition is not None:
            try:
                should_run = task.condition(context)
            except Exception as cond_err:
                task_result.status = TaskStatus.FAILED
                task_result.error = f"Condition evaluation failed: {cond_err}"
                task_result.end_time = time.time()
                task_result.duration = task_result.end_time - task_result.start_time
                return task_result

            if not should_run:
                task_result.status = TaskStatus.SKIPPED
                task_result.end_time = time.time()
                task_result.duration = task_result.end_time - task_result.start_time
                self.event_bus.emit(ExecutionEvent(
                    event_type="TASK_SKIPPED",
                    workflow_id=workflow_id,
                    task_id=task.id,
                    message=f"Task '{task.name}' skipped by condition predicate.",
                ))
                self._notify_plugins("on_task_skipped", task, context)
                return task_result

        self.event_bus.emit(ExecutionEvent(
            event_type="TASK_STARTED",
            workflow_id=workflow_id,
            task_id=task.id,
            message=f"Task '{task.name}' started.",
        ))
        self._notify_plugins("on_task_start", task, context)

        attempt = 0
        while True:
            attempt += 1
            task_result.attempts = attempt

            if self.is_cancelled:
                task_result.status = TaskStatus.CANCELLED
                task_result.error = "Task cancelled during execution."
                break

            try:
                output = self._run_fn_with_timeout(task, context, upstream_outputs)
                task_result.status = TaskStatus.SUCCESS
                task_result.output = output
                context.set_task_output(task.id, output)

                self.event_bus.emit(ExecutionEvent(
                    event_type="TASK_SUCCESS",
                    workflow_id=workflow_id,
                    task_id=task.id,
                    message=f"Task '{task.name}' completed successfully in attempt {attempt}.",
                ))
                self._notify_plugins("on_task_complete", task, task_result, context)
                break

            except Exception as err:
                classification = FailureClassifier.classify(err)
                task_result.error_type = type(err).__name__
                task_result.error = str(err)

                should_retry, retry_reason = task.retry_policy.check_retry(
                    attempt=attempt - 1,
                    exception=err,
                    is_idempotent=task.is_idempotent,
                )

                if should_retry and not self.is_cancelled:
                    delay = task.retry_policy.calculate_delay(attempt - 1)
                    self.event_bus.emit(ExecutionEvent(
                        event_type="TASK_RETRY",
                        workflow_id=workflow_id,
                        task_id=task.id,
                        message=f"Task '{task.name}' retrying (attempt {attempt}). Delay: {delay:.2f}s",
                        payload={"attempt": attempt, "delay": delay, "error": str(err)},
                    ))
                    self._notify_plugins("on_task_retry", task, attempt, err, delay)
                    time.sleep(delay)
                else:
                    if task.fallback_fn:
                        try:
                            fallback_out = task.execute_fallback(context, err)
                            task_result.status = TaskStatus.SUCCESS
                            task_result.output = fallback_out
                            task_result.metadata["used_fallback"] = True
                            context.set_task_output(task.id, fallback_out)
                            break
                        except Exception as fb_err:
                            self.logger.error(f"Fallback failed: {fb_err}")

                    task_result.status = TaskStatus.FAILED
                    self.event_bus.emit(ExecutionEvent(
                        event_type="TASK_FAILED",
                        workflow_id=workflow_id,
                        task_id=task.id,
                        message=f"Task '{task.name}' failed: {err}",
                        payload={"error": str(err), "classification": classification.value},
                    ))
                    self._notify_plugins("on_task_failure", task, task_result, err, context)
                    break

        task_result.end_time = time.time()
        task_result.duration = task_result.end_time - task_result.start_time
        return task_result

    def _run_fn_with_timeout(
        self,
        task: Task,
        context: ExecutionContext,
        upstream_outputs: Dict[str, Any],
    ) -> Any:
        if not task.timeout:
            return task.execute(context, upstream_outputs)

        with ThreadPoolExecutor(max_workers=1) as single_worker:
            future = single_worker.submit(task.execute, context, upstream_outputs)
            try:
                return future.result(timeout=task.timeout)
            except FutureTimeoutError:
                raise TaskTimeoutError(task.id, task.timeout)


class SequentialExecutor(BaseExecutor):
    def run(
        self,
        tasks: Dict[str, Task],
        graph: DependencyGraph,
        context: ExecutionContext,
        workflow_id: str,
        workflow_name: str,
        stop_on_first_error: bool = True,
        completed_task_ids: Optional[Set[str]] = None,
        cached_outputs: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, TaskResult]:
        execution_order = graph.get_execution_order()
        results: Dict[str, TaskResult] = {}
        completed = set(completed_task_ids or set())
        start_time = time.time()

        if cached_outputs:
            for t_id, out in cached_outputs.items():
                context.set_task_output(t_id, out)

        for task_id in execution_order:
            if timeout and (time.time() - start_time) > timeout:
                raise WorkflowTimeoutError(f"Workflow '{workflow_name}' exceeded timeout of {timeout}s")

            task = tasks[task_id]

            if task_id in completed:
                results[task_id] = TaskResult(
                    task_id=task.id,
                    task_name=task.name,
                    status=TaskStatus.SUCCESS,
                    output=context.get_task_output(task_id),
                    metadata={"resumed_from_checkpoint": True},
                )
                continue

            upstream_ids = graph.get_upstream_ids(task_id)
            upstream_failed = any(
                results.get(uid) and results[uid].status in (TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED)
                for uid in upstream_ids
            )

            if upstream_failed:
                res = TaskResult(
                    task_id=task.id,
                    task_name=task.name,
                    status=TaskStatus.SKIPPED,
                    error="Skipped because upstream dependency failed or was skipped.",
                )
                results[task_id] = res
                self.event_bus.emit(ExecutionEvent(
                    event_type="TASK_SKIPPED",
                    workflow_id=workflow_id,
                    task_id=task.id,
                    message=f"Task '{task.name}' skipped due to upstream dependency status.",
                ))
                continue

            upstream_outputs = {}
            for uid in upstream_ids:
                out = context.get_task_output(uid)
                if out is not None:
                    upstream_outputs[uid] = out
                    if uid in tasks:
                        upstream_outputs[tasks[uid].name] = out

            result = self.execute_task_with_retries(task, context, upstream_outputs, workflow_id)
            results[task_id] = result

            if result.status == TaskStatus.SUCCESS:
                completed.add(task_id)
                if self.checkpoint_store:
                    self.checkpoint_store.save(Checkpoint(
                        workflow_id=workflow_id,
                        workflow_name=workflow_name,
                        completed_task_ids=list(completed),
                        task_outputs=context.get_all_task_outputs(),
                        context_data=context.to_dict(),
                    ))
            elif result.status == TaskStatus.FAILED and stop_on_first_error:
                break

        return results


class ParallelExecutor(BaseExecutor):
    def __init__(
        self,
        max_workers: int = 4,
        event_bus: Optional[EventBus] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
        plugins: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(event_bus=event_bus, checkpoint_store=checkpoint_store, plugins=plugins)
        self.max_workers = max(1, max_workers)

    def run(
        self,
        tasks: Dict[str, Task],
        graph: DependencyGraph,
        context: ExecutionContext,
        workflow_id: str,
        workflow_name: str,
        stop_on_first_error: bool = True,
        completed_task_ids: Optional[Set[str]] = None,
        cached_outputs: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, TaskResult]:
        batches = graph.get_parallel_batches()
        results: Dict[str, TaskResult] = {}
        completed = set(completed_task_ids or set())
        start_time = time.time()

        if cached_outputs:
            for t_id, out in cached_outputs.items():
                context.set_task_output(t_id, out)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for batch in batches:
                if timeout and (time.time() - start_time) > timeout:
                    raise WorkflowTimeoutError(f"Workflow '{workflow_name}' exceeded timeout of {timeout}s")

                futures_to_task: Dict[Any, Task] = {}

                for task_id in batch:
                    task = tasks[task_id]

                    if task_id in completed:
                        results[task_id] = TaskResult(
                            task_id=task.id,
                            task_name=task.name,
                            status=TaskStatus.SUCCESS,
                            output=context.get_task_output(task_id),
                            metadata={"resumed_from_checkpoint": True},
                        )
                        continue

                    upstream_ids = graph.get_upstream_ids(task_id)
                    upstream_failed = any(
                        results.get(uid) and results[uid].status in (TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED)
                        for uid in upstream_ids
                    )

                    if upstream_failed:
                        results[task_id] = TaskResult(
                            task_id=task.id,
                            task_name=task.name,
                            status=TaskStatus.SKIPPED,
                            error="Skipped because upstream dependency failed or was skipped.",
                        )
                        self.event_bus.emit(ExecutionEvent(
                            event_type="TASK_SKIPPED",
                            workflow_id=workflow_id,
                            task_id=task.id,
                            message=f"Task '{task.name}' skipped due to upstream dependency status.",
                        ))
                        continue

                    upstream_outputs = {
                        uid: context.get_task_output(uid)
                        for uid in upstream_ids
                        if context.get_task_output(uid) is not None
                    }

                    future = pool.submit(
                        self.execute_task_with_retries,
                        task,
                        context,
                        upstream_outputs,
                        workflow_id,
                    )
                    futures_to_task[future] = task

                has_failure = False
                for future in as_completed(futures_to_task):
                    task = futures_to_task[future]
                    res = future.result()
                    results[task.id] = res

                    if res.status == TaskStatus.SUCCESS:
                        completed.add(task.id)
                    elif res.status == TaskStatus.FAILED:
                        has_failure = True

                if self.checkpoint_store and completed:
                    self.checkpoint_store.save(Checkpoint(
                        workflow_id=workflow_id,
                        workflow_name=workflow_name,
                        completed_task_ids=list(completed),
                        task_outputs=context.get_all_task_outputs(),
                        context_data=context.to_dict(),
                    ))

                if has_failure and stop_on_first_error:
                    break

        return results
