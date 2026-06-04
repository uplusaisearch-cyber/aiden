import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4 py-16">
      <div className="text-center">
        <div className="mb-4 text-5xl" aria-hidden>
          🔍
        </div>
        <h1 className="font-korean text-xl font-bold text-text-primary">
          페이지를 찾을 수 없습니다
        </h1>
        <p className="mt-2 font-korean text-sm text-text-secondary">
          주소가 잘못되었거나 삭제된 페이지일 수 있습니다.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-md bg-accent-pink px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-pink-hover"
        >
          ← 메인으로
        </Link>
      </div>
    </main>
  );
}
