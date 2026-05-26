import type { MockRecentRun } from "@/types/run";
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

/**
 * 메인 페이지 "최근 실행" 카드 5건. 실제 backend SSE 가 붙기 전까지는 정적.
 * sessionId/finishedAt 는 B3-S2-E2E run 폴더에서 가져옴 (실측 메타).
 */
export const MOCK_RECENT_RUNS: MockRecentRun[] = [
  {
    sessionId: "2026-05-26T14-19-20_08a55b97",
    category: "food",
    title: "가족 식비, 매달 50만원 아끼는 법",
    weightedTotal: 50.2,
    finishedAt: "2026-05-26T14:27:00Z",
    status: "completed",
  },
  {
    sessionId: "2026-05-26T14-31-16_022af0b7",
    category: "safety",
    title: "우리 동네 지키는 지하철 필수 안전 수칙",
    weightedTotal: 56.5,
    finishedAt: "2026-05-26T14:39:52Z",
    status: "completed",
  },
  {
    sessionId: "2026-05-26T14-40-39_7cd79b5a",
    category: "ai-trend",
    title: "AI 어시스턴트: 바쁜 일상의 시간 절약 비법",
    weightedTotal: 59.2,
    finishedAt: "2026-05-26T14:48:10Z",
    status: "completed",
  },
  {
    sessionId: "2026-05-26T14-52-34_df9eb51a",
    category: "food",
    title: "성능별 단순: 진짜로 보이는 특별한 맛집",
    weightedTotal: 63.0,
    finishedAt: "2026-05-26T14:57:16Z",
    status: "partial",
  },
  {
    sessionId: "2026-05-25T22-46-12_demo01",
    category: "culture",
    title: "주말 한정 미술관 빅 이벤트 큐레이션",
    weightedTotal: 71.4,
    finishedAt: "2026-05-25T22:55:08Z",
    status: "completed",
  },
];

/** "Generate" 버튼이 만들어내는 mock session id. */
export function makeMockSessionId(prefix = "mock"): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const rand = Math.random().toString(16).slice(2, 10);
  return `${ts}_${prefix}_${rand}`;
}
