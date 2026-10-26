"""Behavioral checks for the synthetic Oracle/Reporter implementation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offline_oracle import InputError, decide, validate_complete_run
from offline_reporter import read_run, store
from run_offline import inputs, load_cases


class OracleTests(unittest.TestCase):
    def sample(self, case_id="OR-01", module="A"):
        case = next(case for case in load_cases() if case["id"] == case_id)
        return inputs(case, module)

    def test_or_01_to_08_both_modules_and_input_immutability(self):
        for module in ("A", "B"):
            for case in load_cases():
                with self.subTest(module=module, case=case["id"]):
                    dispatcher, specialist, criterion, check = inputs(case, module)
                    before = copy.deepcopy((specialist, criterion, check))
                    oracle = decide(specialist, criterion, check)
                    self.assertEqual(oracle["status"], case["expected_status"])
                    self.assertEqual((specialist, criterion, check), before)
                    reporter = copy.deepcopy(oracle)
                    reporter["producer"] = "REPORTER"
                    self.assertEqual(validate_complete_run([dispatcher, specialist, oracle, reporter]), [])
                    if oracle["status"] in ("PASS", "FAIL"):
                        self.assertEqual(oracle["evidence"][0]["criterion_id"], oracle["actions"][0]["criterion_id"])
                        self.assertEqual(oracle["evidence"][0]["execution_basis"], check["execution_basis"])
                    else:
                        self.assertEqual(oracle["evidence"], [])

    def test_or_09_reject_missing_field(self):
        _, specialist, criterion, check = self.sample()
        del specialist["run_id"]
        with self.assertRaises(InputError):
            decide(specialist, criterion, check)

    def test_or_09_reject_specialist_final_status(self):
        for status in ("PASS", "FAIL"):
            _, specialist, criterion, check = self.sample()
            specialist["status"] = status
            with self.assertRaises(InputError):
                decide(specialist, criterion, check)

    def test_or_09_reject_check_identity_changes(self):
        for key in ("run_id", "target_id", "selected_module", "criterion_id", "source", "execution_mode"):
            with self.subTest(key=key):
                _, specialist, criterion, check = self.sample()
                check[key] = "mismatch"
                with self.assertRaises(InputError):
                    decide(specialist, criterion, check)

    def test_reject_live_mode_and_non_synthetic_target(self):
        for key, value in (("execution_mode", "local_lab"), ("target_id", "OTHER")):
            _, specialist, criterion, check = self.sample()
            if key == "execution_mode":
                specialist["observation"][key] = value
            else:
                specialist[key] = value
            with self.assertRaises(InputError):
                decide(specialist, criterion, check)

    def test_reject_activity_status_mismatch(self):
        _, specialist, criterion, check = self.sample()
        specialist["status"] = "NOT_RUN"
        with self.assertRaises(InputError):
            decide(specialist, criterion, check)

    def test_reject_ambiguous_criterion(self):
        _, specialist, criterion, check = self.sample()
        criterion["failure_value"] = criterion["success_value"]
        with self.assertRaises(InputError):
            decide(specialist, criterion, check)

    def test_reject_specialist_basis_without_activity(self):
        _, specialist, criterion, check = self.sample("OR-07")
        check["execution_basis"] = "specialist_execution"
        with self.assertRaises(InputError):
            decide(specialist, criterion, check)

    def test_reject_malformed_action_and_evidence(self):
        for field, value in (("actions", [{}]), ("evidence", [None])):
            _, specialist, criterion, check = self.sample()
            specialist[field] = value
            with self.assertRaises(InputError):
                decide(specialist, criterion, check)

    def test_claim_and_fake_candidate_result_are_not_verification(self):
        _, specialist, criterion, _ = self.sample()
        specialist["observation"]["claim"] = "success"
        specialist["evidence"] = [{"kind": "candidate", "source": "synthetic-specialist",
                                  "criterion_id": criterion["criterion_id"], "summary": "Unverified claim",
                                  "execution_mode": "offline_mock", "result": "matched"}]
        result = decide(specialist, criterion)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["evidence"], [])

    def test_unattempted_check_does_not_create_activity(self):
        _, specialist, criterion, check = self.sample("OR-07")
        check.update(attempted=False, completed=False)
        self.assertEqual(decide(specialist, criterion, check)["status"], "NOT_RUN")

    def test_conflicting_observations_remain_unknown(self):
        _, specialist, criterion, check = self.sample()
        check["observed_value"] = [criterion["success_value"], criterion["failure_value"]]
        self.assertEqual(decide(specialist, criterion, check)["status"], "UNKNOWN")

    def test_reject_non_json_and_nonfinite_data(self):
        for value in (float("nan"), object()):
            _, specialist, criterion, check = self.sample()
            specialist["observation"]["invalid"] = value
            with self.assertRaises(InputError):
                decide(specialist, criterion, check)


class ReporterTests(unittest.TestCase):
    def run_input(self, case=None, module="A"):
        case = case or load_cases()[0]
        dispatcher, specialist, criterion, check = inputs(case, module)
        return [dispatcher, specialist, decide(specialist, criterion, check)]

    def test_rp_01_roundtrip_all_fixtures_both_modules_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            for module in ("A", "B"):
                for case in load_cases():
                    with self.subTest(module=module, case=case["id"]):
                        records = self.run_input(case, module)
                        before = copy.deepcopy(records)
                        path = Path(directory) / f"{module}-{case['id']}.json"
                        outcome = store(records, path)
                        self.assertEqual(outcome["storage"], "written_and_verified")
                        restored = read_run(path)
                        self.assertEqual(restored[:3], before)
                        self.assertEqual(records, before)
                        self.assertEqual(restored[3]["status"], records[2]["status"])
                        self.assertEqual(restored[3]["evidence"], records[2]["evidence"])
                        self.assertEqual(outcome["reporter"], restored[3])

    def assert_storage_failure(self, records, result):
        self.assertEqual(result["storage"], "failed")
        reporter = result["reporter"]
        self.assertEqual(reporter["status"], records[2]["status"])
        self.assertEqual(reporter["evidence"], records[2]["evidence"])
        self.assertEqual(reporter["observation"]["storage"], "failed")
        self.assertEqual(reporter["error"]["kind"], "storage_error")
        self.assertEqual(validate_complete_run(records + [reporter]), [])

    def test_rp_02_write_failure_preserves_pass_and_safe_error(self):
        records = self.run_input()
        before = copy.deepcopy(records)
        with tempfile.TemporaryDirectory() as directory:
            with patch("pathlib.Path.open", side_effect=OSError("PRIVATE-DETAIL")):
                result = store(records, Path(directory) / "run.json")
        self.assert_storage_failure(records, result)
        self.assertNotIn("PRIVATE-DETAIL", json.dumps(result))
        self.assertEqual(records, before)

    def test_rp_03_read_error_preserves_pass(self):
        records = self.run_input()
        with tempfile.TemporaryDirectory() as directory:
            with patch("offline_reporter.read_run", side_effect=OSError("private")):
                result = store(records, Path(directory) / "run.json")
        self.assert_storage_failure(records, result)

    def test_rp_03_corrupted_previous_envelope_detected(self):
        records = self.run_input()
        original_read = read_run
        def altered(path):
            restored = original_read(path)
            restored[0]["next_action"] = "changed"
            return restored
        with tempfile.TemporaryDirectory() as directory:
            with patch("offline_reporter.read_run", side_effect=altered):
                result = store(records, Path(directory) / "run.json")
        self.assert_storage_failure(records, result)

    def test_existing_file_is_not_overwritten(self):
        records = self.run_input()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text("existing", encoding="utf-8")
            result = store(records, path)
            self.assertEqual(path.read_text(encoding="utf-8"), "existing")
        self.assert_storage_failure(records, result)

    def test_reject_wrong_order_or_mismatched_ids_before_write(self):
        for mutation in ("order", "identity", "missing"):
            records = self.run_input()
            if mutation == "order":
                records[0], records[1] = records[1], records[0]
            elif mutation == "identity":
                records[0]["run_id"] = "different"
            else:
                records.pop()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "run.json"
                with self.assertRaises(InputError):
                    store(records, path)
                self.assertFalse(path.exists())

    def test_ct_01_invalid_complete_flows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            store(self.run_input(), path)
            valid = read_run(path)
            for mutation in ("missing", "duplicate", "mode", "evidence"):
                run = copy.deepcopy(valid)
                if mutation == "missing":
                    run.pop(1)
                elif mutation == "duplicate":
                    run.insert(1, copy.deepcopy(run[1]))
                elif mutation == "mode":
                    run[3]["observation"]["execution_mode"] = "local_lab"
                else:
                    run[3]["evidence"] = []
                self.assertTrue(validate_complete_run(run))

    def test_read_run_rejects_invalid_stored_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_run(path)


if __name__ == "__main__":
    unittest.main()
