"""FlowMind AI - Command Line Interface (CLI)."""

import argparse
import json
import os
import sys

import flowmind as fm


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="flowmind",
        description="FlowMind AI - Workflow Automation & Orchestration Engine",
    )
    parser.add_argument("--version", "-v", action="version", version=f"flowmind {fm.__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    demo_parser = subparsers.add_parser("run-demo", help="Run the Student Data Pipeline demo workflow")
    demo_parser.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Simulate a transient failure to demonstrate automatic retries and AI analysis",
    )

    ckpt_parser = subparsers.add_parser("inspect-checkpoint", help="Inspect a stored checkpoint file")
    ckpt_parser.add_argument("file_path", help="Path to the checkpoint JSON file")

    args = parser.parse_args()

    if args.command == "run-demo":
        from examples.student_data_pipeline import run_student_pipeline
        print(f"🚀 Running Student Data Processing Pipeline (simulate_failure={args.simulate_failure})...\n")
        result = run_student_pipeline(simulate_transient_error=args.simulate_failure)
        print(result.summary())
        sys.exit(0 if result.is_success else 1)

    elif args.command == "inspect-checkpoint":
        if not os.path.exists(args.file_path):
            print(f"❌ Error: File not found: {args.file_path}")
            sys.exit(1)
        with open(args.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Checkpoint for workflow: {data.get('workflow_name')} (ID: {data.get('workflow_id')})")
        print(f"Completed Tasks: {data.get('completed_task_ids')}")
        print(f"Timestamp: {data.get('timestamp')}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
