"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface SettingRow {
  id: string;
  label: string;
  hint: string;
  control:
    | { type: "select"; options: string[]; defaultValue: string }
    | { type: "toggle"; defaultValue: boolean }
    | { type: "number"; defaultValue: number; step?: number; min?: number; max?: number };
  // 실동작 = "wired". 장식 = "decorative" (토글만 됨).
  status: "wired" | "decorative" | "blocked";
}

// B3-S3-E §B5 의 모든 항목.
// 실동작 항목은 generate /api/generate 의 GenerateOptions(per-run 옵션) 에는 있지만,
// 어드민에서 ‘서버 전역 default’ 를 바꿀 엔드포인트는 이번 범위 밖이라 [BLOCKED] 처리.
const SECTIONS: Array<{ title: string; rows: SettingRow[] }> = [
  {
    title: "파이프라인 (서버 전역 기본값)",
    rows: [
      {
        id: "max_iter",
        label: "Content Newsroom max_iter",
        hint: "한 run 에서 Writer↔Critique 반복 최대 횟수. /api/generate options 로 per-run override 가능.",
        control: { type: "select", options: ["1", "2", "3"], defaultValue: "3" },
        status: "blocked",
      },
      {
        id: "safety_mode",
        label: "SAFETY_MODE",
        hint: "dry_run = 실제 호출 없이 예상 비용만. normal = 실제 호출.",
        control: {
          type: "select",
          options: ["normal", "dry_run"],
          defaultValue: "normal",
        },
        status: "blocked",
      },
    ],
  },
  {
    title: "비용 예산 (USD)",
    rows: [
      {
        id: "monthly_budget_usd",
        label: "월간 예산",
        hint: "Cost Tracker 가 초과 시 호출을 차단합니다. .env 의 MONTHLY_BUDGET_USD.",
        control: { type: "number", defaultValue: 15, step: 1, min: 0 },
        status: "blocked",
      },
      {
        id: "daily_budget_usd",
        label: "일일 예산",
        hint: ".env 의 DAILY_BUDGET_USD.",
        control: { type: "number", defaultValue: 2, step: 0.5, min: 0 },
        status: "blocked",
      },
      {
        id: "per_run_budget_usd",
        label: "Run 당 예산",
        hint: ".env 의 PER_RUN_BUDGET_USD.",
        control: { type: "number", defaultValue: 0.5, step: 0.05, min: 0 },
        status: "blocked",
      },
    ],
  },
  {
    title: "장식 (현재 토글만 동작)",
    rows: [
      {
        id: "cache_ttl",
        label: "캐시 TTL",
        hint: "장식. 토글만 가능. 실제 캐시는 변경 없음.",
        control: {
          type: "select",
          options: ["30s", "1m", "5m", "10m"],
          defaultValue: "30s",
        },
        status: "decorative",
      },
      {
        id: "concurrency",
        label: "동시 실행 수",
        hint: "장식. 토글만 가능.",
        control: { type: "number", defaultValue: 2, min: 1, max: 8 },
        status: "decorative",
      },
      {
        id: "log_level",
        label: "로그 레벨",
        hint: "장식. 토글만 가능.",
        control: {
          type: "select",
          options: ["DEBUG", "INFO", "WARNING", "ERROR"],
          defaultValue: "INFO",
        },
        status: "decorative",
      },
      {
        id: "grounding_global",
        label: "그라운딩 전역 ON/OFF",
        hint: "장식. 토글만 가능. 실제는 config/agents.yaml 의 agent별 grounding 따름.",
        control: { type: "toggle", defaultValue: true },
        status: "decorative",
      },
      {
        id: "slack_webhook",
        label: "Slack Webhook URL",
        hint: "장식. 토글만 가능.",
        control: { type: "toggle", defaultValue: false },
        status: "decorative",
      },
      {
        id: "auto_backup",
        label: "자동 백업 주기",
        hint: "장식. 토글만 가능.",
        control: {
          type: "select",
          options: ["없음", "1h", "6h", "24h"],
          defaultValue: "없음",
        },
        status: "decorative",
      },
      {
        id: "json_strict",
        label: "JSON strict 모드",
        hint: "장식. 토글만 가능.",
        control: { type: "toggle", defaultValue: true },
        status: "decorative",
      },
      {
        id: "stream_chunk",
        label: "Streaming 청크 크기",
        hint: "장식. 토글만 가능.",
        control: {
          type: "select",
          options: ["1", "5", "10", "50"],
          defaultValue: "5",
        },
        status: "decorative",
      },
    ],
  },
];

function StatusBadge({ status }: { status: SettingRow["status"] }) {
  if (status === "wired") return <Badge variant="default">실동작</Badge>;
  if (status === "blocked")
    return (
      <Badge
        variant="outline"
        className="border-state-warning/50 text-state-warning"
      >
        BLOCKED
      </Badge>
    );
  return <Badge variant="ghost">장식</Badge>;
}

function Control({ row }: { row: SettingRow }) {
  const [v, setV] = useState<string | number | boolean>(
    row.control.defaultValue,
  );
  const disabled = row.status === "blocked";

  if (row.control.type === "toggle") {
    const on = Boolean(v);
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() => setV(!on)}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full border transition",
          on
            ? "border-accent-pink bg-accent-pink-soft"
            : "border-border-subtle bg-bg-secondary",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        <span
          className={cn(
            "ml-0.5 inline-block h-5 w-5 rounded-full bg-text-primary transition",
            on && "translate-x-5 bg-accent-pink",
          )}
        />
      </button>
    );
  }
  if (row.control.type === "select") {
    return (
      <select
        disabled={disabled}
        value={String(v)}
        onChange={(e) => setV(e.target.value)}
        className={cn(
          "h-9 rounded-md border border-border-subtle bg-bg-secondary px-3 text-sm text-text-primary",
          disabled && "opacity-50",
        )}
      >
        {row.control.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  }
  return (
    <input
      type="number"
      disabled={disabled}
      value={Number(v)}
      step={row.control.step ?? 1}
      min={row.control.min}
      max={row.control.max}
      onChange={(e) => setV(Number(e.target.value))}
      className={cn(
        "h-9 w-28 rounded-md border border-border-subtle bg-bg-secondary px-3 text-sm text-text-primary",
        disabled && "opacity-50",
      )}
    />
  );
}

export default function SettingsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl">
      <header className="mb-6">
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          ⚙️ 운영 옵션
        </h1>
        <p className="mt-1 font-korean text-sm text-text-secondary">
          모델 호출과 비용 안전장치, 그 외 장식 토글 한 자리.
        </p>
      </header>

      <div className="mb-6 rounded-md border border-state-warning/40 bg-state-warning/10 px-4 py-3 font-korean text-sm text-text-primary">
        ⚠️ 서버 전역 기본값(BLOCKED 표시)을 어드민에서 변경하는 백엔드 엔드포인트는
        이번 범위 밖입니다. <code className="font-mono">.env</code> /{" "}
        <code className="font-mono">config/agents.yaml</code> 을 수정 후 재시작하세요.
        per-run 옵션은 <code className="font-mono">/api/generate</code> 의 body 로 override 가능합니다.
      </div>

      <div className="space-y-6">
        {SECTIONS.map((section) => (
          <motion.section
            key={section.title}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border-subtle bg-bg-elevated"
          >
            <h2 className="border-b border-border-subtle px-4 py-3 font-korean text-sm font-semibold text-text-primary">
              {section.title}
            </h2>
            <div>
              {section.rows.map((row, idx) => (
                <div
                  key={row.id}
                  className={cn(
                    "flex flex-wrap items-center gap-4 px-4 py-3",
                    idx > 0 && "border-t border-border-subtle/60",
                  )}
                >
                  <div className="flex-1">
                    <div className="font-korean text-sm text-text-primary">
                      {row.label}
                    </div>
                    <div className="mt-0.5 font-korean text-[11px] text-text-muted">
                      {row.hint}
                    </div>
                  </div>
                  <StatusBadge status={row.status} />
                  <Control row={row} />
                </div>
              ))}
            </div>
          </motion.section>
        ))}
      </div>
    </div>
  );
}
