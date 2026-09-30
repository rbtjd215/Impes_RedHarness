"""Offline contract and candidate checks for the B mock adapter."""

from __future__ import annotations

import unittest
import sys
import copy
from pathlib import Path

from mock_adapter import analyze_mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_공통" / "검증"))
from check_contract import validate_complete_run, validate_document
from run_mock_pipeline import build_mock_run


def dispatcher(observation: dict | None = None) -> dict:
    return {
        "contract_version": "1.0",
        "run_id": "RH-MOCK-B-01",
        "target_id": "RH-CASE-01-MOCK",
        "selected_module": "B",
        "producer": "DISPATCHER",
        "observation": observation if observation is not None else {},
        "actions": [],
        "status": "NOT_RUN",
        "evidence": [],
        "error": None,
        "next_action": "Pass synthetic observation to B",
    }


class BMockAdapterTests(unittest.TestCase):
    def test_no_observation_means_not_run(self) -> None:
        result = analyze_mock(dispatcher())
        self.assertEqual(result["status"], "NOT_RUN")
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["evidence"], [])

    def test_reflected_text_is_candidate_only(self) -> None:
        result = analyze_mock(dispatcher({"response_html": "<p>RHMARK</p>", "marker": "RHMARK"}))
        self.assertEqual(result["producer"], "B")
        self.assertEqual(result["selected_module"], "B")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["kind"], "reflected_marker_candidate")
        self.assertEqual(result["evidence"][0]["contexts"], ["text"])
        self.assertNotIn("response_html", result["observation"])

    def test_reflected_attribute_and_comment_are_labelled(self) -> None:
        result = analyze_mock(dispatcher({
            "response_html": '<div title="RHMARK"></div><!-- RHMARK -->',
            "marker": "RHMARK",
        }))
        self.assertEqual(result["evidence"][0]["contexts"], ["attribute", "comment"])

    def test_absent_marker_has_no_reflection_evidence(self) -> None:
        result = analyze_mock(dispatcher({"response_html": "<p>no marker</p>", "marker": "RHMARK"}))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["evidence"], [])

    def test_direct_dom_source_to_sink_is_candidate_only(self) -> None:
        result = analyze_mock(dispatcher({"script_source": "box.innerHTML = location.hash;"}))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["kind"], "dom_source_sink_candidate")
        self.assertEqual(result["evidence"][0]["source"], "location.hash")
        self.assertEqual(result["evidence"][0]["sink"], "innerHTML")

    def test_ordered_variable_dom_flow(self) -> None:
        result = analyze_mock(dispatcher({
            "script_source": "const sample = location.search; box.innerHTML = sample;"
        }))
        self.assertEqual(result["evidence"][0]["source"], "location.search")

    def test_disconnected_dom_source_and_sink_is_not_a_candidate(self) -> None:
        result = analyze_mock(dispatcher({
            "script_source": "const unused = location.hash; box.innerHTML = 'fixed text';"
        }))
        self.assertEqual(result["evidence"], [])

    def test_upstream_error_does_not_run_or_echo_error(self) -> None:
        item = dispatcher({"script_source": "box.innerHTML = location.hash;"})
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
        item["selected_module"] = "A"
        with self.assertRaisesRegex(ValueError, "selected for B"):
            analyze_mock(item)

    def test_missing_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires a short inert marker"):
            analyze_mock(dispatcher({"response_html": "<p>RHMARK</p>"}))

    def test_malformed_observation_and_final_input_are_rejected(self) -> None:
        item = dispatcher()
        item["observation"] = []
        with self.assertRaisesRegex(ValueError, "observation"):
            analyze_mock(item)
        item = dispatcher()
        item["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "final status"):
            analyze_mock(item)

    def test_no_valid_run_can_return_final_pass_or_fail(self) -> None:
        for observation in ({}, {"response_html": "RHMARK", "marker": "RHMARK"},
                            {"script_source": "box.innerHTML = location.hash;"}):
            self.assertIn(analyze_mock(dispatcher(observation))["status"], {"UNKNOWN", "NOT_RUN"})

    def test_malformed_status_types_raise_value_error(self) -> None:
        for status in ([], {}):
            item = dispatcher()
            item["status"] = status
            with self.assertRaisesRegex(ValueError, "final status"):
                analyze_mock(item)

    def test_generated_envelopes_satisfy_shared_contract(self) -> None:
        for observation, upstream_error in (
            ({}, None),
            ({"response_html": "<p>RHMARK</p>", "marker": "RHMARK"}, None),
            ({"script_source": "box.innerHTML = location.hash;"}, None),
            ({"script_source": "box.innerHTML = location.hash;"}, "synthetic upstream error"),
        ):
            source = dispatcher(observation)
            source["error"] = upstream_error
            self.assertEqual(validate_document([source, analyze_mock(source)]), [])

    def test_complete_profile_accepts_b_candidate_and_keeps_input_unchanged(self) -> None:
        records = build_mock_run("UNKNOWN", "B")
        records[0]["observation"].update(response_html="<p>RHMARK</p>", marker="RHMARK")
        original = copy.deepcopy(records[0])
        records[1] = analyze_mock(records[0])
        self.assertEqual(records[0], original)
        self.assertEqual(validate_complete_run(records), [])
        self.assertEqual(records[2]["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
