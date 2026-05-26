# 묶음 3 Step 3-A: Next.js 셋업 + 디자인 토큰 + 메인 페이지

- **ID**: B3-S3-A
- **우선순위**: 묶음 3 우선순위 4 의 첫 분할 명세
- **의존**: B3-S2 (Judge Panel 백엔드) 완료
- **목적**:
  1. 어드민 UI 프로젝트 기반 구축 (Next.js 14 + Tailwind + shadcn/ui)
  2. 디자인 토큰 시스템 (다크모드 + 플러스탭 브랜드 + Judge 모델 색상)
  3. 메인 페이지 (카테고리 선택 + 자유 입력 + 최근 실행 5건)
- **상위 마스터**: `docs/patches/2026-05-25_bundle3_step3_admin_ui_master_v2.md`

---

## 작업 범위 (본 명세서가 책임지는 것)

| 영역 | 포함 | 제외 (다른 명세) |
|---|---|---|
| 프로젝트 셋업 | Next.js 14 + TypeScript + Tailwind + shadcn/ui | — |
| 디자인 토큰 | CSS 변수 + Tailwind config | — |
| 공통 컴포넌트 | Button, Card, Input, Badge, etc (shadcn/ui 설치만) | 커스텀 컴포넌트 (다음 명세) |
| 페이지 | `/` 메인 페이지만 | `/run/<id>`, `/admin/*` (다음 명세) |
| API 호출 | Mock 데이터 (실제 백엔드 호출은 B3-S3-B) | FastAPI 연동 |
| 라우팅 | "Generate" 버튼 → `/run/<mock_id>` (404 페이지 표시 OK) | 실제 SSE 연결 |

---

## 폴더 구조

```
frontend/                          # 신규 프로젝트
├── app/
│   ├── layout.tsx                 # 루트 레이아웃 (다크모드 강제)
│   ├── page.tsx                   # 메인 페이지
│   ├── globals.css                # 디자인 토큰 + Tailwind
│   └── fonts.ts                   # Inter + Pretendard + JetBrains Mono
├── components/
│   ├── ui/                        # shadcn/ui (CLI 설치 결과)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── badge.tsx
│   │   └── ... (기타 필요한 것)
│   ├── main/
│   │   ├── category-card.tsx      # 카테고리 선택 카드
│   │   ├── custom-input-card.tsx  # 자유 입력 카드 (expand 가능)
│   │   ├── recent-runs.tsx        # 최근 실행 5건
│   │   └── hero-header.tsx        # AIDEN 로고 + 타이틀
│   └── shared/
│       ├── agent-avatar.tsx       # 에이전트 아바타 (이모지 + 색상)
│       └── score-bar.tsx          # 진행률 / 점수 바 (재사용)
├── lib/
│   ├── utils.ts                   # cn() 등 shadcn 표준
│   ├── constants.ts               # 에이전트 캐릭터 정의 (마스터 명세서 테이블)
│   └── mock-data.ts               # B3-S2-E2E mock 활용
├── types/
│   ├── agent.ts                   # 에이전트 캐릭터 타입
│   ├── run.ts                     # 실행 메타데이터 타입
│   └── judge.ts                   # Judge Panel 타입 (B3-S2 스키마 미러)
├── public/
├── tailwind.config.ts
├── tsconfig.json
├── next.config.mjs
├── package.json
└── .env.local.example
```

---

## 디자인 토큰 (globals.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Base (다크모드 기본값) */
  --bg-primary: #0a0a0b;
  --bg-secondary: #131316;
  --bg-elevated: #1a1a1f;
  --border-subtle: #2a2a30;
  --border-strong: #3a3a42;

  /* Text */
  --text-primary: #f4f4f5;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  /* Brand */
  --accent-pink: #ff2e98;          /* 플러스탭 핑크 */
  --accent-pink-soft: #ff2e9820;
  --accent-pink-hover: #ff4ba8;

  /* Agent colors (마스터 명세서 테이블 기반) */
  --agent-scout: #3b82f6;          /* Trend Scout */
  --agent-analyst: #a855f7;        /* Audience Analyst */
  --agent-planner: #eab308;        /* Strategy Planner */
  --agent-writer: #22c55e;         /* Writer */
  --agent-factchecker: #06b6d4;    /* Fact-Checker */
  --agent-devils: #ef4444;         /* Devil's Advocate */
  --agent-editor: #f97316;         /* Editor-in-Chief */
  --agent-architect: #94a3b8;      /* Format Architect */
  --agent-builder: #1e40af;        /* HTML Builder */

  /* Judge colors */
  --judge-gemini: #4285f4;
  --judge-gpt: #10a37f;
  --judge-claude: #d97757;
  --judge-mean: #ff2e98;

  /* States */
  --state-success: #22c55e;
  --state-warning: #eab308;
  --state-danger: #ef4444;
  --state-info: #3b82f6;

  /* Radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
}

body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-inter), system-ui, sans-serif;
}

/* Pretendard for Korean body */
.font-korean {
  font-family: var(--font-pretendard), var(--font-inter), sans-serif;
}

/* JetBrains Mono for code */
.font-mono {
  font-family: var(--font-jetbrains-mono), monospace;
}
```

### Tailwind config 매핑

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "var(--bg-primary)",
          secondary: "var(--bg-secondary)",
          elevated: "var(--bg-elevated)",
        },
        border: {
          subtle: "var(--border-subtle)",
          strong: "var(--border-strong)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        accent: {
          pink: "var(--accent-pink)",
          "pink-soft": "var(--accent-pink-soft)",
          "pink-hover": "var(--accent-pink-hover)",
        },
        agent: {
          scout: "var(--agent-scout)",
          analyst: "var(--agent-analyst)",
          planner: "var(--agent-planner)",
          writer: "var(--agent-writer)",
          factchecker: "var(--agent-factchecker)",
          devils: "var(--agent-devils)",
          editor: "var(--agent-editor)",
          architect: "var(--agent-architect)",
          builder: "var(--agent-builder)",
        },
        judge: {
          gemini: "var(--judge-gemini)",
          gpt: "var(--judge-gpt)",
          claude: "var(--judge-claude)",
          mean: "var(--judge-mean)",
        },
        state: {
          success: "var(--state-success)",
          warning: "var(--state-warning)",
          danger: "var(--state-danger)",
          info: "var(--state-info)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)"],
        korean: ["var(--font-pretendard)"],
        mono: ["var(--font-jetbrains-mono)"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

---

## 에이전트 캐릭터 정의 (lib/constants.ts)

마스터 명세서의 12 에이전트 테이블을 TypeScript 상수로:

```ts
export type AgentId =
  | "scout" | "analyst" | "planner" | "writer" | "factchecker"
  | "devils" | "editor" | "architect" | "builder"
  | "judge-gemini" | "judge-gpt" | "judge-claude";

export interface AgentCharacter {
  id: AgentId;
  emoji: string;
  nameKo: string;
  nameEn: string;
  color: string;        // CSS variable name
  tone: string;         // 말투 설명
  description: string;  // 마스터 명세서 캐릭터 설명
}

export const AGENT_CHARACTERS: Record<AgentId, AgentCharacter> = {
  scout: {
    id: "scout",
    emoji: "🔍",
    nameKo: "트렌드 정찰병",
    nameEn: "Trend Scout",
    color: "var(--agent-scout)",
    tone: "정보 수집 보고체",
    description: "방금 X 트렌드 잡았습니다",
  },
  // ... 11 개 더 (마스터 명세서 그대로)
};

export const CATEGORY_PRESETS = [
  { id: "food", label: "맛집", icon: "🍜", description: "주변 가성비·핫플 발굴" },
  { id: "ai-trend", label: "AI트렌드", icon: "🤖", description: "최신 AI 동향·도구 소개" },
  { id: "safety", label: "안전", icon: "🛡️", description: "생활 안전·예방 가이드" },
  { id: "culture", label: "문화", icon: "🎭", description: "전시·공연·여가" },
] as const;

export type CategoryId = typeof CATEGORY_PRESETS[number]["id"] | "custom";
```

---

## 메인 페이지 레이아웃 (`app/page.tsx`)

### 와이어프레임

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│              [AIDEN 로고]                                         │
│              AI Deliberation Engine for Newsroom                 │
│                                                                  │
│  ─────────────────────────────────────────────────────           │
│                                                                  │
│  콘텐츠 카테고리를 선택하세요                                       │
│                                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│  │   🍜   │ │   🤖   │ │   🛡️   │ │   🎭   │ │   ✏️    │         │
│  │  맛집  │ │AI트렌드│ │  안전  │ │  문화  │ │ 자유입력│         │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘         │
│                                                                  │
│  ─────────────────────────────────────────────────────           │
│                                                                  │
│  최근 실행                                          [전체 보기]    │
│                                                                  │
│  ┌─────────────────────┐ ┌─────────────────────┐                 │
│  │ 가족 식비 50만원..  │ │ 장마철 안전점검..   │                 │
│  │ 맛집 · 7.3/10       │ │ 안전 · 6.2/10       │                 │
│  │ 5분 전              │ │ 12분 전             │                 │
│  └─────────────────────┘ └─────────────────────┘                 │
│  ... 5건                                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 인터랙션

| 영역 | 동작 |
|---|---|
| 카테고리 카드 hover | 카드 lift + 아이콘 살짝 scale (Framer Motion) |
| 카테고리 카드 클릭 | 카드 selected 상태 (핑크 보더) + 하단에 "Generate" 버튼 등장 |
| 자유 입력 카드 클릭 | 카드 확장 (텍스트 input + 고급 옵션 토글) |
| 고급 옵션 expand | max_iter / skip_judge 토글 등 (UI만, 실제 동작은 B3-S3-B) |
| "Generate" 버튼 클릭 | mock session_id 생성 후 `/run/<mock_id>` 이동 (404 페이지 표시 OK) |
| 최근 실행 카드 클릭 | `/run/<session_id>` 이동 (404 OK) |

### Mock 데이터 (lib/mock-data.ts)

B3-S2-E2E 결과를 mock 으로 활용:

```ts
import judgeRun1 from "./mocks/run1_food_restaurant.json"; // docs/samples/judge_panel_samples/ 복사
import judgeRun2 from "./mocks/run2_safety.json";
import judgeRun3 from "./mocks/run3_ai_trends.json";

export const MOCK_RECENT_RUNS = [
  {
    sessionId: "2026-05-26T14-19-20_08a55b97",
    category: "food",
    title: "가족 식비, 매달 50만원 아끼는 법",
    weightedTotal: 7.3,
    finishedAt: "2026-05-26T14:27:00Z",
    status: "completed",
  },
  // 5건
];

export const MOCK_JUDGE_DATA = {
  food: judgeRun1,
  safety: judgeRun2,
  "ai-trend": judgeRun3,
};
```

---

## 컴포넌트 상세

### 1. `<HeroHeader />`
- 상단 중앙 정렬
- AIDEN 로고 (SVG 또는 큰 텍스트, 핑크 글로우 효과)
- 부제목: "AI Deliberation Engine for Newsroom"
- 우상단: `/admin` 링크 (조용한 회색 아이콘 + "Admin" 라벨)

### 2. `<CategoryCard />`
- Props: `category: CategoryId`, `selected: boolean`, `onSelect: () => void`
- 크기: 정사각형 (200×200px 데스크탑, 모바일은 grid responsive)
- 아이콘 (이모지 또는 lucide-react), 라벨, 짧은 설명
- 상태:
  - default: bg-elevated + border-subtle
  - hover: lift (translateY -2px) + border-strong + 아이콘 scale 1.05
  - selected: border-accent-pink + bg에 핑크 soft 오버레이
- 애니메이션: Framer Motion `whileHover`, `whileTap`

### 3. `<CustomInputCard />`
- Props: `onSubmit: (input: { topic: string, options: {...} }) => void`
- 기본 상태: 카드 (다른 카테고리 카드와 같은 크기)
- expanded 상태: 카드가 가로로 확장 (전체 너비), 내부에 다음 폼:
  - 텍스트 input ("어떤 주제로 콘텐츠를 만들까요?")
  - "고급 옵션" 토글 (collapse):
    - max_iter: 1/2/3 라디오
    - skip_judge: 체크박스
    - SAFETY_MODE: normal / dry_run 토글
- 하단: Generate 버튼

### 4. `<RecentRuns />`
- Props: `runs: MockRecentRun[]`
- 가로 스크롤 가능한 카드 리스트 (또는 grid 2x3)
- 각 카드: 제목 (2줄 ellipsis), 카테고리 뱃지, 점수 (weighted_total, 색상 점수에 따라), 상대 시간
- 호버 시 카드 lift
- 클릭 시 `/run/<sessionId>` 이동

### 5. `<AgentAvatar />`
- Props: `agentId: AgentId`, `size?: "sm" | "md" | "lg"`
- 원형 배경 + 캐릭터 색상 + 이모지
- size 별: sm 24px, md 36px, lg 56px
- 다른 페이지에서도 재사용 (B3-S3-C 트레이스 뷰어에서 채팅 버블 좌측에 표시)

### 6. `<ScoreBar />`
- Props: `value: number`, `max: number = 10`, `color?: string`, `showLabel?: boolean`
- 가로 progress bar + 점수 라벨
- 색상: value >= 7 success, 4~6.9 warning, <4 danger (기본). color prop 으로 override
- Framer Motion 으로 마운트 시 0 → value 애니메이션

---

## 반응형 (모바일 대응)

| 영역 | 데스크탑 | 모바일 |
|---|---|---|
| 카테고리 카드 그리드 | 5 columns (`grid-cols-5`) | 2 columns (`grid-cols-2`) |
| 자유 입력 카드 expand | 가로 확장 (col-span-5) | 세로 확장 (col-span-2) |
| 최근 실행 | 3 columns | 1 column (세로 스크롤) |
| 헤더 | 가운데 정렬 큰 로고 | 좌측 정렬 작은 로고 |
| /admin 링크 | 우상단 텍스트 | 우상단 아이콘만 |

Tailwind breakpoint: `sm:` (640px) 이상부터 데스크탑.

---

## 단위 테스트 (선택, 시간 되면)

| # | 케이스 | 도구 |
|---|---|---|
| 1 | 카테고리 카드 클릭 시 selected 상태 | Vitest + Testing Library |
| 2 | 자유 입력 카드 expand 토글 | 동일 |
| 3 | "Generate" 버튼 클릭 시 라우팅 호출 | mock router |

마감 임박이라 **테스트 생략 가능**. 작동 확인은 수동 + 시연 리허설.

---

## 의존 패키지

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "tailwind-merge": "^2.3.0",
    "clsx": "^2.1.0",
    "framer-motion": "^11.2.0",
    "lucide-react": "^0.395.0",
    "date-fns": "^3.6.0"
  },
  "devDependencies": {
    "@types/node": "^20.12.0",
    "@types/react": "^18.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.0"
  }
}
```

shadcn/ui CLI 로 컴포넌트 설치 (별도 의존성 자동 추가):
```bash
npx shadcn@latest init
npx shadcn@latest add button card input badge separator
```

---

## 실행 후 검증

### Step 1. 프로젝트 빌드
```bash
cd frontend
npm install
npm run dev
```
→ `http://localhost:3000` 접속 가능, 메인 페이지 정상 렌더링

### Step 2. 메인 페이지 시각 검증
- 다크모드 정상 적용 (배경 #0a0a0b)
- 5개 카테고리 카드 그리드 (또는 모바일 2 columns)
- 호버 인터랙션 작동 (lift + scale)
- 카테고리 선택 시 Generate 버튼 등장
- 자유 입력 카드 expand 정상

### Step 3. 라우팅 검증
- 카테고리 선택 + Generate 클릭 → `/run/<mock_id>` 로 이동 (404 페이지 표시 OK, B3-S3-C 에서 구현)
- 최근 실행 카드 클릭 → 동일 동작
- 우상단 /admin 링크 → 404 표시 OK (B3-S3-E 에서 구현)

### Step 4. 반응형 검증
- DevTools 모바일 뷰 (375px width)
- 카테고리 카드 2 columns
- 자유 입력 카드 세로 expand
- 최근 실행 1 column

### Step 5. mock 데이터 검증
- B3-S2-E2E 산출 mock 4개 가 `frontend/lib/mocks/` 또는 임포트 경로에서 접근 가능
- 최근 실행에 mock 데이터 표시
- 점수·카테고리·시간 정상 렌더링

### Step 6. 빌드 검증
```bash
npm run build
```
→ TypeScript 에러 0건, 빌드 성공

---

## Claude Code 실행 지시

1. `frontend/` 폴더에 Next.js 14 프로젝트 생성 (`create-next-app` 사용, TypeScript + Tailwind + App Router)
2. shadcn/ui 초기화 + 기본 컴포넌트 설치 (Button, Card, Input, Badge, Separator)
3. 위 디자인 토큰 (globals.css + tailwind.config.ts) 적용
4. `lib/constants.ts` 에 12 에이전트 캐릭터 + 카테고리 프리셋 정의 (마스터 명세서 테이블 그대로)
5. `lib/mock-data.ts` 에 B3-S2-E2E mock 4개 임포트 + MOCK_RECENT_RUNS 정의
   - `docs/samples/judge_panel_samples/*.json` 4개를 `frontend/lib/mocks/` 로 복사
6. 메인 페이지 (`app/page.tsx`) 구현 — 위 와이어프레임 그대로
7. 6개 컴포넌트 구현 (HeroHeader, CategoryCard, CustomInputCard, RecentRuns, AgentAvatar, ScoreBar)
8. 모바일 반응형 적용 (Tailwind `sm:` breakpoint)
9. `npm run dev` 동작 확인 + `npm run build` 통과 확인
10. **다른 페이지 (`/run/<id>`, `/admin/*`) 는 본 명세 범위 밖** — 404 또는 placeholder 페이지만
11. **실제 백엔드 API 호출 금지** — 모든 데이터 mock 사용
12. 보고:
    - 생성된 파일 목록 + 라인 수
    - `npm run dev` / `npm run build` 결과
    - 메인 페이지 스크린샷 (가능하면) 또는 시각 검증 체크리스트 결과
    - 의존 패키지 설치 결과
13. **git add / commit / stage 금지**

---

## 후속 작업 (본 명세 완료 후)

- **B3-S3-B**: FastAPI 백엔드 SSE 엔드포인트 + Trace 직렬화 (백엔드 진입)
- **B3-S3-C**: 트레이스 뷰어 (`/run/<session_id>`, 채팅 버블 + 캐릭터화 + 토론 강조)
- **B3-S3-D**: Judge 시각화 (시뮬레이션 연출 + 레이더 차트 + 3-Model 카드)
- **B3-S3-E**: Persona Lab + 운영 페이지들 (`/admin/personas` 등)

---

## 위험 / 제약

- **frontend/ 폴더 충돌**: 기존 `frontend/` 폴더가 이미 있을 수 있음 (CLAUDE.md 참조). Claude Code 가 먼저 확인 후 처리 방향 보고
- **shadcn/ui CLI**: 대화형 프롬프트가 있어서 자동 실행 시 막힐 수 있음. 옵션 자동 지정 필요
- **Pretendard 폰트**: CDN 또는 next/font 로 로딩. 한국어 본문 가독성 핵심
- **mock 데이터 raw JSON**: B3-S2-E2E mock 의 JSON 구조가 TypeScript 타입과 정확히 일치하는지 확인 필요. 불일치 시 타입 정의 보정

---

## 별도 이슈

- **#frontend-folder-conflict**: 기존 `frontend/` 폴더 존재 여부 확인 후 처리
- **#admin-link-mvp**: 메인 페이지 우상단 /admin 링크는 placeholder. 실제 동작은 B3-S3-E
