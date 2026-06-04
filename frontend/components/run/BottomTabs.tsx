"use client";

import { useState } from "react";

import { FinalHtmlPreview } from "./FinalHtmlPreview";
import { JudgePanel } from "./JudgePanel";

type TabKey = "judge" | "final";

interface Props {
  runId: string;
  defaultTab?: TabKey;
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function TabButton({ active, onClick, children }: TabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className="relative rounded-t-lg px-4 py-2 text-sm font-semibold transition-colors duration-200"
      style={{
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
        background: active ? "var(--bg-secondary)" : "transparent",
      }}
    >
      {children}
      {active && (
        <span
          className="absolute inset-x-3 -bottom-px h-0.5 rounded-full"
          style={{ background: "var(--accent-pink)" }}
          aria-hidden
        />
      )}
    </button>
  );
}

export function BottomTabs({ runId, defaultTab = "judge" }: Props) {
  const [tab, setTab] = useState<TabKey>(defaultTab);

  return (
    <section
      className="mt-6 border-t pt-4"
      style={{ borderColor: "var(--border-strong)" }}
    >
      <div role="tablist" className="flex gap-1 px-1">
        <TabButton active={tab === "judge"} onClick={() => setTab("judge")}>
          🎯 판정 (3-Model Judge)
        </TabButton>
        <TabButton active={tab === "final"} onClick={() => setTab("final")}>
          📄 결과물 미리보기
        </TabButton>
      </div>
      <div
        className="rounded-xl rounded-tl-none"
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {tab === "judge" && <JudgePanel key="judge" runId={runId} />}
        {tab === "final" && <FinalHtmlPreview key="final" runId={runId} />}
      </div>
    </section>
  );
}
