import time
import flowmind as fm

# 1. Create a custom plugin by inheriting from BasePlugin
class SlackAlertPlugin(fm.BasePlugin):
    name = "SlackAlert"

    def on_task_start(self, task, context):
        print(f"[?? Notification] Starting task: {task.name}")

    def on_task_complete(self, task, result, context):
        print(f"[? Notification] Completed: {task.name} in {result.duration:.3f}s")

    def on_task_retry(self, task, attempt, error, delay_seconds):
        print(f"[?? WARNING] {task.name} failed attempt #{attempt}. Retrying in {delay_seconds:.2f}s...")

    def on_workflow_complete(self, workflow_id, result):
        print(f"[?? FINISHED] Workflow status: {result.status.value}")

# 2. Build a workflow and register the plugin
workflow = fm.Workflow("Notification Pipeline")
workflow.register_plugin(SlackAlertPlugin())

@fm.task(name="Fetch API Data", retries=2, initial_delay=0.1)
def fetch_api():
    return {"status": 200, "payload": "OK"}

@fm.task(name="Write to Storage")
def write_storage(fetch_api):
    return f"Saved data: {fetch_api['payload']}"

t1 = workflow.add_task(fetch_api)
t2 = workflow.add_task(write_storage, dependencies=[t1])

# 3. Execute
result = workflow.run()
