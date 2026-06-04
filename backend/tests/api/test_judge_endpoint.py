"""GET /api/runs/{id}/judge + /final-html 테스트 (B3-S3-D, 5건)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app


def _write_judge_panel(run_dir: Path, payload: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "judge_panel.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )


def _high_consensus_payload() -> dict:
    """모든 모델이 거의 동일 점수 (max stdev < 1.0)."""
    return {
        "stage": 4,
        "status": "completed",
        "models_used": {"gemini": "gemini-2.5-pro", "gpt": "gpt-5",
                        "claude": "claude-opus-4-7"},
        "evaluations": {
            "gemini": {
                "model": "gemini-2.5-pro",
                "scores": {"topic_fit": 8, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 8.0,
                "one_line_verdict": "균형 잡힘.",
                "strengths": ["탄탄"], "weaknesses": [],
            },
            "gpt": {
                "model": "gpt-5",
                "scores": {"topic_fit": 8, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 8.0,
                "one_line_verdict": "안정.",
                "strengths": ["일관"], "weaknesses": [],
            },
            "claude": {
                "model": "claude-opus-4-7",
                "scores": {"topic_fit": 8, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 8.0,
                "one_line_verdict": "양호.",
                "strengths": ["견고"], "weaknesses": [],
            },
        },
        "aggregate": {
            "mean_scores": {"topic_fit": 8.0, "content_quality": 8.0,
                            "interactivity": 8.0, "tone_authenticity": 8.0,
                            "timeliness_trust": 8.0},
            "stdev_scores": {"topic_fit": 0.0, "content_quality": 0.0,
                             "interactivity": 0.0, "tone_authenticity": 0.0,
                             "timeliness_trust": 0.0},
            "weighted_total": 80.0,
            "outliers": [],
        },
    }


def _outlier_payload() -> dict:
    """gemini 가 interactivity 에서 크게 이탈 (1.5σ 초과)."""
    # scores: 9 / 5 / 5 → mean=6.33, stdev≈2.31, |9-6.33|=2.67 > 1.5*2.31=3.46? No.
    # 더 극단: 9 / 4 / 4 → mean=5.67, stdev≈2.89, 1.5σ=4.33, |9-5.67|=3.33 < 4.33 → no.
    # 한 모델만 큰 격차: scores 10 / 5 / 5 → mean=6.67, stdev=2.89, 1.5σ=4.33,
    # |10-6.67|=3.33 < 4.33 → no.
    # stdev 가 너무 커지면 outlier 판정 어려움. 다른 축은 비슷, 한 축만 격차:
    # interactivity 만 10/6/6, 나머지는 같음 → 그 축 stdev=2.31, 1.5σ=3.46
    # |10-7.33|=2.67 < 3.46 → still not outlier.
    # 극단 case: 한 모델만 한 축에서 매우 다른 값
    # gemini interactivity=10, gpt=7, claude=7 (균등 외 1개) → stdev=1.73, 1.5σ=2.60
    # |10-8|=2.0 < 2.60 → still no.
    # 두 모델 동일 + 1 모델 차이 → stdev 작아짐
    # 5,5,10 → mean=6.67, stdev=2.89, 1.5σ=4.33 → no
    # 7,7,10 → mean=8, stdev=1.73, 1.5σ=2.60, |10-8|=2 → no
    # 8,8,10 → mean=8.67, stdev=1.15, 1.5σ=1.73, |10-8.67|=1.33 → no
    # 9,9,10 → mean=9.33, stdev=0.58, 1.5σ=0.87, |10-9.33|=0.67 → no
    # 9,9,5 → mean=7.67, stdev=2.31, 1.5σ=3.46, |5-7.67|=2.67 → no
    # Looking at theory: with N=3, max |x_i - mean|/stdev <= sqrt(2). sqrt(2)≈1.414 < 1.5.
    # 따라서 N=3 정확 균등 stdev 로는 outlier 판정 불가능.
    # 우리 코드는 raw stdev_scores 를 받음 → 외부에서 직접 stdev 값을 작게 주면 OK.
    # 실제 judge_panel.py 가 population stdev 를 쓰는지 sample stdev 를 쓰는지 미상.
    # 테스트 목적상 stdev_scores 를 작게 mock 해서 outlier 보이도록.
    return {
        "stage": 4,
        "status": "completed",
        "models_used": {"gemini": "gemini-2.5-pro", "gpt": "gpt-5",
                        "claude": "claude-opus-4-7"},
        "evaluations": {
            "gemini": {
                "model": "gemini-2.5-pro",
                "scores": {"topic_fit": 10, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 8.4,
                "one_line_verdict": "후함.", "strengths": [], "weaknesses": [],
            },
            "gpt": {
                "model": "gpt-5",
                "scores": {"topic_fit": 7, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 7.8,
                "one_line_verdict": "보통.", "strengths": [], "weaknesses": [],
            },
            "claude": {
                "model": "claude-opus-4-7",
                "scores": {"topic_fit": 7, "content_quality": 8, "interactivity": 8,
                           "tone_authenticity": 8, "timeliness_trust": 8},
                "overall_score": 7.8,
                "one_line_verdict": "보통.", "strengths": [], "weaknesses": [],
            },
        },
        "aggregate": {
            # mean(10,7,7)=8.0, |10-8|=2.0; |7-8|=1.0
            # 작은 stdev (e.g. 1.0) 을 주입하면 1.5σ=1.5, |10-8|=2.0 > 1.5 → gemini outlier
            "mean_scores": {"topic_fit": 8.0, "content_quality": 8.0,
                            "interactivity": 8.0, "tone_authenticity": 8.0,
                            "timeliness_trust": 8.0},
            "stdev_scores": {"topic_fit": 1.0, "content_quality": 0.0,
                             "interactivity": 0.0, "tone_authenticity": 0.0,
                             "timeliness_trust": 0.0},
            "weighted_total": 80.0,
            "outliers": [],
        },
    }


def _low_consensus_payload() -> dict:
    """max stdev >= 2.0 → low consensus."""
    p = _high_consensus_payload()
    p["aggregate"]["stdev_scores"] = {
        "topic_fit": 0.5, "content_quality": 1.2, "interactivity": 2.3,
        "tone_authenticity": 0.5, "timeliness_trust": 0.5,
    }
    return p


@pytest.fixture
def client_with_run(tmp_path, monkeypatch):
    """tmp_path 에 run_dir 하나 생성 + RUNS_DIR monkeypatch."""
    sid = "2026-06-04T10-00-00_testjudge"
    rd = tmp_path / sid
    _write_judge_panel(rd, _high_consensus_payload())
    # final_output.html 도 1건 작성
    (rd / "final_output.html").write_text("<!DOCTYPE html><html><body>x</body></html>",
                                          encoding="utf-8")

    from backend.api.utils import trace_loader as tl
    monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)

    client = TestClient(create_app())
    return client, sid, tmp_path


class TestJudgeEndpoint:
    def test_1_get_judge_200_with_3_evaluations(self, client_with_run):
        client, sid, _ = client_with_run
        r = client.get(f"/api/runs/{sid}/judge")
        assert r.status_code == 200
        body = r.json()
        assert body["run_id"] == sid
        assert len(body["evaluations"]) == 3
        ids = [e["model_id"] for e in body["evaluations"]]
        assert ids == ["gemini", "gpt", "claude"]
        # 5축 스키마 확인
        for ev in body["evaluations"]:
            for axis in ("topic_fit", "content_quality", "interactivity",
                         "tone_authenticity", "timeliness_trust"):
                assert axis in ev["scores"]
        assert "consensus_level" in body
        assert "aggregate_overall" in body

    def test_2_get_judge_404_when_missing(self, client_with_run):
        client, _, _ = client_with_run
        r = client.get("/api/runs/does-not-exist/judge")
        assert r.status_code == 404

    def test_3_outlier_detection(self, tmp_path, monkeypatch):
        sid = "2026-06-04T10-01-00_outlier"
        _write_judge_panel(tmp_path / sid, _outlier_payload())
        from backend.api.utils import trace_loader as tl
        monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)
        client = TestClient(create_app())
        r = client.get(f"/api/runs/{sid}/judge")
        assert r.status_code == 200
        body = r.json()
        by_id = {e["model_id"]: e for e in body["evaluations"]}
        # gemini topic_fit=10, mean=8, stdev=1.0 → |10-8|=2 > 1.5*1.0=1.5 → outlier
        assert by_id["gemini"]["is_outlier"] is True
        # gpt, claude: topic_fit=7, |7-8|=1 < 1.5 → not outlier
        assert by_id["gpt"]["is_outlier"] is False
        assert by_id["claude"]["is_outlier"] is False

    def test_4_consensus_level_boundaries(self, tmp_path, monkeypatch):
        from backend.api.utils import trace_loader as tl
        monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)
        # high (all stdev = 0)
        sid_h = "2026-06-04T10-02-00_high"
        _write_judge_panel(tmp_path / sid_h, _high_consensus_payload())
        # low (max stdev = 2.3)
        sid_l = "2026-06-04T10-02-30_low"
        _write_judge_panel(tmp_path / sid_l, _low_consensus_payload())

        client = TestClient(create_app())
        rh = client.get(f"/api/runs/{sid_h}/judge").json()
        rl = client.get(f"/api/runs/{sid_l}/judge").json()
        assert rh["consensus_level"] == "high"
        assert rl["consensus_level"] == "low"

    def test_5_final_html_meta_available(self, client_with_run):
        client, sid, _ = client_with_run
        r = client.get(f"/api/runs/{sid}/final-html")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        assert body["url"] == f"/runs/{sid}/final_output.html"
        assert body["size_bytes"] > 0
