"""Agent 베이스 클래스.

각 에이전트는 다음 세 가지로 정의됩니다:
1. 이름 (name)
2. 사용 모델 (model_alias — config/agents.yaml 의 별칭)
3. system prompt 파일 경로 (backend/agents/prompts/*.md)

system prompt 를 markdown 파일에서 읽어오므로, 코드 수정 없이 텍스트
편집만으로 에이전트의 페르소나를 튜닝할 수 있습니다.

또한 `{{KEY_NAME}}` 형식의 placeholder 는 `PromptLoader` 가
`backend/config/agent_resources.json` 매핑에 따라 자동 주입합니다.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.llm_clients import LLMResponse, call_llm

logger = logging.getLogger(__name__)


# =====================================================================
# PromptLoader
# =====================================================================
class PromptLoader:
    """prompt 마크다운 파일을 로드하고 ``{{KEY_NAME}}`` placeholder 를
    config 기반으로 주입한다.

    placeholder 이름은 대문자/숫자/언더스코어만 매칭 (`[A-Z][A-Z0-9_]*`).
    한글 placeholder (예: ``{{질문}}``) 나 dotted 표기 (예: ``{{left.label}}``)
    는 매칭되지 않으므로 영향받지 않는다. → 인터랙티브 템플릿 안전.

    매핑 정의: ``backend/config/agent_resources.json``
        {
          "TONE_REFERENCE": {
            "source_type": "file",
            "path": "docs/samples/content_voice_examples.md"
          }
        }

    파일·JSON 오류는 모두 경고 로그 + 빈 매핑으로 graceful degradation.
    매핑에 없는 placeholder 는 그대로 보존된다.
    """

    PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

    def __init__(
        self,
        prompts_dir: str | Path | None = None,
        resources_config_path: str | Path | None = None,
    ):
        # 늦은 import 로 순환 의존 회피.
        from backend.core.settings import PROJECT_ROOT

        self._project_root = PROJECT_ROOT
        self.prompts_dir = (
            Path(prompts_dir)
            if prompts_dir is not None
            else PROJECT_ROOT / "backend" / "agents" / "prompts"
        )
        self.resources_config_path = (
            Path(resources_config_path)
            if resources_config_path is not None
            else PROJECT_ROOT / "backend" / "config" / "agent_resources.json"
        )
        self._resource_map: dict[str, str] = {}
        self._load_resource_map()

    def _load_resource_map(self) -> None:
        """``agent_resources.json`` 을 읽어 placeholder → 실제 콘텐츠 매핑 구축."""
        if not self.resources_config_path.exists():
            logger.warning(
                "agent_resources.json 을 찾을 수 없습니다 (placeholder 치환 비활성): %s",
                self.resources_config_path,
            )
            return

        try:
            with open(self.resources_config_path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("agent_resources.json 파싱 실패 (%s): %s", e, self.resources_config_path)
            return

        for key, entry in config.items():
            if key.startswith("_"):
                # _comment, _last_updated 같은 메타데이터는 무시.
                continue
            if not isinstance(entry, dict):
                logger.warning("agent_resources.json: '%s' 값이 dict 가 아닙니다 (무시)", key)
                continue

            source_type = entry.get("source_type")
            if source_type == "file":
                rel = entry.get("path", "")
                fp = Path(rel)
                if not fp.is_absolute():
                    fp = self._project_root / rel
                if not fp.exists():
                    logger.warning(
                        "resource 파일 없음 (key=%s, path=%s): 빈 문자열로 매핑", key, fp,
                    )
                    self._resource_map[key] = ""
                else:
                    self._resource_map[key] = fp.read_text(encoding="utf-8")
            elif source_type == "inline":
                self._resource_map[key] = str(entry.get("value", ""))
            else:
                logger.warning(
                    "알 수 없는 source_type (key=%s, source_type=%r): 무시",
                    key, source_type,
                )

    def load(self, prompt_filename: str) -> str:
        """prompt 파일 로드 후 placeholder 치환된 문자열 반환."""
        prompt_path = self.prompts_dir / prompt_filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"prompt 파일을 찾을 수 없습니다: {prompt_path}")
        text = prompt_path.read_text(encoding="utf-8")
        return self.substitute(text)

    def substitute(self, text: str, extra_vars: dict[str, str] | None = None) -> str:
        """임의 텍스트에 placeholder 치환 수행.

        Args:
            text: 치환 대상 텍스트.
            extra_vars: 런타임 추가 변수. resource_map 보다 우선한다.

        Returns:
            치환된 텍스트. 매핑에 없는 placeholder 는 원본 그대로 유지.
        """
        merged: dict[str, str] = dict(self._resource_map)
        if extra_vars:
            merged.update(extra_vars)

        def _repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key in merged:
                logger.debug("placeholder 치환: %s (%d chars)", key, len(merged[key]))
                return merged[key]
            return m.group(0)

        return self.PLACEHOLDER_PATTERN.sub(_repl, text)


# =====================================================================
# WhitelistedSubstitutor
# =====================================================================
class WhitelistedSubstitutor:
    """Format Architect 의 ``placeholder_locations`` 화이트리스트 기반 HTML 치환.

    묶음 1 §6 결정사항:
      - ``placeholder_locations`` 에 명시된 항목만 치환
      - ``render_zone == "outside_comment"`` 인 항목만 치환
      - HTML 주석 ``<!-- ... -->`` 내부의 ``{{VAR}}`` 는 절대 치환 금지
      - 그 외 ``{{VAR}}`` 패턴은 모두 보존
    """

    COMMENT_PATTERN = re.compile(r"<!--[\s\S]*?-->")
    COMMENT_MARKER_TPL = "\x00AIDEN_HTML_COMMENT_{}\x00"
    PLACEHOLDER_SCAN_PATTERN = re.compile(r"\{\{([^}\n]+?)\}\}")

    def substitute(
        self,
        html: str,
        placeholder_locations: list[dict[str, Any]],
        values: dict[str, str],
    ) -> tuple[str, list[str], list[str]]:
        """화이트리스트 기반 치환.

        Args:
            html: 원본 HTML.
            placeholder_locations: Format Architect 출력의 placeholder_locations 배열.
                각 항목은 ``name``, ``location``, ``render_zone`` 키를 가짐.
            values: ``{name: 치환값}`` 매핑.

        Returns:
            (치환된 html, 실제 치환된 name 리스트, 보존된 name 리스트)
            - 치환된: 원본에 ``{{name}}`` 이 있어 실제로 바꾼 항목.
            - 보존된: 최종 html 에 ``{{...}}`` 형태로 남아있는 모든 이름 (주석 내부 포함).
        """
        stripped, comments = self._strip_comments(html)

        substituted: list[str] = []
        for loc in placeholder_locations:
            name = loc.get("name")
            if not name:
                continue
            if loc.get("render_zone") != "outside_comment":
                continue
            if name not in values:
                continue
            marker = "{{" + name + "}}"
            if marker in stripped:
                stripped = stripped.replace(marker, str(values[name]))
                substituted.append(name)

        final_html = self._restore_comments(stripped, comments)
        preserved = sorted(
            {m.group(1).strip() for m in self.PLACEHOLDER_SCAN_PATTERN.finditer(final_html)}
        )
        return final_html, substituted, preserved

    @classmethod
    def _strip_comments(cls, html: str) -> tuple[str, list[str]]:
        """HTML 주석을 안전한 마커로 치환하고 (치환된 html, 주석 목록) 반환."""
        comments: list[str] = []

        def _repl(m: re.Match[str]) -> str:
            idx = len(comments)
            comments.append(m.group(0))
            return cls.COMMENT_MARKER_TPL.format(idx)

        new_html = cls.COMMENT_PATTERN.sub(_repl, html)
        return new_html, comments

    @classmethod
    def _restore_comments(cls, html: str, comments: list[str]) -> str:
        """주석 마커를 원본 주석으로 복원."""
        for i, c in enumerate(comments):
            html = html.replace(cls.COMMENT_MARKER_TPL.format(i), c)
        return html


@dataclass
class AgentRunLog:
    """Agent.run() 호출 1회분의 로그."""

    agent_name: str
    timestamp: str
    input_data: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int
    model_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    raw_content: str = ""


class Agent:
    """모든 에이전트의 베이스.

    Args:
        name: 에이전트 이름 (예: "Trend Scout").
        model_alias: config/agents.yaml 의 models 섹션 키.
        prompt_file_path: system prompt 가 담긴 .md 파일 경로.
        grounding: True 면 web grounding 활성화 (Gemini 만 지원).
    """

    def __init__(
        self,
        name: str,
        model_alias: str,
        prompt_file_path: str | Path,
        grounding: bool = False,
        prompt_loader: PromptLoader | None = None,
    ):
        self.name = name
        self.model_alias = model_alias
        self.prompt_file_path = Path(prompt_file_path)
        self.grounding = grounding
        # placeholder 주입 담당. 명시되지 않으면 기본 PromptLoader 를 1회 생성.
        self._prompt_loader = prompt_loader or PromptLoader()
        self.logs: list[AgentRunLog] = []

        # system prompt 는 인스턴스 생성 시 한 번만 로드
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # System prompt 로딩
    # ------------------------------------------------------------------
    def _load_system_prompt(self) -> str:
        if not self.prompt_file_path.exists():
            raise FileNotFoundError(
                f"[{self.name}] system prompt 파일을 찾을 수 없습니다: "
                f"{self.prompt_file_path}"
            )
        text = self.prompt_file_path.read_text(encoding="utf-8")
        # {{KEY_NAME}} placeholder 치환 (매핑 없으면 원본 보존).
        return self._prompt_loader.substitute(text)

    def reload_prompt(self) -> None:
        """system prompt 파일을 다시 읽어 갱신합니다 (런타임 튜닝용)."""
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # 실행
    # ------------------------------------------------------------------
    def run(
        self,
        input_data: dict[str, Any],
        *,
        run_id: str | None = None,
        max_json_retries: int = 2,
    ) -> dict[str, Any]:
        """에이전트 실행.

        input_data 를 JSON 으로 직렬화해서 user prompt 로 전달합니다.
        응답이 JSON 파싱에 실패하면 max_json_retries 만큼 재시도합니다.

        Args:
            input_data: 에이전트에 넘길 데이터 (JSON 직렬화 가능해야 함).
            run_id: 단일 Topic Newsroom 실행 식별자. CostTracker 가 이 값으로
                run 단위 비용/호출수 한도를 검사합니다.
            max_json_retries: JSON 파싱 실패 시 재시도 횟수.

        Returns:
            파싱된 dict 응답.
        """
        user_prompt = self._build_user_prompt(input_data)
        start = time.monotonic()

        last_response: LLMResponse | None = None
        for attempt in range(max_json_retries + 1):
            response = call_llm(
                prompt=user_prompt,
                model_alias=self.model_alias,
                system_instruction=self._system_prompt,
                grounding=self.grounding,
                run_id=run_id,
            )
            last_response = response

            if response.parsed is not None:
                output = response.parsed
                break

            logger.warning(
                "[%s] JSON 파싱 실패 (attempt %d/%d). raw content head: %s",
                self.name, attempt + 1, max_json_retries + 1,
                response.content[:200],
            )
            # 다음 시도에선 좀 더 강한 지시를 덧붙임
            user_prompt = (
                self._build_user_prompt(input_data)
                + "\n\n[중요] 직전 응답이 유효한 JSON 이 아니었습니다. "
                "코드블록/설명/마크다운 없이 **순수 JSON 객체 하나만** 반환하세요."
            )
        else:
            raise RuntimeError(
                f"[{self.name}] 응답을 JSON 으로 파싱할 수 없습니다 "
                f"({max_json_retries + 1}회 시도). "
                f"raw content head: {(last_response.content if last_response else '')[:300]}"
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        assert last_response is not None
        log_entry = AgentRunLog(
            agent_name=self.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_data=input_data,
            output=output,
            duration_ms=duration_ms,
            model_id=last_response.model_id,
            tokens_in=last_response.prompt_tokens,
            tokens_out=last_response.completion_tokens,
            cost_usd=last_response.estimated_cost_usd,
            raw_content=last_response.content,
        )
        self.logs.append(log_entry)
        logger.info(
            "[%s] 실행 완료 — %dms, $%.4f",
            self.name, duration_ms, last_response.estimated_cost_usd,
        )
        return output

    def _build_user_prompt(self, input_data: dict[str, Any]) -> str:
        """input_data 를 보기 좋은 JSON 문자열로 직렬화."""
        return json.dumps(input_data, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 디버그/관찰용
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"Agent(name={self.name!r}, model_alias={self.model_alias!r}, "
            f"grounding={self.grounding})"
        )
