# Oracle Reporter offline verification

Verified on 2026-10-26 (Asia/Seoul), baseline
`881680333826c0c9e0db1fb28ba9712369660d9e`, with the uncommitted prototype on
`codex/oracle-offline-prototype-1026`. Python 3.12.14 was invoked by its full
bundled-runtime path; `python` and `py` are not on PATH in this checkout environment.
Commands below use `python` as a placeholder for that supported interpreter.

## Reproduce from the repository root

```powershell
python -B tools/run_checks.py
python -B tools/run_checks.py --group oracle
python -B "03_프로젝트/04_Oracle_Reporter/run_offline.py"
```

The registry already includes the oracle group; no shared registry or other team
code was changed. The default demo runs both module labels. Use `--module A` or
`--module B` for one. These are synthetic specialist inputs, not calls to the
actual A/B implementations. All demo outputs are stored, reread and removed in
an OS temporary directory. No real target, browser, model API or credentials are used.

## Actual results

| Check | Result | Evidence and scope |
|---|---|---|
| Full registered runner | PASS, exit 0 | common 42, b 16, tools 33, a 15, oracle 21: 127 tests, zero failures/errors/skips; three common references PASS |
| Oracle suite, final full run | PASS | 21 test methods; subtests include both A/B labels and all compact fixtures |
| Team demo | PASS, exit 0 | Nine fixtures × two module labels = 18 runs; expected verdicts and written_and_verified storage all matched |
| Dispatcher / full integration | NOT_IMPLEMENTED | Reported by the runner, not marked as passed functionality |
| Real lab / real vulnerability verification | SKIP | Approved target, version, reset procedure and request/time limits are not defined |
| Remote CI, upload and PR | SKIP | Local-only work requested; no commit, push or PR for this prototype |

The first focused suite had 20 passing tests. A conflicting-observation case was
then added, and the full runner above passed the final 21-test Oracle suite.

## Case mapping

| Specification cases | Executed evidence |
|---|---|
| OR-01–OR-08 | Fixture verdicts for both labels; linked verify/evidence, original inputs unchanged; error, absent marker, unsupported claim, independent PASS and FAIL |
| OR-09 | Missing field, specialist final PASS/FAIL, mismatched run/target/module/criterion/source/mode rejected as InputError |
| RP-01 | Both labels, all fixtures; stored/reread four envelopes; first three preserved and Oracle/Reporter status/evidence equal |
| RP-02 | Injected write error; Oracle PASS and evidence preserved; safe storage_error, no raw exception text |
| RP-03 | Injected read error and changed preceding envelope; verification failed without changing Oracle verdict |
| CT-01 | Missing/duplicate stages, mixed execution modes and changed Reporter evidence rejected by complete-v1 |
| Additional boundaries | Existing file unchanged; malformed actions/evidence, invalid criterion, unsupported target/mode, nonfinite/non-JSON data and activity mismatch rejected; unattempted check does not create execution; conflicting values remain UNKNOWN |

These tests verify the team's offline implementation. They do not prove evidence
truth, real A/B integration, actual exploit success, production storage durability,
server branch protections or individual authorship. The prototype accepts explicit
synthetic observations from its caller; there is no trusted live observer adapter.

## Local demonstration

1. Show `MODULE_SPEC.md`, `판정규칙.md` and `sample_io.json` to explain the interface.
2. Run the team demo; explain that a line can have a test PASS and Oracle FAIL:
   the test passed because the expected negative verdict was produced.
3. Run the registered runner and show the oracle group and total results.
4. Show `test_oracle_reporter.py` for failure and preservation checks, then the
   task journal for baseline, branch and remaining limits.

Cloning the remote repository again will not include these uncommitted files.
For a remote review, they must first be explicitly published on a task branch and
linked from a PR; local demonstration does not require publication.

## Publication checkpoint

After the local-only verification checkpoint above, publication was explicitly
requested. Draft PR [#8](https://github.com/rbtjd215/Impes_RedHarness/pull/8) was
created for review from `codex/oracle-offline-prototype-1026` into `main`.
The initial implementation commit was `671e5139f3546e33b73c1fcdd03e38ff3e7cad1c`;
its remote branch SHA and PR head matched. The PR is a draft and was not merged.
Subsequent documentation records this publication; code and fixtures are unchanged.
Remote CI is separate from the local 127-test result and must be checked on the PR.
