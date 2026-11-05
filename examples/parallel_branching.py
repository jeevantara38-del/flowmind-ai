"""FlowMind AI - Parallel Branching Example.

Demonstrates fan-out / fan-in DAG topology:
            ┌──> Process Branch A ──┐
Source Task ┤                       ├──> Aggregate Results
            └──> Process Branch B ──┘
"""

import time
import flowmind as fm


def run_parallel_branch_example():
    wf = fm.Workflow("Parallel Branching Pipeline")

    @fm.task(name="Ingest Data")
    def ingest_data() -> dict:
        return {"users": 1000, "transactions": 5400}

    @fm.task(name="Analyze Users")
    def analyze_users(ingest_data: dict) -> dict:
        time.sleep(0.05)
        return {"active_users": int(ingest_data["users"] * 0.85)}

    @fm.task(name="Analyze Transactions")
    def analyze_transactions(ingest_data: dict) -> dict:
        time.sleep(0.05)
        return {"total_volume_usd": ingest_data["transactions"] * 42.50}

    @fm.task(name="Aggregate Metrics")
    def aggregate_metrics(context: fm.ExecutionContext) -> dict:
        users = context.get_task_output("analyze_users")
        txns = context.get_task_output("analyze_transactions")
        return {
            "summary": "Analytics Complete",
            "active_users": users["active_users"] if users else 0,
            "total_volume_usd": txns["total_volume_usd"] if txns else 0.0,
        }

    t_src = wf.add_task(ingest_data, task_id="ingest_data")
    t_u = wf.add_task(analyze_users, task_id="analyze_users", dependencies=[t_src])
    t_tx = wf.add_task(analyze_transactions, task_id="analyze_transactions", dependencies=[t_src])
    t_agg = wf.add_task(aggregate_metrics, task_id="aggregate_metrics", dependencies=[t_u, t_tx])

    print("Executing in parallel...")
    result = wf.run(executor_type="parallel", max_workers=2)
    return result


if __name__ == "__main__":
    res = run_parallel_branch_example()
    print(res.summary())
    print("Aggregate Output:", res.get_output("aggregate_metrics"))
