"""FlowMind AI - Task Definition and Registration."""

import inspect
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

from flowmind.context import ExecutionContext
from flowmind.retry import RetryPolicy, STANDARD_RETRY


class Task:
    def __init__(
        self,
        fn: Callable,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        dependencies: Optional[List[Union["Task", str]]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout: Optional[float] = None,
        is_idempotent: bool = True,
        condition: Optional[Callable[[ExecutionContext], bool]] = None,
        fallback_fn: Optional[Callable] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> None:
        if not callable(fn):
            raise TypeError(f"Task function must be callable, got {type(fn).__name__}")

        self.fn = fn
        self.name = name or fn.__name__
        self.id = task_id or f"{self.name}_{uuid.uuid4().hex[:8]}"
        self.retry_policy = retry_policy or STANDARD_RETRY
        self.timeout = timeout
        self.is_idempotent = is_idempotent
        self.condition = condition
        self.fallback_fn = fallback_fn
        self.params: Dict[str, Any] = params or {}
        self.tags: List[str] = tags or []
        self.description = description or (inspect.getdoc(fn) or "")

        self.dependencies: Set[str] = set()
        if dependencies:
            for dep in dependencies:
                dep_id = dep.id if isinstance(dep, Task) else str(dep)
                self.dependencies.add(dep_id)

        self._inspect_signature()

    def _inspect_signature(self) -> None:
        try:
            self._sig = inspect.signature(self.fn)
            self._accepts_context = "context" in self._sig.parameters
            self._accepts_kwargs = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in self._sig.parameters.values()
            )
        except (ValueError, TypeError):
            self._sig = None
            self._accepts_context = False
            self._accepts_kwargs = True

    def depends_on(self, *upstream: Union["Task", str]) -> "Task":
        for u in upstream:
            dep_id = u.id if isinstance(u, Task) else str(u)
            if dep_id == self.id:
                raise ValueError(f"Task '{self.id}' cannot depend on itself.")
            self.dependencies.add(dep_id)
        return self

    def execute(self, context: ExecutionContext, upstream_outputs: Optional[Dict[str, Any]] = None) -> Any:
        call_args = dict(self.params)

        if self._accepts_context:
            call_args["context"] = context

        if upstream_outputs and self._sig:
            # 1. Match by parameter name
            for param_name, param in self._sig.parameters.items():
                if param_name in ("context", "self"):
                    continue
                if param_name not in call_args and param_name in upstream_outputs:
                    call_args[param_name] = upstream_outputs[param_name]

            # 2. If single expected param and single unique upstream output, inject directly
            user_params = [
                p for p in self._sig.parameters.values()
                if p.name not in ("context", "self") and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            ]
            if len(user_params) == 1:
                single_param_name = user_params[0].name
                if single_param_name not in call_args and upstream_outputs:
                    # Pick the upstream output value
                    val = next(iter(upstream_outputs.values()))
                    call_args[single_param_name] = val

        return self.fn(**call_args) if call_args else self.fn()

    def execute_fallback(self, context: ExecutionContext, error: Exception) -> Any:
        if not self.fallback_fn:
            return None
        sig = inspect.signature(self.fallback_fn)
        args: Dict[str, Any] = {}
        if "context" in sig.parameters:
            args["context"] = context
        if "error" in sig.parameters:
            args["error"] = error
        return self.fallback_fn(**args) if args else self.fallback_fn()

    def __repr__(self) -> str:
        return f"<Task id='{self.id}' name='{self.name}' dependencies={list(self.dependencies)}>"


def task(
    _fn: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    task_id: Optional[str] = None,
    dependencies: Optional[List[Union[Task, str]]] = None,
    retries: int = 3,
    initial_delay: float = 0.05,
    max_delay: float = 10.0,
    backoff_factor: float = 1.5,
    timeout: Optional[float] = None,
    is_idempotent: bool = True,
    condition: Optional[Callable[[ExecutionContext], bool]] = None,
    fallback_fn: Optional[Callable] = None,
    params: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Union[Task, Callable[[Callable], Task]]:
    """Decorator supporting both @task and @task(...) syntax."""
    def make_task(fn: Callable) -> Task:
        policy = RetryPolicy(
            max_retries=retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
        )
        return Task(
            fn=fn,
            name=name or fn.__name__,
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

    if _fn is not None:
        # Called as bare @task
        return make_task(_fn)

    # Called as @task(...)
    return make_task
