"""Unit tests for AI Decision Support and Safe Recommendations."""

import unittest
import flowmind as fm


class TestAIAdvisor(unittest.TestCase):
    def test_mock_ai_failure_explanation(self):
        advisor = fm.AIAdvisor()
        fake_task_result = fm.TaskResult(
            task_id="t_calc",
            task_name="Calculate Ratio",
            status=fm.TaskStatus.FAILED,
            error="division by zero",
            error_type="ZeroDivisionError",
            is_idempotent=True,
        )

        explanation = advisor.explain_failure(fake_task_result)
        self.assertEqual(explanation.task_name, "Calculate Ratio")
        self.assertIn("division by zero", explanation.summary.lower())
        self.assertFalse(explanation.is_transient)

    def test_safe_recovery_recommendation_requires_approval(self):
        advisor = fm.AIAdvisor()
        fake_task_result = fm.TaskResult(
            task_id="t_write",
            task_name="Write Database",
            status=fm.TaskStatus.FAILED,
            error="Row conflict",
            is_idempotent=False,
        )

        rec = advisor.recommend_recovery(fake_task_result)
        self.assertTrue(rec.requires_approval, "Non-idempotent or state modifying recoveries must require approval")


if __name__ == "__main__":
    unittest.main()
