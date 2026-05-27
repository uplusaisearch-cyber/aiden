/**
 * 페르소나 메타 fetch & 타입.
 *
 * 백엔드 `GET /api/personas` 응답 매핑. 진입 시 1회 fetch + 모듈 캐시.
 * 명세: docs/patches/2026-05-28_b3-s3-c_trace_viewer.md §5.
 */
import { API_BASE } from "@/lib/api";

export type StageKey = "topic_newsroom" | "content_newsroom" | "gameifier";

export interface PersonaSpeech {
  prefix_options: string[];
  suffix_options: string[];
  filler_options: string[];
}

export interface Persona {
  display_name: string;
  nickname: string;
  emoji: string;
  oneliner: string;
  stage: StageKey;
  order: number;
  color_hex: string;
  aliases?: string[];
  speech: PersonaSpeech;
}

export interface StageMeta {
  display_name: string;
  subtitle: string;
  emoji: string;
  stage_no: number;
  agents: string[];
}

export interface PersonasData {
  version: number;
  personas: Record<string, Persona>;
  stages: Record<StageKey, StageMeta>;
}

let _cache: PersonasData | null = null;
let _pending: Promise<PersonasData> | null = null;

export async function fetchPersonas(): Promise<PersonasData> {
  if (_cache) return _cache;
  if (_pending) return _pending;
  _pending = (async () => {
    const res = await fetch(`${API_BASE}/api/personas`);
    if (!res.ok) {
      _pending = null;
      throw new Error(`personas API ${res.status}`);
    }
    const data = (await res.json()) as PersonasData;
    _cache = data;
    _pending = null;
    return data;
  })();
  return _pending;
}

export function clearPersonasCache(): void {
  _cache = null;
  _pending = null;
}

/** stage_no(int) → stage key 매핑 (ChatMessage.stage 와 personas.stages 연결용). */
export function stageKeyByNo(
  stages: PersonasData["stages"],
  stageNo: number,
): StageKey | null {
  const entry = Object.entries(stages).find(
    ([, meta]) => meta.stage_no === stageNo,
  );
  return (entry?.[0] as StageKey) ?? null;
}
