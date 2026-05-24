# 묶음 2 Step 2 작업 명세서 — base_agent.py 일반화

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2의 Step 2  
**범위**: base_agent.py 일반화 + config 파일 신규 + 단위 테스트  
**실행 방식**: 코드 작성 + 단위 테스트 실행

---

## 작업 개요

이번 Step의 핵심: **placeholder 주입 메커니즘 일반화**

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `backend/agents/base_agent.py` | 신규 또는 수정 |
| 2 | `backend/config/cdn_urls.json` | 신규 |
| 3 | `backend/config/agent_resources.json` | 신규 |
| 4 | `tests/test_base_agent.py` | 신규 (단위 테스트) |
| 5 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 |
| 6 | `docs/NEXT_BUNDLE_NOTES.md` | §7-1 상태 변경 |

---

## 설계 결정사항 (Step 1 검토에서 확정)

### 결정 A: CDN URL config화
- 옵션: **`backend/config/cdn_urls.json` 분리** (config-first 일관성)
- prompt에 하드코딩된 mathjs 12.4.2, swiper v11 CDN을 config로 빼지 않음 (이번 단계에서는 prompt 그대로 두고 base_agent에서 추가 주입 가능하게만 준비)
- prompt 자체 수정은 Step 3 또는 별도 패치에서 진행

### 결정 B: placeholder 일반화 구조
- 옵션: **TONE_REFERENCE + 향후 확장 가능 구조**
- `{{KEY_NAME}}` 패턴이면 미리 정의된 소스 매핑에서 자동 주입
- 매핑 정의: `backend/config/agent_resources.json`
- 미정의 placeholder는 그대로 둠 (LLM 출력에서 자체 치환되거나 후속 단계에서 처리)

---

# 작업 1: backend/agents/base_agent.py

## 1-1. 파일 위치 확인

기존 파일이 있는지 먼저 확인:
- 있으면: 기존 구조 파악 후 placeholder 주입 메커니즘 추가
- 없으면: 신규 생성

## 1-2. 핵심 기능 명세

### A. PromptLoader 클래스

prompt 파일을 읽고 placeholder를 주입한 후 최종 system prompt 문자열 반환.

```python
class PromptLoader:
    """
    prompt 마크다운 파일을 로드하고 {{KEY_NAME}} placeholder를 
    config 기반으로 주입한다.
    """
    
    def __init__(
        self,
        prompts_dir: str = "backend/agents/prompts",
        resources_config_path: str = "backend/config/agent_resources.json",
    ):
        self.prompts_dir = Path(prompts_dir)
        self.resources_config_path = Path(resources_config_path)
        self._resource_map: dict[str, str] = {}
        self._load_resource_map()
    
    def _load_resource_map(self) -> None:
        """
        agent_resources.json을 읽어 placeholder 이름 → 실제 내용 매핑 구축.
        예:
        {
          "TONE_REFERENCE": {
            "source_type": "file",
            "path": "docs/samples/content_voice_examples.md"
          }
        }
        """
        # JSON 로드 후 source_type에 따라 분기
        # - file: 해당 파일 내용을 읽어 매핑
        # - inline: 값 그대로 매핑
        # 파일 없으면 경고 후 빈 문자열로 매핑 (절대 raise 하지 않음)
        ...
    
    def load(self, prompt_filename: str) -> str:
        """
        prompt 파일 로드 후 placeholder 치환.
        
        Args:
            prompt_filename: 예 "04_writer.md"
        
        Returns:
            치환 완료된 system prompt 문자열
        """
        # 1. 파일 읽기
        # 2. {{KEY_NAME}} 패턴 매칭
        # 3. resource_map에 있으면 치환, 없으면 그대로 유지
        # 4. 치환 로그를 디버그용으로 남김 (logger.debug)
        ...
    
    def substitute(self, text: str, extra_vars: dict[str, str] | None = None) -> str:
        """
        임의 텍스트에 대해 치환 수행. 
        prompt 외에 다른 텍스트(예: HTML Builder의 placeholder_locations 화이트리스트 치환)에도 재사용 가능.
        
        Args:
            text: 치환 대상 텍스트
            extra_vars: 런타임 추가 변수 (예: 카테고리별 동적 주입)
        
        Returns:
            치환된 텍스트
        """
        ...
```

### B. WhitelistedSubstitutor 클래스

HTML Builder가 출력한 HTML에 대해 `placeholder_locations` 화이트리스트 기반으로만 치환.

```python
class WhitelistedSubstitutor:
    """
    Format Architect의 placeholder_locations에 명시된 항목만 치환.
    그 외 {{VAR}} 패턴은 보존.
    
    묶음 1 §6 결정사항: render_zone == "outside_comment" 인 것만 치환.
    """
    
    def substitute(
        self,
        html: str,
        placeholder_locations: list[dict],
        values: dict[str, str],
    ) -> tuple[str, list[str], list[str]]:
        """
        Args:
            html: 원본 HTML 문자열
            placeholder_locations: Format Architect 출력의 placeholder_locations 배열
            values: {placeholder_name: 실제 치환값} 매핑
        
        Returns:
            (치환된 html, 치환된 placeholder 이름 리스트, 보존된 placeholder 이름 리스트)
        
        규칙:
        - placeholder_locations에 없는 {{VAR}}는 치환하지 않음
        - render_zone != "outside_comment" 인 항목은 치환하지 않음
        - values에 키가 없는 항목은 치환하지 않음 (보존)
        - HTML 주석(<!-- -->) 내부의 {{VAR}}는 정규식으로 우회 (주석 영역 제외 후 치환)
        """
        ...
    
    @staticmethod
    def _strip_comments(html: str) -> tuple[str, list[tuple[int, str]]]:
        """
        주석을 임시 마커로 치환 후 (치환된 텍스트, 주석 목록) 반환.
        나중에 _restore_comments로 복원.
        """
        ...
    
    @staticmethod
    def _restore_comments(html: str, comments: list[tuple[int, str]]) -> str:
        """주석 복원"""
        ...
```

### C. BaseAgent 추상 클래스 (있으면 확장, 없으면 신규)

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    모든 에이전트의 공통 베이스.
    PromptLoader를 통해 system prompt 로드.
    """
    
    def __init__(
        self,
        prompt_filename: str,
        llm_client,  # 기존 LLM 클라이언트 (Phase 1 산출물 활용)
        prompt_loader: PromptLoader | None = None,
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.system_prompt = self.prompt_loader.load(prompt_filename)
        self.llm_client = llm_client
    
    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """각 에이전트가 구현. input → output dict 반환."""
        ...
```

## 1-3. 구현 시 주의사항

- **타입 힌트 필수** (Python 3.11+ 문법: `dict[str, str]`, `list[...]`, `tuple[...]`)
- **로깅**: `logging` 모듈 사용. `logger = logging.getLogger(__name__)`
- **에러 처리**:
  - 파일 없음: 경고 로그 + 빈 문자열 매핑 (절대 raise 안 함, 시스템 멈추면 안 됨)
  - JSON 파싱 실패: 경고 로그 + 빈 매핑
  - placeholder 치환 실패: 원본 유지 + 디버그 로그
- **인코딩**: 모든 파일 읽기/쓰기 `encoding="utf-8"` 명시
- **경로**: `pathlib.Path` 사용. 문자열 경로 직접 조작 금지
- **순환 import 방지**: BaseAgent에서 구체 에이전트 import 금지

---

# 작업 2: backend/config/cdn_urls.json 신규

config 파일 신규 생성. 추후 prompt 또는 base_agent에서 참조 가능하도록 구조화.

```json
{
  "_comment": "외부 CDN URL 모음. 보안 패치·버전 업데이트 시 이 파일만 수정.",
  "_last_updated": "2026-05-23",
  
  "mathjs": {
    "version": "12.4.2",
    "js": "https://cdnjs.cloudflare.com/ajax/libs/mathjs/12.4.2/math.min.js"
  },
  
  "swiper": {
    "version": "11",
    "js": "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js",
    "css": "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css"
  }
}
```

**비고**: 이 단계에서는 파일만 만들어두고 prompt에서 직접 참조하지는 않음 (Step 3 이후 활용).

---

# 작업 3: backend/config/agent_resources.json 신규

placeholder 이름 → 실제 콘텐츠 매핑 정의. base_agent의 PromptLoader가 로드.

```json
{
  "_comment": "Prompt 내 {{KEY_NAME}} placeholder 주입 매핑. 새 placeholder 추가 시 여기에 등록.",
  "_last_updated": "2026-05-23",
  
  "TONE_REFERENCE": {
    "source_type": "file",
    "path": "docs/samples/content_voice_examples.md",
    "used_by": ["04_writer.md"],
    "description": "콘텐츠 톤 가이드. Writer가 작성 시 참조."
  }
}
```

**확장 예시 (참고용, 본 작업에선 추가하지 말 것)**:
```
"CDN_MATHJS_JS": {
  "source_type": "json_path",
  "path": "backend/config/cdn_urls.json",
  "json_path": "mathjs.js"
}
```

이런 확장은 Step 3에서 필요 시 진행. 본 작업은 file 타입 1개로 충분.

---

# 작업 4: tests/test_base_agent.py 신규 (단위 테스트)

pytest 기반. 핵심 동작 검증.

```python
"""
base_agent.py 단위 테스트.
실제 LLM 호출 없음. placeholder 주입 + 화이트리스트 치환 로직만 검증.
"""
import pytest
from pathlib import Path
from backend.agents.base_agent import PromptLoader, WhitelistedSubstitutor


class TestPromptLoader:
    
    def test_load_simple_prompt(self, tmp_path):
        """placeholder 없는 prompt는 그대로 반환"""
        ...
    
    def test_substitute_tone_reference(self, tmp_path):
        """{{TONE_REFERENCE}} placeholder가 file 내용으로 치환됨"""
        ...
    
    def test_undefined_placeholder_preserved(self, tmp_path):
        """resource_map에 없는 {{UNKNOWN}}은 그대로 보존됨"""
        ...
    
    def test_missing_resource_file_graceful(self, tmp_path):
        """resource 파일 없으면 빈 문자열로 치환 + 경고 (raise 안 함)"""
        ...
    
    def test_extra_vars_runtime(self, tmp_path):
        """substitute 메서드에 extra_vars 전달 시 정상 치환"""
        ...


class TestWhitelistedSubstitutor:
    
    def test_whitelisted_only_substituted(self):
        """placeholder_locations에 있는 것만 치환"""
        html = '<img src="{{HERO_IMAGE_URL}}"><a href="{{CTA_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values = {"HERO_IMAGE_URL": "https://example.com/hero.jpg", "CTA_URL": "https://ignored.com"}
        
        sub = WhitelistedSubstitutor()
        result, substituted, preserved = sub.substitute(html, locations, values)
        
        assert "https://example.com/hero.jpg" in result
        assert "{{CTA_URL}}" in result  # CTA_URL은 locations에 없으므로 보존
        assert "HERO_IMAGE_URL" in substituted
        assert "CTA_URL" in preserved
    
    def test_comment_internal_preserved(self):
        """HTML 주석 내부의 {{VAR}}는 보존 (locations에 있어도)"""
        html = '<!-- {{HERO_IMAGE_URL}}: 히어로 이미지 자리 --><img src="{{HERO_IMAGE_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values = {"HERO_IMAGE_URL": "https://example.com/hero.jpg"}
        
        sub = WhitelistedSubstitutor()
        result, _, _ = sub.substitute(html, locations, values)
        
        # 주석 내부는 그대로
        assert "<!-- {{HERO_IMAGE_URL}}: 히어로 이미지 자리 -->" in result
        # 주석 외부는 치환됨
        assert 'src="https://example.com/hero.jpg"' in result
    
    def test_non_outside_comment_zone_skipped(self):
        """render_zone != outside_comment 인 항목은 치환 안 함"""
        html = '<img src="{{HERO_IMAGE_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "inside_comment"}
        ]
        values = {"HERO_IMAGE_URL": "https://example.com/hero.jpg"}
        
        sub = WhitelistedSubstitutor()
        result, substituted, preserved = sub.substitute(html, locations, values)
        
        assert "{{HERO_IMAGE_URL}}" in result  # 그대로 보존
        assert "HERO_IMAGE_URL" in preserved
        assert "HERO_IMAGE_URL" not in substituted
    
    def test_missing_value_preserved(self):
        """locations에 있어도 values에 키 없으면 보존"""
        html = '<img src="{{HERO_IMAGE_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values = {}  # 비어있음
        
        sub = WhitelistedSubstitutor()
        result, _, preserved = sub.substitute(html, locations, values)
        
        assert "{{HERO_IMAGE_URL}}" in result
        assert "HERO_IMAGE_URL" in preserved
```

## 4-1. 테스트 실행 명령

```bash
cd C:\Users\jurong\Documents\claude_team\aiden
python -m pytest tests/test_base_agent.py -v
```

모든 테스트 통과 확인 후 다음 단계 진행.

---

# 작업 5: PROGRESS.md 업데이트

## 5-1. Phase 2 체크리스트에 다음 항목 추가 (체크박스 ✅ 처리)

기존 Phase 2 체크리스트 마지막에 다음 항목 추가:

```
- [x] base_agent.py 일반화 (PromptLoader + WhitelistedSubstitutor) _(2026-05-23)_
- [x] backend/config/agent_resources.json 신규 _(2026-05-23)_
- [x] backend/config/cdn_urls.json 신규 _(2026-05-23)_
- [x] tests/test_base_agent.py 단위 테스트 _(2026-05-23)_
```

## 5-2. 진행률 갱신

- 기존: 20/46 (43.5%)
- 신규: 24/46 (52.2%)

## 5-3. 의사결정 로그 추가 (2026-05-23 자)

```
- 2026-05-23 묶음 2 Step 2 완료: base_agent.py 일반화
  - PromptLoader: {{KEY_NAME}} placeholder를 agent_resources.json 매핑에서 자동 주입. file/inline source_type 지원.
  - WhitelistedSubstitutor: Format Architect의 placeholder_locations + render_zone=outside_comment 화이트리스트 기반 치환. HTML 주석 영역은 정규식 우회로 보존.
  - 결정 A (CDN URL config화): cdn_urls.json 분리 생성 완료. prompt 직접 참조는 Step 3 또는 별도 패치에서 진행.
  - 결정 B (placeholder 일반화): TONE_REFERENCE 외 확장 가능 구조로 구현.
  - 단위 테스트 9건 통과 (PromptLoader 5건 + WhitelistedSubstitutor 4건).
```

## 5-4. NEXT_BUNDLE_NOTES.md §7-1 상태 변경

§7-1 끝에 다음 한 줄 추가:

```
> **상태 (2026-05-23)**: cdn_urls.json 분리 생성 완료. 다만 prompt에서 직접 참조는 아직 안 함 (현행 prompt에 CDN URL 하드코딩 유지). Step 3 또는 별도 패치에서 prompt 참조 방식 결정 후 적용 예정.
```

---

# 실행 후 보고 항목

1. base_agent.py 생성/수정 확인 (line count + 핵심 클래스명)
2. 2개 config json 파일 생성 확인 (line count + 첫 키)
3. 단위 테스트 실행 결과 (passed/failed 개수)
4. PROGRESS.md 진행률 20/46 → 24/46 (52.2%) 갱신 확인
5. NEXT_BUNDLE_NOTES.md §7-1 상태 라인 추가 확인
6. git status (스테이징 없음)
7. 다음 단계 안내: 묶음 2 Step 3 (오케스트레이터 3개 + data_flow_spec.md) 진입 준비 완료

---

# 주의사항

- **이번 단계는 코드 실행 있음** (pytest 실행). 단위 테스트만 실행, 실제 LLM 호출 없음.
- Phase 1 산출물(기존 LLM 클라이언트 등)이 있으면 그걸 활용. 없으면 BaseAgent 추상 클래스만 정의하고 구체 구현은 Step 3에서.
- Windows 환경 고려: 경로 구분자 forward slash 또는 pathlib.Path 사용. 백슬래시 직접 사용 금지.
- 모든 파일 UTF-8 인코딩 명시.
- 타입 힌트 필수 (Python 3.11+ 문법).
- pytest 미설치 시 `pip install pytest --break-system-packages` 로 설치.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

다음 케이스 발생 시 처리 방침:

1. **기존 base_agent.py에 다른 구조가 이미 있음**: 기존 구조 보존하면서 PromptLoader/WhitelistedSubstitutor만 추가. 기존 코드 삭제 금지.
2. **docs/samples/content_voice_examples.md 파일 부재**: 경고 로그만 남기고 빈 문자열 매핑. 테스트는 tmp_path로 가짜 파일 생성.
3. **pytest 환경 구성 안 됨**: 테스트 파일은 작성하되 실행은 생략. 보고에 "pytest 환경 미구성으로 실행 보류" 명시.
4. **순환 import 발생**: BaseAgent 추상 클래스를 별도 파일(`backend/agents/_base.py`)로 분리.
