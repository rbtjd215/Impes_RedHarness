"""Reproduce Oracle/Reporter fixtures; temporary storage, no network or lab."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import tempfile

from offline_oracle import InputError, decide
from offline_reporter import store


def load_cases():
    return json.loads(Path(__file__).with_name("sample_io.json").read_text(encoding="utf-8"))


def inputs(case, module):
    base = dict(contract_version="1.0", run_id=f"RH-OR-{module}-{case['id']}",
                target_id="SYNTHETIC-ONLY", selected_module=module, producer="DISPATCHER",
                observation={"execution_mode": "offline_mock"}, actions=[], status="NOT_RUN",
                evidence=[], error=None, next_action="Read a synthetic fixture")
    specialist = copy.deepcopy(base)
    specialist.update(producer=module, next_action="Ask the offline Oracle")
    if case["specialist_active"]:
        specialist["actions"] = [{"kind": "synthetic_observation", "source": "synthetic-specialist",
                                  "summary": "Attempted a fabricated task"}]
        specialist["status"] = "UNKNOWN"
    if case.get("claim"):
        specialist["observation"]["claim"] = case["claim"]
    criterion = dict(criterion_id="MOCK-EXPLICIT-OUTCOME", target_id=base["target_id"],
                     selected_module=module, success_value="confirmed-success", failure_value="confirmed-failure")
    check = copy.deepcopy(case.get("check"))
    if check is not None:
        check.update({key: base[key] for key in ("run_id", "target_id", "selected_module")})
        check.update(criterion_id=criterion["criterion_id"], execution_mode="offline_mock",
                     source="synthetic-observer")
    return base, specialist, criterion, check


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=("A", "B", "both"), default="both")
    args = parser.parse_args(argv)
    modules = ("A", "B") if args.module == "both" else (args.module,)
    failed = False
    try:
        with tempfile.TemporaryDirectory(prefix="redharness-oracle-") as directory:
            for module in modules:
                for case in load_cases():
                    dispatcher, specialist, criterion, check = inputs(case, module)
                    oracle = decide(specialist, criterion, check)
                    result = store([dispatcher, specialist, oracle],
                                   Path(directory) / f"{module}-{case['id']}.json")
                    ok = oracle["status"] == case["expected_status"] and result["storage"] == "written_and_verified"
                    print(f"offline_mock {module} {case['id']}: {'PASS' if ok else 'FAIL'} "
                          f"(Oracle {oracle['status']}; storage {result['storage']})")
                    failed |= not ok
    except (OSError, ValueError, TypeError, KeyError, InputError):
        print("Offline reproduction failed; inspect fixture structure locally")
        return 1
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
