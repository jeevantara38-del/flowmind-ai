"""Unit tests for Workflow creation, validation, and lifecycle."""

import unittest
import flowmind as fm
from flowmind.errors import CircularDependencyError, WorkflowValidationError


class TestWorkflow(unittest.TestCase):
    def test_basic_linear_workflow(self):
        wf = fm.Workflow("Linear Pipeline")

        def step1():
            return 10

        def step2(step1):
            return step1 * 2

        t1 = wf.add_task(step1)
        t2 = wf.add_task(step2, dependencies=[t1])

        result = wf.run()
        self.assertTrue(result.is_success)
        self.assertEqual(result.get_output(t1.id), 10)
        self.assertEqual(result.get_output(t2.id), 20)

    def test_missing_dependency_raises_validation_error(self):
        wf = fm.Workflow("Invalid Graph")

        def task_a():
            return "a"

        t1 = wf.add_task(task_a, dependencies=["non_existent_task_id"])
        with self.assertRaises(WorkflowValidationError):
            wf.run()

    def test_circular_dependency_detected(self):
        wf = fm.Workflow("Cycle Graph")

        def a(): pass
        def b(): pass
        def c(): pass

        t_a = wf.add_task(a, task_id="node_a")
        t_b = wf.add_task(b, task_id="node_b", dependencies=[t_a])
        t_c = wf.add_task(c, task_id="node_c", dependencies=[t_b])
        # Form cycle: a depends on c
        t_a.depends_on(t_c)

        with self.assertRaises(CircularDependencyError) as ctx:
            wf.run()
        self.assertIn("node_a", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
