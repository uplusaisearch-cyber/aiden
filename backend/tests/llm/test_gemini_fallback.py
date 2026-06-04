"""GeminiClient 503/429 폴백 + exponential backoff 테스트.

실제 google-genai API 는 호출하지 않음 (Client 와 _invoke 를 mock).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.llm import gemini_client as gc_mod
from backend.llm.gemini_client import (
    GeminiClient,
    GeminiEmptyResponseError,
    _is_retryable_error,
)


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """backoff sleep 을 no-op 으로 만들어 테스트 속도 확보."""
    monkeypatch.setattr(gc_mod.time, "sleep", lambda _s: None)


@pytest.fixture
def _api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-fake")


def _make_client(_api_key, models: list[str] | None = None) -> GeminiClient:
    """genai.Client 를 MagicMock 으로 대체한 채 GeminiClient 생성."""
    with patch.object(gc_mod, "genai") as mock_genai, patch.object(gc_mod, "types") as mock_types:
        mock_genai.Client.return_value = MagicMock()
        # types.Tool / types.GoogleSearch / types.GenerateContentConfig 호출 안전 처리
        mock_types.Tool.return_value = MagicMock()
        mock_types.GoogleSearch.return_value = MagicMock()
        mock_types.GenerateContentConfig.return_value = MagicMock()
        c = GeminiClient(models=models) if models else GeminiClient()
        return c


def test_is_retryable_503(monkeypatch):
    assert _is_retryable_error(Exception("503 UNAVAILABLE: model overloaded"))
    assert _is_retryable_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert _is_retryable_error(Exception("500 INTERNAL error"))


def test_is_retryable_4xx_not_retried():
    assert not _is_retryable_error(Exception("400 INVALID_ARGUMENT: bad request"))
    assert not _is_retryable_error(Exception("401 UNAUTHENTICATED"))
    assert not _is_retryable_error(Exception("404 NOT_FOUND: model gone"))


def test_fallback_chain_primary_succeeds_no_fallback(_api_key):
    """primary 가 첫 시도에 성공하면 fallback 모델은 건드리지 않음."""
    client = _make_client(_api_key, models=["model-A", "model-B"])
    # _invoke 가 정상 응답 반환하도록 패치
    resp = MagicMock()
    resp.text = '{"ok": true}'
    with patch.object(client, "_invoke", return_value=resp) as mock_invoke:
        result = client.call(system_prompt="sys", user_input={"x": 1})
    assert result == {"ok": True}
    assert mock_invoke.call_count == 1
    assert client.last_used_model == "model-A"
    # primary 만 호출
    called_models = [kw["model_name"] for _a, kw in mock_invoke.call_args_list]
    assert called_models == ["model-A"]


def test_fallback_chain_503_exhausts_primary_then_secondary_succeeds(_api_key):
    """primary 가 503 으로 max_retries 소진 → secondary 가 성공."""
    client = _make_client(_api_key, models=["model-A", "model-B"])
    resp_ok = MagicMock()
    resp_ok.text = '{"ok": true}'

    call_log: list[str] = []

    def _fake_invoke(*, model_name, **_kw):
        call_log.append(model_name)
        if model_name == "model-A":
            raise Exception("503 UNAVAILABLE: overloaded")
        return resp_ok

    with patch.object(client, "_invoke", side_effect=_fake_invoke):
        result = client.call(system_prompt="sys", user_input={"x": 1})

    assert result == {"ok": True}
    assert client.last_used_model == "model-B"
    # primary 3회 + secondary 1회 = 4
    assert call_log == ["model-A", "model-A", "model-A", "model-B"]


def test_fallback_all_models_503_raises(_api_key):
    """모든 모델 / 모든 attempt 503 시 마지막 예외 raise."""
    client = _make_client(_api_key, models=["model-A", "model-B"])

    def _always_503(*, model_name, **_kw):
        raise Exception(f"503 UNAVAILABLE on {model_name}")

    with patch.object(client, "_invoke", side_effect=_always_503):
        with pytest.raises(Exception, match="503"):
            client.call(system_prompt="sys", user_input={"x": 1})


def test_non_retryable_400_immediate_failure(_api_key):
    """400 INVALID_ARGUMENT 는 재시도/폴백 없이 즉시 raise."""
    client = _make_client(_api_key, models=["model-A", "model-B"])

    call_log: list[str] = []

    def _bad_request(*, model_name, **_kw):
        call_log.append(model_name)
        raise Exception("400 INVALID_ARGUMENT: bad prompt")

    with patch.object(client, "_invoke", side_effect=_bad_request):
        with pytest.raises(Exception, match="400"):
            client.call(system_prompt="sys", user_input={"x": 1})

    # 단 1회만 호출 (재시도 X, 폴백 X)
    assert call_log == ["model-A"]


def test_env_var_chain_parsing(_api_key, monkeypatch):
    """AIDEN_GEMINI_MODELS=a,b,c 환경변수가 모델 체인으로 파싱됨."""
    monkeypatch.setenv("AIDEN_GEMINI_MODELS", "alpha-model, beta-model , gamma-model")
    with patch.object(gc_mod, "genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        c = GeminiClient()
    assert c.models == ["alpha-model", "beta-model", "gamma-model"]
    assert c.model_name == "alpha-model"


def test_env_var_single_model_disables_fallback(_api_key, monkeypatch):
    """단일 모델만 지정 시 폴백 없이 그 모델로만 재시도."""
    monkeypatch.setenv("AIDEN_GEMINI_MODELS", "only-model")
    with patch.object(gc_mod, "genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        c = GeminiClient()
    assert c.models == ["only-model"]


def test_grounding_downgraded_on_unsupported_model(_api_key, monkeypatch):
    """Grounding 미지원 모델로 폴백 시 use_grounding 자동 비활성화."""
    # gemini-2.5-flash-lite 는 _NO_GROUNDING_MODELS 에 포함됨
    client = _make_client(_api_key, models=["gemini-2.5-flash", "gemini-2.5-flash-lite"])
    resp_ok = MagicMock()
    resp_ok.text = '{"ok": true}'

    grounding_seen: list[bool] = []

    def _capture(*, model_name, use_grounding, **_kw):
        grounding_seen.append(use_grounding)
        if model_name == "gemini-2.5-flash":
            raise Exception("503 UNAVAILABLE")
        return resp_ok

    with patch.object(client, "_invoke", side_effect=_capture):
        result = client.call(system_prompt="sys", user_input={"x": 1}, use_grounding=True)

    assert result == {"ok": True}
    # primary 시도: grounding True
    # lite 폴백 시: grounding False 로 강등
    assert grounding_seen[0] is True
    assert grounding_seen[-1] is False


def test_json_parse_failure_not_retried(_api_key):
    """LLM 이 응답은 했지만 JSON 파싱 실패 시 즉시 raise (재시도 X)."""
    client = _make_client(_api_key, models=["model-A", "model-B"])
    bad_resp = MagicMock()
    bad_resp.text = "not json at all"
    bad_resp.candidates = []

    call_count = 0

    def _bad_json(*_a, **_kw):
        nonlocal call_count
        call_count += 1
        return bad_resp

    with patch.object(client, "_invoke", side_effect=_bad_json):
        with pytest.raises(ValueError, match="Failed to parse"):
            client.call(system_prompt="sys", user_input={"x": 1})

    assert call_count == 1  # 재시도/폴백 X


def test_empty_response_triggers_retry_and_fallback(_api_key):
    """response.candidates[0].content == None 케이스 (safety 차단 / 빈 응답) 가
    GeminiEmptyResponseError 로 raise 되어 다음 모델로 폴백된다."""
    client = _make_client(_api_key, models=["model-A", "model-B"])

    # primary: response.text 없음 + candidates[0].content == None (safety 차단 패턴)
    empty_cand = MagicMock()
    empty_cand.content = None
    empty_cand.finish_reason = "SAFETY"
    empty_resp = MagicMock()
    empty_resp.text = None
    empty_resp.candidates = [empty_cand]
    empty_resp.prompt_feedback = None

    # secondary: 정상 응답
    ok_resp = MagicMock()
    ok_resp.text = '{"ok": true}'

    call_log: list[str] = []

    def _fake(*, model_name, **_kw):
        call_log.append(model_name)
        return empty_resp if model_name == "model-A" else ok_resp

    with patch.object(client, "_invoke", side_effect=_fake):
        result = client.call(system_prompt="sys", user_input={"x": 1})

    assert result == {"ok": True}
    assert client.last_used_model == "model-B"
    # primary 3회 (모두 empty) + secondary 1회 (성공)
    assert call_log == ["model-A", "model-A", "model-A", "model-B"]


def test_extract_text_empty_response_includes_finish_reason():
    """_extract_text 가 빈 응답을 GeminiEmptyResponseError 로 raise 하며,
    finish_reason / block_reason 진단 정보를 메시지에 포함해야 한다."""
    cand = MagicMock()
    cand.content = None
    cand.finish_reason = "SAFETY"
    feedback = MagicMock()
    feedback.block_reason = "OTHER"
    resp = MagicMock()
    resp.text = None
    resp.candidates = [cand]
    resp.prompt_feedback = feedback

    with pytest.raises(GeminiEmptyResponseError) as exc_info:
        GeminiClient._extract_text(resp)
    msg = str(exc_info.value)
    assert "SAFETY" in msg
    assert "OTHER" in msg
    assert _is_retryable_error(exc_info.value) is True
