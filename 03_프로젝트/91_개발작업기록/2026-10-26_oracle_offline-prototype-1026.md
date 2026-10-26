# 개발 작업 기록 · offline-prototype-1026

<!-- redharness-worklog:v1 begin -->
```json
{
  "schema_version": 1,
  "team": "oracle",
  "task_id": "offline-prototype-1026",
  "kind": "development",
  "branch": "codex/oracle-offline-prototype-1026",
  "base_sha": "881680333826c0c9e0db1fb28ba9712369660d9e",
  "created_at": "2026-10-26T16:15:22+09:00",
  "captured_at": "2026-10-26T16:23:52+09:00",
  "snapshot": {
    "head": "881680333826c0c9e0db1fb28ba9712369660d9e",
    "changes": [
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/MODULE_SPEC.md"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/QA.md"
      },
      {
        "state": " M",
        "path": "03_프로젝트/04_Oracle_Reporter/README.md"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/offline_oracle.py"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/offline_reporter.py"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/run_offline.py"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/sample_io.json"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/test_oracle_reporter.py"
      },
      {
        "state": "??",
        "path": "03_프로젝트/04_Oracle_Reporter/판정규칙.md"
      },
      {
        "state": "??",
        "path": "03_프로젝트/91_개발작업기록/2026-10-26_oracle_module-spec-1026.md"
      },
      {
        "state": "??",
        "path": "03_프로젝트/91_개발작업기록/2026-10-26_oracle_setup_week03-readiness-1026.md"
      }
    ],
    "omitted_path_count": 0,
    "remote_state": "unverified",
    "tests": "unverified"
  }
}
```
<!-- redharness-worklog:v1 end -->

- 날짜/체크포인트: 2026-10-26, Asia/Seoul. 구현 전 최신 확인, 구현 후 검사.
- 팀/상태: Oracle·Reporter; 로컬 합성 프로토타입 구현·검사 완료. 실랩·전체 통합 미완료.
- task-id / 브랜치: `offline-prototype-1026` / `codex/oracle-offline-prototype-1026`.
- 기준 SHA: `881680333826c0c9e0db1fb28ba9712369660d9e`.
- fetch origin 성공; 명령 한 번의 safe.directory 예외 사용, 영구 Git 설정 변경 없음. HEAD와 origin/main 0/0. 새 로컬 브랜치 upstream 없음.
- 기준 자료: 루트 AGENTS.md·README.md, 인덱스, 역할표, PROJECT_SPEC.md, CODEX_개발협업.md, 최신확인·환경준비·검증 안내와 팀 AGENTS.md·README.md. 자체 MODULE_SPEC.md와 직전 spec/setup 기록을 대조했다. 공통 check_contract 및 mock 저장 예시를 읽었다.
- 열린 PR: GitHub connector search_prs에서 해당 저장소 open 결과 0개. 같은 경로 PR 겹침 발견 없음.
- 이전 setup/spec 미커밋 기록을 보존한 별도 개발 브랜치. commit/stash/삭제하지 않았다.
- 사용자 지시: 구현 후 한국어·영어 보고서; 현재는 로컬 작업만, 업로드 안내 제공. commit/push/PR 미수행, author 값 미확인·미수집.
- 목표: 판정 규칙·fixture·Oracle/Reporter 구현·테스트·QA를 끝낸 뒤 확인한 사실로 보고서 작성.

## 실제 변경

| 경로 | 실제 내용 | 계약 영향 |
|---|---|---|
| `04_Oracle_Reporter/offline_oracle.py` | 별도 합성 criterion/check를 비교하는 decide 함수, 잘못된 입력 InputError, v1/complete-v1 검증 연계 | 공통 의미 유지; 네트워크 없음 |
| `04_Oracle_Reporter/offline_reporter.py` | 세 봉투에서 Reporter 생성, 새 파일 저장·fsync·재읽기, 입력 불변·기존 파일 보존·별도 storage_error | status/evidence 그대로 유지 |
| `04_Oracle_Reporter/run_offline.py` | 두 모듈 라벨의 fixture 확장·실제 합성 판정/저장/재읽기 후 임시 폴더 정리 | 실제 A/B 호출하지 않음 |
| `04_Oracle_Reporter/sample_io.json` | 9개 compact 입력/기대 상태 fixture | 합성 데이터만 |
| `04_Oracle_Reporter/test_oracle_reporter.py` | 21개 unittest 메서드 및 A/B·fixture subtest | 기존 oracle 등록 그룹에서 자동 실행 |
| `04_Oracle_Reporter/판정규칙.md`, `QA.md` | 실제 인자·상태·저장 규칙, 실행 결과, 사례 대응, 한계 | 공통 계약 변경 없음 |
| `04_Oracle_Reporter/MODULE_SPEC.md`, `README.md` | 이전 초안을 구현 현황에 맞춰 갱신; 로컬 재현 안내 | 실제 랩 미검증 유지 |
| 이 작업 기록 | 기준·시도·검사·인계 | 자기 기록 |

위 경로는 `03_프로젝트/` 아래다. 공통 검증기·registry·다른 팀 소스는 수정하지 않았다. 이전 setup/spec 기록은 과거 시점의 사실로 보존했다. 자동 snapshot에 보이는 파일은 stage 목록이나 작성자 인증이 아니다.

## 실제 시도와 아이디어

| 항목 | 상태 | 확인 근거와 남은 범위 |
|---|---|---|
| 독립 합성 criterion/check 함수 | 실험 채택 | 모델/A/B claim을 믿지 않고 서로 다른 success/failure 값과 비교; 입력 check는 테스트 호출자가 제공하므로 실제 근거 출처 인증 기능은 아님 |
| independent_check | 실험 채택 | A/B NOT_RUN 뒤 Oracle PASS와 FAIL을 모두 테스트; 동일 기준 verify/evidence 연결 |
| Reporter 저장 | 실험 채택 | 기존 파일을 덮어쓰지 않는 exclusive create와 재읽기; 원자성·실패 복구는 미구현, 일부 파일이 남을 수 있음 |
| 공통 mock 예시 | 참고 | 계약 검증·상태 보존 원칙을 참고; 실제 Oracle/Reporter는 별도 함수와 테스트로 구현 |
| 실제 랩/실제 A/B·통합 | 보류 | 허용 대상·버전·초기화·한도와 팀 간 실제 기준/호출 연결이 미확정 |

## 검증

2026-10-26 Asia/Seoul, 위 기준 SHA + 현재 미커밋 구현. 런타임은 번들 Python 3.12.14의 전체 경로이며 아래 python 표기는 그 실행 파일을 뜻한다. PATH의 python/py 부재를 숨기지 않는다.

| 실제 명령/방법 | 결과 | 범위 |
|---|---|---|
| `python -B tools/run_checks.py --group oracle` | PASS exit 0 | 첫 focused 실행 20 tests; 이후 충돌 관찰 테스트 추가 |
| `python -B tools/run_checks.py` | PASS exit 0 | 최종 common 42, b 16, tools 33, a 15, oracle 21 = 127 tests; failures/errors/skips 모두 0; reference 세 개 PASS |
| `python -B 03_프로젝트/04_Oracle_Reporter/run_offline.py` | PASS exit 0 | 9 fixture × A/B = 18 실행, 기대 상태와 written_and_verified 모두 일치 |
| OR-01~09 / RP-01~03 / CT-01 | PASS | QA case mapping 참조. 미실행을 PASS로 표시하지 않음. write/read/변조 오류는 unittest에서 주입 |
| 코드·문서 수동 검토 | PASS | 상태 책임, 증거 연결, 입력 복사, 안전한 오류, 기존 파일 보존; 실제 근거 인증/내구성 미구현 명시 |
| 실제 랩·Dispatcher/전체 통합 | SKIP | 랩 허용 목록 미정; runner의 dispatcher/integration NOT_IMPLEMENTED |
| 원격 CI·업로드·PR | SKIP | 사용자가 현재 로컬 작업만 선택 |

테스트 PASS와 제품 PASS/FAIL/UNKNOWN/NOT_RUN은 다르다. 파일 저장 성공도 Oracle 판정과 별개다. 구조 검증은 증거 진위나 개인정보 부재를 증명하지 않는다.

## 막힘과 인계

- 구현된 범위: synthetic-only Oracle/Reporter. 현재 필수 로컬 검사는 PASS다.
- 다음 개발: A/B 팀과 실제 기준·관찰 어댑터, Dispatcher/통합과 호출 방식을 조율한다. 실랩은 허용 범위 확정 후 별도 검사한다.
- 한국어·영어 학생 보고서는 지정된 저장소 밖 폴더에 별도 작성한다. 보고서는 공개 Git 파일 범위가 아니다. 보고서 작성·렌더 검토는 코드 테스트 이후 진행한다.
- GitHub로 보여주려면 사용자의 별도 업로드 지시·작성자 본인 확인 후 정확한 파일 commit/push/PR과 원격 검증이 필요하다. 현재는 미커밋 로컬 코드이므로 새 clone에는 없다.
- 재진입: `codex/oracle-offline-prototype-1026`, task-id `offline-prototype-1026`, PR 없음. 이전 setup/spec 기록 보존.

## 보고서·종료 체크포인트

- 구현과 테스트 이후 지정된 저장소 밖 제출 폴더에 한국어·영어 DOCX를 각각 작성했다. template-id, submission-report 상태와 공통 일곱 H2 제목·순서를 유지했다. 각 2페이지다.
- 표준 render_docx.py는 LibreOffice 부재로 실행 불가였다. 로컬 ONLYOFFICE 변환기의 폰트 캐시 설정을 지정해 PDF로 변환하고 번들 Poppler로 PNG를 생성해 네 페이지 모두 확인했다. 중간 PDF/이미지는 제출 파일에 포함하지 않았다.
- 최종 DOCX 두 개와 러시아어 로컬 시연/GitHub 공유 안내를 저장소 밖에 복사하고 SHA256 일치를 확인했다. 보고서에 개인 홈 경로·개인 Git 값·원시 출력·대화 링크를 넣지 않았다.
- 보고서는 구현 범위의 완료와 실제 랩/통합·공유의 미완료를 구분한다. 안내는 기존 clone에서 시연하는 방법과 향후 별도 위임 후 push/PR 방법을 구분한다.
- 종료 시 코드 변경은 최종 127-test runner 이후 없으며 이후 수정은 문서·보고서뿐이다. 실제 모듈/실랩·원격 CI 미실행 상태는 유지한다.

## Draft PR 준비 체크포인트

- 사용자가 이번 공개 안전 파일의 commit/push와 검토용 Draft PR 생성을 명시 요청했다. main 병합은 수행하지 않는다. 이전 로컬 전용 선택은 이번 공유 범위에서 갱신됐다.
- 공유 전 fetch 성공, HEAD/origin/main은 기준 SHA와 동일하고 0/0. open PR 조회 결과 0개다.
- 등록 runner를 실제 재실행했다: common 42, b 16, tools 33, a 15, oracle 21 = 127 tests PASS, 실패/오류/SKIP 0, reference 3개 PASS, exit 0. 팀 CLI도 실제 재실행해 18회 PASS, exit 0.
- 공개 범위: 팀 폴더의 명세·규칙·코드·fixture·테스트·QA·README와 이번 채팅의 setup/spec/prototype 기록. 저장소 밖 학생 보고서는 제외한다.
- Draft PR 설명을 준비했다. author 설정의 사용자 확인은 받았으나 실제 clone에서 이름 누락 및 noreply 형식 불일치를 확인해, 정확한 로컬 설정 해결을 요청했다. 실제 값은 기록하지 않는다.
- 이 체크포인트 시점: commit/push/PR 미실행. 작성자 설정이 해결되면 같은 브랜치에서 정확한 파일 commit/push와 원격 검증 후 Draft PR을 만든다.

## 작성자 확인과 업로드 착수

- 사용자가 확인한 공개 표시 이름과 정확한 GitHub noreply 주소를 제공했다. 해당 값을 저장소 로컬에만 적용·일치 확인했다. 값은 공개 기록에 쓰지 않는다. 전역 설정은 변경하지 않았다.
- 업로드 직전 fetch를 다시 수행했고 HEAD/origin/main 0/0, 열린 PR 0개를 확인했다. 같은 작업 브랜치와 task-id를 유지한다.
- 앞선 공유 체크포인트의 127 tests 및 18개 합성 재현 결과를 사용한다. 그 뒤 변경은 문서·기록뿐이고 코드·fixture·런타임은 동일하다.
- 이 기록을 포함한 검토된 12개 파일만 commit/push하고 검토용 Draft PR을 만든다. 생성·원격 확인 결과는 후속 체크포인트 또는 완료 보고에서 사실로 확인한다. main 병합은 하지 않는다.
