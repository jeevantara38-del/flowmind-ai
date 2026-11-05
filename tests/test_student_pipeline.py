"""Integration test for the Student Data Processing demonstration project."""

import unittest
from examples.student_data_pipeline import run_student_pipeline


class TestStudentPipelineIntegration(unittest.TestCase):
    def test_student_pipeline_with_retry_simulation(self):
        res = run_student_pipeline(simulate_transient_error=True)
        self.assertTrue(res.is_success)
        self.assertEqual(len(res.task_results), 5)

        # Check saved students in context
        saved = res.context_data.get("variables", {}).get("processed_students")
        self.assertIsNotNone(saved)
        self.assertGreater(len(saved), 0)


if __name__ == "__main__":
    unittest.main()
