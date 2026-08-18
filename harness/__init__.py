#!/usr/bin/env python3
"""Rocom Conformance Harness — L1

Implements eh-req-023 and eh-req-024:
  eh-req-023: Every CI job MUST report test count with mandatory fields
              (test_id, verdict, coverage, evidence, timestamp).
  eh-req-024: A CI job reporting success MUST have executed >0 tests.
              0 executed or only skipped = NOT_RUN, never PASS.

Usage:
  python3 -m harness.preflight --spec specs/hrrm-core-api.yaml
  python3 -m harness.reporter --output report.json
"""
import json
import os
import sys
from datetime import datetime, timezone

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "harness-report.schema.json")

def get_schema():
    """Load the harness report schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)

def create_report(test_id, verdict, test_count, passed, failed, skipped, not_run,
                  coverage=None, evidence=None, requirements=None, harness_version="1.0.0"):
    """Create a harness report with eh-req-023 mandatory fields."""
    report = {
        "report_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "harness_version": harness_version,
        "test_id": test_id,
        "verdict": verdict,
        "test_count": test_count,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "not_run": not_run,
        "coverage": coverage or {
            "total_requirements": 0,
            "tested_requirements": 0,
            "implemented_requirements": 0,
            "coverage_ratio": "0/0"
        },
        "evidence": evidence or [],
        "requirements": requirements or []
    }
    # eh-req-024 enforcement
    enforce_eh_req_024(report)
    return report

def enforce_eh_req_024(report):
    """Enforce eh-req-024: 0 tests or all skipped = NOT_RUN."""
    if report["test_count"] == 0:
        report["verdict"] = "NOT_RUN"
    elif report["passed"] == 0 and report["failed"] == 0 and report["skipped"] > 0:
        report["verdict"] = "NOT_RUN"

def validate_report(report):
    """Validate report against schema (basic check without jsonschema lib)."""
    required = ["report_version", "timestamp", "harness_version", "test_id",
                "verdict", "test_count", "passed", "failed", "skipped",
                "not_run", "coverage", "evidence", "requirements"]
    missing = [f for f in required if f not in report]
    if missing:
        return False, f"Missing mandatory fields (eh-req-023): {missing}"

    # eh-req-024
    if report["test_count"] == 0 and report["verdict"] != "NOT_RUN":
        return False, "eh-req-024 violation: test_count=0 but verdict != NOT_RUN"

    if (report["passed"] == 0 and report["failed"] == 0 and
        report["skipped"] > 0 and report["verdict"] != "NOT_RUN"):
        return False, "eh-req-024 violation: all tests skipped but verdict != NOT_RUN"

    return True, "OK"
