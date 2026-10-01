"""Offline worklog state, preservation and safety tests; no real Git mutations/network."""
from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import worklog

HEAD = "a" * 40
NEXT = "b" * 40


class WorklogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="redharness-worklog-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        for name in ("AGENTS.md", "README.md", "03_프로젝트/00_공통/PROJECT_SPEC.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("public fixture\n", encoding="utf-8")
        records = self.root / worklog.RECORDS
        records.mkdir()
        for name in ("작업기록_템플릿.md", "환경준비_기록_템플릿.md"):
            (records / name).write_text("# 양식\n\n## 실제 시도와 아이디어\n- 확인 전\n\n## 검증\n- 미확인\n\n## 인계\n- 다음 행동 미확인\n", encoding="utf-8")
        self.branch, self.head = "codex/fixture-task", HEAD
        self.origin = "https://github.com/rbtjd215/Impes_RedHarness.git"
        self.status = b""
        self.committed = {}
        self.calls = []
        self.remote = HEAD
        self.remote_fail = False
        self.production_git = worklog.git
        self.patcher = patch("worklog.git", side_effect=self.fake_git)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def fake_git(self, root, *args):
        self.calls.append(args)
        if args == ("rev-parse", "--show-toplevel"):
            return str(self.root).encode()
        if args == ("remote", "get-url", "--all", "origin"):
            return self.origin.encode()
        if args == ("symbolic-ref", "--quiet", "--short", "HEAD"):
            return self.branch.encode()
        if args == ("rev-parse", "HEAD"):
            return self.head.encode()
        if args[0] == "status":
            return self.status
        if args[0] == "show":
            if args[1][5:] not in self.committed:
                raise worklog.WorklogError("uncommitted fixture")
            return self.committed[args[1][5:]]
        if args[0] == "ls-remote":
            if self.remote_fail:
                raise worklog.WorklogError("offline fixture")
            return (self.remote + "\t" + args[-1] + "\n").encode()
        self.fail("Unexpected Git call: " + repr(args))

    def make(self, team="common", task="fixture", kind="development"):
        return worklog.init_record(self.root, team, task, kind)["record"]

    def test_init_reuses_one_file_and_generates_unique_task(self):
        first = worklog.init_record(self.root, "a")
        second = worklog.init_record(self.root, "a")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["record"], second["record"])
        self.assertEqual(len(list((self.root / worklog.RECORDS).glob("*_a_*.md"))), 1)

    def test_setup_name_and_kst_created_at(self):
        relative = self.make("b", "first", "setup")
        meta, _, _ = worklog.decode_record((self.root / relative).read_text(encoding="utf-8"))
        self.assertTrue(relative.endswith("_b_setup_first.md"))
        self.assertTrue(meta["created_at"].endswith("+09:00"))
        self.assertEqual(meta["base_sha"], HEAD)
        self.assertEqual(meta["snapshot"]["tests"], "unverified")

    def test_refresh_preserves_narrative_base_and_is_idempotent(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_text(encoding="utf-8")
        original += "\n## 실제 확인\n아이디어는 보류, 실제 테스트는 미실행.\n"
        path.write_text(original, encoding="utf-8")
        _, start, end = worklog.decode_record(original)
        self.head = NEXT
        self.status = (" M tools/worklog.py\0?? " + relative + "\0").encode()
        self.assertTrue(worklog.refresh_record(self.root, relative)["updated"])
        updated = path.read_text(encoding="utf-8")
        meta, changed_start, changed_end = worklog.decode_record(updated)
        self.assertEqual(original[:start], updated[:changed_start])
        self.assertEqual(original[end:], updated[changed_end:])
        self.assertEqual(meta["base_sha"], HEAD)
        self.assertEqual(meta["snapshot"]["head"], NEXT)
        self.assertEqual(len(meta["snapshot"]["changes"]), 1)
        self.assertFalse(worklog.refresh_record(self.root, relative)["updated"])
        self.assertEqual(path.read_text(encoding="utf-8"), updated)

    def test_main_and_foreign_branch_refuse_mutation(self):
        relative = self.make()
        original = (self.root / relative).read_bytes()
        self.branch = "main"
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "common", "another")
        with self.assertRaises(worklog.WorklogError):
            worklog.refresh_record(self.root, relative)
        self.branch = "codex/another-task"
        with self.assertRaises(worklog.WorklogError):
            worklog.refresh_record(self.root, relative)
        self.assertEqual((self.root / relative).read_bytes(), original)

    def test_task_or_team_conflict_does_not_create_or_overwrite(self):
        relative = self.make()
        original = (self.root / relative).read_bytes()
        for team, task in (("a", "fixture"), ("common", "different")):
            with self.assertRaises(worklog.WorklogError):
                worklog.init_record(self.root, team, task)
        self.branch = "codex/new-branch"
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "common", "fixture")
        self.assertEqual((self.root / relative).read_bytes(), original)

    def test_legacy_same_task_is_preserved(self):
        legacy = self.root / worklog.RECORDS / "2026-09-30_a_existing.md"
        legacy.write_text("historical confirmed evidence", encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "a", "existing")
        self.assertEqual(legacy.read_text(encoding="utf-8"), "historical confirmed evidence")

    def test_wrong_root_remote_and_multiple_origins_are_rejected(self):
        for origin in ("https://example.invalid/repo.git", self.origin + "\nhttps://example.invalid/repo.git"):
            self.origin = origin
            with self.assertRaises(worklog.WorklogError):
                self.make()
        self.origin = "https://github.com/rbtjd215/Impes_RedHarness.git"
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root / "03_프로젝트", "a", "badroot")

    def test_path_escape_invalid_task_and_link_are_rejected(self):
        relative = self.make()
        for bad in ("../outside.md", "/outside.md", "C:/private.md", worklog.RECORDS + "/../outside.md"):
            with self.assertRaises(worklog.WorklogError):
                worklog.refresh_record(self.root, bad)
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "a", "../bad")
        original_linked = worklog.linked
        with patch("worklog.linked", side_effect=lambda path: path == self.root / relative or original_linked(path)):
            with self.assertRaises(worklog.WorklogError):
                worklog.refresh_record(self.root, relative)

    def test_privacy_filter_and_rename_do_not_collect_sensitive_values(self):
        relative = self.make()
        self.status = ("?? tools/session_cookie.txt\0?? person@example.invalid.txt\0"
                       "?? runs/raw.json\0?? unknown-personal-file.txt\0"
                       "R  tools/new.py\0tools/old.py\0").encode()
        worklog.refresh_record(self.root, relative)
        meta, _, _ = worklog.decode_record((self.root / relative).read_text(encoding="utf-8"))
        self.assertEqual(meta["snapshot"]["omitted_path_count"], 4)
        self.assertEqual(meta["snapshot"]["changes"][0]["previous_path"], "tools/old.py")
        serialized = json.dumps(meta)
        self.assertNotIn("example.invalid", serialized)
        self.assertNotIn("session_cookie", serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertFalse(any(call[0] in {"config", "log", "fetch", "push", "commit"} for call in self.calls))

    def test_check_rejects_duplicate_markers_and_false_automatic_pass(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_text(encoding="utf-8")
        meta, start, end = worklog.decode_record(original)
        meta["snapshot"]["tests"] = "PASS"
        path.write_text(original[:start] + worklog.block(meta) + original[end:], encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.check_record(self.root, relative)
        path.write_text(original + worklog.BEGIN, encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.check_record(self.root, relative)

    def test_concurrent_write_and_failed_replace_preserve_narrative(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\nother writer\n", encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.atomic_refresh(path, original, original + "changed")
        self.assertTrue(path.read_text(encoding="utf-8").endswith("other writer\n"))
        now = path.read_text(encoding="utf-8")
        with patch("worklog.os.replace", side_effect=PermissionError("synthetic denied")):
            with self.assertRaises(worklog.WorklogError):
                worklog.atomic_refresh(path, now, now + "changed")
        self.assertEqual(path.read_text(encoding="utf-8"), now)
        self.assertEqual(list(path.parent.glob(".worklog-*.tmp")), [])

    def test_default_summary_never_calls_network_or_changes_record(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_bytes()
        result = worklog.summary_record(self.root, relative)
        self.assertEqual(result["remote"], "unverified")
        self.assertFalse(result["committed_record_matches_worktree"])
        self.assertFalse(any(call[0] == "ls-remote" for call in self.calls))
        self.assertEqual(path.read_bytes(), original)

    def test_remote_summary_requires_exact_committed_record_and_head(self):
        relative = self.make()
        self.assertEqual(worklog.summary_record(self.root, relative, True)["remote"], "not_matched")
        self.committed[relative] = (self.root / relative).read_bytes()
        result = worklog.summary_record(self.root, relative, True)
        self.assertEqual(result["remote"], "head_and_committed_record_match")
        self.assertEqual(result["pr"], "unverified")
        self.assertEqual(result["tests"], "unverified")
        (self.root / relative).write_text("changed after commit", encoding="utf-8")
        # Restore a valid structure with a narrative-only difference.
        (self.root / relative).write_bytes(self.committed[relative] + b"\nnew narrative\n")
        self.assertEqual(worklog.summary_record(self.root, relative, True)["remote"], "not_matched")
        self.remote_fail = True
        self.assertEqual(worklog.summary_record(self.root, relative, True)["remote"], "unverified")

    def test_unsafe_origin_blocks_even_explicit_remote_check(self):
        relative = self.make()
        self.origin = "https://example.invalid/unexpected.git"
        with self.assertRaises(worklog.WorklogError):
            worklog.summary_record(self.root, relative, True)
        self.assertFalse(any(call[0] == "ls-remote" for call in self.calls))

    def test_malformed_metadata_returns_safe_errors(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_text(encoding="utf-8")
        base, start, end = worklog.decode_record(original)
        for key, value in (("team", []), ("kind", {}), ("schema_version", True)):
            meta = copy.deepcopy(base)
            meta[key] = value
            path.write_text(original[:start] + worklog.block(meta) + original[end:], encoding="utf-8")
            with self.subTest(key=key):
                with self.assertRaises(worklog.WorklogError):
                    worklog.check_record(self.root, relative)
        path.write_text(original, encoding="utf-8")
        self.assertEqual(worklog.check_record(self.root, relative)["structure"], "valid")

    def test_git_transport_rejects_mutations_without_starting_process(self):
        # Restore the production transport locally; subprocess remains a fake.
        transport = self.production_git
        with patch("worklog.subprocess.run") as process:
            for args in (("push",), ("commit",), ("fetch",), ("config", "user.name"), ("remote", "set-url", "origin", "x")):
                with self.assertRaises(worklog.WorklogError):
                    transport(self.root, *args)
            process.assert_not_called()

    def test_unrelated_broken_record_warns_without_blocking(self):
        other = self.root / worklog.RECORDS / "2026-09-30_b_broken.md"
        other.write_text(worklog.BEGIN + "\n```json\n{broken}\n```\n" + worklog.END, encoding="utf-8")
        original = other.read_bytes()
        schema_bad = self.root / worklog.RECORDS / "2026-09-30_b_schema-broken.md"
        schema_bad.write_text(worklog.block({"schema_version": 1}), encoding="utf-8")
        schema_original = schema_bad.read_bytes()
        result = worklog.init_record(self.root, "a", "new-task")
        self.assertTrue(result["created"])
        self.assertEqual(result["ignored_record_count"], 2)
        self.assertEqual(other.read_bytes(), original)
        self.assertEqual(schema_bad.read_bytes(), schema_original)

    def test_own_broken_name_or_branch_never_creates_duplicate(self):
        records = self.root / worklog.RECORDS
        own = records / "2026-09-30_a_existing.md"
        own.write_text(worklog.BEGIN + "\ninvalid\n" + worklog.END, encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "a", "existing")
        self.assertEqual(len(list(records.glob("*_a_existing.md"))), 1)
        own.unlink()
        other_name = records / "2026-09-30_b_other-name.md"
        other_name.write_text(worklog.BEGIN + '\n```json\n{"branch": "' + self.branch + '", invalid}\n```\n' + worklog.END, encoding="utf-8")
        with self.assertRaises(worklog.WorklogError):
            worklog.init_record(self.root, "a", "existing")
        self.assertEqual(list(records.glob("*_a_existing.md")), [])

    def test_remote_record_comparison_normalizes_only_crlf(self):
        relative = self.make()
        path = self.root / relative
        original = path.read_bytes()
        self.committed[relative] = original
        path.write_bytes(original.replace(b"\n", b"\r\n"))
        self.assertEqual(worklog.summary_record(self.root, relative, True)["remote"], "head_and_committed_record_match")
        path.write_bytes(original.replace(b"\n", b"\r\n") + b"extra line\r\n")
        self.assertEqual(worklog.summary_record(self.root, relative, True)["remote"], "not_matched")

    def test_cli_error_hides_raw_exception_and_old_python_fails(self):
        with patch("worklog.sys.version_info", (3, 11)), patch("worklog.sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(worklog.main(["init", "--team", "a"]), 1)
            self.assertIn("3.12", output.getvalue())
        with patch("worklog.Path.cwd", return_value=self.root), patch("worklog.sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(worklog.main(["init", "--team", "a", "--task-id", "cli"]), 0)
            self.assertTrue(json.loads(output.getvalue())["created"])


if __name__ == "__main__":
    unittest.main()
