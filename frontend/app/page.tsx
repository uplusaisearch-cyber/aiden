"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { HeroHeader } from "@/components/main/hero-header";
import { CategoryCard } from "@/components/main/category-card";
import { CustomInputCard, type CustomInputPayload } from "@/components/main/custom-input-card";
import { PlanningModal } from "@/components/main/planning-modal";
import { RecentRuns } from "@/components/main/recent-runs";
import { Separator } from "@/components/ui/separator";
import { CATEGORY_PRESETS, type CategoryId } from "@/lib/constants";
import type { MockRecentRun } from "@/types/run";
import {
  fetchOutputs,
  startGenerate,
  type OutputSummary,
  type SelectionOverride,
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
  // B4-S2 후속: 프리셋 4 카테고리 클릭 시 angle/SEG 선택 모달 오픈.
  // 자유 입력은 이번 범위 X (모달 미오픈, 기존 카드 흐름 그대로).
  const [modalCategory, setModalCategory] = useState<CategoryId | null>(null);

  // 데이터 소스: outputs.db (영속). MOCK fallback 없음 — 빈 DB 는 빈 상태로 표시.
  // placeholderData = (prev) => prev 로 재요청 중 이전 데이터 유지 → 새로고침 외 깜빡임 0.
  // 첫 진입 (prev=undefined) 은 isLoading 으로 스켈레톤 노출, 데이터 도착 시 카드로 전환.
  const recentRunsQuery = useQuery({
    queryKey: ["outputs", "main-cards"],
    queryFn: () => fetchOutputs(6),
    placeholderData: (prev) => prev,
  });

  const generateMutation = useMutation({
    mutationFn: (payload: {
      category: ApiCategoryId;
      custom_topic?: string;
      selection_override?: SelectionOverride | null;
    }) => startGenerate(payload),
    onSuccess: (data) => router.push(`/run/${data.session_id}`),
  });

  const handleSelect = (id: CategoryId) => {
    if (id === "custom") {
      // 자유 입력은 카드 내부 토픽 입력 흐름이라 모달 미오픈.
      setSelected((prev) => (prev === id ? null : id));
      return;
    }
    // 프리셋 4 카테고리는 클릭 시 즉시 모달 오픈 (selected 상태 유지로 시각 강조)
    setSelected(id);
    setCustomExpanded(false);
    setModalCategory(id);
  };

  const handleConfirmModal = (override: SelectionOverride) => {
    if (!modalCategory || modalCategory === "custom") return;
    generateMutation.mutate({
      category: modalCategory as ApiCategoryId,
      selection_override:
        override.angle || override.audience_segment ? override : null,
    });
  };

  const handleGenerateCustom = (override: CustomInputPayload) => {
    generateMutation.mutate({
      category: "custom",
      custom_topic: override.topic,
    });
  };

  const runsForUI: MockRecentRun[] =
    recentRunsQuery.data?.outputs?.map(outputToMock) ?? [];

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
            onSubmit={handleGenerateCustom}
          />
        </div>

        {generateMutation.isError && (
          <p className="font-korean text-xs text-state-danger">
            생성 요청 실패: {(generateMutation.error as Error).message}
          </p>
        )}
      </section>

      <PlanningModal
        open={modalCategory !== null}
        category={modalCategory}
        onClose={() => setModalCategory(null)}
        onConfirm={handleConfirmModal}
        pending={generateMutation.isPending}
      />

      <Separator className="my-10 bg-border-subtle" />

      <section aria-labelledby="recent-heading">
        <RecentRuns
          runs={runsForUI}
          isLoading={recentRunsQuery.isLoading}
          isError={recentRunsQuery.isError}
          errorMessage={
            recentRunsQuery.error instanceof Error
              ? recentRunsQuery.error.message
              : undefined
          }
        />
      </section>
    </main>
  );
}
