# B · XSS 오프라인 mock 어댑터 검증

## 범위와 출처

- `mock_adapter.py`는 메모리의 **합성** Dispatcher v1 봉투만 읽고 B v1 봉투를 반환한다. 네트워크 요청, 브라우저 실행, JavaScript 실행, 실제 랩 접속은 없다.
- 팀이 제공한 독립 XSS 프로토타입의 `contexts.py`·`sinks.py`에서 **정적 반사 위치와 DOM 소스→싱크 후보를 구분하는 아이디어**만 검토했다. 코드는 새로 작성했고 프로토타입의 계약·Oracle·Reporter·페이로드·설정·원시 로그·sample I/O는 복사하지 않았다. 기존 프로토타입의 라이선스와 공개 가능 범위는 별도 확인이 필요하다.
- `response_html`+짧은 무해 마커가 있으면 HTML text/attribute/comment/raw text에서 **반사 후보**를 찾는다. `script_source`가 있으면 소스와 sink가 같은 문장 또는 순서상 한 변수 대입으로 이어지는 **DOM 후보**만 찾는다. 결과에는 원문 HTML·JavaScript를 넣지 않는다.
- `status`는 검사 자체가 실행되면 `UNKNOWN`, 입력이나 상위 오류로 검사를 안 했으면 `NOT_RUN`이다. 후보는 성공 증거가 아니며 `PASS`/`FAIL`은 반환하지 않는다. 최종 판정은 공통 Oracle의 책임이다.

## 실행

저장소 루트에서:

```powershell
python -B -m unittest discover -s "03_프로젝트/03_전문모듈_B" -p "test_*.py" -v
```

## 확인 결과와 남은 검증

| 항목 | 결과 |
|---|---|
| 합성 반사 text·attribute·comment 후보, marker 부재 | `PASS` · B 단위 테스트 포함 |
| DOM 직접/한 변수 흐름과 무관한 source·sink | `PASS` · B 단위 테스트 포함 |
| v1 필수 필드·B 선택·중간 상태, 상위 오류 시 미실행·잘못된 상태 타입·공통 계약 연결 | `PASS` · B 단위 테스트 포함 |
| B 단위 테스트 전체 / 공통 계약 테스트 전체 | `PASS` · 15건 / 19건 |
| 생성한 Dispatcher→B 봉투를 공통 `validate_document`로 검사 | `PASS` · 합성 반사 입력 1건 |
| 실제 XSS 프로토타입 이식·L0 동작·로컬 랩·브라우저 증거 | `SKIP` · 원본 이식 및 허용 랩/기준 환경 미확정 |
| 짝의 같은 입력 재실행·검토 | `SKIP` · 실제 검토 기록 대기 |

이 검사는 HTML/JavaScript 파서 전체, sanitizer 의미, 런타임 DOM 변경, 브라우저 실행 증거를 다루지 않는다. 주석·문자열 속 코드 같은 정적 오탐 또는 복잡한 흐름의 누락이 가능하다. 공개 작업 기록·PR에도 개인 정보, 키, 쿠키, 원시 응답을 넣지 않는다.
