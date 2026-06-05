/**
 * Writer 전용 상세 — 본문 전문 + iter 간 단어 diff + revision_notes.
 *
 * 입력 raw_json 키: draft_version, title, subtitle, intro, sections[], closing, cta, revision_notes
 */
"use client";

import { diffWords, type DiffToken } from "@/lib/wordDiff";
import { cn } from "@/lib/utils";
import { pickArr, pickNum, pickStr, type RawJson } from "./types";

interface WriterDetailProps {
  raw: RawJson;
  /** 이전 iter 의 raw_json. 있으면 본문 diff 렌더. */
  prevRaw?: RawJson | null;
}

interface WriterSection {
  heading?: string;
  body?: string;
  fact_claims?: unknown;
}

interface WriterRevisionNote {
  target?: string;
  applied?: string;
}

function composeBody(raw: RawJson): string {
  const parts: string[] = [];
  const intro = pickStr(raw, "intro");
  if (intro) parts.push(intro);
  for (const s of pickArr<WriterSection>(raw, "sections")) {
    if (s && typeof s === "object") {
      if (typeof s.heading === "string" && s.heading) parts.push(s.heading);
      if (typeof s.body === "string" && s.body) parts.push(s.body);
    }
  }
  const closing = pickStr(raw, "closing");
  if (closing) parts.push(closing);
  const cta = pickStr(raw, "cta");
  if (cta) parts.push(cta);
  return parts.join("\n\n");
}

function DiffSpan({ token }: { token: DiffToken }) {
  if (token.status === "same") return <span>{token.text}</span>;
  if (token.status === "add") {
    return (
      <span className="rounded bg-state-success/20 px-0.5 text-state-success">
        {token.text}
      </span>
    );
  }
  return (
    <span className="rounded bg-state-danger/20 px-0.5 text-state-danger line-through">
      {token.text}
    </span>
  );
}

export function WriterDetail({ raw, prevRaw }: WriterDetailProps) {
  const title = pickStr(raw, "title", "(제목 없음)");
  const subtitle = pickStr(raw, "subtitle");
  const draftV = pickNum(raw, "draft_version");
  const sections = pickArr<WriterSection>(raw, "sections");
  const revisionNotes = pickArr<WriterRevisionNote>(raw, "revision_notes");

  const body = composeBody(raw);
  const prevBody = prevRaw ? composeBody(prevRaw) : "";

  const diff = prevBody ? diffWords(prevBody, body) : null;

  return (
    <div className="space-y-4">
      <div>
        <div className="font-mono text-[10px] text-text-muted">
          draft_version: {draftV ?? "?"}
        </div>
        <h3 className="font-korean text-lg font-bold text-text-primary">{title}</h3>
        {subtitle && (
          <p className="font-korean text-sm text-text-secondary">{subtitle}</p>
        )}
      </div>

      {diff ? (
        <div>
          <div className="mb-2 flex flex-wrap gap-2 font-mono text-[10px]">
            <span className="rounded bg-state-success/15 px-1.5 py-0.5 text-state-success">
              + {diff.stats.added}
            </span>
            <span className="rounded bg-state-danger/15 px-1.5 py-0.5 text-state-danger">
              - {diff.stats.removed}
            </span>
            <span className="rounded bg-bg-elevated px-1.5 py-0.5 text-text-secondary">
              same {diff.stats.same}
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border-subtle bg-bg-elevated p-3">
              <div className="mb-1 font-mono text-[10px] text-text-muted">
                PREV (iter {(draftV ?? 1) - 1})
              </div>
              <div className="whitespace-pre-wrap font-korean text-sm leading-relaxed text-text-primary">
                {diff.left.map((t, i) => (
                  <DiffSpan key={i} token={t} />
                ))}
              </div>
            </div>
            <div className="rounded-md border border-border-subtle bg-bg-elevated p-3">
              <div className="mb-1 font-mono text-[10px] text-text-muted">
                CURR (iter {draftV ?? "?"})
              </div>
              <div className="whitespace-pre-wrap font-korean text-sm leading-relaxed text-text-primary">
                {diff.right.map((t, i) => (
                  <DiffSpan key={i} token={t} />
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="whitespace-pre-wrap rounded-md border border-border-subtle bg-bg-elevated p-3 font-korean text-sm leading-relaxed text-text-primary">
          {body || "(본문 없음)"}
        </div>
      )}

      {sections.length > 0 && (
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-text-secondary">
            섹션 ({sections.length})
          </div>
          <div className="space-y-1">
            {sections.map((s, i) => {
              const claims = Array.isArray(s?.fact_claims) ? s.fact_claims : [];
              return (
                <div
                  key={i}
                  className="rounded border border-border-subtle bg-bg-primary/40 px-2 py-1"
                >
                  <div className="font-korean text-xs font-semibold text-text-primary">
                    {i + 1}. {(s && typeof s.heading === "string" && s.heading) || "(소제목 없음)"}
                  </div>
                  {claims.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {claims.slice(0, 6).map((fc, j) => (
                        <span
                          key={j}
                          className={cn(
                            "rounded bg-bg-elevated px-1.5 py-0.5 font-mono text-[10px] text-text-muted",
                          )}
                        >
                          fact: {String(typeof fc === "string" ? fc : JSON.stringify(fc)).slice(0, 40)}
                        </span>
                      ))}
                      {claims.length > 6 && (
                        <span className="font-mono text-[10px] text-text-muted">
                          +{claims.length - 6}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {revisionNotes.length > 0 && (
        <div>
          <div className="mb-1 font-korean text-xs font-semibold text-text-secondary">
            revision_notes
          </div>
          <ul className="space-y-1">
            {revisionNotes.map((rn, i) => (
              <li
                key={i}
                className="rounded border border-border-subtle bg-bg-elevated p-2 font-korean text-xs text-text-primary"
              >
                <span className="font-mono text-[10px] text-text-muted">target:</span>{" "}
                {rn?.target ?? "?"}
                <br />
                <span className="font-mono text-[10px] text-text-muted">applied:</span>{" "}
                {rn?.applied ?? "?"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
