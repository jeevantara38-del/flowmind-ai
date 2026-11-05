"""Unit tests for Retry Policies, Backoff Jitter, and Idempotency Guard."""

import unittest
import flowmind as fm


class TestRetryAndIdempotency(unittest.TestCase):
    def test_successful_retry_after_transient_failure(self):
        attempts = 0

        @fm.task(retries=3, initial_delay=0.01, is_idempotent=True)
        def flaky_service():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionResetError("Connection dropped by peer")
            return "recovered"

        wf = fm.Workflow("Retry Test")
        t = wf.add_task(flaky_service)
        res = wf.run()

        self.assertTrue(res.is_success)
        self.assertEqual(attempts, 3)
        self.assertEqual(res.task_results[t.id].attempts, 3)

    def test_non_idempotent_task_is_never_retried(self):
        attempts = 0

        @fm.task(retries=5, initial_delay=0.01, is_idempotent=False)
        def charge_credit_card():
            nonlocal attempts
            attempts += 1
            raise RuntimeError("Payment gateway timeout")

        wf = fm.Workflow("Payment Workflow")
        t = wf.add_task(charge_credit_card)
        res = wf.run()

        self.assertTrue(res.is_failed)
        self.assertEqual(attempts, 1, "Non-idempotent task must not be retried automatically")

    def test_custom_fallback_callable_on_exhausted_retries(self):
        @fm.task(retries=2, initial_delay=0.01, fallback_fn=lambda: "fallback_cached_value")
        def unstable_fetch():
            raise TimeoutError("Dead upstream")

        wf = fm.Workflow("Fallback Test")
        t = wf.add_task(unstable_fetch)
        res = wf.run()

        self.assertTrue(res.is_success)
        self.assertEqual(res.get_output(t.id), "fallback_cached_value")


if __name__ == "__main__":
    unittest.main()
