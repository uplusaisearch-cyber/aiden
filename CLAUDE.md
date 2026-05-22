# AIDEN Project Guidelines

## Project Overview
LG U+ 사내 AI 콘텐츠 자동화 대회 출품작.
9개 AI 에이전트가 뉴스룸처럼 토론하며 LG U+ 플러스탭 콘텐츠를 자동 생성하는 시스템.

## Core Design Principles
1. **이관성/확장성 우선**: GitHub repo 소유권 이전, 다른 팀 인계, 다른 브랜드 적용 모두 쉬워야 함
2. **비개발자 친화**: system prompt와 설정값은 코드가 아닌 markdown/yaml로 분리
3. **하드코딩 금지**: 모든 환경변수/설정은 .env와 config/*.yaml로 중앙화
4. **한국어 처리**: 모든 파일 UTF-8 인코딩
5. **이관 가능성을 항상 고려**: 작성하는 모든 코드/문서가 다른 사람이 받아도 5분 내 이해 가능해야 함

## Architecture
- Backend: Python 3.11+ / FastAPI / Gemini SDK (메인) / OpenAI SDK / Anthropic SDK
- Frontend: Next.js 14 + Tailwind + shadcn/ui (Phase 4)
- Streaming: Server-Sent Events (SSE)
- Deploy: Vercel (Frontend) + Railway (Backend)

## File Structure Rules
- system prompts → backend/agents/prompts/*.md (텍스트 편집만으로 튜닝 가능)
- 설정값 → config/*.yaml (코드 수정 없이 변경 가능)
- 브랜드/플랫폼 정보 → config/brand.yaml, config/platform.yaml
- API 키 → .env (절대 git 커밋 금지)

## Coding Conventions
- Python: ruff + black 호환 스타일
- 한국어 주석 OK
- 함수/변수명은 영문, 사용자 대면 문자열은 한국어
- 모든 파일 열 때 encoding='utf-8' 명시
- LLM 호출은 반드시 core/llm_clients.py를 통해서만

## Git Workflow
- main 브랜치에 직접 커밋 OK (개인 프로젝트 단계)
- 의미 있는 작업 단위마다 커밋
- 커밋 메시지는 한국어/영문 모두 가능, 명확하게

## Cost Awareness
- Gemini 호출 시 Pro/Flash 구분 확실히 (config/agents.yaml 따름)
- Grounding은 명시된 에이전트만 (Trend Scout, Fact-Checker)
- 개발/테스트 시 불필요한 반복 호출 자제

## DO NOT
- API 키를 코드에 하드코딩하지 말 것
- .env를 git에 커밋하지 말 것
- system prompt를 코드 안에 박지 말 것 (반드시 .md 파일로)
- 브랜드 정보 (LG U+, 플러스탭)를 코드에 하드코딩하지 말 것 (반드시 config/brand.yaml)

## Progress Tracking Rules

모든 작업 세션에서 반드시:

1. **세션 시작 시**:
   PROGRESS.md를 가장 먼저 읽어 현재 단계와 미완료 항목 파악,
   사용자에게 "현재 진행 상황: Phase X, 미완료 N개" 보고

2. **작업 진행 중**:
   - 체크리스트 항목 완료 시 즉시 [ ]를 [x]로 변경
   - 중요한 결정사항은 "의사결정 로그"에 날짜와 함께 추가
   - 발견된 이슈는 "이슈/리스크"에 기록

3. **세션 종료 시 또는 보고 요청 시**:
   - PROGRESS.md "마지막 업데이트" 일시 갱신
   - 전체 진행률 % 재계산
   - 다음 형식으로 사용자에게 보고:
     ## 📊 진행 보고
     - 이번 세션 완료: [항목들]
     - 전체 진행률: XX% (Phase X.X)
     - 다음 추천 액션: [구체적 다음 단계]
     - 이슈: [있다면]

4. **Phase 완료 시**:
   - 해당 Phase 모든 항목 [x] 확인
   - Git 커밋: "Phase X 완료: [한 줄 요약]"
   - 다음 Phase 진입 여부 확인
