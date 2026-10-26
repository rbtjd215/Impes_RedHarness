"""Oracle for explicit synthetic observations only; no target or model calls."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

_validator_path = Path(__file__).resolve().parents[1] / "00_공통/검증/check_contract.py"
_spec = importlib.util.spec_from_file_location("oracle_contract_v1", _validator_path)
_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract)
validate_complete_run = _contract.validate_complete_run


class InputError(ValueError):
    """Invalid offline interface input, distinct from a target FAIL verdict."""


def json_copy(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, OverflowError):
        raise InputError("Expected finite JSON data") from None


def action(kind, summary, **extra):
    return dict(kind=kind, source="synthetic-oracle-reporter", summary=summary, **extra)


def decide(specialist, criterion, check=None):
    """Compare an explicit mock check with distinct success/failure values.

    check is supplied by the offline fixture caller, never extracted from an
    A/B success claim. This is not an authentication or evidence-truth boundary.
    """
    specialist, criterion, check = json_copy([specialist, criterion, check])
    if _contract.validate_envelope(specialist):
        raise InputError("Invalid specialist envelope")
    if (specialist["producer"] not in ("A", "B")
            or specialist["target_id"] != "SYNTHETIC-ONLY"
            or specialist["observation"].get("execution_mode") != "offline_mock"):
        raise InputError("Only synthetic specialist input is supported")
    active = bool(specialist["actions"])
    if specialist["status"] != ("UNKNOWN" if active else "NOT_RUN"):
        raise InputError("Specialist status must agree with activity")
    if (not isinstance(criterion, dict)
            or not isinstance(criterion.get("criterion_id"), str)
            or not criterion["criterion_id"].strip()
            or criterion.get("target_id") != specialist["target_id"]
            or criterion.get("selected_module") != specialist["selected_module"]
            or any(not isinstance(criterion.get(key), str) or not criterion[key]
                   for key in ("success_value", "failure_value"))
            or criterion["success_value"] == criterion["failure_value"]):
        raise InputError("Invalid synthetic criterion")
    oracle = {key: copy.deepcopy(specialist[key]) for key in
              ("contract_version", "run_id", "target_id", "selected_module")}
    oracle.update(producer="ORACLE", observation={"execution_mode": "offline_mock"},
                  actions=[], status="UNKNOWN" if active else "NOT_RUN", evidence=[],
                  error=None, next_action="Preserve verdict and obtain missing mock evidence")
    if check is not None:
        if (not isinstance(check, dict)
                or any(check.get(key) != specialist[key]
                       for key in ("run_id", "target_id", "selected_module"))
                or check.get("criterion_id") != criterion["criterion_id"]
                or check.get("execution_mode") != "offline_mock"
                or check.get("source") != "synthetic-observer"
                or type(check.get("attempted")) is not bool
                or type(check.get("completed")) is not bool
                or check.get("execution_basis") not in ("specialist_execution", "independent_check")
                or (check["completed"] and not check["attempted"])
                or (check["attempted"] and check["execution_basis"] == "specialist_execution" and not active)):
            raise InputError("Invalid synthetic check or mismatched identifiers")
        if check["attempted"]:
            oracle["status"] = "UNKNOWN"
            oracle["actions"] = [action("verify", "Compare synthetic observation with criterion",
                                         criterion_id=criterion["criterion_id"])]
            if check.get("error") is not None:
                oracle["error"] = {"kind": "mock_check_error"}
            elif check["completed"]:
                value = check.get("observed_value")
                if value == criterion["success_value"]:
                    oracle["status"] = "PASS"
                elif value == criterion["failure_value"]:
                    oracle["status"] = "FAIL"
                if oracle["status"] in ("PASS", "FAIL"):
                    oracle["evidence"] = [{
                        "kind": "verification", "source": "synthetic-observer",
                        "criterion_id": criterion["criterion_id"],
                        "summary": "Compared an explicit synthetic observation; no real target",
                        "execution_mode": "offline_mock", "execution_basis": check["execution_basis"],
                        "result": "matched" if oracle["status"] == "PASS" else "not_matched",
                    }]
                    oracle["next_action"] = "Preserve the synthetic Oracle verdict"
    # Reuse the complete profile for action/evidence and cross-stage semantics.
    dispatcher = copy.deepcopy(specialist)
    dispatcher.update(producer="DISPATCHER", status="NOT_RUN", actions=[], evidence=[], error=None)
    reporter = copy.deepcopy(oracle)
    reporter["producer"] = "REPORTER"
    if validate_complete_run([dispatcher, specialist, oracle, reporter]):
        raise InputError("Input or output does not satisfy complete-v1")
    return oracle
