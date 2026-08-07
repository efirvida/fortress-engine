#!/usr/bin/env python3
"""Enforce the project's testing hard gate: TOTAL coverage must be > 99%
for BOTH statements and branches (AGENTS.md).

Reads the JSON report produced by:
    pytest --cov=src/fortress_engine --cov-branch --cov-report=json

Exit code 0 = gate passed; 1 = gate failed (blocks merge).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THRESHOLD = 99.0


def main() -> int:
    report_path = Path("coverage.json")
    if not report_path.is_file():
        print("ERROR: coverage.json not found. Run pytest with --cov-report=json first.")
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    totals = report.get("totals", {})

    statements_pct = totals.get("percent_statements_covered", 0.0)
    branches_pct = totals.get("percent_branches_covered", 0.0)

    print(f"Statement coverage: {statements_pct:.2f}%")
    print(f"Branch coverage:    {branches_pct:.2f}%")
    print(f"Gate threshold:     > {THRESHOLD:.0f}% (both)")

    ok = statements_pct > THRESHOLD and branches_pct > THRESHOLD
    if not ok:
        print("FAIL: coverage gate not met — tests do NOT cover all implemented code.")
        return 1

    print("PASS: coverage gate met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
