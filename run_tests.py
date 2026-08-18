#!/usr/bin/env python3
# FILE: run_tests.py
# Conformance test runner — executed as compose service or locally.
import json
import os
import subprocess
import sys


def main():
    os.makedirs("reports", exist_ok=True)

    test_modules = [
        "tests.test_self",
        "tests.test_dg01",
        "tests.test_id01",
    ]

    all_passed = True
    results = []

    for mod in test_modules:
        # Import dynamically to avoid dependency issues
        try:
            __import__(mod)
            imported = sys.modules[mod]
            if hasattr(imported, "run_tests"):
                report = imported.run_tests()
                results.append(report)
                verdict = report.get("verdict", "ERROR")
                print(f"  {mod}: {verdict}")
                if verdict != "PASS":
                    all_passed = False
            else:
                print(f"  {mod}: no run_tests() found — skipping")
        except Exception as e:
            print(f"  {mod}: ERROR — {e}")
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
