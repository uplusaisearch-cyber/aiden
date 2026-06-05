/**
 * 에이전트 상세 모달 — 공용 타입 + 안전 pick 헬퍼.
 *
 * raw_json 은 백엔드 스키마 키 그대로 들어오지만 폴백을 위해 loose 타입으로 다룬다.
 * 전용 렌더러는 자기 에이전트의 필드만 pick 하고 누락 시 graceful 표시 (크래시 0).
 */

export type RawJson = Record<string, unknown>;

export function pickStr(raw: RawJson | undefined | null, key: string, fallback = ""): string {
  if (!raw) return fallback;
  const v = raw[key];
  return typeof v === "string" ? v : fallback;
}

export function pickNum(raw: RawJson | undefined | null, key: string): number | null {
  if (!raw) return null;
  const v = raw[key];
  return typeof v === "number" ? v : null;
}

export function pickArr<T = unknown>(raw: RawJson | undefined | null, key: string): T[] {
  if (!raw) return [];
  const v = raw[key];
  return Array.isArray(v) ? (v as T[]) : [];
}

export function pickObj(raw: RawJson | undefined | null, key: string): RawJson | null {
  if (!raw) return null;
  const v = raw[key];
  return typeof v === "object" && v !== null && !Array.isArray(v) ? (v as RawJson) : null;
}

export function isEmptyRaw(raw: RawJson | undefined | null): boolean {
  return !raw || Object.keys(raw).length === 0;
}
