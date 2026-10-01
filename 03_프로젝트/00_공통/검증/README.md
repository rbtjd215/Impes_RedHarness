# 공통 계약·완성 흐름·합성 저장 검증

[PROJECT_SPEC.md](../PROJECT_SPEC.md)의 wire v1과 완성 프로필 `complete-v1`을 구분한다. 1~4절의 합성 참고 검사는 Python 표준 라이브러리만 사용하며 네트워크 요청·브라우저·모델 API·실제 공격·학생 모듈을 실행하지 않는다. 5절 등록 러너는 등록된 팀 테스트 코드를 실제 실행하므로 해당 코드의 공개 안전·오프라인 범위를 별도로 검토한다. 명령은 저장소 루트에서 실행한다.

## 1. 기존 부분 형식 검사 · 호환 유지

```powershell
python -B "03_프로젝트/00_공통/검증/check_contract.py" "03_프로젝트/00_공통/검증/fixtures/mock_a_pass.json" "03_프로젝트/00_공통/검증/fixtures/mock_b_unknown.json"
```

각 JSON은 단일 공통 봉투 또는 한 run의 봉투 배열이다. 작성 중 단일 A/B 봉투와 부분 흐름을 허용한다. 필수 필드·식별자·단계 순서·Oracle 단일 최종 판정·Reporter 상태/근거 보존을 검사한다. `next_action`의 빈 문자열도 형식상 허용한다. Reporter 단독 봉투는 Oracle과의 일치를 확인할 수 없어 거부한다.

이 기본 모드는 기존 샘플·B 부분 검사 호환성을 유지한다. **통과했다고 네 단계가 모두 있거나 근거 항목의 최소 외피가 갖춰졌다는 뜻은 아니다.** `contract_version: 1.0`을 바꿔 기본 검사를 조용히 강화하지 않았다.

## 2. 완성 실행 프로필 검사 · 별도 선택

```powershell
python -B "03_프로젝트/00_공통/검증/check_contract.py" --complete "03_프로젝트/00_공통/검증/fixtures/complete/mock_pass.json" "03_프로젝트/00_공통/검증/fixtures/complete/mock_fail.json" "03_프로젝트/00_공통/검증/fixtures/complete/mock_unknown.json" "03_프로젝트/00_공통/검증/fixtures/complete/mock_not_run.json"
```

- 정확히 Dispatcher → 선택된 A/B → Oracle → Reporter 네 봉투와 일치하는 run/target/module/version을 요구한다.
- 각 봉투의 observation.execution_mode를 `offline_mock`/`local_lab` 중 하나로 표시하고 같은 실행에서는 일치시킨다.
- actions는 kind/source/summary 객체, evidence는 kind/source/criterion_id와 summary 또는 evidence_ref, execution_mode를 요구한다. 분야별 추가 필드는 팀이 정한다.
- Oracle PASS/FAIL은 비어 있지 않은 verification 근거, 각각 matched/not_matched 결과, execution_basis와 같은 기준의 verify 행동에 연결한다. `[null]`이나 성공 기준을 그대로 둔 FAIL을 거부한다.
- A/B NOT_RUN 뒤 Oracle PASS/FAIL을 무조건 오류로 취급하지 않는다. `independent_check`와 실제 Oracle 확인 기준 연결을 기록하면 형식상 가능하다. 실제 독립 확인의 진위는 별도 실행 증거로 판단한다.
- 저장 실패 봉투도 Oracle status/evidence를 보존하고 Reporter 자신의 error로 드러내면 유효하다. 구조 통과와 저장 완료는 다르다.

## 3. 네 상태의 작은 참고 실행·저장 · 한 명령

```powershell
python -B "03_프로젝트/00_공통/검증/run_mock_pipeline.py" --all
```

합성 PASS/FAIL/UNKNOWN/NOT_RUN을 만들고 complete-v1 검사 → OS 임시 폴더에 저장 → 재읽기/보존 검사를 실행한 뒤 정리한다. 기본값은 A이고 `--module B`로 B를 재현할 수 있다. 출력의 `storage PASS`는 합성 저장 검사 통과이며 그 옆의 final status FAIL/UNKNOWN/NOT_RUN과 모순되지 않는다.

파일을 남겨 살펴보고 싶을 때만 `--output-dir "<저장소 밖 로컬 결과 폴더>"`를 지정한다. 생성 파일은 실제 실행 기록이 아니며 Git에 올릴 필요가 없다. 참고 코드의 `build_mock_run(scenario, selected_module)`·`store_run(records, path)`는 팀이 함수/CLI 입출력을 조율할 작은 예시다. 팀의 계획·프로토타입·실제 저장 방식 채택을 대신 결정하지 않는다.

`store_run`은 호출자의 입력 봉투를 변경하지 않고 별도 복사본을 저장한다. 반환값의 `storage`가 `written_and_verified`여야 저장/재읽기 성공이다. 실패하면 `storage: failed`, 별도 error와 Reporter 오류 봉투를 반환하며 Oracle status/evidence는 그대로 둔다. 원시 오류 메시지·사용자 홈 경로·계정명은 출력하지 않는다.

## 4. 회귀·저장·B 단위 검사

```powershell
python -B -m unittest discover -s "03_프로젝트/00_공통/검증" -p "test_*.py" -v
python -B -m unittest discover -s "03_프로젝트/03_전문모듈_B" -p "test_*.py" -v
```

공통 검사는 기존 부분 형식 호환, 네 상태, 필수 단계, 최소 근거, 판정/근거 연결, 독립 확인, mock/실제 라벨 혼용, Reporter 저장/재읽기·입력 불변·저장 실패·변조 감지를 다룬다. B 검사는 합성 후보와 최소 근거 외피의 연결을 다루며 실제 브라우저 증거를 다루지 않는다. 실제 테스트 수·종료 코드를 기록한다. **0개 발견은 통과가 아니다.**

## 5. 등록 검사 러너

`tools/checks.json`에 등록된 오프라인 명령은 저장소 루트에서 `python -B tools/run_checks.py`로 실행한다. 기본 호출은 필수 common·b·tools 검사와 선택 팀 구현 상태를 확인하며 `--group common`, `--group b`, `--group tools`, `--group a`, `--group oracle`, `--group dispatcher`, `--group integration`으로 관련 범위만 선택할 수 있다. 기본 전체 실행에서 선택 팀이 미구현이면 `NOT_IMPLEMENTED`로 밝히고 현재 필수 검사만 계속한다. 미구현 팀을 `--group a`처럼 명시 선택하면 범위 미완료와 비성공 종료 코드를 낸다. 구현 없이 테스트만 있으면 `TESTS_ONLY`로 표시해 그 검사를 실행한다. 구현 파일이 있는데 테스트가 없거나 필수 검사 0개/FAIL/ERROR/SKIP/expected failure/unexpected success이면 미통과다. 완료를 주장할 때는 발견 수·실제 종료 코드·기준 SHA·검증 범위를 기록한다.

이 러너는 등록된 검사 코드를 실행하며 네트워크·Git 설정·원격 조작 명령을 자체 추가하지 않는다. 등록된 검사 코드 자체를 격리하는 보안 샌드박스는 아니다. `tools/worklog.py check`의 메타블록 구조 통과와 Git clean은 이 검사 결과를 대신하지 않는다. 두 도구는 **Python 3.12 이상**을 요구하고 CI 기준은 3.13이다. `python`과 `py` 중 실제 사용하는 명령이 같은 지원 버전·환경인지 확인한다. 도구와 CI의 통과를 학생 준비 완료나 실제 모듈 완료로 표시하지 않는다.

## 6. CI의 적용 상태

[`offline-checks.yml`](../../../.github/workflows/offline-checks.yml)은 모든 PR과 main push에서 `python -B tools/run_checks.py` 한 명령을 실행한다. 등록된 common·b·tools 필수 검사와 구현된 선택 팀 테스트를 수행하며 선택 미구현은 `NOT_IMPLEMENTED`로 보고한다. 실제 서버 실행 여부와 결과는 해당 PR의 검사와 Actions에서 확인한다. 토큰 권한은 contents: read이며 비밀값·API 키를 전달하거나 실제 랩을 호출하지 않는다.

2026-10-01에 [공식 checkout 사용법](https://github.com/actions/checkout#usage)과 [공식 setup-python 사용법](https://github.com/actions/setup-python#basic-usage)의 `@v7`을 확인해 사용했다. Python은 3.13으로 명시했다. **로컬 파일 작성과 로컬 검사 통과는 GitHub CI 실행이나 필수 체크/보호 설정 적용을 뜻하지 않는다.** main의 필수 검사는 실제 PR에서 실행된 체크 이름·결과에 맞춘다. PR·필수 CI 통과·강제 push/삭제 금지 정책의 적용은 GitHub 설정에서 확인한다. 필수 인적 승인 수는 0이다.

## 검증 한계와 기록

합성 예시는 실제 대상·모듈·Oracle 판정 기준·Reporter 구현의 완료가 아니다. 정적 검사는 근거 진위, 실제 실행 사실, 공개 요약의 민감성, 허용 목록 준수를 증명하지 않는다. 허용 랩·외부 판정·학생 환경은 별도 확인하고 미실행 항목은 SKIP과 이유를 남긴다. 제품 봉투 PASS/FAIL/UNKNOWN/NOT_RUN과 작업 기록의 테스트 PASS/FAIL/SKIP은 구분한다.
