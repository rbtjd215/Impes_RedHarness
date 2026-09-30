---
team: common
task_id: workflow-improvements
status: local-verified
branch: codex/environment-readiness
base_commit: 7cc7d5643e7e75142b018dc0608821b86d9dbea8
---

# 공동 개발 흐름 보완 · 작업 기록

## 목표와 실제 상태

- 2026-10-01 현재 대화의 보완안 적용 승인에 따라 공통 개발 규칙·인계·검증을 보완한다. 일반 팀의 계획·프로토타입 도입·검토·병합은 팀 자율이다.
- 작업 기준: 위 HEAD, 원격 main f8db1504b6081ef3710c15daeef7d9723ec67844, 기존 [PR #2](https://github.com/rbtjd215/Impes_RedHarness/pull/2).
- 시작 전 git fetch --no-tags origin 성공·작업 브랜치 upstream 0/0 확인. 기존 관련 로컬 변경에서 이어가고 다른 작업 기록·기존 fixture를 보존했다.
- 상태: 로컬 작성/검증 완료, 미커밋·미업로드. 이번 변경의 커밋 작성 이력은 아직 없으며 향후 실제 author/committer·PR로 확인한다. PR 내용·main·GitHub 권한/보호를 변경하지 않았다.
- 종료 확인 SHA는 실제 Git·PR에서 확인한다. 자기 최종 SHA를 맞추기 위한 반복 commit은 하지 않는다.

## 실제 변경 파일

아래는 작업 시작 체크포인트의 파일 해시와 비교한 이번 변경·추가 경로다. 이전 작업에서 이미 미커밋이었던 관련 수정은 이어받되 과거 기록은 덮어쓰지 않는다.

- .github/PULL_REQUEST_TEMPLATE/module-development.md
- .github/workflows/offline-checks.yml
- 03_프로젝트/00_공통/CODEX_개발협업.md
- 03_프로젝트/00_공통/PROJECT_SPEC.md
- 03_프로젝트/00_공통/개발_역할표.md
- 03_프로젝트/00_공통/검증/README.md
- 03_프로젝트/00_공통/검증/check_contract.py
- 03_프로젝트/00_공통/검증/fixtures/complete/mock_fail.json
- 03_프로젝트/00_공통/검증/fixtures/complete/mock_not_run.json
- 03_프로젝트/00_공통/검증/fixtures/complete/mock_pass.json
- 03_프로젝트/00_공통/검증/fixtures/complete/mock_unknown.json
- 03_프로젝트/00_공통/검증/run_mock_pipeline.py
- 03_프로젝트/00_공통/검증/test_complete_run.py
- 03_프로젝트/00_공통/검증/test_mock_pipeline.py
- 03_프로젝트/00_공통/작업시작_최신확인.md
- 03_프로젝트/00_공통/팀원용_Codex_사용법.md
- 03_프로젝트/00_공통/환경준비_완료확인.md
- 03_프로젝트/01_Dispatcher/README.md
- 03_프로젝트/02_전문모듈_A/AGENTS.md
- 03_프로젝트/02_전문모듈_A/README.md
- 03_프로젝트/03_전문모듈_B/AGENTS.md
- 03_프로젝트/03_전문모듈_B/QA.md
- 03_프로젝트/03_전문모듈_B/README.md
- 03_프로젝트/03_전문모듈_B/mock_adapter.py
- 03_프로젝트/03_전문모듈_B/test_mock_adapter.py
- 03_프로젝트/04_Oracle_Reporter/AGENTS.md
- 03_프로젝트/04_Oracle_Reporter/README.md
- 03_프로젝트/05_통합/README.md
- 03_프로젝트/91_개발작업기록/2026-10-01_common_workflow-improvements.md
- 03_프로젝트/91_개발작업기록/README.md
- 03_프로젝트/91_개발작업기록/작업기록_템플릿.md
- 03_프로젝트/91_개발작업기록/환경준비_기록_템플릿.md
- 03_프로젝트/프로젝트_인덱스.md
- AGENTS.md
- README.md

### 변경 내용과 공통 영향

- 루트/팀 안내: 최신 확인 빈도, 자기 브랜치→PR→task-id의 인계 선택, 자기 미완료 변경 재사용과 필요한 격리. A=인증우회·B=XSS, Oracle/Reporter 한 팀과 단일 판정 책임 유지.
- 환경/사용법: 첫 준비·매일 작업·업로드 경로, 로컬 필수 검사와 작성자/업로드/PR 구분. 로컬 통과 뒤 안전한 계획서 읽기 검토, 접근 불가 원본의 이유·재첨부 안내.
- 협업/양식/PR: 필수 시작·기록·기존 변경 보존의 생략/완화를 포함한 공통 예외 표. 일반 팀 PR의 짝 검토/팀장 승인 의무 없음. 현재 확정 설계와 과거 아이디어 상태 구분.
- 계약/검증: 설명 문서 판 0.3·wire 1.0·complete-v1 분리. 기존 기본 검사 호환성을 유지하고 정확한 네 봉투·최소 행동/근거·Oracle 기준 연결·Reporter 상태/근거 보존 검사 추가.
- 합성 참고 예시: 네 상태 봉투 생성과 임시 파일 저장·재읽기·입력 불변성·저장 실패·변조·재시도 검증. 팀 모듈/네트워크/브라우저/모델 호출 없음. 기본 결과는 OS 임시 폴더에서 정리한다.
- B mock: 최소 공통 외피와 상호작용 검사 추가. 독립 프로토타입의 전체 도입이나 실제 B L0 완료를 결정하지 않는다.
- CI: RedHarness offline checks / offline-checks. 모든 PR와 main push에서 읽기 권한으로 기존 fixture·공통/B 검사·합성 재현 실행. 0개 테스트 발견은 실패. 아직 로컬 파일이며 서버 확인/필수 보호 적용 전이다.

## 실제 방법·아이디어와 결과

| 방법/아이디어 | 상태 | 실제 결과·선택 이유 |
|---|---|---|
| 규칙·학생 경로·계약 검증을 각 에이전트의 다른 파일에 배정 | 실험 채택 | 같은 파일 동시 수정 없이 통합·교차검토 |
| 로컬 준비와 작성자/업로드/PR 분리 | 선택·로컬 적용 | 인증 대기가 안전한 자료 읽기까지 막지 않도록 승인한 보완 반영 |
| 브랜치→PR→task-id·경로로 본인 인계 선택 | 선택·로컬 적용 | 같은 팀의 날짜 최신만으로 자기 작업을 식별할 수 없음 |
| 기본 부분 검사 + 별도 완성 프로필 | 실험 채택 | 기존 19회귀/2fixture 유지, 신규 완성/저장 검증 통과 |
| 항상 worktree를 요구 | 폐기 | 자기 미완료/깨끗한 작업에도 폴더 전환을 요구하는 조건 제거 |
| Reporter 저장 재시도 뒤 오류 정리 | 실험 채택 | 성공 뒤 이전 오류가 남는 문제 발견, 자신의 오류만 정리·입력/앞선 봉투 보존, 회귀 PASS |
| 훅·서버 보호를 즉시 필수로 적용 | 보류 | 학생 환경 신뢰·서버 CI·권한 확인 전, 설치/설정 변경 없음 |
| XSS 원본/runs 전체 자동 도입 | 미채택 | 팀이 공개 범위·계약/Oracle 대응·출처를 먼저 검토해야 함 |

## 실행한 검증

기준은 위 HEAD에서 이 기록의 로컬 변경을 적용한 상태다. Python 3.13.12, 오프라인 실행. 명령은 개발 저장소 루트 기준이다.

| 명령/확인 | 결과 | 실제 범위 |
|---|---|---|
| python -B 03_프로젝트/00_공통/검증/check_contract.py (기존 fixture 2경로) | PASS | 각 4봉투, 기존 부분 형식/단계 책임 |
| 같은 checker --complete (완성 fixture 4경로) | PASS | 각 4봉투, 완성 프로필 |
| python -B -m unittest discover -s 03_프로젝트/00_공통/검증 -p test_*.py | PASS | 42개, 기존 19개 포함 |
| python -B -m unittest discover -s 03_프로젝트/03_전문모듈_B -p test_*.py | PASS | 16개 |
| python -B 03_프로젝트/00_공통/검증/run_mock_pipeline.py --all | PASS | A 네 상태의 합성 구조·저장·재읽기 |
| 같은 pipeline --all --module B | PASS | B 네 상태의 합성 구조·저장·재읽기 |
| CI YAML 구조/모든 run 명령·0개 발견 방어 | PASS · 에이전트 로컬 확인 | 0개 발견은 예상 종료 코드 1, 서버 실행과 구분 |
| 개발 안내 20문서·118개 로컬 링크·19규칙 항목 | PASS · 정적 확인 | A/B 시작·담당 미확인·미완료 종료 후 재진입 포함 |
| git diff --check | PASS | 변경 공백 검사 |
| 실제 학생 새 Codex/설치/초대/push·merge 권한 | SKIP | 실제 학생 시범 전 |
| 실제 팀 모듈/랩/근거 진위/전체 하네스 | SKIP | 합성 참고 예시로 대체해 완료했다고 주장하지 않음 |
| GitHub 서버 CI/필수 체크/보호 | SKIP | 미업로드·설정 변경 미승인 |

예시의 최종 FAIL/UNKNOWN/NOT_RUN도 예상 상태를 재현하면 검사 PASS다. 형태와 연결 검사만으로 증거의 진위를 보장하지 않는다.

## 막힘과 짧은 인계

- 원격 main에는 새 로컬 보완이 없다. 기존 준비 규칙 PR #2도 아직 미병합이다. 새 clone에 전부 적용됐다고 말하지 않는다.
- 학생별 실제 배정/권한, 통합 대행, 실제 랩/기준 동결은 확인 필요. 기존 동아리장 통합 배정은 유지한다.
- 이어받을 곳: codex/environment-readiness·기존 PR #2·task-id workflow-improvements. 실제 dirty/diff와 이 기록을 대조한다.
- 다음: 사용자 로컬 검토 → 별도 업로드 지시 후 공개 변경 선별·fetch·commit/push·원격 SHA/파일/PR 확인 → 팀 방식에 따라 main 반영·서버 CI/필요 보호 설정 확인 → 학생 1명 준비/작업/기록/재진입 시범.
- 공개 파일에는 원시 runs/·비밀값·개인정보·전체 대화·숨은 추론을 넣지 않는다. 앱 종료 뒤 자동 기록은 보장하지 않는다.

## PR 설명 초안 · 아직 원격에 작성하지 않음

- 목적: 학생 진입/재시작 대기와 검증 범위 혼동을 줄이고 팀 자율을 유지한다.
- 변경: 시작/인계/준비 단계·공통 예외·아이디어 기록, complete-v1·합성 저장 예시·B 외피·오프라인 CI.
- 검증: 공통 42+B 16 PASS, 기존 fixture 2/완성 4 PASS, A/B 네 상태 저장 재현 PASS, 네 상황 정적 점검.
- 미확인: 실제 학생/팀 모듈/랩·근거 진위·서버 CI·보호. 이번 로컬 변경은 미커밋/미업로드.
- 상세 근거: 이 작업 기록 링크와 실제 Files changed를 사용한다.

## 최종 보존·범위 확인

작업 전 해시와 비교해 이번 변경/추가 35경로만 확인했다. 과거 작업 기록과 기존 fixture는 보존했고 HEAD·브랜치·빈 staging 상태를 유지했다. 신규 runs/·비밀 설정·비공개 교육 원본 복사 없음. 공개 경로/민감 리터럴 점검·git diff --check 통과. 서버 반영은 미수행이다.

## 게시 작업 재진입 · 2026-10-01

사용자가 한국어 교육자료를 승인하고 그에 기초한 영어 제작 완료 뒤 병합·Git 업로드·교육 사이트 게시를 명시 지시했다. 교육 안내가 읽는 공통 개발 규칙의 main 반영을 함께 마무리한다. 작업 전 fetch로 upstream 0/0·main f8db150 확인, 기존 PR #2 open/mergeable 확인. 현재 안내의 “매일”은 “환경 구축 후 작업”으로 명확화, 학생 시범은 환경 구축 때 확인할 항목으로 두며 준비 완료를 추정하지 않는다. 기존 repository-first 기록도 같은 관련 개발 작업 근거로 선별 포함한다. 서버 CI·병합·원격 SHA는 실제 결과에서 확인하고 GitHub 보호·학생 권한·모듈 완료는 추정하지 않는다.
