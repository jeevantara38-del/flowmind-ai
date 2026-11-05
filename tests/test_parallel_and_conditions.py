"""Unit tests for Parallel Execution and Conditional Branching."""

import time
import unittest
import flowmind as fm


class TestParallelAndConditions(unittest.TestCase):
    def test_parallel_execution_speed(self):
        wf = fm.Workflow("Parallel Speed Test")

        @fm.task
        def branch_1():
            time.sleep(0.08)
            return "branch1_ok"

        @fm.task
        def branch_2():
            time.sleep(0.08)
            return "branch2_ok"

        t1 = wf.add_task(branch_1)
        t2 = wf.add_task(branch_2)

        start = time.time()
        res = wf.run(executor_type="parallel", max_workers=2)
        elapsed = time.time() - start

        self.assertTrue(res.is_success)
        # In parallel, total duration should be ~0.08s, well under sequential 0.16s
        self.assertLess(elapsed, 0.15)

    def test_conditional_branching_skip(self):
        wf = fm.Workflow("Condition Test")

        @fm.task
        def calculate_score():
            return 45

        @fm.task(condition=lambda ctx: ctx.get_task_output("t_score", 0) >= 50)
        def grant_award():
            return "Award Granted"

        t_score = wf.add_task(calculate_score, task_id="t_score")
        t_award = wf.add_task(grant_award, task_id="t_award", dependencies=[t_score])

        res = wf.run()
        self.assertTrue(res.is_success)
        self.assertEqual(res.task_results[t_award.id].status, fm.TaskStatus.SKIPPED)


if __name__ == "__main__":
    unittest.main()
