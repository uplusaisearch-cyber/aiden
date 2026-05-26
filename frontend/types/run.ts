import type { CategoryId } from "@/lib/constants";

export type RunStatus = "completed" | "partial" | "failed" | "running";

export interface MockRecentRun {
  sessionId: string;
  category: CategoryId;
  title: string;
  weightedTotal: number; // 0-100
  finishedAt: string; // ISO 8601
  status: RunStatus;
}
