# 팀원용 Codex 사용법 · 한 페이지

**작업 장소:** 공개 [Impes_RedHarness](https://github.com/rbtjd215/Impes_RedHarness). 각자 GitHub에서 Code → HTTPS 주소를 복사해 자신의 컴퓨터에 clone하고, Codex에서 그 폴더를 연다. 파일·브랜치·커밋·PR·기록은 공개된다. 키·쿠키·개인정보·내부 교안/운영 기록·원시 실행 출력은 넣지 않는다.

## 1. 각자 clone하고 Git 설정 확인

```powershell
git clone https://github.com/rbtjd215/Impes_RedHarness.git
cd Impes_RedHarness
git config --show-origin --get user.name
git config --show-origin --get user.email
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

값은 **본인이 로컬에서만 확인**하고 공개 채팅·PR·작업 기록에 붙여 넣지 않는다. 현재 값이 본인이 쓰려는 공개 작성자 정보와 다르면, 본인이 직접 확인한 값으로 이 저장소에서만 설정한다. Codex가 임의의 이름·이메일을 골라 설정하거나 다른 사람의 Git 설정을 바꾸게 하지 않는다.

```powershell
git config --local user.name "<본인이 선택한 공개 표시 이름>"
git config --local user.email "<본인 GitHub 설정에서 확인한 noreply 주소>"
```

GitHub Settings → Emails에서 **Keep my email addresses private**와 본인에게 제공된 noreply 주소를 확인한다. 주소 형식은 계정에 따라 다르므로 예시를 실제 값처럼 복사하지 않는다. [GitHub의 커밋 이메일 설정 안내](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address)를 따른다. Git author는 설정된 작성자, committer는 커밋을 생성·적용한 사람으로 기록된다. **둘 다 실제 편집자를 인증하지 않는다.** 각자 자기 변경을 커밋하고 SHA·PR로 범위를 확인한다.

## 2. Codex에서 파트 시작

Codex는 [역할표](개발_역할표.md), [공통 계약](PROJECT_SPEC.md), 해당 팀 안내, 최근 [작업별 기록](../91_개발작업기록/README.md), Git 상태를 읽고 **목표 / 지금 할 일 / 수정 경로 / 테스트 방법**을 짧게 보여 준다. 파트가 명확하면 바로 진행하고 `작업 시작`만으로 불분명할 때만 파트를 확인한다. 이름 확인은 필요하지 않으며 GitHub 권한 검증도 아니다.

```text
A파트 진행. 역할표·공통 계약·A팀 안내·최근 인계를 Git 상태와 대조해 목표, 수정 경로, mock 테스트를 알려줘.
```

```text
B파트 진행. XSS 팀 안내와 최근 인계를 읽고 지금 할 일, B팀 경로, 검증 방법을 알려줘.
```

`XSS 작업`, `Oracle 작업`, `Reporter 작업`도 사용할 수 있다. 현재 파트는 **A=인증우회, B=XSS, 별도 Oracle·Reporter**다.

## 3. 기능 요청·기록·종료

기능 요청에는 목표, 예상 입력·출력, 수정 범위, 완료 조건을 넣는다. 팀은 구현 방식과 내부 절차, 프로토타입 채택 여부를 정한다. B의 현재 mock 어댑터는 참고 예시이며 채택이나 실제 L0 완료가 아니다.

```text
A팀: 인증우회 mock 입력을 공통 계약 v1으로 처리해줘. A팀 경로만 수정하고 실행한 테스트와 막힌 점을 작업별 기록에 남겨줘.
```

```text
B팀: XSS 프로토타입을 검토해 채택 여부를 제안해줘. B 표기·공통 계약·Oracle 중복의 차이를 정리하고, 안전한 mock 검증만 실행해줘.
```

의미 있는 결과·실패 원인·범위 변경·인계 때 `03_프로젝트/91_개발작업기록/`의 **작업별 파일**을 갱신한다. 실제 Git 변경, 테스트 PASS/FAIL/SKIP, 막힘과 다음 행동만 간결하게 적는다. 개인 작업량 순위, 전체 대화, 숨은 추론, 비밀·개인정보는 수집하지 않는다. 허용 랩과 한도가 정해지기 전에는 mock만 쓴다.

```text
작업 종료. 실제 Git 변경과 실행한 테스트를 확인해 작업 기록, 짧은 인계, PR 설명을 작성해줘.
```

다음에는 `지난 B팀 인계를 Git 상태와 대조해 이어서 진행해줘`처럼 시작한다. Codex 앱을 닫은 뒤 자동 기록되지는 않는다.

## 4. 브랜치와 PR

최신 확인 가능한 기준에서 작업별 브랜치를 만들고 자기 변경만 커밋·push해 PR을 연다. 기존 변경이 있으면 보존하고 Codex와 안전한 분리 방법을 먼저 정한다. PR에는 `module-development.md` 템플릿을 사용한다. 팀 내부 검토·병합 순서는 팀이 정하며 **모든 PR에 짝 검토나 동아리장 승인을 요구하지 않는다.** 다른 팀에 영향이 있으면 당사자와 조율하고, 공통 필수 계약·최종 판정 책임·자동 실행 허용 범위의 변경/예외만 동아리장 명시 승인을 받는다.

GitHub PR의 Commits와 각 커밋 SHA에서 author/committer를 확인할 수 있다. 여러 사람의 커밋을 squash하면 상세 커밋 이력이 줄어드므로 작업별 작성 흐름을 확인할 필요가 있으면 PR Commits를 보고, 팀에서 일반 merge로 이력을 유지할지 정한다. `AGENTS.md`·`CODEOWNERS`는 폴더 권한을 강제하지 않는다.
