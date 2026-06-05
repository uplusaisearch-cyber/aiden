/**
 * 공통 카드 렌더러 — scout / analyst / planner / architect / builder 5종 + 전용 렌더러 폴백.
 *
 * raw_json 을 key-value 카드로 표시. 중첩 객체/배열은 <details> 로 접힘.
 */
"use client";

import type { ReactNode } from "react";
import { isEmptyRaw, type RawJson } from "./types";

interface GenericDetailProps {
  raw: RawJson;
}

function isPlainObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function renderValue(v: unknown, depth = 0): ReactNode {
  if (v === null || v === undefined) {
    return <span className="text-text-muted">null</span>;
  }
  if (typeof v === "string") {
    if (v.length > 200 && depth === 0) {
      return (
        <details className="mt-0.5">
          <summary className="cursor-pointer font-mono text-[10px] text-text-muted">
            &quot;…&quot; ({v.length}자, 펼치기)
          </summary>
          <div className="mt-1 whitespace-pre-wrap font-korean text-sm text-text-primary">
            {v}
          </div>
        </details>
      );
    }
    return <span className="font-korean text-sm text-text-primary">{v}</span>;
  }
  if (typeof v === "number" || typeof v === "boolean") {
    return <span className="font-mono text-sm text-text-primary">{String(v)}</span>;
  }
  if (Array.isArray(v)) {
    if (v.length === 0) {
      return <span className="font-mono text-[10px] text-text-muted">[]</span>;
    }
    return (
      <details open={depth === 0}>
        <summary className="cursor-pointer font-mono text-[10px] text-text-muted">
          [ {v.length} ]
        </summary>
        <ol className="ml-3 mt-1 space-y-1">
          {v.map((item, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="font-mono text-[10px] text-text-muted">{i}:</span>
              <span className="min-w-0 flex-1">{renderValue(item, depth + 1)}</span>
            </li>
          ))}
        </ol>
      </details>
    );
  }
  if (isPlainObj(v)) {
    const keys = Object.keys(v);
    return (
      <details open={depth === 0}>
        <summary className="cursor-pointer font-mono text-[10px] text-text-muted">
          {`{ ${keys.length} keys }`}
        </summary>
        <div className="ml-3 mt-1 space-y-1">
          {Object.entries(v).map(([k, val]) => (
            <div key={k} className="flex gap-1.5">
              <span className="font-mono text-[10px] font-semibold text-text-secondary">
                {k}:
              </span>
              <span className="min-w-0 flex-1">{renderValue(val, depth + 1)}</span>
            </div>
          ))}
        </div>
      </details>
    );
  }
  return <span className="font-mono text-sm text-text-primary">{String(v)}</span>;
}

export function GenericDetail({ raw }: GenericDetailProps) {
  if (isEmptyRaw(raw)) {
    return (
      <div className="font-korean text-sm text-text-muted">원본 JSON 이 없습니다.</div>
    );
  }
  return (
    <div className="space-y-2 rounded-md border border-border-subtle bg-bg-elevated p-3">
      {Object.entries(raw).map(([k, v]) => (
        <div key={k} className="flex gap-2">
          <span className="font-mono text-xs font-semibold text-text-secondary">
            {k}:
          </span>
          <span className="min-w-0 flex-1">{renderValue(v)}</span>
        </div>
      ))}
    </div>
  );
}
