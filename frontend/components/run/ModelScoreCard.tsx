"use client";

import { useState } from "react";

import { useCountUp } from "@/hooks/useCountUp";
import {
  AXIS_META,
  type ModelEvaluation,
  MODEL_COLORS,
  MODEL_DISPLAY_NAME,
} from "@/types/judge";

interface Props {
  evaluation: ModelEvaluation;
  aggregateOverall: number;
}

function diffLabel(delta: number): { text: string; color: string } {
  const abs = Math.abs(delta);
  if (abs < 0.05) return { text: "≈ 평균", color: "var(--text-muted)" };
  if (delta > 0) {
    return {
      text: `↑ +${abs.toFixed(1)} vs 평균`,
      color: "var(--state-success)",
    };
  }
  return {
    text: `↓ -${abs.toFixed(1)} vs 평균`,
    color: "var(--state-warning)",
  };
}

function AxisGauge({ axis, score }: { axis: string; score: number }) {
  // mount transition: width 0 → score*10% via CSS keyframe (Tailwind transition-all 0.8s)
  const widthPct = Math.max(0, Math.min(10, score)) * 10;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        className="w-20 shrink-0 truncate"
        style={{ color: "var(--text-secondary)" }}
      >
        {axis}
      </span>
      <div
        className="relative h-2 flex-1 overflow-hidden rounded-full"
        style={{ background: "var(--bg-elevated)" }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-700 ease-out"
          style={{
            width: `${widthPct}%`,
            background:
              "linear-gradient(90deg, var(--accent-pink) 0%, var(--accent-pink-hover) 100%)",
          }}
        />
      </div>
      <span
        className="w-8 shrink-0 text-right tabular-nums"
        style={{ color: "var(--text-primary)" }}
      >
        {score.toFixed(1)}
      </span>
    </div>
  );
}

export function ModelScoreCard({ evaluation, aggregateOverall }: Props) {
  const animatedOverall = useCountUp(evaluation.overall, 1200);
  const [expanded, setExpanded] = useState(false);
  const color = MODEL_COLORS[evaluation.model_id];
  const delta = diffLabel(evaluation.overall - aggregateOverall);

  const COMMENT_PREVIEW_LEN = 180;
  const commentNeedsToggle = evaluation.comment.length > COMMENT_PREVIEW_LEN;
  const visibleComment = expanded || !commentNeedsToggle
    ? evaluation.comment
    : `${evaluation.comment.slice(0, COMMENT_PREVIEW_LEN)}…`;

  return (
    <article
      className="group relative overflow-hidden rounded-xl p-5 transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl"
      style={{
        background: "var(--bg-elevated)",
        border: evaluation.is_outlier
          ? "2px solid var(--state-danger)"
          : "1px solid var(--border-subtle)",
      }}
    >
      {/* 좌측 액센트 라인 */}
      <span
        className="absolute inset-y-0 left-0 w-1"
        style={{ background: color }}
        aria-hidden
      />

      {/* 헤더: 모델명 + outlier 표시 */}
      <header className="mb-3 flex items-center gap-2">
        <span
          className="inline-block h-3 w-3 rounded-full"
          style={{ background: color }}
        />
        <h3
          className="text-base font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          {MODEL_DISPLAY_NAME[evaluation.model_id]}
        </h3>
        {evaluation.is_outlier && (
          <span
            className="ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
            style={{
              background: "var(--state-danger)",
              color: "white",
            }}
            title="다른 평가자 대비 ±1.5σ 이상 격차"
          >
            <span
              className="h-1.5 w-1.5 animate-pulse rounded-full bg-white"
              aria-hidden
            />
            OUTLIER
          </span>
        )}
      </header>
      <p
        className="mb-4 text-[11px] tabular-nums"
        style={{ color: "var(--text-muted)" }}
      >
        {evaluation.model_name}
      </p>

      {/* Overall 점수 (카운트업) */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span
            className="text-5xl font-extrabold tabular-nums leading-none"
            style={{ color: "var(--text-primary)" }}
          >
            {animatedOverall.toFixed(1)}
          </span>
          <span
            className="text-base tabular-nums"
            style={{ color: "var(--text-muted)" }}
          >
            / 10
          </span>
        </div>
        <p
          className="mt-1 text-xs font-semibold tabular-nums"
          style={{ color: delta.color }}
        >
          {delta.text}
        </p>
      </div>

      {/* 5축 게이지 */}
      <div
        className="my-4 border-t pt-4"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div className="space-y-2">
          {AXIS_META.map(({ key, label }) => (
            <AxisGauge
              key={key}
              axis={label}
              score={evaluation.scores[key]}
            />
          ))}
        </div>
      </div>

      {/* 코멘트 */}
      <div
        className="mt-4 border-t pt-3"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <p
          className="text-xs leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          {visibleComment}
        </p>
        {commentNeedsToggle && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-[11px] font-semibold hover:underline"
            style={{ color: "var(--accent-pink)" }}
          >
            {expanded ? "접기" : "더보기"}
          </button>
        )}
      </div>
    </article>
  );
}
