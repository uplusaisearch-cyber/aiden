/**
 * Devil's Advocate 전용 — overall_verdict + scores 5축 + critical_issues 쌍 카드.
 *
 * 입력 raw_json 키: overall_verdict, scores{}, critical_issues[], pass_threshold, carried_over_from_previous
 */
"use client";

import { cn } from "@/lib/utils";
import { pickArr, pickObj, pickStr, type RawJson } from "./types";

interface DevilsDetailProps {
  raw: RawJson;
}

interface CriticalIssue {
  location?: string;
  problem?: string;
  suggestion?: string;
}

export function DevilsDetail({ raw }: DevilsDetailProps) {
  const verdict = pickStr(raw, "overall_verdict");
  const scores = pickObj(raw, "scores") ?? {};
  const issues = pickArr<CriticalIssue>(raw, "critical_issues");
  const passed = raw["pass_threshold"] === true;
  const carriedOver = pickArr<string>(raw, "carried_over_from_previous");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded px-2 py-1 font-mono text-xs",
            passed
              ? "bg-state-success/15 text-state-success"
              : "bg-state-danger/15 text-state-danger",
          )}
        >
          {passed ? "PASS" : "FAIL"}
        </span>
        <span className="font-mono text-[10px] text-text-muted">
          {issues.length} 비판
        </span>
        {carriedOver.length > 0 && (
          <span className="rounded bg-state-warning/15 px-1.5 py-0.5 font-mono text-[10px] text-state-warning">
            이월 {carriedOver.length}
          </span>
        )}
      </div>

      {verdict && (
        <blockquote className="rounded-md border-l-4 border-state-danger bg-state-danger/5 px-3 py-2 font-korean text-sm italic text-text-primary">
          &quot;{verdict}&quot;
        </blockquote>
      )}

      {Object.keys(scores).length > 0 && (
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-text-secondary">
            scores
          </div>
          <div className="grid grid-cols-2 gap-1 sm:grid-cols-5">
            {Object.entries(scores).map(([k, v]) => (
              <div
                key={k}
                className="rounded border border-border-subtle bg-bg-elevated px-2 py-1 text-center"
              >
                <div className="font-mono text-[9px] uppercase text-text-muted">
                  {k}
                </div>
                <div className="font-mono text-sm font-bold text-text-primary">
                  {String(v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {issues.length === 0 && (
          <div className="font-korean text-xs text-text-muted">
            critical_issues 가 비어 있습니다.
          </div>
        )}
        {issues.map((iss, i) => (
          <div
            key={i}
            className="rounded-md border border-border-subtle bg-bg-elevated p-2"
          >
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded bg-state-danger/15 px-1.5 py-0.5 font-mono text-[10px] text-state-danger">
                #{i + 1}
              </span>
              <span className="font-mono text-[10px] text-text-muted">
                {iss?.location ?? "(위치 미지정)"}
              </span>
            </div>
            <p className="font-korean text-xs text-text-primary">
              <span className="font-semibold">문제:</span> {iss?.problem ?? "?"}
            </p>
            {iss?.suggestion && (
              <p className="mt-1 font-korean text-xs text-state-success">
                <span className="font-semibold">제안:</span> {iss.suggestion}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
