"use client";

import { useQuery } from "@tanstack/react-query";

import { API_BASE, fetchFinalHtmlMeta, fetchOutputDetail } from "@/lib/api";
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

function NotAvailable({ message, polling }: { message?: string; polling?: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div
        className="mb-4 flex h-16 w-16 items-center justify-center rounded-full text-3xl"
        style={{
          background: "var(--bg-elevated)",
          color: "var(--text-muted)",
        }}
      >
        {polling ? "⏳" : "📄"}
      </div>
      <p
        className="text-sm font-semibold"
        style={{ color: "var(--text-secondary)" }}
      >
        {polling
          ? "최종 콘텐츠 준비 중"
          : "최종 콘텐츠가 아직 준비되지 않았습니다."}
      </p>
      <p
        className="mt-1 max-w-md text-xs leading-relaxed"
        style={{ color: "var(--text-muted)" }}
      >
        {message ??
          (polling
            ? "9 에이전트 파이프라인이 끝나면 자동으로 iframe 미리보기로 전환됩니다."
            : "파이프라인이 완료된 후 다시 확인해주세요.")}
      </p>
      {polling && (
        <div className="mt-4 flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ background: "var(--accent-pink)" }}
          />
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ background: "var(--accent-pink)", animationDelay: "200ms" }}
          />
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ background: "var(--accent-pink)", animationDelay: "400ms" }}
          />
        </div>
      )}
    </div>
  );
}

export function FinalHtmlPreview({ runId }: Props) {
  const metaQ = useQuery<FinalHtmlMeta>({
    queryKey: ["final-html", runId],
    queryFn: () => fetchFinalHtmlMeta(runId),
    retry: false,
    // 진행 중 run: final_output.html 이 생길 때까지 자동 폴링 (15초 간격).
    // available:true 도착 시 자동 정지 → 완료된 run 에서는 1회만 fetch.
    refetchInterval: (query) =>
      query.state.data?.available ? false : 15_000,
    staleTime: 60_000,
  });

  // 디스크 final_output.html 부재 (또는 session_exists false) 시 outputs.db 영속본으로 폴백.
  // metaQ 가 available:true 되면 enabled=false 로 자동 정지. 라이브 run 은 outputs.db 가
  // 완료 전엔 miss 이므로 자연스럽게 "준비 중" UI 가 유지된다.
  const outputsQ = useQuery({
    queryKey: ["output-fallback", runId],
    queryFn: () => fetchOutputDetail(runId),
    retry: false,
    enabled: !metaQ.data?.available,
    staleTime: 60_000,
  });

  if (metaQ.isLoading && outputsQ.isLoading) return <Skeleton />;

  // 1차: 디스크 final_output.html
  if (metaQ.data?.available && metaQ.data.url) {
    return <DiskPreview url={metaQ.data.url} sizeBytes={metaQ.data.size_bytes} />;
  }

  // 2차: outputs.db 영속본 (디스크 wipe 또는 저장 누락 케이스 — PROGRESS L240 완화).
  if (outputsQ.data?.final_html) {
    return <FallbackPreview html={outputsQ.data.final_html} runId={runId} />;
  }

  // 둘 다 없음: 라이브 폴링 상태 또는 진짜 부재.
  // metaQ error + outputsQ error 면 메시지 합쳐 노출 — 그 외엔 폴링 UI.
  const metaErr = metaQ.error instanceof Error ? metaQ.error.message : null;
  const outErr = outputsQ.error instanceof Error ? outputsQ.error.message : null;
  if (metaErr && outErr) {
    return <NotAvailable message={`${metaErr} / outputs.db: ${outErr}`} />;
  }
  return <NotAvailable polling />;
}

function DiskPreview({
  url,
  sizeBytes,
}: {
  url: string;
  sizeBytes: number | null;
}) {
  const src = `${API_BASE}${url}`;
  const sizeKB = sizeBytes != null ? (sizeBytes / 1024).toFixed(1) : "?";

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

function FallbackPreview({ html, runId }: { html: string; runId: string }) {
  const sizeKB = (new Blob([html]).size / 1024).toFixed(1);
  return (
    <div className="p-6 animate-in fade-in duration-500">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            최종 콘텐츠
            <span
              className="ml-2 align-middle text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--state-warning)" }}
              title="디스크 final_output.html 부재 — outputs.db 영속본으로 폴백"
            >
              영속본
            </span>
          </h2>
          <p
            className="mt-1 text-xs tabular-nums"
            style={{ color: "var(--text-muted)" }}
          >
            {sizeKB} KB · outputs.db
          </p>
        </div>
        <a
          href={`${API_BASE}/api/outputs/${runId}/download`}
          download
          className="rounded-lg px-3 py-2 text-xs font-semibold transition-colors hover:bg-white/10"
          style={{
            color: "var(--text-primary)",
            border: "1px solid var(--border-strong)",
          }}
        >
          다운로드 ↓
        </a>
      </header>
      <div
        className="overflow-hidden rounded-xl bg-white shadow-2xl"
        style={{ border: "1px solid var(--border-strong)" }}
      >
        <iframe
          srcDoc={html}
          className="h-[800px] w-full"
          // srcDoc 은 별도 origin 으로 취급되어 allow-same-origin 없어도 인터랙티브
          // (CHECKLIST/CALCULATOR inline script) 동작 — admin/runs preview 와 동일.
          sandbox="allow-scripts"
          title="Final content fallback preview"
        />
      </div>
    </div>
  );
}
