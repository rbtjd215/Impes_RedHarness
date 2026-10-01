"""Local worklog metadata helper; never upload, configure Git, or infer test success."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import uuid

RECORDS = "03_프로젝트/91_개발작업기록"
BEGIN = "<!-- redharness-worklog:v1 begin -->"
END = "<!-- redharness-worklog:v1 end -->"
TEAMS = {"a", "b", "oracle", "integration", "common"}
ORIGINS = {
    "https://github.com/rbtjd215/Impes_RedHarness.git",
    "https://github.com/rbtjd215/Impes_RedHarness",
    "git@github.com:rbtjd215/Impes_RedHarness.git",
    "ssh://git@github.com/rbtjd215/Impes_RedHarness.git",
}
TASK = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
BRANCH = re.compile(r"codex/[a-z0-9][a-z0-9._/-]{0,119}\Z")
SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
KST = dt.timezone(dt.timedelta(hours=9))
MIN_PYTHON = (3, 12)
PRIVATE_PARTS = {"runs", "private", "attachments", "secrets", "credentials", ".env"}


class WorklogError(ValueError):
    """A public-safe explanation, never raw Git output or an absolute path."""


def git(root: Path, *args: str) -> bytes:
    """Read-only Git invocation; stdout is returned privately, stderr is not published."""
    allowed = bool(args) and (args[0] in {"rev-parse", "symbolic-ref", "status", "show", "ls-remote"}
                                or args[:3] == ("remote", "get-url", "--all"))
    if not allowed:
        raise WorklogError("이 보조 도구는 읽기 전용 Git 확인만 허용합니다.")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                timeout=20, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorklogError("Git 확인 불가: " + type(exc).__name__) from None
    if result.returncode:
        raise WorklogError("Git 확인 실패; 원시 출력 대신 로컬 상태를 직접 점검하세요.")
    return result.stdout


def text_git(root: Path, *args: str) -> str:
    try:
        return git(root, *args).decode("utf-8").strip()
    except UnicodeError:
        raise WorklogError("Git 결과 인코딩을 확인할 수 없습니다.") from None


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def safe_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise WorklogError("저장소 상대 경로가 필요합니다.")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {".", ".."} for part in relative.split("/")):
        raise WorklogError("경로 탈출은 허용하지 않습니다.")
    current = root
    for part in pure.parts:
        current = current / part
        if linked(current):
            raise WorklogError("symlink/junction 경로는 허용하지 않습니다.")
    if not current.resolve().is_relative_to(root.resolve()):
        raise WorklogError("경로가 저장소 밖을 가리킵니다.")
    if exists and (not current.is_file() or current.stat().st_size > 1_000_000):
        raise WorklogError("확인할 일반 파일이 없거나 너무 큽니다.")
    return current


def inspect_repository(root: Path) -> dict:
    if linked(root) or any(linked(parent) for parent in root.parents) or not root.is_dir():
        raise WorklogError("실제 저장소 루트 폴더가 필요합니다.")
    root = root.resolve()
    try:
        actual = Path(text_git(root, "rev-parse", "--show-toplevel")).resolve()
    except (OSError, ValueError):
        raise WorklogError("Git 저장소 루트를 확인할 수 없습니다.") from None
    if actual != root:
        raise WorklogError("저장소 루트에서 실행하세요.")
    origins = text_git(root, "remote", "get-url", "--all", "origin").splitlines()
    if len(origins) != 1 or origins[0] not in ORIGINS:
        raise WorklogError("예상 공개 개발 저장소 origin과 다릅니다.")
    for relative in ("AGENTS.md", "README.md", "03_프로젝트/00_공통/PROJECT_SPEC.md"):
        safe_path(root, relative)
    folder = safe_path(root, RECORDS, exists=False)
    if not folder.is_dir():
        raise WorklogError("작업 기록 폴더가 없습니다.")
    branch = text_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = text_git(root, "rev-parse", "HEAD")
    if not SHA.fullmatch(head):
        raise WorklogError("기준 커밋을 확인할 수 없습니다.")
    return {"root": root, "origin": origins[0], "branch": branch, "head": head}


def task_branch(branch: str) -> None:
    if not BRANCH.fullmatch(branch) or ".." in branch or branch.endswith(("/", ".")):
        raise WorklogError("init/refresh는 안전한 codex/ 작업 브랜치에서만 가능합니다.")


def safe_public_name(name: str) -> bool:
    if not isinstance(name, str) or not name or "@" in name or ":" in name or "\\" in name:
        return False
    parts = name.split("/")
    if any(part in {"", ".", ".."} or part.lower() in PRIVATE_PARTS for part in parts):
        return False
    if any(word in name.lower() for word in ("cookie", "password", "token", "secret", "credential")):
        return False
    if any(not (char.isalnum() or char in " _./-()") for char in name):
        return False
    # Unknown personal/attachment paths are not collected automatically.
    return parts[0] in {"03_프로젝트", "tools", ".github", "AGENTS.md", "README.md",
                        ".gitignore", "LICENSE", "LICENSE.md"}


def git_snapshot(root: Path, head: str, record: str) -> dict:
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    try:
        entries = raw.decode("utf-8").split("\0")
    except UnicodeError:
        raise WorklogError("변경 경로 인코딩을 확인할 수 없습니다.") from None
    changes, omitted, index = [], 0, 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise WorklogError("Git 변경 상태를 해석할 수 없습니다.")
        state, name = entry[:2], entry[3:]
        previous = None
        if "R" in state or "C" in state:
            if index >= len(entries) or not entries[index]:
                raise WorklogError("Git 이동 경로를 해석할 수 없습니다.")
            previous = entries[index]
            index += 1
        if name == record:
            continue  # A log never continually snapshots its own metadata writes.
        if not safe_public_name(name) or (previous and not safe_public_name(previous)):
            omitted += 1
            continue
        item = {"state": state, "path": name}
        if previous:
            item["previous_path"] = previous
        changes.append(item)
    return {"head": head, "changes": sorted(changes, key=lambda item: item["path"]),
            "omitted_path_count": omitted, "remote_state": "unverified", "tests": "unverified"}


def decode_record(content: str) -> tuple[dict, int, int]:
    if content.count(BEGIN) != 1 or content.count(END) != 1:
        raise WorklogError("관리 블록이 없거나 중복됩니다. 기존 기록은 수동으로 이어가세요.")
    start, end = content.index(BEGIN), content.index(END) + len(END)
    block = content[start + len(BEGIN):content.index(END)].strip()
    if not block.startswith("```json\n") or not block.endswith("\n```"):
        raise WorklogError("관리 블록 형식이 다릅니다.")
    try:
        meta = json.loads(block[len("```json\n"):-len("\n```")])
    except (ValueError, TypeError):
        raise WorklogError("관리 블록 JSON을 읽을 수 없습니다.") from None
    if not isinstance(meta, dict):
        raise WorklogError("관리 메타데이터가 객체가 아닙니다.")
    return meta, start, end


def block(meta: dict) -> str:
    return BEGIN + "\n```json\n" + json.dumps(meta, ensure_ascii=False, indent=2) + "\n```\n" + END


def load_record(root: Path, relative: str, state: dict, *, same_branch: bool = True) -> tuple[Path, str, dict, int, int]:
    path = safe_path(root, relative)
    if path.parent != root / RECORDS:
        raise WorklogError("작업 기록 폴더 바로 아래의 기록을 지정하세요.")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise WorklogError("기록 파일을 안전하게 읽을 수 없습니다.") from None
    meta, start, end = decode_record(content)
    if type(meta.get("schema_version")) is not int or meta.get("schema_version") != 1 or not isinstance(meta.get("team"), str) or meta.get("team") not in TEAMS:
        raise WorklogError("기록 schema/team이 다릅니다.")
    task = meta.get("task_id")
    if not isinstance(task, str) or not TASK.fullmatch(task):
        raise WorklogError("기록 task-id가 올바르지 않습니다.")
    kind = meta.get("kind")
    if not isinstance(kind, str) or kind not in {"development", "setup"}:
        raise WorklogError("기록 종류가 올바르지 않습니다.")
    try:
        date = dt.datetime.fromisoformat(meta["created_at"]).date().isoformat()
    except (KeyError, TypeError, ValueError):
        raise WorklogError("기록 생성 시점이 올바르지 않습니다.") from None
    expected = f"{date}_{meta['team']}_{'setup_' if kind == 'setup' else ''}{task}.md"
    if path.name != expected or not SHA.fullmatch(str(meta.get("base_sha", ""))):
        raise WorklogError("기록 이름/기준 SHA와 작업 메타데이터가 다릅니다.")
    task_branch(str(meta.get("branch", "")))
    if same_branch and meta["branch"] != state["branch"]:
        raise WorklogError("현재 브랜치의 기록이 아닙니다. 타 작업 기록을 갱신하지 않습니다.")
    expected_keys = {"schema_version", "team", "task_id", "kind", "branch", "base_sha", "created_at", "captured_at", "snapshot"}
    if set(meta) != expected_keys:
        raise WorklogError("관리 블록에는 정해진 자동 수집 필드만 사용하세요.")
    snapshot = meta.get("snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("remote_state") != "unverified" or snapshot.get("tests") != "unverified":
        raise WorklogError("자동 수집 블록은 원격/테스트 완료를 주장할 수 없습니다.")
    if set(snapshot) != {"head", "changes", "omitted_path_count", "remote_state", "tests"} or not SHA.fullmatch(str(snapshot.get("head", ""))):
        raise WorklogError("Git 상태 메타데이터가 올바르지 않습니다.")
    if type(snapshot.get("omitted_path_count")) is not int or snapshot["omitted_path_count"] < 0 or not isinstance(snapshot.get("changes"), list):
        raise WorklogError("Git 변경 목록이 올바르지 않습니다.")
    for change in snapshot["changes"]:
        if not isinstance(change, dict) or set(change) not in ({"state", "path"}, {"state", "path", "previous_path"}):
            raise WorklogError("Git 변경 항목이 올바르지 않습니다.")
        if not isinstance(change["state"], str) or not re.fullmatch(r"[ MADRCUT?!]{2}", change["state"]):
            raise WorklogError("Git 변경 상태가 올바르지 않습니다.")
        if not isinstance(change["path"], str) or not safe_public_name(change["path"]) or ("previous_path" in change and not safe_public_name(change["previous_path"])):
            raise WorklogError("자동 수집에 허용되지 않은 상대 경로입니다.")
    return path, content, meta, start, end


def atomic_refresh(path: Path, original: str, updated: str) -> bool:
    if original == updated:
        return False
    temporary = None
    try:
        if linked(path) or path.read_text(encoding="utf-8") != original:
            raise WorklogError("기록이 동시에 변경됐습니다. 다시 읽고 조율하세요.")
        fd, name = tempfile.mkstemp(prefix=".worklog-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(updated)
        if linked(path) or path.read_text(encoding="utf-8") != original:
            raise WorklogError("기록이 동시에 변경됐습니다. 기존 내용을 보존합니다.")
        os.replace(temporary, path)
        return True
    except OSError:
        raise WorklogError("기록 저장 실패; 기존 파일을 확인하세요.") from None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def init_record(root: Path, team: str, task_id: str | None = None, kind: str = "development") -> dict:
    state = inspect_repository(root)
    root = state["root"]
    task_branch(state["branch"])
    if not isinstance(team, str) or team not in TEAMS or not isinstance(kind, str) or kind not in {"development", "setup"}:
        raise WorklogError("알려진 팀/기록 종류를 선택하세요.")
    if task_id is not None and (not isinstance(task_id, str) or not TASK.fullmatch(task_id)):
        raise WorklogError("task-id는 소문자 영문/숫자/하이픈 1~64자로 정하세요.")
    matches, ignored = [], 0
    for candidate in (root / RECORDS).glob("*.md"):
        # Without a task-id, damaged same-team records are ambiguous and need review.
        prefix = re.fullmatch(r"\d{4}-\d{2}-\d{2}_" + re.escape(team) + r"_(.+)\.md", candidate.name)
        name_candidate = bool(prefix) and (task_id is None or prefix[1] in {task_id, "setup_" + task_id})
        try:
            candidate = safe_path(root, candidate.relative_to(root).as_posix())
            content = candidate.read_text(encoding="utf-8")
        except (WorklogError, OSError, UnicodeError):
            if name_candidate:
                raise WorklogError("자기 후보 기록을 읽을 수 없습니다. 보존하고 확인하세요.") from None
            ignored += 1
            continue
        if BEGIN not in content:
            legacy_branch = re.search(r"(?:^branch:\s*|^- 작업 브랜치:\s*)`?" + re.escape(state["branch"]) + r"(?:`|\s|$)", content, re.MULTILINE)
            if name_candidate and task_id is not None or legacy_branch:
                raise WorklogError("같은 작업의 기존 기록이 있습니다. 수동으로 이어가고 중복 생성하지 마세요.")
            continue
        try:
            meta, _, _ = decode_record(content)
        except WorklogError:
            hint = content.split(BEGIN, 1)[1].split(END, 1)[0][:10000]
            branch_candidate = re.search(r'"branch"\s*:\s*"' + re.escape(state["branch"]) + r'"', hint)
            if name_candidate or branch_candidate:
                raise WorklogError("자기 후보 기록의 관리 블록이 손상됐습니다. 덮거나 중복 생성하지 마세요.") from None
            ignored += 1
            continue
        try:
            load_record(root, candidate.relative_to(root).as_posix(), state, same_branch=False)
        except WorklogError:
            if name_candidate or meta.get("branch") == state["branch"]:
                raise WorklogError("자기 후보 기록의 메타데이터가 손상됐습니다. 보존하고 확인하세요.") from None
            ignored += 1
            continue
        if meta.get("branch") == state["branch"]:
            matches.append(candidate.relative_to(root).as_posix())
        elif task_id and meta.get("team") == team and meta.get("task_id") == task_id:
            raise WorklogError("이 task-id는 다른 브랜치의 기록에 사용 중입니다.")
    if matches:
        if len(matches) != 1:
            raise WorklogError("현재 브랜치에 기록이 여러 개입니다. 자기 작업을 확인하세요.")
        _, _, meta, _, _ = load_record(root, matches[0], state)
        if meta["team"] != team or meta["kind"] != kind or (task_id and meta["task_id"] != task_id):
            raise WorklogError("현재 브랜치의 기존 작업과 팀/task/종류가 다릅니다.")
        return {"record": matches[0], "created": False, "ignored_record_count": ignored, "tests": "unverified", "remote": "unverified"}
    task_id = task_id or "task-" + uuid.uuid4().hex[:12]
    now = dt.datetime.now(KST).isoformat(timespec="seconds")
    date = dt.datetime.fromisoformat(now).date().isoformat()
    relative = f"{RECORDS}/{date}_{team}_{'setup_' if kind == 'setup' else ''}{task_id}.md"
    path = safe_path(root, relative, exists=False)
    template_name = "환경준비_기록_템플릿.md" if kind == "setup" else "작업기록_템플릿.md"
    template = safe_path(root, f"{RECORDS}/{template_name}").read_text(encoding="utf-8")
    if BEGIN in template or END in template:
        raise WorklogError("원본 양식에는 관리 블록을 미리 넣지 마세요.")
    meta = {"schema_version": 1, "team": team, "task_id": task_id, "kind": kind,
            "branch": state["branch"], "base_sha": state["head"], "created_at": now,
            "captured_at": now, "snapshot": git_snapshot(root, state["head"], relative)}
    title, _, body = template.partition("\n")
    content = f"# {'환경 준비' if kind == 'setup' else '개발 작업'} 기록 · {task_id}\n\n{block(meta)}\n\n" + body.lstrip("\n")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError:
        raise WorklogError("기록 파일이 이미 있습니다. 덮어쓰지 않습니다.") from None
    return {"record": relative, "created": True, "ignored_record_count": ignored, "tests": "unverified", "remote": "unverified"}


def refresh_record(root: Path, relative: str) -> dict:
    state = inspect_repository(root)
    root = state["root"]
    task_branch(state["branch"])
    path, content, meta, start, end = load_record(root, relative, state)
    snapshot = git_snapshot(root, state["head"], relative)
    if meta["snapshot"] == snapshot:
        return {"record": relative, "updated": False, "tests": "unverified", "remote": "unverified"}
    meta["snapshot"] = snapshot
    meta["captured_at"] = dt.datetime.now(KST).isoformat(timespec="seconds")
    changed = atomic_refresh(path, content, content[:start] + block(meta) + content[end:])
    return {"record": relative, "updated": changed, "tests": "unverified", "remote": "unverified"}


def check_record(root: Path, relative: str) -> dict:
    state = inspect_repository(root)
    _, _, meta, _, _ = load_record(state["root"], relative, state)
    return {"record": relative, "structure": "valid", "task_id": meta["task_id"],
            "tests": "unverified", "public_safety": "not_verified", "actual_feature": "not_verified"}


def summary_record(root: Path, relative: str, remote_check: bool = False) -> dict:
    state = inspect_repository(root)
    root = state["root"]
    path, _, meta, _, _ = load_record(root, relative, state, same_branch=False)
    try:
        committed = git(root, "show", "HEAD:" + relative).replace(b"\r\n", b"\n") == path.read_bytes().replace(b"\r\n", b"\n")
    except WorklogError:
        committed = False
    result = {"record": relative, "task_id": meta["task_id"], "team": meta["team"],
              "branch": state["branch"], "record_branch_matches": meta["branch"] == state["branch"],
              "local_head": state["head"], "committed_record_matches_worktree": committed,
              "remote": "unverified", "tests": "unverified", "pr": "unverified", "main_merge": "unverified"}
    if remote_check:
        try:
            lines = text_git(root, "ls-remote", "--exit-code", "origin", "refs/heads/" + meta["branch"]).splitlines()
            values = [line.split() for line in lines]
            if len(values) != 1 or len(values[0]) != 2 or values[0][1] != "refs/heads/" + meta["branch"] or not SHA.fullmatch(values[0][0]):
                raise WorklogError("원격 참조 결과를 확인할 수 없습니다.")
            result["remote_head"] = values[0][0]
            result["remote"] = ("head_and_committed_record_match" if values[0][0] == state["head"]
                                and committed and result["record_branch_matches"] else "not_matched")
        except WorklogError:
            result["remote"] = "unverified"
            result["remote_error"] = "원격 확인 실패; 업로드 완료를 주장하지 않습니다."
    return result


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--team", required=True, choices=sorted(TEAMS))
    init.add_argument("--task-id")
    init.add_argument("--kind", choices=("development", "setup"), default="development")
    for command in ("refresh", "check", "summary"):
        item = sub.add_parser(command)
        item.add_argument("--record", required=True)
        if command == "summary":
            item.add_argument("--remote-check", action="store_true")
    args = parser.parse_args(argv)
    if sys.version_info < MIN_PYTHON:
        print("Python 3.12 이상이 필요합니다.", file=sys.stderr)
        return 1
    try:
        root = Path.cwd()
        if args.command == "init":
            result = init_record(root, args.team, args.task_id, args.kind)
        elif args.command == "refresh":
            result = refresh_record(root, args.record)
        elif args.command == "check":
            result = check_record(root, args.record)
        else:
            result = summary_record(root, args.record, args.remote_check)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorklogError, OSError, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, WorklogError) else "파일 확인 실패; 기존 기록을 보존하세요."
        print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
