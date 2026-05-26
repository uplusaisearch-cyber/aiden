import { AGENT_CHARACTERS } from "@/lib/constants";
import type { AgentId } from "@/types/agent";
import { cn } from "@/lib/utils";

type Size = "sm" | "md" | "lg";

const SIZE_MAP: Record<Size, { px: number; text: string }> = {
  sm: { px: 24, text: "text-xs" },
  md: { px: 36, text: "text-base" },
  lg: { px: 56, text: "text-2xl" },
};

interface Props {
  agentId: AgentId;
  size?: Size;
  className?: string;
  /** 라벨(에이전트 이름 한국어) 노출 여부. 트레이스 뷰어에선 false. */
  showLabel?: boolean;
}

export function AgentAvatar({ agentId, size = "md", className, showLabel = false }: Props) {
  const ch = AGENT_CHARACTERS[agentId];
  const dim = SIZE_MAP[size];

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div
        className={cn("inline-flex items-center justify-center rounded-full shrink-0", dim.text)}
        style={{
          width: dim.px,
          height: dim.px,
          backgroundColor: `${ch.color}33`, // 20% alpha tint
          color: ch.color,
          border: `1px solid ${ch.color}66`,
        }}
        aria-label={`${ch.nameKo} (${ch.nameEn})`}
      >
        <span>{ch.emoji}</span>
      </div>
      {showLabel && (
        <span className="font-korean text-text-secondary text-sm">{ch.nameKo}</span>
      )}
    </div>
  );
}
