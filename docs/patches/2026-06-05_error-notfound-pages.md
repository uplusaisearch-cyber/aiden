# [PATCH] error.tsx / not-found.tsx 추가 (prerender 안정성 + 배포 안전망)

## Claude Code 복붙 명령

aiden 프론트(Next.js 14 App Router)에 error boundary와 404 커스텀 페이지를 추가한다. 아래 명세대로 진행하고, 기존 design token / 다크모드 / LG U+ 브랜드 스타일을 그대로 따른다. git add·commit은 하지 말 것 (내가 직접 stage·commit).

---

## 목적

1. **Vercel 배포 안전망** — 시연/배포 중 우발적 런타임 에러·잘못된 URL 진입 시, Next.js 기본 흰 화면 대신 브랜드 일관 페이지 노출.
2. **prerender 안정성** — production build에서 에러/404 처리 경로 명시.

> ⚠️ 확인 필요: §5 `npm run build` prerender FAIL이 **이 파일 부재가 직접 원인인지**는 build 로그로 확인. 부재가 원인이 아니어도 배포 안전망 가치는 유효하니 추가는 진행.

---

## 작업 1 — `app/error.tsx` (route segment error boundary)

> 경로는 프로젝트 구조에 맞춤 (`app/` 또는 `src/app/`). **확인 필요.**

요구사항:
- `'use client'` 디렉티브 필수 (error boundary는 클라이언트 컴포넌트)
- props: `{ error: Error & { digest?: string }; reset: () => void }`
- `useEffect`로 `console.error(error)` 로깅
- "다시 시도" 버튼 → `reset()` 호출
- 스타일: 기존 다크모드 배경 + `#ff2e98` 포인트, 중앙 정렬, 기존 폰트/토큰 사용
- 문구 한국어 (예: "문제가 발생했습니다 / 잠시 후 다시 시도해 주세요")

골격:

```tsx
'use client';
import { useEffect } from 'react';

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return ( /* 브랜드 스타일 + reset 버튼 */ );
}
```

## 작업 2 — `app/not-found.tsx` (404)

요구사항:
- 서버 컴포넌트 OK (`'use client'` 불필요)
- `next/link`의 `Link`로 홈("/") 복귀 버튼
- 작업 1과 동일 브랜드/다크모드 스타일 (시각 일관성)
- 문구 한국어 (예: "페이지를 찾을 수 없습니다")

골격:

```tsx
import Link from 'next/link';

export default function NotFound() {
  return ( /* 404 + 홈으로 Link, error.tsx와 동일 톤 */ );
}
```

## 작업 3 (판단) — `app/global-error.tsx`

- root layout 자체 에러용. 있으면 더 견고하지만 **필수 아님**.
- 30분 예산 내에서 작업 1·2 우선. 여유 있으면 추가, 없으면 skip.

---

## 종료 조건

- `app/error.tsx`, `app/not-found.tsx` 생성 완료
- `npm run build` 성공 + prerender 단계 통과
- dev에서 의도적 404 진입(`/존재하지않는경로`) 시 커스텀 404 렌더 확인

---

## 회귀 점검

- 기존 라우트(`/run/<id>` 등) 정상 동작 — error.tsx가 정상 페이지를 가로채지 않음
- 라이브 generate / trace 뷰어 / Judge 시각화 / iframe 회귀 없음
- `npm run build` 기존 PASS 항목 유지

---

## 시각 임팩트 체크리스트 (결선 시연 중 우발 노출 대비)

- [ ] error / not-found 페이지가 다크모드 배경에서 깨지지 않음
- [ ] `#ff2e98` 포인트 컬러 일관 적용 (생뚱맞은 기본 스타일 X)
- [ ] 버튼(다시 시도 / 홈으로) 동작 + 호버 상태 정상
- [ ] 모바일 폭에서도 중앙 정렬 유지 (시연 화면 비율 대비)

---

## 저장 / commit

1. 이 파일을 `docs/patches/2026-06-05_error-notfound-pages.md`로 저장
2. Claude Code 실행 후, B(Gemini 폴백)와 **분리해서** 별도 commit:

```
git add app/error.tsx app/not-found.tsx
git status   # staged 목록 확인
git commit -m "feat(ui): error boundary + 커스텀 404 페이지 추가"
```
