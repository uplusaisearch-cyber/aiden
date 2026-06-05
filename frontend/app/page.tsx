"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { HeroHeader } from "@/components/main/hero-header";
import { CategoryCard } from "@/components/main/category-card";
import { CustomInputCard, type CustomInputPayload } from "@/components/main/custom-input-card";
import { RecentRuns } from "@/components/main/recent-runs";
import { Separator } from "@/components/ui/separator";
import { CATEGORY_PRESETS, type CategoryId } from "@/lib/constants";
import { MOCK_RECENT_RUNS } from "@/lib/mock-data";
import type { MockRecentRun } from "@/types/run";
import {
  fetchOutputs,
  startGenerate,
  type OutputSummary,
  type CategoryId as ApiCategoryId,
} from "@/lib/api";

function outputToMock(o: OutputSummary): MockRecentRun {
  // outputs.db 는 정상 종료된 run 만 저장 → status 는 항상 "completed".
  const category = (o.category ?? "custom") as MockRecentRun["category"];
  return {
    sessionId: o.run_id,
    category,
    title: o.topic ?? "(제목 없음)",
    weightedTotal: o.weighted_score ?? 0,
    finishedAt: o.created_at ?? new Date().toISOString(),
    status: "completed",
  };
}

export default function HomePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<CategoryId | null>(null);
  const [customExpanded, setCustomExpanded] = useState(false);

  // 데이터 소스: outputs.db (영속). API 실패 또는 빈 DB 시 mock fallback.
  const recentRunsQuery = useQuery({
    queryKey: ["outputs", "main-cards"],
    queryFn: () => fetchOutputs(6),
  });

  const generateMutation = useMutation({
    mutationFn: (payload: { category: ApiCategoryId; custom_topic?: string }) =>
      startGenerate(payload),
    onSuccess: (data) => router.push(`/run/${data.session_id}`),
  });

  const handleSelect = (id: CategoryId) => {
    setSelected((prev) => (prev === id ? null : id));
    setCustomExpanded(false);
  };

  const handleGenerate = (override?: CustomInputPayload) => {
    if (override) {
      generateMutation.mutate({
        category: "custom",
        custom_topic: override.topic,
      });
      return;
    }
    if (!selected || selected === "custom") return;
    generateMutation.mutate({ category: selected as ApiCategoryId });
  };

  // API 성공 + 데이터 있음 → outputs.db. 빈 DB 또는 API 실패 → mock fallback.
  const dbRuns: MockRecentRun[] =
    recentRunsQuery.data?.outputs?.map(outputToMock) ?? [];
  const runsForUI: MockRecentRun[] = dbRuns.length > 0 ? dbRuns : MOCK_RECENT_RUNS;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-4 pb-16 sm:px-6">
      <HeroHeader />

      <Separator className="my-6 bg-border-subtle" />

      <section aria-labelledby="category-heading" className="space-y-4">
        <h2
          id="category-heading"
          className="font-korean text-lg font-semibold text-text-primary sm:text-xl"
        >
          콘텐츠 카테고리를 선택하세요
        </h2>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
          {CATEGORY_PRESETS.map((preset) => (
            <CategoryCard
              key={preset.id}
              category={preset.id}
              selected={selected === preset.id}
              onSelect={() => handleSelect(preset.id)}
            />
          ))}

          <CustomInputCard
            expanded={customExpanded}
            onExpand={() => {
              setSelected("custom");
              setCustomExpanded(true);
            }}
            onCollapse={() => {
              setCustomExpanded(false);
              if (selected === "custom") setSelected(null);
            }}
            onSubmit={handleGenerate}
          />
        </div>

        <AnimatePresence>
          {selected && selected !== "custom" && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="flex justify-end pt-2"
            >
              <button
                type="button"
                onClick={() => handleGenerate()}
                disabled={generateMutation.isPending}
                className="rounded-md bg-accent-pink px-6 py-2 text-sm font-semibold text-white transition hover:bg-accent-pink-hover disabled:cursor-wait disabled:opacity-60 sm:text-base"
              >
                {generateMutation.isPending ? "시작 중…" : "Generate"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {generateMutation.isError && (
          <p className="font-korean text-xs text-state-danger">
            생성 요청 실패: {(generateMutation.error as Error).message}
          </p>
        )}
      </section>

      <Separator className="my-10 bg-border-subtle" />

      <section aria-labelledby="recent-heading">
        <RecentRuns runs={runsForUI} />
        {recentRunsQuery.isError && (
          <p className="mt-3 font-korean text-xs text-text-muted">
            (API 미응답 — mock 데이터 표시 중)
          </p>
        )}
      </section>
    </main>
  );
}
