import Link from "next/link";
import { Settings } from "lucide-react";

export function HeroHeader() {
  return (
    <header className="relative w-full pt-12 pb-6 sm:pt-20 sm:pb-10">
      {/* /admin link — placeholder. 실제 페이지는 B3-S3-E */}
      <Link
        href="/admin"
        className="absolute right-4 top-4 inline-flex items-center gap-1.5 rounded-md border border-border-subtle bg-bg-elevated px-2.5 py-1.5 text-xs text-text-secondary transition hover:border-border-strong hover:text-text-primary sm:right-8 sm:top-8 sm:px-3 sm:py-2 sm:text-sm"
      >
        <Settings className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
        <span className="hidden sm:inline">Admin</span>
      </Link>

      <div className="mx-auto flex max-w-3xl flex-col items-start gap-2 px-4 sm:items-center sm:px-6 sm:text-center">
        <h1
          className="text-4xl font-extrabold tracking-tight sm:text-6xl pink-glow"
          style={{ color: "var(--accent-pink)" }}
        >
          AIDEN
        </h1>
        <p className="font-korean text-sm text-text-secondary sm:text-base">
          AI Deliberation Engine for Newsroom
        </p>
        <p className="font-korean text-xs text-text-muted sm:text-sm">
          9 AI 에이전트가 토론으로 플러스탭 콘텐츠를 만듭니다.
        </p>
      </div>
    </header>
  );
}
