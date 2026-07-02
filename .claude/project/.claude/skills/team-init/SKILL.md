---
name: team-init
description: 새 팀 워크스페이스를 `teams/<팀명>/` 아래에 표준 구조로 생성한다. 팀별 CLAUDE.md, 기획 노트, 프로토타입 폴더, README를 만든다. 5팀 운영을 일관되게 시작하는 용도.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# /team-init

새 팀을 시작할 때 표준 폴더 구조를 만든다.

## 입력

사용자가 `/team-init team-1`처럼 팀명을 인자로 줄 수 있다. 없으면 `AskUserQuestion`으로:
1. 팀명 (예: `team-1`, `team-pothole`)
2. 세부 과제 (도로 파손 라벨링 / CCTV 이상행동 / 시설물 점검 / 공공데이터 QA / 하이브리드 RAG 지식검색 / 기타)
3. 팀원 4명 닉네임(선택)

## 동작 순서

1. `teams/<팀명>/` 이미 존재하면 **덮어쓰지 말고 멈춘다** (사용자에게 알림).
2. 아래 디렉터리 생성:
   ```
   teams/<팀명>/
   ├── CLAUDE.md          # 팀별 컨텍스트 (세부 과제, 멤버, 진행 상황)
   ├── README.md          # 팀 소개 + 시연 계획
   ├── notes/             # 회의록, 리서치 메모
   ├── prototype/         # 첫 프로토타입(나중에 prototypes/로 승격)
   └── data/              # 샘플 데이터 (대용량은 금지)
   ```
3. `CLAUDE.md`에 다음을 채워 넣는다:
   ```markdown
   # <팀명> 작업 컨텍스트

   ## 세부 과제
   <선택한 과제>

   ## 팀원
   - <닉1>, <닉2>, <닉3>, <닉4>

   ## 진행 현황
   - [ ] 문제 정의
   - [ ] 후보 모델 선정 (vlm-researcher 호출)
   - [ ] 데이터 확보 (public-data-finder 호출)
   - [ ] 첫 프로토타입 (prototype-builder 호출)
   - [ ] 시연 시나리오 정리
   - [ ] 기획 보고서 (planning-writer 호출)
   - [ ] 발표자료

   ## 시연 시나리오 (잠정)
   - 예: "포트홀 영역을 빨갛게 표시해줘"

   ## 관련 디렉터리
   - prototype/  ← 첫 데모
   - notes/      ← 리서치 메모
   ```
4. `README.md`에는 팀 소개 한 줄 + "실행 방법: `uv run python prototype/app.py`"만 적는다.
5. `git status`로 새로 생긴 파일들을 사용자에게 보여준다.
6. 다음 행동 제안: "이제 `vlm-researcher`로 모델 후보를 찾아볼까요, 아니면 바로 `prototype-builder`로 MOCK 데모부터 만들까요?"

## 하지 말 것

- 임의로 git commit 하지 말 것. 파일만 만들고 멈춘다.
- 팀별 가상환경을 만들지 말 것. 프로젝트 루트의 `.venv` 공용.
- 비밀번호/API 키를 자동 채우지 말 것.
