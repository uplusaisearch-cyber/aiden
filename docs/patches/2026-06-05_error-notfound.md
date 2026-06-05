# AIDEN error.tsx / not-found.tsx 작업 명세

**작성일:** 2026-06-05
**대상:** 프론트엔드 (Next.js 14 App Router)
**목적:** 런타임 에러·404 경계 화면 추가. 빈 화면/디폴트 Next 에러 노출 방지
**전제:** 기존 디자인 토큰·다크모드·브랜드 핑크(`#ff2e98`)·shadcn 컴포넌트 사용. 새 디자인 잡지 말 것.

---

## 1. 사전 확인 (수정 전 보고)

1. `frontend/app/` 라우트 구조 확인 — `layout.tsx`, 기존 `error.tsx`/`not-found.tsx`/`global-error.tsx` 유무.
2. 기존 디자인 토큰 위치(색/폰트/spacing CSS 변수)와 공용 버튼/링크 컴포넌트(shadcn `Button` 등) 경로.
3. App Router 세그먼트 구조 — 에러 경계를 루트에만 둘지, `/runs` 등 주요 세그먼트에도 필요한지.

> 위 확인 후 코드 시작. 기존 error/not-found 가 이미 있으면 덮어쓰지 말고 차이만 보고.

---

## 2. 작업 내용

### 2-1. `app/not-found.tsx` (404)
- Next App Router 규약 파일. 존재하지 않는 경로 진입 시 렌더.
- 내용: 404 표시 + 한국어 안내("페이지를 찾을 수 없습니다") + **홈(`/`)으로 돌아가기** 버튼(`next/link`).
- 기존 레이아웃·다크모드 톤 유지. 브랜드 핑크는 액센트(버튼/포인트)에만.

### 2-2. `app/error.tsx` (런타임 에러 경계)
- `"use client"` 필수. props 로 `error: Error & { digest?: string }`, `reset: () => void` 받음.
- 내용: 에러 안내("문제가 발생했습니다") + **다시 시도**(`reset()`) 버튼 + **홈으로** 링크.
- `useEffect` 로 `console.error(error)` 로깅(개발 편의). 프로덕션에서 raw 스택을 사용자에게 직접 노출하지 말 것 — `error.digest` 만 작게 표기.
- 이 경계는 하위 세그먼트 렌더링 에러를 잡되, **레이아웃 자체의 에러는 못 잡음**(아래 2-3 참고).

### 2-3. `app/global-error.tsx` (루트 레이아웃 에러 — 선택)
- 루트 `layout.tsx` 에서 터지는 에러까지 잡는 최후 경계. `"use client"`, 자체 `<html><body>` 포함해야 함.
- **판단:** 데모 안정성 목적이면 추가 권장(작음). 단 자체 html/body 가 있어 기존 글로벌 스타일이 안 먹을 수 있으니 인라인 최소 스타일로. 공수 부담되면 생략 가능 — 보고 시 추가/생략 의견 제시.

### 2-4. 공통
- 카피는 한국어, 간결하게. 과한 일러스트/애니메이션 금지(번들·산만함).
- 신규 무거운 의존성 추가 금지. 기존 컴포넌트·아이콘(lucide-react 등 이미 설치된 것)만.
- SSR/CSR 경계 준수: `not-found.tsx` 는 서버 컴포넌트 가능, `error.tsx`/`global-error.tsx` 는 클라이언트 컴포넌트.

---

## 3. 종료 조건

- [ ] `app/not-found.tsx` 추가 — 없는 경로 진입 시 커스텀 404 렌더, 홈 버튼 동작.
- [ ] `app/error.tsx` 추가 — 하위 에러 발생 시 경계 렌더, `reset()` 으로 복구 시도 동작.
- [ ] (선택) `global-error.tsx` 추가 또는 생략 사유 보고.
- [ ] 다크모드·브랜드 토큰 일관, 새 색/폰트 추가 없음.
- [ ] 프로덕션에서 raw 스택 미노출(digest 만).

---

## 4. 회귀 점검

- [ ] **백엔드 무변경** (프론트 파일만 diff).
- [ ] 기존 라우트·레이아웃·SSE 스트림·트레이스 뷰어·모달 동작 무영향.
- [ ] 정상 경로(홈, run 생성, 트레이스 뷰어)는 에러 경계와 무관하게 그대로 렌더.
- [ ] `error.tsx` 가 클라이언트 컴포넌트로 정상 빌드(서버 전용 import 없음).
- [ ] npm build PASS, 타입 에러 0.

---

## 5. 검증 방법 (수동)

- 404: 존재하지 않는 URL(예: `/nonexistent`) 진입 → 커스텀 404 확인.
- error: 임시로 한 페이지에서 `throw new Error("test")` 넣어 경계 렌더·`reset()` 확인 후 **반드시 원복**.
- 검증 후 임시 throw 코드 제거 확인.

---

## 6. commit 안내 (작업 후)

```
git status
git diff --stat
```
```
git add frontend/app/not-found.tsx frontend/app/error.tsx
git commit -m "feat(frontend): error/not-found 경계 화면 추가"
```
> `global-error.tsx` 추가했으면 함께 add. 백엔드 파일이 diff 에 잡히면 잘못된 것.
