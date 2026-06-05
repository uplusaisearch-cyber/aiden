"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  getPrompt,
  getPromptHistory,
  listPrompts,
  restorePrompt,
  rollbackPrompt,
  updatePrompt,
  type PromptSummary,
  type PromptHistoryEntry,
} from "@/lib/admin-api";
import { Button } from "@/components/ui/button";
import { ToastStack, useToasts } from "@/components/admin/Toast";
import { PromptEditor } from "@/components/admin/PromptEditor";
import { cn } from "@/lib/utils";

// agent 색상은 globals.css 의 CSS 변수 키와 매칭. 트레이스 뷰어와 동일 토큰.
const AGENT_COLOR_VAR: Record<string, string> = {
  scout: "var(--agent-scout)",
  analyst: "var(--agent-analyst)",
  planner: "var(--agent-planner)",
  writer: "var(--agent-writer)",
  factchecker: "var(--agent-factchecker)",
  devils: "var(--agent-devils)",
  editor: "var(--agent-editor)",
  architect: "var(--agent-architect)",
  builder: "var(--agent-builder)",
  "judge-gemini": "var(--judge-gemini)",
  "judge-gpt": "var(--judge-gpt)",
  "judge-claude": "var(--judge-claude)",
};

function formatTimestamp(ts: string): string {
  // ts = YYYYMMDDTHHMMSS — UTC
  if (ts.length !== 15 || ts[8] !== "T") return ts;
  const y = ts.slice(0, 4);
  const mo = ts.slice(4, 6);
  const d = ts.slice(6, 8);
  const hh = ts.slice(9, 11);
  const mm = ts.slice(11, 13);
  const ss = ts.slice(13, 15);
  return `${y}-${mo}-${d} ${hh}:${mm}:${ss} UTC`;
}

export default function PersonasPage() {
  const qc = useQueryClient();
  const { toasts, push } = useToasts();

  const promptsQ = useQuery({
    queryKey: ["admin", "prompts"],
    queryFn: listPrompts,
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [dirty, setDirty] = useState(false);
  const [pendingSwitchId, setPendingSwitchId] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const list: PromptSummary[] = useMemo(
    () => promptsQ.data?.prompts ?? [],
    [promptsQ.data],
  );

  // 최초 로딩 시 첫 에이전트 자동 선택
  useEffect(() => {
    if (!selectedId && list.length > 0) {
      setSelectedId(list[0].agent_id);
    }
  }, [list, selectedId]);

  const detailQ = useQuery({
    queryKey: ["admin", "prompt-detail", selectedId],
    queryFn: () => getPrompt(selectedId!),
    enabled: !!selectedId,
  });

  useEffect(() => {
    if (detailQ.data) {
      setDraft(detailQ.data.content);
      setDirty(false);
    }
  }, [detailQ.data]);

  const historyQ = useQuery({
    queryKey: ["admin", "prompt-history", selectedId],
    queryFn: () => getPromptHistory(selectedId!),
    enabled: !!selectedId && historyOpen,
  });

  const saveM = useMutation({
    mutationFn: (content: string) => updatePrompt(selectedId!, content),
    onSuccess: () => {
      push("success", "저장 완료 — 다음 run 부터 반영");
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["admin", "prompts"] });
      qc.invalidateQueries({ queryKey: ["admin", "prompt-detail", selectedId] });
      qc.invalidateQueries({ queryKey: ["admin", "prompt-history", selectedId] });
    },
    onError: (err: unknown) => {
      push("error", `저장 실패: ${(err as Error).message}`);
    },
  });

  const restoreM = useMutation({
    mutationFn: () => restorePrompt(selectedId!),
    onSuccess: () => {
      push("success", "기본값 복원 완료");
      qc.invalidateQueries({ queryKey: ["admin", "prompt-detail", selectedId] });
      qc.invalidateQueries({ queryKey: ["admin", "prompt-history", selectedId] });
    },
    onError: (err: unknown) => {
      push("error", `복원 실패: ${(err as Error).message}`);
    },
  });

  const rollbackM = useMutation({
    mutationFn: (timestamp: string) => rollbackPrompt(selectedId!, timestamp),
    onSuccess: () => {
      push("success", "롤백 완료");
      setHistoryOpen(false);
      qc.invalidateQueries({ queryKey: ["admin", "prompt-detail", selectedId] });
      qc.invalidateQueries({ queryKey: ["admin", "prompt-history", selectedId] });
    },
    onError: (err: unknown) => {
      push("error", `롤백 실패: ${(err as Error).message}`);
    },
  });

  const handleSelect = (id: string) => {
    if (id === selectedId) return;
    if (dirty) {
      setPendingSwitchId(id);
      return;
    }
    setSelectedId(id);
  };

  const confirmSwitch = (discard: boolean) => {
    if (discard && pendingSwitchId) {
      setSelectedId(pendingSwitchId);
      setDirty(false);
    }
    setPendingSwitchId(null);
  };

  const selectedMeta = useMemo(
    () => list.find((p) => p.agent_id === selectedId) ?? null,
    [list, selectedId],
  );

  return (
    <div className="mx-auto w-full max-w-7xl">
      <header className="mb-6">
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          🎭 Persona Lab
        </h1>
        <p className="mt-1 font-korean text-sm text-text-secondary">
          9 에이전트 + 3 Judge 의 system prompt 를 코드 수정 없이 편집·복원·롤백합니다.
        </p>
      </header>

      <div className="grid grid-cols-12 gap-4">
        {/* 좌패널: 에이전트 리스트 */}
        <aside className="col-span-12 lg:col-span-3">
          <div className="sticky top-4 max-h-[calc(100vh-2rem)] overflow-y-auto rounded-xl border border-border-subtle bg-bg-elevated p-2">
            {promptsQ.isLoading && (
              <div className="px-3 py-2 font-korean text-xs text-text-muted">
                로딩…
              </div>
            )}
            {promptsQ.isError && (
              <div className="px-3 py-2 font-korean text-xs text-state-danger">
                API 응답 없음. 백엔드 기동 여부를 확인하세요.
              </div>
            )}
            {list.map((p) => {
              const active = p.agent_id === selectedId;
              const color = AGENT_COLOR_VAR[p.agent_id] ?? "var(--text-muted)";
              const isDirtyHere = active && dirty;
              return (
                <button
                  key={p.agent_id}
                  type="button"
                  onClick={() => handleSelect(p.agent_id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition",
                    active
                      ? "bg-bg-secondary text-text-primary"
                      : "text-text-secondary hover:bg-bg-secondary/60",
                  )}
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: color }}
                    aria-hidden
                  />
                  <span className="text-base leading-none">{p.emoji ?? "🤖"}</span>
                  <span className="font-korean text-sm">
                    {p.display_name ?? p.agent_id}
                  </span>
                  {isDirtyHere && (
                    <span
                      className="ml-auto h-1.5 w-1.5 rounded-full bg-accent-pink"
                      title="미저장 변경"
                    />
                  )}
                  {!isDirtyHere && p.version_count > 0 && (
                    <span className="ml-auto font-mono text-[10px] text-text-muted">
                      v{p.version_count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>

        {/* 우패널: 에디터 */}
        <section className="col-span-12 lg:col-span-9">
          <div className="rounded-xl border border-border-subtle bg-bg-elevated">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="text-xl">{selectedMeta?.emoji ?? "🎭"}</span>
                <div>
                  <div className="font-korean text-sm font-semibold text-text-primary">
                    {selectedMeta?.display_name ?? "에이전트 선택"}
                  </div>
                  <div className="font-mono text-[11px] text-text-muted">
                    {selectedMeta?.path ?? ""}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setHistoryOpen((v) => !v)}
                  disabled={!selectedId}
                >
                  버전 히스토리
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (!selectedId) return;
                    if (
                      window.confirm(
                        "현재 내용을 _defaults 스냅샷으로 되돌립니다. 진행할까요?",
                      )
                    ) {
                      restoreM.mutate();
                    }
                  }}
                  disabled={!selectedId || restoreM.isPending}
                >
                  기본값 복원
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => saveM.mutate(draft)}
                  disabled={!selectedId || !dirty || saveM.isPending}
                >
                  {saveM.isPending ? "저장 중…" : "저장"}
                </Button>
              </div>
            </div>

            {/* B3-S3-E §B2: Monaco Editor (next/dynamic ssr:false 로 마운트).
                저장/복원/히스토리 액션·dirty·경고 모달 로직은 그대로 재사용. */}
            <div className="relative">
              {!selectedId ? (
                <div className="flex h-[60vh] items-center justify-center font-korean text-sm text-text-muted">
                  좌측에서 에이전트를 선택하세요.
                </div>
              ) : detailQ.isLoading ? (
                <div className="flex h-[60vh] items-center justify-center font-korean text-sm text-text-muted">
                  프롬프트 로드 중…
                </div>
              ) : (
                <PromptEditor
                  value={draft}
                  onChange={(next) => {
                    setDraft(next);
                    if (!dirty) setDirty(true);
                  }}
                />
              )}
            </div>

            <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2 font-korean text-[11px] text-text-muted">
              <span>
                {dirty
                  ? "● 미저장 변경 있음"
                  : detailQ.data?.last_modified
                    ? `최종 수정: ${new Date(detailQ.data.last_modified).toLocaleString()}`
                    : "—"}
              </span>
              <span>
                {detailQ.data
                  ? `~${detailQ.data.estimated_tokens} tokens · ${draft.length.toLocaleString()} chars`
                  : ""}
              </span>
            </div>
          </div>

          {/* 히스토리 드로어 — Persona Lab 우측 패널 아래로 펼침 (모바일 친화) */}
          <AnimatePresence>
            {historyOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-4 rounded-xl border border-border-subtle bg-bg-elevated p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-korean text-sm font-semibold text-text-primary">
                    버전 히스토리 — {selectedMeta?.display_name}
                  </h3>
                  <button
                    type="button"
                    className="font-korean text-xs text-text-muted hover:text-text-primary"
                    onClick={() => setHistoryOpen(false)}
                  >
                    닫기
                  </button>
                </div>
                {historyQ.isLoading && (
                  <div className="font-korean text-xs text-text-muted">
                    로딩…
                  </div>
                )}
                {historyQ.data && historyQ.data.history.length === 0 && (
                  <div className="font-korean text-xs text-text-muted">
                    백업이 없습니다. 저장 시점부터 누적됩니다.
                  </div>
                )}
                <ul className="divide-y divide-border-subtle">
                  {historyQ.data?.history.map((h: PromptHistoryEntry) => (
                    <li
                      key={h.filename}
                      className="flex items-center justify-between py-2"
                    >
                      <div>
                        <div className="font-mono text-xs text-text-primary">
                          {h.version_id}
                        </div>
                        <div className="font-korean text-[11px] text-text-muted">
                          {formatTimestamp(h.timestamp)} · {h.size_bytes} bytes
                        </div>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          if (
                            window.confirm(
                              `${h.version_id} 으로 롤백합니다. 현재 내용은 history 에 백업됩니다.`,
                            )
                          ) {
                            rollbackM.mutate(h.timestamp);
                          }
                        }}
                        disabled={rollbackM.isPending}
                      >
                        이 버전으로 롤백
                      </Button>
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>

      {/* 미저장 상태 다른 에이전트 클릭 시 경고 모달 */}
      <AnimatePresence>
        {pendingSwitchId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
            onClick={() => setPendingSwitchId(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md rounded-xl border border-border-subtle bg-bg-elevated p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="font-korean text-base font-semibold text-text-primary">
                저장하지 않은 변경이 있습니다
              </h3>
              <p className="mt-2 font-korean text-sm text-text-secondary">
                다른 에이전트로 이동하면 변경이 사라집니다. 계속할까요?
              </p>
              <div className="mt-5 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => confirmSwitch(false)}
                >
                  머무르기
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => confirmSwitch(true)}
                >
                  변경 버리고 이동
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <ToastStack toasts={toasts} />

      <div className="mt-6 rounded-md border border-border-subtle bg-bg-secondary px-4 py-3 font-korean text-xs text-text-muted">
        ℹ️ 저장된 프롬프트는 다음 run 부터 반영됩니다. 백업·복원·롤백은{" "}
        <span className="text-accent-pink">컨테이너 파일</span>에 저장되며 재배포 시
        초기화됩니다 (ephemeral).
      </div>
    </div>
  );
}
