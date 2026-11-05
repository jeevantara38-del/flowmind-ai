"""Unit tests for Advanced Features: timeouts, cancellation, plugins, and non-retryables."""

import time
import unittest
import flowmind as fm
from flowmind.errors import TaskTimeoutError, WorkflowTimeoutError


class TestAdvancedFeatures(unittest.TestCase):
    def test_task_timeout(self):
        wf = fm.Workflow("Timeout WF")

        @fm.task(timeout=0.05, retries=0)
        def slow_task():
            time.sleep(0.2)
            return "too_late"

        t = wf.add_task(slow_task)
        res = wf.run()
        self.assertTrue(res.is_failed)
        self.assertEqual(res.task_results[t.id].error_type, "TaskTimeoutError")

    def test_workflow_cancellation(self):
        wf = fm.Workflow("Cancel WF")

        @fm.task
        def step1():
            return "done"

        @fm.task
        def step2():
            return "should_not_run"

        t1 = wf.add_task(step1)
        t2 = wf.add_task(step2, dependencies=[t1])

        # Cancel before run finishes
        wf.cancel()
        res = wf.run()
        self.assertEqual(res.status, fm.WorkflowStatus.CANCELLED)

    def test_audit_log_plugin(self):
        audit = fm.AuditLogPlugin()
        wf = fm.Workflow("Audit Test")
        wf.register_plugin(audit)

        @fm.task
        def sample():
            return 42

        wf.add_task(sample)
        res = wf.run()

        self.assertTrue(res.is_success)
        actions = [entry["action"] for entry in audit.entries]
        self.assertIn("WORKFLOW_START", actions)
        self.assertIn("TASK_START", actions)
        self.assertIn("TASK_COMPLETE", actions)
        self.assertIn("WORKFLOW_COMPLETE", actions)

    def test_non_retryable_exception_fails_immediately(self):
        attempts = 0

        @fm.task(retries=3, initial_delay=0.01)
        def type_error_task():
            nonlocal attempts
            attempts += 1
            raise TypeError("Fatal programming mistake")

        # Configure policy with TypeError as non-retryable
        policy = fm.RetryPolicy(max_retries=3, non_retryable_exceptions=(TypeError,))
        wf = fm.Workflow("Type Error WF")
        t = wf.add_task(type_error_task)
        t.retry_policy = policy

        res = wf.run()
        self.assertTrue(res.is_failed)
        self.assertEqual(attempts, 1, "Non-retryable exception must fail on attempt 1 without retries")


if __name__ == "__main__":
    unittest.main()
