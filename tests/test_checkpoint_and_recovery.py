"""Unit tests for Checkpoint persistence and resume recovery."""

import unittest
import flowmind as fm


class TestCheckpointAndRecovery(unittest.TestCase):
    def test_checkpoint_resumption(self):
        store = fm.MemoryCheckpointStore()
        step1_calls = 0

        def run_step1():
            nonlocal step1_calls
            step1_calls += 1
            return "result_step_1"

        fail_step2 = True
        def run_step2():
            if fail_step2:
                raise ValueError("Crash on step 2")
            return "result_step_2"

        def make_wf():
            wf = fm.Workflow("Resumption WF", checkpoint_store=store, stop_on_first_error=True)
            t1 = wf.add_task(run_step1, task_id="step1")
            t2 = wf.add_task(run_step2, task_id="step2", dependencies=[t1])
            return wf, t1, t2

        wf1, t1, t2 = make_wf()
        res1 = wf1.run()
        self.assertTrue(res1.is_failed)
        self.assertEqual(step1_calls, 1)

        # Resume from checkpoint after fixing failure
        fail_step2 = False
        wf2, _, _ = make_wf()
        wf2.id = wf1.id  # Same ID to load checkpoint
        res2 = wf2.run(resume_from_checkpoint=True)

        self.assertTrue(res2.is_success)
        # step1 should NOT have been re-executed!
        self.assertEqual(step1_calls, 1, "Completed task must not be re-run when resuming from checkpoint")
        self.assertEqual(res2.get_output("step1"), "result_step_1")
        self.assertEqual(res2.get_output("step2"), "result_step_2")


if __name__ == "__main__":
    unittest.main()
