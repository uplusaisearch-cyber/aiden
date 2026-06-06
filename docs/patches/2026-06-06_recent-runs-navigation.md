# 패치: 메인 "최근 실행" 카드 → /run/{run_id} 채팅 재진입 + final HTML fallback

작성일: 2026-06-06
대상: frontend (메인 page / recent-runs / run 페이지) · backend (outputs 라우터)
분류: 폴리싱 (P1, 마감 6/8). 네비게이션 IA 정리 + 빈 화면 차단.

---

## 0. 현황 / 제약 (C1~C3 진단 기반)

- **현재 카드 동선**: 메인 카드 클릭 → `/admin/runs?preview=${sessionId}` 모달 (outputs.db final_html iframe). `/run/{run_id}` 아님.
- **두 저장소 분리**:
  - outputs.db (SQLite, Volume 영속): topic/score/**final_html**. 정상완료+final_html 시만 적재.
  - `runs/<session>/` (디스크, **Railway ephemeral — 재배포 휘발**): 9에이전트+저지 채팅 전체.
- **`/run/{run_id}` 복원**: 마운트 시 `runs/` 디스크 read (fetch-then-stream). 디스크 부재 시 채팅·final탭 **둘 다 사망**. outputs.db final_html은 이 경로에서 현재 미사용.

---

## 1. 목표

1. 메인 카드 클릭 동선 변경: `/admin/runs?preview=` → **`/run/{run_id}`** (채팅 과정 다시보기)
2. `/run/{run_id}` fallback: `runs/` 부재 시 outputs.db final_html 표시 + 만료 안내 (**빈 화면 차단**)
3. 메인 "최근 실행" 6개 제한 → 더보기
4. "전체 보기" 버튼 라벨을 도착지(`/admin/runs` "출력 히스토리")와 통일

비목표: `runs/` 영속화(Volume) = v2. 채팅 영구 복원은 범위 외.

---

## 2. 작업 단위

### A. 카드 동선 변경
- `recent-runs.tsx:80` 클릭 핸들러: `/admin/runs?preview=${sessionId}` → `/run/${sessionId}`
- admin/runs 자체는 무변경 (영구 결과물 + 다운로드 페이지로 유지)

### B. `/run/{run_id}` final HTML fallback (빈 화면 차단 핵심)
- 프론트: `fetchRunDetail` 결과가 404 OR (messages 0건 AND status terminal) → **fallback 모드** 진입
  - fallback UI: outputs.db final_html iframe 렌더 + 안내 배너 "이 run의 대화 기록은 만료되어 최종 결과물만 표시됩니다."
  - 데이터: `GET /api/outputs/{run_id}` 의 final_html 컬럼 (이미 존재 — outputs_store.py:172). 응답 형태 확인 필요.
- BottomTabs final 탭: 기존 `/api/runs/{id}/final-html`(runs/ 디스크 의존) 404 시 → outputs.db final_html로 fallback 추가
- **라이브 run(비terminal)은 절대 fallback 타면 안 됨** — 기존 SSE 연결 분기 보존

### C. 6개 → 더보기
- `page.tsx:46` `fetchOutputs(6)` → 초기 6 + "더보기" 클릭 시 추가 로드
- `GET /api/outputs` 의 limit/offset(또는 cursor) 지원 여부 확인 필요. 미지원이면 (a) 백엔드 param 추가 or (b) 전체 받아 프론트 slice 중 결정 — db 규모 작으면 (b)도 허용

### D. 라벨 통일
- "전체 보기" 버튼 텍스트 → **"저장된 출력 히스토리 →"** (디폴트안, 변경 가능)
- 도착지 `/admin/runs` 페이지 제목 "출력 히스토리"와 일관

---

## 3. 종료 조건

- 카드 클릭 → `/run/{run_id}` 이동.
  - `runs/` 살아있음 → 채팅 과정 전체 복원 ✅
  - `runs/` 부재(재배포 후) → final_html + 만료 안내, **빈 화면("페르소나 로딩 중…" 멈춤) 0건**
- 라이브 진행중 run 진입 → 기존대로 실시간 SSE (fallback 미발동)
- 더보기 동작 (6개 → 추가 로드)
- "전체 보기" 버튼 → `/admin/runs`, 라벨 일치

---

## 4. 회귀 점검

- [ ] **라이브 run `/run/{run_id}` 정상** (비terminal 시 SSE 연결 유지, fallback 분기에 안 걸림 — 최우선)
- [ ] terminal run 채팅 복원 정상 (`runs/` 살아있을 때 기존과 동일)
- [ ] admin/runs preview 모달 기존대로 동작 (동선 변경이 admin 영향 0)
- [ ] outputs.db 적재/조회 정상 (run 완료 시 upsert 무변경)
- [ ] 메인 카드 초기 6개 노출 유지
- [ ] `appendUnique` dedupe 정상 (setState 순수성 — 기존 이슈 재발 금지)
- [ ] fallback 분기가 정상 채팅 케이스를 오판해 결과물만 띄우지 않는지 (messages 0 판정 타이밍 주의)

## 5. 시각 임팩트 체크리스트

- [ ] fallback 안내 배너 명확 (왜 채팅 없고 결과물만인지 1줄 설명)
- [ ] 더보기 버튼 `#ff2e98` / 다크 / 모바일 일관
- [ ] 카드 hover·cursor affordance (클릭 가능 표시)
- [ ] "저장된 출력 히스토리" 버튼이 일반 카드와 시각 구분

---

## 6. 확인 필요 (Claude Code)

- `GET /api/outputs` limit/offset 페이지네이션 지원? (미지원 시 C 방식 결정)
- `GET /api/outputs/{run_id}` 응답에 final_html 포함되는지 / 형태(full html string)
- `/run/{run_id}` 페이지에서 fallback 분기 삽입 위치 (useRunStream.ts vs 페이지 컴포넌트)
- BottomTabs final 탭 fallback 추가 시 judges.py 라우터 영향 범위
- 존재하지 않는 run_id 직접 진입 → not-found.tsx 와 묶을지 (마감 잔여 항목과 연계 가능)
