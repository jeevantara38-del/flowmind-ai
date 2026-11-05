# FlowMind AI Public API Reference

## Workflow
- `Workflow(name, max_retries, timeout, stop_on_first_error, checkpoint_store)`
- `add_task(task_or_fn, dependencies, retries, timeout, is_idempotent, condition, fallback_fn)`
- `run(initial_context, executor_type="sequential"|"parallel", max_workers=4, resume_from_checkpoint=False)`
- `cancel()`
- `validate()`

## Task
- `@task(name, retries, initial_delay, max_delay, backoff_factor, timeout, is_idempotent, condition, fallback_fn)`
- `task.depends_on(*upstream_tasks)`

## AI Advisor
- `explain_failure(task_result)`
- `recommend_recovery(task_result)`
- `suggest_workflow_improvements(workflow_result)`
- `summarize_execution(workflow_result)`
