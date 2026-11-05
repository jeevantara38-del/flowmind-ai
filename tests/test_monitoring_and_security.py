"""Unit tests for Monitoring, EventBus, and Secret Redaction."""

import logging
import unittest
import flowmind as fm
from flowmind.monitoring import SecretRedactingFilter


class TestMonitoringAndSecurity(unittest.TestCase):
    def test_event_bus_emission(self):
        events = []
        wf = fm.Workflow("Event Test")
        wf.event_bus.subscribe_all(lambda ev: events.append(ev.event_type))

        @fm.task
        def dummy(): return "ok"

        wf.add_task(dummy)
        wf.run()

        self.assertIn("WORKFLOW_STARTED", events)
        self.assertIn("TASK_STARTED", events)
        self.assertIn("TASK_SUCCESS", events)
        self.assertIn("WORKFLOW_FINISHED", events)

    def test_secret_redaction_in_logs(self):
        redactor = SecretRedactingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User login with password=SuperSecretPassword123 and token=eyJhbGciOiJIUzI1NiJ9",
            args=(),
            exc_info=None,
        )
        redactor.filter(record)
        self.assertNotIn("SuperSecretPassword123", record.msg)
        self.assertIn("password=[REDACTED]", record.msg)

    def test_context_secret_redaction(self):
        ctx = fm.ExecutionContext({"api_key": "sk-1234567890abcdef", "public_id": 99})
        exported = ctx.to_dict(redact_secrets=True)
        self.assertEqual(exported["variables"]["api_key"], "[REDACTED]")
        self.assertEqual(exported["variables"]["public_id"], 99)


if __name__ == "__main__":
    unittest.main()
