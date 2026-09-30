---
tags: [project, contract]
version: 0.3
wire_contract_version: '1.0'
completion_profile: complete-v1
status: draft
---

# RedHarness 공통 프로젝트 계약

이 문서는 공개 가능한 공통 인터페이스와 실행 경계를 정의한다. 팀별 구현과 내부 절차는 각 팀이 정한다. 다른 팀에 영향을 주는 변경은 해당 팀과 조율하고, 공통 필수 계약·최종 판정 책임·자동 실행 허용 범위의 변경이나 예외는 동아리장의 명시 승인을 받는다. 계약 버전 1.0은 현재 작업 기준이며 최종 동결 승인을 뜻하지 않는다.

`version: 0.3`은 이 설명 문서의 판이며 JSON의 `contract_version: 1.0`과 다르다. 2026-10-01 보완안 적용에서 기존 v1 부분 형식 검사와 별도로 **완성 실행 프로필 `complete-v1`**을 추가했다. 기존 필수 봉투 필드·상태 의미와 기본 검사 호환성은 유지한다. 부분 봉투나 예전 v1 샘플이 기본 검사를 통과해도 완성 실행 프로필을 충족한 것은 아니다. 이 로컬 변경의 원격/main 반영 상태는 실제 Git 보고에서 확인한다.

## 구조와 책임

    실행 요청 → Dispatcher → 전문 모듈 A 또는 B → 허용된 로컬 랩
             → Oracle → Reporter와 실행 기록

| 단계 | 입력 | 출력과 책임 |
|---|---|---|
| Dispatcher | 허용된 실행 요청과 대상 ID | A 또는 B를 선택하고 공통 봉투를 전달 |
| A · 인증우회 | A로 선택된 봉투와 허용 대상 정보 | 관찰·행동·근거 후보·오류·다음 행동을 반환; 필수 목표 L1 |
| B · XSS | B로 선택된 봉투와 허용 대상 정보 | 관찰·행동·근거 후보·오류·다음 행동을 반환; 필수 목표 L0 |
| Oracle | 전문 모듈 봉투와 해당 문제의 확인 기준 | 외부 근거를 확인해 최종 상태를 한 번 판정 |
| Reporter | Oracle 봉투 | 상태와 근거를 보존하고 실행 흐름을 기록 |

A와 B는 각기 분야별 판단·도구 사용 전략을 설계할 수 있다. 최종 PASS/FAIL은 Oracle만 내리며, Reporter는 다시 판정하지 않는다.

## v1 공통 봉투

모든 단계는 아래 필드를 가진 JSON 객체를 주고받는다. 각 단계의 결과를 한 실행 기록에 모을 때는 생성 순서대로 별도 봉투를 보존한다.

    {
      "contract_version": "1.0",
      "run_id": "string",
      "target_id": "string",
      "selected_module": "A | B",
      "producer": "DISPATCHER | A | B | ORACLE | REPORTER",
      "observation": {},
      "actions": [],
      "status": "PASS | FAIL | UNKNOWN | NOT_RUN",
      "evidence": [],
      "error": null,
      "next_action": "string"
    }

- contract_version, run_id, target_id, selected_module은 한 실행을 관통하는 식별자다. selected_module은 A 또는 B 하나다.
- producer는 현재 봉투를 만든 단계다. observation은 관찰 객체, actions와 evidence는 배열이다.
- error는 오류가 없으면 null로 둔다. 오류가 있으면 설명 문자열 또는 구조화된 객체를 사용할 수 있다.
- next_action은 다음 행동을 설명하는 문자열이다.
- 상태와 근거는 검증 가능한 사실을 기록한다. 모델의 주장만으로 성공을 확정하지 않는다.

| 상태 | 의미 |
|---|---|
| PASS | 외부에서 확인 가능한 성공 증거가 있음 |
| FAIL | 실제 실행했고 실패 근거가 있음 |
| UNKNOWN | 실행했지만 판정 근거가 부족함 |
| NOT_RUN | 실제로 실행하지 않음 |

| 단계 | 상태 사용 규칙 |
|---|---|
| Dispatcher·A·B | 미실행은 NOT_RUN, 실행 후 Oracle 판정 전은 UNKNOWN. 최종 PASS/FAIL을 쓰지 않음 |
| Oracle | 허용된 대상의 증거로 PASS/FAIL/UNKNOWN/NOT_RUN 중 하나를 최종 판정 |
| Reporter | Oracle의 status와 evidence를 그대로 유지 |

Reporter 봉투의 observation, actions, error, next_action은 저장 단계 자체를 설명할 수 있다. 실행 기록에는 앞선 Dispatcher·전문 모듈·Oracle 봉투를 원형대로 순서 있게 보존한다. 기본 JSON 형식 검사는 필드·순서·상태·근거 일치를 확인하지만 실제 파일 저장, 원본 불변성 또는 증거의 진위를 증명하지는 않는다. 아래 합성 저장 참고 예시의 통과도 학생의 실제 Reporter·랩 실행 완료와 구분한다.

## 완성 실행 프로필 · complete-v1

부분 구현의 `validate_document`/기본 명령은 유지한다. 한 실행을 완성된 흐름으로 확인하려면 `validate_complete_run` 또는 `check_contract.py --complete`를 사용한다. 이 프로필은 **Dispatcher → 선택된 A/B → Oracle → Reporter**의 정확히 네 봉투를 요구한다. 한 단계의 여러 행동은 그 봉투의 actions에 모으며, 재시도/다른 실행은 별도 run_id를 쓴다. 식별자 일치·단계 누락/중복·최종 상태 책임·Reporter의 상태/근거 보존을 검사한다.

모든 봉투의 `observation.execution_mode`는 같은 `offline_mock` 또는 `local_lab`이다. 실행한 사실을 나타내는 출처 라벨이지 실행 여부 자체가 아니다. mock은 합성 관찰로만 작성하고 실제 랩 완료로 보고하지 않는다. `local_lab`라는 문자열만으로 대상 허가·실제 접속이 증명되는 것도 아니다.

### 행동·근거의 최소 외피

actions의 각 항목은 `kind`, `source`, `summary`의 비어 있지 않은 문자열을 가진 객체다. 행동이 없으면 빈 배열을 사용한다. Oracle의 최종 검증 행동은 `kind: verify`와 확인한 `criterion_id`를 함께 쓴다.

evidence의 각 항목은 다음 최소값을 가진 객체다. 분야별 `contexts`, `sink` 등 추가 분석 필드는 팀이 정할 수 있다.

| 필드 | 의미 |
|---|---|
| kind | 후보/검증의 종류. A/B의 분야별 후보 이름은 자율이며 최종 근거는 `verification` |
| source | 공개 가능한 관찰·확인 출처 식별자. 실제 키·쿠키·개인주소 대신 안전한 이름 |
| criterion_id | 어떤 확인 기준과 연결되는지 나타내는 공개 가능한 ID |
| summary 또는 evidence_ref | 비어 있지 않은 안전한 요약 또는 근거 식별자. 원시 응답·개인 홈 경로·비밀 URL은 넣지 않음 |
| execution_mode | 해당 봉투와 동일한 `offline_mock` 또는 `local_lab` |

Oracle 최종 PASS/FAIL의 evidence는 비어 있지 않은 `verification` 항목으로만 구성한다. 각 항목에는 `result`와 `execution_basis`가 추가된다.

- `result: matched`는 PASS의 성공 기준 확인, `not_matched`는 FAIL의 실패 기준 확인을 뒷받침한다. 이것은 개별 기준 관찰이며 최종 상태를 다시 판정하는 별도 Oracle이 아니다. 다른 맥락 설명은 observation 또는 후보 봉투에 보존한다.
- matched/not_matched는 Oracle이 분야별 확인 기준과 실제 관찰을 검토해 표준화한 결과다. 단순히 표식이 없거나 도구가 오류를 냈다는 사실만으로 FAIL을 만들지 않으며, 실패 근거가 불충분하면 UNKNOWN 또는 실제 미실행이면 NOT_RUN을 사용한다.
- `execution_basis: specialist_execution`이면 앞선 A/B는 `UNKNOWN`과 비어 있지 않은 실제 행동 기록을 가진다.
- `execution_basis: independent_check`이면 Oracle가 자체적으로 확인한 외부 근거에 의존한다. **A/B가 NOT_RUN이었다는 이유만으로 Oracle PASS/FAIL을 일괄 거부하지 않는다.** 같은 criterion_id의 Oracle verify 행동과 근거를 명시하며 실제로 독립 확인했는지는 별도 실행 증거로 검토한다.
- 각 최종 근거의 criterion_id는 Oracle actions의 verify 기준과 연결돼야 한다. 문자열·연결 검사만으로 근거의 진위는 보장하지 않는다.
- 최종 UNKNOWN은 A/B 또는 Oracle가 수행한 행동이 있지만 판정 근거가 부족한 경우다. 최종 NOT_RUN은 A/B·Oracle의 실행 행동과 최종 근거가 없는 경우다. Reporter의 기록 행동은 이 실행 여부를 바꾸지 않는다.

Reporter가 저장에 실패하면 Oracle status/evidence를 유지한 채 자신의 `observation.storage: failed`, `error: {kind: storage_error, ...}`와 다음 행동으로 드러낸다. **실행의 최종 PASS와 저장 완료는 별도 결과다.** 네 봉투가 형식상 유효해도 저장 성공이라고 보고하지 않는다. 실제 저장·재읽기·앞선 봉투 보존은 저장 검증으로 확인한다.

### 작은 연결 예시와 팀 선택

검증 폴더의 `run_mock_pipeline.py`는 `build_mock_run(scenario, selected_module)`과 `store_run(records, path)`를 사용하는 **합성 전용 참고 구현**이다. 다음 한 명령으로 네 상태의 구조 검사·임시 저장·재읽기를 재현한다.

    python -B "03_프로젝트/00_공통/검증/run_mock_pipeline.py" --all

기본 실행은 OS 임시 폴더를 정리하며 네트워크·브라우저·모델 API·실제 공격·팀 모듈을 호출하지 않는다. 팀은 자신의 함수/CLI 진입점을 입력 봉투 → 출력 봉투의 작은 예시로 조율한다. 이 참고 함수·저장 방식을 실제 모듈에 채택할 의무는 없다. 호출 방식·도메인 판정 전략은 팀 자율이며 공통 필수 의미를 바꾸는 경우에만 예외 절차를 따른다.

## 실행 대상과 기록 경계

- 자동 요청은 버전과 초기화 방법을 고정한, 허가된 자체 로컬 교육용 랩에만 보낸다.
- 대상 주소·포트·버전·초기화·최대 요청 횟수·시간 한도를 실행 전에 별도로 확정한다. 허용 목록이 비어 있으면 실대상 자동 실행을 하지 않는다.
- 공개 웹 학습 자료에는 자동 공격 도구를 연결하지 않는다.
- API 키는 환경변수로만 전달한다. 저장소, 작업 기록, 실행 로그, 채팅에 키·쿠키·개인정보를 남기지 않는다.
- 이 저장소는 공개다. 내부 교안·운영 문서, 원시 실행 결과, 민감한 대상 정보와 비밀 설정은 여기에 복사하지 않는다. 공개 가능한 mock과 검토된 코드만 다룬다.
- 실제 랩이나 모델을 사용할 수 없으면 mock 입력과 검증된 예시 로그를 사용하고 실제 실행으로 표시하지 않는다.

| target_id | 주소·포트 | 랩 버전 | 초기화 | 요청·시간 한도 | 검토 상태 |
|---|---|---|---|---|---|
| 미정 | 미정 | 미정 | 미정 | 미정 | 실대상 실행 불가 |

## 변경과 검증

공통 필수 계약·판정 책임·자동 실행 허용 범위를 바꾸거나 예외를 두는 PR에는 변경 이유, 영향받는 팀과 인터페이스, 호환성, 검증 결과를 적고 동아리장의 명시 승인을 받는다. 팀별 계획·구현·검토 방식은 각 팀이 정한다. 기존 프로토타입을 가져올 때는 필드 대응을 명시하고 자체 최종 판정이 Oracle과 중복되지 않게 한다. 오프라인 형식 검사는 검증/README.md를 따른다.
