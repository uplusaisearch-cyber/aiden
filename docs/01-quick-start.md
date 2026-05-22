# 01. Quick Start (30분 가이드)

신규 사용자가 AIDEN 프로젝트를 처음 받아 30분 내에 로컬에서 실행할 수 있도록 안내합니다.

---

## 0. 사전 준비

다음이 설치되어 있어야 합니다.

| 도구 | 버전 | 다운로드 |
|---|---|---|
| Python | **3.11 이상** | https://www.python.org/downloads/ |
| Git | 최신 | https://git-scm.com/downloads |
| Node.js | LTS (Phase 4부터 필요) | https://nodejs.org/ |

설치 확인:

```bash
python --version    # Python 3.11.x
git --version
```

> Windows 사용자: 명령 프롬프트 대신 **PowerShell** 또는 **Git Bash** 사용을 권장합니다.

---

## 1. 저장소 가져오기

```bash
git clone <repo-url> aiden
cd aiden
```

---

## 2. 가상환경 + 의존성 설치

```bash
# 가상환경 생성
python -m venv .venv

# 활성화
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 의존성 설치 (개발 도구 포함)
pip install -e ".[dev]"
```

---

## 3. API 키 설정

```bash
# .env.example 을 .env 로 복사
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

`.env` 파일을 열어 다음 키를 채워주세요.

```
GEMINI_API_KEY=실제_키
OPENAI_API_KEY=실제_키       # 선택
ANTHROPIC_API_KEY=실제_키    # 선택
```

키 발급:
- Gemini: https://aistudio.google.com/apikey (무료 티어 있음)
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/

> ⚠️ `.env` 는 절대 git 에 커밋하지 마세요. `.gitignore` 에 이미 등록되어 있습니다.

---

## 4. 설정 검증

```bash
python -c "from backend.core.settings import get_settings; print('OK:', get_settings().default_llm_provider)"
```

`OK: gemini` 가 출력되면 환경변수 로딩이 정상입니다.

---

## 5. (Phase 3 이후) 첫 실행

```bash
uvicorn backend.api.main:app --reload
```

브라우저에서 http://localhost:8000/docs 로 접속하면 FastAPI 자동 문서가 보입니다.

---

## 문제 해결

| 증상 | 원인/해결 |
|---|---|
| `RuntimeError: 환경변수 로드에 실패...` | `.env` 가 프로젝트 루트에 있는지, `GEMINI_API_KEY` 가 채워졌는지 확인 |
| `ModuleNotFoundError: No module named 'backend'` | 가상환경이 활성화되어 있고 `pip install -e .` 가 완료됐는지 확인 |
| 한글이 깨짐 | 모든 파일은 UTF-8. Windows 터미널 인코딩을 UTF-8 로 설정 (`chcp 65001`) |

다음 단계: [`02-architecture.md`](02-architecture.md)
