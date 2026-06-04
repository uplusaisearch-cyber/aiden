"use client";

import { useQuery } from "@tanstack/react-query";

import { API_BASE, fetchFinalHtmlMeta } from "@/lib/api";
import type { FinalHtmlMeta } from "@/types/judge";

interface Props {
  runId: string;
}

function Skeleton() {
  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div
          className="h-6 w-32 animate-pulse rounded"
          style={{ background: "var(--bg-elevated)" }}
        />
        <div
          className="h-9 w-40 animate-pulse rounded"
          style={{ background: "var(--bg-elevated)" }}
        />
      </div>
      <div
        className="h-[800px] animate-pulse rounded-lg"
        style={{ background: "var(--bg-elevated)" }}
      />
    </div>
  );
}

function NotAvailable({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div
        className="mb-4 flex h-16 w-16 items-center justify-center rounded-full text-3xl"
        style={{
          background: "var(--bg-elevated)",
          color: "var(--text-muted)",
        }}
      >
        📄
      </div>
      <p
        className="text-sm font-semibold"
        style={{ color: "var(--text-secondary)" }}
      >
        최종 콘텐츠가 아직 준비되지 않았습니다.
      </p>
      <p
        className="mt-1 text-xs"
        style={{ color: "var(--text-muted)" }}
      >
        {message ?? "파이프라인이 완료된 후 다시 확인해주세요."}
      </p>
    </div>
  );
}

export function FinalHtmlPreview({ runId }: Props) {
  const { data, isLoading, error } = useQuery<FinalHtmlMeta>({
    queryKey: ["final-html", runId],
    queryFn: () => fetchFinalHtmlMeta(runId),
    retry: 1,
    staleTime: 30_000,
  });

  if (isLoading) return <Skeleton />;
  if (error) {
    return (
      <NotAvailable
        message={error instanceof Error ? error.message : "메타 조회 실패"}
      />
    );
  }
  if (!data?.available || !data.url) return <NotAvailable />;

  const src = `${API_BASE}${data.url}`;
  const sizeKB = data.size_bytes != null ? (data.size_bytes / 1024).toFixed(1) : "?";

  return (
    <div className="p-6 animate-in fade-in duration-500">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            최종 콘텐츠
          </h2>
          <p
            className="mt-1 text-xs tabular-nums"
            style={{ color: "var(--text-muted)" }}
          >
            {sizeKB} KB · 플러스탭 스탠드얼론 HTML
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg px-3 py-2 text-xs font-semibold transition-colors hover:bg-white/10"
            style={{
              color: "var(--text-primary)",
              border: "1px solid var(--border-strong)",
            }}
          >
            새 창에서 열기 ↗
          </a>
        </div>
      </header>
      <div
        className="overflow-hidden rounded-xl bg-white shadow-2xl"
        style={{ border: "1px solid var(--border-strong)" }}
      >
        <iframe
          src={src}
          className="h-[800px] w-full"
          // CHECKLIST / CALCULATOR 인터랙티브 컴포넌트는 inline script 사용 → allow-scripts 필수.
          // backend StaticFiles 가 같은 origin (NEXT_PUBLIC_API_BASE) 으로 서빙 → allow-same-origin 안전.
          sandbox="allow-scripts allow-same-origin"
          title="Final content preview"
        />
      </div>
    </div>
  );
}
