"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  clearKey,
  listKeys,
  setKey,
  type KeyProvider,
  type KeyStatus,
} from "@/lib/admin-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ToastStack, useToasts } from "@/components/admin/Toast";
import { cn } from "@/lib/utils";

const PROVIDERS: Array<{
  id: KeyProvider;
  label: string;
  envVar: string;
  emoji: string;
}> = [
  { id: "gemini", label: "Google Gemini", envVar: "GEMINI_API_KEY", emoji: "✨" },
  { id: "openai", label: "OpenAI", envVar: "OPENAI_API_KEY", emoji: "🟢" },
  {
    id: "anthropic",
    label: "Anthropic",
    envVar: "ANTHROPIC_API_KEY",
    emoji: "🟠",
  },
];

function SourceBadge({ source }: { source: KeyStatus["source"] }) {
  if (source === "runtime") {
    return <Badge variant="default">런타임 설정됨</Badge>;
  }
  if (source === "env") {
    return <Badge variant="ghost">env 사용 중</Badge>;
  }
  return (
    <Badge
      variant="outline"
      className="border-state-danger/50 text-state-danger"
    >
      미설정
    </Badge>
  );
}

export default function AdminKeysPage() {
  const qc = useQueryClient();
  const { toasts, push } = useToasts();
  const keysQ = useQuery({ queryKey: ["admin", "keys"], queryFn: listKeys });

  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const setM = useMutation({
    mutationFn: ({ provider, key }: { provider: KeyProvider; key: string }) =>
      setKey(provider, key),
    onSuccess: (data) => {
      push("success", `${data.provider} 런타임 키 적용됨`);
      setDrafts((prev) => ({ ...prev, [data.provider]: "" }));
      qc.invalidateQueries({ queryKey: ["admin", "keys"] });
    },
    onError: (err: unknown) =>
      push("error", `적용 실패: ${(err as Error).message}`),
  });

  const clearM = useMutation({
    mutationFn: (provider: KeyProvider) => clearKey(provider),
    onSuccess: (data) => {
      push("info", `${data.provider} 런타임 키 해제 → env 로 복귀`);
      qc.invalidateQueries({ queryKey: ["admin", "keys"] });
    },
    onError: (err: unknown) =>
      push("error", `해제 실패: ${(err as Error).message}`),
  });

  const byProvider = useMemo(() => {
    const map: Record<string, KeyStatus> = {};
    for (const k of keysQ.data?.keys ?? []) map[k.provider] = k;
    return map;
  }, [keysQ.data]);

  return (
    <div className="mx-auto w-full max-w-4xl">
      <header className="mb-6">
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          🔑 API 키 설정
        </h1>
        <p className="mt-1 font-korean text-sm text-text-secondary">
          제공자별 키를 런타임에 임시 반영합니다. 코드·.env 수정 없음.
        </p>
      </header>

      <div className="mb-6 rounded-md border border-accent-pink/40 bg-accent-pink-soft px-4 py-3 font-korean text-sm text-text-primary">
        입력한 키는{" "}
        <span className="font-semibold text-accent-pink">
          현재 실행 중인 서버 메모리에만
        </span>{" "}
        반영됩니다. 서버 재시작·재배포 시 사라지고 환경변수 값으로 돌아갑니다.
        (영속 저장은 v2 예정)
      </div>

      <div className="rounded-xl border border-border-subtle bg-bg-elevated">
        {PROVIDERS.map((p, idx) => {
          const status = byProvider[p.id];
          const draft = drafts[p.id] ?? "";
          const isRuntime = status?.source === "runtime";
          return (
            <div
              key={p.id}
              className={cn(
                "flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center",
                idx > 0 && "border-t border-border-subtle",
              )}
            >
              <div className="w-44 shrink-0">
                <div className="flex items-center gap-2 font-korean text-sm font-medium text-text-primary">
                  <span className="text-base">{p.emoji}</span>
                  {p.label}
                </div>
                <div className="mt-1 font-mono text-[10px] text-text-muted">
                  {p.envVar}
                </div>
              </div>
              <div className="flex flex-1 items-center gap-3">
                <SourceBadge source={status?.source ?? "none"} />
                <code className="rounded bg-bg-secondary px-2 py-1 font-mono text-xs text-text-secondary">
                  {status?.masked || "—"}
                </code>
              </div>
              <div className="flex flex-1 items-center gap-2">
                <Input
                  type="password"
                  placeholder="새 키 입력"
                  value={draft}
                  onChange={(e) =>
                    setDrafts((prev) => ({ ...prev, [p.id]: e.target.value }))
                  }
                  // 자동완성·복사 노출 방지
                  autoComplete="off"
                  className="h-9"
                />
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    if (!draft.trim()) {
                      push("error", "키가 비어 있습니다.");
                      return;
                    }
                    setM.mutate({ provider: p.id, key: draft.trim() });
                  }}
                  disabled={setM.isPending}
                >
                  적용
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => clearM.mutate(p.id)}
                  disabled={!isRuntime || clearM.isPending}
                  title={
                    isRuntime ? "런타임 override 해제" : "런타임 override 없음"
                  }
                >
                  해제
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 font-korean text-xs text-text-muted">
        • <span className="text-accent-pink">런타임 설정됨</span>: 어드민 입력 키 사용
        중 <br />
        • <span className="text-text-secondary">env 사용 중</span>: .env 의 값 사용
        중 <br />
        • <span className="text-state-danger">미설정</span>: 두 가지 모두 없음
        (해당 provider 호출 시 실패)
      </p>

      <ToastStack toasts={toasts} />
    </div>
  );
}
