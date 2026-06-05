# B4-S2 (v2): 토픽 × angle × SEG 기획 폼 + 프론트 선정결과 노출

> v1 대비 변경: Discovery 결과 반영. 토픽 중복정의 제거(기존 category 사용), angle 자율→지정 전환 명시, SEG↔target_persona 계층 확정, run 메타 주입 지점 확정, 네이밍 충돌 회피, **3→4 커밋(회귀 핵심 단독 분리)**.

## 목표
1. 운영자는 **토픽(기존 category 4개)만 선택**, 시스템이 **angle round-robin + SEG 회전**으로 `토픽 × angle × SEG` 조합 자동 확정.
2. 확정 조합을 **Strategy Planner 시스템 프롬프트에 지정 주입**.
3. **프론트에서 (a) 토픽 선택(기존 CategoryCard 활용), (b) 선정 조합을 헤더 카드로 가시화**.
4. run 스트림 메타에 선정 조합 노출.

---

## 범위 / 비범위

| 구분 | 내용 |
|---|---|
| **범위** | angle 라이브러리 9종(`event_tie` enabled=false), `audience_segments` 리스트(연령대 포함), **in-memory round-robin selector**, Strategy Planner 프롬프트 주입, `pipeline_start`/RunDetail 메타 확장, 프론트 헤더 카드 |
| **비범위(v2)** | `dedup_window`(최근 N건 중복회피) → **발행이력 영속 의존이라 v2**, 발행이력 연동, `event_tie` 실데이터(`data/events.json`) 주입, `campaign_or_rotate`, 영속 카운터(Volume) |

> **토픽은 `planning_presets.json`에 중복 정의하지 않는다.** 기존 `category`(food/ai-trend/safety/culture/custom)가 토픽 역할. 라벨은 기존 `run_manager.CATEGORY_LABEL` 재사용.

---

## 1. 데이터 정의 (`data/planning_presets.json` 신설)

`pathlib.Path` 로드, UTF-8. **topics 키 없음**(기존 category가 토픽).

### 1-1. angle 라이브러리 (9종, `enabled` 플래그)

| key | 한글 라벨 | 후크 지시문(LLM 주입용 요지) | enabled |
|---|---|---|---|
| `contrast` | 대조/충돌 | 통념을 뒤집는 반대 시각으로 접근 | true |
| `ranking` | 큐레이션/랭킹 | TOP N 선별·순위 형식 | true |
| `narrative` | 1인칭 서사 | 개인 경험담 톤으로 풀기 | true |
| `howto` | 하우투 가이드 | 단계별 실행법 중심 | true |
| `data` | 데이터/근거 | 수치·통계 기반 논증 | true |
| `trend` | 트렌드 진단 | "요즘 ~하는 이유" 진단 | true |
| `compare` | 비교/선택 | A vs B 의사결정 도움 | true |
| `quiz` | 퀴즈/진단 결합 | 유형테스트·자가진단 결합 | true |
| `event_tie` | 시의성/이벤트 연계 | 실제 PlusTap 이벤트와 묶기 | **false** |

> `event_tie`는 admin event injection(별건) 전까지 **false**. selector는 `enabled=true`만 회전.

### 1-2. audience_segments (연령대 포함 결합 페르소나)

> 키명 주의: `personas.yaml`(에이전트 발화 페르소나)과 구분 위해 **`audience_segments`** 사용.

| key | 한글 라벨 | 페르소나 요지(LLM 주입용) |
|---|---|---|
| `twenties_newbie` | 20대 사회초년생 | 첫 직장, 가처분소득 적음, 자기계발 관심 |
| `twenties_student` | 20대 대학생·취준생 | 가성비 극민감, 트렌드 흡수 빠름 |
| `thirties_single` | 30대 1인가구 | 자기투자·편의·시간 절약 중시 |
| `thirties_worklife` | 30대 워라밸 직장인 | 시간 > 돈, 효율·루틴 최적화 |
| `side_hustler` | N잡러 | 부수입·생산성 도구·자동화 관심 |
| `frugal` | 알뜰소비러 | 할인·혜택·포인트 극대화 |
| `early_adopter` | 트렌드 얼리어답터 | 신기술·신상 선점 |

> 최종 항목·라벨은 Kane 조정 가능(JSON 수정). 순수 "20대"/"30대" 단독 세그가 필요하면 항목 추가.

### 1-3. rotation 설정

```json
{
  "angle": "round_robin",
  "segment": "rotate",
  "dedup_window": 5,         // v2: 발행이력 연동 시 활성. 이번 미사용
  "campaign_priority": false // v2: 이번 단순 rotate
}
```

---

## 2. 백엔드 작업

### C1. selector 모듈 + JSON (독립, 회귀 무관)

- 신규 모듈(예: `backend/api/services/planning_selector.py`).
- `data/planning_presets.json` 로드(`pathlib.Path`, UTF-8).
- **in-memory round-robin 카운터**(모듈 레벨 또는 RunManager 보유). `enabled=true` angle만 순환. segment 리스트 순환(rotate). redeploy 리셋 허용(v2 영속).
- 입력 `category` → 출력 `{angle, angle_label, angle_directive, audience_segment, segment_label, segment_persona}`.
- `logging`(print 금지), type hints.
- **단위 테스트**: 연속 호출 시 angle 순환 확인, `event_tie` 제외 확인, segment 순환 확인.

### C2. selector 호출 + run 메타 배관

- `_execute`(run_manager.py:187 인근, `pipeline_start` 발행 직전)에서 selector 호출 → 조합 확정. **custom 포함 전 category 동일 적용**(토픽만 custom_topic 사용).
- `pipeline_start` payload(현재 `{session_id, category, custom_topic, options, started_at}`)에 추가:
  `angle, angle_label, audience_segment, segment_label`.
- RunDetail 응답 스키마에 동일 필드 추가(재진입·새로고침 시 표시용).
- 확정된 조합을 `_run_pipeline`로 전달해 Strategy Planner 입력에 쓸 수 있게 보관.
- **SSE 스키마 변경이므로 `useRunStream`의 `pipeline_start` 핸들러 파싱 깨짐 없는지 확인**(필드 추가는 비파괴적이어야).

### C3. Strategy Planner 프롬프트 주입 ★회귀 핵심·단독 커밋

- `backend/agents/prompts/03_strategy_planner.md` 수정.
- **PromptLoader 화이트리스트에 키 추가**: `{{INJECTED_ANGLE}}`, `{{INJECTED_ANGLE_DIRECTIVE}}`, `{{INJECTED_SEGMENT}}`, `{{INJECTED_SEGMENT_PERSONA}}`.
- **angle 자율→지정 전환**:
  - 입력 섹션(L16-20)에 주입 angle/segment 명시.
  - rule 6(L29, angle_suggestion 참고)을 **"시스템 지정 `{{INJECTED_ANGLE}}`를 우선 적용. Audience Analyst의 angle_suggestion은 보조 참고만"** 으로 보강.
  - 출력 `final_topic.angle`(L40)이 **주입된 angle과 정합**하도록 명시.
- **SEG↔target_persona 계층**:
  - `target_persona`(L41) 생성 시 **`{{INJECTED_SEGMENT}}`({{INJECTED_SEGMENT_PERSONA}}) 독자군 안에서 구체화**하도록 지시 추가.
  - Writer(04_writer.md:106)는 변경 불필요(상위에서 SEG 제약된 target_persona를 그대로 받음).
- selector 출력을 PromptLoader 치환값으로 전달하는 배선.

---

## 3. 프론트 작업

### C4. 토픽 선택 + 헤더 카드

- **토픽 선택 UI는 기존 활용**: `page.tsx`의 CategoryCard 4개 + CustomInputCard. 신규 제작 불필요.
- **선정 조합 헤더 카드 신설**: `frontend/app/run/[id]/page.tsx` 슬림 bar 아래(L126)와 3-컬럼 그리드(L128) 사이에 삽입(간섭 최소).
  - 표시: `토픽 라벨` · `angle 배지` · `SEG 배지` + 한 줄 요약(예: "30대 1인가구 독자에게 통념을 뒤집는 시각으로").
  - 메타 출처: `useRunStream`의 `pipeline_start` 수신값(없으면 RunDetail). `useRunStream`에 메타 보관 상태 추가(**setState 업데이터 순수성 유지**).
  - angle/SEG 배지 색 구분, 한글 라벨. Judge 뱃지(ConsensusBadge 등) 색 패턴 재사용.
  - run 진행 중에도 상단 고정 노출.

---

## 종료 조건 (Exit Criteria)

- [ ] 토픽 4개(+custom) 선택 → run 시작(기존 흐름 유지).
- [ ] 백엔드가 run마다 angle(round-robin) + segment(rotate) 확정, `pipeline_start`/RunDetail 메타에 `angle, angle_label, audience_segment, segment_label` 포함.
- [ ] **동일 토픽 2회 연속 run 시 angle 순환되어 달라짐**(enabled 8종 기준).
- [ ] Strategy Planner trace에 주입 angle 지시문 + SEG 페르소나 반영, `final_topic.angle` = 주입 angle.
- [ ] 프론트 헤더 카드에 조합 + 한 줄 요약 노출, 진행 중 유지.
- [ ] `event_tie`는 회전 대상 제외.

---

## 회귀 점검 (Regression Check)

- [ ] **C3 직후 우선**: 동일 토픽으로 1~2 run 실제 생성 → 글 품질·종료·출력 정상인지 육안 확인(angle 지정 전환 영향 점검).
- [ ] 9 에이전트 파이프라인 정상 종료, Writer/편집국장 반론 반영 흐름 유지.
- [ ] Judge Panel 3모델 + radar chart 정상.
- [ ] SSE 라이브 스트림 정상(메타 필드 추가로 인한 파싱 깨짐 없음). `useRunStream` setState 순수.
- [ ] `final_output.html` 저장 정상.
- [ ] 백엔드 테스트 PASS(기존 57 유지 + selector 신규 테스트).
- [ ] `npm run build` PASS.

---

## 시각 임팩트 체크리스트

- [ ] 헤더 카드: 토픽·angle·SEG 배지 색 구분, 한글 라벨, 잘림 없음.
- [ ] 슬림 bar↔그리드 사이 삽입으로 기존 3-컬럼 레이아웃(h-[70vh]) 안 깨짐.
- [ ] run 진행 중 상단 고정 유지.
- [ ] 모바일 폭(~380px)에서 배지 줄바꿈 정상.

---

## 분할 commit 안내

각 커밋 전 **`git status` + `git diff` 확인** 후 Kane 수동 스테이징·커밋. (auto add/commit 금지.) **커밋 단위로 멈추고 보고** — 한 번에 C1~C4 연속 실행 금지.

| commit | 범위 |
|---|---|
| C1 | `data/planning_presets.json` + `planning_selector.py` + 단위테스트 |
| C2 | `_execute` selector 호출 + `pipeline_start`/RunDetail 메타 확장 |
| C3 | `03_strategy_planner.md` 주입(angle 지정 + SEG) + PromptLoader 화이트리스트 ★회귀검증 동반 |
| C4 | 프론트 헤더 카드 + `useRunStream` 메타 수신 |

커밋 메시지 초안은 각 커밋 완료 후 요청 시 복사용 코드블록 제공.

---

## v2 백로그

1. 발행이력(Topic Registry) 연동 → 선정 조합 기록.
2. `dedup_window`: 최근 N건 `topic+angle` 중복금지(1번 영속 의존).
3. `event_tie` 활성: `data/events.json` 실 PlusTap 이벤트 주입(admin event injection 결합).
4. `campaign_or_rotate`: 캠페인 타겟 SEG 우선.
5. selector 카운터 영속(Volume/DB).
