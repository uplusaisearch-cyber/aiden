/**
 * 에이전트 상세 모달 — iter 탭 + 에이전트별 렌더러 dispatch.
 *
 * - Base UI Dialog/Tabs 사용 (shadcn 미설치, 기존 디자인 토큰 그대로).
 * - judge-* 는 모달 미적용 (호출 측 거름 + 안전망).
 * - 같은 agent_id 의 iter 별 메시지를 모아 탭으로 전환.
 * - Writer/FactChecker/Devils/Editor 는 전용 렌더러, 그 외 5종은 GenericDetail.
 * - 전용 렌더러가 기대 필드를 못 찾으면 graceful fallback (각 렌더러 내부에서 처리).
 */
"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Tabs } from "@base-ui/react/tabs";
import type { ChatMessage } from "@/lib/api";
import type { Persona } from "@/lib/personas";
import { cn } from "@/lib/utils";
import { WriterDetail } from "./agent-detail/WriterDetail";
import { FactCheckerDetail } from "./agent-detail/FactCheckerDetail";
import { DevilsDetail } from "./agent-detail/DevilsDetail";
import { EditorDetail } from "./agent-detail/EditorDetail";
import { GenericDetail } from "./agent-detail/GenericDetail";
import type { RawJson } from "./agent-detail/types";

interface AgentDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
  /** 같은 agent_id 의 모든 iter 메시지. 호출 측에서 필터링해 넘김. */
  iterMessages: ChatMessage[];
  persona: Persona | undefined;
}

type Tone = "success" | "warning" | "danger" | "info";

function renderAgentDetail(
  agentId: string,
  raw: RawJson,
  prevRaw: RawJson | null,
) {
  switch (agentId) {
    case "writer":
      return <WriterDetail raw={raw} prevRaw={prevRaw} />;
    case "factchecker":
      return <FactCheckerDetail raw={raw} />;
    case "devils":
      return <DevilsDetail raw={raw} />;
    case "editor":
      return <EditorDetail raw={raw} />;
    default:
      return <GenericDetail raw={raw} />;
  }
}

/** 탭 라벨 옆 작은 뱃지: confidence/이슈수/decision/draft_version 등 핵심 지표. */
function tabBadge(
  agentId: string,
  raw: RawJson,
): { label: string; tone: Tone } | null {
  if (agentId === "factchecker") {
    const c = raw["confidence_score"];
    if (typeof c === "number") {
      return {
        label: `conf ${c}`,
        tone: c >= 7 ? "success" : c >= 4 ? "warning" : "danger",
      };
    }
  }
  if (agentId === "devils") {
    const arr = Array.isArray(raw["critical_issues"])
      ? raw["critical_issues"]
      : [];
    const passed = raw["pass_threshold"] === true;
    return {
      label: `${arr.length}건 ${passed ? "P" : "F"}`,
      tone: passed ? "success" : "danger",
    };
  }
  if (agentId === "editor") {
    const d = typeof raw["decision"] === "string" ? raw["decision"] : "?";
    return {
      label: d,
      tone: d === "approved" ? "success" : "warning",
    };
  }
  if (agentId === "writer") {
    const v =
      typeof raw["draft_version"] === "number" ? raw["draft_version"] : null;
    return { label: v != null ? `v${v}` : "draft", tone: "info" };
  }
  return null;
}

const TONE_CLS: Record<Tone, string> = {
  success: "bg-state-success/15 text-state-success",
  warning: "bg-state-warning/15 text-state-warning",
  danger: "bg-state-danger/15 text-state-danger",
  info: "bg-state-info/15 text-state-info",
};

export function AgentDetailModal({
  open,
  onOpenChange,
  agentId,
  iterMessages,
  persona,
}: AgentDetailModalProps) {
  // 안전망: judge-* 는 본 모달 대상이 아님. 호출 측이 이미 걸렀더라도 한 번 더 차단.
  if (agentId.startsWith("judge-")) {
    return null;
  }

  const sorted = [...iterMessages].sort(
    (a, b) => (a.iteration ?? 0) - (b.iteration ?? 0),
  );
  const hasMultipleIters =
    sorted.length > 1 && sorted.some((m) => typeof m.iteration === "number");

  const emoji = persona?.emoji ?? "💬";
  const name = persona?.display_name ?? agentId;
  const color = persona?.color_hex ?? "#6B7280";
  const oneliner = persona?.oneliner ?? `${agentId} 의 상세`;

  const allEmpty = sorted.every(
    (m) => !m.raw_json || Object.keys(m.raw_json).length === 0,
  );

  const defaultIter = sorted[sorted.length - 1]?.iteration ?? 0;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Popup
          className={cn(
            "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2",
            "w-[92vw] max-w-3xl",
            "rounded-lg border border-border-subtle bg-bg-primary shadow-xl",
            "flex max-h-[85vh] flex-col overflow-hidden",
          )}
        >
          <header className="flex items-center justify-between gap-3 border-b border-border-subtle px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-base"
                style={{
                  backgroundColor: `${color}1F`,
                  color,
                  border: `1px solid ${color}55`,
                }}
                aria-hidden
              >
                {emoji}
              </div>
              <div className="min-w-0">
                <Dialog.Title className="truncate font-korean text-sm font-bold text-text-primary">
                  {name}
                </Dialog.Title>
                <Dialog.Description className="truncate font-korean text-[11px] text-text-secondary">
                  {oneliner}
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close className="rounded-md border border-border-subtle bg-bg-elevated px-2 py-1 font-mono text-xs text-text-secondary hover:border-accent-pink hover:text-text-primary">
              닫기
            </Dialog.Close>
          </header>

          <div className="flex-1 overflow-y-auto p-4">
            {allEmpty ? (
              <div className="rounded-md border border-border-subtle bg-bg-elevated p-3 font-korean text-sm text-text-muted">
                원본 JSON 이 비어 있습니다. 채팅 요약만 표시합니다.
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-text-secondary">
                  {sorted.map((m) => (
                    <li key={m.id}>
                      {m.humanized || m.headline || "(요약 없음)"}
                    </li>
                  ))}
                </ul>
              </div>
            ) : hasMultipleIters ? (
              <Tabs.Root defaultValue={String(defaultIter)}>
                <Tabs.List className="mb-3 flex gap-1 border-b border-border-subtle">
                  {sorted.map((m) => {
                    const iter = m.iteration ?? 0;
                    const badge = tabBadge(agentId, m.raw_json as RawJson);
                    return (
                      <Tabs.Tab
                        key={m.id}
                        value={String(iter)}
                        className={cn(
                          "group flex items-center gap-2 border-b-2 border-transparent px-3 py-1.5",
                          "font-korean text-xs text-text-secondary transition hover:text-text-primary",
                          "data-[selected]:border-accent-pink data-[selected]:text-text-primary",
                        )}
                      >
                        <span className="font-mono">iter {iter}</span>
                        {badge && (
                          <span
                            className={cn(
                              "rounded px-1.5 py-0.5 font-mono text-[10px]",
                              TONE_CLS[badge.tone],
                            )}
                          >
                            {badge.label}
                          </span>
                        )}
                      </Tabs.Tab>
                    );
                  })}
                </Tabs.List>
                {sorted.map((m, idx) => {
                  const iter = m.iteration ?? 0;
                  const prev =
                    idx > 0 ? (sorted[idx - 1].raw_json as RawJson) : null;
                  return (
                    <Tabs.Panel
                      key={m.id}
                      value={String(iter)}
                      className="focus:outline-none"
                    >
                      {renderAgentDetail(
                        agentId,
                        m.raw_json as RawJson,
                        prev,
                      )}
                    </Tabs.Panel>
                  );
                })}
              </Tabs.Root>
            ) : (
              renderAgentDetail(
                agentId,
                (sorted[0]?.raw_json ?? {}) as RawJson,
                null,
              )
            )}
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
