"use client";

import { useQuery } from "@tanstack/react-query";

import { useCountUp } from "@/hooks/useCountUp";
import { fetchJudge } from "@/lib/api";
import type { ConsensusLevel, JudgeResult } from "@/types/judge";

import { ModelScoreCard } from "./ModelScoreCard";
import { RadarChart } from "./RadarChart";

interface Props {
  runId: string;
}

const CONSENSUS_TEXT: Record<ConsensusLevel, { label: string; color: string }> = {
  high: { label: "합의 높음", color: "var(--state-success)" },
  medium: { label: "합의 보통", color: "var(--state-warning)" },
  low: { label: "합의 낮음", color: "var(--state-danger)" },
};

function ConsensusBadge({ level }: { level: ConsensusLevel }) {
  const meta = CONSENSUS_TEXT[level];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{
        background: `${meta.color}20`,
        color: meta.color,
        border: `1px solid ${meta.color}`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: meta.color }}
      />
      {meta.label}
    </span>
  );
}

function aggregateColor(score: number): string {
  if (score >= 8) return "var(--state-success)";
  if (score >= 6) return "var(--state-warning)";
  return "var(--state-danger)";
}

function AggregateOverall({ value }: { value: number }) {
  const animated = useCountUp(value, 1400);
  return (
    <div className="flex flex-col items-end">
      <span
        className="text-6xl font-extrabold tabular-nums leading-none transition-colors duration-300"
        style={{ color: aggregateColor(value) }}
      >
        {animated.toFixed(1)}
      </span>
      <span
        className="mt-1 text-xs font-medium tracking-wide"
        style={{ color: "var(--text-muted)" }}
      >
        AGGREGATE / 10
      </span>
    </div>
  );
}

function JudgePanelSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div
            className="h-6 w-48 animate-pulse rounded"
            style={{ background: "var(--bg-elevated)" }}
          />
          <div
            className="h-3 w-64 animate-pulse rounded"
            style={{ background: "var(--bg-elevated)" }}
          />
        </div>
        <div
          className="h-16 w-24 animate-pulse rounded"
          style={{ background: "var(--bg-elevated)" }}
        />
      </div>
      <div
        className="h-[400px] animate-pulse rounded-lg"
        style={{ background: "var(--bg-elevated)" }}
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-80 animate-pulse rounded-xl"
            style={{ background: "var(--bg-elevated)" }}
          />
        ))}
      </div>
    </div>
  );
}

function JudgePanelError({ message }: { message: string }) {
  return (
    <div
      className="m-6 rounded-lg p-6 text-sm"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--state-danger)",
        color: "var(--text-secondary)",
      }}
    >
      <p className="mb-1 font-semibold" style={{ color: "var(--state-danger)" }}>
        Judge Panel 결과를 불러오지 못했습니다.
      </p>
      <p className="text-xs">{message}</p>
    </div>
  );
}

export function JudgePanel({ runId }: Props) {
  const { data, isLoading, error } = useQuery<JudgeResult>({
    queryKey: ["judge", runId],
    queryFn: () => fetchJudge(runId),
    retry: 1,
    staleTime: 60_000,
  });

  if (isLoading) return <JudgePanelSkeleton />;
  if (error || !data) {
    return <JudgePanelError message={error instanceof Error ? error.message : "unknown"} />;
  }

  return (
    <div className="space-y-6 p-6">
      {/* 헤더 — fade in stagger 1 */}
      <header
        className="flex items-start justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-500"
      >
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            3-Model Judge Panel
          </h2>
          <p
            className="mt-1 flex flex-wrap items-center gap-2 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            <span>Gemini + GPT + Claude 동시 평가</span>
            <span style={{ color: "var(--text-muted)" }}>·</span>
            <span>{data.evaluations.length} models</span>
            <ConsensusBadge level={data.consensus_level} />
          </p>
        </div>
        <AggregateOverall value={data.aggregate_overall} />
      </header>

      {/* 레이더 차트 — stagger 2 */}
      <div
        className="rounded-xl p-4 animate-in fade-in slide-in-from-bottom-2 duration-700 delay-150 fill-mode-both"
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div className="hidden lg:block">
          <RadarChart
            evaluations={data.evaluations}
            aggregate={data.aggregate}
            height={400}
          />
        </div>
        <div className="lg:hidden">
          <RadarChart
            evaluations={data.evaluations}
            aggregate={data.aggregate}
            height={320}
          />
        </div>
      </div>

      {/* 3 모델 카드 — stagger 3 */}
      <div className="grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-bottom-3 duration-700 delay-300 fill-mode-both lg:grid-cols-3">
        {data.evaluations.map((ev) => (
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
