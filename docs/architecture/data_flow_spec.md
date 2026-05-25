# AIDEN 데이터 흐름 명세서 (Data Flow Spec)

**버전**: 1.0
**작성일**: 2026-05-23
**목적**: 9개 에이전트 간 입출력 매핑 + 오케스트레이터의 데이터 변환 규칙 명시

---

## 1. 전체 파이프라인 개요

```
[User Input: category]
        │
        ▼
┌──────────────────────────────┐
│  Stage 1: Topic Newsroom     │  단방향, 1회 실행
│  Scout → Analyst → Planner   │
└──────────────────────────────┘
        │ final_topic
        ▼
┌──────────────────────────────┐
│  Stage 2: Content Newsroom   │  max 3 iter 토론
│  Writer ↔ FC ↔ DA ↔ Editor   │
└──────────────────────────────┘
        │ final_content
        ▼
┌──────────────────────────────┐
│  Stage 3: Game-ifier         │  단방향
│  Format Architect → HTML B   │
└──────────────────────────────┘
        │ html
        ▼
[Output: Plustab-ready HTML]
```

## 2. Stage 1: Topic Newsroom

### 2-1. Trend Scout
- **입력**: 오케스트레이터가 직접 조립
  ```json
  {
    "category": "<user input>",
    "target_date": "<오늘 날짜 ISO>"
  }
  ```
- **출력**: prompt에 명시된 스키마 그대로

### 2-2. Audience Analyst
- **입력 조립 규칙**:
  ```python
  audience_input = {
      "category": scout_output["category"],
      "trending_topics": scout_output["trending_topics"]  # 이것만 전달
  }
  # summary, search_queries_used는 무시
  ```

### 2-3. Strategy Planner
- **입력 조립 규칙**:
  ```python
  planner_input = {
      "category": scout_output["category"],
      "trend_scout": scout_output,         # 전체 전달
      "audience_analyst": analyst_output   # 전체 전달
  }
  ```
- **출력의 `final_topic`이 Stage 2의 시작점**

## 3. Stage 1 → Stage 2 핸드오프

```python
# Topic Newsroom 출력 (planner_output) → Content Newsroom 입력
writer_input_iter1 = {
    "iteration": 1,
    "category": planner_output["final_topic"]["category"],
    "strategy": planner_output["final_topic"]  # final_topic 전체를 strategy로 매핑
}
```

**중요**: Writer의 입력 키 `strategy`는 `final_topic` 객체와 동치. category는 한 단계 위로 끌어올림.

## 4. Stage 2: Content Newsroom (Step 3-2에서 상세)

### 4-1. Round-Robin 흐름 (iter 1)
```
Writer → Fact-Checker → Devil's Advocate → Editor
```

### 4-2. iter 2+ 입력 조립
Writer.input v2+:
```python
writer_input_iter2 = {
    "iteration": 2,
    "category": <상동>,
    "strategy": <상동>,
    "previous_draft": writer_output_v1,
    "factcheck_log": factchecker_output_v1,
    "critique": da_output_v1,
    "editor_instructions": editor_output_v1["revision_instructions"]
}
```

Devil's Advocate.input v2+:
```python
da_input_iter2 = {
    "iteration": 2,
    "category": <상동>,
    "annotated_draft": factchecker_output_v2,
    "previous_critiques": da_output_v1["critical_issues"],
    "editor_response": {
        "accepted_critiques": editor_output_v1["accepted_critiques"],
        "rejected_critiques": editor_output_v1["rejected_critiques"]
    }
}
```

### 4-3. 종료 조건
- `editor_output["decision"] == "approved"` → 즉시 종료
- `iteration == 3` AND `editor_output["decision"] == "needs_revision"` → 강제 종료 (Editor가 approved + known_weaknesses 명시)

## 5. Stage 2 → Stage 3 핸드오프

```python
# Editor 최종 출력 → Format Architect 입력
format_architect_input = editor_output["final_content"]
```

## 6. Stage 3: Game-ifier

### 6-1. Format Architect
- **입력**: `editor_output["final_content"]`
- **출력**: prompt에 명시된 스키마 (selected_type, base_layout, interactive, layout_hints, placeholder_locations)

### 6-2. HTML Builder
- **입력 조립**:
  ```python
  html_builder_input = {
      "final_content": editor_output["final_content"],
      "format_decision": format_architect_output
  }
  ```
- **출력**: html(문자열) + meta(placeholder_substitutions, preserved_placeholders, warnings)

### 6-3. Gameifier 오케스트레이터
- 두 에이전트 단방향. iter 없음.
- 에이전트 실패 시 fallback: Editor.final_content를 plain HTML로 변환 (`_orchestrator_fallback` 플래그)
- fallback HTML도 `known_weaknesses` 섹션 포함 (투명성)

### 6-4. FullPipeline 통합
- 3 Newsroom을 단일 TraceLogger로 묶어 실행
- base_order 자동 분배: Topic 1-3, Content 4-7 (iter별 suffix), Game-ifier 8-9
- 최종 HTML은 `runs/<run_id>/final_output.html`로 저장 (스크립트가 처리, 오케스트레이터는 dict만 반환)

## 7. 트레이스 로그 구조

실행마다 다음 폴더 구조 생성:

```
runs/
  2026-05-23T14-30-00_{run_id}/
    metadata.json              # 입력 + 전체 진행 요약
    summary.jsonl              # 에이전트별 한 줄 요약 (시각화용)
    agents/
      01_trend_scout.json
      02_audience_analyst.json
      03_strategy_planner.json
      04_writer_iter1.json
      05_fact_checker_iter1.json
      06_devils_advocate_iter1.json
      07_editor_iter1.json
      (iter 2/3 있으면 그대로 누적)
      08_format_architect.json
      09_html_builder.json
    final_output.html           # 최종 HTML
```

## 8. 에러 처리 원칙

- 각 에이전트가 잘못된 JSON 반환 → 1회 재시도, 실패 시 trace에 기록 후 fallback
- LLM API 호출 실패 → 지수 백오프 3회 재시도
- 오케스트레이터는 절대 raise 안 함. 실패 시 trace에 명시 후 최선 결과 반환.

## 9. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-23 | 초안 작성 (Step 3-1) |
