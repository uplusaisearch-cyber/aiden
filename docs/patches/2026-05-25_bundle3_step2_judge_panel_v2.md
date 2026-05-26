# 묶음 3 Step 2 v2: Judge Panel 오케스트레이터 (Stage 4)

- **ID**: B3-S2 (v2 — 결정사항 반영)
- **우선순위**: 묶음 3 우선순위 3
- **의존**: 묶음 2 Step 3-3 (FullPipeline) 완료
- **목적**: 9 에이전트 파이프라인이 만든 최종 콘텐츠를 **3-Model (Gemini + GPT + Claude)** 로 교차 평가
- **v1 대비 변경**: 의사결정 4건 확정 반영 (특히 모델명 환경변수화)

---

## 확정된 설계 결정

| # | 결정 | 채택안 |
|---|---|---|
| 1 | 호출 방식 | **동시 호출** (asyncio.gather) |
| 2 | 의견 불일치 처리 | **평균 + 표준편차 + 차원별 outlier 표시** |
| 3 | 평가 입력 | **final_output.html (렌더 HTML)** |
| 4 | 모델명 관리 | **환경변수 + 어드민 UI 런타임 override (3단계 우선순위)** |

---

## 모델명 3단계 우선순위 (운영자 손에 넘어가도 코드 수정 불필요)

런타임 모델 선택 우선순위:

```
1. 어드민 UI 런타임 override (있으면 최우선) — B3-S3 영역, 본 명세서는 hook만 제공
2. 환경변수 (.env)
   - JUDGE_GEMINI_MODEL
   - JUDGE_GPT_MODEL
   - JUDGE_CLAUDE_MODEL
3. config/agents.yaml 기본값 (fallback)
```

기본값 (`config/agents.yaml`):
```yaml
judge_panel:
  models:
    gemini: gemini-2.5-pro
    gpt: gpt-5
    claude: claude-opus-4-7
  budget_per_run_usd: 0.05
  timeout_sec: 60
```

`.env.example` 추가:
```
# Judge Panel (선택. 미지정 시 config/agents.yaml 기본값 사용)
JUDGE_GEMINI_MODEL=
JUDGE_GPT_MODEL=
JUDGE_CLAUDE_MODEL=
```

JudgePanel 초기화 코드 (의사 코드):
```python
def _resolve_model(judge_name: str, runtime_override: dict | None = None) -> str:
    # 1. UI 런타임 override
    if runtime_override and f"{judge_name}_model" in runtime_override:
        return runtime_override[f"{judge_name}_model"]
    # 2. 환경변수
    env_key = f"JUDGE_{judge_name.upper()}_MODEL"
    if env_value := os.getenv(env_key):
        return env_value
    # 3. config 기본값
    return settings.judge_panel.models[judge_name]
```

---

## 평가 차원 (공모전 채점 기준)

| 차원 | 가중치 | 설명 |
|---|---|---|
| `topic_fit` | 20% | 카테고리·페르소나 적합성 |
| `content_quality` | 25% | 정보 정확성·논리 흐름·실용성 |
| `interactivity` | 15% | 인터랙티브 요소 효과성 |
| `tone_authenticity` | 20% | 사람이 쓴 글다움·플러스탭 톤 일치 |
| `timeliness_trust` | 20% | 시의성·출처 신뢰도 |

가중치도 환경변수로 override 가능하게 (`JUDGE_WEIGHTS_TOPIC_FIT=20` 같은 형식). 단 합이 100이 되는지 startup 시 검증.

---

## 변경 대상

### 신규 파일
| 경로 | 역할 |
|---|---|
| `backend/orchestrators/judge_panel.py` | 메인 오케스트레이터 (3 judge 동시 호출, asyncio.gather) |
| `backend/core/openai_client.py` | OpenAI API 래퍼 (gpt-5 호출, JSON mode) |
| `backend/core/anthropic_client.py` | Anthropic API 래퍼 (claude-opus-4-7 호출, JSON mode) |
| `backend/core/judge_model_resolver.py` | 위 3단계 우선순위 모델 해석기 |
| `backend/agents/prompts/10_judge_gemini.md` | Gemini용 평가 프롬프트 |
| `backend/agents/prompts/11_judge_gpt.md` | GPT용 평가 프롬프트 |
| `backend/agents/prompts/12_judge_claude.md` | Claude용 평가 프롬프트 |
| `tests/test_judge_panel.py` | 단위 테스트 |
| `tests/test_judge_model_resolver.py` | 우선순위 해석기 단위 테스트 |

### 수정 파일
| 경로 | 변경 |
|---|---|
| `backend/orchestrators/full_pipeline.py` | Stage 4 추가 (JudgePanel 호출, 결과를 metadata.json에 병합) |
| `backend/orchestrators/trace_logger.py` | judge_panel highlight 추가 (3 모델 평균·표준편차·outlier) |
| `backend/config/agents.yaml` | `judge_panel` 섹션 추가 (위 기본값 블록 그대로) |
| `backend/core/settings.py` | judge_panel 설정 로딩 + 가중치 합 검증 |
| `scripts/run_full_pipeline.py` | `--skip-judge` 옵션 추가 (디버깅용) |
| `.env.example` | 위 환경변수 추가 |

### 라이브러리
- `openai>=1.55.0`
- `anthropic>=0.40.0`

---

## JSON 스키마

### 평가 프롬프트 공통 출력 (3 모델 동일)
```json
{
  "model": "gemini-2.5-pro | gpt-5 | claude-opus-4-7",
  "scores": {
    "topic_fit": 8,
    "content_quality": 7,
    "interactivity": 9,
    "tone_authenticity": 6,
    "timeliness_trust": 8
  },
  "comments": {
    "topic_fit": "...",
    "content_quality": "...",
    "interactivity": "...",
    "tone_authenticity": "...",
    "timeliness_trust": "..."
  },
  "overall_score": 7.6,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "one_line_verdict": "한 줄 평 (50자 이내)"
}
```

### JudgePanel 최종 출력 (`runs/<session>/judge_panel.json`)
```json
{
  "stage": 4,
  "status": "completed | degraded | failed",
  "input_source": "final_output.html",
  "input_size_bytes": 6664,
  "models_used": {
    "gemini": "gemini-2.5-pro",
    "gpt": "gpt-5",
    "claude": "claude-opus-4-7"
  },
  "models_resolution_source": {
    "gemini": "config | env | runtime_override",
    "gpt": "config",
    "claude": "env"
  },
  "evaluations": {
    "gemini": { ... 공통 스키마 ... },
    "gpt": { ... },
    "claude": { ... }
  },
  "aggregate": {
    "mean_scores": {
      "topic_fit": 7.67,
      "content_quality": 7.33,
      "interactivity": 8.0,
      "tone_authenticity": 6.0,
      "timeliness_trust": 7.67
    },
    "stdev_scores": {
      "topic_fit": 0.94,
      "content_quality": 0.47,
      "interactivity": 0.0,
      "tone_authenticity": 1.63,
      "timeliness_trust": 0.47
    },
    "weighted_total": 73.4,
    "outliers": [
      {
        "dimension": "tone_authenticity",
        "model": "claude",
        "score": 4,
        "mean": 6.0,
        "delta": -2.0,
        "outlier_severity": "high"
      }
    ]
  },
  "failed_models": [],
  "duration_ms": 12450,
  "cost_usd_estimate": 0.026
}
```

`models_resolution_source` 필드는 어드민 UI에서 "이 모델은 어디서 온 설정이지?" 보여주는 용도.

---

## Outlier 감지 룰

- 5 차원 각각, 3 모델 점수 mean ± stdev 계산
- 어느 모델 점수가 `mean ± 1.5σ` 벗어나면 outlier 표시
- σ가 매우 작으면 (< 0.5) outlier 판정 안 함 (의미 없음)
- severity:
  - `|delta| >= 2.0` → `high`
  - `1.0 <= |delta| < 2.0` → `medium`
  - 그 외 → `low`

---

## 동시 호출 구현 (asyncio.gather)

```python
async def evaluate(self, input_html: str) -> dict:
    runtime_override = self._get_runtime_override()  # B3-S3에서 hook
    
    tasks = [
        self._evaluate_with_gemini(input_html, runtime_override),
        self._evaluate_with_gpt(input_html, runtime_override),
        self._evaluate_with_claude(input_html, runtime_override),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    evaluations = {}
    failed_models = []
    for name, result in zip(["gemini", "gpt", "claude"], results):
        if isinstance(result, Exception):
            failed_models.append(name)
            logger.warning(f"Judge {name} failed: {result}")
        else:
            evaluations[name] = result
    
    if len(evaluations) == 0:
        return {"status": "failed", ...}
    if len(evaluations) < 3:
        return {"status": "degraded", "evaluations": evaluations, "failed_models": failed_models, ...}
    
    aggregate = self._compute_aggregate(evaluations)
    return {"status": "completed", "evaluations": evaluations, "aggregate": aggregate, ...}
```

---

## 평가 프롬프트 공통 골자

각 prompt 파일은 모델 차이를 반영한 톤 조정 외에는 공통 구조:

```markdown
# Judge (Gemini | GPT | Claude)

당신은 LG U+ 플러스탭 콘텐츠 공모전의 심사위원입니다.
독립적으로 평가하되, 아래 기준을 엄격히 따릅니다.

## 입력
runtime: final_output.html (렌더 HTML 전체)

## 평가 차원 (각 1-10점, 정수)
[5개 차원 설명 + 채점 가이드 — 모델별 동일]

## 점수 가이드
- 10: 출간 가능한 프로 콘텐츠 수준
- 7-9: 양질, 약간 다듬으면 출간 가능
- 4-6: 평균. 결정적 약점 1-2개
- 1-3: 결정적 결함, 재작성 필요

## 출력 형식
[공통 JSON 스키마]

## 규칙
- 점수와 코멘트 일관성 (점수 8인데 코멘트 약점 위주면 안 됨)
- one_line_verdict 50자 이내, 발표 자료에 그대로 인용 가능
- 자기 모델 출력에 호의적이 되지 말 것 (특히 Gemini Judge가 Gemini 생성 콘텐츠 평가 시)
- 추측 금지. HTML/콘텐츠에 실제 있는 것만 평가
```

---

## 단위 테스트

### `test_judge_panel.py` (8건)
| # | 케이스 | 검증 |
|---|---|---|
| 1 | Happy path (3 모델 모두 성공) | aggregate 정확 계산, status=completed |
| 2 | 1 모델 실패 (예: OpenAI rate limit) | 2 모델로 평균 산출, failed_models=["gpt"], status=degraded |
| 3 | 2 모델 실패 | status=degraded, evaluations 1개만 보존 |
| 4 | 3 모델 모두 실패 | status=failed |
| 5 | JSON 파싱 실패 (1 모델) | 해당 모델만 failed 처리 |
| 6 | outlier 감지 (high) | mean±1.5σ 벗어난 점수를 outliers에 high severity로 기록 |
| 7 | weighted_total 계산 | 5개 차원 × 가중치 = 100 검증 |
| 8 | concurrent 실행 | 3개 호출이 직렬 합보다 짧은 시간 (mock latency) |

### `test_judge_model_resolver.py` (5건)
| # | 케이스 | 검증 |
|---|---|---|
| 1 | runtime_override 있으면 최우선 | UI 설정 반영 |
| 2 | runtime_override 없고 env 있으면 env | 환경변수 반영 |
| 3 | runtime_override·env 없으면 config | 기본값 반영 |
| 4 | models_resolution_source 정확 기록 | "runtime_override"/"env"/"config" 라벨 정확 |
| 5 | 가중치 합 != 100 → ValidationError | startup 검증 동작 |

---

## 비용 추정

| 모델 | 호출당 입력 토큰 | 호출당 출력 토큰 | 단가 (입/출 per 1M) | 호출당 비용 |
|---|---|---|---|---|
| Gemini 2.5 Pro | ~2K (HTML 5KB) | ~1K | $1.25 / $5.00 | $0.0075 |
| GPT-5 | ~2K | ~1K | (실측 후 갱신) | ~$0.010 |
| Claude Opus 4.7 | ~2K | ~1K | (실측 후 갱신) | ~$0.015 |
| **합계** | | | | **~$0.032/run** |

⚠️ GPT-5, Claude Opus 4.7 단가는 명세서 작성 시점 추정. 구현 시 공식 docs 재확인 필수.

`budget_per_run_usd: 0.05` 로 안전 마진 잡음.

---

## 검증 방법

### Step 1. 구현
- 신규 파일 9개 생성 + 수정 파일 6개 변경
- 단위 테스트 13건 통과 (panel 8 + resolver 5)
- 회귀 테스트 전체 통과 (기존 36건 + 신규 13건 = 49건)

### Step 2. E2E with Judge
- 카테고리 "맛집" 1회 실행 (실제 LLM, 모든 환경변수 미설정 — config 기본값 사용 확인)
- `runs/<session>/judge_panel.json` 생성 확인
- 3 모델 평가 모두 채워졌는지, weighted_total 계산 정확한지 확인
- `models_resolution_source` 모두 "config" 인지 확인

### Step 3. 모델 우선순위 검증
- `JUDGE_GEMINI_MODEL=gemini-2.0-flash-exp` 환경변수 설정 후 1회 실행
- `models_resolution_source.gemini == "env"` 확인
- 다른 두 모델은 여전히 "config" 인지 확인

### Step 4. 의도된 실패 테스트
- OPENAI_API_KEY 빈 값으로 1회 실행 → status=degraded, failed_models=["gpt"] 확인
- 정상 산출물(final_output.html)은 영향 없음

---

## 롤백

- 신규 파일 9개 `git rm`
- 수정 파일 6개 `git checkout HEAD --` 으로 원복

---

## Claude Code 실행 지시

1. 위 "변경 대상" 의 신규 파일 9개 + 수정 파일 6개 작업
2. `judge_model_resolver.py` 의 3단계 우선순위 로직을 가장 먼저 구현 (테스트 우선)
3. 단위 테스트 13건 작성 + 통과 확인
4. 회귀 테스트 전체 통과 확인 (49건)
5. **실제 LLM E2E는 별도 명령에서 실행. 본 명령은 코드 작성 + 단위 테스트만**
6. 보고:
   - 신규/수정 파일 절대 경로 + 라인 수
   - 단위 테스트 13건 결과 (통과/실패)
   - 회귀 테스트 결과 (총 N건 / 통과 N건)
   - 의존 패키지 (`openai`, `anthropic`) requirements.txt 추가 여부
7. **git add / commit / stage 금지**

---

## 후속 작업 (본 명세서 완료 후)

- **B3-S2-E2E**: Judge Panel 포함 실제 LLM E2E 검증 (3회, B3-S1 패턴 답습)
- **B3-S3**: 어드민 UI 시작 (마스터 명세서는 이미 작성됨, 분할 명세서 A부터 진입)
