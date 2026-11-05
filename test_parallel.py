import time
import flowmind as fm

@fm.task(name="Ingest Data")
def ingest_data():
    return {"users": 1000, "sales": 45000}

@fm.task(name="Analyze Users")
def analyze_users(ingest_data):
    time.sleep(1.0)  # Simulates 1s of work
    return f"Active users: {int(ingest_data['users'] * 0.8)}"

@fm.task(name="Analyze Sales")
def analyze_sales(ingest_data):
    time.sleep(1.0)  # Simulates 1s of work
    return f"Avg order: ${ingest_data['sales'] / ingest_data['users']:.2f}"

@fm.task(name="Merge Insights")
def merge_insights(context: fm.ExecutionContext):
    u = context.get_task_output("analyze_users")
    s = context.get_task_output("analyze_sales")
    return {"user_metric": u, "sales_metric": s}

wf = fm.Workflow("Parallel Dashboard Workflow")
t_in = wf.add_task(ingest_data)
t_u = wf.add_task(analyze_users, task_id="analyze_users", dependencies=[t_in])
t_s = wf.add_task(analyze_sales, task_id="analyze_sales", dependencies=[t_in])
t_m = wf.add_task(merge_insights, dependencies=[t_u, t_s])

# Notice executor_type="parallel"
result = wf.run(executor_type="parallel", max_workers=2)

print(result.summary())
print("Combined Insights:", result.get_output(t_m.id))
