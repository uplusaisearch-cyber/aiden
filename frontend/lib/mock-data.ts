import type { JudgePanelResult } from "@/types/judge";
import judgeRun1 from "./mocks/run1_food_restaurant.json";
import judgeRun2 from "./mocks/run2_safety.json";
import judgeRun3 from "./mocks/run3_ai_trends.json";
import judgeRun4 from "./mocks/run4_env_override.json";

/**
 * B3-S2-E2E 실측 산출물 4건을 그대로 mock 으로 활용.
 * JSON 의 outlier_severity 등 enum 문자열은 runtime 검증 없이 cast.
 */
export const MOCK_JUDGE_DATA = {
  food: judgeRun1 as unknown as JudgePanelResult,
  safety: judgeRun2 as unknown as JudgePanelResult,
  "ai-trend": judgeRun3 as unknown as JudgePanelResult,
  "env-override": judgeRun4 as unknown as JudgePanelResult,
};

/** "Generate" 버튼이 만들어내는 mock session id. */
export function makeMockSessionId(prefix = "mock"): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const rand = Math.random().toString(16).slice(2, 10);
  return `${ts}_${prefix}_${rand}`;
}
