#!/usr/bin/env python3
"""Rocom Conformance Harness — L1

Implemented requirements:
  eh-req-001: JUnit XML output for machine-readable evidence
  eh-req-002: Status vocabulary PASS/FAIL/NOT_RUN/ERROR with not_run_reason enum
  eh-req-003: Per-test timeout — NOT_RUN/timeout on breach, exit 124 impossible
  eh-req-005: build_provenance (mandatory, "n/a" where no build exists)
  eh-req-011: Preflight dependency probing with bounded timeout
  eh-req-022: Self-test must cover all 4 statuses including negative fixtures
  eh-req-023: Zero executed tests → verdict MUST be NOT_RUN
  eh-req-024: CI job reporting success MUST specify number of executed tests

Usage:
  from harness import create_report, validate_report, generate_junit_xml, run_with_timeout
"""
import json
import os
import signal
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "harness-report.schema.json")

# eh-req-002: status vocabulary
VALID_VERDICTS = {"PASS", "FAIL", "NOT_RUN", "ERROR"}

# eh-req-002: not_run_reason enum — matches spec
NOT_RUN_REASONS = {
    "missing_service",
    "missing_toolchain",
    "missing_fixture",
    "missing_credential",
    "timeout",
    "n/a"
}


def get_schema():
    """Load the harness report schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _determine_applies_to(junit_xml=False, build_provenance=None, has_timeout=False):
    """D5: applies_to is computed per-report, not a global constant."""
    reqs = []
    if junit_xml:
        reqs.append("eh-req-001")
    reqs.append("eh-req-002")
    if has_timeout:
        reqs.append("eh-req-003")
    if build_provenance and build_provenance.get("toolchain") != "n/a":
        reqs.append("eh-req-005")
    reqs.append("eh-req-023")
    reqs.append("eh-req-024")
    return reqs


def create_report(test_id, verdict, test_count, passed, failed, skipped, not_run,
                  build_provenance=None, coverage=None, evidence=None, requirements=None,
                  not_run_reason="n/a", harness_version="1.0.0",
                  junit_xml=False, per_test_timeout=False):
    """Create a harness report with eh-req-023/024 enforcement."""
    # eh-req-005: build_provenance mandatory
    if build_provenance is None:
        build_provenance = {"toolchain": "n/a"}

    # D1: enforce_verdict — failed>0 forces FAIL
    verdict = enforce_verdict(verdict, test_count, passed, failed, skipped)

    # D5: applies_to per report
    applies = _determine_applies_to(
        junit_xml=junit_xml,
        build_provenance=build_provenance,
        has_timeout=per_test_timeout
    )

    report = {
        "report_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "harness_version": harness_version,
        "test_id": test_id,
        "applies_to": applies,
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
    """Enforce verdict rules.

    eh-req-023: zero tests → NOT_RUN
    D1: failed > 0 → FAIL (cannot be overridden to PASS)
    """
    # eh-req-023: zero tests → NOT_RUN
    if test_count == 0:
        return "NOT_RUN"
    # All skipped → NOT_RUN
    if passed == 0 and failed == 0 and skipped > 0:
        return "NOT_RUN"
    # D1: any failures → FAIL
    if failed > 0:
        return "FAIL"
    return verdict


def validate_report(report):
    """Validate report against schema requirements."""
    required = [
        "report_version", "timestamp", "harness_version", "test_id",
        "applies_to", "verdict", "test_count", "passed", "failed",
        "skipped", "not_run", "build_provenance", "coverage",
        "evidence", "requirements"
    ]
    missing = [f for f in required if f not in report]
    if missing:
        return False, f"Missing mandatory fields: {missing}"

    # eh-req-002: valid verdict
    if report["verdict"] not in VALID_VERDICTS:
        return False, f"eh-req-002: invalid verdict '{report['verdict']}' — must be PASS/FAIL/NOT_RUN/ERROR"

    # eh-req-005: build_provenance must exist
    if not report.get("build_provenance"):
        return False, "eh-req-005: build_provenance is required"

    # eh-req-023: test_count=0 → NOT_RUN
    if report["test_count"] == 0 and report["verdict"] != "NOT_RUN":
        return False, "eh-req-023 violation: test_count=0 but verdict != NOT_RUN"

    # D1: PASS with failed>0 must be rejected
    if report["verdict"] == "PASS" and report["failed"] > 0:
        return False, "D1: verdict=PASS but failed={0} — must be FAIL".format(report["failed"])

    # eh-req-024: PASS/FAIL → test_count > 0
    if report["verdict"] in ("PASS", "FAIL") and report["test_count"] == 0:
        return False, "eh-req-024 violation: PASS/FAIL with test_count=0"

    # eh-req-002: NOT_RUN must have not_run_reason
    if report["verdict"] == "NOT_RUN" and report.get("not_run_reason") not in NOT_RUN_REASONS:
        return False, f"eh-req-002: NOT_RUN requires valid not_run_reason"

    return True, "OK"


class TimeoutError(Exception):
    """Raised when a test exceeds its time limit (eh-req-003)."""
    pass


def run_with_timeout(func, timeout, *args, **kwargs):
    """D4: eh-req-003 — run a test function with a hard timeout.

    Returns (result, timed_out). If timeout is hit, returns (None, True).
    Exit 124 is impossible — we catch SIGALRM and return gracefully.
    """
    def _alarm(signum, frame):
        raise TimeoutError("Test exceeded {0}s limit".format(timeout))

    old_handler = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(timeout)
    try:
        result = func(*args, **kwargs)
        return result, False
    except TimeoutError:
        return None, True
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def generate_junit_xml(report, output_path):
    """eh-req-001: Generate JUnit XML from report data.

    D2: errors and failures are distinct.
      - failures: tests that ran but assertion failed (status=FAIL)
      - errors: tests that crashed or were interrupted (status=ERROR)
    """
    suite = ET.Element("testsuite")
    suite.set("name", report.get("test_id", "unknown"))
    suite.set("tests", str(report["test_count"]))

    # D2: count errors and failures separately from requirements
    error_count = 0
    failure_count = 0
    for req in report.get("requirements", []):
        if req.get("status") == "ERROR":
            error_count += 1
        elif req.get("status") == "FAIL":
            failure_count += 1

    suite.set("errors", str(error_count))
    suite.set("failures", str(failure_count))
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

    # D2: no redundant tree variable
    ET.indent(suite, space="  ")
    import io
    buf = ET.ElementTree(suite)
    stream = io.StringIO()
    buf.write(stream, encoding="unicode", xml_declaration=True)
    with open(output_path, "w") as f:
        f.write(stream.getvalue())
    return output_path
