"""FlowMind AI - Performance Benchmarking Suite.

Measures latency overhead, DAG compilation time, parallel speedup,
and checkpoint serialization throughput.
"""

import gc
import json
import os
import sys
import time

import flowmind as fm


def benchmark_task_dispatch_overhead(num_tasks: int = 100) -> dict:
    """Measure raw engine overhead per task (running no-op tasks)."""
    wf = fm.Workflow(f"Dispatch Overhead Test ({num_tasks} tasks)")

    def noop():
        pass

    tasks = [wf.add_task(noop, name=f"noop_{i}") for i in range(num_tasks)]
    # Linear chain
    for i in range(1, num_tasks):
        tasks[i].depends_on(tasks[i - 1])

    start_time = time.perf_counter()
    result = wf.run(executor_type="sequential")
    elapsed = time.perf_counter() - start_time

    overhead_per_task_us = (elapsed / num_tasks) * 1_000_000

    return {
        "num_tasks": num_tasks,
        "total_elapsed_seconds": round(elapsed, 5),
        "overhead_per_task_microseconds": round(overhead_per_task_us, 2),
        "status": result.status.value,
    }


def benchmark_parallel_scaling(num_tasks: int = 20, task_work_s: float = 0.01) -> dict:
    """Compare Sequential vs Parallel throughput with realistic I/O sleep tasks."""
    # Sequential
    wf_seq = fm.Workflow("Seq Scaling")
    for i in range(num_tasks):
        wf_seq.add_task(lambda: time.sleep(task_work_s), name=f"work_{i}")

    start_seq = time.perf_counter()
    res_seq = wf_seq.run(executor_type="sequential")
    dur_seq = time.perf_counter() - start_seq

    # Parallel (4 workers)
    wf_par = fm.Workflow("Par Scaling")
    for i in range(num_tasks):
        wf_par.add_task(lambda: time.sleep(task_work_s), name=f"work_{i}")

    start_par = time.perf_counter()
    res_par = wf_par.run(executor_type="parallel", max_workers=4)
    dur_par = time.perf_counter() - start_par

    speedup = dur_seq / dur_par if dur_par > 0 else 1.0

    return {
        "num_tasks": num_tasks,
        "sequential_duration_s": round(dur_seq, 4),
        "parallel_duration_s": round(dur_par, 4),
        "speedup_factor": round(speedup, 2),
    }


def benchmark_checkpoint_throughput(num_records: int = 1000) -> dict:
    """Measure state persistence latency for large context datasets."""
    store = fm.MemoryCheckpointStore()
    ckpt = fm.Checkpoint(
        workflow_id="bench_ckpt_001",
        workflow_name="Benchmark Workflow",
        completed_task_ids=[f"task_{i}" for i in range(100)],
        task_outputs={f"task_{i}": {"id": i, "data": "x" * 100} for i in range(num_records)},
        context_data={"records_processed": num_records},
    )

    t0 = time.perf_counter()
    store.save(ckpt)
    save_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    loaded = store.load("bench_ckpt_001")
    load_time = time.perf_counter() - t1

    return {
        "records": num_records,
        "save_time_ms": round(save_time * 1000, 3),
        "load_time_ms": round(load_time * 1000, 3),
        "verified": loaded is not None and len(loaded.task_outputs) == num_records,
    }


def run_all_benchmarks():
    print("=" * 65)
    print(" FLOWMIND AI PERFORMANCE BENCHMARKS")
    print("=" * 65)

    print("\n1. Measuring Dispatch Overhead (100 No-op Tasks)...")
    res1 = benchmark_task_dispatch_overhead(100)
    print(f"   Total Time: {res1['total_elapsed_seconds']}s")
    print(f"   Overhead Per Task: {res1['overhead_per_task_microseconds']} µs")

    print("\n2. Measuring Parallel Speedup (20 Tasks x 10ms I/O)...")
    res2 = benchmark_parallel_scaling(20, 0.01)
    print(f"   Sequential Run: {res2['sequential_duration_s']}s")
    print(f"   Parallel (4w):  {res2['parallel_duration_s']}s")
    print(f"   Speedup Factor: {res2['speedup_factor']}x")

    print("\n3. Measuring Checkpoint Persistence (1,000 Records)...")
    res3 = benchmark_checkpoint_throughput(1000)
    print(f"   Save Latency: {res3['save_time_ms']} ms")
    print(f"   Load Latency: {res3['load_time_ms']} ms")

    results = {
        "dispatch_overhead": res1,
        "parallel_scaling": res2,
        "checkpoint_persistence": res3,
    }
    with open("benchmarks/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved benchmark results to benchmarks/results.json")


if __name__ == "__main__":
    run_all_benchmarks()
