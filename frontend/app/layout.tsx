import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

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
        <style>{`:root { --font-pretendard: "Pretendard Variable", Pretendard, -apple-system, sans-serif; }`}</style>
      </head>
      <body className="bg-bg-primary text-text-primary antialiased font-korean">
        {children}
      </body>
    </html>
  );
}
