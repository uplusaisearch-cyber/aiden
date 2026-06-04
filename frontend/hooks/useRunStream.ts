/**
 * Run 트레이스 상태 훅 — 과거 메시지(history) + 라이브 SSE 통합.
 *
 * fetch-then-stream 패턴:
 *   1) 마운트 시 `GET /api/runs/{id}` 로 디스크에 기록된 ChatMessage 일괄 로드
 *   2) 응답 status 가 종료 상태 (`completed`/`partial`/`failed*`) → `completed`/`error` 로 정착, SSE 미연결
 *   3) 진행 중 상태 (`running`/`unknown` — metadata 미작성) 또는 fetch 404 → SSE 구독으로 후속 메시지 합치기
 *
 * 실제 백엔드 SSE 이벤트 (backend/api/routers/stream.py + run_manager.py):
 *   - `ping`            : heartbeat (무시)
 *   - `pipeline_start`  : { session_id, category, custom_topic, options, started_at }
 *   - `chat`            : ChatMessage (trace_converter.convert 결과)
 *   - `stage_change`    : { stage, stage_name, previous_stage, ts }
 *   - `cost_update`     : { total_usd, budget_usd, elapsed_ms, last_latency_ms }
 *   - `judge_evaluation`: 개별 judge 모델 결과
 *   - `pipeline_complete`: { status, final_output_url, judge_summary, ... }
 *   - `error`           : { error_message, is_recoverable, ... }
 */
"use client";

import { useEffect, useRef, useState } from "react";
import {
  type ChatMessage,
  fetchRunDetail,
  subscribeRunStream,
  type RunStreamHandlers,
} from "@/lib/api";

export type RunStatus = "connecting" | "streaming" | "completed" | "error";

export interface RunState {
  status: RunStatus;
  messages: ChatMessage[];
  currentAgent: string | null;     // ChatMessage.agent_id (예: "writer")
  currentStage: number | null;     // 1: topic_newsroom, 2: content_newsroom, 3: gameifier, 4: judge
  currentIter: number | null;
  startedAt: number | null;        // Date.now() 기준 (라이브 elapsed 카운트업용)
  elapsedMs: number;
  totalTokens: number;             // 백엔드가 cost_update 에 토큰을 넘기지 않으면 0 유지
  totalCostUSD: number;
  error: string | null;
  /** 과거 run(완료/실패) 여부. PlaybackToggle 등에서 사용. */
  isHistorical: boolean;
}

const INITIAL: RunState = {
  status: "connecting",
  messages: [],
  currentAgent: null,
  currentStage: null,
  currentIter: null,
  startedAt: null,
  elapsedMs: 0,
  totalTokens: 0,
  totalCostUSD: 0,
  error: null,
  isHistorical: false,
};

const TERMINAL_PREFIXES = ["completed", "partial", "failed"];

function isTerminalStatus(s: string | null | undefined): boolean {
  if (!s) return false;
  return TERMINAL_PREFIXES.some((p) => s === p || s.startsWith(p));
}

function deriveFromMessages(messages: ChatMessage[]): {
  currentAgent: string | null;
  currentStage: number | null;
  currentIter: number | null;
} {
  if (messages.length === 0) {
    return { currentAgent: null, currentStage: null, currentIter: null };
  }
  const last = messages[messages.length - 1];
  return {
    currentAgent: last.agent_id,
    currentStage: last.stage,
    currentIter: last.iteration ?? null,
  };
}

export function useRunStream(runId: string): RunState {
  const [state, setState] = useState<RunState>(INITIAL);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!runId) return;
    setState({ ...INITIAL });

    let cancelled = false;
    let unsubscribe: (() => void) | null = null;

    // 메시지 id 기준 dedupe — fetch 와 SSE 가 boundary 에서 겹칠 경우 방어.
    // setState updater 안에서 호출되므로 반드시 pure 해야 한다. React Strict Mode 가
    // dev 에서 updater 를 2 회 호출해 순수성을 검사하는데, 외부 Set 을 mutate 하면
    // 2 번째 호출이 첫 번째 결과를 dedupe 해 messages 가 빈 배열로 끝난다 (라이브 화면 멈춤 root cause).
    const appendUnique = (
      prev: ChatMessage[],
      next: ChatMessage[],
    ): ChatMessage[] => {
      const existing = new Set(prev.map((m) => m.id).filter(Boolean));
      const merged = prev.slice();
      for (const m of next) {
        if (m.id && existing.has(m.id)) continue;
        if (m.id) existing.add(m.id);
        merged.push(m);
      }
      return merged;
    };

    const subscribeLive = (initialStartedAt: number | null) => {
      const handlers: RunStreamHandlers = {
        onPipelineStart: () => {
          setState((s) => ({
            ...s,
            status: "streaming",
            startedAt: s.startedAt ?? Date.now(),
          }));
        },
        onChat: (msg: ChatMessage) => {
          setState((s) => {
            const merged = appendUnique(s.messages, [msg]);
            const derived = deriveFromMessages(merged);
            return {
              ...s,
              status: "streaming",
              startedAt: s.startedAt ?? Date.now(),
              messages: merged,
              currentAgent: derived.currentAgent,
              currentStage: derived.currentStage,
              currentIter: derived.currentIter ?? s.currentIter,
            };
          });
        },
        onStageChange: (data) => {
          const stage = typeof data.stage === "number" ? data.stage : null;
          if (stage === null) return;
          setState((s) => ({ ...s, currentStage: stage }));
        },
        onCostUpdate: (data) => {
          const total = typeof data.total_usd === "number" ? data.total_usd : null;
          const tokens = typeof data.total_tokens === "number" ? data.total_tokens : null;
          if (total === null && tokens === null) return;
          setState((s) => ({
            ...s,
            totalCostUSD: total ?? s.totalCostUSD,
            totalTokens: tokens ?? s.totalTokens,
          }));
        },
        onPipelineComplete: () => {
          setState((s) => ({ ...s, status: "completed" }));
        },
        onError: (data) => {
          setState((s) => ({
            ...s,
            status: "error",
            error: data?.error_message ?? "스트림 오류",
          }));
        },
      };

      unsubscribe = subscribeRunStream(runId, handlers);
      cleanupRef.current = unsubscribe;
      // 라이브 모드에선 즉시 connecting → streaming 으로 (첫 chat 전이라도 패널 표시)
      setState((s) => ({
        ...s,
        status: "streaming",
        startedAt: s.startedAt ?? initialStartedAt ?? Date.now(),
      }));
    };

    (async () => {
      try {
        const detail = await fetchRunDetail(runId);
        if (cancelled) return;

        const derived = deriveFromMessages(detail.messages);
        const startedAtMs = detail.started_at
          ? new Date(detail.started_at).getTime()
          : null;

        // 토큰·비용: judge_panel.cost_usd_estimate 만 메타로 남기는 현 구현은 부분 정보.
        // 라이브 cost_update 와 합쳐 사용. 과거 run 에선 0 으로 두거나 judge 비용만 표시.
        const judgeCost = detail.judge_panel?.cost_usd_estimate ?? 0;

        const terminal = isTerminalStatus(detail.status);

        setState((s) => ({
          ...s,
          messages: detail.messages,
          currentAgent: derived.currentAgent,
          currentStage: derived.currentStage,
          currentIter: derived.currentIter,
          startedAt: startedAtMs,
          elapsedMs:
            detail.duration_sec !== null
              ? detail.duration_sec * 1000
              : startedAtMs
                ? Math.max(0, Date.now() - startedAtMs)
                : 0,
          totalCostUSD: typeof judgeCost === "number" ? judgeCost : s.totalCostUSD,
          status: terminal ? "completed" : "streaming",
          isHistorical: terminal,
        }));

        if (!terminal) {
          subscribeLive(startedAtMs);
        }
      } catch (_e: unknown) {
        if (cancelled) return;
        // 404 등 fetch 실패 — 신규 라이브 run 가능성 → SSE 시도
        // (실패 원인이 진짜 네트워크 에러면 SSE 도 실패할 텐데, 그건 onError 에서 잡힘)
        subscribeLive(null);
      }
    })();

    return () => {
      cancelled = true;
      try {
        unsubscribe?.();
      } catch {
        /* noop */
      }
      cleanupRef.current = null;
    };
  }, [runId]);

  // elapsed 카운트업 (1초). 과거 run 은 duration_sec 으로 한 번 세팅하고 멈춤.
  useEffect(() => {
    if (state.status !== "streaming" || state.startedAt === null) return;
    const startedAt = state.startedAt;
    const id = window.setInterval(() => {
      setState((s) => ({ ...s, elapsedMs: Date.now() - startedAt }));
    }, 1000);
    return () => window.clearInterval(id);
  }, [state.status, state.startedAt]);

  return state;
}
