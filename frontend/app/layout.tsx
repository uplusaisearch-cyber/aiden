import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

// Pretendard via CDN — next/font/google 미지원이라 link 로 로드
const pretendardCdn =
  "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css";

export const metadata: Metadata = {
  title: "AIDEN — AI Deliberation Engine for Newsroom",
  description: "9 AI 에이전트가 토론으로 콘텐츠를 만드는 뉴스룸 (LG U+ 플러스탭)",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ko"
      className={`dark ${inter.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <link rel="stylesheet" href={pretendardCdn} />
        {/* --font-pretendard 변수는 globals.css :root 에서 정의 — 인라인 <style> 은 SSR 큰따옴표 인코딩으로 hydration mismatch 유발 */}
      </head>
      <body className="bg-bg-primary text-text-primary antialiased font-korean">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
