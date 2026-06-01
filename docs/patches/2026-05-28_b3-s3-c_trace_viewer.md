# B3-S3-C 트레이스 뷰어 작업 명세서

**작성일**: 2026-05-28
**범위**: `/run/<session_id>` 페이지 본격 구현
**의존**: B3-S3-B 완료 (SSE 스트림 + RunDetail API + ChatMessage 스키마)
**마스터**: `docs/patches/2026-05-25_bundle3_step3_admin_ui_master_v2.md`

---

## 0. 결정사항 확정

| 항목 | 결정 |
|---|---|
| 사람말투 변환 | **룰베이스** (페르소나별 어미·prefix 템플릿) |
| 페르소나 정의 위치 | `backend/config/personas.yaml` → API 노출 |
| iter 1/2/3 레이아웃 | **세로 누적**, iter 헤더 + 색 변화 |
| 재생 모드 | **인스턴트(기본) / 애니메이션 토글** |
| Mock fallback | **제거**, 명시적 에러 표시 |
| 좌측 Stage 패널 | **2단 계층** (Newsroom 펼치면 9 에이전트) |
| Now Playing 4개 | 에이전트 이름·이모지·페르소나 / Stage+iter / elapsed / 누적 토큰·비용 |

---

## 1. 작업 개요

| # | 파일 | 작업 |
|---|---|---|
| 1 | `backend/config/personas.yaml` | 신규 (9 에이전트 페르소나 정의) |
| 2 | `backend/services/humanizer.py` | 신규 (룰베이스 텍스트 변환기) |
| 3 | `backend/services/sse_broker.py` | 수정 (humanized 필드 추가) |
| 4 | `backend/api/personas.py` | 신규 (`GET /api/personas`) |
| 5 | `backend/main.py` | 라우터 등록 |
| 6 | `frontend/lib/personas.ts` | 신규 (페르소나 타입 + 클라이언트 fetch) |
| 7 | `frontend/components/run/StagePanel.tsx` | 신규 (좌측, 2단 계층) |
| 8 | `frontend/components/run/ChatStream.tsx` | 신규 (중앙, 채팅 버블 + iter 그룹) |
| 9 | `frontend/components/run/NowPlayingPanel.tsx` | 신규 (우측, 4개 정보) |
| 10 | `frontend/components/run/PlaybackToggle.tsx` | 신규 (인스턴트/애니메이션 토글) |
| 11 | `frontend/hooks/useRunStream.ts` | 신규 (SSE 구독 + 상태 머신) |
| 12 | `frontend/app/run/[id]/page.tsx` | placeholder → 본격 구현 |
| 13 | `tests/test_humanizer.py` | 신규 (단위 테스트) |
| 14 | `tests/test_personas_api.py` | 신규 (API 테스트) |

테스트 11건 + 수동 검증 체크리스트.

---

## 2. 페르소나 정의

### 2-1. `backend/config/personas.yaml` 신규

```yaml
# AIDEN 9 에이전트 페르소나 정의
# - 트레이스 뷰어의 채팅 버블 + 좌측 Stage 패널 + Now Playing 패널에서 사용
# - 비개발자도 수정 가능. 어미·prefix·oneliner만 바꿔도 톤이 즉시 변경됨
# - humanizer.py가 이 파일을 로드해 raw trace → 사람말투 변환

version: 1

personas:
  trend_scout:
    display_name: "트렌드 정찰"
    nickname: "정찰병"
    emoji: "🔭"
    oneliner: "발로 뛰는 막내 기자, 핫이슈 사냥꾼"
    stage: "topic_newsroom"
    order: 1
    color_hex: "#F59E0B"   # amber
    speech:
      prefix_options:
        - "방금 발견했는데요,"
        - "트렌드 잡았어요—"
        - "현장에서 보니까,"
      suffix_options:
        - "잡았습니다!"
        - "뜨고 있더라구요."
        - "이거 떡상 중이에요."
      filler_options: ["그래서요,", "참고로요,"]

  audience_analyst:
    display_name: "독자 분석"
    nickname: "분석가"
    emoji: "🎯"
    oneliner: "데이터 룸의 침착한 분석가"
    stage: "topic_newsroom"
    order: 2
    color_hex: "#3B82F6"   # blue
    speech:
      prefix_options:
        - "데이터를 보면,"
        - "독자 반응을 분석하면,"
        - "타겟 관점에선,"
      suffix_options:
        - "로 분석됩니다."
        - "경향이 있어요."
        - "가능성 높아요."
      filler_options: ["덧붙이면,", "한 가지 더,"]

  strategy_planner:
    display_name: "편집 기획"
    nickname: "기획 데스크"
    emoji: "🧭"
    oneliner: "큰 그림 그리는 편집 기획"
    stage: "topic_newsroom"
    order: 3
    color_hex: "#8B5CF6"   # violet
    speech:
      prefix_options:
        - "정리하면,"
        - "결정하자면,"
        - "방향은 이렇게—"
      suffix_options:
        - "로 가시죠."
        - "이 앵글이 좋겠네요."
        - "최종 결정합니다."
      filler_options: ["요약하면,", "핵심은,"]

  writer:
    display_name: "집필"
    nickname: "작가"
    emoji: "✍️"
    oneliner: "마감에 쫓기는 열혈 신입 기자"
    stage: "content_newsroom"
    order: 4
    color_hex: "#10B981"   # emerald
    speech:
      prefix_options:
        - "일단 초안인데요,"
        - "이렇게 써봤어요—"
        - "방금 쓴 건데,"
      suffix_options:
        - "어떠세요?"
        - "괜찮을까요?"
        - "이 정도면 될까요?"
      filler_options: ["참고로,", "추가로,"]

  fact_checker:
    display_name: "팩트 검증"
    nickname: "검증 데스크"
    emoji: "🔍"
    oneliner: "꼬치꼬치 물어보는 사람"
    stage: "content_newsroom"
    order: 5
    color_hex: "#EAB308"   # yellow
    speech:
      prefix_options:
        - "잠깐, 이 부분—"
        - "출처 확인했는데요,"
        - "팩트체크 결과,"
      suffix_options:
        - "확인 필요합니다."
        - "출처 어디예요?"
        - "검증 완료."
      filler_options: ["덧붙이면,", "그리고요,"]

  devils_advocate:
    display_name: "반론 제기"
    nickname: "악마"
    emoji: "😈"
    oneliner: "회의실의 미운 오리, 모든 걸 의심"
    stage: "content_newsroom"
    order: 6
    color_hex: "#EF4444"   # red
    speech:
      prefix_options:
        - "반박하자면,"
        - "솔직히 말해서,"
        - "그게 진짜 맞아요?"
      suffix_options:
        - "이거 약한데요."
        - "별로인데?"
        - "근거 부족합니다."
      filler_options: ["더 짚자면,", "한 가지 더,"]

  editor_in_chief:
    display_name: "편집국장"
    nickname: "편집장"
    emoji: "👔"
    oneliner: "최종 결재권자, 책임지는 사람"
    stage: "content_newsroom"
    order: 7
    color_hex: "#1F2937"   # slate-800
    speech:
      prefix_options:
        - "정리하죠."
        - "최종 판단하면,"
        - "지금까지 들었는데,"
      suffix_options:
        - "확정합니다."
        - "OK, 이걸로 마감."
        - "통과."
      filler_options: ["그러니까,", "결론적으로,"]

  format_architect:
    display_name: "포맷 설계"
    nickname: "아트 디렉터"
    emoji: "🎨"
    oneliner: "지면 레이아웃 짜는 사람"
    stage: "gameifier"
    order: 8
    color_hex: "#EC4899"   # pink
    speech:
      prefix_options:
        - "레이아웃은,"
        - "이 콘텐츠 보니까,"
        - "포맷 결정—"
      suffix_options:
        - "타입으로 갑니다."
        - "배치하면 좋겠네요."
        - "이렇게 짭니다."
      filler_options: ["참고로,", "디테일은,"]

  html_builder:
    display_name: "퍼블리싱"
    nickname: "퍼블리셔"
    emoji: "🛠️"
    oneliner: "코드로 결과물 마감하는 개발자"
    stage: "gameifier"
    order: 9
    color_hex: "#06B6D4"   # cyan
    speech:
      prefix_options:
        - "빌드 시작합니다."
        - "코딩 들어가서—"
        - "HTML 짜는 중,"
      suffix_options:
        - "빌드 완료."
        - "떴습니다."
        - "퍼블 완성."
      filler_options: ["참고로,", "메모로,"]

# Stage 메타데이터 (좌측 패널의 1단 계층)
stages:
  topic_newsroom:
    display_name: "Topic Newsroom"
    subtitle: "주제 발굴"
    emoji: "📰"
    agents: ["trend_scout", "audience_analyst", "strategy_planner"]
  content_newsroom:
    display_name: "Content Newsroom"
    subtitle: "콘텐츠 토론 (iter 1~3)"
    emoji: "🗣️"
    agents: ["writer", "fact_checker", "devils_advocate", "editor_in_chief"]
  gameifier:
    display_name: "Game-ifier"
    subtitle: "인터랙티브 변환"
    emoji: "🎮"
    agents: ["format_architect", "html_builder"]
```

**비개발자 수정 포인트**: emoji, oneliner, speech 블록만 바꿔도 즉시 톤이 변함. 코드 변경 0.

---

## 3. 사람말투 변환기

### 3-1. `backend/services/humanizer.py` 신규

**입력**: raw trace 텍스트 (LLM 응답 또는 trace_logger 요약)
**출력**: 페르소나 prefix + 원본의 자연어 요약 + suffix 1~2개를 조합한 1~3문장

```python
"""
룰베이스 사람말투 변환기.
- personas.yaml 로드 후 캐싱
- humanize(agent_id, raw_text) → str
- 결정론적: 같은 입력 → 같은 출력 (seed 기반)
"""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PERSONAS_PATH = Path(__file__).parent.parent / "config" / "personas.yaml"
_MAX_LEN = 280   # 채팅 버블 한 줄 안전 길이


@lru_cache(maxsize=1)
def load_personas() -> dict[str, Any]:
    if not _PERSONAS_PATH.exists():
        logger.warning("personas.yaml not found: %s", _PERSONAS_PATH)
        return {"personas": {}, "stages": {}}
    with _PERSONAS_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _seed_pick(options: list[str], seed_text: str) -> str:
    """raw_text 해시 기반 결정론적 선택"""
    if not options:
        return ""
    h = int(hashlib.md5(seed_text.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def _summarize(raw_text: str, max_chars: int = 200) -> str:
    """원본 텍스트의 첫 1~2문장만 추출. JSON·코드블록 안전 처리."""
    if not raw_text:
        return ""
    # JSON / code fence 제거
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # ```json ... ``` 형태면 본문만 추출 시도
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.startswith("```"))
    # 첫 2문장
    sentences = []
    buf = ""
    for ch in cleaned:
        buf += ch
        if ch in "다.!?\n" and len(buf.strip()) > 5:
            sentences.append(buf.strip())
            buf = ""
            if len(sentences) >= 2:
                break
    if buf.strip():
        sentences.append(buf.strip())
    summary = " ".join(sentences)[:max_chars]
    return summary.rstrip()


def humanize(agent_id: str, raw_text: str, iter_no: int | None = None) -> str:
    """
    agent_id: personas.yaml의 키 (예: "trend_scout")
    raw_text: LLM 원본 출력 또는 trace 요약
    iter_no: Content Newsroom의 iter 번호 (선택). 변환에는 미사용, 메타로 캡처.

    반환: "{prefix} {summary} {suffix}" 형태의 1~3문장
    """
    data = load_personas()
    personas = data.get("personas", {})
    p = personas.get(agent_id)
    if not p:
        logger.debug("persona not found: %s", agent_id)
        return _summarize(raw_text)

    speech = p.get("speech", {})
    seed = f"{agent_id}::{raw_text[:50]}"
    prefix = _seed_pick(speech.get("prefix_options", []), seed)
    suffix = _seed_pick(speech.get("suffix_options", []), seed + "::suf")
    body = _summarize(raw_text, max_chars=_MAX_LEN - len(prefix) - len(suffix) - 4)

    parts = [s for s in [prefix, body, suffix] if s]
    result = " ".join(parts).strip()
    return result[:_MAX_LEN]


def get_persona(agent_id: str) -> dict[str, Any] | None:
    """페르소나 메타 조회 (API에서 사용)"""
    return load_personas().get("personas", {}).get(agent_id)


def get_all_personas() -> dict[str, Any]:
    """전체 페르소나 + stages 조회"""
    return load_personas()
```

### 3-2. `backend/services/sse_broker.py` 수정

기존 `ChatMessage` 직렬화 시 `humanized` 필드 추가.

```python
# sse_broker.py 내 ChatMessage 변환 로직
from backend.services.humanizer import humanize

def build_chat_message(agent_id: str, raw_text: str, iter_no: int | None) -> dict:
    return {
        "agent_id": agent_id,
        "iter": iter_no,
        "raw": raw_text,
        "humanized": humanize(agent_id, raw_text, iter_no),
        "ts": ...,
    }
```

⚠️ 기존 raw 필드는 유지 (디버그·재현용). humanized는 추가만.

---

## 4. 페르소나 API

### 4-1. `backend/api/personas.py` 신규

```python
from fastapi import APIRouter
from backend.services.humanizer import get_all_personas

router = APIRouter(prefix="/api/personas", tags=["personas"])

@router.get("")
def list_personas():
    """페르소나 + stages 메타 전체 반환. 프론트 캐시 권장."""
    return get_all_personas()
```

### 4-2. `backend/main.py` 라우터 등록

```python
from backend.api import personas
app.include_router(personas.router)
```

---

## 5. 프론트 — 페르소나 fetch & 타입

### 5-1. `frontend/lib/personas.ts` 신규

```typescript
export interface Persona {
  display_name: string;
  nickname: string;
  emoji: string;
  oneliner: string;
  stage: 'topic_newsroom' | 'content_newsroom' | 'gameifier';
  order: number;
  color_hex: string;
  speech: {
    prefix_options: string[];
    suffix_options: string[];
    filler_options: string[];
  };
}

export interface StageMeta {
  display_name: string;
  subtitle: string;
  emoji: string;
  agents: string[];
}

export interface PersonasData {
  version: number;
  personas: Record<string, Persona>;
  stages: Record<string, StageMeta>;
}

let _cache: PersonasData | null = null;

export async function fetchPersonas(): Promise<PersonasData> {
  if (_cache) return _cache;
  const res = await fetch('/api/personas');
  if (!res.ok) throw new Error('failed to fetch personas');
  _cache = await res.json();
  return _cache!;
}

export function clearPersonasCache() { _cache = null; }
```

---

## 6. SSE 구독 훅

### 6-1. `frontend/hooks/useRunStream.ts` 신규

상태 머신:
- `connecting` → `streaming` → `completed` / `error`
- `ChatMessage[]` 누적
- 현재 활성 에이전트·stage·iter 트래킹
- elapsed (ms), 토큰·비용 누적 추적

```typescript
import { useEffect, useRef, useState } from 'react';

export type RunStatus = 'connecting' | 'streaming' | 'completed' | 'error';

export interface ChatMessage {
  agent_id: string;
  iter: number | null;
  raw: string;
  humanized: string;
  ts: number;
}

export interface RunState {
  status: RunStatus;
  messages: ChatMessage[];
  currentAgent: string | null;
  currentStage: string | null;
  currentIter: number | null;
  startedAt: number | null;
  elapsedMs: number;
  totalTokens: number;
  totalCostUSD: number;
  error: string | null;
}

export function useRunStream(runId: string): RunState {
  const [state, setState] = useState<RunState>({
    status: 'connecting',
    messages: [],
    currentAgent: null,
    currentStage: null,
    currentIter: null,
    startedAt: null,
    elapsedMs: 0,
    totalTokens: 0,
    totalCostUSD: 0,
    error: null,
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`/api/runs/${runId}/stream`);
    esRef.current = es;

    es.addEventListener('agent_start', (ev: MessageEvent) => {
      const d = JSON.parse(ev.data);
      setState(s => ({
        ...s,
        currentAgent: d.agent_id,
        currentStage: d.stage,
        currentIter: d.iter ?? null,
        startedAt: s.startedAt ?? Date.now(),
        status: 'streaming',
      }));
    });

    es.addEventListener('chat_message', (ev: MessageEvent) => {
      const msg: ChatMessage = JSON.parse(ev.data);
      setState(s => ({ ...s, messages: [...s.messages, msg] }));
    });

    es.addEventListener('agent_end', (ev: MessageEvent) => {
      const d = JSON.parse(ev.data);
      setState(s => ({
        ...s,
        totalTokens: s.totalTokens + (d.tokens ?? 0),
        totalCostUSD: s.totalCostUSD + (d.cost_usd ?? 0),
      }));
    });

    es.addEventListener('run_complete', () => {
      setState(s => ({ ...s, status: 'completed' }));
      es.close();
    });

    es.onerror = () => {
      setState(s => ({ ...s, status: 'error', error: 'SSE connection lost' }));
      es.close();
    };

    return () => { es.close(); esRef.current = null; };
  }, [runId]);

  // elapsed 카운트업 (1초 간격)
  useEffect(() => {
    if (state.status !== 'streaming' || !state.startedAt) return;
    const id = setInterval(() => {
      setState(s => ({ ...s, elapsedMs: Date.now() - (s.startedAt ?? Date.now()) }));
    }, 1000);
    return () => clearInterval(id);
  }, [state.status, state.startedAt]);

  return state;
}
```

⚠️ 백엔드 SSE 이벤트 이름(`agent_start`, `chat_message`, `agent_end`, `run_complete`)이 실제 `sse_broker.py` 구현과 일치하는지 **Claude Code가 직접 확인 필요**. 다르면 훅 이벤트명만 맞춰서 수정.

---

## 7. 좌측 — Stage 패널

### 7-1. `frontend/components/run/StagePanel.tsx` 신규

- 2단 계층 (3 Newsroom 카드 → 펼치면 에이전트 줄)
- 현재 활성 에이전트 highlight (페르소나 color_hex 사용)
- 완료된 에이전트는 체크 표시, 진행 중은 펄스 애니메이션, 대기는 회색

레이아웃:
```
📰 Topic Newsroom              [완료]
  🔭 트렌드 정찰    ✓
  🎯 독자 분석     ✓
  🧭 편집 기획     ✓

🗣️ Content Newsroom            [iter 2 진행]
  ✍️ 작가          ✓ (iter 1, 2)
  🔍 검증 데스크    ⏵ (iter 2 진행 중)
  😈 악마          · 대기
  👔 편집국장       · 대기

🎮 Game-ifier                  [대기]
  🎨 아트 디렉터    · 대기
  🛠️ 퍼블리셔      · 대기
```

Props:
```typescript
interface StagePanelProps {
  personasData: PersonasData;
  currentAgent: string | null;
  completedAgents: Set<string>;  // 메시지 받은 에이전트
  iterByAgent: Record<string, number>;  // agent_id → 최신 iter
}
```

---

## 8. 중앙 — Chat Stream

### 8-1. `frontend/components/run/ChatStream.tsx` 신규

- 메시지를 시간순 누적
- Content Newsroom 메시지는 iter별 그룹핑 헤더 (`— iter 1 —`, `— iter 2 —`)
- 채팅 버블: 좌측에 페르소나 이모지·이름·시간, 우측 본문(humanized)
- 본문 클릭 시 raw 토글 (코드 블록 + 들여쓰기, 작은 글씨)
- 새 메시지 도착 시 자동 스크롤 bottom (사용자가 스크롤 올리면 자동 스크롤 OFF + "↓ 새 메시지" 배지)

iter 헤더 디자인:
```
─────── iter 1 (Writer 초안) ───────
✍️ 작가 [12:03:15]
"일단 초안인데요, ~~~ 어떠세요?"

🔍 검증 데스크 [12:03:18]
"잠깐, 이 부분 출처 어디예요?"

😈 악마 [12:03:21]
"반박하자면, ~~~ 별로인데?"

👔 편집국장 [12:03:24]
"정리하죠. iter 2 가시죠."

─────── iter 2 ───────
...
```

iter 헤더 색상: iter1 = 연한 회색, iter2 = 연한 노랑, iter3 = 연한 빨강 (수렴 어려움 시각화).

### 8-2. 재생 모드 토글 (`PlaybackToggle.tsx`)

- "인스턴트" (기본, 한 번에 표시) / "재생" (typing 시뮬, 50~200ms/character)
- 과거 run에서만 의미 있음 (라이브는 SSE 자체가 점진적 도착)
- 토글 상태는 URL query param (`?playback=animate`) 으로 공유 가능

⚠️ **명세**: 라이브 run에서는 토글 비활성화 + tooltip "라이브 스트림은 실시간 표시됩니다".

---

## 9. 우측 — Now Playing 패널

### 9-1. `frontend/components/run/NowPlayingPanel.tsx` 신규

4개 카드:

1. **현재 에이전트 카드**
   - 큰 이모지 + 별명 + display_name
   - oneliner 1줄
   - 페르소나 color_hex 액센트
   - 비활성 (대기/완료) 시 회색

2. **Stage + iter 카드**
   - "Content Newsroom · iter 2/3"
   - iter 진행 dot (●●○) 시각화

3. **Elapsed 카드**
   - "00:01:42" 카운트업
   - 1초 간격 업데이트

4. **누적 사용량 카드**
   - 토큰 (예: 12,403 tokens)
   - 비용 (예: $0.018)
   - 현재 진행 중인 호출 1개당 평균 표시 (선택)

---

## 10. 페이지 통합

### 10-1. `frontend/app/run/[id]/page.tsx` 본격 구현

기존 placeholder 제거. 3-컬럼 레이아웃 (lg 이상). 모바일은 탭 전환.

```typescript
'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useRunStream } from '@/hooks/useRunStream';
import { fetchPersonas, PersonasData } from '@/lib/personas';
import { StagePanel } from '@/components/run/StagePanel';
import { ChatStream } from '@/components/run/ChatStream';
import { NowPlayingPanel } from '@/components/run/NowPlayingPanel';
import { PlaybackToggle } from '@/components/run/PlaybackToggle';

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const run = useRunStream(id);
  const [personas, setPersonas] = useState<PersonasData | null>(null);

  useEffect(() => { fetchPersonas().then(setPersonas); }, []);

  if (!personas) return <div className="p-8">페르소나 로딩...</div>;
  if (run.status === 'error') {
    return (
      <div className="p-8 text-red-600">
        스트림 연결 실패: {run.error}
        <br />백엔드 SSE 엔드포인트 확인 필요.
      </div>
    );
  }

  // 파생 상태
  const completedAgents = new Set(run.messages.map(m => m.agent_id));
  const iterByAgent: Record<string, number> = {};
  run.messages.forEach(m => {
    if (m.iter !== null) iterByAgent[m.agent_id] = Math.max(iterByAgent[m.agent_id] ?? 0, m.iter);
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_300px] gap-4 p-4 h-screen">
      <aside className="overflow-y-auto">
        <StagePanel
          personasData={personas}
          currentAgent={run.currentAgent}
          completedAgents={completedAgents}
          iterByAgent={iterByAgent}
        />
      </aside>
      <main className="overflow-y-auto">
        <div className="flex justify-between items-center mb-2">
          <h1 className="font-bold">Run {id.slice(0, 8)}</h1>
          <PlaybackToggle disabled={run.status === 'streaming'} />
        </div>
        <ChatStream messages={run.messages} personas={personas.personas} />
      </main>
      <aside className="overflow-y-auto">
        <NowPlayingPanel
          run={run}
          personas={personas.personas}
        />
      </aside>
    </div>
  );
}
```

---

## 11. 단위 테스트

### 11-1. `tests/test_humanizer.py` 신규

| # | 케이스 | 검증 |
|---|---|---|
| 1 | `load_personas()` 정상 로드 | 9 personas + 3 stages 존재 |
| 2 | `humanize("trend_scout", "...")` 결정론 | 같은 입력 → 같은 출력 (3회 호출 동일) |
| 3 | 알 수 없는 agent_id | `_summarize` 결과만 반환 (prefix·suffix 없음) |
| 4 | 빈 raw_text | 빈 문자열 또는 prefix·suffix만 |
| 5 | 매우 긴 raw_text (>1000자) | 결과 ≤ 280자 |
| 6 | JSON code block 포함된 raw | 펜스 제거 + 본문 추출 |
| 7 | personas.yaml에 없는 stage | 안전 폴백 (KeyError 없음) |

### 11-2. `tests/test_personas_api.py` 신규

| # | 케이스 | 검증 |
|---|---|---|
| 8 | `GET /api/personas` 200 | personas, stages 키 존재 |
| 9 | 9 에이전트 모두 응답 | trend_scout ~ html_builder |
| 10 | 각 페르소나 필수 필드 | display_name, emoji, stage, color_hex, speech |
| 11 | personas.yaml 변경 후 재호출 | `load_personas.cache_clear()` 후 변경 반영 (테스트에서 직접 cache_clear) |

⚠️ 프론트 단위 테스트는 마감 일정 고려해 본 명세에서 생략. 수동 검증으로 대체.

---

## 12. 수동 검증 체크리스트

Claude Code 작업 완료 후 **사용자 직접** 수행:

### 12-1. 백엔드
- [ ] `curl http://localhost:8000/api/personas` 200, 9 personas + 3 stages
- [ ] `pytest tests/test_humanizer.py tests/test_personas_api.py -v` 전부 PASS
- [ ] `personas.yaml` 의 `trend_scout.emoji` 를 다른 값으로 바꾸고 재시작 → API 반영 확인 → 원복

### 12-2. 프론트
- [ ] `npm run dev` → `http://localhost:3000/run/<기존 session_id>` 진입
- [ ] 좌측 Stage 패널 3 Newsroom 카드 + 9 에이전트 표시
- [ ] 중앙 채팅 영역: 메시지 시간순 누적, iter 헤더 색 변화 (1→2→3)
- [ ] 채팅 버블 본문 클릭 → raw 토글 동작
- [ ] 우측 Now Playing: 현재 에이전트·Stage·elapsed·토큰 4개 카드
- [ ] 새 run 생성 (`/` 메인에서 generate) → 라이브 SSE로 9 에이전트 실시간 도착
- [ ] 백엔드 끄고 페이지 새로고침 → mock fallback 없이 명시적 에러 표시
- [ ] PlaybackToggle: 라이브 중 비활성 / 완료된 run 진입 시 활성

---

## 13. 미해결 / 다음 명세 이월

- **B3-S3-D (Judge 시각화)**: 본 명세 범위 외. 채팅 영역 하단에 Judge 결과 placeholder 만 두기.
- **Persona Lab UI**: `/admin/personas` 라우트는 본 명세에서 placeholder만, B3-S3-E에서 본격.
- **모바일 반응형 폴리싱**: lg 미만 탭 전환은 최소 동작만. 디테일은 폴리싱 단계.
- **iter 색상 접근성**: 색맹 사용자 고려한 아이콘 보강은 폴리싱 단계.

---

## 14. 작업 순서 (Claude Code용)

1. `backend/config/personas.yaml` 작성 (작업 2-1)
2. `backend/services/humanizer.py` 작성 (작업 3-1)
3. `backend/services/sse_broker.py` 의 ChatMessage 직렬화에 `humanized` 필드 추가 (작업 3-2)
4. `backend/api/personas.py` + `main.py` 라우터 등록 (작업 4)
5. `tests/test_humanizer.py` + `tests/test_personas_api.py` 작성 + `pytest` PASS 확인
6. `frontend/lib/personas.ts` + `frontend/hooks/useRunStream.ts` 작성 (작업 5, 6)
7. `frontend/components/run/` 4개 컴포넌트 작성 (작업 7, 8, 9)
8. `frontend/app/run/[id]/page.tsx` 본격 구현 (작업 10)
9. `npm run build` 통과 확인 (타입 에러 0)
10. 변경 파일 목록 출력 + 사용자에게 수동 검증 안내

각 단계 완료 후 짧은 상태 보고 (변경된 파일 목록만). git add/commit 자동 금지.

---

## 15. 환경 / 의존성

- 백엔드: `pyyaml>=6.0` (이미 있을 가능성 높음, 없으면 `requirements.txt` 추가)
- 프론트: 추가 dep 없음 (EventSource는 브라우저 기본)

---

## 16. 회귀 영향 점검

- ChatMessage 스키마 변경 (`humanized` 추가) → 메인 페이지의 `recentRuns` 표시는 영향 없음 (다른 엔드포인트). 그래도 한 번 확인.
- `humanizer.py` import 누락 시 `sse_broker.py` 실패 → 단위 테스트로 차단.
- `personas.yaml` 미배포 시 API 500 → `load_personas()` 가 빈 dict 반환, API는 200 with empty.

---

## 작업 종료 조건

- [ ] 단위 테스트 11건 PASS
- [ ] `/api/personas` 응답 정상
- [ ] `/run/<id>` 페이지에서 3-컬럼 레이아웃 + 9 에이전트 실시간 표시 동작
- [ ] 사용자 수동 검증 §12 모두 통과
- [ ] `PROGRESS.md` 에 B3-S3-C 완료 체크 + 의사결정 로그 1줄 추가
