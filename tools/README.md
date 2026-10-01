# 작업 기록 보조 도구와 필수 검사

학생은 `작업을 마무리해주세요`처럼 한 줄로 요청한다. 아래 명령은 Codex가 저장소 규칙을 읽고 실행하는 보조 수단이다. 학생이 양식을 직접 작성할 필요는 없다.

Python **3.12 이상**이 필요하다. Windows symlink/junction 경계 확인을 위해 낮은 버전은 거부한다. CI는 3.13, 이번 로컬 실증 환경은 3.13.12다. 3.12의 별도 실행 실증은 아직 없다. `python`/`py`가 같은 지원 Python을 가리키는지 확인한다. 저장소 루트에서 실행한다.

## 1. 작업별 기록 생성·체크포인트

```powershell
python -B tools/worklog.py init --team a --task-id auth-envelope
```

- `team`: `a`, `b`, `oracle`, `integration`, `common`. Oracle·Reporter는 `oracle` 한 팀이다.
- task-id는 공개 안전한 영문 소문자·숫자·하이픈 1~64자다. 이름·이메일을 넣지 않는다. 생략하면 안전한 랜덤 ID를 만들고, 현재 브랜치의 기존 관리 기록이 있으면 재사용한다.
- 현재 `codex/` 작업 브랜치만 사용한다. 브랜치를 만들거나 바꾸지 않는다. main·detached HEAD·다른 저장소 원격·루트가 아닌 폴더에서는 생성/갱신하지 않는다.
- 새 파일: `03_프로젝트/91_개발작업기록/YYYY-MM-DD_<team>_<task-id>.md`. `--kind setup`이면 `YYYY-MM-DD_<team>_setup_<task-id>.md`다. 날짜·시각은 명시한 한국 시간 UTC+09:00이다.
- 같은 작업은 같은 파일을 재사용한다. 다른 팀/task/브랜치 충돌, 기존 파일 덮어쓰기, 경로 탈출과 symlink/junction을 거부한다. 기록의 branch/task 대응은 협업 안전장치이며 작업자의 신원 인증·접근 권한 검증이 아니다.
- 관리 블록 없는 기존 기록이 같은 task-id로 발견되면 보존하고 중복 생성하지 않는다. Codex가 기존 파일을 수동으로 이어 쓴다. 과거 기록의 일괄 변환이나 임의 소유권 변경은 하지 않는다. 자기 task-id/브랜치 후보의 손상은 보존·확인하도록 멈춘다. 무관한 손상 기록은 읽기 대상에서 제외하고 `ignored_record_count`로 알리므로 다른 팀 전체를 멈추지 않는다. task-id 없이 같은 팀의 손상 후보가 남으면 자기 작업인지 확인한다.

```powershell
python -B tools/worklog.py refresh --record "03_프로젝트/91_개발작업기록/YYYY-MM-DD_a_auth-envelope.md"
```

실제 파일명을 `init` 결과에서 사용한다. `refresh`는 한 개의 `redharness-worklog:v1` JSON 관리 블록만 갱신한다. **블록 밖의 Codex 서술은 그대로 보존한다.** 같은 HEAD/변경 목록이면 파일을 다시 쓰지 않는다. 자신의 기록 변경을 자동 변경 목록에서 제외해 갱신 루프를 피한다. 작업 기준 `base_sha`는 최초 값이며 최신 관찰 HEAD와 다르다. 같은 폴더에서 동시에 기록을 쓰면 충돌을 확인해 멈추지만, 이 도구는 여러 사용자의 임의 파일 접근을 막는 권한 시스템이 아니다.

자동 수집 범위:

- schema_version, team, task_id, kind, 작업 branch, 기준 SHA, 생성/관찰 시각.
- 현재 HEAD·Git 변경 상태와 제한된 저장소 상대 경로. 이름·이메일·author/committer 값·절대 홈 경로·파일 내용·원시 로그·대상 주소·키·쿠키는 수집하지 않는다.
- `runs/`, 비밀 표식 경로, 이메일 표식, 알 수 없는 개인 경로 등은 내용을 기록하지 않고 제외 개수만 표시한다. 이 경로 필터는 완전한 개인정보 탐지기가 아니다. 공개 전 diff와 서술을 별도로 검토한다.
- 자동 블록의 `tests`와 `remote_state`는 항상 `unverified`다. cached refs·기록 양식·체크포인트 생성만으로 PASS/업로드/PR/main 완료를 주장하지 않는다.

`snapshot.changes`는 저장소 전체의 허용된 dirty 경로를 관찰한 정보이며 자기 task의 수정 목록이나 stage 목록이 아니다. 본문·공유에는 실제 자기 변경만 선별하고 관련 없는 변경은 보존한다.

자동 블록에 명령 출력·아이디어 본문·추가 개인정보 필드를 넣지 않는다. 본문에는 Codex가 **실제 변경·시도와 결과·아이디어 상태/확인된 이유·실제 테스트 PASS/FAIL/SKIP·막힘·다음 행동**을 현재 양식에 따라 작성한다. 실행하지 않은 검사, 읽지 못한 자료, 결정하지 않은 아이디어를 만들어 채우지 않는다. `check`가 본문의 진위나 민감성을 판단하는 것은 아니다.

## 2. 구조 확인과 종료 요약

```powershell
python -B tools/worklog.py check --record "03_프로젝트/91_개발작업기록/YYYY-MM-DD_a_auth-envelope.md"
python -B tools/worklog.py summary --record "03_프로젝트/91_개발작업기록/YYYY-MM-DD_a_auth-envelope.md"
```

`check`는 관리 JSON·팀/task/파일명/브랜치·기준 SHA와 자동 필드 형태를 확인한다. **구조 valid ≠ 테스트 통과 ≠ 민감성 검토 ≠ 실제 기능 완료**다. 실제 테스트 결과는 실행 증거를 보고 Codex가 별도로 요약한다. `summary`는 현재 Git HEAD와 작업 기록이 커밋 내용과 정확히 같은지 읽어서 보여 주며 파일을 수정하지 않는다. 원격/PR/main/실제 기능은 기본 미확인이다. 다른 브랜치에서 요약하면 branch 불일치를 표시하므로 자기 인계를 확인한다.

종료가 미완료 작업에도 적용되는 순서:

1. 저장소 시작 규칙과 실제 Git 변경, 자기 branch/PR/task-id를 확인한다.
2. 새 작업은 `init`, 자기 기존 관리 기록은 재사용한 뒤 `refresh`한다. 오래된 수동 기록은 그 파일을 이어 쓴다.
3. Codex가 실제 시도·아이디어·검증·막힘·다음 행동을 본문에 작성한다.
4. `check`와 `summary`를 실행해 기록 링크와 짧은 인계를 보여 준다. 구조와 실제 사실을 사람이 확인한다.

체크포인트는 의미 있는 작업 중에도 남긴다. 앱 종료 후 자동 기록을 약속하지 않는다. 이 도구에는 백그라운드 실행·세션 훅·commit·push·fetch·PR·Git 설정 변경이 없다. `작업을 마무리해주세요`는 기록 전용이며 업로드·병합 허가가 아니다. `작업을 마무리하고 공유해주세요`의 명시 공유와 같은 범위의 직접 위임은 [협업 규칙](../03_프로젝트/00_공통/CODEX_개발협업.md)을 따른다.

## 3. 별도 업로드 요청 후 읽기 전용 원격 확인

```powershell
python -B tools/worklog.py summary --record "03_프로젝트/91_개발작업기록/YYYY-MM-DD_a_auth-envelope.md" --remote-check
```

이 옵션을 명시한 경우에만 예상 공개 origin의 작업 브랜치를 `git ls-remote`로 읽는다. 원격 오류·인증 실패·브랜치 없음은 미확인이다. 토큰이나 로그인 값을 요청하거나 바꾸지 않는다.

`remote: head_and_committed_record_match`는 **현재 HEAD = 실제 원격 작업 브랜치 SHA**, 현재 branch = 기록 branch, 현재 기록 내용 = HEAD에 포함된 기록 내용이 모두 맞았다는 뜻이다. Windows checkout의 CRLF와 Git blob의 LF만 정규화하고 비교하며 실제 본문 변경·공백·추가 행은 차이로 유지한다. push 성공 메시지나 cached refs로 대신하지 않는다. 기록이 미커밋/수정 중이면 이 상태를 내지 않는다. PR 생성·검사·main 병합은 별도 실제 확인 대상이다. 원격 확인은 기록을 수정하지 않으므로 자기 최종 SHA를 넣기 위한 반복 commit을 하지 않는다.

## 4. 필수 오프라인 검사 runner

```powershell
python -B tools/run_checks.py
```

CI도 이 한 명령을 사용한다. 현재 공통 계약/저장, B 오프라인 참고 어댑터, tools 그룹을 필수 실행하고 기존 두 fixture와 A/B 합성 네 상태 재현을 수행한다. 테스트 그룹은 별도 Python 프로세스로 발견해 같은 테스트 파일명의 import 충돌과 tools 검사 재귀를 피한다. 필수 그룹은 **0개 발견·SKIP·FAIL·ERROR·예상외 성공(unexpected success)·예상 실패(expected failure)·실행 불가**를 실패로 처리한다. expectedFailure로 표시한 미완료 검사는 필수 통과 근거가 아니다. 의도한 선택적 실랩 검사를 필수 오프라인 그룹에 섞지 않는다.

A·Oracle·Dispatcher·통합 폴더는 구현 또는 검사 파일이 생기면 실행한다. 둘 다 없으면 `NOT_IMPLEMENTED (미구현; 기능 완료 아님)`을 출력한다. 테스트만 있는 폴더는 `TESTS_ONLY (구현 없음; 테스트만 검사)`를 함께 표시한다. 구현이 있는데 검사 0개면 실패한다. 미구현 팀에 가짜 PASS 검사나 팀장 승인 대기 조건을 만들지 않는다. 팀이 자신의 구현과 작은 완료 조건을 선택한다.

```powershell
python -B tools/run_checks.py --group tools
python -B tools/run_checks.py --group a --group oracle
```

선택 실행은 해당 그룹만 검사하며 전체 필수 통과를 뜻하지 않는다. 선택한 그룹 중 미구현/실제 검사 0건이 있으면 범위 미완료를 출력하고 0이 아닌 종료 코드로 반환한다. 기본 전체 실행은 아직 미구현인 선택 팀을 명시한 뒤 현재 필수 범위를 검사한다. 실패 시 안전한 검사 ID와 로컬 상세 `unittest discover` 명령을 안내한다. traceback/원시 입력은 자동으로 공개 기록에 복사하지 않는다. 예를 들어:

```powershell
python -B -m unittest discover -s tools -p "test_*.py" -v
```

현재 검사 성공은 등록된 코드/합성 범위의 검증이다. 실제 팀 프로토타입 채택, 외부 근거 진위, 인증우회/XSS 성공, 학생 환경 준비, 공개 안전성, GitHub 업로드·보호 설정을 보증하지 않는다. CI 파일 수정은 서버에서 실행됐다는 증거가 아니다.

## 5. 다른 언어 또는 새 검사 등록

`tools/checks.json`의 schema_version은 1이다. 그룹 id·상대 path·required·구현 확장자·검사 방법을 등록한다. 기본은 Python `unittest`의 `test_*.py`다. 테스트만 추가한 폴더도 검사한다. 파일 확장자로 발견하지 못하는 다른 언어를 추가할 때에는 해당 확장자를 등록한다.

다른 언어는 팀이 공개 안전한 오프라인 adapter를 작성하고 해당 그룹의 `checks`를 교체/추가한다:

```json
{"kind": "command", "argv": ["node", "03_프로젝트/02_전문모듈_A/check_adapter.js"]}
```

또는 `{"kind":"command","argv":["{python}","-B","팀폴더/check_adapter.py"]}`로 팀의 검사 도구를 연결한다. 실행 파일은 `{python}` 또는 `node` 검사 adapter만 허용하며 shell/Git/설정 명령은 거부한다. 명령은 argv 배열, `shell=False` 방식이며 `cmd /c`·PowerShell 문자열을 등록하지 않는다.

adapter는 정확히 한 줄의 결과 프로토콜을 출력하고 검사 실패 시 0이 아닌 종료 코드를 반환해야 한다:

```text
REDHARNESS_CHECK_RESULT={"tests":3,"failures":0,"errors":0,"skipped":0}
```

runner는 단순 종료 0만 믿지 않고 양의 실제 검사 수와 실패/오류/SKIP 0을 요구한다. Python adapter는 `unexpected_successes`, `expected_failures`도 출력하고 둘 모두 0이어야 한다. 이 개념이 없는 다른 언어 adapter는 두 필드를 생략할 수 있다(기본 0). 숫자나 결과를 임의로 만들어 쓰지 않는다. 검사 코드 자체는 실행되는 프로젝트 코드이며 이 runner가 그 코드를 보안 sandbox로 격리하지는 않는다. 네트워크·API·실랩 없이 수행하는 검사만 등록하고 변경의 범위·테스트를 PR에 남긴다. 공통 검증 규칙의 변경/생략은 기존 공통 예외 절차를 따른다. 일반 팀 PR에 짝 검토·팀장 승인을 추가하지 않는다.
