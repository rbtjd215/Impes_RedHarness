"""Store an offline run without changing Oracle's verdict or caller inputs."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from offline_oracle import InputError, action, json_copy, validate_complete_run


def store(records, path):
    """Accept D/specialist/Oracle; create a new file and verify it by rereading.

    Existing files are never overwritten. A failed operation can leave a partial
    file; storage failure is returned separately and does not change the verdict.
    """
    records = json_copy(records)
    if not isinstance(records, list) or len(records) != 3:
        raise InputError("Expected Dispatcher, specialist and Oracle envelopes")
    reporter = copy.deepcopy(records[2])
    if not isinstance(reporter, dict):
        raise InputError("Invalid Oracle envelope")
    reporter.update(producer="REPORTER", observation={"execution_mode": "offline_mock",
                    "storage": "written"}, actions=[action("report", "Write and reread synthetic run")],
                    error=None, next_action="Review the stored synthetic run")
    snapshot = records + [reporter]
    if (validate_complete_run(snapshot)
            or any(item["observation"].get("execution_mode") != "offline_mock"
                   or item["target_id"] != "SYNTHETIC-ONLY" for item in snapshot)):
        raise InputError("Expected a complete synthetic offline run")
    outcome = {"storage": "failed", "reporter": copy.deepcopy(reporter), "error": None}
    try:
        # Exclusive creation keeps previous results intact, including symlinks.
        with Path(path).open("x", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        restored = read_run(path)
        if restored != snapshot:
            raise ValueError("Stored content differs")
        outcome.update(storage="written_and_verified", reporter=copy.deepcopy(restored[3]))
    except (OSError, ValueError, TypeError):
        # Never expose OS messages, paths, original inputs or exception payloads.
        outcome["error"] = {"kind": "storage_error", "summary": "Write or read-back verification failed"}
        outcome["reporter"]["observation"]["storage"] = "failed"
        outcome["reporter"]["error"] = copy.deepcopy(outcome["error"])
        outcome["reporter"]["next_action"] = "Resolve storage failure and use a new output file"
    return outcome


def read_run(path):
    """Read and validate a stored complete-v1 run; truth is not inferred."""
    with Path(path).open(encoding="utf-8") as handle:
        records = json.load(handle)
    if validate_complete_run(records):
        raise ValueError("Invalid stored complete-v1 run")
    return records
