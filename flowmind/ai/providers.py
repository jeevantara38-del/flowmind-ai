"""FlowMind AI - AI Provider Adapters."""

import json
import os
from typing import Any, Dict, Optional


class BaseAIProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        raise NotImplementedError


class MockAIProvider(BaseAIProvider):
    def generate(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        prompt_lower = user_prompt.lower()

        if "explain" in prompt_lower or "failure" in prompt_lower or "error" in prompt_lower:
            return self._generate_failure_explanation(user_prompt)
        elif "recovery" in prompt_lower or "action" in prompt_lower:
            return self._generate_recovery_recommendation(user_prompt)
        elif "improve" in prompt_lower or "suggestion" in prompt_lower or "optimize" in prompt_lower:
            return self._generate_workflow_suggestion(user_prompt)
        return self._generate_execution_summary(user_prompt)

    def _generate_failure_explanation(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()
        if "zerodivision" in p:
            return {
                "summary": "Division by zero occurred during computation.",
                "possible_causes": [
                    "Denominator variable was zero due to empty input set or invalid record count.",
                    "Missing guard statement before division operation.",
                ],
                "is_transient": False,
                "recommended_action": "Add validation check: 'if count > 0: ... else: default_val'",
                "confidence_score": 0.98,
            }
        elif "timeout" in p or "connection" in p:
            return {
                "summary": "Network connection timed out or remote endpoint was unreachable.",
                "possible_causes": [
                    "Temporary network latency or firewall disruption.",
                    "Remote service is undergoing maintenance or experiencing heavy load.",
                ],
                "is_transient": True,
                "recommended_action": "Enable exponential backoff retry policy with jitter.",
                "confidence_score": 0.95,
            }
        elif "keyerror" in p or "missing" in p:
            return {
                "summary": "A required key or attribute was missing from the record payload.",
                "possible_causes": [
                    "Upstream task schema changed without updating downstream parser.",
                    "Malformed or incomplete input record passed to pipeline.",
                ],
                "is_transient": False,
                "recommended_action": "Use dict.get(key, default) or validate incoming records against schema.",
                "confidence_score": 0.92,
            }
        elif "filenotfound" in p or "path" in p:
            return {
                "summary": "Target file or directory could not be located.",
                "possible_causes": [
                    "Invalid file path provided in parameters.",
                    "Upstream file export task failed to write file to expected directory.",
                ],
                "is_transient": False,
                "recommended_action": "Verify file path existence with os.path.exists() before opening.",
                "confidence_score": 0.95,
            }
        else:
            return {
                "summary": "Task encountered an unhandled runtime exception.",
                "possible_causes": [
                    "Unexpected input format or data type mismatch.",
                    "Unhandled edge case in function logic.",
                ],
                "is_transient": False,
                "recommended_action": "Inspect stack trace and add defensive input verification.",
                "confidence_score": 0.85,
            }

    def _generate_recovery_recommendation(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()
        if "timeout" in p or "connection" in p:
            return {
                "action_type": "RETRY",
                "title": "Automated Exponential Backoff Retry",
                "description": "The failure appears transient. Retrying with jitter is recommended.",
                "requires_approval": False,
                "suggested_fix": "Increase retry count or max_delay in RetryPolicy.",
            }
        elif "idempotent" in p and "non" in p:
            return {
                "action_type": "MANUAL_FIX",
                "title": "Manual Verification Required",
                "description": "Task is non-idempotent. Retrying automatically could cause duplicate side effects.",
                "requires_approval": True,
                "suggested_fix": "Check target system state, resolve root cause, and manually resume.",
            }
        else:
            return {
                "action_type": "FIX_INPUT",
                "title": "Clean Input and Resume Checkpoint",
                "description": "Sanitize faulty records in context and resume workflow from last checkpoint.",
                "requires_approval": True,
                "suggested_fix": "Filter invalid rows before task execution.",
            }

    def _generate_workflow_suggestion(self, prompt: str) -> Dict[str, Any]:
        return {
            "summary": "Workflow executes predictably. Consider enabling parallel batches for independent tasks.",
            "parallelism_opportunities": [
                "Tasks without shared dependencies can be dispatched concurrently via ParallelExecutor."
            ],
            "reliability_improvements": [
                "Configure FileCheckpointStore to ensure crash-safe state recovery.",
                "Explicitly mark side-effect free tasks with is_idempotent=True.",
            ],
            "estimated_speedup": "Up to 2x - 4x on multi-core systems when parallelizing I/O tasks.",
        }

    def _generate_execution_summary(self, prompt: str) -> Dict[str, Any]:
        return {
            "headline": "Workflow Execution Complete",
            "status": "COMPLETED",
            "duration_seconds": 1.25,
            "total_tasks": 5,
            "failed_tasks": 0,
            "key_findings": [
                "All tasks completed within acceptable latency thresholds.",
                "Zero retry attempts required.",
            ],
        }


class OpenAIAdapter(BaseAIProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.timeout = timeout
        self.fallback = MockAIProvider()

    def generate(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return self.fallback.generate(system_prompt, user_prompt)

        try:
            import urllib.request
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content_str = data["choices"][0]["message"]["content"]
                return json.loads(content_str)
        except Exception:
            return self.fallback.generate(system_prompt, user_prompt)
