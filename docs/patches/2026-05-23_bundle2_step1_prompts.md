# 묶음 2 Step 1 작업 지시서 — 4개 prompt 신규 작성

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2의 Step 1  
**범위**: 4개 prompt 신규 작성 + PROGRESS.md 업데이트  
**실행 방식**: 파일 복사 + 기존 placeholder 파일 교체. 코드 실행/테스트 없음.

---

## 작업 개요

| # | 파일 | 작업 | source |
|---|---|---|---|
| 1 | `backend/agents/prompts/01_trend_scout.md` | 전체 교체 | `docs/patches/_src_01_trend_scout.md` |
| 2 | `backend/agents/prompts/02_audience_analyst.md` | 전체 교체 | `docs/patches/_src_02_audience_analyst.md` |
| 3 | `backend/agents/prompts/03_strategy_planner.md` | 전체 교체 | `docs/patches/_src_03_strategy_planner.md` |
| 4 | `backend/agents/prompts/09_html_builder.md` | 전체 교체 | `docs/patches/_src_09_html_builder.md` |
| 5 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 업데이트 | - |

대상 4개 파일은 현재 placeholder 한 줄만 있는 상태:

```
# {에이전트 이름}

> 시스템 프롬프트 내용은 Phase 2에서 작성 예정.
```

이걸 source 파일 내용으로 전체 교체.

---

## 묶음 1 검토 패턴 적용 확인

4개 prompt 모두 다음 패턴을 따름 (묶음 1 검토에서 도출):

1. **모든 입력에 `category` 일관 포함** ✅
2. **04~08과 입출력 키 매칭** ✅
   - Trend Scout → Audience Analyst: `trending_topics` 그대로 전달
   - Audience Analyst → Strategy Planner: `audience_evaluation`, `verdict.top_choice_topic` 그대로 매칭
   - Strategy Planner.final_topic → Writer.strategy: 키 완전 매칭 (key_messages, data_grounding, target_persona, content_type_recommendation)
   - Editor.final_content + Format Architect.format_decision → HTML Builder 입력
3. **항목별 매핑 필요한 곳은 배열** ✅
4. **출력 스키마 예시값에 `"<입력 ~ 그대로>"` 주석 일관 적용** ✅
5. **AI 클리셰 금지 섹션 명시** ✅

---

## 5건 결정사항 적용 확인 (묶음 1 → 묶음 2 핸드오프)

NEXT_BUNDLE_NOTES.md §5에서 미정이었던 5건, 모두 HTML Builder prompt에 반영:

| # | 결정 | 적용 위치 |
|---|---|---|
| 1 | placeholder_locations.location 형식: **dotted notation** | `## placeholder_locations 해석 (dotted notation)` 섹션 |
| 2 | image_descriptions 용도: **alt + 생성 프롬프트 통합** | `## layout_hints.image_descriptions 활용` 섹션 |
| 3 | placement 구체화: **between_section_N_and_N+1** | `## 작업 절차` 2-3번 + 인터랙티브 placement 옵션 |
| 4 | CALCULATOR 안전성: **mathjs 사용, eval 금지** | `### CALCULATOR` 섹션 + 규칙 섹션 |
| 5 | Grounding 호출 단위: **draft 전체 1회** | Trend Scout `## 검색 절차` 2번 항목 |

---

# 작업 1: backend/agents/prompts/01_trend_scout.md

`docs/patches/_src_01_trend_scout.md` 의 전체 내용으로 교체.

기존 placeholder 파일 내용 (3줄):
```
# Trend Scout

> 시스템 프롬프트 내용은 Phase 2에서 작성 예정.
```

→ source 파일 내용으로 전체 덮어쓰기.

---

# 작업 2: backend/agents/prompts/02_audience_analyst.md

`docs/patches/_src_02_audience_analyst.md` 의 전체 내용으로 교체.

---

# 작업 3: backend/agents/prompts/03_strategy_planner.md

`docs/patches/_src_03_strategy_planner.md` 의 전체 내용으로 교체.

---

# 작업 4: backend/agents/prompts/09_html_builder.md

`docs/patches/_src_09_html_builder.md` 의 전체 내용으로 교체.

---

# 작업 5: PROGRESS.md 업데이트

## 5-1. Phase 2 체크리스트 4개 항목 ✅ 처리

기존:
```
- [ ] Trend Scout system prompt 작성
- [ ] Audience Analyst system prompt 작성
- [ ] Strategy Planner system prompt 작성
- [ ] HTML Builder system prompt 작성
```

교체:
```
- [x] Trend Scout system prompt 작성
- [x] Audience Analyst system prompt 작성
- [x] Strategy Planner system prompt 작성
- [x] HTML Builder system prompt 작성
```

## 5-2. 진행률 갱신

- 기존: 16/46 (34.8%)
- 신규: 20/46 (43.5%)
- 마지막 업데이트 일자: 2026-05-23

## 5-3. 의사결정 로그 추가 (2026-05-23 자)

다음 항목 추가:

```
- 2026-05-23 묶음 2 Step 1 완료: 4개 prompt 신규 작성 (Trend Scout / Audience Analyst / Strategy Planner / HTML Builder).
  - 묶음 1 검토 패턴 적용: category 입력 일관, 입출력 키 매칭, 항목별 배열화, AI 클리셰 금지 명시
  - NEXT_BUNDLE_NOTES.md §5의 5건 미정사항 모두 확정 적용:
    1. placeholder_locations.location: dotted notation
    2. image_descriptions: alt + 이미지 생성 프롬프트 통합
    3. placement 구체화: between_section_N_and_N+1
    4. CALCULATOR formula: mathjs 사용, eval 금지
    5. Grounding 호출 단위: draft 전체 1회
- 2026-05-23 묶음 2 분할 진행 결정:
  - Step 1: 4개 prompt 신규 작성 (이번 단계)
  - Step 2 (다음): base_agent.py 일반화 (TONE_REFERENCE + placeholder 화이트리스트 치환)
  - Step 3 (다다음): 오케스트레이터 3개 (Topic Newsroom + Content Newsroom + Game-ifier)
  - 묶음 3 (별도): Judge Panel + 통합 테스트
```

## 5-4. NEXT_BUNDLE_NOTES.md §5 상태 변경

§5의 5건이 모두 확정·적용되었으므로 §5 섹션 끝에 다음 한 줄 추가:

```
> **상태**: 위 5건 모두 2026-05-23 묶음 2 Step 1 작업 중 확정. HTML Builder prompt + Trend Scout prompt에 반영 완료. 본 섹션은 이력 보존 목적으로 유지.
```

---

# 실행 후 보고 항목

작업 완료 후 다음을 보고:

1. 4개 prompt 파일 교체 적용 확인 (각 파일별 line count, 첫 3줄)
2. PROGRESS.md 변경 사항:
   - 체크리스트 4건 [x] 처리 확인
   - 진행률 16/46 → 20/46 (43.5%)
   - 의사결정 로그 신규 항목 2건
3. NEXT_BUNDLE_NOTES.md §5 상태 라인 추가 확인
4. git status (스테이징은 하지 말 것)
5. 다음 단계 안내: "묶음 2 Step 2 (base_agent.py 일반화) 진입 준비 완료"

---

# 주의사항

- **코드 실행이나 import 테스트 안 함**. 파일 편집만.
- source 파일은 `docs/patches/` 아래에 있음. 복사 시 파일 내용 그대로 (UTF-8 인코딩 유지).
- 기존 placeholder 파일을 **전체 교체** (append 아님).
- 4개 source 파일은 작업 후에도 `docs/patches/` 에 남겨둠 (이력 보존).
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.
