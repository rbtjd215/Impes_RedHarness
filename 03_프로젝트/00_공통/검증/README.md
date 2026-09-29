# 공통 계약 mock 검증

이 폴더의 검사는 [PROJECT_SPEC.md](../PROJECT_SPEC.md)의 v1 봉투 필드, 상태값, 생산자 순서와 판정 책임을 확인한다. Python 표준 라이브러리만 사용하며 JSON 파일을 읽을 뿐 웹 요청이나 실제 모듈 실행을 하지 않는다.

저장소 루트에서 실행:

    python "03_프로젝트/00_공통/검증/check_contract.py" "03_프로젝트/00_공통/검증/fixtures/mock_a_pass.json" "03_프로젝트/00_공통/검증/fixtures/mock_b_unknown.json"
    python -m unittest discover -s "03_프로젝트/00_공통/검증" -p "test_*.py" -v

각 JSON은 단일 공통 봉투 또는 한 run의 봉투 배열이다. `next_action`은 문자열이며 빈 문자열도 형식상 허용한다. 배열에서는 Dispatcher → 선택된 A/B → Oracle → Reporter 순서를 확인한다. A/B와 Dispatcher는 최종 PASS/FAIL을 내리지 않고, Oracle만 최종 판정을 내린다. Oracle의 PASS/FAIL에는 증거 항목이 필요하다. Reporter는 같은 배열의 Oracle 상태와 증거를 그대로 보존해야 한다.

예시는 모두 가상의 로컬 mock 결과다. 검사는 증거가 실제 외부 성공/실패를 입증하는지, 대상 허용 목록을 지켰는지, 테스트를 실행했는지까지 증명하지 못한다. 이 항목은 짝의 실제 재실행·검토와 PR에서 확인한다. 단일 A/B 봉투는 작성 중 형식 점검용이며, Reporter 단독 봉투는 Oracle과의 일치를 확인할 수 없어서 거부한다.
