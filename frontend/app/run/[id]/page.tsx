import Link from "next/link";

interface Props {
  params: { id: string };
}

export default function RunPlaceholder({ params }: Props) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
      <div className="text-center">
        <div className="mb-4 text-5xl">🚧</div>
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          트레이스 뷰어 준비 중
        </h1>
        <p className="mt-2 font-korean text-sm text-text-secondary">
          B3-S3-C 명세서에서 구현 예정입니다.
        </p>
        <p className="mt-6 font-mono text-xs text-text-muted">
          session: {params.id}
        </p>
        <Link
          href="/"
          className="mt-8 inline-block rounded-md border border-border-subtle bg-bg-elevated px-4 py-2 text-sm text-text-secondary transition hover:border-accent-pink hover:text-accent-pink"
        >
          ← 메인으로
        </Link>
      </div>
    </main>
  );
}
