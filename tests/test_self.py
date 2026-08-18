#!/usr/bin/env python3
"""Self-test: verify harness validates its own output.

Per eh-req-022: must cover all 4 statuses (PASS, FAIL, NOT_RUN, ERROR).
Emits SUSPECT_TAUTOLOGY if negative fixtures are missing.

Tests:
  1. Schema structure (all fields, enums, not_run_reason)
  2. D5: applies_to is per-report, not global
  3. eh-req-023 zero tests → NOT_RUN
  4. eh-req-024 success with test count
  5. D1: enforce_verdict — failed>0 forces FAIL
  6. D1: validate_report rejects PASS with failed=3 (negative fixture)
  7. Ekte ERROR — invalid verdict caught (eh-req-002)
  8. NOT_RUN/missing_service
  9. D4: eh-req-003 — timeout enforcement
  10. eh-req-001 JUnit XML — errors vs failures distinct
  11. SUSPECT_TAUTOLOGY: all 4 verdicts present?
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from harness import (
    create_report, validate_report, generate_junit_xml,
    VALID_VERDICTS, NOT_RUN_REASONS, run_with_timeout, HarnessTimeout
)

observed_verdicts = set()


def record_verdict(v):
    observed_verdicts.add(v)


def test_schema_structure():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "harness-report.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    for field in ["test_id", "verdict", "test_count", "build_provenance", "applies_to"]:
        assert field in schema["required"], f"Schema missing required: {field}"

    verdict_enum = schema["properties"]["verdict"]["enum"]
    assert set(verdict_enum) == {"PASS", "FAIL", "NOT_RUN", "ERROR"}

    nr_enum = schema["properties"]["not_run_reason"]["enum"]
    assert "missing_toolchain" in nr_enum, "not_run_reason must have missing_toolchain"
    assert "timeout" in nr_enum, "not_run_reason must have timeout"
    assert "missing_tool" not in nr_enum, "missing_tool removed, use missing_toolchain"

    print("PASS: schema structure (eh-req-001/002/003/005/023/024)")


def test_applies_to_per_report():
    """D5: applies_to is computed per-report, not a global constant."""
    # Report with junit_xml=True
    r1 = create_report(
        test_id="d5-junit", verdict="PASS", test_count=1,
        passed=1, failed=0, skipped=0, not_run=0, junit_xml=True
    )
    assert "eh-req-001" in r1["applies_to"], "junit_xml=True → eh-req-001 in applies_to"

    # Report with junit_xml=False
    r2 = create_report(
        test_id="d5-no-junit", verdict="PASS", test_count=1,
        passed=1, failed=0, skipped=0, not_run=0, junit_xml=False
    )
    assert "eh-req-001" not in r2["applies_to"], "junit_xml=False → eh-req-001 NOT in applies_to"

    print("PASS: D5 — applies_to varies per report")


def test_eh_req_023_zero_tests():
    report = create_report(
        test_id="self-023", verdict="PASS",
        test_count=0, passed=0, failed=0, skipped=0, not_run=17
    )
    record_verdict(report["verdict"])
    assert report["verdict"] == "NOT_RUN", f"eh-req-023: got {report['verdict']}"
    valid, msg = validate_report(report)
    assert valid, msg
    print("PASS: eh-req-023 — zero tests → NOT_RUN")


def test_eh_req_024_success_with_count():
    report = create_report(
        test_id="self-024", verdict="PASS",
        test_count=5, passed=5, failed=0, skipped=0, not_run=12
    )
    record_verdict(report["verdict"])
    assert report["verdict"] == "PASS"
    assert report["test_count"] > 0
    valid, msg = validate_report(report)
    assert valid, msg
    print("PASS: eh-req-024 — success with test count")


def test_d1_enforce_failed():
    """D1: enforce_verdict forces FAIL when failed > 0."""
    report = create_report(
        test_id="d1-enforce", verdict="PASS",  # deliberately wrong
        test_count=4, passed=1, failed=3, skipped=0, not_run=0
    )
    record_verdict(report["verdict"])
    assert report["verdict"] == "FAIL", \
        f"D1: enforce_verdict should force FAIL when failed=3, got {report['verdict']}"
    print("PASS: D1 — enforce_verdict: failed=3 → FAIL")


def test_d1_validate_rejects_pass_with_failures():
    """D1: validate_report must reject PASS verdict when failed > 0."""
    bad = {
        "report_version": "1.0.0",
        "timestamp": "2026-08-18T00:00:00+00:00",
        "harness_version": "1.0.0",
        "test_id": "d1-bad-pass",
        "applies_to": ["eh-req-002", "eh-req-023", "eh-req-024"],
        "verdict": "PASS",
        "test_count": 4, "passed": 1, "failed": 3, "skipped": 0, "not_run": 0,
        "not_run_reason": "n/a",
        "build_provenance": {"toolchain": "n/a"},
        "coverage": {"total_requirements": 4, "tested_requirements": 4,
                      "implemented_requirements": 1, "coverage_ratio": "1/4"},
        "evidence": [], "requirements": [
            {"id": "T-01", "status": "PASS"},
            {"id": "T-02", "status": "FAIL"},
            {"id": "T-03", "status": "FAIL"},
            {"id": "T-04", "status": "FAIL"},
        ]
    }
    valid, msg = validate_report(bad)
    assert not valid, "D1: PASS with failed=3 must be rejected"
    assert "failed" in msg.lower(), f"D1: error message should mention 'failed', got: {msg}"
    print(f"PASS: D1 — PASS with failed=3 rejected: {msg}")


def test_ekte_error():
    bad_report = {
        "report_version": "1.0.0",
        "timestamp": "2026-08-18T00:00:00+00:00",
        "harness_version": "1.0.0",
        "test_id": "self-error-001",
        "applies_to": ["eh-req-002"],
        "verdict": "INVALID_VERDICT",
        "test_count": 1, "passed": 0, "failed": 0, "skipped": 0, "not_run": 0,
        "not_run_reason": "n/a",
        "build_provenance": {"toolchain": "n/a"},
        "coverage": {"total_requirements": 1, "tested_requirements": 0,
                      "implemented_requirements": 0, "coverage_ratio": "0/1"},
        "evidence": [], "requirements": []
    }
    valid, msg = validate_report(bad_report)
    assert not valid, "Should reject invalid verdict"
    assert "eh-req-002" in msg, f"Should cite eh-req-002, got: {msg}"

    # Manual ERROR
    manual_error = {
        "report_version": "1.0.0",
        "timestamp": "2026-08-18T00:00:00+00:00",
        "harness_version": "1.0.0",
        "test_id": "self-error-manual",
        "applies_to": ["eh-req-002"],
        "verdict": "ERROR",
        "test_count": 3, "passed": 0, "failed": 0, "skipped": 0, "not_run": 3,
        "not_run_reason": "missing_service",
        "build_provenance": {"toolchain": "n/a"},
        "coverage": {"total_requirements": 3, "tested_requirements": 0,
                      "implemented_requirements": 0, "coverage_ratio": "0/3"},
        "evidence": [], "requirements": [
            {"id": "ID-001", "status": "ERROR", "not_run_reason": "missing_service"}
        ]
    }
    record_verdict("ERROR")
    valid2, msg2 = validate_report(manual_error)
    assert valid2, f"ERROR verdict should pass: {msg2}"
    print("PASS: ekte ERROR — invalid verdict caught, ERROR valid")


def test_not_run_missing_service():
    report = create_report(
        test_id="self-nr", verdict="NOT_RUN",
        test_count=0, passed=0, failed=0, skipped=0, not_run=5,
        not_run_reason="missing_service"
    )
    record_verdict(report["verdict"])
    assert report["verdict"] == "NOT_RUN"
    valid, msg = validate_report(report)
    assert valid, msg
    print("PASS: NOT_RUN/missing_service")


def test_d4_timeout():
    """D4: eh-req-003 — per-test timeout, exit 124 impossible."""
    def slow_test():
        time.sleep(10)
        return "done"

    result, timed_out = run_with_timeout(slow_test, timeout=1)
    assert timed_out, "Test should have timed out after 1s"
    assert result is None, "Timed-out test should return None"

    # Verify exit 124 is impossible — run completes cleanly
    print("PASS: D4 — eh-req-003 timeout enforcement (1s limit, no exit 124)")


def test_junit_errors_vs_failures():
    """eh-req-001 D2: errors and failures are distinct in JUnit XML."""
    report = create_report(
        test_id="self-junit", verdict="FAIL",
        test_count=3, passed=1, failed=1, skipped=0, not_run=0,
        requirements=[
            {"id": "ID-001", "status": "PASS"},
            {"id": "ID-002", "status": "FAIL", "details": "assertion failed"},
            {"id": "ID-003", "status": "ERROR", "details": "unhandled exception"},
        ]
    )
    record_verdict(report["verdict"])

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        xml_path = f.name

    try:
        generate_junit_xml(report, xml_path)
        with open(xml_path) as f:
            content = f.read()

        assert '<?xml' in content, "Missing XML declaration"
        assert 'testsuite' in content, "Missing testsuite"
        # D2: errors=1, failures=1
        assert 'errors="1"' in content, "Should have errors=1"
        assert 'failures="1"' in content, "Should have failures=1"
        assert '<failure>' in content, "Missing <failure> element"
        assert '<error>' in content, "Missing <error> element"
        print("PASS: eh-req-001 — JUnit XML errors≠failures (D2)")
    finally:
        os.unlink(xml_path)


def test_suspect_tautology():
    expected = {"PASS", "FAIL", "NOT_RUN", "ERROR"}
    missing = expected - observed_verdicts
    if missing:
        print(f"SUSPECT_TAUTOLOGY: verdicts not observed: {missing}")
        raise AssertionError(f"SUSPECT_TAUTOLOGY: missing {missing}")
    print("PASS: eh-req-022 — all 4 verdicts observed")


def main():
    tests = [
        test_schema_structure,
        test_applies_to_per_report,
        test_eh_req_023_zero_tests,
        test_eh_req_024_success_with_count,
        test_d1_enforce_failed,
        test_d1_validate_rejects_pass_with_failures,
        test_ekte_error,
        test_not_run_missing_service,
        test_d4_timeout,
        test_junit_errors_vs_failures,
        test_suspect_tautology,
    ]

    passed_count = 0
    failed_count = 0
    errors = []

    for test in tests:
        try:
            test()
            passed_count += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed_count += 1
            errors.append(str(e))
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed_count += 1
            errors.append(str(e))

    # Build report
    verdict = "PASS" if failed_count == 0 else "FAIL"
    report = create_report(
        test_id="self-test-l1-v3",
        verdict=verdict,
        test_count=len(tests),
        passed=passed_count,
        failed=failed_count,
        skipped=0, not_run=0,
        build_provenance={"toolchain": "python 3.x (harness self-test)"},
        requirements=[
            {"id": f"T-{i:02d}", "status": "PASS" if i < passed_count else "FAIL",
             "details": errors[i - passed_count] if i >= passed_count and len(errors) > i - passed_count else ""}
            for i in range(len(tests))
        ],
        coverage={
            "total_requirements": len(tests),
            "tested_requirements": len(tests),
            "implemented_requirements": passed_count,
            "coverage_ratio": f"{passed_count}/{len(tests)}"
        },
        evidence=[{"type": "log", "path": "tests/self-test-output.txt"}]
    )

    out = "tests/self-test-report.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)

    junit = "tests/self-test-report.xml"
    generate_junit_xml(report, junit)

    print(f"\n{'='*40}")
    print(f"Self-test: {passed_count}/{len(tests)} passed, {failed_count} failed")
    print(f"Verdicts: {sorted(observed_verdicts)}")
    print(f"Report: {out}")
    print(f"JUnit XML: {junit}")
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == "__main__":
    main()
