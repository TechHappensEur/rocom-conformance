# Rocom Conformance Harness

L1 conformance harness for Rocom specification testing.

## Requirements Implemented

| ID | Description | Status |
|----|-------------|--------|
| eh-req-023 | Every CI job MUST report test count with mandatory fields (test_id, verdict, coverage, evidence, timestamp) | Implemented |
| eh-req-024 | CI job with 0 executed tests or only skipped tests MUST report NOT_RUN, never success | Implemented |

## Structure

```
schemas/
  harness-report.schema.json  — JSON Schema for test reports
harness/
  __init__.py                 — Report creation, validation, eh-req enforcement
  preflight.py                — Spec file validation (OpenAPI/AsyncAPI)
  reporter.py                 — CLI reporter for generating reports
tests/
  test_self.py                — Self-test: harness validates its own output
```

## Usage

### Preflight
```bash
python3 -m harness.preflight --spec ../Rocom/specs/hrrm-core-api.yaml
```

### Reporter
```bash
python3 -m harness.reporter --output report.json \
  --test-id "run-2026-08-18" \
  --passed 5 --failed 0 --skipped 0 --not-run 12 \
  --coverage "5/17"
```

### Self-test
```bash
python3 tests/test_self.py
```

## eh-req-024 Enforcement

The harness automatically enforces verdict rules:
- `test_count == 0` → verdict forced to `NOT_RUN`
- `passed == 0 && failed == 0 && skipped > 0` → verdict forced to `NOT_RUN`
- `passed > 0 && failed == 0` → `PASS`
- `failed > 0` → `FAIL`
