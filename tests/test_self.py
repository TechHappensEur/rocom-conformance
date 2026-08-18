#!/usr/bin/env python3
"""Self-test: verify the harness validates its own reports (eh-req-023, eh-req-024)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from harness import create_report, validate_report, enforce_eh_req_024

def test_eh_req_023_mandatory_fields():
    """eh-req-023: Every report MUST have mandatory fields."""
    report = create_report(
        test_id="self-test-001",
        verdict="PASS",
        test_count=3,
        passed=3,
        failed=0,
        skipped=0,
        not_run=0
    )
    valid, msg = validate_report(report)
    assert valid, f"Self-test report failed validation: {msg}"

    # Check all mandatory fields present
    required = ["report_version", "timestamp", "harness_version", "test_id",
                "verdict", "test_count", "passed", "failed", "skipped",
                "not_run", "coverage", "evidence", "requirements"]
    for field in required:
        assert field in report, f"Missing mandatory field (eh-req-023): {field}"

    print("PASS: eh-req-023 — all mandatory fields present")

def test_eh_req_024_zero_tests_not_run():
    """eh-req-024: 0 tests MUST result in NOT_RUN verdict."""
    report = create_report(
        test_id="self-test-002",
        verdict="PASS",  # Intentionally PASS — should be overridden
        test_count=0,
        passed=0,
        failed=0,
        skipped=0,
        not_run=17
    )
    assert report["verdict"] == "NOT_RUN", f"eh-req-024: test_count=0 should yield NOT_RUN, got {report['verdict']}"
    valid, msg = validate_report(report)
    assert valid, f"Validation failed: {msg}"

    print("PASS: eh-req-024 — zero tests = NOT_RUN")

def test_eh_req_024_all_skipped_not_run():
    """eh-req-024: All skipped tests MUST result in NOT_RUN verdict."""
    report = create_report(
        test_id="self-test-003",
        verdict="PASS",  # Intentionally PASS — should be overridden
        test_count=5,
        passed=0,
        failed=0,
        skipped=5,
        not_run=0
    )
    assert report["verdict"] == "NOT_RUN", f"eh-req-024: all skipped should yield NOT_RUN, got {report['verdict']}"

    print("PASS: eh-req-024 — all skipped = NOT_RUN")

def test_eh_req_024_pass_with_tests():
    """Normal case: passed tests = PASS."""
    report = create_report(
        test_id="self-test-004",
        verdict="PASS",
        test_count=3,
        passed=3,
        failed=0,
        skipped=0,
        not_run=0
    )
    assert report["verdict"] == "PASS"

    print("PASS: normal pass case")

def test_schema_structure():
    """Verify schema file exists and is valid JSON."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "harness-report.schema.json")
    assert os.path.exists(schema_path), "Schema file not found"
    with open(schema_path) as f:
        schema = json.load(f)
    assert "required" in schema, "Schema missing 'required' field"
    assert "properties" in schema, "Schema missing 'properties' field"

    print("PASS: schema structure valid")

def main():
    tests = [
        test_schema_structure,
        test_eh_req_023_mandatory_fields,
        test_eh_req_024_zero_tests_not_run,
        test_eh_req_024_all_skipped_not_run,
        test_eh_req_024_pass_with_tests,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Self-test: {passed} passed, {failed} failed, {len(tests)} total")

    # Write self-test report
    report = create_report(
        test_id="self-test-l1",
        verdict="PASS" if failed == 0 else "FAIL",
        test_count=len(tests),
        passed=passed,
        failed=failed,
        skipped=0,
        not_run=0
    )

    with open("tests/self-test-report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report: tests/self-test-report.json")

    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
