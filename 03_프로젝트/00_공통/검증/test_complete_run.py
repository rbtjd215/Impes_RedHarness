"""Tests for meaningful complete-v1 gaps; all observations are synthetic."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from check_contract import validate_complete_run, validate_document
from run_mock_pipeline import build_mock_run


class CompleteRunTests(unittest.TestCase):
    def assert_rejected(self, records: object, fragment: str) -> None:
        self.assertIn(fragment, " ".join(validate_complete_run(records)))

    def test_four_final_states_for_both_modules_are_valid(self) -> None:
        for module in ("A", "B"):
            for state in ("PASS", "FAIL", "UNKNOWN", "NOT_RUN"):
                with self.subTest(module=module, state=state):
                    self.assertEqual(validate_complete_run(build_mock_run(state, module)), [])

    def test_checked_in_complete_fixtures_are_valid(self) -> None:
        folder = Path(__file__).parent / "fixtures" / "complete"
        self.assertEqual(len(list(folder.glob("*.json"))), 4)
        for path in folder.glob("*.json"):
            with self.subTest(path=path.name):
                self.assertEqual(validate_complete_run(json.loads(path.read_text(encoding="utf-8"))), [])

    def test_legacy_partial_drafting_remains_valid_but_not_complete(self) -> None:
        record = build_mock_run("PASS")[1]
        self.assertEqual(validate_document(record), [])
        self.assert_rejected(record, "exactly four")

    def test_complete_requires_every_stage_and_no_duplicates(self) -> None:
        records = build_mock_run("PASS")
        for index in range(4):
            with self.subTest(missing=index):
                self.assert_rejected(records[:index] + records[index + 1:], "exactly four")
        duplicate = copy.deepcopy(records)
        duplicate[3] = copy.deepcopy(duplicate[2])
        self.assert_rejected(duplicate, "only one final ORACLE")
        self.assert_rejected(duplicate, "selected specialist, ORACLE, REPORTER")

    def test_rejects_changed_run_identifiers_and_final_specialist(self) -> None:
        for key in ("contract_version", "run_id", "target_id", "selected_module"):
            records = build_mock_run("PASS")
            records[2][key] = "other"
            with self.subTest(key=key):
                self.assert_rejected(records, "differs from records[0]")
        records = build_mock_run("PASS")
        records[1]["status"] = "PASS"
        self.assert_rejected(records, "only ORACLE")

    def test_null_evidence_is_rejected_only_by_complete_profile(self) -> None:
        records = build_mock_run("PASS")
        records[2]["evidence"] = records[3]["evidence"] = [None]
        self.assertEqual(validate_document(records), [])
        self.assert_rejected(records, "expected an evidence object")

    def test_evidence_needs_minimum_structure_and_safe_summary_or_reference(self) -> None:
        for key in ("kind", "source", "criterion_id", "summary", "execution_mode"):
            records = build_mock_run("PASS")
            del records[2]["evidence"][0][key]
            records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
            with self.subTest(key=key):
                self.assertTrue(validate_complete_run(records))
        records = build_mock_run("PASS")
        item = records[2]["evidence"][0]
        del item["summary"]
        item["evidence_ref"] = "synthetic-artifact:completion-check"
        records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
        self.assertEqual(validate_complete_run(records), [])

    def test_malformed_criterion_returns_errors_without_exception(self) -> None:
        records = build_mock_run("PASS")
        records[2]["evidence"][0]["criterion_id"] = []
        records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
        self.assert_rejected(records, "criterion_id")

    def test_success_evidence_cannot_support_fail(self) -> None:
        records = build_mock_run("PASS")
        records[2]["status"] = records[3]["status"] = "FAIL"
        self.assert_rejected(records, "verification result must support")

    def test_candidate_is_not_final_verification(self) -> None:
        records = build_mock_run("PASS")
        records[2]["evidence"][0]["kind"] = "candidate"
        records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
        self.assert_rejected(records, "needs verification evidence")

    def test_final_verification_needs_matching_recorded_check(self) -> None:
        records = build_mock_run("PASS")
        records[2]["actions"][0]["criterion_id"] = "different-criterion"
        self.assert_rejected(records, "matching ORACLE verify action")

    def test_not_run_specialist_can_have_independent_oracle_verification(self) -> None:
        records = build_mock_run("PASS")
        records[1].update(status="NOT_RUN", actions=[])
        self.assert_rejected(records, "specialist_execution needs recorded")
        records[2]["evidence"][0]["execution_basis"] = "independent_check"
        records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
        self.assertEqual(validate_complete_run(records), [])

    def test_not_run_and_unknown_require_consistent_recorded_activity(self) -> None:
        records = build_mock_run("NOT_RUN")
        records[1] = build_mock_run("UNKNOWN")[1]
        records[1]["run_id"] = records[0]["run_id"]
        self.assert_rejected(records, "NOT_RUN requires no recorded execution")
        records = build_mock_run("UNKNOWN")
        records[1]["actions"] = records[2]["actions"] = []
        self.assert_rejected(records, "UNKNOWN needs recorded activity")

    def test_mock_and_real_modes_cannot_be_mixed(self) -> None:
        records = build_mock_run("PASS")
        records[1]["observation"]["execution_mode"] = "local_lab"
        self.assert_rejected(records, "execution_mode must be consistent")

    def test_actions_require_objects_with_kind_source_and_summary(self) -> None:
        for action in (None, {}, {"kind": "check", "source": "fixture"}):
            records = build_mock_run("UNKNOWN")
            records[1]["actions"] = [action]
            with self.subTest(action=action):
                self.assertTrue(validate_complete_run(records))

    def test_reporter_parity_is_checked_in_complete_mode(self) -> None:
        for key in ("status", "evidence"):
            records = build_mock_run("PASS")
            records[3][key] = "UNKNOWN" if key == "status" else []
            with self.subTest(key=key):
                self.assert_rejected(records, "REPORTER must preserve")

    def test_reporter_storage_error_does_not_invalidate_oracle_verdict(self) -> None:
        records = build_mock_run("PASS")
        records[3]["observation"]["storage"] = "failed"
        records[3]["error"] = {"kind": "storage_error"}
        self.assertEqual(validate_complete_run(records), [])
        self.assertEqual(records[3]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
