# B4-S2: 토픽 × angle × SEG 기획 폼 + 프론트 선정결과 노출

## 목표
1. 운영자는 **토픽(4개 고정)만 선택**, 시스템이 **angle round-robin + SEG 회전**으로 `토픽 × angle × SEG` 조합을 자동 확정.
2. 확정된 조합을 **Strategy Planner 입력(시스템 프롬프트)**에 주입.
3. **프론트/UI에서 (a) 토픽 선택, (b) 선정된 조합(토픽·angle·SEG)을 가시화** — "이번 회차에 무엇이 정해졌는지"를 운영자가 즉시 확인.
4. run 스트림 / judge 영역에도 선정 조합 메타 노출.

---

## 범위 / 비범위 (반드시 준수)

| 구분 | 내용 |
|---|---|
| **범위(이번 작업)** | angle 라이브러리 9종, segment 리스트(연령대 포함), 토픽 4종 고정, **in-memory round-robin selector**, Strategy Planner 프롬프트 주입, run 메타 노출(SSE/API), 프론트 토픽 선택 + 조합 표시 UI |
| **비범위(v2)** | `dedup_window`(최근 N건 topic+angle 중복금지) → **발행이력(Topic Registry) 영속 의존이라 v2**, 발행이력 연동, `event_tie` angle 실데이터(`data/events.json`) 주입, `campaign_or_rotate`(캠페인 타겟 우선), 영속 카운터(Railway Volume) |

> 핵심 경계: **발행이력이 v2로 빠졌으므로 "최근 N건 중복회피"는 이번 범위 아님.** 이번엔 단순 순환(round-robin) 카운터만 구현. 진짜 중복회피는 발행이력 붙는 v2에서.

---

## 0. Discovery (먼저 보고만, 코드 변경 X)

아래를 조사해서 **표로 보고하고 멈춤**. 사용자 OK 후 §1부터 진행.

1. **run 진입 경로**: 프론트에서 run을 시작할 때 토픽/카테고리를 입력받는 UI가 현재 있는지. 있으면 컴포넌트 경로 + 입력값이 백엔드 어느 엔드포인트로 가는지.
2. **토픽 정의 위치**: 현재 토픽/카테고리(맛집·AI트렌드·안전·문화 등)가 하드코딩인지, config인지, 어디서 정의되는지.
3. **Strategy Planner 입력**: Strategy Planner가 시스템 프롬프트/입력으로 무엇을 받는지. SEG·angle 개념이 이미 들어가는 슬롯이 있는지, 아니면 토픽만 받는지.
4. **run 메타 전달 경로**: `run_manager._run_pipeline`(또는 해당 파이프라인 진입점)에서 run 단위 메타데이터를 SSE/응답으로 내보내는 구조가 있는지. 있으면 메타 스키마.
5. **프론트 run 헤더**: run 진행/결과 화면 상단에 회차 정보를 표시하는 영역(컴포넌트)이 있는지. B3-S3-D의 judge 카드/iframe 패턴 재사용 가능 위치.
6. **기존 segment 흔적**: 코드/프롬프트에 segment·persona·타겟 관련 기존 정의가 있는지(중복 정의 방지).

→ 위 6개 보고 후 **중단**. 작업 진행 금지.

---

## 1. 데이터 정의 (`data/planning_presets.json`)

repo-seeded JSON. 백엔드가 로드. (event 실데이터 주입은 별건 admin injection이므로 여기선 참조 키만 둠.)

### 1-1. angle 라이브러리 (9종, `enabled` 플래그 포함)

| key | 한글 라벨 | 후크 요지 | enabled |
|---|---|---|---|
| `contrast` | 대조/충돌 | 통념을 뒤집는 반대 시각 | true |
| `ranking` | 큐레이션/랭킹 | TOP N 선별 | true |
| `narrative` | 1인칭 서사 | 개인 경험담 톤 | true |
| `howto` | 하우투 가이드 | 단계별 실행법 | true |
| `data` | 데이터/근거 | 수치·통계 기반 | true |
| `trend` | 트렌드 진단 | "요즘 ~하는 이유" | true |
| `compare` | 비교/선택 | A vs B 의사결정 | true |
| `quiz` | 퀴즈/진단 결합 | 유형테스트·자가진단 | true |
| `event_tie` | 시의성/이벤트 연계 | 실제 PlusTap 이벤트와 묶기 | **false** |

> `event_tie`는 `data/events.json` 실데이터 주입(admin event injection, 별건) 전까지 **enabled=false**로 둔다. selector는 `enabled=true`만 회전 대상으로 삼는다. 데이터 붙으면 플래그만 true로.

### 1-2. segment 리스트 (연령대 포함, 확장)

연령대를 **별도 축으로 분리하지 않고**(조합 폭발·마감 스코프) 연령+라이프스타일 **결합 페르소나** 단일 축으로 둔다. 글쓰기에 더 구체적인 페르소나를 제공.

| key | 한글 라벨 | 페르소나 요지 |
|---|---|---|
| `twenties_newbie` | 20대 사회초년생 | 첫 직장, 가처분소득 적음, 자기계발 관심 |
| `twenties_student` | 20대 대학생·취준생 | 가성비 극민감, 트렌드 흡수 빠름 |
| `thirties_single` | 30대 1인가구 | 자기투자·편의·시간 절약 중시 |
| `thirties_worklife` | 30대 워라밸 직장인 | 시간 > 돈, 효율·루틴 최적화 |
| `side_hustler` | N잡러 | 부수입·생산성 도구·자동화 관심 |
| `frugal` | 알뜰소비러 | 할인·혜택·포인트 극대화 |
| `early_adopter` | 트렌드 얼리어답터 | 신기술·신상 선점, 자랑 욕구 |

> 이 리스트는 JSON에서 수정 가능. 최종 항목·라벨은 Kane이 조정. (순수 "20대"/"30대" 단독 세그를 추가하고 싶으면 `age_20s`/`age_30s` 항목을 더하면 되나, 회전 주기가 길어지므로 7개 내외 권장.)

### 1-3. topics (4개 고정)

```
["맛집", "AI트렌드", "안전", "문화"]
```

### 1-4. rotation 설정 (이번 범위 / v2 구분 명시)

```json
{
  "angle": "round_robin",
  "segment": "rotate",
  "dedup_window": 5,        // v2: 발행이력 연동 시 활성. 이번 범위 미사용(주석/무시)
  "campaign_priority": false // v2: campaign_or_rotate. 이번 범위 단순 rotate
}
```

> `dedup_window`, `campaign_priority`는 **필드만 존재, 로직 미연결**. v2 발행이력 작업에서 활성.

---

## 2. 백엔드 작업

### 2-1. selector 모듈 (in-memory round-robin)

- `enabled=true`인 angle만 대상으로 **순환 카운터**로 다음 angle 선택. (최근 N건 중복회피 아님 — 단순 순환.)
- segment는 리스트 순환(rotate).
- 카운터는 **런타임 메모리**(모듈 레벨 or RunManager 인스턴스). redeploy 시 리셋 허용(v2에서 Volume/DB 영속).
- 입력: `topic`(운영자 선택) → 출력: `{topic, angle, angle_label, segment, segment_label}`.
- `logging` 사용(`print` 금지), type hints, `pathlib.Path`로 JSON 로드, UTF-8.

### 2-2. 파이프라인 주입

- run 진입점(`run_manager._run_pipeline` 또는 Discovery에서 확정된 위치)에서 selector 호출 → 조합 확정 → run 메타에 저장.
- **Strategy Planner 시스템 프롬프트에 주입**:
  - angle 지시문: 해당 angle의 후크 방식으로 기획하도록 (예: `contrast` → "통념을 뒤집는 반대 시각으로 접근")
  - segment 페르소나: 해당 SEG 독자를 타겟으로 (예: `thirties_single` → "30대 1인가구 독자 관점")
- trace에 선정 조합이 남도록(데모에서 "AI가 이 각도·이 독자로 기획" 가시화).

### 2-3. run 메타 노출 (SSE / API)

- run 응답 및 SSE 메타 이벤트에 `{topic, angle, angle_label, segment, segment_label}` 포함.
- 기존 SSE 스키마에 필드 추가 방식(브레이킹 없게). `useRunStream` 소비 측 호환 확인.

---

## 3. 프론트 작업

### 3-1. 토픽 선택 UI (run 시작)

- 4개 토픽 카드/버튼 그리드. 1개 선택 강제.
- U+ 핑크(`#ff2e98`) 선택 강조. 다크모드 토큰 준수.

### 3-2. 선정 조합 표시 ("이번 회차 기획")

- run 시작 직후, 백엔드가 확정한 `토픽 · angle · SEG`를 **헤더 카드/배지로 고정 노출**.
- 형식 예: `맛집` · `대조/충돌` · `30대 1인가구` + 한 줄 요약("30대 1인가구 독자에게 통념을 뒤집는 시각으로").
- angle / SEG 배지 색 구분(가독). 한글 라벨 표시.
- run 진행 중에도 상단 고정(스크롤해도 회차 기획이 보이게).

### 3-3. run 스트림 / judge 노출

- B3-S3-D judge 카드 영역 또는 run 헤더에 동일 조합 메타 표기(중복 OK, 일관성).

---

## 종료 조건 (Exit Criteria)

- [ ] 프론트에서 토픽 4개 중 1개 선택 → run 시작 가능. 미선택 시 시작 불가(또는 기본값 처리, Discovery 결과 따름).
- [ ] 백엔드가 run마다 angle(round-robin) + segment(rotate) 자동 선정, 응답/SSE 메타에 `{topic, angle, angle_label, segment, segment_label}` 포함.
- [ ] 동일 토픽 **2회 연속 run 시 angle이 순환되어 달라짐**(enabled angle 8종 기준).
- [ ] Strategy Planner trace에 선정된 angle 지시문 + segment 페르소나가 실제 반영됨(육안 확인 가능).
- [ ] 프론트 헤더에 `토픽 · angle · SEG` 조합 + 한 줄 요약 노출, run 진행 중에도 유지.
- [ ] `event_tie`는 enabled=false라 회전 대상에서 제외됨.

---

## 회귀 점검 (Regression Check)

- [ ] 기존 run 파이프라인 정상(9 에이전트 흐름, 종료).
- [ ] Judge Panel 3모델 평가 + radar chart 정상.
- [ ] SSE 라이브 스트림 정상(메타 필드 추가로 인한 파싱 깨짐 없음). `useRunStream` setState 순수성 유지.
- [ ] `final_output.html` 저장 정상.
- [ ] 백엔드 테스트 PASS(기존 56/56 유지). selector 신규 테스트 추가 시 카운트 갱신.
- [ ] `npm run build` PASS.

---

## 시각 임팩트 체크리스트

- [ ] 토픽 선택 카드: 4개 그리드, 선택 시 U+ 핑크 강조, 다크모드 대비 충분.
- [ ] 선정 조합 배지: angle / SEG 색 구분, 한글 라벨, 잘림 없음.
- [ ] "이번 회차 기획" 카드 run 상단 고정 노출.
- [ ] 모바일 폭(~380px)에서 배지·카드 레이아웃 깨짐 없음.

---

## 분할 commit 안내

각 커밋 전 **`git status` + `git diff` 확인** 후 Kane이 수동 스테이징·커밋. (auto `git add`/`commit` 금지.)

| commit | 범위 |
|---|---|
| 1 | `data/planning_presets.json` + selector 모듈(백엔드 in-memory round-robin) + 단위 테스트 |
| 2 | 파이프라인 주입(Strategy Planner 프롬프트) + run 메타 노출(SSE/API) |
| 3 | 프론트 토픽 선택 UI + 선정 조합 표시(헤더/judge) |

커밋 메시지 초안은 작업 완료 후 Kane이 요청 시 복사용 코드블록으로 제공.

---

## v2 백로그 (이번 작업에서 의도적으로 제외)

1. **발행이력(Topic Registry) 연동** → 선정 조합 기록.
2. `dedup_window`: 최근 N건 `topic+angle` 조합 중복금지 (1번 영속 의존).
3. `event_tie` angle 활성: `data/events.json` 실 PlusTap 이벤트 주입(admin event injection과 결합).
4. `campaign_or_rotate`: 캠페인 타겟 SEG 우선.
5. selector 카운터 영속(Railway Volume/DB) — redeploy 시 회전 상태 유지.
