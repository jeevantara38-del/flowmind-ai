"""FlowMind AI - Student Data Processing Automation Example.

Demonstration Workflow:
1. Load student records from simulated source.
2. Validate records against schema (GPA 0.0-4.0, positive credits, valid email).
3. Identify and isolate invalid entries.
4. Process valid records (calculate honors eligibility, letter grades, class standing).
5. Save processed results (simulated persistence).
6. Generate execution report with AI decision support.
"""

from dataclasses import asdict, dataclass
import json
import os
import sys
from typing import Any, Dict, List, Tuple

import flowmind as fm


# Simulated Transient State for demonstrating automatic retries
_RETRY_COUNTER = 0


@dataclass
class StudentRecord:
    student_id: str
    name: str
    email: str
    gpa: float
    credits: int
    major: str


# 1. Load Student Records Task
@fm.task(name="Load Student Records", retries=3, initial_delay=0.1, is_idempotent=True)
def load_student_records(context: fm.ExecutionContext) -> List[Dict[str, Any]]:
    """Simulates loading raw student records from a database or file."""
    global _RETRY_COUNTER
    simulate_error = context.get("simulate_transient_error", False)

    if simulate_error and _RETRY_COUNTER < 1:
        _RETRY_COUNTER += 1
        raise ConnectionError("Temporary connection timeout to Student Information System (SIS) database.")

    return [
        {"student_id": "STU101", "name": "Alice Johnson", "email": "alice@university.edu", "gpa": 3.92, "credits": 88, "major": "Computer Science"},
        {"student_id": "STU102", "name": "Bob Smith", "email": "bob@university.edu", "gpa": 3.45, "credits": 45, "major": "Mathematics"},
        {"student_id": "STU103", "name": "Charlie Brown", "email": "invalid-email", "gpa": -1.5, "credits": -10, "major": "Physics"}, # Invalid
        {"student_id": "STU104", "name": "Diana Prince", "email": "diana@university.edu", "gpa": 4.00, "credits": 115, "major": "Electrical Engineering"},
        {"student_id": "STU105", "name": "Evan Wright", "email": "evan@university.edu", "gpa": 2.85, "credits": 60, "major": "Economics"},
        {"student_id": "STU106", "name": "Fiona Gallagher", "email": "fiona@university.edu", "gpa": 5.20, "credits": 30, "major": "Biology"}, # Invalid GPA
    ]


# 2. Validate Records Task
@fm.task(name="Validate Records", is_idempotent=True)
def validate_records(load_student_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspects all student records, partitioning into valid and invalid records."""
    valid = []
    invalid = []

    for rec in load_student_records:
        errors = []
        if not ("@" in rec.get("email", "") and "." in rec.get("email", "")):
            errors.append("Invalid email format")
        gpa = rec.get("gpa", 0.0)
        if not (0.0 <= gpa <= 4.0):
            errors.append(f"GPA {gpa} out of bounds (0.0 - 4.0)")
        if rec.get("credits", 0) < 0:
            errors.append(f"Credits cannot be negative: {rec.get('credits')}")

        if errors:
            invalid.append({"record": rec, "errors": errors})
        else:
            valid.append(rec)

    return {"valid": valid, "invalid": invalid}


# 3. Identify and Log Invalid Entries
@fm.task(name="Identify Invalid Entries", is_idempotent=True)
def identify_invalid_entries(validate_records: Dict[str, Any], context: fm.ExecutionContext) -> List[Dict[str, Any]]:
    """Logs and routes invalid records for administrative inspection."""
    invalid = validate_records["invalid"]
    context.set("invalid_count", len(invalid))
    context.set("invalid_entries", invalid)
    return invalid


# 4. Process Valid Records
@fm.task(name="Process Valid Records", is_idempotent=True)
def process_valid_records(validate_records: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculates standing, honors status, and Dean's List eligibility for valid students."""
    processed = []
    for s in validate_records["valid"]:
        gpa = s["gpa"]
        credits = s["credits"]

        if credits >= 90:
            standing = "Senior"
        elif credits >= 60:
            standing = "Junior"
        elif credits >= 30:
            standing = "Sophomore"
        else:
            standing = "Freshman"

        is_deans_list = gpa >= 3.75
        honors = "Summa Cum Laude" if gpa >= 3.9 else ("Magna Cum Laude" if gpa >= 3.7 else "None")

        processed.append({
            "student_id": s["student_id"],
            "name": s["name"],
            "major": s["major"],
            "gpa": gpa,
            "standing": standing,
            "deans_list": is_deans_list,
            "honors": honors,
        })
    return processed


# 5. Save Processed Results
@fm.task(name="Save Results", is_idempotent=True)
def save_results(process_valid_records: List[Dict[str, Any]], context: fm.ExecutionContext) -> Dict[str, Any]:
    """Persists processed student evaluations to context storage."""
    context.set("processed_students", process_valid_records)
    return {
        "status": "SAVED",
        "saved_count": len(process_valid_records),
    }


def build_student_pipeline(simulate_transient_error: bool = False) -> Tuple[fm.Workflow, fm.TaskResult]:
    workflow = fm.Workflow(
        name="Student Data Processing Automation",
        description="End-to-end student records intake, validation, enrichment, and reporting pipeline.",
    )

    # Register tasks
    t1 = workflow.add_task(load_student_records)
    t2 = workflow.add_task(validate_records, dependencies=[t1])
    t3 = workflow.add_task(identify_invalid_entries, dependencies=[t2])
    t4 = workflow.add_task(process_valid_records, dependencies=[t2])
    t5 = workflow.add_task(save_results, dependencies=[t4])

    return workflow


def run_student_pipeline(simulate_transient_error: bool = False) -> fm.WorkflowResult:
    global _RETRY_COUNTER
    _RETRY_COUNTER = 0

    workflow = build_student_pipeline(simulate_transient_error=simulate_transient_error)
    result = workflow.run(initial_context={"simulate_transient_error": simulate_transient_error})
    return result


if __name__ == "__main__":
    print("=" * 70)
    print(" FlowMind AI Demonstration: Student Data Processing Automation")
    print("=" * 70)

    # 1. Run with transient failure to demonstrate automatic retries
    print("\n▶ SCENARIO 1: Transient Database Failure with Automated Retry")
    res1 = run_student_pipeline(simulate_transient_error=True)
    print(res1.summary())

    # 2. Run AI Decision Support Analysis
    print("\n▶ SCENARIO 2: AI Decision Support Analysis")
    advisor = fm.AIAdvisor()
    summary = advisor.summarize_execution(res1)
    print(f"Executive Headline: {summary.headline}")
    print(f"Key Findings:       {summary.key_findings}")

    suggestions = advisor.suggest_workflow_improvements(res1)
    print(f"AI Optimization:    {suggestions.summary}")
    print(f"Speedup Potential:  {suggestions.estimated_speedup}")
