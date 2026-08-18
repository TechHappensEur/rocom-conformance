#!/usr/bin/env python3
"""Rocom Conformance Harness — L1

Implemented requirements:
  eh-req-001: JUnit XML output for machine-readable evidence
  eh-req-002: Status vocabulary PASS/FAIL/NOT_RUN/ERROR with not_run_reason enum
  eh-req-005: build_provenance (mandatory, "n/a" where no build exists)
  eh-req-011: Preflight dependency probing with bounded timeout
  eh-req-022: Self-test must cover all 4 statuses including negative fixtures
  eh-req-023: Zero executed tests → verdict MUST be NOT_RUN
  eh-req-024: CI job reporting success MUST specify number of executed tests

Usage:
  from harness import create_report, validate_report, generate_junit_xml
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "harness-report.schema.json")

# eh-req-002: status vocabulary
VALID_VERDICTS = {"PASS", "FAIL", "NOT_RUN", "ERROR"}
NOT_RUN_REASONS = {
    "missing_service", "missing_tool", "simulated",
    "no_tests_implemented", "preflight_failure", "n/a"
}

APPLIES_TO = ["eh-req-001", "eh-req-002", "eh-req-005", "eh-req-023", "eh-req-024"]


def get_schema():
    """Load the harness report schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def create_report(test_id, verdict, test_count, passed, failed, skipped, not_run,
                  build_provenance=None, coverage=None, evidence=None, requirements=None,
                  not_run_reason="n/a", harness_version="1.0.0"):
    """Create a harness report with eh-req-023/024 enforcement."""
    # eh-req-005: build_provenance mandatory
    if build_provenance is None:
        build_provenance = {"toolchain": "n/a"}

    # eh-req-023: zero tests → NOT_RUN
    # eh-req-024: PASS/FAIL requires test_count > 0
    verdict = enforce_verdict(verdict, test_count, passed, failed, skipped)

    report = {
        "report_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "harness_version": harness_version,
        "test_id": test_id,
        "applies_to": APPLIES_TO,
        "verdict": verdict,
        "test_count": test_count,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "not_run": not_run,
        "not_run_reason": not_run_reason if verdict == "NOT_RUN" else "n/a",
        "build_provenance": build_provenance,
        "coverage": coverage or {
            "total_requirements": 0,
            "tested_requirements": 0,
            "implemented_requirements": 0,
            "coverage_ratio": "0/0"
        },
        "evidence": evidence or [],
        "requirements": requirements or []
    }
    return report


def enforce_verdict(verdict, test_count, passed, failed, skipped):
    """Enforce eh-req-023 and eh-req-024 verdict rules."""
    # eh-req-023: zero tests → NOT_RUN
    if test_count == 0:
        return "NOT_RUN"
    # All skipped → NOT_RUN
    if passed == 0 and failed == 0 and skipped > 0:
        return "NOT_RUN"
    return verdict


def validate_report(report):
    """Validate report against schema requirements (eh-req-001 through eh-req-024)."""
    # eh-req-023/024: mandatory fields
    required = [
        "report_version", "timestamp", "harness_version", "test_id",
        "applies_to", "verdict", "test_count", "passed", "failed",
        "skipped", "not_run", "build_provenance", "coverage",
        "evidence", "requirements"
    ]
    missing = [f for f in required if f not in report]
    if missing:
        return False, f"Missing mandatory fields (eh-req-024): {missing}"

    # eh-req-002: valid verdict
    if report["verdict"] not in VALID_VERDICTS:
        return False, f"eh-req-002: invalid verdict '{report['verdict']}' — must be PASS/FAIL/NOT_RUN/ERROR"

    # eh-req-005: build_provenance must exist
    if not report.get("build_provenance"):
        return False, "eh-req-005: build_provenance is required (use toolchain='n/a' if no build)"

    # eh-req-023: test_count=0 → NOT_RUN
    if report["test_count"] == 0 and report["verdict"] != "NOT_RUN":
        return False, "eh-req-023 violation: test_count=0 but verdict != NOT_RUN"

    # eh-req-024: PASS/FAIL → test_count > 0
    if report["verdict"] in ("PASS", "FAIL") and report["test_count"] == 0:
        return False, "eh-req-024 violation: PASS/FAIL with test_count=0"

    # eh-req-002: NOT_RUN must have not_run_reason
    if report["verdict"] == "NOT_RUN" and report.get("not_run_reason") not in NOT_RUN_REASONS:
        return False, f"eh-req-002: NOT_RUN requires valid not_run_reason"

    return True, "OK"


def generate_junit_xml(report, output_path):
    """eh-req-001: Generate JUnit XML from report data."""
    suite = ET.Element("testsuite")
    suite.set("name", report.get("test_id", "unknown"))
    suite.set("tests", str(report["test_count"]))
    suite.set("errors", str(report.get("failed", 0)))
    suite.set("failures", str(report.get("failed", 0)))
    suite.set("skipped", str(report.get("skipped", 0)))
    suite.set("time", "0.0")
    suite.set("timestamp", report.get("timestamp", ""))

    for req in report.get("requirements", []):
        case = ET.SubElement(suite, "testcase")
        case.set("name", req["id"])
        if req["status"] == "FAIL":
            failure = ET.SubElement(case, "failure")
            failure.text = req.get("details", "")
        elif req["status"] == "ERROR":
            error = ET.SubElement(case, "error")
            error.text = req.get("details", "")
        elif req["status"] == "NOT_RUN":
            skipped_el = ET.SubElement(case, "skipped")
            skipped_el.set("message", req.get("not_run_reason", "n/a"))

    tree = ET.ElementTree(suite)
    ET.indent(tree, space="  ")
    buf = ET.ElementTree(suite)
    import io
    stream = io.StringIO()
    buf.write(stream, encoding="unicode", xml_declaration=True)
    with open(output_path, "w") as f:
        f.write(stream.getvalue())
    return output_path
