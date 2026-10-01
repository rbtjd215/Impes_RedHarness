"""Run registered offline checks. Required suites reject zero tests, SKIP and FAIL."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unittest

PREFIX = "REDHARNESS_CHECK_RESULT="
MIN_PYTHON = (3, 12)
EXTENSIONS = [".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".cs"]


class CheckError(ValueError):
    pass


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def within(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise CheckError("registry 경로는 저장소 상대 경로여야 합니다.")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {".", ".."} for part in relative.split("/")):
        raise CheckError("registry 경로 탈출을 거부합니다.")
    path = root
    for part in pure.parts:
        path = path / part
        if linked(path):
            raise CheckError("symlink/junction 검사 경로를 거부합니다.")
    if not path.resolve().is_relative_to(root.resolve()):
        raise CheckError("검사 경로가 저장소 밖입니다.")
    return path


def load_registry(root: Path) -> dict:
    if linked(root) or not (root / "AGENTS.md").is_file() or not (root / "03_프로젝트/00_공통/PROJECT_SPEC.md").is_file():
        raise CheckError("개발 저장소 루트에서 실행하세요.")
    path = within(root, "tools/checks.json")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CheckError("checks.json을 읽을 수 없습니다.") from None
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise CheckError("checks.json schema_version은 1이어야 합니다.")
    groups = config.get("groups")
    if not isinstance(groups, list) or not groups:
        raise CheckError("검사 그룹이 필요합니다.")
    names = []
    for group in groups:
        if not isinstance(group, dict) or not re.fullmatch(r"[a-z][a-z0-9-]*", str(group.get("id", ""))):
            raise CheckError("그룹 id가 올바르지 않습니다.")
        names.append(group["id"])
        within(root, group.get("path"))
        if type(group.get("required")) is not bool:
            raise CheckError("required는 true/false여야 합니다.")
        extensions = group.get("implementation_extensions", EXTENSIONS)
        if not isinstance(extensions, list) or not extensions or any(not re.fullmatch(r"\.[a-z0-9]+", str(item)) for item in extensions):
            raise CheckError("구현 확장자를 명시하세요.")
        checks = group.get("checks")
        if not isinstance(checks, list) or not checks:
            raise CheckError("그룹 검사 방법을 등록하세요.")
        for check in checks:
            if not isinstance(check, dict) or check.get("kind") not in {"unittest", "command"}:
                raise CheckError("unittest 또는 command 검사가 필요합니다.")
            if check["kind"] == "unittest":
                pattern = check.get("pattern", "test_*.py")
                if not isinstance(pattern, str) or "/" in pattern or "\\" in pattern or ".." in pattern:
                    raise CheckError("unittest 파일 패턴이 올바르지 않습니다.")
            else:
                validate_argv(check.get("argv"))
    if len(set(names)) != len(names):
        raise CheckError("그룹 id가 중복됩니다.")
    for argv in config.get("references", []):
        validate_argv(argv)
    return config


def validate_argv(argv: object) -> list[str]:
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item or "\0" in item for item in argv):
        raise CheckError("명령은 비어 있지 않은 argv 문자열 배열이어야 합니다.")
    if argv[0] not in {"{python}", "node"}:
        raise CheckError("등록 실행 파일은 {python} 또는 node 검사 adapter만 허용합니다. shell/Git/설정 명령은 거부합니다.")
    return [sys.executable if item == "{python}" else item for item in argv]


def implementation_present(folder: Path, extensions: list[str]) -> bool:
    if not folder.is_dir():
        return False
    found = False
    for path in folder.rglob("*"):
        if linked(path):
            raise CheckError("검사 폴더 안의 symlink/junction을 거부합니다.")
        if path.is_file() and path.suffix in extensions and not path.name.startswith("test_") and path.name != "__init__.py":
            found = True
    return found


def run_suite(folder: Path, pattern: str = "test_*.py") -> dict:
    """Worker only: loader state stays in a separate process for each group."""
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        suite = unittest.TestLoader().discover(str(folder), pattern=pattern)
        count = suite.countTestCases()
        result = unittest.TextTestRunner(stream=captured, verbosity=0).run(suite)
    failed = []
    for case, _ in result.failures + result.errors:
        name = case.id()
        failed.append(name if re.fullmatch(r"[A-Za-z0-9_.]+", name) else "test failure")
    for case in result.unexpectedSuccesses + [case for case, _ in result.expectedFailures]:
        name = case.id()
        failed.append(name if re.fullmatch(r"[A-Za-z0-9_.]+", name) else "test failure")
    return {"tests": count, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "unexpected_successes": len(result.unexpectedSuccesses),
            "expected_failures": len(result.expectedFailures), "failed_tests": failed}


def evaluate(metrics: object, returncode: int = 0) -> bool:
    if not isinstance(metrics, dict) or returncode != 0:
        return False
    for key in ("tests", "failures", "errors", "skipped"):
        if type(metrics.get(key)) is not int or metrics[key] < 0:
            return False
    for key in ("unexpected_successes", "expected_failures"):
        if type(metrics.get(key, 0)) is not int or metrics.get(key, 0) < 0 or metrics.get(key, 0) != 0:
            return False
    return metrics["tests"] > 0 and all(metrics[key] == 0 for key in ("failures", "errors", "skipped"))


def invoke(root: Path, argv: list[str], process=None) -> tuple[int, str]:
    process = process or subprocess.run
    try:
        result = process(argv, cwd=root, capture_output=True, text=True, encoding="utf-8",
                         timeout=120, check=False, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckError("검사 실행 불가: " + type(exc).__name__) from None
    return result.returncode, result.stdout


def read_metrics(output: str) -> dict:
    lines = [line[len(PREFIX):] for line in output.splitlines() if line.startswith(PREFIX)]
    if len(lines) != 1:
        raise CheckError("검사 수/실패/SKIP 결과 프로토콜이 없습니다.")
    try:
        metrics = json.loads(lines[0])
    except ValueError:
        raise CheckError("검사 결과 JSON이 올바르지 않습니다.") from None
    if not isinstance(metrics, dict):
        raise CheckError("검사 결과가 객체가 아닙니다.")
    if "failed_tests" in metrics and not isinstance(metrics["failed_tests"], list):
        raise CheckError("실패 검사 ID는 배열이어야 합니다.")
    return metrics


def run_registered(root: Path, selected: list[str] | None = None, *, process=None, stream=None) -> bool:
    stream = stream or sys.stdout
    if linked(root) or any(linked(parent) for parent in root.parents):
        raise CheckError("실제 저장소 루트 폴더가 필요합니다.")
    root = root.resolve()
    config = load_registry(root)
    ids = {group["id"] for group in config["groups"]}
    if selected and set(selected) - ids:
        raise CheckError("등록되지 않은 검사 그룹입니다.")
    groups = [group for group in config["groups"] if not selected or group["id"] in selected]
    passed = True
    for group in groups:
        folder = within(root, group["path"])
        implemented = implementation_present(folder, group.get("implementation_extensions", EXTENSIONS))
        test_present = folder.is_dir() and any(
            path.is_file() for check in group["checks"] if check["kind"] == "unittest"
            for path in folder.rglob(check.get("pattern", "test_*.py"))
        )
        if not group["required"] and not implemented and not test_present:
            print(f"{group['id']}: NOT_IMPLEMENTED (미구현; 기능 완료 아님)", file=stream)
            if selected:
                passed = False
                print("선택 검사 범위 미완료: 이 그룹은 실제 검사 0건입니다.", file=stream)
            continue
        if not folder.is_dir():
            print(f"{group['id']}: FAIL (필수 검사 폴더 없음)", file=stream)
            passed = False
            continue
        if not implemented and test_present:
            print(f"{group['id']}: TESTS_ONLY (구현 없음; 테스트만 검사)", file=stream)
        for check in group["checks"]:
            if check["kind"] == "unittest":
                argv = [sys.executable, "-B", str(root / "tools/run_checks.py"), "--worker",
                        group["path"], "--pattern", check.get("pattern", "test_*.py")]
            else:
                argv = validate_argv(check["argv"])
            try:
                code, output = invoke(root, argv, process)
                metrics = read_metrics(output)
                ok = evaluate(metrics, code)
                counters = {key: metrics.get(key, 0) for key in ("tests", "failures", "errors", "skipped", "unexpected_successes", "expected_failures")}
                print(f"{group['id']}: {'PASS' if ok else 'FAIL'} " + json.dumps(counters), file=stream)
                if not ok:
                    failed_ids = [name for name in metrics.get("failed_tests", [])
                                  if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.]+", name)]
                    if failed_ids:
                        print("실패 검사: " + ", ".join(failed_ids), file=stream)
                    print("필수 0개/SKIP/FAIL 또는 실행 오류를 확인하세요. 원시 출력은 기록하지 않습니다.", file=stream)
                    if check["kind"] == "unittest":
                        print("로컬 상세 확인: python -B -m unittest discover -s "
                              + json.dumps(group["path"], ensure_ascii=False) + " -p "
                              + json.dumps(check.get("pattern", "test_*.py")) + " -v", file=stream)
            except CheckError as exc:
                ok = False
                print(f"{group['id']}: FAIL ({exc})", file=stream)
            passed = passed and ok
    if not selected:
        for index, command in enumerate(config.get("references", []), 1):
            try:
                code, _ = invoke(root, validate_argv(command), process)
                ok = code == 0
            except CheckError:
                ok = False
            print(f"reference-{index}: {'PASS' if ok else 'FAIL'} (합성 검사; 실제 모듈/랩 아님)", file=stream)
            passed = passed and ok
    print("검사 결과는 등록된 코드/합성 범위이며 실기능·공개 안전성·학생 준비·원격 반영을 보증하지 않습니다.", file=stream)
    return passed


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", action="append", help="Registered group; repeat to select several")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--pattern", default="test_*.py", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if sys.version_info < MIN_PYTHON:
        print("Python 3.12 이상이 필요합니다.", file=sys.stderr)
        return 1
    try:
        root = Path.cwd()
        if args.worker:
            folder = within(root, args.worker)
            if "/" in args.pattern or "\\" in args.pattern or ".." in args.pattern:
                raise CheckError("잘못된 검사 패턴입니다.")
            metrics = run_suite(folder, args.pattern)
            print(PREFIX + json.dumps(metrics))
            return 0 if evaluate(metrics) else 1
        return 0 if run_registered(root, args.group) else 1
    except (CheckError, OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc, CheckError) else "검사 자료를 확인할 수 없습니다."
        print("FAIL: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
