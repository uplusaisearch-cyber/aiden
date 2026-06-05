"use client";

/**
 * B4-S2 C4: 선정 조합 헤더 카드.
 *
 * 토픽 라벨 + angle/SEG 배지 + 한 줄 요약. run 상단 고정 노출.
 * 메타 출처는 ``useRunStream.planning`` (pipeline_start → RunDetail fallback).
 *
 * angle_directive / segment_persona 는 API 미노출이므로 사용 금지.
 * label 2개만으로 요약 문장 조립.
 */

import type { PlanningMeta } from "@/hooks/useRunStream";
import { CATEGORY_LABEL_MAP, type CategoryId } from "@/lib/constants";

interface Props {
  category: string | null;
  planning: PlanningMeta;
}

interface BadgeProps {
  label: string;
  color: string;
  ariaLabel: string;
}

function Badge({ label, color, ariaLabel }: BadgeProps) {
  return (
    <span
      aria-label={ariaLabel}
      className="inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{
        background: `${color}20`,
        color,
        border: `1px solid ${color}`,
      }}
    >
      {label}
    </span>
  );
}

export function PlanningHeaderCard({ category, planning }: Props) {
  const topicLabel =
    (category && CATEGORY_LABEL_MAP[category as CategoryId]) ||
    category ||
    "자유 토픽";
  const summary = `${planning.segment_label} 독자에게 · ${planning.angle_label} 시각`;

  return (
    <div
      className="mb-3 rounded-lg border px-4 py-3"
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--bg-elevated)",
      }}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span
          className="font-korean text-xs font-medium uppercase tracking-wide"
          style={{ color: "var(--text-muted)" }}
        >
          이번 회차
        </span>
        <span
          className="font-korean text-base font-bold sm:text-lg"
          style={{ color: "var(--text-primary)" }}
        >
          {topicLabel}
        </span>
        <Badge
          label={planning.angle_label}
          color="var(--accent-pink)"
          ariaLabel={`angle: ${planning.angle_label}`}
        />
        <Badge
          label={planning.segment_label}
          color="var(--state-info)"
          ariaLabel={`audience segment: ${planning.segment_label}`}
        />
      </div>
      <p
        className="mt-2 font-korean text-xs"
        style={{ color: "var(--text-secondary)" }}
      >
        {summary}
      </p>
    </div>
  );
}
