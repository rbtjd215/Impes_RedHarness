"""Static checks for the RedHarness v1 mock input/output contract.

This module only reads JSON files. It does not run a module or contact a target.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "contract_version",
    "run_id",
    "target_id",
    "selected_module",
    "producer",
    "observation",
    "actions",
    "status",
    "evidence",
    "error",
    "next_action",
}
MODULES = {"A", "B"}
PRODUCERS = {"DISPATCHER", "A", "B", "ORACLE", "REPORTER"}
STATUSES = {"PASS", "FAIL", "UNKNOWN", "NOT_RUN"}
STAGE = {"DISPATCHER": 0, "A": 1, "B": 1, "ORACLE": 2, "REPORTER": 3}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_envelope(value: Any, label: str = "record") -> list[str]:
    """Check fields and status ownership for one PROJECT_SPEC v1 envelope."""
    if not isinstance(value, dict):
        return [f"{label}: expected a JSON object"]

    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - value.keys())
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")

    if "contract_version" in value and value["contract_version"] != "1.0":
        errors.append(f"{label}.contract_version: expected '1.0'")
    for key in ("run_id", "target_id"):
        if key in value and not _nonempty_string(value[key]):
            errors.append(f"{label}.{key}: expected a non-empty string")
    if "next_action" in value and not isinstance(value["next_action"], str):
        errors.append(f"{label}.next_action: expected a string")
    if "selected_module" in value and (
        not isinstance(value["selected_module"], str)
        or value["selected_module"] not in MODULES
    ):
        errors.append(f"{label}.selected_module: expected A or B")
    if "producer" in value and (
        not isinstance(value["producer"], str)
        or value["producer"] not in PRODUCERS
    ):
        errors.append(f"{label}.producer: invalid producer")
    if "status" in value and (
        not isinstance(value["status"], str)
        or value["status"] not in STATUSES
    ):
        errors.append(f"{label}.status: invalid status")
    if "observation" in value and not isinstance(value["observation"], dict):
        errors.append(f"{label}.observation: expected an object")
    for key in ("actions", "evidence"):
        if key in value and not isinstance(value[key], list):
            errors.append(f"{label}.{key}: expected an array")
    if "error" in value and value["error"] is not None and not isinstance(
        value["error"], (str, dict)
    ):
        errors.append(f"{label}.error: expected null, string, or object")

    producer = value.get("producer") if isinstance(value.get("producer"), str) else None
    selected = (
        value.get("selected_module")
        if isinstance(value.get("selected_module"), str)
        else None
    )
    status = value.get("status") if isinstance(value.get("status"), str) else None
    evidence = value.get("evidence")
    if producer in MODULES and selected in MODULES and producer != selected:
        errors.append(f"{label}: specialist producer does not match selected_module")
    if producer in {"DISPATCHER", "A", "B"} and status in {"PASS", "FAIL"}:
        errors.append(f"{label}: only ORACLE may make the final PASS/FAIL decision")
    if producer == "ORACLE" and status in {"PASS", "FAIL"}:
        if isinstance(evidence, list) and not evidence:
            errors.append(f"{label}: {status} requires recorded evidence")

    return errors


def validate_document(value: Any) -> list[str]:
    """Validate one envelope or an ordered list of envelopes for one run."""
    if isinstance(value, dict):
        errors = validate_envelope(value)
        if value.get("producer") == "REPORTER":
            errors.append("record: REPORTER needs an ORACLE envelope in the same list")
        return errors
    if not isinstance(value, list) or not value:
        return ["document: expected one envelope or a non-empty array of envelopes"]

    errors: list[str] = []
    for index, record in enumerate(value):
        errors.extend(validate_envelope(record, f"records[{index}]"))
    if any(not isinstance(record, dict) for record in value):
        return errors

    first = value[0]
    for index, record in enumerate(value[1:], 1):
        for key in ("contract_version", "run_id", "target_id", "selected_module"):
            if key in first and key in record and first[key] != record[key]:
                errors.append(f"records[{index}].{key}: differs from records[0]")

    previous_stage = -1
    oracle_index: int | None = None
    reporter_index: int | None = None
    specialist_seen = False
    for index, record in enumerate(value):
        producer = record.get("producer")
        if not isinstance(producer, str):
            continue
        stage = STAGE.get(producer)
        if stage is None:
            continue
        if stage < previous_stage:
            errors.append(f"records[{index}]: producer is out of flow order")
        previous_stage = max(previous_stage, stage)
        if producer in MODULES:
            specialist_seen = True
        if producer == "ORACLE":
            if oracle_index is not None:
                errors.append(f"records[{index}]: a run has only one final ORACLE decision")
            if not specialist_seen:
                errors.append(f"records[{index}]: ORACLE needs a preceding specialist")
            oracle_index = index
        if producer == "REPORTER":
            if reporter_index is not None:
                errors.append(f"records[{index}]: duplicate REPORTER envelope")
            if oracle_index is None:
                errors.append(f"records[{index}]: REPORTER needs a preceding ORACLE")
            else:
                oracle_status = value[oracle_index].get("status")
                if record.get("status") != oracle_status:
                    errors.append(
                        f"records[{index}].status: REPORTER must preserve ORACLE status"
                    )
                oracle_evidence = value[oracle_index].get("evidence")
                if record.get("evidence") != oracle_evidence:
                    errors.append(
                        f"records[{index}].evidence: REPORTER must preserve ORACLE evidence"
                    )
            reporter_index = index
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate mock RedHarness v1 JSON envelopes; no network requests."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JSON fixture path(s)")
    args = parser.parse_args(argv)

    failed = False
    for path in args.paths:
        try:
            with path.open(encoding="utf-8-sig") as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{path}: FAIL: {exc}", file=sys.stderr)
            failed = True
            continue
        errors = validate_document(value)
        if errors:
            print(f"{path}: FAIL", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            failed = True
        else:
            count = len(value) if isinstance(value, list) else 1
            print(f"{path}: PASS ({count} envelope(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
