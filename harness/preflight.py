#!/usr/bin/env python3
"""Preflight: dependency probing per eh-req-011.

Probes required services and tools with bounded timeout.
Tests depending on unavailable services are marked NOT_RUN/missing_service.

Dependencies probed:
  - mqtt_broker     (localhost:1883)
  - hrrm_core_api   (localhost:8000)
  - vda5050_gateway (localhost:8001)
  - allocation_engine (localhost:8002)
  - cargo           (CLI)
  - omc             (CLI — OpenModelica)
  - newman          (CLI — Postman runner)
  - cadquery        (CLI)
  - docker          (CLI)

Usage:
  python3 -m harness.preflight [--timeout 5] [--skip omc,newman]
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time


# eh-req-011: bounded timeout for each probe (seconds)
DEFAULT_TIMEOUT = 5

# Ports configurable via env (WP5: out of 8000-series which AI1 uses for llama-server)
DEFAULT_SERVICES = {
    "mqtt_broker":       {"host": "localhost", "port": int(os.environ.get("MQTT_BROKER_PORT", 1883)), "type": "tcp"},
    "hrrm_core_api":     {"host": "localhost", "port": int(os.environ.get("HRRM_CORE_PORT", 18830)), "type": "tcp"},
    "vda5050_gateway":   {"host": "localhost", "port": int(os.environ.get("VDA_GATEWAY_PORT", 18831)), "type": "tcp"},
    "allocation_engine": {"host": "localhost", "port": int(os.environ.get("ALLOCATION_PORT", 18832)), "type": "tcp"},
}

TOOL_CHECKS = ["cargo", "omc", "newman", "cadquery", "docker"]


def probe_tcp(host, port, timeout):
    """Probe a TCP port with bounded timeout."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True, f"{host}:{port} reachable"
    except (socket.timeout, OSError) as e:
        return False, str(e)


def probe_cli(tool, timeout):
    """Probe CLI tool availability."""
    try:
        result = subprocess.run(
            [tool, "--version"],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            ver = result.stdout.strip().split("\n")[0]
            return True, ver
        return False, f"exit code {result.returncode}"
    except FileNotFoundError:
        return False, "not found"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"


def run_preflight(timeout=DEFAULT_TIMEOUT, skip=None):
    """Run all probes and return results dict."""
    skip = set(skip or [])
    results = {"services": {}, "tools": {}, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    missing_services = []

    # Service probes
    for name, cfg in DEFAULT_SERVICES.items():
        if name in skip:
            continue
        ok, msg = probe_tcp(cfg["host"], cfg["port"], timeout)
        results["services"][name] = {"status": "available" if ok else "unavailable", "detail": msg}
        if not ok:
            missing_services.append(name)

    # Tool probes
    for tool in TOOL_CHECKS:
        if tool in skip:
            continue
        ok, msg = probe_cli(tool, timeout)
        results["tools"][tool] = {"status": "available" if ok else "unavailable", "detail": msg}

    results["missing_services"] = missing_services
    return results


def main():
    parser = argparse.ArgumentParser(description="Preflight dependency probing (eh-req-011)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Per-probe timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--skip", default="",
                        help="Comma-separated list of checks to skip (e.g., 'omc,newman')")
    parser.add_argument("--output", help="Write results to JSON file")
    args = parser.parse_args()

    skip = [s for s in args.skip.split(",") if s]
    results = run_preflight(timeout=args.timeout, skip=skip)

    # Print summary
    svc_avail = sum(1 for v in results["services"].values() if v["status"] == "available")
    svc_total = len(results["services"])
    tool_avail = sum(1 for v in results["tools"].values() if v["status"] == "available")
    tool_total = len(results["tools"])

    print(f"Services: {svc_avail}/{svc_total} available")
    print(f"Tools:    {tool_avail}/{tool_total} available")
    if results["missing_services"]:
        print(f"Missing:  {', '.join(results['missing_services'])}")
        print("Dependent tests will be marked NOT_RUN/missing_service")
    else:
        print("All services available — no tests blocked")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {args.output}")

    # Exit 0 only if all critical services are available
    # (non-critical tools like omc/newman don't block)
    critical = {"mqtt_broker", "hrrm_core_api"}
    critical_missing = critical & set(results["missing_services"])
    sys.exit(1 if critical_missing else 0)


if __name__ == "__main__":
    main()
