"""FlowMind AI - Interactive Demonstration User Interface.

Supports both:
1. Streamlit execution: `streamlit run app.py`
2. Standalone web dashboard execution: `python3 app.py`
"""

import json
import os
import sys
import time

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

import flowmind as fm
from examples.student_data_pipeline import build_student_pipeline


def render_streamlit_app():
    st.set_page_config(page_title="FlowMind AI Studio", layout="wide", page_icon="⚡")
    st.title("⚡ FlowMind AI - Workflow Orchestration & Decision Studio")
    st.markdown("Visual interface for creating, executing, monitoring, and diagnosing automation workflows.")

    st.sidebar.header("Workflow Configuration")
    executor_choice = st.sidebar.selectbox("Executor Engine", ["Sequential", "Parallel (4 Workers)"])
    simulate_fail = st.sidebar.checkbox("Simulate Transient Failure (Test Retries)", value=False)
    max_retries = st.sidebar.slider("Max Retries", 0, 5, 3)

    st.subheader("1. Workflow Blueprint: Student Data Processing Automation")
    st.info("Pipeline Stages: 1. Load Records ➔ 2. Validate Records ➔ 3. Identify Invalid Entries ➔ 4. Process Valid Records ➔ 5. Save Results")

    if st.button("🚀 Run Workflow Now", type="primary"):
        wf = build_student_pipeline(simulate_transient_error=simulate_fail)
        executor_type = "parallel" if "Parallel" in executor_choice else "sequential"

        with st.spinner("Executing workflow DAG..."):
            res = wf.run(
                initial_context={"simulate_transient_error": simulate_fail},
                executor_type=executor_type,
            )

        st.success(f"Workflow Finished! Status: {res.status.value} (Duration: {res.duration:.4f}s)")

        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tasks", len(res.task_results))
        col2.metric("Succeeded", len(res.successful_tasks()))
        col3.metric("Failed", len(res.failed_tasks()))
        col4.metric("Retries Triggered", res.metrics.total_retries if res.metrics else 0)

        # Task Execution Table
        st.subheader("2. Task Execution History")
        table_data = []
        for tid, tr in res.task_results.items():
            table_data.append({
                "Task Name": tr.task_name,
                "Status": tr.status.value,
                "Attempts": tr.attempts,
                "Duration (s)": round(tr.duration, 4),
                "Error": tr.error or "None",
            })
        st.table(table_data)

        # AI Decision Support Section
        st.subheader("3. AI Decision Support & Operational Insights")
        advisor = fm.AIAdvisor()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 📋 Executive Summary")
            summary = advisor.summarize_execution(res)
            st.write(f"**Headline:** {summary.headline}")
            for finding in summary.key_findings:
                st.write(f"- {finding}")

        with col_b:
            st.markdown("### 💡 AI Recovery & Optimization Recommendations")
            if res.failed_tasks():
                failed_task = res.failed_tasks()[0]
                rec = advisor.recommend_recovery(failed_task)
                st.warning(f"**Action:** {rec.action_type} - {rec.title}")
                st.write(f"**Description:** {rec.description}")
            else:
                sug = advisor.suggest_workflow_improvements(res)
                st.write(f"**Optimization:** {sug.summary}")
                for opp in sug.parallelism_opportunities:
                    st.write(f"- {opp}")


def render_standalone_cli():
    print("=" * 70)
    print(" FlowMind AI Studio - Demonstration Interface")
    print("=" * 70)
    print("Streamlit is not installed in this environment.")
    print("Running headless interactive demonstration using FlowMind core:\n")

    wf = build_student_pipeline(simulate_transient_error=True)
    res = wf.run(initial_context={"simulate_transient_error": True}, executor_type="parallel")

    print(res.summary())

    advisor = fm.AIAdvisor()
    print("\n[AI Advisor Summary]")
    print(json.dumps(advisor.summarize_execution(res).to_dict(), indent=2))
    print("\nTo launch Streamlit UI on your machine: streamlit run app.py")


if __name__ == "__main__":
    if HAS_STREAMLIT:
        render_streamlit_app()
    else:
        render_standalone_cli()
