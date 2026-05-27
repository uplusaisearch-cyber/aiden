/**
 * 좌측 Stage 패널 — 3 Newsroom 카드 + 9 에이전트 2단 계층.
 *
 * 명세 §7. ChatMessage.agent_id (짧은 id) 와 personas.yaml 의 키가 동일하다고 가정.
 */
"use client";

import { useMemo } from "react";
import type { PersonasData, StageKey, StageMeta } from "@/lib/personas";
import { cn } from "@/lib/utils";

interface StagePanelProps {
  personasData: PersonasData;
  currentAgent: string | null;
  completedAgents: Set<string>;
  iterByAgent: Record<string, number>;
}

const STAGE_ORDER: StageKey[] = ["topic_newsroom", "content_newsroom", "gameifier"];

type AgentStatus = "done" | "active" | "waiting";

function agentStatus(
  agentId: string,
  currentAgent: string | null,
  completedAgents: Set<string>,
): AgentStatus {
  if (agentId === currentAgent) return "active";
  if (completedAgents.has(agentId)) return "done";
  return "waiting";
}

function stageStatusLabel(
  stage: StageMeta,
  currentAgent: string | null,
  completedAgents: Set<string>,
  iterByAgent: Record<string, number>,
): string {
  const allDone = stage.agents.every((a) => completedAgents.has(a));
  if (allDone) return "완료";
  const anyActive = currentAgent && stage.agents.includes(currentAgent);
  if (anyActive) {
    const iter = currentAgent ? iterByAgent[currentAgent] : undefined;
    if (iter) return `iter ${iter} 진행`;
    return "진행";
  }
  return "대기";
}

export function StagePanel({
  personasData,
  currentAgent,
  completedAgents,
  iterByAgent,
}: StagePanelProps) {
  const stages = personasData.stages;
  const personas = personasData.personas;

  const stageEntries = useMemo(
    () =>
      STAGE_ORDER.map((k) => ({ key: k, meta: stages[k] })).filter(
        (e) => e.meta,
      ),
    [stages],
  );

  return (
    <div className="space-y-3">
      <h2 className="font-korean text-sm font-semibold text-text-secondary">
        Stages
      </h2>
      {stageEntries.map(({ key, meta }) => {
        const statusLabel = stageStatusLabel(
          meta,
          currentAgent,
          completedAgents,
          iterByAgent,
        );
        return (
          <div
            key={key}
            className="rounded-lg border border-border-subtle bg-bg-elevated p-3"
          >
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg" aria-hidden>
                  {meta.emoji}
                </span>
                <div>
                  <div className="font-korean text-sm font-semibold text-text-primary">
                    {meta.display_name}
                  </div>
                  <div className="font-korean text-[11px] text-text-muted">
                    {meta.subtitle}
                  </div>
                </div>
              </div>
              <span className="font-korean text-[11px] text-text-secondary">
                [{statusLabel}]
              </span>
            </div>
            <ul className="space-y-1.5">
              {meta.agents.map((agentId) => {
                const p = personas[agentId];
                if (!p) return null;
                const status = agentStatus(agentId, currentAgent, completedAgents);
                const iter = iterByAgent[agentId];
                return (
                  <li
                    key={agentId}
                    className={cn(
                      "flex items-center justify-between gap-2 rounded px-2 py-1 text-xs transition",
                      status === "active" && "animate-pulse",
                    )}
                    style={
                      status === "active"
                        ? {
                            backgroundColor: `${p.color_hex}1A`,
                            borderLeft: `2px solid ${p.color_hex}`,
                          }
                        : undefined
                    }
                  >
                    <span className="flex items-center gap-2">
                      <span aria-hidden>{p.emoji}</span>
                      <span
                        className={cn(
                          "font-korean",
                          status === "waiting" && "text-text-muted",
                          status !== "waiting" && "text-text-primary",
                        )}
                      >
                        {p.display_name}
                      </span>
                    </span>
                    <span
                      className={cn(
                        "font-mono text-[10px]",
                        status === "done" && "text-state-success",
                        status === "active" && "text-state-info",
                        status === "waiting" && "text-text-muted",
                      )}
                    >
                      {status === "done"
                        ? iter
                          ? `✓ iter ${iter}`
                          : "✓"
                        : status === "active"
                          ? iter
                            ? `⏵ iter ${iter}`
                            : "⏵"
                          : "·"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
