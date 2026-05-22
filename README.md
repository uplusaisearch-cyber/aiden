# AIDEN

> **A**I-driven **I**nteractive **D**iscussion **E**ditorial **N**ewsroom
> 9개 AI 에이전트가 뉴스룸처럼 토론하며 LG U+ 플러스탭 콘텐츠를 자동 생성합니다.

LG U+ 사내 AI 콘텐츠 자동화 대회 출품작입니다.

---

## ✨ 무엇을 하는 시스템인가

기획자가 주제 한 줄만 던지면, 9명의 AI 에이전트가 **뉴스룸 회의처럼 토론**하여
플러스탭에 바로 게재 가능한 HTML 콘텐츠 한 편을 만들어냅니다.

- **Trend Scout** — 최신 트렌드 리서치 (Grounding)
- **Audience Analyst** — 타겟 독자 분석
- **Strategy Planner** — 콘텐츠 전략 수립
- **Writer** — 본문 초안 작성
- **Fact-Checker** — 사실 검증 (Grounding)
- **Devil's Advocate** — 비판/반박
- **Editor-in-Chief** — 최종 편집/판단
- **Format Architect** — 콘텐츠 형식 설계 (A/B/C 타입)
- **HTML Builder** — 최종 HTML 출력

---

## 🚀 5분 셋업

### 1. 사전 준비
- Python **3.11 이상**
- Git
- (Phase 4 이후) Node.js LTS

### 2. 설치 (Windows / macOS 공통)

```bash
# 저장소 클론
git clone <repo-url> aiden
cd aiden

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 의존성 설치
pip install -e ".[dev]"
```

### 3. 환경변수 설정

```bash
# .env.example 복사
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env

# .env 파일을 열어 API 키를 채워주세요.
```

필요한 키:
- `GEMINI_API_KEY` — https://aistudio.google.com/apikey
- `OPENAI_API_KEY` — https://platform.openai.com/api-keys
- `ANTHROPIC_API_KEY` — https://console.anthropic.com/

### 4. 첫 실행

```bash
# 백엔드 개발 서버 (Phase 3 이후)
uvicorn backend.api.main:app --reload
```

---

## 📂 폴더 구조

```
aiden/
├── CLAUDE.md             # Claude Code 작업 가이드라인
├── README.md             # (이 파일)
├── .env.example          # 환경변수 템플릿
├── pyproject.toml        # Python 패키지 정의
│
├── config/               # ⭐ 비개발자도 수정 가능한 설정
│   ├── brand.yaml          # 브랜드/톤앤매너 (LG U+ 플러스탭)
│   ├── platform.yaml       # 플러스탭 콘텐츠 타입 정의
│   ├── agents.yaml         # 9 에이전트 모델/라운드 설정
│   └── deployment.yaml     # 배포 환경 설정
│
├── backend/
│   ├── core/               # 핵심 모듈 (settings / llm_clients / base_agent)
│   ├── agents/
│   │   ├── prompts/        # ⭐ 9개 에이전트 system prompt (.md)
│   │   └── definitions.py  # 에이전트 인스턴스 정의
│   ├── orchestration/      # 뉴스룸 토론 오케스트레이션
│   ├── templates/          # 플러스탭 HTML 템플릿 (A/B 타입)
│   ├── api/                # FastAPI 라우터 (SSE 스트리밍)
│   └── tests/              # 테스트
│
├── frontend/             # Next.js 14 (Phase 4)
│
├── docs/
│   ├── 01-quick-start.md
│   ├── 02-architecture.md
│   ├── 03-customization.md
│   └── 06-handover.md
│
└── scripts/              # 운영 스크립트
```

---

## 🛠 핵심 명령어

```bash
# 백엔드 개발 서버 (Phase 3+)
uvicorn backend.api.main:app --reload

# 테스트 실행
pytest

# 린트 / 포맷
ruff check .
black .
```

---

## 📚 다음 단계

- [`docs/01-quick-start.md`](docs/01-quick-start.md) — 신규 사용자 30분 가이드
- [`docs/02-architecture.md`](docs/02-architecture.md) — 시스템 아키텍처
- [`docs/03-customization.md`](docs/03-customization.md) — 브랜드/페르소나 커스터마이징
- [`docs/06-handover.md`](docs/06-handover.md) — 인계/이관 가이드

---

## 🔑 설계 원칙 (꼭 읽어주세요)

1. **이관성/확장성**: 다른 팀/다른 브랜드로 옮길 수 있어야 합니다.
2. **비개발자 친화**: 프롬프트는 `.md`, 설정은 `.yaml`. 코드 수정 없이 튜닝 가능.
3. **하드코딩 금지**: 모든 키/설정은 `.env`와 `config/`로 중앙화.
4. **한국어 처리**: 모든 파일 UTF-8.

자세한 가이드라인은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.
