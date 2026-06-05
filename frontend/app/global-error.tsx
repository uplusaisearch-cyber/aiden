"use client";

/**
 * 루트 layout 자체에서 터지는 최후 에러 경계 (Next.js App Router 규약).
 *
 * - `app/error.tsx` 는 layout 안쪽 자식 트리 에러만 잡음. 본 파일은 layout/Providers
 *   자체가 죽었을 때의 safety net.
 * - 자체 `<html><body>` 가 필요 (globals.css·dark class·Pretendard CDN 모두 못 받음).
 *   디자인 토큰 의존 0 — 인라인 minimal 스타일로 한국어 안내 + 새로고침 버튼 1개만.
 * - global-error 상황은 layout 자체가 회복 불가일 수 있어 `reset()` 보다
 *   `window.location.reload()` 가 안전.
 */
import { useEffect } from "react";

export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    console.error("[app/global-error]", error);
  }, [error]);

  return (
    <html lang="ko">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "#0a0a0b",
          color: "#f4f4f5",
          fontFamily: "system-ui, -apple-system, sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "16px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: 480 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }} aria-hidden>
            💥
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>
            앱에 치명적인 오류가 발생했습니다
          </h1>
          <p
            style={{
              fontSize: 14,
              marginTop: 8,
              marginBottom: 0,
              color: "#a1a1aa",
              lineHeight: 1.55,
            }}
          >
            페이지를 새로고침해 주세요. 문제가 계속되면 잠시 후 다시 접속 부탁드립니다.
          </p>
          {error.digest && (
            <p
              style={{
                fontSize: 10,
                marginTop: 6,
                marginBottom: 0,
                color: "#71717a",
                fontFamily:
                  "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              }}
            >
              ref: {error.digest}
            </p>
          )}
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              marginTop: 24,
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 600,
              color: "#ffffff",
              background: "#ff2e98",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            새로고침
          </button>
        </div>
      </body>
    </html>
  );
}
