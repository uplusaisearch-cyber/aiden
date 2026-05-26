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
          DEFAULT: "hsl(var(--border))",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
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

        // shadcn/ui base
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "var(--font-pretendard)", "system-ui", "sans-serif"],
        korean: ["var(--font-pretendard)", "var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
