"""Optional offline reference for four-stage validation and Reporter storage.

Uses fabricated observations only. No team module, network, browser or model API
is invoked. The reference does not replace the teams' implementation decisions.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from check_contract import validate_complete_run


STATUSES = ("PASS", "FAIL", "UNKNOWN", "NOT_RUN")
CRITERION = "MOCK-COMPLETION-MARKER"


def _action(kind: str, summary: str, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "source": "offline reference", "summary": summary, **extra}


def build_mock_run(scenario: str, selected_module: str = "A") -> list[dict[str, Any]]:
    """Build one fabricated run; Oracle maps a synthetic check to one status."""
    if scenario not in STATUSES or selected_module not in ("A", "B"):
        raise ValueError("expected a known synthetic scenario and A or B")
    result = {
        "PASS": "matched", "FAIL": "not_matched",
        "UNKNOWN": "inconclusive", "NOT_RUN": "not_checked",
    }[scenario]
    oracle_status = {
        "matched": "PASS", "not_matched": "FAIL",
        "inconclusive": "UNKNOWN", "not_checked": "NOT_RUN",
    }[result]
    base = {
        "contract_version": "1.0",
        "run_id": f"RH-REFERENCE-{selected_module}-{scenario}",
        "target_id": "SYNTHETIC-ONLY",
        "selected_module": selected_module,
        "producer": "DISPATCHER",
        "observation": {"execution_mode": "offline_mock", "source": "fabricated scenario"},
        "actions": [], "status": "NOT_RUN", "evidence": [],
        "error": None, "next_action": "Pass synthetic input to the reference specialist",
    }
    specialist = copy.deepcopy(base)
    specialist.update(producer=selected_module, next_action="Ask the reference Oracle")
    if scenario != "NOT_RUN":
        specialist["status"] = "UNKNOWN"
        specialist["actions"] = [_action("synthetic_observation", "Read fabricated completion input")]
    oracle = copy.deepcopy(base)
    oracle.update(producer="ORACLE", status=oracle_status, next_action="Preserve the Oracle envelope")
    oracle["observation"]["synthetic_check"] = result
    if scenario != "NOT_RUN":
        oracle["actions"] = [_action("verify", "Compare a fabricated criterion", criterion_id=CRITERION)]
    if scenario in ("PASS", "FAIL"):
        oracle["evidence"] = [{
            "kind": "verification", "source": "synthetic verifier", "criterion_id": CRITERION,
            "summary": "Fabricated completion criterion comparison; no real target",
            "execution_mode": "offline_mock", "execution_basis": "specialist_execution",
            "result": result,
        }]
    reporter = copy.deepcopy(oracle)
    reporter.update(producer="REPORTER", actions=[_action("report", "Prepare the synthetic run for storage")],
                    next_action="Store and reread the synthetic run")
    reporter["observation"] = {"execution_mode": "offline_mock", "storage": "not_attempted"}
    return [base, specialist, oracle, reporter]


def store_run(records: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    """Validate, atomically store and reread a copy; never mutate caller envelopes.

    A failure returns a separate storage outcome, retaining Oracle's verdict and
    evidence. It does not turn a PASS into FAIL or claim a failed write succeeded.
    """
    snapshot = copy.deepcopy(records)
    errors = validate_complete_run(snapshot)
    if errors:
        raise ValueError("invalid complete-v1 run: " + "; ".join(errors))
    oracle = snapshot[2]
    outcome: dict[str, Any] = {
        "storage": "failed", "status": oracle["status"],
        "evidence": copy.deepcopy(oracle["evidence"]), "error": None,
        "reporter": copy.deepcopy(snapshot[3]),
    }
    temporary: Path | None = None
    try:
        snapshot[3]["observation"]["storage"] = "written"
        snapshot[3]["error"] = None
        snapshot[3]["next_action"] = "Review the stored synthetic run"
        path.parent.mkdir(parents=True, exist_ok=True)
        # The temporary file lives beside the destination for atomic replacement.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".redharness-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        temporary = None
        with path.open(encoding="utf-8") as handle:
            restored = json.load(handle)
        if restored != snapshot or validate_complete_run(restored):
            raise ValueError("stored run does not preserve the validated snapshot")
        outcome.update(storage="written_and_verified", reporter=copy.deepcopy(restored[3]))
    except (OSError, ValueError, TypeError) as exc:
        # Do not echo paths, payloads, OS account names, or raw exception messages.
        outcome["error"] = {"kind": "storage_error", "exception_type": type(exc).__name__}
        outcome["reporter"]["observation"]["storage"] = "failed"
        outcome["reporter"]["error"] = copy.deepcopy(outcome["error"])
        outcome["reporter"]["next_action"] = "Resolve storage failure; preserve the Oracle verdict"
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic offline reference; no real modules or targets")
    parser.add_argument("--all", action="store_true", help="Reproduce all four final states")
    parser.add_argument("--scenario", choices=STATUSES, default="PASS")
    parser.add_argument("--module", choices=("A", "B"), default="A")
    parser.add_argument("--output-dir", type=Path, help="Explicit local output directory; keep results out of Git")
    args = parser.parse_args(argv)
    scenarios = STATUSES if args.all else (args.scenario,)

    def reproduce(directory: Path) -> int:
        failed = False
        for scenario in scenarios:
            records = build_mock_run(scenario, args.module)
            outcome = store_run(records, directory / f"mock_{args.module.lower()}_{scenario.lower()}.json")
            verified = outcome["storage"] == "written_and_verified"
            print(f"offline_mock {args.module} {scenario}: complete-v1 + storage "
                  f"{'PASS' if verified else 'FAIL'} (final status {outcome['status']})")
            failed = failed or not verified
        return 1 if failed else 0

    if args.output_dir is not None:
        return reproduce(args.output_dir)
    # Default one-command reproduction leaves no execution files in the repo.
    with tempfile.TemporaryDirectory(prefix="redharness-reference-") as directory:
        return reproduce(Path(directory))


if __name__ == "__main__":
    raise SystemExit(main())
