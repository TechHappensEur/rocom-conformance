#!/usr/bin/env python3
"""Reporter: generate harness report from test results.

Implements eh-req-001 (JUnit XML), eh-req-005 (build_provenance),
eh-req-023 (zero tests → NOT_RUN), eh-req-024 (success → test count).
"""
import argparse
import json
import sys
from . import create_report, validate_report, generate_junit_xml

def main():
    parser = argparse.ArgumentParser(description="Generate harness report (eh-req-001/005/023/024)")
    parser.add_argument("--output", required=True, help="Output path for report JSON")
    parser.add_argument("--test-id", required=True, help="Unique test run identifier")
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--failed", type=int, default=0)
    parser.add_argument("--skipped", type=int, default=0)
    parser.add_argument("--not-run", type=int, default=0)
    parser.add_argument("--coverage", default="0/0", help="Coverage ratio (e.g., '3/17')")
    parser.add_argument("--harness-version", default="1.0.0")
    parser.add_argument("--build-toolchain", default="n/a", help="eh-req-005: build toolchain")
    parser.add_argument("--build-commit", default="", help="eh-req-005: commit SHA")
    parser.add_argument("--junit-xml", help="eh-req-001: output JUnit XML path")
    args = parser.parse_args()

    test_count = args.passed + args.failed + args.skipped

    # Determine verdict
    if test_count == 0:
        verdict = "NOT_RUN"
        not_run_reason = "no_tests_implemented"
    elif args.failed > 0:
        verdict = "FAIL"
        not_run_reason = "n/a"
    elif test_count == args.skipped:
        verdict = "NOT_RUN"
        not_run_reason = "simulated"
    else:
        verdict = "PASS"
        not_run_reason = "n/a"

    parts = args.coverage.split("/")
    total_req = 17
    tested_req = int(parts[0]) if parts[0] else 0

    coverage = {
        "total_requirements": total_req,
        "tested_requirements": tested_req,
        "implemented_requirements": args.passed,
        "coverage_ratio": args.coverage
    }

    bp = {"toolchain": args.build_toolchain}
    if args.build_commit:
        bp["commit"] = args.build_commit

    report = create_report(
        test_id=args.test_id,
        verdict=verdict,
        test_count=test_count,
        passed=args.passed,
        failed=args.failed,
        skipped=args.skipped,
        not_run=args.not_run,
        build_provenance=bp,
        coverage=coverage,
        not_run_reason=not_run_reason,
        harness_version=args.harness_version
    )

    valid, msg = validate_report(report)
    if not valid:
        print(f"REPORT INVALID: {msg}")
        sys.exit(1)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    # eh-req-001: JUnit XML
    junit_path = None
    if args.junit_xml:
        junit_path = generate_junit_xml(report, args.junit_xml)
        print(f"JUnit XML: {junit_path}")

    print(f"Report: {args.output}")
    print(f"Verdict: {report['verdict']} ({report['test_count']} tests, {args.coverage} coverage)")
    sys.exit(0)

if __name__ == "__main__":
    main()
