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

## 5. Format Architect → HTML Builder 핸드오프 정의

### 5-1. placeholder_locations.location 형식
- 현재 dotted notation 사용 (예: "section.hero.img-figure")
- HTML Builder가 이걸 어떻게 해석할지(CSS selector? 가상 경로? AST?) 묶음 2에서 정의
- 권장: AIDEN 자체 mini-DSL 정의 후 HTML Builder가 파싱

### 5-2. layout_hints.image_descriptions 용도
- alt text용? 이미지 생성 프롬프트용? placeholder URL 캡션용?
- 묶음 2 HTML Builder 또는 이후 이미지 생성 에이전트에서 어떻게 소비할지 정의

### 5-3. placement: between_sections 모호성
- "어느 섹션 사이"인지 명시 필요
- 권장: between_section_N_and_N+1 형식 또는 LLM이 인덱스 명시

### 5-4. CALCULATOR.formula 안전성
- 문자열 수식 → JS eval 위험
- mathjs 같은 안전 표현식 파서 도입 또는 화이트리스트 연산자(+, -, *, /, 괄호)만 허용
- HTML Builder 또는 Frontend 렌더링 단계에서 처리

### 5-5. Google Search Grounding 호출 단위
- Fact-Checker가 claim 1개당 1회 호출인지, 묶어서 호출인지 결정 필요
- 비용·속도 트레이드오프
- Content Newsroom 오케스트레이터 또는 base_agent에서 분기 처리

> **상태**: 위 5건 모두 2026-05-23 묶음 2 Step 1 작업 중 확정. HTML Builder prompt + Trend Scout prompt에 반영 완료. 본 섹션은 이력 보존 목적으로 유지.

## 6. base_agent 치환 화이트리스트 강제 (이슈/리스크에서 이관)

- `{{VAR}}` 치환은 Format Architect의 `placeholder_locations` 화이트리스트 기반
- 매핑 외 `{{VAR}}` 패턴은 무시 (= 주석 안에 있는 변수 자동 보호)
- type_a/b.html 헤더 주석의 문서화용 `{{VAR}}` 안전하게 보존됨
- 묶음 2 base_agent.py 구현 시 치환 함수에 명시

## 7. Step 2/3 작업 진입 전 결정·구현 필요 사항 (묶음 2 Step 1 검토에서 도출)

### 7-1. 외부 CDN URL config화 (Step 2 검토)
- mathjs (12.4.2), swiper (v11) 등 CDN URL이 prompt에 하드코딩됨
- 보안 패치·버전 업데이트 시 prompt 재편집 필요
- 옵션 A: 현행 유지 (단순)
- 옵션 B: `backend/config/cdn_urls.json` 분리 → base_agent가 prompt에 주입 → prompt는 키만 참조
- Step 2 base_agent 일반화 시 검토

> **상태 (2026-05-23)**: cdn_urls.json 분리 생성 완료. 다만 prompt에서 직접 참조는 아직 안 함 (현행 prompt에 CDN URL 하드코딩 유지). Step 3 또는 별도 패치에서 prompt 참조 방식 결정 후 적용 예정.

### 7-2. 실제 이미지 URL 주입 시점 (Step 3 검토)
- HTML Builder는 입력에 실제 이미지 URL 없음
- 현재 default: placeholder URL `https://image.lguplus.com/static/{slug}.jpg` 사용
- 옵션 A: 사람이 어드민에서 채움 (default, MVP)
- 옵션 B: 별도 이미지 생성 에이전트가 layout_hints.image_descriptions로 생성 → 오케스트레이터가 final_content에 주입 → HTML Builder가 받음
- Step 3 오케스트레이터 설계 시 결정

> **상태 (2026-05-23)**: MVP 결정 - placeholder URL 그대로 유지. 별도 이미지 생성 에이전트는 묶음 3 또는 v2에서 검토. HTML Builder가 default URL 패턴 사용.

### 7-3. 에이전트 간 데이터 흐름 명세 (Step 3 필수)
- 각 prompt의 입출력 스키마는 정의되었으나, 오케스트레이터가 어느 필드를 어느 에이전트에 어떻게 잘라서 넘기는지 명세 누락
- Step 3 Topic Newsroom / Content Newsroom 오케스트레이터 설계 시 명시 필요:
  - Trend Scout 출력의 어느 필드가 Audience Analyst 입력으로 가는지 (현재 `trending_topics`만)
  - Strategy Planner는 Trend Scout + Audience Analyst 출력을 어떻게 합쳐 받는지
  - Strategy Planner.final_topic이 Writer.strategy로 들어갈 때 매핑 (category는 외부에서 별도 주입 또는 final_topic.category에서 추출)
  - Editor.final_content + Format Architect 출력이 HTML Builder 입력으로 합쳐지는 방식
- 권장: `backend/orchestrators/data_flow_spec.md` 또는 오케스트레이터 코드 상단 주석으로 명세화

> **상태 (2026-05-23)**: data_flow_spec.md 신규 작성으로 해소. Stage 1~3 전체 핸드오프 규칙 명세화. Step 3-2/3-3 진행하면서 보강 예정.
