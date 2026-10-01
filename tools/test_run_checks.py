"""Required check policy and registry tests, isolated from real group discovery."""
from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import run_checks


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="redharness-checks-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        for name in ("AGENTS.md", "03_프로젝트/00_공통/PROJECT_SPEC.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("public fixture", encoding="utf-8")
        (self.root / "tools").mkdir()
        self.group = {"id": "fixture", "path": "module", "required": True,
                      "checks": [{"kind": "unittest", "pattern": "test_*.py"}]}
        self.config = {"schema_version": 1, "groups": [self.group], "references": []}
        (self.root / "module").mkdir()
        self.metrics = {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}
        self.calls = []
        self.output = io.StringIO()

    def save(self):
        (self.root / "tools/checks.json").write_text(json.dumps(self.config), encoding="utf-8")

    def fake_process(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return types.SimpleNamespace(returncode=0, stdout=run_checks.PREFIX + json.dumps(self.metrics), stderr="private diagnostic")

    def run_fixture(self):
        self.save()
        return run_checks.run_registered(self.root, process=self.fake_process, stream=self.output)

    def test_positive_results_and_subprocess_isolation_no_shell(self):
        self.assertTrue(self.run_fixture())
        argv, kwargs = self.calls[0]
        self.assertIn("--worker", argv)
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertNotIn("private diagnostic", self.output.getvalue())

    def test_zero_skip_fail_error_and_malformed_counts_fail(self):
        for key, value in (("tests", 0), ("skipped", 1), ("failures", 1), ("errors", 1), ("tests", True), ("tests", -1)):
            with self.subTest(key=key, value=value):
                metrics = dict(self.metrics, **{key: value})
                self.assertFalse(run_checks.evaluate(metrics))
        self.metrics["skipped"] = 1
        self.assertFalse(self.run_fixture())
        self.assertIn("SKIP", self.output.getvalue())

    def test_unimplemented_group_is_not_feature_complete(self):
        self.group["required"] = False
        self.assertTrue(self.run_fixture())
        self.assertIn("NOT_IMPLEMENTED", self.output.getvalue())
        self.assertEqual(self.calls, [])

    def test_implementation_without_tests_fails(self):
        self.group["required"] = False
        (self.root / "module/module.py").write_text("pass", encoding="utf-8")
        self.metrics["tests"] = 0
        self.assertFalse(self.run_fixture())
        self.assertEqual(len(self.calls), 1)

    def test_test_only_optional_group_is_executed(self):
        self.group["required"] = False
        (self.root / "module/test_future.py").write_text("pass", encoding="utf-8")
        self.assertTrue(self.run_fixture())
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("NOT_IMPLEMENTED", self.output.getvalue())
        self.assertIn("TESTS_ONLY", self.output.getvalue())

    def test_failure_ids_are_sanitized_and_local_debug_command_shown(self):
        self.metrics.update(failures=1, failed_tests=["test_future.Case.test_feature", "C:/private/person", "person@example.invalid"])
        self.assertFalse(self.run_fixture())
        output = self.output.getvalue()
        self.assertIn("test_future.Case.test_feature", output)
        self.assertIn("unittest discover", output)
        self.assertNotIn("person", output)

    def test_registry_path_escape_duplicate_and_git_shell_commands_rejected(self):
        for path in ("../private", "/private", "C:/private"):
            self.group["path"] = path
            self.save()
            with self.assertRaises(run_checks.CheckError):
                run_checks.load_registry(self.root)
        self.group["path"] = "module"
        self.config["groups"].append(dict(self.group))
        self.save()
        with self.assertRaises(run_checks.CheckError):
            run_checks.load_registry(self.root)
        for argv in (["git", "push"], ["cmd", "/c", "echo x"], ["powershell", "-Command", "x"], "node --test"):
            with self.assertRaises(run_checks.CheckError):
                run_checks.validate_argv(argv)

    def test_custom_language_requires_result_counts_not_just_exit_zero(self):
        self.group["checks"] = [{"kind": "command", "argv": ["node", "module/check_adapter.js"]}]
        self.assertTrue(self.run_fixture())
        self.assertEqual(self.calls[0][0], ["node", "module/check_adapter.js"])
        self.assertFalse(run_checks.evaluate(self.metrics, 1))
        with self.assertRaises(run_checks.CheckError):
            run_checks.read_metrics("process exited zero without counts")
        with self.assertRaises(run_checks.CheckError):
            run_checks.read_metrics(run_checks.PREFIX + "{}\n" + run_checks.PREFIX + "{}")

    def test_group_selection_and_symlink_are_checked(self):
        self.save()
        with self.assertRaises(run_checks.CheckError):
            run_checks.run_registered(self.root, ["unregistered"], process=self.fake_process)
        original_linked = run_checks.linked
        with patch("run_checks.linked", side_effect=lambda path: path == self.root / "module" or original_linked(path)):
            with self.assertRaises(run_checks.CheckError):
                run_checks.load_registry(self.root)

    def test_worker_suite_records_real_skips_and_empty_discovery(self):
        # Own temporary suite only; never recursively discover tools/test_*.py.
        (self.root / "module/test_fixture_skip.py").write_text(
            "import unittest\nclass Fixture(unittest.TestCase):\n"
            "    @unittest.skip('synthetic unavailable')\n"
            "    def test_required(self): pass\n", encoding="utf-8")
        metrics = run_checks.run_suite(self.root / "module", "test_fixture_skip.py")
        self.assertEqual(metrics["skipped"], 1)
        self.assertFalse(run_checks.evaluate(metrics))
        metrics = run_checks.run_suite(self.root / "module", "test_no_such_case.py")
        self.assertEqual(metrics["tests"], 0)
        self.assertFalse(run_checks.evaluate(metrics))

    def test_unexpected_success_and_expected_failure_are_not_required_passes(self):
        (self.root / "module/test_fixture_expected.py").write_text(
            "import unittest\nclass Fixture(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_unexpected_success(self): pass\n"
            "    @unittest.expectedFailure\n"
            "    def test_expected_failure(self): self.fail('synthetic')\n", encoding="utf-8")
        metrics = run_checks.run_suite(self.root / "module", "test_fixture_expected.py")
        self.assertEqual(metrics["unexpected_successes"], 1)
        self.assertEqual(metrics["expected_failures"], 1)
        self.assertFalse(run_checks.evaluate(metrics))
        for key in ("unexpected_successes", "expected_failures"):
            self.assertFalse(run_checks.evaluate(dict(self.metrics, **{key: 1})))

    def test_selected_unimplemented_group_returns_incomplete(self):
        self.group["required"] = False
        self.save()
        self.assertFalse(run_checks.run_registered(self.root, ["fixture"], process=self.fake_process, stream=self.output))
        self.assertIn("범위 미완료", self.output.getvalue())
        self.assertEqual(self.calls, [])

    def test_execution_failure_hides_raw_output_and_old_python_rejected(self):
        self.save()
        with patch("run_checks.subprocess.run", side_effect=FileNotFoundError("private user path")):
            self.assertFalse(run_checks.run_registered(self.root, stream=self.output))
        self.assertNotIn("private user path", self.output.getvalue())
        with patch("run_checks.sys.version_info", (3, 11)), patch("run_checks.sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(run_checks.main([]), 1)
            self.assertIn("3.12", output.getvalue())


if __name__ == "__main__":
    unittest.main()
