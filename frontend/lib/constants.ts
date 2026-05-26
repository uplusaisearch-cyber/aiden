import type { AgentCharacter, AgentId } from "@/types/agent";

/**
 * 12 에이전트 캐릭터 정의 (마스터 명세서 테이블 기반).
 * 9개 핵심 에이전트 + 3개 Judge 모델.
 */
export const AGENT_CHARACTERS: Record<AgentId, AgentCharacter> = {
  scout: {
    id: "scout",
    emoji: "🔍",
    nameKo: "트렌드 정찰병",
    nameEn: "Trend Scout",
    color: "var(--agent-scout)",
    tone: "정보 수집 보고체",
    description: "방금 X 트렌드 잡았습니다",
  },
  analyst: {
    id: "analyst",
    emoji: "📊",
    nameKo: "오디언스 분석가",
    nameEn: "Audience Analyst",
    color: "var(--agent-analyst)",
    tone: "데이터 기반 분석체",
    description: "이 페르소나엔 이 주제가 80% 맞습니다",
  },
  planner: {
    id: "planner",
    emoji: "🧭",
    nameKo: "전략 기획자",
    nameEn: "Strategy Planner",
    color: "var(--agent-planner)",
    tone: "기획 PD 톤",
    description: "이 앵글로 가시죠",
  },
  writer: {
    id: "writer",
    emoji: "✍️",
    nameKo: "작가",
    nameEn: "Writer",
    color: "var(--agent-writer)",
    tone: "친근·서사체",
    description: "초안 v{iter} 나왔습니다",
  },
  factchecker: {
    id: "factchecker",
    emoji: "🔬",
    nameKo: "팩트체커",
    nameEn: "Fact-Checker",
    color: "var(--agent-factchecker)",
    tone: "신중·근거 우선",
    description: "이 수치는 근거 부족, confidence 0.6",
  },
  devils: {
    id: "devils",
    emoji: "😈",
    nameKo: "악마의 변호인",
    nameEn: "Devil's Advocate",
    color: "var(--agent-devils)",
    tone: "공격적·날카로움",
    description: "이 글의 결정적 약점 3가지는…",
  },
  editor: {
    id: "editor",
    emoji: "🎯",
    nameKo: "편집장",
    nameEn: "Editor-in-Chief",
    color: "var(--agent-editor)",
    tone: "단호·결정",
    description: "iter2 수정 후 채택. 다음으로.",
  },
  architect: {
    id: "architect",
    emoji: "🏛️",
    nameKo: "포맷 설계자",
    nameEn: "Format Architect",
    color: "var(--agent-architect)",
    tone: "디자이너 톤",
    description: "B타입 + 퀴즈 인터랙티브로 가시죠",
  },
  builder: {
    id: "builder",
    emoji: "🔧",
    nameKo: "HTML 빌더",
    nameEn: "HTML Builder",
    color: "var(--agent-builder)",
    tone: "엔지니어 톤",
    description: "B-quiz 템플릿에 placeholder 14개 치환 완료",
  },
  "judge-gemini": {
    id: "judge-gemini",
    emoji: "🟦",
    nameKo: "심사위원 (Gemini)",
    nameEn: "Judge Gemini",
    color: "var(--judge-gemini)",
    tone: "분석적·차원별 데이터 인용",
    description: "정량 차원에서 가장 후한 평가",
  },
  "judge-gpt": {
    id: "judge-gpt",
    emoji: "🟢",
    nameKo: "심사위원 (GPT)",
    nameEn: "Judge GPT",
    color: "var(--judge-gpt)",
    tone: "균형·가독성 강조",
    description: "중도. 구조·실용성 판단",
  },
  "judge-claude": {
    id: "judge-claude",
    emoji: "🟧",
    nameKo: "심사위원 (Claude)",
    nameEn: "Judge Claude",
    color: "var(--judge-claude)",
    tone: "톤·뉘앙스 엄격",
    description: "tone_authenticity 가장 엄격",
  },
};

/**
 * 카테고리 프리셋 (메인 페이지 그리드용).
 */
export const CATEGORY_PRESETS = [
  { id: "food", label: "맛집", icon: "🍜", description: "주변 가성비·핫플 발굴" },
  { id: "ai-trend", label: "AI트렌드", icon: "🤖", description: "최신 AI 동향·도구 소개" },
  { id: "safety", label: "안전", icon: "🛡️", description: "생활 안전·예방 가이드" },
  { id: "culture", label: "문화", icon: "🎭", description: "전시·공연·여가" },
] as const;

export type CategoryId = (typeof CATEGORY_PRESETS)[number]["id"] | "custom";

export const CATEGORY_LABEL_MAP: Record<CategoryId, string> = {
  food: "맛집",
  "ai-trend": "AI트렌드",
  safety: "안전",
  culture: "문화",
  custom: "자유 입력",
};
