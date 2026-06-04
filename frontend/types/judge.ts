/**
 * Judge Panel 결과 타입 (backend/orchestrators/judge_panel.py 의 출력 스키마 미러).
 */

export type JudgeModelKey = "gemini" | "gpt" | "claude";
export type JudgeStatus = "completed" | "degraded" | "failed";
export type ResolutionSource = "config" | "env" | "runtime_override";
export type OutlierSeverity = "low" | "medium" | "high";

export interface JudgeScores {
  topic_fit: number;
  content_quality: number;
  interactivity: number;
  tone_authenticity: number;
  timeliness_trust: number;
}

export interface JudgeEvaluation {
  model: string;
  scores: JudgeScores;
  comments: Record<keyof JudgeScores, string>;
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
  one_line_verdict: string;
}

export interface JudgeOutlier {
  dimension: keyof JudgeScores;
  model: JudgeModelKey;
  score: number;
  mean: number;
  delta: number;
  outlier_severity: OutlierSeverity;
}

export interface JudgeAggregate {
  mean_scores: JudgeScores;
  stdev_scores: JudgeScores;
  weighted_total: number;
  outliers: JudgeOutlier[];
}

export interface JudgePanelResult {
  stage: 4;
  status: JudgeStatus;
  input_source: string;
  input_size_bytes: number;
  models_used: Record<JudgeModelKey, string>;
  models_resolution_source: Record<JudgeModelKey, ResolutionSource>;
  evaluations: Partial<Record<JudgeModelKey, JudgeEvaluation>>;
  aggregate: JudgeAggregate | null;
  failed_models: JudgeModelKey[];
  duration_ms: number;
  cost_usd_estimate: number;
}

// ---------------------------------------------------------------
// B3-S3-D — Judge 시각화 응답 (어댑터 적용된 새 스키마)
// 백엔드 backend/api/schemas/judge.py 의 JudgeResult 와 1:1 매칭.
// ---------------------------------------------------------------

export type ConsensusLevel = "high" | "medium" | "low";

export interface CriterionScore {
  topic_fit: number;
  content_quality: number;
  interactivity: number;
  tone_authenticity: number;
  timeliness_trust: number;
}

export interface ModelEvaluation {
  model_id: JudgeModelKey;
  model_name: string;
  scores: CriterionScore;
  overall: number;
  comment: string;
  is_outlier: boolean;
}

export interface JudgeResult {
  run_id: string;
  evaluations: ModelEvaluation[];
  aggregate: CriterionScore;
  aggregate_overall: number;
  consensus_level: ConsensusLevel;
  timestamp: string;
}

export interface FinalHtmlMeta {
  available: boolean;
  url: string | null;
  size_bytes: number | null;
}

// 5축 메타 (UI 라벨 / 키 매핑 단일 출처)
export const AXIS_META: ReadonlyArray<{
  key: keyof CriterionScore;
  label: string;
}> = [
  { key: "topic_fit", label: "타깃 적합성" },
  { key: "content_quality", label: "콘텐츠 품질" },
  { key: "interactivity", label: "인터랙티브" },
  { key: "tone_authenticity", label: "톤 진정성" },
  { key: "timeliness_trust", label: "출처 신뢰" },
];

// 모델별 디자인 토큰 — 페르소나 palette 와 분리, Judge 전용
export const MODEL_COLORS: Record<JudgeModelKey, string> = {
  gemini: "#4285F4", // Google blue
  gpt: "#10A37F", // OpenAI green
  claude: "#CC785C", // Anthropic terra
};

export const MODEL_DISPLAY_NAME: Record<JudgeModelKey, string> = {
  gemini: "Gemini",
  gpt: "GPT",
  claude: "Claude",
};
