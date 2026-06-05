/**
 * Editor-in-Chief 전용 — editorial_decision + accepted/rejected 2-column + revision_instructions.
 *
 * 입력 raw_json 키: editorial_decision, accepted_critiques[], rejected_critiques[],
 *                  factcheck_handling, decision, final_content?, revision_instructions[]
 */
"use client";

import { cn } from "@/lib/utils";
import { pickArr, pickStr, type RawJson } from "./types";

interface EditorDetailProps {
  raw: RawJson;
}

interface CritiqueIssue {
  location?: string;
  problem?: string;
}
interface AcceptedCritique {
  issue?: CritiqueIssue;
  action?: string;
}
interface RejectedCritique {
  issue?: CritiqueIssue;
  reason?: string;
}
interface RevisionInstruction {
  target?: string;
  instruction?: string;
}

export function EditorDetail({ raw }: EditorDetailProps) {
  const decision = pickStr(raw, "decision");
  const editorialDecision = pickStr(raw, "editorial_decision");
  const factcheckHandling = pickStr(raw, "factcheck_handling");
  const accepted = pickArr<AcceptedCritique>(raw, "accepted_critiques");
  const rejected = pickArr<RejectedCritique>(raw, "rejected_critiques");
  const revInstructions = pickArr<RevisionInstruction>(raw, "revision_instructions");

  const decTone =
    decision === "approved"
      ? "bg-state-success/15 text-state-success"
      : decision === "needs_revision"
        ? "bg-state-warning/15 text-state-warning"
        : "bg-bg-elevated text-text-secondary";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded px-2 py-1 font-mono text-xs uppercase",
            decTone,
          )}
        >
          {decision || "?"}
        </span>
        <span className="font-mono text-[10px] text-text-muted">
          accepted {accepted.length} / rejected {rejected.length}
        </span>
      </div>

      {editorialDecision && (
        <div className="rounded-md border border-border-subtle bg-bg-elevated p-3">
          <div className="mb-1 font-korean text-xs font-semibold text-text-secondary">
            editorial_decision
          </div>
          <p className="whitespace-pre-wrap font-korean text-sm text-text-primary">
            {editorialDecision}
          </p>
        </div>
      )}

      {factcheckHandling && (
        <div className="rounded border border-border-subtle bg-bg-primary/40 p-2 font-korean text-xs text-text-secondary">
          <span className="font-semibold">factcheck_handling:</span> {factcheckHandling}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-state-success">
            accepted ({accepted.length})
          </div>
          <ul className="space-y-1">
            {accepted.length === 0 && (
              <li className="font-korean text-xs text-text-muted">없음.</li>
            )}
            {accepted.map((a, i) => (
              <li
                key={i}
                className="rounded border border-state-success/30 bg-state-success/5 p-2 font-korean text-xs text-text-primary"
              >
                <span className="font-mono text-[10px] text-text-muted">
                  {a?.issue?.location ?? "?"}
                </span>
                <p className="mt-0.5">{a?.issue?.problem ?? "?"}</p>
                {a?.action && (
                  <p className="mt-0.5 text-state-success">↳ {a.action}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-state-danger">
            rejected ({rejected.length})
          </div>
          <ul className="space-y-1">
            {rejected.length === 0 && (
              <li className="font-korean text-xs text-text-muted">없음.</li>
            )}
            {rejected.map((r, i) => (
              <li
                key={i}
                className="rounded border border-state-danger/30 bg-state-danger/5 p-2 font-korean text-xs text-text-primary"
              >
                <span className="font-mono text-[10px] text-text-muted">
                  {r?.issue?.location ?? "?"}
                </span>
                <p className="mt-0.5">{r?.issue?.problem ?? "?"}</p>
                {r?.reason && (
                  <p className="mt-0.5 text-state-danger">↳ {r.reason}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {revInstructions.length > 0 && (
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-text-secondary">
            revision_instructions
          </div>
          <ol className="space-y-1">
            {revInstructions.map((ri, i) => (
              <li
                key={i}
                className="rounded border border-border-subtle bg-bg-elevated p-2 font-korean text-xs text-text-primary"
              >
                <span className="font-mono text-[10px] text-text-muted">
                  {ri?.target ?? "?"}:
                </span>{" "}
                {ri?.instruction ?? "?"}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
