"use client";

import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as RechartsRadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import {
  AXIS_META,
  type CriterionScore,
  type ModelEvaluation,
  MODEL_COLORS,
  MODEL_DISPLAY_NAME,
} from "@/types/judge";

interface Props {
  evaluations: ModelEvaluation[];
  aggregate: CriterionScore;
  height?: number;
}

interface RadarRow {
  axis: string;
  gemini?: number;
  gpt?: number;
  claude?: number;
  aggregate: number;
}

const AGGREGATE_COLOR = "#ff2e98"; // var(--accent-pink) — Judge mean 강조

function buildRows(evaluations: ModelEvaluation[], aggregate: CriterionScore): RadarRow[] {
  const byId = Object.fromEntries(evaluations.map((e) => [e.model_id, e]));
  return AXIS_META.map(({ key, label }) => ({
    axis: label,
    gemini: byId.gemini?.scores[key],
    gpt: byId.gpt?.scores[key],
    claude: byId.claude?.scores[key],
    aggregate: aggregate[key],
  }));
}

interface TooltipPayloadItem {
  dataKey: string;
  color: string;
  value: number | string;
}

interface TooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs shadow-lg"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-strong)",
        color: "var(--text-primary)",
      }}
    >
      <div className="mb-1 font-bold">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color }}
          />
          <span style={{ color: "var(--text-secondary)" }}>
            {p.dataKey === "aggregate"
              ? "평균"
              : MODEL_DISPLAY_NAME[p.dataKey as keyof typeof MODEL_DISPLAY_NAME]}
          </span>
          <span className="ml-auto font-semibold tabular-nums">
            {typeof p.value === "number" ? p.value.toFixed(1) : "-"}
          </span>
        </div>
      ))}
    </div>
  );
}

export function RadarChart({ evaluations, aggregate, height = 400 }: Props) {
  const data = buildRows(evaluations, aggregate);
  const hasGemini = evaluations.some((e) => e.model_id === "gemini");
  const hasGpt = evaluations.some((e) => e.model_id === "gpt");
  const hasClaude = evaluations.some((e) => e.model_id === "claude");

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadarChart data={data} margin={{ top: 20, right: 32, bottom: 20, left: 32 }}>
          <PolarGrid gridType="polygon" stroke="var(--border-subtle)" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{
              fill: "var(--text-secondary)",
              fontSize: 13,
              fontFamily: "var(--font-pretendard)",
            }}
          />
          <PolarRadiusAxis
            domain={[0, 10]}
            tickCount={6}
            tick={{ fill: "var(--text-muted)", fontSize: 10 }}
            stroke="var(--border-subtle)"
          />
          {hasGemini && (
            <Radar
              name="Gemini"
              dataKey="gemini"
              stroke={MODEL_COLORS.gemini}
              fill={MODEL_COLORS.gemini}
              fillOpacity={0.18}
              strokeWidth={2}
              isAnimationActive
              animationDuration={1500}
              animationEasing="ease-out"
            />
          )}
          {hasGpt && (
            <Radar
              name="GPT"
              dataKey="gpt"
              stroke={MODEL_COLORS.gpt}
              fill={MODEL_COLORS.gpt}
              fillOpacity={0.18}
              strokeWidth={2}
              isAnimationActive
              animationDuration={1500}
              animationEasing="ease-out"
              animationBegin={150}
            />
          )}
          {hasClaude && (
            <Radar
              name="Claude"
              dataKey="claude"
              stroke={MODEL_COLORS.claude}
              fill={MODEL_COLORS.claude}
              fillOpacity={0.18}
              strokeWidth={2}
              isAnimationActive
              animationDuration={1500}
              animationEasing="ease-out"
              animationBegin={300}
            />
          )}
          <Radar
            name="평균"
            dataKey="aggregate"
            stroke={AGGREGATE_COLOR}
            fill={AGGREGATE_COLOR}
            fillOpacity={0.08}
            strokeWidth={3}
            strokeDasharray="6 4"
            isAnimationActive
            animationDuration={1500}
            animationEasing="ease-out"
            animationBegin={450}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{
              fontSize: 12,
              fontFamily: "var(--font-pretendard)",
              color: "var(--text-secondary)",
            }}
            iconSize={10}
          />
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  );
}
