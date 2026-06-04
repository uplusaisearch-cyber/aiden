# final-html iframe 미리보기 자동 폴링 적용

**작성일**: 2026-06-05
**범위**: B3-S3-D 후속 폴리싱 — `FinalHtmlPreview` 에 `JudgePanel` 과 동일한 자동 폴링 패턴 적용
**관련 commit**: 이 패치 (별도 single commit, 사용자 직접 stage·commit)
**선행**: `ea2d3b9 fix(frontend): Judge Panel pending UI + auto-poll for in-progress runs`

---

## 1. 문제

진행 중인 run 에서 사용자가 하단 "📄 결과물 미리보기" 탭을 미리 누를 경우:

- 백엔드 `/api/runs/{id}/final-html` 은 `{available: false, url: null, size_bytes: null}` 200 응답
- 프론트는 `NotAvailable` UI 정적 표시 (`📄 + "최종 콘텐츠가 아직 준비되지 않았습니다."`)
- **파이프라인 완료 후에도 사용자가 새로고침 또는 탭 재진입을 하지 않으면 iframe 영역이 갱신되지 않음**

`JudgePanel` 은 이미 `refetchInterval: 15_000` + `JudgePanelPending` 으로 라이브 발견-fix
사이클 (commit `ea2d3b9`) 에서 동일 패턴 적용 완료. 결과물 탭만 동일 패턴이 빠져 있음.

---

## 2. 변경 사항

**파일 1건만 수정**: `frontend/components/run/FinalHtmlPreview.tsx`

### 2-1. useQuery 옵션 변경

```tsx
const { data, isLoading, error } = useQuery<FinalHtmlMeta>({
  queryKey: ["final-html", runId],
  queryFn: () => fetchFinalHtmlMeta(runId),
  retry: false,                                    // 변경: 1 → false
  refetchInterval: (query) =>                       // 신규
    query.state.data?.available ? false : 15_000,
  staleTime: 60_000,                                // 변경: 30_000 → 60_000 (Judge 와 정렬)
});
```

폴링 정지 조건: `query.state.data?.available === true`
→ **완료된 run 은 첫 fetch 직후 폴링 자동 정지** (1회만 fetch). 진행 중 run 은 15초 간격
재시도, `final_output.html` 작성되면 다음 사이클에 `available: true` 도착 → 즉시 정지 +
iframe 렌더.

### 2-2. NotAvailable UI 두 가지 mode 지원

```tsx
<NotAvailable polling />   // 진행 중: ⏳ + 3-dot pulse + "9 에이전트 파이프라인 끝나면 자동 전환"
<NotAvailable />            // 정적: 📄 + "파이프라인이 완료된 후 다시 확인"
```

- `polling` prop: `available:false` 200 응답 시 true (= 폴링 사이클 표시)
- 기존 정적 fallback (error 핸들러 분기) 는 그대로 — `<NotAvailable message={...} />`

3-dot pulse 애니메이션은 `JudgePanelPending` 과 동일 디자인 (액센트 핑크, 200/400ms stagger).

### 2-3. error 분기 NotAvailable 호출 변경 없음

`error instanceof Error` 케이스 (네트워크 / 500) 는 polling false 유지 — 진짜 에러
상황 (백엔드 다운 등). 일관성 위해 retry 제거했지만 사용자가 탭 재진입 시 1회 재시도됨.

---

## 3. 요구사항 매핑

| # | 요구사항 | 구현 |
|---|---|---|
| 1 | refetchInterval: 15_000, available:true 시 정지 | `(query) => query.state.data?.available ? false : 15_000` |
| 2 | retry: false | 적용 |
| 3 | 진행 중 → 완료 자동 전환 | available:false → 15s 폴링 → available:true 도착 → iframe 렌더 (사용자 새로고침 불필요) |
| 4 | 완료된 run 즉시 렌더 + 불필요 폴링 X | 첫 fetch 결과 available:true → refetchInterval false 반환 → 폴링 안 시작 |

---

## 4. 회귀 점검

| 항목 | 확인 |
|---|---|
| 완료된 run 에서 결과물 탭 정상 렌더 | ✅ available:true 첫 fetch → iframe 즉시 렌더. refetchInterval false → 폴링 없음 |
| `available:false` 200 응답 NotAvailable UI | ✅ `<NotAvailable polling />` 로 강화 (회귀 없음, UI 더 친절) |
| Judge 폴링 (`["judge", runId]`) 과 중복 충돌 | ✅ queryKey 별개 (`["final-html", runId]`) → 독립 큐, 충돌 없음 |
| 네트워크 에러 / 500 케이스 | ✅ `<NotAvailable message={err.message} />` 분기 유지, polling=false |
| Build / Type check | ✅ `npx tsc --noEmit` 통과 |

---

## 5. 미해결 / 이월

- **JudgePanel 패턴과 코드 중복**: `JudgePanelPending` / `NotAvailable polling` 의 ⏳ + 3-dot
  pulse + 안내 문구 구조가 거의 동일. 추후 공통 컴포넌트 `<PendingPanel ... />` 로 추출
  여지 있음. 본 패치 범위 외 (현재 2건 = DRY 임계치 미만).
- **폴링 간격 통일 15s**: Judge 와 final-html 둘 다 15초. 파이프라인 평균 소요 ~6분 기준
  넉넉. 발표 데모 시 더 짧게 (5초) 가도 무방.
- **백엔드 SSE pipeline_complete 후 invalidateQueries 자동 호출**: 현재 미적용. SSE 가
  완료 이벤트 발행 시 React Query 캐시를 invalidate 하면 폴링 사이클 기다릴 필요 없음.
  본 패치 범위 외. 별도 patch 고려.

---

## 6. 작업 종료 조건

- [x] FinalHtmlPreview 폴링 적용
- [x] 완료 run 폴링 안 도는지 query.state.data?.available 분기로 보장
- [x] NotAvailable polling 모드 추가 (UX)
- [x] `npx tsc --noEmit` 통과
- [x] docs/patches/2026-06-05_final-html-polling.md 작성
- [ ] 사용자 stage + commit (claude 직접 X)
