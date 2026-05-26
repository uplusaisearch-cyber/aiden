"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { HeroHeader } from "@/components/main/hero-header";
import { CategoryCard } from "@/components/main/category-card";
import { CustomInputCard, type CustomInputPayload } from "@/components/main/custom-input-card";
import { RecentRuns } from "@/components/main/recent-runs";
import { Separator } from "@/components/ui/separator";
import { CATEGORY_PRESETS, type CategoryId } from "@/lib/constants";
import { MOCK_RECENT_RUNS, makeMockSessionId } from "@/lib/mock-data";

export default function HomePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<CategoryId | null>(null);
  const [customExpanded, setCustomExpanded] = useState(false);

  const handleSelect = (id: CategoryId) => {
    setSelected((prev) => (prev === id ? null : id));
    setCustomExpanded(false);
  };

  const handleGenerate = (override?: CustomInputPayload) => {
    const session = makeMockSessionId();
    // 실제 백엔드 호출은 B3-S3-B 에서. 본 명세서는 라우팅만.
    void override; // payload 는 mock 단계에서 사용 안 함
    router.push(`/run/${session}`);
  };

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
                className="rounded-md bg-accent-pink px-6 py-2 text-sm font-semibold text-white transition hover:bg-accent-pink-hover sm:text-base"
              >
                Generate
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <Separator className="my-10 bg-border-subtle" />

      <section aria-labelledby="recent-heading">
        <RecentRuns runs={MOCK_RECENT_RUNS} />
      </section>
    </main>
  );
}
