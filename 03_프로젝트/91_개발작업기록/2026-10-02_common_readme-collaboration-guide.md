# 개발 작업 기록 · readme-collaboration-guide

<!-- redharness-worklog:v1 begin -->
```json
{
  "schema_version": 1,
  "team": "common",
  "task_id": "readme-collaboration-guide",
  "kind": "development",
  "branch": "codex/readme-collaboration-guide",
  "base_sha": "f9dd2abdeb1569cb69721ecc7fb7c220924ac027",
  "created_at": "2026-10-02T01:30:09+09:00",
  "captured_at": "2026-10-02T01:30:09+09:00",
  "snapshot": {
    "head": "f9dd2abdeb1569cb69721ecc7fb7c220924ac027",
    "changes": [
      {
        "state": "??",
        "path": "03_프로젝트/00_공통/공동_개발_사용_안내.md"
      },
      {
        "state": " M",
        "path": "03_프로젝트/프로젝트_인덱스.md"
      },
      {
        "state": " M",
        "path": "README.md"
      }
    ],
    "omitted_path_count": 0,
    "remote_state": "unverified",
    "tests": "unverified"
  }
}
```
<!-- redharness-worklog:v1 end -->

- 체크포인트: 2026-10-02, common 문서 작업 로컬 검증 완료.
- task-id / 브랜치: readme-collaboration-guide / codex/readme-collaboration-guide.
- 기준 SHA: f9dd2abdeb1569cb69721ecc7fb7c220924ac027. fetch 후 main 차이 없음, 열린 PR 없음 확인.
- 적용 문서: AGENTS.md, 작업시작_최신확인, 프로젝트 인덱스, 개발 역할표, PROJECT_SPEC, CODEX_개발협업, 검증 README, 개발 작업 기록 README.
- 공유 상태: 이 체크포인트는 로컬 기록이다. 최종 업로드와 main 반영은 PR·Git 원격에서 확인한다.
- 목표: 사용자 승인 문안으로 README를 프로젝트 소개·구조·개발 현황 중심으로 정리하고 기존 공동 개발 설명을 별도 안내로 보존한다.

## 실제 변경

| 파일 | 변경 내용 | 계약 영향 |
|---|---|---|
| README.md | 프로젝트 소개·구조·개발 현황과 하단 안내 링크 | 없음 |
| 00_공통/공동_개발_사용_안내.md | 기존 README 운영 설명·10개 미완료 체크 항목 보존, 상대 링크 조정 | 기존 원본 문서가 기준 |
| 프로젝트_인덱스.md | 세 동선 참조 링크만 새 안내로 이동 | 없음 |

## 선택과 검증

사용자가 2026-10-02 문안과 배치안을 최종 승인했다. 새 안내는 기존 공통 폴더에 두고 README 하단과 교육자료에서 연결한다. 소개 화면에서 설명이 길게 노출되는 문제를 해결하며 기존 기술 원본은 유지한다.

| 확인 | 결과 | 범위 |
|---|---|---|
| 승인 문안·기존 본문 대조 | PASS | README·안내 승인 파일 일치, 기존 설명과 10개 미완료 체크 항목 보존 |
| 안내·소개 상대 링크 | PASS | 18개 대상 존재 |
| 기존 파일 SHA256 | PASS | README·인덱스를 제외한 기존 추적 파일 50개 동일; AGENTS·계약·검증·도구 포함 |
| python -B tools/run_checks.py | PASS | common42+b16+tools33=91개, 합성 참고3개; 선택 팀 a/oracle/dispatcher/integration 미구현 |
| 실제 모듈·로컬 랩·학생 환경 | SKIP | 이번 작업은 문서·연결 변경이며 해당 실행을 하지 않음 |

## 인계

기술 규칙·계약·검증 절차·기존 사용 매뉴얼·양식은 변경하지 않았다. 다음은 전용 PR의 필수 offline-checks 확인과 승인 범위 main 반영이다. 교육 링크는 새 안내가 main에서 공개된 뒤 전환한다. 최종 업로드는 Git SHA·PR 이력으로 확인하며 기록의 자기 최종 SHA를 맞추는 반복 커밋은 하지 않는다.
