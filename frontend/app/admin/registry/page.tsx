"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  createTopic,
  deleteTopic,
  listTopics,
  patchTopic,
  type TopicCategory,
  type TopicEntry,
  type TopicStatus,
} from "@/lib/admin-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ToastStack, useToasts } from "@/components/admin/Toast";
import { cn } from "@/lib/utils";

const CATEGORIES: Array<{ id: TopicCategory; label: string }> = [
  { id: "food", label: "맛집" },
  { id: "ai_trend", label: "AI 트렌드" },
  { id: "safety", label: "안전" },
  { id: "culture", label: "문화" },
  { id: "free", label: "기타" },
];

const STATUSES: Array<{ id: TopicStatus; label: string; className: string }> = [
  {
    id: "published",
    label: "published",
    className: "bg-state-success/20 text-state-success",
  },
  {
    id: "rejected",
    label: "rejected",
    className: "bg-state-danger/20 text-state-danger",
  },
  {
    id: "expired",
    label: "expired",
    className: "bg-bg-secondary text-text-muted",
  },
];

function StatusBadge({ status }: { status: TopicStatus }) {
  const meta = STATUSES.find((s) => s.id === status);
  return (
    <span
      className={cn(
        "rounded-md px-2 py-0.5 font-mono text-[11px]",
        meta?.className ?? "bg-bg-secondary text-text-secondary",
      )}
    >
      {status}
    </span>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function RegistryPage() {
  const qc = useQueryClient();
  const { toasts, push } = useToasts();

  const [statusFilter, setStatusFilter] = useState<TopicStatus | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<TopicCategory | "all">(
    "all",
  );
  const [modalOpen, setModalOpen] = useState(false);

  const topicsQ = useQuery({
    queryKey: ["admin", "registry", statusFilter, categoryFilter],
    queryFn: () =>
      listTopics({
        status: statusFilter === "all" ? undefined : statusFilter,
        category: categoryFilter === "all" ? undefined : categoryFilter,
      }),
  });

  const createM = useMutation({
    mutationFn: createTopic,
    onSuccess: () => {
      push("success", "토픽 추가 완료");
      setModalOpen(false);
      qc.invalidateQueries({ queryKey: ["admin", "registry"] });
      qc.invalidateQueries({ queryKey: ["admin", "registry", "all"] });
    },
    onError: (err: unknown) =>
      push("error", `추가 실패: ${(err as Error).message}`),
  });

  const patchM = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TopicStatus }) =>
      patchTopic(id, { status }),
    onSuccess: () => {
      push("info", "상태 변경 완료");
      qc.invalidateQueries({ queryKey: ["admin", "registry"] });
    },
    onError: (err: unknown) =>
      push("error", `상태 변경 실패: ${(err as Error).message}`),
  });

  const deleteM = useMutation({
    mutationFn: deleteTopic,
    onSuccess: () => {
      push("info", "삭제 완료");
      qc.invalidateQueries({ queryKey: ["admin", "registry"] });
    },
    onError: (err: unknown) =>
      push("error", `삭제 실패: ${(err as Error).message}`),
  });

  const topics: TopicEntry[] = useMemo(
    () => topicsQ.data?.topics ?? [],
    [topicsQ.data],
  );

  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-korean text-2xl font-bold text-text-primary">
            📚 발행 이력
          </h1>
          <p className="mt-1 font-korean text-sm text-text-secondary">
            Topic Scout 가 다음 run 부터 회피할 토픽 레지스트리입니다.
          </p>
        </div>
        <Button type="button" onClick={() => setModalOpen(true)}>
          + 토픽 추가
        </Button>
      </header>

      {/* 필터 */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="font-korean text-xs text-text-muted">상태</span>
          <select
            className="rounded-md border border-border-subtle bg-bg-secondary px-2 py-1 text-xs text-text-primary"
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as TopicStatus | "all")
            }
          >
            <option value="all">전체</option>
            {STATUSES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <span className="font-korean text-xs text-text-muted">카테고리</span>
          <select
            className="rounded-md border border-border-subtle bg-bg-secondary px-2 py-1 text-xs text-text-primary"
            value={categoryFilter}
            onChange={(e) =>
              setCategoryFilter(e.target.value as TopicCategory | "all")
            }
          >
            <option value="all">전체</option>
            {CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        {topicsQ.isLoading && (
          <span className="ml-auto font-korean text-xs text-text-muted">
            로딩…
          </span>
        )}
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto rounded-xl border border-border-subtle bg-bg-elevated">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left font-korean text-[11px] uppercase tracking-wider text-text-muted">
              <th className="px-4 py-2">토픽</th>
              <th className="px-3 py-2">카테고리</th>
              <th className="px-3 py-2">상태</th>
              <th className="px-3 py-2">발행</th>
              <th className="px-3 py-2">만료</th>
              <th className="px-3 py-2 text-right">액션</th>
            </tr>
          </thead>
          <tbody>
            {topics.length === 0 && !topicsQ.isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center">
                  <div className="font-korean text-sm text-text-muted">
                    아직 발행 이력이 없습니다.
                  </div>
                  <div className="mt-2 font-korean text-xs text-text-muted">
                    + 토픽 추가 로 시작하세요.
                  </div>
                </td>
              </tr>
            )}
            {topics.map((t) => (
              <tr key={t.id} className="border-b border-border-subtle/60">
                <td className="max-w-md truncate px-4 py-2 font-korean text-text-primary">
                  {t.topic}
                  {t.rejected_similar_to && (
                    <Badge variant="ghost" className="ml-2">
                      유사: {t.rejected_similar_to.slice(0, 12)}…
                    </Badge>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-text-secondary">
                  {t.category}
                </td>
                <td className="px-3 py-2">
                  <select
                    value={t.status}
                    onChange={(e) =>
                      patchM.mutate({
                        id: t.id,
                        status: e.target.value as TopicStatus,
                      })
                    }
                    className="cursor-pointer rounded-md bg-bg-secondary px-2 py-1 font-mono text-[11px] text-text-primary"
                  >
                    {STATUSES.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                  <span className="ml-2 align-middle">
                    <StatusBadge status={t.status} />
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-text-muted">
                  {formatDate(t.published_at)}
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-text-muted">
                  {formatDate(t.expiry)}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (window.confirm(`삭제: ${t.topic}`)) {
                        deleteM.mutate(t.id);
                      }
                    }}
                    className="text-state-danger hover:text-state-danger"
                  >
                    삭제
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 추가 모달 */}
      <AnimatePresence>
        {modalOpen && (
          <CreateTopicModal
            onClose={() => setModalOpen(false)}
            onSubmit={(payload) => createM.mutate(payload)}
            pending={createM.isPending}
          />
        )}
      </AnimatePresence>

      <ToastStack toasts={toasts} />
    </div>
  );
}

function CreateTopicModal({
  onClose,
  onSubmit,
  pending,
}: {
  onClose: () => void;
  onSubmit: (payload: {
    topic: string;
    category: TopicCategory;
    status: TopicStatus;
    expiry?: string | null;
  }) => void;
  pending: boolean;
}) {
  const [topic, setTopic] = useState("");
  const [category, setCategory] = useState<TopicCategory>("food");
  const [status, setStatus] = useState<TopicStatus>("published");
  const [expiry, setExpiry] = useState("");

  const submit = () => {
    if (!topic.trim()) return;
    onSubmit({
      topic: topic.trim(),
      category,
      status,
      expiry: expiry ? new Date(expiry).toISOString() : null,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-md rounded-xl border border-border-subtle bg-bg-elevated p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-korean text-base font-semibold text-text-primary">
          토픽 추가
        </h3>
        <div className="mt-4 space-y-3">
          <label className="block">
            <span className="font-korean text-xs text-text-secondary">토픽</span>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="예: 강남 디저트 카페 5선"
              className="mt-1"
            />
          </label>
          <label className="block">
            <span className="font-korean text-xs text-text-secondary">
              카테고리
            </span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as TopicCategory)}
              className="mt-1 h-10 w-full rounded-md border border-border-subtle bg-bg-secondary px-3 text-sm text-text-primary"
            >
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label} ({c.id})
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-korean text-xs text-text-secondary">상태</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as TopicStatus)}
              className="mt-1 h-10 w-full rounded-md border border-border-subtle bg-bg-secondary px-3 text-sm text-text-primary"
            >
              {STATUSES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-korean text-xs text-text-secondary">
              만료 (선택)
            </span>
            <Input
              type="datetime-local"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="mt-1"
            />
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            취소
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={submit}
            disabled={pending || !topic.trim()}
          >
            {pending ? "추가 중…" : "추가"}
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
