"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app/error]", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
      <div className="text-center">
        <div className="mb-4 text-5xl" aria-hidden>
          ⚠️
        </div>
        <h1 className="font-korean text-xl font-bold text-text-primary">
          예기치 못한 오류가 발생했습니다
        </h1>
        <p className="mt-2 font-korean text-sm text-text-secondary">
          잠시 후 다시 시도해주세요.
        </p>
        {error.digest && (
          <p className="mt-1 font-mono text-[10px] text-text-muted">
            ref: {error.digest}
          </p>
        )}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-md bg-accent-pink px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-pink-hover"
          >
            다시 시도
          </button>
          <Link
            href="/"
            className="rounded-md border border-border-subtle bg-bg-elevated px-4 py-2 text-sm text-text-secondary hover:border-accent-pink"
          >
            ← 메인으로
          </Link>
        </div>
      </div>
    </main>
  );
}
