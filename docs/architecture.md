# FlowMind AI Architecture Guide

## 1. System Overview
FlowMind AI uses an event-driven, decoupled pipeline architecture:
- **Graph Layer**: Topological ordering via Kahn's algorithm.
- **Execution Layer**: Sequential and bounded thread-pool parallel executors.
- **State Layer**: Thread-safe `ExecutionContext` and atomic `CheckpointStore`.
- **Reliability Layer**: Exponential backoff with AWS-style full jitter and idempotency checking.
- **Advisor Layer**: Zero-dependency structured failure classification and recovery recommendations.
