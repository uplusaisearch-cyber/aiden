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
