/**
 * 우측 Now Playing 패널 — 4개 정보 카드.
 *
 * 명세 §9. 현재 에이전트 / Stage+iter / Elapsed / 누적 토큰·비용.
 */
"use client";

import type { Persona, PersonasData, StageMeta } from "@/lib/personas";
import { stageKeyByNo } from "@/lib/personas";
import type { RunState } from "@/hooks/useRunStream";

interface NowPlayingProps {
  run: RunState;
  personasData: PersonasData;
}

function formatElapsed(ms: number): string {
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function StageDots({ iter, total = 3 }: { iter: number; total?: number }) {
  return (
    <span className="font-mono text-xs">
      {Array.from({ length: total }).map((_, i) => (
        <span key={i} className={i < iter ? "text-text-primary" : "text-text-muted"}>
          {i < iter ? "●" : "○"}
        </span>
      ))}
    </span>
  );
}

function Card({
  title,
  children,
  accent,
}: {
  title: string;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div
      className="rounded-lg border border-border-subtle bg-bg-elevated p-3"
      style={accent ? { borderLeft: `3px solid ${accent}` } : undefined}
    >
      <div className="mb-1 font-korean text-[11px] uppercase tracking-wide text-text-muted">
        {title}
      </div>
      {children}
    </div>
  );
}

function AgentCard({ persona }: { persona: Persona | null }) {
  if (!persona) {
    return (
      <Card title="현재 에이전트">
        <div className="font-korean text-sm text-text-muted">대기 중…</div>
      </Card>
    );
  }
  return (
    <Card title="현재 에이전트" accent={persona.color_hex}>
      <div className="flex items-center gap-3">
        <span className="text-2xl" aria-hidden>
          {persona.emoji}
        </span>
        <div>
          <div className="font-korean text-sm font-semibold text-text-primary">
            {persona.nickname}
          </div>
          <div className="font-korean text-[11px] text-text-muted">
            {persona.display_name}
          </div>
        </div>
      </div>
      <p className="mt-2 font-korean text-xs text-text-secondary">
        {persona.oneliner}
      </p>
    </Card>
  );
}

function StageCard({
  stage,
  iter,
}: {
  stage: StageMeta | null;
  iter: number | null;
}) {
  if (!stage) {
    return (
      <Card title="Stage / iter">
        <div className="font-korean text-sm text-text-muted">대기 중…</div>
      </Card>
    );
  }
  return (
    <Card title="Stage / iter">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-korean text-sm font-semibold text-text-primary">
            <span className="mr-1" aria-hidden>
              {stage.emoji}
            </span>
            {stage.display_name}
          </div>
          <div className="font-korean text-[11px] text-text-muted">
            {stage.subtitle}
          </div>
        </div>
        {iter !== null && <StageDots iter={iter} />}
      </div>
    </Card>
  );
}

function ElapsedCard({ ms }: { ms: number }) {
  return (
    <Card title="Elapsed">
      <div className="font-mono text-2xl tabular-nums text-text-primary">
        {formatElapsed(ms)}
      </div>
    </Card>
  );
}

function UsageCard({
  tokens,
  costUsd,
}: {
  tokens: number;
  costUsd: number;
}) {
  return (
    <Card title="누적 사용량">
      <div className="font-korean text-sm text-text-primary">
        토큰 <span className="font-mono">{tokens.toLocaleString()}</span>
      </div>
      <div className="font-korean text-sm text-text-primary">
        비용 <span className="font-mono">${costUsd.toFixed(4)}</span>
      </div>
    </Card>
  );
}

export function NowPlayingPanel({ run, personasData }: NowPlayingProps) {
  const persona = run.currentAgent
    ? personasData.personas[run.currentAgent] ?? null
    : null;
  const stageKey = run.currentStage !== null
    ? stageKeyByNo(personasData.stages, run.currentStage)
    : null;
  const stage = stageKey ? personasData.stages[stageKey] : null;

  return (
    <div className="space-y-3">
      <h2 className="font-korean text-sm font-semibold text-text-secondary">
        Now Playing
      </h2>
      <AgentCard persona={persona} />
      <StageCard stage={stage} iter={run.currentIter} />
      <ElapsedCard ms={run.elapsedMs} />
      <UsageCard tokens={run.totalTokens} costUsd={run.totalCostUSD} />
    </div>
  );
}
