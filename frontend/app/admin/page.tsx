"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { listPrompts, listKeys, listTopics } from "@/lib/admin-api";
import { fetchRecentRuns } from "@/lib/api";
import { cn } from "@/lib/utils";

interface StatCardProps {
  href: string;
  emoji: string;
  label: string;
  value: string;
  hint: string;
  accent?: boolean;
}

function StatCard({ href, emoji, label, value, hint, accent }: StatCardProps) {
  return (
    <Link href={href} className="block">
      <motion.div
        whileHover={{ y: -3 }}
        className={cn(
          "h-full rounded-xl border border-border-subtle bg-bg-elevated p-5 transition",
          "hover:border-accent-pink/60 hover:shadow-[0_0_24px_-12px_rgba(255,46,152,0.6)]",
          accent && "border-accent-pink/40",
        )}
      >
        <div className="flex items-center justify-between">
          <span className="text-2xl leading-none">{emoji}</span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider",
              accent
                ? "bg-accent-pink-soft text-accent-pink"
                : "bg-bg-secondary text-text-muted",
            )}
          >
            {hint}
          </span>
        </div>
        <div className="mt-4 font-mono text-3xl text-text-primary">{value}</div>
        <div className="mt-1 font-korean text-sm text-text-secondary">
          {label}
        </div>
      </motion.div>
    </Link>
  );
}

export default function AdminDashboard() {
  const prompts = useQuery({
    queryKey: ["admin", "prompts"],
    queryFn: listPrompts,
  });
  const keys = useQuery({
    queryKey: ["admin", "keys"],
    queryFn: listKeys,
  });
  const topics = useQuery({
    queryKey: ["admin", "registry", "all"],
    queryFn: () => listTopics(),
  });
  const recent = useQuery({
    queryKey: ["recent-runs", "admin-dashboard"],
    queryFn: () => fetchRecentRuns(20),
  });

  const agentCount = prompts.data?.prompts.length ?? 0;
  const recentRuns = recent.data?.length ?? 0;
  const publishedTopics =
    topics.data?.topics.filter((t) => t.status === "published").length ?? 0;
  const runtimeKeyCount =
    keys.data?.keys.filter((k) => k.source === "runtime").length ?? 0;
  const envKeyCount =
    keys.data?.keys.filter((k) => k.source === "env").length ?? 0;
  const missingKeyCount =
    keys.data?.keys.filter((k) => k.source === "none").length ?? 0;

  const keysHint =
    runtimeKeyCount > 0
      ? `런타임 ${runtimeKeyCount}`
      : missingKeyCount > 0
        ? `미설정 ${missingKeyCount}`
        : `env ${envKeyCount}`;

  return (
    <div className="mx-auto w-full max-w-5xl">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="font-korean text-2xl font-bold text-text-primary">
            Admin Dashboard
          </h1>
          <p className="mt-1 font-korean text-sm text-text-secondary">
            9 에이전트 페르소나·키·발행 이력을 한 화면에서 운영하세요.
          </p>
        </div>
        <Link
          href="/"
          className="font-korean text-xs text-text-muted hover:text-accent-pink"
        >
          ← 메인으로
        </Link>
      </header>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          href="/admin/personas"
          emoji="🎭"
          label="에이전트 프롬프트"
          value={`${agentCount}`}
          hint="9 + 3 judges"
        />
        <StatCard
          href="/"
          emoji="🏃"
          label="최근 Run"
          value={`${recentRuns}`}
          hint="recent"
        />
        <StatCard
          href="/admin/registry"
          emoji="📚"
          label="발행된 토픽"
          value={`${publishedTopics}`}
          hint="published"
        />
        <StatCard
          href="/admin/keys"
          emoji="🔑"
          label="API 키 상태"
          value={`${(keys.data?.keys.length ?? 3) - missingKeyCount}/${keys.data?.keys.length ?? 3}`}
          hint={keysHint}
          accent={runtimeKeyCount > 0 || missingKeyCount > 0}
        />
      </section>

      <section className="mt-10">
        <h2 className="mb-3 font-korean text-lg font-semibold text-text-primary">
          빠른 액션
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link
            href="/admin/personas"
            className="rounded-md border border-border-subtle bg-bg-elevated px-4 py-3 font-korean text-sm text-text-secondary transition hover:border-accent-pink hover:text-text-primary"
          >
            🎨 Persona Lab — 에이전트 system prompt 편집
          </Link>
          <Link
            href="/admin/keys"
            className="rounded-md border border-border-subtle bg-bg-elevated px-4 py-3 font-korean text-sm text-text-secondary transition hover:border-accent-pink hover:text-text-primary"
          >
            🔑 API 키 — 런타임 임시 키 적용/해제
          </Link>
          <Link
            href="/admin/registry"
            className="rounded-md border border-border-subtle bg-bg-elevated px-4 py-3 font-korean text-sm text-text-secondary transition hover:border-accent-pink hover:text-text-primary"
          >
            📚 발행 이력 — Topic Scout 중복 토픽 회피
          </Link>
          <Link
            href="/admin/settings"
            className="rounded-md border border-border-subtle bg-bg-elevated px-4 py-3 font-korean text-sm text-text-secondary transition hover:border-accent-pink hover:text-text-primary"
          >
            ⚙️ 운영 옵션 — max_iter / 안전 모드 등
          </Link>
        </div>
      </section>

      <section className="mt-10 rounded-md border border-border-subtle bg-bg-secondary px-4 py-3 font-korean text-xs text-text-muted">
        ℹ️ 어드민 변경은 모두 <span className="text-accent-pink">ephemeral</span>{" "}
        입니다. 서버 재시작·재배포 시 .env 값으로 돌아갑니다.
      </section>
    </div>
  );
}
