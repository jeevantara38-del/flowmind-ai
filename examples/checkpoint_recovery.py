"""FlowMind AI - Checkpoint and Interruption Recovery Example.

Demonstrates:
1. Workflow running first 2 tasks, then failing on task 3.
2. Saving checkpoint of completed work.
3. Resuming execution from checkpoint without repeating completed tasks.
"""

import flowmind as fm

_SIMULATE_FAIL = True

def run_checkpoint_recovery_demo():
    global _SIMULATE_FAIL
    store = fm.MemoryCheckpointStore()

    def make_workflow():
        wf = fm.Workflow("Crash Safe Workflow", checkpoint_store=store, stop_on_first_error=True)

        @fm.task(name="Step 1: Download Assets")
        def step1():
            return "assets_v1.tar"

        @fm.task(name="Step 2: Unpack and Verify")
        def step2():
            return "verified_ok"

        @fm.task(name="Step 3: Process Heavy Model")
        def step3():
            if _SIMULATE_FAIL:
                raise RuntimeError("Unexpected machine crash or power cut!")
            return "model_trained"

        @fm.task(name="Step 4: Publish Output")
        def step4():
            return "published_successfully"

        t1 = wf.add_task(step1, task_id="step1")
        t2 = wf.add_task(step2, task_id="step2", dependencies=[t1])
        t3 = wf.add_task(step3, task_id="step3", dependencies=[t2])
        t4 = wf.add_task(step4, task_id="step4", dependencies=[t3])
        return wf

    # 1. Run until failure
    print("▶ Phase 1: Running workflow that crashes on Step 3...")
    wf1 = make_workflow()
    res1 = wf1.run()
    print(f"Run 1 Status: {res1.status.value}")

    # Inspect AI advice
    advisor = fm.AIAdvisor()
    failed_task = res1.failed_tasks()[0]
    rec = advisor.recommend_recovery(failed_task)
    print(f"AI Recovery Advice: {rec.title} -> {rec.description}")

    # 2. Fix the error and resume from checkpoint!
    print("\n▶ Phase 2: Resolving root issue and resuming from checkpoint...")
    _SIMULATE_FAIL = False
    wf2 = make_workflow()
    wf2.id = wf1.id  # Same workflow ID to load checkpoint
    res2 = wf2.run(resume_from_checkpoint=True)
    print(f"Run 2 Status: {res2.status.value}")
    return res2


if __name__ == "__main__":
    res = run_checkpoint_recovery_demo()
    print(res.summary())
