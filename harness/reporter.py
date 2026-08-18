#!/usr/bin/env python3
"""Reporter: generate harness report from test results.

Usage:
  python3 -m harness.reporter --output report.json \
    --test-id "run-2026-08-18" \
    --passed 5 --failed 2 --skipped 0 --not-run 10 \
    --coverage "7/17"
"""
import argparse
import json
import sys
from . import create_report, validate_report

def main():
    parser = argparse.ArgumentParser(description="Generate harness report")
    parser.add_argument("--output", required=True, help="Output path for report JSON")
    parser.add_argument("--test-id", required=True, help="Unique test run identifier")
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--failed", type=int, default=0)
    parser.add_argument("--skipped", type=int, default=0)
    parser.add_argument("--not-run", type=int, default=0)
    parser.add_argument("--coverage", default="0/0", help="Coverage ratio string (e.g., '3/17')")
    parser.add_argument("--harness-version", default="1.0.0")
    args = parser.parse_args()

    test_count = args.passed + args.failed + args.skipped

    # Determine verdict
    if test_count == 0:
        verdict = "NOT_RUN"
    elif args.failed > 0:
        verdict = "FAIL"
    elif test_count == args.skipped:
        verdict = "NOT_RUN"
    else:
        verdict = "PASS"

    # Parse coverage
    parts = args.coverage.split("/")
    total_req = int(parts[0]) if len(parts) > 1 and parts[0] else 0
    tested_req = int(parts[0]) if len(parts) > 1 and parts[0] else 0

    coverage = {
        "total_requirements": 17,  # Default Rocom spec requirements
        "tested_requirements": tested_req,
        "implemented_requirements": args.passed,
        "coverage_ratio": args.coverage
    }

    report = create_report(
        test_id=args.test_id,
        verdict=verdict,
        test_count=test_count,
        passed=args.passed,
        failed=args.failed,
        skipped=args.skipped,
        not_run=args.not_run,
        coverage=coverage,
        harness_version=args.harness_version
    )

    valid, msg = validate_report(report)
    if not valid:
        print(f"REPORT INVALID: {msg}")
        sys.exit(1)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report written: {args.output}")
    print(f"Verdict: {report['verdict']} ({report['test_count']} tests, {args.coverage} coverage)")
    sys.exit(0)

if __name__ == "__main__":
    main()
