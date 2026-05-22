# 06. Handover (인계/이관 가이드)

이 문서는 AIDEN 을 **다른 팀/다른 담당자/다른 회사 계정**으로 넘길 때 필요한 절차를 정리합니다.

---

## 1. GitHub Repo 소유권 이전

### 방법 A: Transfer Ownership (가장 간단)
1. 현재 소유자가 GitHub repo > **Settings > General** 진입
2. 맨 아래 **Danger Zone > Transfer ownership**
3. 새 소유자(개인 또는 organization) 입력 후 확인
4. 새 소유자가 24시간 내에 transfer 수락

이전 후 체크:
- [ ] CI/CD (Vercel, Railway) 의 GitHub 연동 재설정
- [ ] Branch protection rules 재설정
- [ ] Webhook / GitHub App 권한 재확인

### 방법 B: Fork + Push
새 소유자 계정에서 새 repo 를 만들고:
```bash
git remote set-url origin <new-repo-url>
git push -u origin main
```

---

## 2. API 키 재발급 & 교체

이관 시 **모든 키를 새로 발급**하는 것이 원칙입니다. (이전 담당자 계정에 결제가 묶일 수 있음)

| Provider | 발급 페이지 | 교체 방법 |
|---|---|---|
| Google Gemini | https://aistudio.google.com/apikey | 새 키 발급 → `.env` 의 `GEMINI_API_KEY` 교체 |
| OpenAI | https://platform.openai.com/api-keys | 새 키 발급 → `.env` 의 `OPENAI_API_KEY` 교체 |
| Anthropic | https://console.anthropic.com/ | 새 키 발급 → `.env` 의 `ANTHROPIC_API_KEY` 교체 |

> ⚠️ 이전 담당자 계정의 키는 **즉시 revoke** 하세요.

배포 환경의 환경변수도 함께 교체:
- Vercel: Dashboard > Project > Settings > Environment Variables
- Railway: Project > Variables

---

## 3. 인프라 이관 체크리스트

### Vercel (Frontend)
- [ ] 새 계정/팀으로 프로젝트 transfer
- [ ] 도메인 연결 (있다면) 재설정
- [ ] 환경변수 재입력
- [ ] `config/deployment.yaml` 의 `production.frontend_url` 갱신

### Railway (Backend)
- [ ] 새 계정으로 프로젝트 transfer 또는 재배포
- [ ] 환경변수 재입력
- [ ] `config/deployment.yaml` 의 `production.backend_url` 갱신

### 도메인 / DNS
- [ ] CNAME / A 레코드 변경 필요 시 안내

---

## 4. 콘텐츠/브랜드 자산 이관

다른 브랜드로 적용하는 경우:

- [ ] `config/brand.yaml` — 브랜드명, 컬러, 톤 교체
- [ ] `config/platform.yaml` — 게재 플랫폼 타입 정의 검토
- [ ] `backend/agents/prompts/*.md` — 페르소나/톤 지시 검토 (브랜드별 미묘한 조정 필요할 수 있음)
- [ ] `backend/templates/*.html` — 게재 플랫폼이 다르면 HTML 구조 재정의 필요

---

## 5. 인계 시 함께 전달할 것

새 담당자에게 다음을 함께 전달하세요:

1. **이 저장소 링크** + 이 문서(`docs/06-handover.md`) 위치
2. **CLAUDE.md** — Claude Code 사용 시 자동 적용되는 가이드라인
3. **README.md** — 5분 셋업 가이드
4. **현재 운영 중인 배포 URL** (Vercel/Railway)
5. **이전 결제/사용량 이력** (선택)

---

## 6. 최소 동작 확인 (Smoke Test)

이관이 끝났다면 새 담당자가 다음을 확인하세요:

```bash
# 1. 클론
git clone <new-repo-url> aiden
cd aiden

# 2. 가상환경 + 설치
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. 환경변수
cp .env.example .env
# .env 에 새로 발급받은 키 입력

# 4. 설정 로드 확인
python -c "from backend.core.settings import get_settings, load_brand_config; print(get_settings().default_llm_provider, load_brand_config()['brand']['name'])"
```

`gemini LG U+ 플러스탭` (또는 변경된 브랜드명) 이 출력되면 인계 성공입니다.
