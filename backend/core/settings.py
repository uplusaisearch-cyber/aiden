"""환경변수 + YAML 설정 로더.

- .env 의 시크릿/런타임 옵션 → `Settings` (pydantic-settings)
- config/*.yaml 의 정적 설정 → `load_*_config()` 함수들

향후 AWS Secrets Manager / HashiCorp Vault 같은 외부 비밀 저장소로
이관할 때는 `Settings.from_secrets_manager()` 같은 classmethod 를
추가하면 됩니다 (현재는 .env 만 사용).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트 = 이 파일 기준 3단계 위 (backend/core/settings.py → aiden/)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CONFIG_DIR: Path = PROJECT_ROOT / "config"


class Settings(BaseSettings):
    """런타임 환경변수.

    .env 파일을 자동 로드합니다. 키가 누락되면 친절한 에러를 던집니다.
    """

    # --- API Keys ---
    gemini_api_key: str = Field(..., description="Google Gemini API 키")
    openai_api_key: str = Field("", description="OpenAI API 키 (선택)")
    anthropic_api_key: str = Field("", description="Anthropic API 키 (선택)")

    # --- 런타임 옵션 ---
    log_level: str = Field("INFO", description="로깅 레벨")
    default_llm_provider: str = Field("gemini", description="기본 LLM 제공자")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # 확장 포인트
    # ------------------------------------------------------------------
    @classmethod
    def from_secrets_manager(cls) -> "Settings":
        """미래 확장용 placeholder.

        AWS Secrets Manager / Vault 등에서 비밀을 불러와 Settings 인스턴스를
        만들 때 이 메서드를 구현하세요. 현재는 .env 만 지원합니다.
        """
        raise NotImplementedError(
            "외부 시크릿 매니저 연동은 아직 구현되지 않았습니다. "
            "현재는 .env 파일을 사용합니다."
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤 Settings 인스턴스를 반환합니다.

    누락된 환경변수가 있을 경우 사용자에게 도움이 되는 에러 메시지를 출력합니다.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        raise RuntimeError(
            "환경변수 로드에 실패했습니다.\n"
            f"  - 프로젝트 루트({PROJECT_ROOT})에 .env 파일이 있는지 확인하세요.\n"
            "  - .env.example 을 복사해서 시작하면 됩니다.\n"
            "  - 최소한 GEMINI_API_KEY 는 반드시 설정되어야 합니다.\n"
            f"원본 에러: {e}"
        ) from e


# =====================================================================
# YAML 설정 로더
# =====================================================================
def _load_yaml(path: Path) -> dict[str, Any]:
    """UTF-8 인코딩으로 YAML 파일을 읽어 dict 로 반환."""
    if not path.exists():
        raise FileNotFoundError(
            f"설정 파일을 찾을 수 없습니다: {path}\n"
            "config/ 폴더 안에 해당 파일이 있는지 확인하세요."
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_brand_config() -> dict[str, Any]:
    """config/brand.yaml 로드."""
    return _load_yaml(CONFIG_DIR / "brand.yaml")


@lru_cache(maxsize=1)
def load_platform_config() -> dict[str, Any]:
    """config/platform.yaml 로드."""
    return _load_yaml(CONFIG_DIR / "platform.yaml")


@lru_cache(maxsize=1)
def load_agents_config() -> dict[str, Any]:
    """config/agents.yaml 로드."""
    return _load_yaml(CONFIG_DIR / "agents.yaml")


@lru_cache(maxsize=1)
def load_deployment_config() -> dict[str, Any]:
    """config/deployment.yaml 로드."""
    return _load_yaml(CONFIG_DIR / "deployment.yaml")
