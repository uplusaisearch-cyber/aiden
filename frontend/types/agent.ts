export type AgentId =
  | "scout"
  | "analyst"
  | "planner"
  | "writer"
  | "factchecker"
  | "devils"
  | "editor"
  | "architect"
  | "builder"
  | "judge-gemini"
  | "judge-gpt"
  | "judge-claude";

export interface AgentCharacter {
  id: AgentId;
  emoji: string;
  nameKo: string;
  nameEn: string;
  color: string; // CSS variable reference (예: "var(--agent-scout)")
  tone: string;
  description: string;
}
