# Oracle·Reporter

## 역할

Oracle는 A/B가 반환한 v1 봉투와 외부 증거로 **최종 상태를 한 번 판정**한다. Reporter는 그 결과와 입력·행동·관찰·근거·오류를 바꾸지 않고 기록한다. 이 문서는 작업 경계이며 실제 판정 코드·실행 검증 완료를 주장하지 않는다.

`Oracle 작업` 또는 `Reporter 작업`으로 시작하면 [팀 규칙](AGENTS.md), [공통 계약](../00_공통/PROJECT_SPEC.md), [공개 역할표](../00_공통/개발_역할표.md), [협업 규칙](../00_공통/CODEX_개발협업.md), 최근 [작업 기록](../91_개발작업기록/README.md)과 Git 상태를 확인한다.

## 공통 계약과 상태

공통 v1 봉투의 `contract_version`, `run_id`, `target_id`, `selected_module`, `producer`, `observation`, `actions`, `status`, `evidence`, `error`, `next_action`을 사용한다. A/B는 분야별 근거 기준을 제안할 수 있지만 최종 `status`는 Oracle에만 있다.

| 상태 | 최종 사용 조건 |
|---|---|
| `PASS` | 외부에서 확인 가능한 성공 증거가 있다. |
| `FAIL` | 실제로 실행했고 실패 근거가 있다. |
| `UNKNOWN` | 실행했으나 판정 근거가 부족하다. |
| `NOT_RUN` | 실제 실행이 없다. |

Reporter는 같은 `run_id`·`selected_module`의 Oracle 상태와 근거, 실행 조건을 보존한다. 저장 실패는 별도 오류로 드러내고 상태를 임의로 변경하지 않는다. 제품 상태 `NOT_RUN`과 테스트 상태 `SKIP`은 다르다.

## 이 폴더에서 발전시킬 파일

- `AGENTS.md`: Codex 작업 경계
- `MODULE_SPEC.md`: Oracle/Reporter 입출력과 책임
- `판정규칙.md`: 외부 근거와 분야별 규칙 검토 기준
- `sample_io.json`: 네 상태의 mock 사례
- `QA.md`: 재실행 명령·입력·실제 결과·근거

아직 없는 파일은 해당 작업 시작 때 만든다. 네 상태와 증거 없는 성공 주장, Reporter 저장 실패를 mock으로 검증하고, 실제 랩 검사는 허용 목록·버전·초기화가 정해진 뒤 수행한다. 미실행 검사는 `SKIP`과 이유를 [작업 기록](../91_개발작업기록/README.md)에 남긴다. 짝의 교차 검토 후 PR로 인계한다.
