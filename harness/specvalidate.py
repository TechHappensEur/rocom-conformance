#!/usr/bin/env python3
"""SpecValidator: validate OpenAPI/AsyncAPI spec files.

Separated from preflight (eh-req-011: preflight is for dependency probing only).
"""
import argparse
import json
import os
import sys


def validate_openapi(path):
    """Basic OpenAPI spec validation."""
    with open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            try:
                import yaml
                with open(path) as fy:
                    data = yaml.safe_load(fy)
            except ImportError:
                return False, "Cannot parse JSON/YAML: install pyyaml"

    if "openapi" not in data:
        return False, "Missing 'openapi' field"
    if not data["openapi"].startswith("3."):
        return False, f"Not OpenAPI 3.x: {data['openapi']}"
    if "paths" not in data:
        return False, "Missing 'paths' field"
    return True, f"OpenAPI {data['openapi']} with {len(data['paths'])} paths"


def validate_asyncapi(path):
    """Basic AsyncAPI spec validation."""
    try:
        import yaml
    except ImportError:
        return False, "pyyaml required for AsyncAPI validation"

    with open(path) as f:
        data = yaml.safe_load(f)

    if "asyncapi" not in data:
        return False, "Missing 'asyncapi' field"
    if not data["asyncapi"].startswith("3."):
        return False, f"Not AsyncAPI 3.x: {data['asyncapi']}"
    if "channels" not in data:
        return False, "Missing 'channels' field"
    return True, f"AsyncAPI {data['asyncapi']} with {len(data['channels'])} channels"


def main():
    parser = argparse.ArgumentParser(description="Validate OpenAPI/AsyncAPI spec files")
    parser.add_argument("--spec", required=True, help="Path to spec file")
    args = parser.parse_args()

    if not os.path.exists(args.spec):
        print(f"ERROR: {args.spec} not found")
        sys.exit(1)

    if "asyncapi" in args.spec.lower() or "vda5050" in args.spec.lower():
        ok, msg = validate_asyncapi(args.spec)
    else:
        ok, msg = validate_openapi(args.spec)

    print(f"{'PASS' if ok else 'FAIL'}: {msg}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
