"use client";

import dynamic from "next/dynamic";

// SSR 회피: Monaco 는 window/document 의존 → next/dynamic + ssr:false.
// 로딩 동안 빈 다크 패널 + 안내 문구로 layout shift 방지.
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[60vh] items-center justify-center bg-bg-secondary font-korean text-sm text-text-muted">
        에디터 로드 중…
      </div>
    ),
  },
);

export interface PromptEditorProps {
  value: string;
  onChange: (next: string) => void;
}

/**
 * Persona Lab markdown 에디터.
 *
 * - language="markdown"
 * - vs-dark 기반 + 디자인 토큰 매칭 커스텀 테마 (`aiden-dark`)
 * - 외부 라이브러리 동작 변경 없이 props 만 노출
 */
export function PromptEditor({ value, onChange }: PromptEditorProps) {
  return (
    <div className="bg-bg-secondary">
      <MonacoEditor
        height="60vh"
        defaultLanguage="markdown"
        language="markdown"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        theme="aiden-dark"
        beforeMount={(monaco) => {
          // 디자인 토큰 매칭: bg-secondary(#131316), text-primary(#f4f4f5),
          // accent-pink(#ff2e98). vs-dark base 에 색만 override.
          monaco.editor.defineTheme("aiden-dark", {
            base: "vs-dark",
            inherit: true,
            rules: [],
            colors: {
              "editor.background": "#131316",
              "editor.foreground": "#f4f4f5",
              "editorLineNumber.foreground": "#3a3a42",
              "editorLineNumber.activeForeground": "#a1a1aa",
              "editor.selectionBackground": "#ff2e9833",
              "editor.lineHighlightBackground": "#1a1a1f",
              "editorCursor.foreground": "#ff2e98",
              "editorGutter.background": "#131316",
            },
          });
        }}
        options={{
          fontFamily:
            "var(--font-jetbrains-mono), ui-monospace, SFMono-Regular, monospace",
          fontSize: 13,
          lineHeight: 22,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          renderWhitespace: "selection",
          smoothScrolling: true,
          padding: { top: 12, bottom: 12 },
          automaticLayout: true,
          // markdown 편집에 도움 되는 옵션
          quickSuggestions: false,
          // 한글 IME 안전
          unicodeHighlight: { ambiguousCharacters: false },
        }}
      />
    </div>
  );
}
