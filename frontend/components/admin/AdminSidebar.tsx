"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  emoji: string;
}

const NAV: NavItem[] = [
  { href: "/admin", label: "대시보드", emoji: "📊" },
  { href: "/admin/personas", label: "Persona Lab", emoji: "🎭" },
  { href: "/admin/registry", label: "발행 이력", emoji: "📚" },
  { href: "/admin/keys", label: "API 키", emoji: "🔑" },
  { href: "/admin/settings", label: "운영 옵션", emoji: "⚙️" },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border-subtle bg-bg-secondary px-3 py-5 md:flex">
      <Link
        href="/"
        className="mb-6 flex items-center gap-2 px-2 text-sm text-text-secondary transition hover:text-accent-pink"
      >
        <span className="text-base">←</span>
        <span className="font-korean">AIDEN 메인</span>
      </Link>
      <div className="mb-4 px-2 font-korean text-xs uppercase tracking-wider text-text-muted">
        Admin Console
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const active =
            item.href === "/admin"
              ? pathname === "/admin"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 font-korean text-sm transition",
                active
                  ? "bg-accent-pink-soft text-accent-pink"
                  : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary",
              )}
            >
              <span className="text-base leading-none">{item.emoji}</span>
              <span>{item.label}</span>
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent-pink" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-md border border-border-subtle bg-bg-elevated px-3 py-3 text-[11px] leading-relaxed text-text-muted">
        <div className="mb-1 font-korean font-medium text-text-secondary">
          ephemeral 안내
        </div>
        프롬프트 백업·API 키·발행 이력은 모두 메모리 또는 컨테이너 파일에 저장됩니다.
        재배포 시 초기화됩니다.
      </div>
    </aside>
  );
}
