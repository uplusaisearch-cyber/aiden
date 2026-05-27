/**
 * 인스턴트 / 애니메이션 재생 토글 — 라이브 run 에서는 비활성.
 *
 * 명세 §8-2. URL query param (`?playback=animate`) 공유 가능.
 * (현재는 UI 토글만 — 실제 타이핑 시뮬 효과는 후속 단계.)
 */
"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface PlaybackToggleProps {
  disabled?: boolean;
}

const QS_KEY = "playback";

export function PlaybackToggle({ disabled = false }: PlaybackToggleProps) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const mode = (params.get(QS_KEY) === "animate" ? "animate" : "instant") as
    | "instant"
    | "animate";

  const setMode = (next: "instant" | "animate") => {
    if (disabled) return;
    const sp = new URLSearchParams(params.toString());
    if (next === "instant") sp.delete(QS_KEY);
    else sp.set(QS_KEY, "animate");
    const q = sp.toString();
    router.replace(`${pathname}${q ? `?${q}` : ""}`);
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-border-subtle bg-bg-elevated p-1 text-xs",
        disabled && "opacity-60",
      )}
      title={
        disabled
          ? "라이브 스트림은 실시간 표시됩니다"
          : "재생 모드를 전환합니다"
      }
    >
      <button
        type="button"
        onClick={() => setMode("instant")}
        disabled={disabled}
        className={cn(
          "rounded px-2 py-1 font-korean transition",
          mode === "instant"
            ? "bg-accent-pink text-white"
            : "text-text-secondary hover:text-text-primary",
        )}
      >
        인스턴트
      </button>
      <button
        type="button"
        onClick={() => setMode("animate")}
        disabled={disabled}
        className={cn(
          "rounded px-2 py-1 font-korean transition",
          mode === "animate"
            ? "bg-accent-pink text-white"
            : "text-text-secondary hover:text-text-primary",
        )}
      >
        재생
      </button>
    </div>
  );
}
