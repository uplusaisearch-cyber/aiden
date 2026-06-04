import { useEffect, useState } from "react";

/**
 * 0 → target 까지 easeOutQuart 보간으로 카운트업.
 *
 * - target 변경 시 다시 0 부터 시작
 * - SSR safe: useEffect 안에서만 rAF 사용
 * - durationMs 기본 1200ms
 */
export function useCountUp(target: number, durationMs = 1200): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(target) || target === 0) {
      setValue(target);
      return;
    }
    let raf = 0;
    const start = performance.now();

    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / durationMs);
      // easeOutQuart
      const eased = 1 - Math.pow(1 - t, 4);
      setValue(target * eased);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return value;
}
