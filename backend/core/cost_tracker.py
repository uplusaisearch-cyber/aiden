"""LLM 호출 비용 추적 + 예산 한도 enforcement.

- **일일 누적**: `.cache/daily_cost.json` 에 영속화 (atomic replace)
- **월간 누적**: 일일 데이터의 같은 (YYYY-MM) prefix 합산으로 도출
- **run 단위**: in-memory (런 종료 시 휘발). Topic Newsroom 1회 = 1 run.

각 한도는 `Settings` (= `.env`) 에서 읽으며, **값이 0 이하면 해당 검사는 비활성**입니다.
한도 초과 시 `LLMBudgetExceeded` 예외가 발생합니다.

스레드 안전을 위해 `threading.RLock` 으로 직렬화합니다.
(FastAPI async 환경에서도 짧은 critical section 이라 안전합니다.)
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date
from pathlib import Path
from typing import Any

from backend.core.settings import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

CACHE_DIR: Path = PROJECT_ROOT / ".cache"
DAILY_FILE: Path = CACHE_DIR / "daily_cost.json"


class LLMBudgetExceeded(RuntimeError):
    """LLM 호출 비용/횟수가 예산 한도를 초과했을 때 발생합니다."""


class CostTracker:
    """비용 누적기 (싱글톤).

    `get_cost_tracker()` 로 접근하세요.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._daily: dict[str, float] = self._load_daily()
        # run_id -> {"cost": float, "calls": int, "prompt_tokens": int, "completion_tokens": int}
        # 토큰 필드는 2026-06-05 추가. 기존 cost/calls 누적 로직 무변경, 필드만 추가.
        self._runs: dict[str, dict[str, float]] = {}

    # ------------------------------------------------------------------
    # 파일 I/O
    # ------------------------------------------------------------------
    @staticmethod
    def _load_daily() -> dict[str, float]:
        if not DAILY_FILE.exists():
            return {}
        try:
            data = json.loads(DAILY_FILE.read_text(encoding="utf-8"))
            # 안전성: 숫자만 통과
            return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning(
                "daily_cost.json 읽기 실패 (%s). 빈 캐시로 시작합니다.", e
            )
            return {}

    def _save_daily(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = DAILY_FILE.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._daily, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(DAILY_FILE)  # 윈도우/리눅스 양쪽에서 atomic

    # ------------------------------------------------------------------
    # 한도 검사
    # ------------------------------------------------------------------
    def precheck(self, *, run_id: str | None = None) -> None:
        """호출 직전 예산 검사. 초과 시 `LLMBudgetExceeded` 발생."""
        s = get_settings()
        with self._lock:
            today = date.today().isoformat()

            # 일일 한도
            if s.daily_budget_usd > 0:
                daily = self._daily.get(today, 0.0)
                if daily >= s.daily_budget_usd:
                    raise LLMBudgetExceeded(
                        f"일일 예산 초과: ${daily:.4f} ≥ ${s.daily_budget_usd:.2f}. "
                        f"오늘({today}) LLM 호출이 차단됩니다. "
                        f".env 의 DAILY_BUDGET_USD 를 조정하거나, 캐시(.cache/daily_cost.json)를 초기화하세요."
                    )

            # 월간 한도
            if s.monthly_budget_usd > 0:
                monthly = self._monthly_total()
                if monthly >= s.monthly_budget_usd:
                    raise LLMBudgetExceeded(
                        f"월간 예산 초과: ${monthly:.4f} ≥ ${s.monthly_budget_usd:.2f}. "
                        f".env 의 MONTHLY_BUDGET_USD 를 조정하세요."
                    )

            # run 단위 한도
            if run_id is not None:
                r = self._runs.get(
                    run_id,
                    {"cost": 0.0, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
                )
                if s.max_llm_calls_per_run > 0 and r["calls"] >= s.max_llm_calls_per_run:
                    raise LLMBudgetExceeded(
                        f"run({run_id}) 호출 수 초과: {int(r['calls'])} ≥ "
                        f"{s.max_llm_calls_per_run}. 토론 라운드를 줄이거나 MAX_LLM_CALLS_PER_RUN 을 늘리세요."
                    )
                if s.per_run_budget_usd > 0 and r["cost"] >= s.per_run_budget_usd:
                    raise LLMBudgetExceeded(
                        f"run({run_id}) 비용 초과: ${r['cost']:.4f} ≥ "
                        f"${s.per_run_budget_usd:.2f}. PER_RUN_BUDGET_USD 를 조정하세요."
                    )

    # ------------------------------------------------------------------
    # 비용 기록
    # ------------------------------------------------------------------
    def record(
        self,
        cost_usd: float,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        run_id: str | None = None,
    ) -> None:
        """호출 직후 비용·토큰 기록 (daily 파일 즉시 저장).

        Args:
            cost_usd: 추정 비용. 음수면 무시.
            prompt_tokens: SDK 응답에서 실측된 prompt 토큰. 모르면 0 폴백.
            completion_tokens: SDK 응답에서 실측된 completion 토큰. 모르면 0 폴백.
            run_id: 있을 때만 run 단위 누적 (토큰 포함). 일일/월간 누적은 토큰 미반영.
        """
        if cost_usd < 0:
            return
        with self._lock:
            today = date.today().isoformat()
            self._daily[today] = self._daily.get(today, 0.0) + cost_usd
            self._save_daily()

            if run_id is not None:
                r = self._runs.setdefault(
                    run_id,
                    {"cost": 0.0, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
                )
                r["cost"] += cost_usd
                r["calls"] = int(r["calls"]) + 1
                r["prompt_tokens"] = int(r.get("prompt_tokens", 0)) + max(0, int(prompt_tokens))
                r["completion_tokens"] = int(r.get("completion_tokens", 0)) + max(
                    0, int(completion_tokens)
                )

    # ------------------------------------------------------------------
    # 조회 / 관리
    # ------------------------------------------------------------------
    def _monthly_total(self) -> float:
        today = date.today()
        prefix = f"{today.year:04d}-{today.month:02d}"
        return sum(v for k, v in self._daily.items() if k.startswith(prefix))

    def snapshot(self, *, run_id: str | None = None) -> dict[str, Any]:
        """현재 누적 상태 스냅샷 (디버그/UI용)."""
        with self._lock:
            today = date.today().isoformat()
            snap: dict[str, Any] = {
                "today": today,
                "daily_cost_usd": round(self._daily.get(today, 0.0), 6),
                "monthly_cost_usd": round(self._monthly_total(), 6),
            }
            if run_id is not None:
                r = self._runs.get(
                    run_id,
                    {"cost": 0.0, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
                )
                snap["run_id"] = run_id
                snap["run_cost_usd"] = round(float(r["cost"]), 6)
                snap["run_calls"] = int(r["calls"])
                snap["run_prompt_tokens"] = int(r.get("prompt_tokens", 0))
                snap["run_completion_tokens"] = int(r.get("completion_tokens", 0))
                snap["run_total_tokens"] = (
                    snap["run_prompt_tokens"] + snap["run_completion_tokens"]
                )
            return snap

    def reset_run(self, run_id: str) -> None:
        """run 단위 카운터 제거 (run 종료 시 호출 권장, 메모리 누수 방지)."""
        with self._lock:
            self._runs.pop(run_id, None)

    def reset_daily_cache(self) -> None:
        """일일 캐시 파일 초기화 (테스트/리셋 용)."""
        with self._lock:
            self._daily.clear()
            if DAILY_FILE.exists():
                DAILY_FILE.unlink()


# =====================================================================
# 싱글톤
# =====================================================================
_tracker: CostTracker | None = None
_singleton_lock = threading.Lock()


def get_cost_tracker() -> CostTracker:
    """프로세스 전역 단일 인스턴스 반환."""
    global _tracker
    if _tracker is None:
        with _singleton_lock:
            if _tracker is None:
                _tracker = CostTracker()
    return _tracker
