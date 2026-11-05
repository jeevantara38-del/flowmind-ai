# Changelog

All notable changes to **FlowMind AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-04

### Added
- Core Directed Acyclic Graph (DAG) dependency resolution engine using Kahn's algorithm.
- `Task` model and `@fm.task` decorator with parameter inspection and automatic output injection.
- Dual execution engines: `SequentialExecutor` and bounded `ParallelExecutor`.
- Resilient retry policy with exponential backoff, full jitter, and strict idempotency checks.
- Checkpoint persistence and crash recovery (`MemoryCheckpointStore` and atomic `FileCheckpointStore`).
- Event-driven monitoring bus (`EventBus`) and secret-redacting logger.
- Extensible lifecycle hook architecture with `BasePlugin`.
- Optional zero-dependency `AIAdvisor` with deterministic offline fallbacks and OpenAI adapters.
- Command-line interface (`flowmind`) for running demos and inspecting checkpoints.
- Demonstration project: Student Data Processing Automation.
- Comprehensive test suite covering 19 unit and integration test scenarios.
- Performance benchmark suite showing sub-30µs dispatch latency and 3.5x parallel speedup.
