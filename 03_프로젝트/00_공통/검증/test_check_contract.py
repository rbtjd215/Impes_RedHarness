"""Meaningful contract checks with fixture data only; no live target calls."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from check_contract import validate_document, validate_envelope


HERE = Path(__file__).resolve().parent


def fixture(name: str) -> list[dict]:
    with (HERE / "fixtures" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


class ContractTests(unittest.TestCase):
    def test_a_mock_pass_chain(self) -> None:
        self.assertEqual(validate_document(fixture("mock_a_pass.json")), [])

    def test_b_mock_unknown_chain(self) -> None:
        self.assertEqual(validate_document(fixture("mock_b_unknown.json")), [])

    def test_specialist_cannot_mark_final_pass(self) -> None:
        records = fixture("mock_a_pass.json")
        records[1]["status"] = "PASS"
        self.assertIn("only ORACLE", " ".join(validate_document(records)))

    def test_specialist_cannot_mark_final_fail(self) -> None:
        records = fixture("mock_b_unknown.json")
        records[1]["status"] = "FAIL"
        self.assertIn("only ORACLE", " ".join(validate_document(records)))

    def test_oracle_pass_requires_evidence(self) -> None:
        records = fixture("mock_a_pass.json")
        records[2]["evidence"] = []
        self.assertIn("requires recorded evidence", " ".join(validate_document(records)))

    def test_oracle_fail_with_failure_evidence(self) -> None:
        records = fixture("mock_b_unknown.json")
        records[2]["status"] = "FAIL"
        records[2]["evidence"] = [{"source": "mock verifier", "failure": "criterion not met"}]
        records[3]["status"] = "FAIL"
        records[3]["evidence"] = copy.deepcopy(records[2]["evidence"])
        self.assertEqual(validate_document(records), [])

    def test_reporter_must_preserve_oracle_status(self) -> None:
        records = fixture("mock_a_pass.json")
        records[3]["status"] = "UNKNOWN"
        self.assertIn("must preserve ORACLE status", " ".join(validate_document(records)))

    def test_reporter_must_preserve_oracle_evidence(self) -> None:
        records = fixture("mock_a_pass.json")
        records[3]["evidence"] = [{"source": "reporter", "value": "invented"}]
        self.assertIn("must preserve ORACLE evidence", " ".join(validate_document(records)))

    def test_reporter_preserves_both_status_and_evidence(self) -> None:
        records = fixture("mock_a_pass.json")
        self.assertEqual(records[3]["status"], records[2]["status"])
        self.assertEqual(records[3]["evidence"], records[2]["evidence"])
        self.assertEqual(validate_document(records), [])

    def test_reporter_needs_oracle_in_same_chain(self) -> None:
        records = fixture("mock_a_pass.json")
        self.assertIn("needs a preceding ORACLE", " ".join(validate_document(records[:2] + records[3:])))

    def test_rejects_changed_run_id(self) -> None:
        records = fixture("mock_a_pass.json")
        records[2]["run_id"] = "OTHER-RUN"
        self.assertIn("differs from records[0]", " ".join(validate_document(records)))

    def test_rejects_wrong_specialist_and_module(self) -> None:
        records = fixture("mock_b_unknown.json")
        records[1]["producer"] = "A"
        self.assertIn("does not match selected_module", " ".join(validate_document(records)))

    def test_rejects_missing_field(self) -> None:
        record = fixture("mock_a_pass.json")[1]
        del record["target_id"]
        self.assertIn("missing fields", " ".join(validate_envelope(record)))

    def test_malformed_enum_types_return_errors_not_exceptions(self) -> None:
        record = fixture("mock_a_pass.json")[1]
        record["selected_module"] = ["A"]
        record["producer"] = ["A"]
        record["status"] = ["PASS"]
        errors = validate_document(record)
        self.assertIn("expected A or B", " ".join(errors))
        self.assertIn("invalid producer", " ".join(errors))
        self.assertIn("invalid status", " ".join(errors))

    def test_empty_next_action_is_valid_string(self) -> None:
        record = fixture("mock_a_pass.json")[1]
        record["next_action"] = ""
        self.assertEqual(validate_document(record), [])

    def test_non_string_next_action_is_rejected(self) -> None:
        record = fixture("mock_a_pass.json")[1]
        record["next_action"] = None
        self.assertIn("expected a string", " ".join(validate_document(record)))

    def test_single_specialist_envelope_is_valid_for_drafting(self) -> None:
        record = fixture("mock_a_pass.json")[1]
        self.assertEqual(validate_document(record), [])

    def test_single_reporter_cannot_claim_parity(self) -> None:
        record = fixture("mock_a_pass.json")[3]
        self.assertIn("needs an ORACLE envelope", " ".join(validate_document(record)))

    def test_rejects_duplicate_oracle_final_decision(self) -> None:
        records = fixture("mock_a_pass.json")
        records.insert(3, copy.deepcopy(records[2]))
        self.assertIn("only one final ORACLE", " ".join(validate_document(records)))


if __name__ == "__main__":
    unittest.main()
