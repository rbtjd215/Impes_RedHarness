"""Offline 2FA observation adapter for the RedHarness A contract.

This module reads only an in-memory, synthetic v1 envelope. It does not send
HTTP requests, use accounts or cookies, contact an external service, or decide
the final result.
"""

from __future__ import annotations

from typing import Any


_FIELDS = {
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
_ACCESS_RESULTS = {"granted", "denied", "indeterminate"}
_SOURCE = "A offline 2FA mock adapter"
_CRITERION_ID = "AUTH-2FA-ENFORCEMENT"


def _validate_input(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ValueError("input must be a v1 envelope object")
    missing = sorted(_FIELDS - envelope.keys())
    if missing:
        raise ValueError("missing v1 fields: " + ", ".join(missing))
    if envelope["contract_version"] != "1.0":
        raise ValueError("contract_version must be 1.0")
    for key in ("run_id", "target_id"):
        if not isinstance(envelope[key], str) or not envelope[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if envelope["selected_module"] != "A" or envelope["producer"] != "DISPATCHER":
        raise ValueError("A mock adapter requires a Dispatcher envelope selected for A")
    if not isinstance(envelope["status"], str) or envelope["status"] not in {
        "NOT_RUN",
        "UNKNOWN",
    }:
        raise ValueError("Dispatcher input cannot contain a final status")
    if not isinstance(envelope["observation"], dict):
        raise ValueError("observation must be an object")
    if not isinstance(envelope["actions"], list) or not isinstance(
        envelope["evidence"], list
    ):
        raise ValueError("actions and evidence must be arrays")
    if envelope["error"] is not None and not isinstance(
        envelope["error"], (str, dict)
    ):
        raise ValueError("error must be null, a string, or an object")
    if not isinstance(envelope["next_action"], str):
        raise ValueError("next_action must be a string")

    observation = envelope["observation"]
    has_auth_state = "auth_state" in observation
    has_resource = "protected_resource" in observation
    if not has_auth_state and not has_resource:
        if "execution_mode" in observation and observation["execution_mode"] != "offline_mock":
            raise ValueError("A mock adapter accepts only offline_mock observations")
        return envelope
    if not has_auth_state or not has_resource:
        raise ValueError("auth_state and protected_resource must be provided together")
    if observation.get("execution_mode") != "offline_mock":
        raise ValueError("2FA mock observation requires execution_mode offline_mock")

    auth_state = observation["auth_state"]
    if not isinstance(auth_state, dict):
        raise ValueError("auth_state must be an object")
    for key in ("primary_authenticated", "second_factor_verified"):
        if not isinstance(auth_state.get(key), bool):
            raise ValueError(f"auth_state.{key} must be a boolean")

    protected_resource = observation["protected_resource"]
    if not isinstance(protected_resource, dict):
        raise ValueError("protected_resource must be an object")
    if not isinstance(protected_resource.get("request_attempted"), bool):
        raise ValueError("protected_resource.request_attempted must be a boolean")
    if protected_resource.get("access_result") not in _ACCESS_RESULTS:
        raise ValueError(
            "protected_resource.access_result must be granted, denied, or indeterminate"
        )
    if "http_status" in protected_resource and (
        isinstance(protected_resource["http_status"], bool)
        or not isinstance(protected_resource["http_status"], int)
        or not 100 <= protected_resource["http_status"] <= 599
    ):
        raise ValueError("protected_resource.http_status must be an integer from 100 to 599")
    if "redirected_to_second_factor" in protected_resource and not isinstance(
        protected_resource["redirected_to_second_factor"], bool
    ):
        raise ValueError("protected_resource.redirected_to_second_factor must be a boolean")
    return envelope


def analyze_mock(envelope: Any) -> dict[str, Any]:
    """Return an A v1 envelope with a 2FA candidate, never a final verdict.

    The input may describe a synthetic authentication state and a synthetic
    protected-resource observation. Raw response content and identifiers beyond
    the v1 envelope are not copied to the output. Invalid input raises
    ``ValueError`` and produces no output envelope.
    """
    source = _validate_input(envelope)
    input_observation = source["observation"]
    auth_state = input_observation.get("auth_state")
    protected_resource = input_observation.get("protected_resource")

    ran = bool(
        source["error"] is None
        and isinstance(protected_resource, dict)
        and protected_resource["request_attempted"]
    )
    candidate = bool(
        ran
        and isinstance(auth_state, dict)
        and auth_state["primary_authenticated"]
        and not auth_state["second_factor_verified"]
        and protected_resource["access_result"] == "granted"
    )

    actions: list[dict[str, str]] = []
    evidence: list[dict[str, str]] = []
    if ran:
        actions.append(
            {
                "kind": "offline_mock_2fa_check",
                "source": _SOURCE,
                "summary": (
                    "Compare synthetic second-factor state with the "
                    "protected-resource observation"
                ),
            }
        )
    if candidate:
        evidence.append(
            {
                "kind": "multi_step_auth_candidate",
                "source": _SOURCE,
                "criterion_id": _CRITERION_ID,
                "summary": (
                    "Synthetic protected-resource access was observed before "
                    "second-factor verification"
                ),
                "execution_mode": "offline_mock",
            }
        )

    if candidate:
        next_action = "Send the 2FA enforcement candidate to Oracle for verification"
    elif ran:
        next_action = "Send the mock observation to Oracle; final classification remains with Oracle"
    else:
        next_action = "Provide a complete offline 2FA observation or resolve the upstream error"

    return {
        "contract_version": "1.0",
        "run_id": source["run_id"],
        "target_id": source["target_id"],
        "selected_module": "A",
        "producer": "A",
        "observation": {
            "execution_mode": "offline_mock",
            "scenario": "multi_step_authentication",
            "request_attempted": ran,
            "candidate_count": len(evidence),
        },
        "actions": actions,
        "status": "UNKNOWN" if ran else "NOT_RUN",
        "evidence": evidence,
        "error": {"kind": "upstream_error"} if source["error"] is not None else None,
        "next_action": next_action,
    }
