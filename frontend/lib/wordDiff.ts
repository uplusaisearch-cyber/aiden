/**
 * 가벼운 단어 단위 diff.
 *
 * - LCS 백트래킹 1회 — 추가 의존성 없음.
 * - Writer 본문 비교용 (~1000자 / ~500 토큰 가정). 토큰 수가 너무 크면 line-level 폴백.
 * - 한국어/공백/구두점 모두 토큰 경계로 잡고 separator 자체도 토큰으로 유지.
 */

export type DiffStatus = "same" | "add" | "remove";
export interface DiffToken {
  text: string;
  status: DiffStatus;
}

export interface DiffResult {
  /** 좌측(원본 = a) 시점의 토큰 흐름. status=add 토큰은 없음. */
  left: DiffToken[];
  /** 우측(신본 = b) 시점의 토큰 흐름. status=remove 토큰은 없음. */
  right: DiffToken[];
  /** 정량 통계 — 헤더 뱃지에 사용 가능 */
  stats: { added: number; removed: number; same: number };
}

const MAX_TOKENS = 2000;

export function tokenize(s: string): string[] {
  if (!s) return [];
  return s.split(/(\s+|[.,!?·—:;\-()\[\]"'`]+)/).filter((t) => t.length > 0);
}

export function diffWords(a: string, b: string): DiffResult {
  const aw = tokenize(a);
  const bw = tokenize(b);

  // 너무 큰 입력은 비교 포기 — same 1덩어리로 표시
  if (aw.length > MAX_TOKENS || bw.length > MAX_TOKENS) {
    return {
      left: [{ text: a, status: "same" }],
      right: [{ text: b, status: "same" }],
      stats: { added: 0, removed: 0, same: aw.length },
    };
  }

  const m = aw.length;
  const n = bw.length;
  // dp[i][j] = LCS length for aw[0..i-1], bw[0..j-1]
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    new Array(n + 1).fill(0),
  );
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (aw[i - 1] === bw[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1;
      else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  const left: DiffToken[] = [];
  const right: DiffToken[] = [];
  let added = 0;
  let removed = 0;
  let same = 0;
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && aw[i - 1] === bw[j - 1]) {
      left.unshift({ text: aw[i - 1], status: "same" });
      right.unshift({ text: bw[j - 1], status: "same" });
      i--;
      j--;
      same++;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      right.unshift({ text: bw[j - 1], status: "add" });
      j--;
      added++;
    } else {
      left.unshift({ text: aw[i - 1], status: "remove" });
      i--;
      removed++;
    }
  }

  return { left, right, stats: { added, removed, same } };
}
