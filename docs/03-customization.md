# 03. Customization

> 코드를 한 줄도 안 만져도 AIDEN 의 동작을 바꿀 수 있습니다.
> 이 문서는 비개발자도 따라할 수 있도록 작성되었습니다.

---

## 🎨 다른 브랜드/서비스로 이관하기

`config/brand.yaml` 한 파일만 수정하면 됩니다.

예시 — LG U+ → 다른 브랜드로 변경:

```yaml
brand:
  name: "○○ 브랜드명"
  short_name: "○○"
  primary_color: "#1428A0"   # 본인 브랜드 메인 컬러
  secondary_color: "#1A1A1A"
  accent_color: "#666666"
  background_card: "#F5F5F5"

content_voice:
  tone: "친근하면서 신뢰감 있는"   # 브랜드 톤으로 변경
  ending_style: "~합니다 / ~해요"
  paragraph_length: "3-5문장"

target_audience:
  description: "본인 서비스의 타겟 독자"
  characteristics:
    - "...
```

저장하고 백엔드를 재시작하면 즉시 반영됩니다.

---

## 🔧 모델 / 라운드 수 조정하기

`config/agents.yaml` 을 수정하세요.

### 모델 교체 예시
gpt-5 대신 Claude Opus 로 심판 모델을 바꾸고 싶다면:

```yaml
models:
  gemini_pro: "gemini-2.5-pro"
  gemini_flash: "gemini-2.5-flash"
  openai_judge: "gpt-5"
  anthropic_judge: "claude-opus-4-7"   # ← 이 값을 원하는 모델로

agents:
  editor_in_chief:
    model: "anthropic_judge"            # ← 별칭만 바꾸면 끝
    grounding: false
```

### 토론 라운드 수 변경
비용을 줄이고 싶다면 라운드를 2회로:

```yaml
orchestration:
  content_newsroom:
    max_iterations: 2                    # 3 → 2
    devils_advocate_critique_count:
      round_1: 5
      round_2: 2
```

---

## 🎭 에이전트 페르소나 튜닝하기

각 에이전트의 시스템 프롬프트는 `backend/agents/prompts/` 폴더의 `.md` 파일입니다.

| 파일 | 에이전트 |
|---|---|
| `01_trend_scout.md` | Trend Scout |
| `02_audience_analyst.md` | Audience Analyst |
| `03_strategy_planner.md` | Strategy Planner |
| `04_writer.md` | Writer |
| `05_fact_checker.md` | Fact-Checker |
| `06_devils_advocate.md` | Devil's Advocate |
| `07_editor_in_chief.md` | Editor-in-Chief |
| `08_format_architect.md` | Format Architect |
| `09_html_builder.md` | HTML Builder |

해당 파일을 메모장이나 VS Code 같은 텍스트 편집기로 열어 내용을 수정하면,
다음 실행부터 새 프롬프트가 적용됩니다.

### 수정 시 주의사항
- **UTF-8 인코딩**으로 저장하세요. (메모장: 저장 시 인코딩 선택)
- 마크다운 형식을 권장합니다 (구조가 명확해서 LLM 이 더 잘 따릅니다).
- JSON 출력 스키마를 변경했다면, 해당 에이전트를 호출하는 오케스트레이션 쪽도 같이 확인해야 합니다.

---

## 🎬 플러스탭 콘텐츠 타입 정의 바꾸기

`config/platform.yaml` 에서 콘텐츠 타입과 인터랙티브 템플릿 목록을 관리합니다.
새로운 인터랙티브 템플릿을 추가하고 싶다면 `interactive_templates` 리스트에 항목을 추가하세요.

---

## 자주 묻는 질문

**Q. YAML 수정 후 반영이 안 됩니다.**
A. 백엔드 서버를 재시작하세요. `Settings` 와 config 로더는 `@lru_cache` 로 캐시되어 있습니다.

**Q. 프롬프트 수정이 반영이 안 됩니다.**
A. 에이전트 인스턴스가 생성 시 프롬프트를 한 번만 읽어옵니다. 서버 재시작 또는
`agent.reload_prompt()` 호출이 필요합니다.

**Q. 모델 별칭(gemini_pro 등)을 새로 추가하고 싶어요.**
A. `config/agents.yaml` 의 `models:` 에 `provider_xxx: "실제-모델-ID"` 형식으로 추가하세요.
`provider` 부분은 `gemini_`, `openai_`, `anthropic_` 중 하나로 시작해야 자동 인식됩니다.
