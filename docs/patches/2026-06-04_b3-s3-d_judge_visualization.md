# B3-S3-D Judge 시각화 + 결과 HTML 미리보기 통합 명세

**작성일**: 2026-06-04
**범위**: 트레이스 뷰어 하단에 Judge Panel 시각화 + 최종 콘텐츠 iframe 미리보기 통합
**의존**: B3-S3-C 완료 (트레이스 뷰어 3-컬럼 정상 동작)
**관련 산출물**: Judge Panel 백엔드 (B3-S2-E2E 완료), 9 에이전트 E2E (judge_panel.json 생성됨)
**부수 fix**: API 경로 final_output.html 저장 누락 (메모리 #5)

---

## 0. 결정사항 확정

| 항목 | 결정 |
|---|---|
| 차트 라이브러리 | **Recharts** (Next.js 14 + React Query 환경 안정성) |
| 3-Model 카드 | **가로 3열** (lg 이상). 모바일은 세로 누적 |
| Judge 결과 위치 | 트레이스 뷰어 **하단 탭** (같은 페이지) |
| 페이지 구조 | 하단 탭 2개: **`판정` (Judge Panel)** / **`결과물` (iframe 미리보기)** |
| 점수 카운트업 애니메이션 | **ON** (mount 시 0 → 실제값 1.2s) |
| 레이더 차트 | 5축 — `사실성` / `참신성` / `명확성` / `완성도` / `인터랙티브` |
| Outlier 표시 | 점수 카드에 빨간 dot + tooltip "다른 평가자 대비 ±1.5σ 이상" |
| 시각 임팩트 | 풍부하게 (애니메이션·gradient·subtle motion) |

---

## 1. 작업 개요

| # | 파일 | 작업 |
|---|---|---|
| **백엔드** | | |
| 1 | `backend/api/services/run_manager.py` | API 경로 `_run_pipeline` 마지막에 HTML 래퍼 적용 + `final_output.html` 저장 후처리 추가 |
| 2 | `backend/api/routers/runs.py` | `GET /api/runs/{id}/judge` 엔드포인트 추가 (판정 결과 반환). `GET /api/runs/{id}/final-html` 도 추가 |
| 3 | `backend/api/schemas/judge.py` | 신규. Judge 응답 스키마 (3 모델 점수 + aggregate + outlier flag) |
| 4 | `backend/api/main.py` | `runs` 폴더 정적 서빙 등록 (`StaticFiles`로 `/runs/{id}/final_output.html` 노출) |
| 5 | `backend/tests/api/test_judge_endpoint.py` | 신규. judge / final-html 엔드포인트 테스트 |
| **프론트엔드** | | |
| 6 | `frontend/lib/api.ts` | `fetchJudge(runId)` + `fetchFinalHtmlUrl(runId)` 함수 추가 |
| 7 | `frontend/lib/types/judge.ts` | 신규. JudgeResult / ModelEvaluation / Outlier 타입 |
| 8 | `frontend/components/run/RadarChart.tsx` | 신규. Recharts radar 5축 |
| 9 | `frontend/components/run/ModelScoreCard.tsx` | 신규. 3 모델 각각의 점수 카드 (카운트업 + outlier) |
| 10 | `frontend/components/run/JudgePanel.tsx` | 신규. Radar + 3 카드 + aggregate + 평가 코멘트 |
| 11 | `frontend/components/run/FinalHtmlPreview.tsx` | 신규. iframe + 로딩 + 에러 fallback |
| 12 | `frontend/components/run/BottomTabs.tsx` | 신규. Judge / 결과물 탭 분기 |
| 13 | `frontend/app/run/[id]/page.tsx` | 하단 탭 통합 (기존 3-컬럼 위 유지, 아래에 탭) |
| 14 | `frontend/hooks/useCountUp.ts` | 신규. 0 → target 카운트업 (1.2s easeOut) |

테스트: 백엔드 5건 + 수동 검증 §10 체크리스트.

---

## 2. 백엔드 — API 경로 final_output.html 저장 fix

### 2-1. `backend/api/services/run_manager.py` 수정

`_run_pipeline` 의 9 에이전트 완주 직후, 기존 CLI 스크립트(`scripts/run_full_pipeline.py`)의 후처리 로직을 동일하게 적용:

```python
# _run_pipeline 끝 부분 (judge_panel 호출 전/후 적절한 위치)
html_builder_output = agents[8]["output"]  # 09_html_builder.json의 output
inner_html = html_builder_output.get("html", "")
if inner_html:
    final_html = self._apply_wrapper(inner_html)  # CLI 와 동일한 래퍼 적용
    final_path = self.run_dir / "final_output.html"
    final_path.write_text(final_html, encoding="utf-8")
    logger.info(f"Saved final_output.html: {final_path}")
```

⚠️ `_apply_wrapper` 로직은 `scripts/run_full_pipeline.py` 에서 그대로 import 또는 복사. CLI와 결과 동일해야 함.

### 2-2. `backend/api/main.py` — runs 폴더 정적 서빙

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
if RUNS_DIR.exists():
    app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
```

이러면 `http://localhost:8000/runs/{run_id}/final_output.html` 로 직접 접근 가능. iframe src 로 사용.

⚠️ **보안 주의**: prod 배포 시 임의 path traversal 차단되는지 확인. StaticFiles 는 기본적으로 안전하지만 마감 후 점검 항목으로 남김.

---

## 3. 백엔드 — Judge 엔드포인트

### 3-1. `backend/api/schemas/judge.py` 신규

```python
from typing import Literal
from pydantic import BaseModel


class CriterionScore(BaseModel):
    factuality: float       # 사실성
    novelty: float          # 참신성
    clarity: float          # 명확성
    completeness: float     # 완성도
    interactivity: float    # 인터랙티브


class ModelEvaluation(BaseModel):
    model_id: Literal["gemini", "gpt", "claude"]
    model_name: str          # 실제 모델 식별자 (예: "gemini-2.5-pro")
    scores: CriterionScore
    overall: float           # 5축 평균 또는 가중평균
    comment: str             # 평가 코멘트 (200~500자)
    is_outlier: bool         # ±1.5σ 초과 여부


class JudgeResult(BaseModel):
    run_id: str
    evaluations: list[ModelEvaluation]   # 3개
    aggregate: CriterionScore             # 3 모델 평균
    aggregate_overall: float
    consensus_level: Literal["high", "medium", "low"]  # 분산 기반
    timestamp: str
```

### 3-2. `backend/api/routers/runs.py` 에 엔드포인트 추가

```python
@router.get("/api/runs/{run_id}/judge", response_model=JudgeResult)
def get_judge(run_id: str):
    judge_path = RUNS_DIR / run_id / "judge_panel.json"
    if not judge_path.exists():
        raise HTTPException(404, "Judge panel result not found")
    raw = json.loads(judge_path.read_text(encoding="utf-8"))
    # raw judge_panel.json → JudgeResult 변환 어댑터
    return _adapt_judge_panel(raw, run_id)


@router.get("/api/runs/{run_id}/final-html")
def get_final_html_meta(run_id: str):
    final_path = RUNS_DIR / run_id / "final_output.html"
    if not final_path.exists():
        return {"available": False, "url": None}
    return {
        "available": True,
        "url": f"/runs/{run_id}/final_output.html",
        "size_bytes": final_path.stat().st_size,
    }
```

`_adapt_judge_panel(raw, run_id)` 어댑터: 기존 judge_panel.json 구조(3 모델 평가 + aggregate)를 위 스키마로 변환. 구조 확인은 `runs/2026-06-01T04-36-57_a21069d8/judge_panel.json` (7920 bytes) 참조.

### 3-3. Outlier 계산

aggregate 계산 시 5축 각각의 표준편차 계산 → 한 모델이 모든 축 평균 점수에서 1.5σ 초과 이탈 → `is_outlier=True`. consensus_level:
- `high`: 모든 축의 σ < 1.0
- `medium`: 1.0 ≤ max(σ) < 2.0
- `low`: max(σ) ≥ 2.0

---

## 4. 프론트엔드 — 데이터 계층

### 4-1. `frontend/lib/types/judge.ts`

위 백엔드 스키마와 1:1 매칭되는 TypeScript 타입. `Literal` → string literal union.

### 4-2. `frontend/lib/api.ts` 함수 추가

```typescript
export async function fetchJudge(runId: string): Promise<JudgeResult> { ... }
export async function fetchFinalHtmlMeta(runId: string): Promise<{ available: boolean; url: string | null; size_bytes?: number }> { ... }
```

useQuery 로 wrapping 권장 (`useJudge(runId)`, `useFinalHtmlMeta(runId)`).

---

## 5. 프론트엔드 — useCountUp 훅

### 5-1. `frontend/hooks/useCountUp.ts`

```typescript
import { useEffect, useState } from "react";

export function useCountUp(target: number, durationMs = 1200): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / durationMs);
      // easeOutQuart
      const eased = 1 - Math.pow(1 - t, 4);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);
  return value;
}
```

ModelScoreCard·aggregate 표시에 사용. mount 시 0 → 실제값 부드럽게.

---

## 6. 프론트엔드 — RadarChart

### 6-1. `frontend/components/run/RadarChart.tsx`

Recharts 사용. 한 차트에 **3개 모델 시리즈 + aggregate 시리즈 1개**.

```tsx
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from "recharts";

interface Props {
  evaluations: ModelEvaluation[];   // 3개
  aggregate: CriterionScore;
}

const AXES = [
  { key: "factuality", label: "사실성" },
  { key: "novelty", label: "참신성" },
  { key: "clarity", label: "명확성" },
  { key: "completeness", label: "완성도" },
  { key: "interactivity", label: "인터랙티브" },
];

// 시리즈 색 (페르소나 palette 와 분리 — Judge 전용)
const MODEL_COLORS: Record<string, string> = {
  gemini: "#4285F4",      // Google blue
  gpt: "#10A37F",         // OpenAI green
  claude: "#CC785C",      // Anthropic terra
  aggregate: "#FFFFFF",   // 흰색 + 두꺼운 stroke
};
```

데이터 변환: AXES 순회하며 `{ axis: "사실성", gemini: 8.2, gpt: 7.5, claude: 8.0, aggregate: 7.9 }` 형태로 변환.

레이아웃: `<ResponsiveContainer width="100%" height={400}>`. 모바일 (lg 미만)은 320 height.

**시각 효과**:
- aggregate 시리즈는 `strokeWidth={3}` + fill opacity 0.1 (강조)
- 각 모델 시리즈 fill opacity 0.25, strokeWidth 2
- 격자: PolarGrid `gridType="polygon"`, stroke 색 매우 옅게 (디자인 토큰 `--border-subtle`)
- 축 라벨: `PolarAngleAxis` tick 폰트 `font-korean` 14px
- 점수 범위: `PolarRadiusAxis domain={[0, 10]}` tickCount={6} (0, 2, 4, 6, 8, 10)
- mount 애니메이션: Recharts 기본 `isAnimationActive={true}` `animationDuration={1500}` `animationEasing="ease-out"`
- Tooltip: 호버 시 해당 축의 4개 값(3 모델 + aggregate) + 차이 표시

---

## 7. 프론트엔드 — ModelScoreCard

### 7-1. `frontend/components/run/ModelScoreCard.tsx`

3 모델 카드 1개당.

```tsx
interface Props {
  evaluation: ModelEvaluation;
  aggregateOverall: number;   // 차이 표시용
}
```

레이아웃 (가로 3열 중 1열):

```
┌──────────────────────────┐
│ 🟦 Gemini                │  ← 모델 이름 + 색 dot
│ gemini-2.5-pro           │  ← 작은 식별자
│                          │
│    8.4 / 10              │  ← 큰 overall 점수 (카운트업)
│    ↑ +0.3 vs avg         │  ← aggregate 대비 차이
│    🔴 outlier            │  ← outlier 시에만
│                          │
│ ──────────────           │
│ 사실성   ██████░░  8.0   │  ← 5축 가로 게이지
│ 참신성   ████████ 9.5   │
│ 명확성   ███████░  8.5   │
│ 완성도   ██████░░  7.5   │
│ 인터랙티브 ████░░░░ 5.0  │
│ ──────────────           │
│ "본문 사실성 높고 ..."  │  ← 코멘트 (200자 미리보기 + 더보기)
└──────────────────────────┘
```

**시각 효과**:
- overall 점수: 큰 폰트 (text-5xl) + 카운트업 1.2s
- 게이지: width transition 0.8s, mount 시 0 → 실제값
- outlier 시: 카드 전체에 `border-2 border-state-warning` + 빨간 dot
- 카드 호버 시 subtle lift (translate-y-1 + shadow)
- 모델별 액센트 색 (좌측 4px 두께 border)

코멘트 더보기: 초기 200자 + "...더보기" 클릭 시 modal 또는 카드 확장.

---

## 8. 프론트엔드 — JudgePanel 조립

### 8-1. `frontend/components/run/JudgePanel.tsx`

```tsx
interface Props {
  runId: string;
}

export function JudgePanel({ runId }: Props) {
  const { data, isLoading, error } = useJudge(runId);

  if (isLoading) return <JudgePanelSkeleton />;
  if (error || !data) return <JudgePanelError />;

  return (
    <div className="space-y-6 p-6">
      {/* 헤더 */}
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">3-Model Judge Panel</h2>
          <p className="text-sm text-muted">
            Gemini + GPT + Claude 동시 평가 · consensus: <ConsensusBadge level={data.consensus_level} />
          </p>
        </div>
        <AggregateOverall value={data.aggregate_overall} />  {/* 큰 종합 점수 카운트업 */}
      </header>

      {/* 레이더 차트 */}
      <RadarChart evaluations={data.evaluations} aggregate={data.aggregate} />

      {/* 3 모델 카드 가로 3열 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {data.evaluations.map(ev => (
          <ModelScoreCard
            key={ev.model_id}
            evaluation={ev}
            aggregateOverall={data.aggregate_overall}
          />
        ))}
      </div>
    </div>
  );
}
```

**시각 효과**:
- 페이지 진입 시 순차 fade-in: 헤더 → 차트 → 카드들 (stagger 150ms)
- AggregateOverall: 종합 점수 큰 숫자 + 색이 점수에 따라 변화 (8+ 녹색, 6-8 노란색, 6 미만 빨간색)

### 8-2. ConsensusBadge

```
high   → 🟢 합의 높음
medium → 🟡 합의 보통
low    → 🔴 합의 낮음 (★ 발표 어필 포인트 — 토론이 의미 있다는 시그널)
```

---

## 9. 프론트엔드 — 결과 HTML iframe 미리보기

### 9-1. `frontend/components/run/FinalHtmlPreview.tsx`

```tsx
interface Props {
  runId: string;
}

export function FinalHtmlPreview({ runId }: Props) {
  const { data, isLoading } = useFinalHtmlMeta(runId);

  if (isLoading) return <Skeleton />;
  if (!data?.available) return <NotAvailable />;

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const src = `${apiBase}${data.url}`;

  return (
    <div className="p-6">
      <header className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">최종 콘텐츠</h2>
        <div className="flex gap-2">
          <a href={src} target="_blank" className="btn-secondary">
            새 창에서 열기
          </a>
          <button onClick={() => window.print()} className="btn-secondary">
            인쇄
          </button>
        </div>
      </header>
      <div className="rounded-lg overflow-hidden border" style={{ borderColor: "var(--border-strong)" }}>
        <iframe
          src={src}
          className="w-full h-[800px] bg-white"
          sandbox="allow-scripts allow-same-origin"
          title="Final content preview"
        />
      </div>
      <p className="text-xs text-muted mt-2">
        파일 크기: {(data.size_bytes! / 1024).toFixed(1)} KB
      </p>
    </div>
  );
}
```

⚠️ **sandbox 주의**: CHECKLIST/CALCULATOR 인터랙티브 script 실행 필요 → `allow-scripts` 필수. `allow-same-origin` 은 같은 origin 가정 시. 다른 origin이면 빼야 함.

---

## 10. 프론트엔드 — 하단 탭 통합

### 10-1. `frontend/components/run/BottomTabs.tsx`

```tsx
import { useState } from "react";
import { JudgePanel } from "./JudgePanel";
import { FinalHtmlPreview } from "./FinalHtmlPreview";

interface Props {
  runId: string;
  defaultTab?: "judge" | "final";
}

export function BottomTabs({ runId, defaultTab = "judge" }: Props) {
  const [tab, setTab] = useState(defaultTab);

  return (
    <section className="mt-8 border-t pt-6" style={{ borderColor: "var(--border-strong)" }}>
      <div role="tablist" className="flex gap-2 mb-4">
        <TabButton active={tab === "judge"} onClick={() => setTab("judge")}>
          🎯 판정 (3-Model Judge)
        </TabButton>
        <TabButton active={tab === "final"} onClick={() => setTab("final")}>
          📄 결과물 미리보기
        </TabButton>
      </div>
      <div className="bg-surface-2 rounded-xl">
        {tab === "judge" && <JudgePanel runId={runId} />}
        {tab === "final" && <FinalHtmlPreview runId={runId} />}
      </div>
    </section>
  );
}
```

**시각 효과**:
- TabButton 액티브 표시: 하단 액센트 라인 (LG U+ pink) + bg 변화
- 탭 전환 시 fade transition 200ms

### 10-2. `frontend/app/run/[id]/page.tsx` 통합

```tsx
// 기존 3-컬럼 레이아웃 아래에 BottomTabs 추가
return (
  <div className="min-h-screen p-4">
    {/* 상단 3-컬럼 (B3-S3-C 그대로) */}
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_300px] gap-4 h-[70vh]">
      <aside><StagePanel ... /></aside>
      <main><ChatStream ... /></main>
      <aside><NowPlayingPanel ... /></aside>
    </div>

    {/* 하단 탭 (신규) */}
    <BottomTabs runId={id} defaultTab="judge" />
  </div>
);
```

⚠️ 상단 3-컬럼 높이를 `h-[70vh]` 정도로 제한해서 하단 탭이 자연스럽게 보이도록. 너무 높으면 스크롤해야 탭 보임.

---

## 11. 단위 테스트

### 11-1. `backend/tests/api/test_judge_endpoint.py` 신규

| # | 케이스 | 검증 |
|---|---|---|
| 1 | `GET /api/runs/{valid_id}/judge` 200 | JudgeResult 스키마 일치, 3 evaluations |
| 2 | `GET /api/runs/{invalid_id}/judge` 404 | 메시지 명확 |
| 3 | Outlier 계산 정확성 | 한 모델만 ±1.5σ 초과 mock 데이터로 검증 |
| 4 | Consensus level 계산 | high/medium/low 경계 검증 |
| 5 | `GET /api/runs/{id}/final-html` `available=true` + URL | 파일 존재 시 |

프론트 단위 테스트는 마감 일정 고려 생략. 수동 검증으로 대체.

---

## 12. 수동 검증 체크리스트

### 12-1. 백엔드
- [ ] `curl http://localhost:8000/api/runs/<id>/judge` 200 + 3 evaluations
- [ ] `curl http://localhost:8000/api/runs/<id>/final-html` `available=true` + url
- [ ] 브라우저로 `http://localhost:8000/runs/<id>/final_output.html` 직접 접근 정상
- [ ] 신규 generate (CLI 또는 API) 시 `runs/<new_id>/final_output.html` 자동 생성
- [ ] `pytest backend/tests/api/test_judge_endpoint.py -v` 전체 PASS

### 12-2. 프론트
- [ ] `/run/<id>` 진입 → 상단 3-컬럼 + 하단 탭 동시 표시
- [ ] 하단 "🎯 판정" 탭: 레이더 차트 mount 애니메이션 + 3 카드 카운트업
- [ ] aggregate 점수 카운트업 1.2s 부드럽게
- [ ] outlier 모델 있으면 빨간 border + dot
- [ ] consensus_level 배지 표시
- [ ] "📄 결과물 미리보기" 탭: iframe 정상 로드, 인터랙티브 컴포넌트 동작 (CHECKLIST 체크박스 등)
- [ ] iframe "새 창에서 열기" 버튼 → 별도 탭 열림
- [ ] 모바일 폭(< lg)에서 3 카드 세로 누적, 레이더 차트 height 320px

---

## 13. 시각 임팩트 체크리스트 ("멋지게 보이는 것 다 넣어" 요구사항)

| 항목 | 적용 위치 | 비고 |
|---|---|---|
| 카운트업 애니메이션 | overall, aggregate, 각 축 점수 | useCountUp 훅 |
| Recharts mount 애니메이션 | 레이더 차트 라인·면 | 1.5s ease-out |
| 5축 게이지 mount fill | ModelScoreCard 게이지 width | 0.8s ease-out |
| Stagger fade-in | 헤더 → 차트 → 카드들 | 150ms 간격 |
| Outlier 강조 | 빨간 border + dot + 약한 pulse | 발표 어필 |
| Consensus 색 변화 | high 녹색 / medium 노랑 / low 빨강 | 신호등 메타포 |
| 카드 호버 lift | translate-y-1 + shadow | subtle motion |
| 탭 전환 fade | 200ms | 부드럽게 |
| Aggregate 점수 색 변화 | 8+ green / 6-8 yellow / <6 red | 큰 숫자 임팩트 |
| Tooltip 디테일 | 레이더 호버 시 4개 값 비교 | 정보 밀도 |

⚠️ **과하지 않게**: 모든 효과 200~1500ms 범위. infinite loop 애니메이션은 outlier pulse 정도만.

---

## 14. 미해결 / 다음 단계 이월

- **/admin/prompts 편집기**: 본 명세 범위 외. 마감 후 우선순위 강등 (cut 결정됨).
- **iframe sandbox 정밀화**: prod 배포 시 same-origin 검증. 마감 후.
- **Judge Panel debate simulation 연출** (B3-S3 master spec에 언급됐던 "토론 시뮬레이션 애니메이션"): 본 명세에서 정적 결과 표시만. 시뮬레이션 연출은 마감 후 또는 발표 자료에서 별도.
- **Tablet 폭 (md~lg)**: lg 미만은 모바일 취급. tablet 전용 레이아웃은 폴리싱 단계.

---

## 15. 작업 순서 (Claude Code용)

1. **백엔드 final_output.html 저장 fix** (가장 먼저 — Judge 시각화 검증 시 결과 HTML 필요)
   - `run_manager.py` 수정 + CLI의 wrapper 로직 import 또는 복사
   - 신규 generate 1회 후 `runs/<new_id>/final_output.html` 생성 확인
2. **백엔드 정적 서빙** (`main.py` StaticFiles mount)
3. **백엔드 Judge 스키마 + 엔드포인트 2개** (`schemas/judge.py`, `routers/runs.py`)
4. **백엔드 어댑터** (기존 judge_panel.json 구조 → 새 스키마 변환)
5. **백엔드 테스트 5건 작성 + PASS**
6. **프론트 타입 + API 함수** (`types/judge.ts`, `lib/api.ts`)
7. **프론트 useCountUp 훅**
8. **프론트 RadarChart 컴포넌트** (가장 시각 임팩트 큰 단위 — 먼저 만들고 단독 확인)
9. **프론트 ModelScoreCard**
10. **프론트 JudgePanel 조립**
11. **프론트 FinalHtmlPreview**
12. **프론트 BottomTabs + page.tsx 통합**
13. **`npm run build` 통과 + 변경 파일 목록 출력**
14. **PROGRESS.md 갱신 + 의사결정 로그 1줄 추가**

각 step 짧은 진행 보고. git add/commit 자동 금지.

---

## 16. 환경 / 의존성

### 백엔드
- 추가 dep 없음 (FastAPI StaticFiles는 기본 포함)
- json, pathlib, statistics 표준 라이브러리만 사용 (consensus·outlier 계산)

### 프론트
- `recharts` 추가 필요:
  ```
  cd frontend && npm install recharts
  ```
- 이미 설치돼 있을 가능성 있음 (B3-S3 master spec에 언급됐었음). `package.json` 확인 후 결정.

---

## 17. 회귀 영향 점검

- B3-S3-C 트레이스 뷰어 (상단 3-컬럼): **영향 없음** (page.tsx 에 BottomTabs 추가만, 상단 그대로)
- 메인 페이지 RecentRuns: **영향 없음** (별도 라우트)
- `/api/runs/{id}` 기본 응답: **영향 없음** (judge / final-html 은 별도 엔드포인트)
- 기존 단위 테스트: **영향 없음** (신규 추가만)
- CLI 스크립트: **영향 없음** (run_manager 변경은 API 경로만 영향)

⚠️ 다만 `run_manager.py` 의 `_apply_wrapper` 가 CLI의 wrapper 로직과 **결과가 동일해야 함**. 첫 검증 시 CLI run의 final_output.html 과 API run의 final_output.html 을 diff 떠서 동일 확인.

---

## 18. 작업 종료 조건

- [ ] 백엔드 테스트 5건 PASS + 기존 회귀 0
- [ ] `npm run build` 타입 에러 0
- [ ] API 신규 generate 시 `final_output.html` 자동 생성 (CLI 와 결과 동일)
- [ ] `/api/runs/<id>/judge` 정상 응답
- [ ] `/run/<id>` 페이지에서:
  - 상단 3-컬럼 트레이스 뷰어 정상 (회귀 0)
  - 하단 탭 2개 표시
  - 판정 탭: 레이더 + 3 카드 + 카운트업 + outlier + consensus 모두 동작
  - 결과물 탭: iframe 정상 로드 + 인터랙티브 동작
- [ ] 사용자 수동 검증 §12 통과
- [ ] PROGRESS.md 에 B3-S3-D 완료 체크 + 의사결정 로그 추가
- [ ] 시각 임팩트 §13 체크리스트 통과 (발표 시연 가능 수준)
