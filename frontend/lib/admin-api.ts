/**
 * B3-S3-E admin API 클라이언트.
 *
 * - prompts: GET 목록/단일, PUT 저장, history, restore, rollback
 * - keys: GET 목록, PUT 설정, DELETE 해제
 * - registry: GET 목록, POST/PATCH/DELETE
 */
import { API_BASE } from "@/lib/api";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
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
    throw new Error(`API ${res.status} ${url}: ${detail.slice(0, 300)}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------
export interface PromptSummary {
  agent_id: string;
  filename: string;
  path: string;
  size_bytes: number;
  last_modified: string;
  version_count: number;
  display_name?: string | null;
  emoji?: string | null;
  color_key?: string | null;
}

export interface PromptDetail {
  agent_id: string;
  content: string;
  size_bytes: number;
  last_modified: string;
  detected_variables: string[];
  estimated_tokens: number;
}

export interface PromptHistoryEntry {
  timestamp: string;
  version_id: string;
  filename: string;
  size_bytes: number;
}

export interface PromptUpdateResponse {
  agent_id: string;
  saved_at: string;
  size_bytes: number;
  version_id: string | null;
  diff_summary: string | null;
}

export interface PromptRestoreResponse {
  agent_id: string;
  restored_from: string;
  saved_at: string;
  size_bytes: number;
}

export function listPrompts(): Promise<{ prompts: PromptSummary[] }> {
  return jsonFetch(`${API_BASE}/api/prompts`);
}

export function getPrompt(agentId: string): Promise<PromptDetail> {
  return jsonFetch(`${API_BASE}/api/prompts/${agentId}`);
}

export function updatePrompt(
  agentId: string,
  content: string,
): Promise<PromptUpdateResponse> {
  return jsonFetch(`${API_BASE}/api/prompts/${agentId}`, {
    method: "PUT",
    body: JSON.stringify({ content, save_version: true }),
  });
}

export function getPromptHistory(
  agentId: string,
): Promise<{ agent_id: string; history: PromptHistoryEntry[] }> {
  return jsonFetch(`${API_BASE}/api/prompts/${agentId}/history`);
}

export function restorePrompt(agentId: string): Promise<PromptRestoreResponse> {
  return jsonFetch(`${API_BASE}/api/prompts/${agentId}/restore`, {
    method: "POST",
  });
}

export function rollbackPrompt(
  agentId: string,
  timestamp: string,
): Promise<PromptRestoreResponse> {
  return jsonFetch(`${API_BASE}/api/prompts/${agentId}/rollback`, {
    method: "POST",
    body: JSON.stringify({ timestamp }),
  });
}

// ---------------------------------------------------------------------
// Keys
// ---------------------------------------------------------------------
export type KeyProvider = "gemini" | "openai" | "anthropic";
export type KeySource = "runtime" | "env" | "none";

export interface KeyStatus {
  provider: KeyProvider;
  source: KeySource;
  masked: string;
}

export function listKeys(): Promise<{ keys: KeyStatus[] }> {
  return jsonFetch(`${API_BASE}/api/admin/keys`);
}

export function setKey(provider: KeyProvider, key: string): Promise<KeyStatus> {
  return jsonFetch(`${API_BASE}/api/admin/keys`, {
    method: "PUT",
    body: JSON.stringify({ provider, key }),
  });
}

export function clearKey(provider: KeyProvider): Promise<KeyStatus> {
  return jsonFetch(`${API_BASE}/api/admin/keys/${provider}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------
export type TopicCategory =
  | "food"
  | "ai_trend"
  | "safety"
  | "culture"
  | "free";
export type TopicStatus = "published" | "rejected" | "expired";

export interface TopicEntry {
  id: string;
  topic: string;
  category: TopicCategory;
  status: TopicStatus;
  published_at: string;
  expiry: string | null;
  rejected_similar_to: string | null;
  created_at: string;
  updated_at: string;
}

export function listTopics(params?: {
  status?: TopicStatus;
  category?: TopicCategory;
}): Promise<{ topics: TopicEntry[]; total: number }> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.category) q.set("category", params.category);
  const suffix = q.toString();
  return jsonFetch(
    `${API_BASE}/api/admin/registry${suffix ? `?${suffix}` : ""}`,
  );
}

export function createTopic(payload: {
  topic: string;
  category: TopicCategory;
  status?: TopicStatus;
  expiry?: string | null;
}): Promise<TopicEntry> {
  return jsonFetch(`${API_BASE}/api/admin/registry`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchTopic(
  id: string,
  payload: { status?: TopicStatus; expiry?: string | null },
): Promise<TopicEntry> {
  return jsonFetch(`${API_BASE}/api/admin/registry/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTopic(id: string): Promise<{ id: string; deleted: boolean }> {
  return jsonFetch(`${API_BASE}/api/admin/registry/${id}`, {
    method: "DELETE",
  });
}
