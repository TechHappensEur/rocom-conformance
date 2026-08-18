# Rocom Conformance Harness

L1 conformance harness for Rocom specification testing.

## Implemented Requirements

| ID | Description | Status |
|----|-------------|--------|
| eh-req-001 | JUnit XML output for machine-readable evidence | Implemented |
| eh-req-002 | Status vocabulary: PASS/FAIL/NOT_RUN/ERROR with not_run_reason enum | Implemented |
| eh-req-005 | build_provenance (mandatory, "n/a" where no build exists) | Implemented |
| eh-req-011 | Preflight: dependency probing with bounded timeout, dependent tests marked NOT_RUN/missing_service | Implemented |
| eh-req-022 | Self-test must cover all 4 statuses including negative fixtures (SUSPECT_TAUTOLOGY) | Implemented |
| eh-req-023 | Zero executed tests → verdict MUST be NOT_RUN | Implemented |
| eh-req-024 | CI job reporting success MUST specify number of executed tests | Implemented |

## Structure

```
schemas/
  harness-report.schema.json  — JSON Schema (applies_to, build_provenance, JUnit XML, status vocab)
harness/
  __init__.py                 — Report creation, validation, eh-req enforcement, JUnit XML
  preflight.py                — Dependency probing (eh-req-011): mqtt_broker, hrrm_core_api, etc.
  reporter.py                 — CLI reporter for generating reports
  specvalidate.py             — OpenAPI/AsyncAPI spec validation (separate from preflight)
tests/
  test_self.py                — Self-test: 9/9, all 4 verdicts, negative fixtures
  self-test-report.json       — Actual run report
  self-test-report.xml        — JUnit XML evidence
```

## Usage

### Preflight (dependency probing)
```bash
python3 -m harness.preflight --timeout 5 --skip omc,newman
```

### Spec validation
```bash
python3 -m harness.specvalidate --spec ../Rocom/specs/hrrm-core-api.yaml
```

### Reporter
```bash
python3 -m harness.reporter --output report.json \
  --test-id "run-2026-08-18" \
  --passed 5 --failed 0 --skipped 0 --not-run 12 \
  --coverage "5/17" --junit-xml report.xml
```

### Self-test
```bash
python3 tests/test_self.py
# Output: 9/9 passed, verdicts: ERROR, FAIL, NOT_RUN, PASS
```

## eh-req-024 Enforcement

The harness automatically enforces verdict rules:
- `test_count == 0` → verdict forced to `NOT_RUN`
- `passed == 0 && failed == 0 && skipped > 0` → verdict forced to `NOT_RUN`
- `passed > 0 && failed == 0` → `PASS`
- `failed > 0` → `FAIL`

## Evidence

### Commit History
- Initial: https://github.com/TechHappensEur/rocom-conformance/commit/d67f9d1
- v2 (eh-req-001/002/005/011/022/023/024): https://github.com/TechHappensEur/rocom-conformance/commit/1ceaafd

### WP1 Receipt
- receipt-wp1.json: https://github.com/TechHappensEur/Rocom-HRRM/commit/5ea25c4 (committed in Rocom-HRRM)
- verify_receipt.py: 5/5 checks pass, exit code 0

### Self-Test Report
- tests/self-test-report.json — actual run, schema-validated
- tests/self-test-report.xml — JUnit XML (eh-req-001)

## Ferrocene / IEC 62304 Class C — Claim vs Reality

Three instances where the codebase claims IEC 62304 Class C / Ferrocene compliance
without build evidence. Listed as-is, not corrected.

| # | File | Line | Claim |
|---|------|------|-------|
| 1 | `rocom-core/src/lib.rs` | 4 | `//! Built with Ferrocene 24.11.0 (IEC 62304 Class C qualified)` — code does not compile on rustc 1.97.1 stable (13 errors in order.rs). Ferrocene toolchain never configured. |
| 2 | `rocom-hrrm/src/lib.rs` | 5 | `//! IEC 62304 Class C: deterministic, bounded, no ML at runtime.` — no build verification, no toolchain evidence. Crate fails to compile (3 errors in replan.rs). |
| 3 | `rocom-hrrm/src/replan.rs` | 243 | `// Placeholder — the Ferrocene BSP provides this.` — references a BSP that does not exist in the repository. `read_hw_ns()` returns `0`. |

Source: `reports/rust-build-status-2026-08-18.md` (https://github.com/TechHappensEur/Rocom-HRRM/commit/1770fcb)

## CI Findings (Rocom-HRRM)

### integration job — eh-req-023/024 violation
The `integration` job runs `make demo` (demo.py), not a test suite. No pytest,
no test count, no machine-readable output. Reports `success` with 0 executed tests.
Both eh-req-023 (zero tests → NOT_RUN) and eh-req-024 (success → test count) are violated.

### lint-specs — spectral annotation failure
`lint-specs` spectral step fails silently with "Resource not accessible by integration"
due to missing `checks: write` scope. Fix: add `permissions: { contents: read, checks: write, pull-requests: write }`.

### crossplatform — CI vs local discrepancy
CI: 6 tests pass. Local: 2 tests pass. CI runs Docker containers (mqtt broker, HRRM core, etc.)
which satisfy the test dependencies. Local environment lacks running services.
