# A 인증우회 모듈 · 첫 오프라인 mock 명세

이 문서는 제공된 Authentication Specialist 계획서에서 2FA 단계 확인을 가장 작은 실행 단위로 선택한 현재 A 모듈 설계를 기록한다. 실제 랩·계정·네트워크를 사용한 결과가 아니다.

## 책임

`mock_adapter.analyze_mock` 함수는 Dispatcher가 A로 선택한 v1 봉투의 **합성 2FA 상태와 보호 자원 관찰**을 읽고 A v1 봉투를 반환한다.

- 요청이 수행되었으면 Oracle 판정 전 상태인 `UNKNOWN`을 반환한다.
- 요청이 수행되지 않았거나 상위 오류가 있으면 `NOT_RUN`을 반환한다.
- 1차 인증 완료, 2FA 미완료, 보호 자원 접근 관찰이 모두 있을 때 `AUTH-2FA-ENFORCEMENT` 기준의 **후보 근거**를 Oracle에 넘긴다.
- A는 `PASS`나 `FAIL`을 만들지 않으며, 근거 후보의 최종 진위를 판정하지 않는다.

## 합성 입력

Dispatcher 봉투의 `observation` 객체에 다음 mock 필드를 사용한다.

| 필드 | 의미 |
|---|---|
| `execution_mode: offline_mock` | 실대상 실행이 아닌 합성 관찰 |
| `auth_state.primary_authenticated` | 1차 인증 완료 여부 |
| `auth_state.second_factor_verified` | 2FA 완료 여부 |
| `protected_resource.request_attempted` | 보호 자원 확인 행동 수행 여부 |
| `protected_resource.access_result` | 합성 관찰 `granted`, `denied`, `indeterminate` |
| `http_status`, `redirected_to_second_factor` | 선택 구조 필드 |

모든 필드는 합성 데이터에만 사용한다. 어댑터는 원시 응답·세션·쿠키를 입력 계약으로 채택하거나 출력에 복사하지 않는다.

## 현재 검증 범위

```text
python -B tools/run_checks.py --group a
python -B tools/run_checks.py
```

단위 검사는 후보 생성·비후보·미실행·상위 오류·입력 거부·입력 불변·공통 부분/완성 계약 호환을 확인한다. 이 통과는 실제 2FA 우회, 근거의 진위, Oracle·Reporter 구현, 전체 L1 완료를 의미하지 않는다.
