import Link from "next/link";

export default function AdminPlaceholder() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
      <div className="text-center">
        <div className="mb-4 text-5xl">⚙️</div>
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          어드민 페이지 준비 중
        </h1>
        <p className="mt-2 font-korean text-sm text-text-secondary">
          B3-S3-E 명세서에서 구현 예정입니다 (Persona Lab, 운영 페이지 등).
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
