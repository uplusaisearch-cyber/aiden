"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useRunStream } from "@/hooks/useRunStream";
import {
  type AgentModelsResponse,
  fetchAgentModels,
  fetchOutputDetail,
} from "@/lib/api";
import {
  fetchPersonas,
  type PersonasData,
} from "@/lib/personas";
import { StagePanel } from "@/components/run/StagePanel";
import { ChatStream } from "@/components/run/ChatStream";
import { NowPlayingPanel } from "@/components/run/NowPlayingPanel";
import { BottomTabs } from "@/components/run/BottomTabs";
import { PlanningHeaderCard } from "@/components/run/PlanningHeaderCard";

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const run = useRunStream(runId);

  const [personas, setPersonas] = useState<PersonasData | null>(null);
  const [personasErr, setPersonasErr] = useState<string | null>(null);
  // B4-S1: 모델 라벨용 — 실패해도 채팅 자체는 동작해야 하므로 silent fallback.
  const [agentModels, setAgentModels] = useState<AgentModelsResponse | null>(
    null,
  );

  // outputs.db (영속) 병렬 조회. 라이브 진행 중인 run 은 upsert 전이라 404 반환 →
  // fallback 게이트가 자동으로 닫힌다. 즉 라이브 run 절대 fallback 모드 진입 X.
  const outputFallbackQ = useQuery({
    queryKey: ["output-fallback", runId],
    queryFn: () => fetchOutputDetail(runId),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    fetchPersonas()
      .then(setPersonas)
      .catch((e: unknown) => {
        setPersonasErr(e instanceof Error ? e.message : "unknown");
      });
    fetchAgentModels()
      .then(setAgentModels)
      .catch(() => {
        // 라벨이 없어도 UI 정상 — 모델 매핑 fetch 실패는 silent.
      });
  }, []);

  // Fallback 모드 판정. outputs.db hit 이 핵심 게이트 — upsert 가 종료 시점에만 일어나므로
  // 라이브 run 은 항상 outputs.db miss → fallback 무발동 보장.
  const outputAvailable =
    outputFallbackQ.isSuccess && !!outputFallbackQ.data?.final_html;
  const shouldFallback =
    outputAvailable &&
    run.messages.length === 0 &&
    (run.status === "completed" || run.fetchNotFound);

  // 파생 상태: completedAgents, iterByAgent
  const { completedAgents, iterByAgent } = useMemo(() => {
    const done = new Set<string>();
    const iter: Record<string, number> = {};
    run.messages.forEach((m) => {
      done.add(m.agent_id);
      if (typeof m.iteration === "number") {
        iter[m.agent_id] = Math.max(iter[m.agent_id] ?? 0, m.iteration);
      }
    });
    return { completedAgents: done, iterByAgent: iter };
  }, [run.messages]);

  // --- Fallback 우선 분기 ---
  // runs/ 디스크가 만료된(또는 처음부터 없는) 완료 run 에 대해 outputs.db final_html 만이라도 표시.
  // 라이브 run 은 outputs.db miss → 이 분기 진입 X. personas 로딩과 무관하게 즉시 렌더.
  if (shouldFallback && outputFallbackQ.data) {
    const detail = outputFallbackQ.data;
    return (
      <main className="mx-auto min-h-screen w-full max-w-5xl p-4">
        <div className="mb-3 flex items-center">
          <Link
            href="/"
            className="font-korean text-[11px] text-text-secondary hover:text-accent-pink"
          >
            ← 메인
          </Link>
        </div>

        <div
          className="mb-4 rounded-lg border p-4"
          style={{
            borderColor: "var(--state-warning)",
            background: "var(--bg-elevated)",
          }}
        >
          <h1 className="font-korean text-base font-bold text-text-primary sm:text-lg">
            📦 {detail.topic ?? "(제목 없음)"}
          </h1>
          <p
            className="mt-1 font-korean text-xs"
            style={{ color: "var(--state-warning)" }}
          >
            ⚠️ 이 run 의 대화 기록은 만료되어 최종 결과물만 표시됩니다.
          </p>
          <p className="mt-0.5 font-mono text-[10px] text-text-muted">
            run: {runId.slice(0, 24)}…
            {detail.created_at ? ` · ${detail.created_at.slice(0, 16)}` : ""}
            {detail.weighted_score != null
              ? ` · ${detail.weighted_score.toFixed(1)} / 100`
              : ""}
          </p>
        </div>

        <div
          className="overflow-hidden rounded-xl bg-white shadow-2xl"
          style={{ border: "1px solid var(--border-strong)" }}
        >
          <iframe
            srcDoc={detail.final_html}
            className="h-[80vh] w-full"
            // srcDoc 은 별도 origin 으로 취급되어 allow-same-origin 없어도 인터랙티브
            // (CHECKLIST/CALCULATOR inline script) 동작. admin/runs preview 와 동일 정책.
            sandbox="allow-scripts"
            title={`Output fallback: ${runId}`}
          />
        </div>
      </main>
    );
  }

  // --- 에러 / 로딩 ---
  if (personasErr) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
        <div className="text-center">
          <div className="mb-4 text-5xl" aria-hidden>
            ⚠️
          </div>
          <h1 className="font-korean text-xl font-bold text-text-primary">
            페르소나 정보를 불러오지 못했습니다
          </h1>
          <p className="mt-2 font-korean text-sm text-text-secondary">
            백엔드 `/api/personas` 응답을 확인해주세요. ({personasErr})
          </p>
          <Link
            href="/"
            className="mt-6 inline-block rounded-md border border-border-subtle bg-bg-elevated px-4 py-2 text-sm text-text-secondary hover:border-accent-pink"
          >
            ← 메인으로
          </Link>
        </div>
      </main>
    );
  }

  if (!personas) {
    return (
      <main className="flex min-h-screen items-center justify-center font-korean text-sm text-text-muted">
        페르소나 로딩 중…
      </main>
    );
  }

  if (run.status === "error") {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
        <div className="text-center">
          <div className="mb-4 text-5xl" aria-hidden>
            🚫
          </div>
          <h1 className="font-korean text-xl font-bold text-text-primary">
            스트림 연결 실패
          </h1>
          <p className="mt-2 font-korean text-sm text-state-danger">
            {run.error ?? "백엔드 SSE 엔드포인트를 확인해주세요."}
          </p>
          <p className="mt-1 font-mono text-xs text-text-muted">
            session: {runId}
          </p>
          <Link
            href="/"
            className="mt-6 inline-block rounded-md border border-border-subtle bg-bg-elevated px-4 py-2 text-sm text-text-secondary hover:border-accent-pink"
          >
            ← 메인으로
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4">
      {/* 좌상단 복귀 동선 — 풀폭 슬림 top bar (그리드 위 additive) */}
      <div className="mb-2 flex items-center">
        <Link
          href="/"
          className="font-korean text-[11px] text-text-secondary hover:text-accent-pink"
        >
          ← 메인
        </Link>
      </div>

      {/* B4-S2 C4: 선정 조합 헤더 카드 — planning 메타 있을 때만 렌더 (폴백/과거 run 비렌더). */}
      {run.planning && (
        <PlanningHeaderCard category={run.category} planning={run.planning} />
      )}

      {/* 상단 3-컬럼 (B3-S3-C 트레이스 뷰어 — 회귀 0 유지) */}
      <div className="grid h-[70vh] grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_320px]">
        <aside className="overflow-y-auto rounded-lg border border-border-subtle bg-bg-primary p-3">
          <StagePanel
            personasData={personas}
            currentAgent={run.currentAgent}
            completedAgents={completedAgents}
            iterByAgent={iterByAgent}
          />
        </aside>

        <section className="flex min-h-0 flex-col rounded-lg border border-border-subtle bg-bg-primary p-3">
          <header className="mb-2 flex items-center gap-3">
            <div className="min-w-0">
              <h1 className="font-korean text-base font-bold text-text-primary">
                Run {runId.slice(0, 18)}…
              </h1>
              <p className="font-mono text-[10px] text-text-muted">
                {statusLabel(run.status)} · 메시지 {run.messages.length}건
              </p>
            </div>
          </header>
          <div className="min-h-0 flex-1">
            <ChatStream
              messages={run.messages}
              personas={personas.personas}
              agentModels={agentModels?.newsroom}
            />
          </div>
        </section>

        <aside className="overflow-y-auto rounded-lg border border-border-subtle bg-bg-primary p-3">
          <NowPlayingPanel run={run} personasData={personas} />
        </aside>
      </div>

      {/* B3-S3-D — 하단 탭 (판정 + 결과물 미리보기) */}
      <BottomTabs runId={runId} defaultTab="judge" />
    </main>
  );
}

function statusLabel(s: string): string {
  switch (s) {
    case "connecting":
      return "연결 중";
    case "streaming":
      return "스트리밍";
    case "completed":
      return "완료";
    case "error":
      return "오류";
    default:
      return s;
  }
}
