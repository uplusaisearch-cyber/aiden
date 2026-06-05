/**
 * 중앙 채팅 스트림 — 페르소나 버블 + iter 그룹 헤더.
 *
 * 명세 §8. ChatMessage.humanized 우선 표시, 본문 클릭 시 raw_json 토글.
 */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/api";
import type { Persona } from "@/lib/personas";
import { cn } from "@/lib/utils";
import { AgentDetailModal } from "./AgentDetailModal";

interface ChatStreamProps {
  messages: ChatMessage[];
  personas: Record<string, Persona>;
}

interface RenderItem {
  kind: "iter-header" | "message";
  iter?: number;
  msg?: ChatMessage;
  key: string;
}

const ITER_BG: Record<number, string> = {
  1: "bg-bg-elevated",
  2: "bg-state-warning/10",
  3: "bg-state-danger/10",
};

function formatTime(ts: string | null): string {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function buildItems(messages: ChatMessage[]): RenderItem[] {
  const items: RenderItem[] = [];
  let lastIter: number | null = null;
  let lastStage: number | null = null;
  messages.forEach((m, idx) => {
    // stage 2 (content_newsroom) 에서 iter 가 바뀌면 헤더 삽입
    const inContent = m.stage === 2;
    if (
      inContent &&
      typeof m.iteration === "number" &&
      (lastIter !== m.iteration || lastStage !== m.stage)
    ) {
      items.push({
        kind: "iter-header",
        iter: m.iteration,
        key: `iter-${m.iteration}-${idx}`,
      });
      lastIter = m.iteration;
    }
    if (!inContent) {
      lastIter = null;
    }
    lastStage = m.stage;
    items.push({ kind: "message", msg: m, key: m.id });
  });
  return items;
}

function MessageBubble({
  msg,
  persona,
  onOpen,
}: {
  msg: ChatMessage;
  persona: Persona | undefined;
  onOpen: (agentId: string) => void;
}) {
  const emoji = persona?.emoji ?? "💬";
  const name = persona?.display_name ?? msg.agent_id;
  const color = persona?.color_hex ?? "#6B7280";
  const text = msg.humanized || msg.headline || msg.body_text || "(내용 없음)";
  // Judge 버블은 본 모달 대상이 아님(B3-S3-D 별도 시각화). 클릭 비활성, 정적 표시.
  const isJudge = msg.agent_id.startsWith("judge-");

  return (
    <div className="flex gap-3 py-2">
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
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-korean text-xs font-semibold text-text-primary">
            {name}
          </span>
          <span className="font-mono text-[10px] text-text-muted">
            {formatTime(msg.timestamp)}
          </span>
          {msg.duration_ms ? (
            <span className="font-mono text-[10px] text-text-muted">
              {(msg.duration_ms / 1000).toFixed(1)}s
            </span>
          ) : null}
        </div>
        {isJudge ? (
          <div className="block w-full rounded-md border border-border-subtle bg-bg-elevated/70 p-2 text-left font-korean text-sm text-text-primary">
            {text}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onOpen(msg.agent_id)}
            className="block w-full rounded-md border border-border-subtle bg-bg-elevated/70 p-2 text-left font-korean text-sm text-text-primary transition hover:border-accent-pink"
            title="클릭 → 상세 모달"
          >
            {text}
          </button>
        )}
        {msg.badges.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {msg.badges.map((b, i) => (
              <span
                key={`${b.label}-${i}`}
                className={cn(
                  "rounded px-1.5 py-0.5 font-mono text-[10px]",
                  b.color === "success" && "bg-state-success/15 text-state-success",
                  b.color === "warning" && "bg-state-warning/15 text-state-warning",
                  b.color === "danger" && "bg-state-danger/15 text-state-danger",
                  b.color === "info" && "bg-state-info/15 text-state-info",
                  !b.color && "bg-bg-elevated text-text-secondary",
                )}
              >
                {b.label}: {b.value}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatStream({ messages, personas }: ChatStreamProps) {
  const items = useMemo(() => buildItems(messages), [messages]);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [newCount, setNewCount] = useState(0);
  // 모달 진입점: 클릭한 에이전트의 모든 iter 메시지를 모아 AgentDetailModal 에 전달.
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const selectedMessages = useMemo(() => {
    if (!selectedAgentId) return [];
    return messages.filter((m) => m.agent_id === selectedAgentId);
  }, [messages, selectedAgentId]);

  // 자동 스크롤 (사용자가 위로 올렸으면 OFF)
  useEffect(() => {
    if (!autoScroll) {
      setNewCount((c) => c + 1);
      return;
    }
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [items.length, autoScroll]);

  const onScroll = () => {
    const el = scrollerRef.current;
    if (!el) return;
    const nearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (nearBottom) {
      setAutoScroll(true);
      setNewCount(0);
    } else {
      setAutoScroll(false);
    }
  };

  return (
    <div className="relative h-full">
      <div
        ref={scrollerRef}
        onScroll={onScroll}
        className="h-full overflow-y-auto pr-2"
      >
        {items.length === 0 && (
          <div className="flex h-full items-center justify-center font-korean text-sm text-text-muted">
            연결 중… 첫 메시지를 기다립니다.
          </div>
        )}
        {items.map((item) => {
          if (item.kind === "iter-header") {
            const bg = ITER_BG[item.iter ?? 1] ?? "bg-bg-elevated";
            return (
              <div
                key={item.key}
                className={cn(
                  "my-3 flex items-center gap-3 rounded-md px-3 py-1.5",
                  bg,
                )}
              >
                <div className="h-px flex-1 bg-border-subtle" />
                <span className="font-korean text-[11px] font-semibold text-text-secondary">
                  iter {item.iter}
                </span>
                <div className="h-px flex-1 bg-border-subtle" />
              </div>
            );
          }
          const m = item.msg!;
          return (
            <MessageBubble
              key={item.key}
              msg={m}
              persona={personas[m.agent_id]}
              onOpen={setSelectedAgentId}
            />
          );
        })}
      </div>
      {selectedAgentId && (
        <AgentDetailModal
          open={selectedAgentId !== null}
          onOpenChange={(o) => {
            if (!o) setSelectedAgentId(null);
          }}
          agentId={selectedAgentId}
          iterMessages={selectedMessages}
          persona={personas[selectedAgentId]}
        />
      )}
      {!autoScroll && newCount > 0 && (
        <button
          type="button"
          onClick={() => {
            setAutoScroll(true);
            setNewCount(0);
            scrollerRef.current?.scrollTo({
              top: scrollerRef.current.scrollHeight,
              behavior: "smooth",
            });
          }}
          className="absolute bottom-3 right-4 rounded-full bg-accent-pink px-3 py-1 font-korean text-xs text-white shadow"
        >
          ↓ 새 메시지 {newCount}
        </button>
      )}
    </div>
  );
}
