"""Offline contract and 2FA-candidate checks for the A mock adapter."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

from mock_adapter import analyze_mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_공통" / "검증"))
from check_contract import validate_complete_run, validate_document
from run_mock_pipeline import build_mock_run


def dispatcher(observation: dict | None = None) -> dict:
    return {
        "contract_version": "1.0",
        "run_id": "RH-MOCK-A-2FA-01",
        "target_id": "RH-CASE-01-MOCK",
        "selected_module": "A",
        "producer": "DISPATCHER",
        "observation": observation if observation is not None else {},
        "actions": [],
        "status": "NOT_RUN",
        "evidence": [],
        "error": None,
        "next_action": "Pass the synthetic 2FA observation to A",
    }


def two_factor_observation(
    *,
    primary_authenticated: bool = True,
    second_factor_verified: bool = False,
    request_attempted: bool = True,
    access_result: str = "granted",
) -> dict:
    return {
        "execution_mode": "offline_mock",
        "auth_state": {
            "primary_authenticated": primary_authenticated,
            "second_factor_verified": second_factor_verified,
        },
        "protected_resource": {
            "request_attempted": request_attempted,
            "access_result": access_result,
            "http_status": 200,
            "redirected_to_second_factor": False,
        },
    }


class AMockAdapterTests(unittest.TestCase):
    def test_no_observation_means_not_run(self) -> None:
        result = analyze_mock(dispatcher())
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["evidence"], [])

    def test_unverified_second_factor_and_granted_access_is_candidate_only(self) -> None:
        result = analyze_mock(dispatcher(two_factor_observation()))
        self.assertEqual(result["producer"], "A")
        self.assertEqual(result["selected_module"], "A")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["kind"], "multi_step_auth_candidate")
        self.assertEqual(result["evidence"][0]["criterion_id"], "AUTH-2FA-ENFORCEMENT")

    def test_denied_access_is_observed_without_candidate(self) -> None:
        result = analyze_mock(
            dispatcher(two_factor_observation(access_result="denied"))
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["evidence"], [])

    def test_verified_second_factor_does_not_create_bypass_candidate(self) -> None:
        result = analyze_mock(
            dispatcher(two_factor_observation(second_factor_verified=True))
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["evidence"], [])

    def test_unattempted_request_remains_not_run(self) -> None:
        result = analyze_mock(
            dispatcher(two_factor_observation(request_attempted=False))
        )
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["evidence"], [])

    def test_upstream_error_does_not_run_or_echo_error(self) -> None:
        item = dispatcher(two_factor_observation())
        item["error"] = "private upstream detail"
        result = analyze_mock(item)
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertEqual(result["error"], {"kind": "upstream_error"})
        self.assertEqual(result["evidence"], [])

    def test_missing_required_field_is_rejected(self) -> None:
        item = dispatcher()
        del item["run_id"]
        with self.assertRaisesRegex(ValueError, "run_id"):
            analyze_mock(item)

    def test_wrong_module_is_rejected(self) -> None:
        item = dispatcher()
        item["selected_module"] = "B"
        with self.assertRaisesRegex(ValueError, "selected for A"):
            analyze_mock(item)

    def test_partial_or_live_observation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "provided together"):
            analyze_mock(
                dispatcher(
                    {
                        "execution_mode": "offline_mock",
                        "auth_state": {
                            "primary_authenticated": True,
                            "second_factor_verified": False,
                        },
                    }
                )
            )
        live = two_factor_observation()
        live["execution_mode"] = "local_lab"
        with self.assertRaisesRegex(ValueError, "offline_mock"):
            analyze_mock(dispatcher(live))

    def test_malformed_domain_fields_are_rejected(self) -> None:
        malformed = two_factor_observation()
        malformed["auth_state"]["second_factor_verified"] = "no"
        with self.assertRaisesRegex(ValueError, "second_factor_verified"):
            analyze_mock(dispatcher(malformed))

        malformed = two_factor_observation()
        malformed["protected_resource"]["http_status"] = True
        with self.assertRaisesRegex(ValueError, "http_status"):
            analyze_mock(dispatcher(malformed))

    def test_malformed_envelope_and_final_input_are_rejected(self) -> None:
        item = dispatcher()
        item["observation"] = []
        with self.assertRaisesRegex(ValueError, "observation"):
            analyze_mock(item)
        item = dispatcher()
        item["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "final status"):
            analyze_mock(item)

    def test_output_does_not_echo_raw_mock_details_or_mutate_input(self) -> None:
        item = dispatcher(two_factor_observation())
        item["observation"]["raw_response"] = "synthetic detail that must not be copied"
        original = copy.deepcopy(item)
        result = analyze_mock(item)
        self.assertEqual(item, original)
        self.assertNotIn("auth_state", result["observation"])
        self.assertNotIn("protected_resource", result["observation"])
        self.assertNotIn("raw_response", result["observation"])

    def test_no_valid_run_can_return_final_pass_or_fail(self) -> None:
        for observation in (
            {},
            two_factor_observation(),
            two_factor_observation(access_result="denied"),
        ):
            self.assertIn(
                analyze_mock(dispatcher(observation))["status"],
                {"UNKNOWN", "NOT_RUN"},
            )

    def test_generated_envelopes_satisfy_shared_contract(self) -> None:
        for observation, upstream_error in (
            ({}, None),
            (two_factor_observation(), None),
            (two_factor_observation(access_result="denied"), None),
            (two_factor_observation(), "synthetic upstream error"),
        ):
            source = dispatcher(observation)
            source["error"] = upstream_error
            self.assertEqual(validate_document([source, analyze_mock(source)]), [])

    def test_complete_profile_accepts_a_candidate(self) -> None:
        records = build_mock_run("UNKNOWN", "A")
        records[0]["observation"] = two_factor_observation()
        records[1] = analyze_mock(records[0])
        self.assertEqual(validate_complete_run(records), [])
        self.assertEqual(records[1]["status"], "UNKNOWN")
        self.assertEqual(records[2]["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
