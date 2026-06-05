"use client";

/**
 * /admin/registry — 발행 이력.
 *
 * Method A (JSON 파일) CRUD 백엔드(`/api/admin/registry`)는 유지되어 있으며
 * Topic Scout 의 `{{PUBLISHED_TOPICS}}` 동적 주입도 동작한다. 다만 자동 적재
 * 경로가 없어 운영 데모 흐름에 노출하지 않고, v2 에서 자동 적재 + 영속화로 완성
 * 예정. 본 페이지는 그 동안 진입 시 안내만 표시한다.
 */
export default function RegistryPage() {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <header className="mb-6">
        <h1 className="font-korean text-2xl font-bold text-text-primary">
          📚 발행 이력
        </h1>
        <p className="mt-1 font-korean text-sm text-text-secondary">
          Topic Scout 가 회피할 발행 완료 토픽 목록.
        </p>
      </header>

      <div className="rounded-xl border border-border-subtle bg-bg-elevated px-6 py-12 text-center">
        <div className="text-4xl" aria-hidden>
          🚧
        </div>
        <h2 className="mt-4 font-korean text-base font-semibold text-text-primary">
          아직 구현중인 메뉴입니다.
        </h2>
        <p className="mt-2 font-korean text-sm text-text-muted">
          v2 에서 자동 적재 + 영속화로 제공 예정입니다.
        </p>
      </div>
    </div>
  );
}
