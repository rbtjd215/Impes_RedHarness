"""Reporter round-trip, mutation and failure tests for the optional reference."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_contract import validate_complete_run
from run_mock_pipeline import build_mock_run, main, store_run


class MockPipelineTests(unittest.TestCase):
    def test_roundtrip_all_states_preserves_previous_envelopes_and_input(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for state in ("PASS", "FAIL", "UNKNOWN", "NOT_RUN"):
                with self.subTest(state=state):
                    records = build_mock_run(state)
                    original = copy.deepcopy(records)
                    path = Path(folder) / f"{state}.json"
                    outcome = store_run(records, path)
                    restored = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(outcome["storage"], "written_and_verified")
                    self.assertEqual(records, original)
                    self.assertEqual(restored[:3], original[:3])
                    self.assertEqual(restored[3]["status"], original[2]["status"])
                    self.assertEqual(restored[3]["evidence"], original[2]["evidence"])
                    self.assertEqual(validate_complete_run(restored), [])

    def test_write_failure_preserves_oracle_verdict_and_cleans_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            records = build_mock_run("PASS")
            original = copy.deepcopy(records)
            with patch("run_mock_pipeline.os.replace", side_effect=PermissionError("synthetic denied")):
                outcome = store_run(records, Path(folder) / "result.json")
            self.assertEqual(outcome["storage"], "failed")
            self.assertEqual(outcome["status"], original[2]["status"])
            self.assertEqual(outcome["evidence"], original[2]["evidence"])
            self.assertEqual(outcome["error"], {"kind": "storage_error", "exception_type": "PermissionError"})
            self.assertEqual(outcome["reporter"]["status"], "PASS")
            self.assertEqual(outcome["reporter"]["evidence"], original[2]["evidence"])
            self.assertEqual(validate_complete_run(original[:3] + [outcome["reporter"]]), [])
            self.assertEqual(outcome["reporter"]["error"]["kind"], "storage_error")
            self.assertEqual(records, original)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_reread_corruption_is_not_reported_as_storage_success(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            records = build_mock_run("PASS")
            wrong = copy.deepcopy(records)
            wrong[3]["status"] = "FAIL"
            with patch("run_mock_pipeline.json.load", return_value=wrong):
                outcome = store_run(records, Path(folder) / "result.json")
            self.assertEqual(outcome["storage"], "failed")
            self.assertEqual(outcome["status"], "PASS")
            self.assertEqual(outcome["error"]["kind"], "storage_error")

    def test_successful_retry_clears_only_reporter_storage_error(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            original = build_mock_run("PASS")
            path = Path(folder) / "result.json"
            with patch("run_mock_pipeline.os.replace", side_effect=PermissionError("synthetic denied")):
                failed = store_run(original, path)
            retry = original[:3] + [failed["reporter"]]
            before_retry = copy.deepcopy(retry)
            self.assertEqual(validate_complete_run(retry), [])
            outcome = store_run(retry, path)
            restored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(outcome["storage"], "written_and_verified")
            self.assertIsNone(outcome["error"])
            self.assertIsNone(outcome["reporter"]["error"])
            self.assertIsNone(restored[3]["error"])
            self.assertEqual(restored[:3], before_retry[:3])
            self.assertEqual(retry, before_retry)
            self.assertEqual(validate_complete_run(restored), [])

    def test_invalid_partial_run_is_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            with self.assertRaisesRegex(ValueError, "exactly four"):
                store_run(build_mock_run("PASS")[:2], path)
            self.assertFalse(path.exists())

    def test_single_command_reproduces_four_states_for_b(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(main(["--all", "--module", "B", "--output-dir", folder]), 0)
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 4)


if __name__ == "__main__":
    unittest.main()
