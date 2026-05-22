# 묶음 2 진입 전 처리 TODO

묶음 1 (콘텐츠 품질 라인 5개) 작업 중 결정된 사항으로, 
묶음 2 진입 시 반영 필요.

## 1. HTML Builder 구현 시 (09_html_builder.md)
- Format Architect의 `placeholder_locations.render_zone` 값 확인
- `render_zone == "outside_comment"` 인 placeholder만 치환 대상
- HTML 주석(`<!-- -->`) 내부에는 `{{VAR}}`가 있어도 절대 치환 금지
- 이유: 주석 내부 치환은 렌더링에 무영향이고 디버깅 시 혼란 유발

## 2. base_agent.py 확장
- Writer 호출 시 `{{TONE_REFERENCE}}` placeholder 치환 로직 추가
- 치환 소스: `docs/samples/content_voice_examples.md` 파일 전체 내용
- 다른 에이전트에도 동일 placeholder 메커니즘 확장 가능하게 일반화 권장

## 3. Content Newsroom 오케스트레이터
- iteration 카운터 관리 (1, 2, 3)
- 라운드 1: Writer → Fact-Checker → Devil's Advocate(iter=1) → Editor
- 라운드 2+: Writer 입력에 previous_draft, factcheck_log, critique, editor_instructions 추가
- 라운드 2+: Devil's Advocate 입력에 previous_critiques, editor_response 추가
- Editor decision == "approved" 또는 iteration == 3 도달 시 종료
- 종료 시점 final_content를 Format Architect에 전달

## 4. 진행률 추적
- 묶음 2 작업 항목: Trend Scout / Audience Analyst / Strategy Planner / HTML Builder
- 4개 prompt + 위 1-3번 구현 = 묶음 2 완료 조건
