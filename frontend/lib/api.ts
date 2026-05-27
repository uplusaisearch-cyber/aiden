/**
 * AIDEN API 클라이언트 (B3-S3-B 연동).
 *
 * - 기본 base: NEXT_PUBLIC_API_BASE 또는 http://localhost:8000
 * - 모든 fetch 는 에러 시 throw (React Query 에서 retry/error UI 처리)
 * - subscribeRunStream: EventSource 기반 SSE 구독 + 이벤트별 핸들러 등록
 */
import type { JudgePanelResult } from "@/types/judge";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ---------------------------------------------------------------
// 타입 (백엔드 스키마 미러)
// ---------------------------------------------------------------
export type CategoryId =
  | "food"
  | "ai-trend"
  | "safety"
  | "culture"
  | "custom";

export interface GenerateOptions {
  max_iter: 1 | 2 | 3;
  skip_judge: boolean;
  safety_mode: "normal" | "dry_run";
}

export interface GenerateRequest {
  category: CategoryId;
  custom_topic?: string;
  options?: Partial<GenerateOptions>;
}

export interface GenerateResponse {
  session_id: string;
  status: "started";
  stream_url: string;
  started_at: string;
}

export interface RunSummary {
  session_id: string;
  category: string | null;
  title: string | null;
  status: string;
  started_at: string | null;
  duration_ms: number | null;
  judge_weighted_total: number | null;
  judge_status: string | null;
  thumbnail_url: string | null;
}

export interface RunListResponse {
  runs: RunSummary[];
  total: number;
}

export interface ChatMessage {
  id: string;
  agent_id: string;
  stage: number;
  iteration: number | null;
  timestamp: string | null;
  duration_ms: number;
  headline: string;
  body_text: string;
  /** B3-S3-C: 페르소나 사람말투 변환 결과 (트레이스 뷰어 채팅 버블 본문) */
  humanized: string;
  raw_json: Record<string, unknown>;
  highlights: Array<{ label: string; value: string | number }>;
  badges: Array<{ label: string; value: string; color?: string }>;
}

export interface RunDetail {
  session_id: string;
  category: string | null;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_sec: number | null;
  messages: ChatMessage[];
  stages: Array<{
    stage: number;
    status: string;
    duration_ms: number | null;
    agents_completed: number | null;
    iterations: number | null;
  }>;
  judge_panel: JudgePanelResult | null;
  final_output_html_url: string | null;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------
// REST 클라이언트
// ---------------------------------------------------------------
async function _fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {
      /* ignore */
    }
    throw new Error(`API ${res.status} ${url}: ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export function startGenerate(req: GenerateRequest): Promise<GenerateResponse> {
  return _fetchJson<GenerateResponse>(`${API_BASE}/api/generate`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function fetchRecentRuns(limit = 10): Promise<RunSummary[]> {
  const data = await _fetchJson<RunListResponse>(
    `${API_BASE}/api/runs?limit=${limit}`,
  );
  return data.runs;
}

export function fetchRunDetail(sessionId: string): Promise<RunDetail> {
  return _fetchJson<RunDetail>(`${API_BASE}/api/runs/${sessionId}`);
}

export interface HealthResponse {
  status: string;
  version: string;
  uptime_sec: number;
  active_runs: number;
  subscribers: number;
  judge_panel_available: boolean;
}

export function fetchHealth(): Promise<HealthResponse> {
  return _fetchJson<HealthResponse>(`${API_BASE}/api/health`);
}

// ---------------------------------------------------------------
// SSE 구독
// ---------------------------------------------------------------
export interface RunStreamHandlers {
  onChat?: (msg: ChatMessage) => void;
  onPipelineStart?: (data: Record<string, unknown>) => void;
  onStageChange?: (data: Record<string, unknown>) => void;
  onCostUpdate?: (data: Record<string, unknown>) => void;
  onJudge?: (data: Record<string, unknown>) => void;
  onPipelineComplete?: (data: Record<string, unknown>) => void;
  onError?: (data: { error_message: string }) => void;
  onPing?: () => void;
}

/**
 * SSE 구독. EventSource native API 사용. Cleanup 함수 반환.
 */
export function subscribeRunStream(
  sessionId: string,
  handlers: RunStreamHandlers,
): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  const es = new EventSource(`${API_BASE}/api/stream/${sessionId}`);

  const wrap = <T>(fn?: (data: T) => void) => (e: MessageEvent) => {
    if (!fn) return;
    try {
      fn(JSON.parse(e.data) as T);
    } catch {
      /* ignore */
    }
  };

  es.addEventListener("chat", wrap(handlers.onChat));
  es.addEventListener("pipeline_start", wrap(handlers.onPipelineStart));
  es.addEventListener("stage_change", wrap(handlers.onStageChange));
  es.addEventListener("cost_update", wrap(handlers.onCostUpdate));
  es.addEventListener("judge_evaluation", wrap(handlers.onJudge));
  es.addEventListener("pipeline_complete", (e) => {
    handlers.onPipelineComplete?.(JSON.parse((e as MessageEvent).data));
    es.close();
  });
  es.addEventListener("error", (e) => {
    if ((e as MessageEvent).data) {
      try {
        handlers.onError?.(JSON.parse((e as MessageEvent).data));
      } catch {
        /* ignore */
      }
    }
  });
  es.addEventListener("ping", () => handlers.onPing?.());

  return () => es.close();
}
