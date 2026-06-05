/**
 * Fact-Checker 전용 — verification_log 항목별 카드 + 상태 색구분 + confidence_score.
 *
 * 입력 raw_json 키: verification_log[], annotated_draft, confidence_score, summary
 */
"use client";

import { cn } from "@/lib/utils";
import { pickArr, pickNum, pickStr, type RawJson } from "./types";

interface FactCheckerDetailProps {
  raw: RawJson;
}

interface VerificationEntry {
  claim?: string;
  status?: string;
  evidence?: string;
  source_url?: string;
  source_domain?: string;
  source_date?: string;
  correction?: string;
}

function statusClass(status: string): string {
  switch (status) {
    case "verified":
      return "border-state-success/40 bg-state-success/10 text-state-success";
    case "unverified":
      return "border-state-warning/40 bg-state-warning/10 text-state-warning";
    case "corrected":
      return "border-state-danger/40 bg-state-danger/10 text-state-danger";
    default:
      return "border-border-subtle bg-bg-elevated text-text-secondary";
  }
}

function confidenceTone(c: number | null): string {
  if (c == null) return "bg-bg-elevated text-text-secondary";
  if (c >= 7) return "bg-state-success/15 text-state-success";
  if (c >= 4) return "bg-state-warning/15 text-state-warning";
  return "bg-state-danger/15 text-state-danger";
}

export function FactCheckerDetail({ raw }: FactCheckerDetailProps) {
  const confidence = pickNum(raw, "confidence_score");
  const summary = pickStr(raw, "summary");
  const log = pickArr<VerificationEntry>(raw, "verification_log");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-md px-2 py-1 font-mono text-xs",
            confidenceTone(confidence),
          )}
        >
          confidence: {confidence ?? "?"}/10
        </span>
        <span className="font-mono text-[10px] text-text-muted">
          {log.length} claims
        </span>
      </div>

      {summary && (
        <div className="rounded border border-border-subtle bg-bg-elevated p-2 font-korean text-sm text-text-primary">
          {summary}
        </div>
      )}

      <div className="space-y-2">
        {log.length === 0 && (
          <div className="font-korean text-xs text-text-muted">
            verification_log 가 비어 있습니다.
          </div>
        )}
        {log.map((entry, i) => {
          const st = String(entry?.status ?? "?");
          return (
            <div key={i} className={cn("rounded-md border p-2", statusClass(st))}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-mono text-[10px] uppercase">{st}</span>
                {(entry?.source_domain || entry?.source_date) && (
                  <span className="font-mono text-[10px] text-text-muted">
                    {entry?.source_domain ?? ""}
                    {entry?.source_date ? `, ${entry.source_date}` : ""}
                  </span>
                )}
              </div>
              <p className="font-korean text-xs text-text-primary">
                &quot;{entry?.claim ?? ""}&quot;
              </p>
              {entry?.evidence && (
                <p className="mt-1 font-korean text-[11px] text-text-secondary">
                  근거: {entry.evidence}
                </p>
              )}
              {entry?.correction && (
                <p className="mt-1 font-korean text-[11px] text-state-danger">
                  ↳ 정정: {entry.correction}
                </p>
              )}
              {entry?.source_url && (
                <a
                  href={entry.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-block font-mono text-[10px] text-text-muted underline hover:text-accent-pink"
                >
                  source URL
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
