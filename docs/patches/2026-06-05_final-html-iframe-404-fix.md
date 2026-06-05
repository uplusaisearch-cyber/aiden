# 패치 명세: final-html iframe 404 fix (배포 환경)

## Claude Code 실행 명령

````text
docs/patches/2026-06-05_final-html-iframe-404-fix.md 를 읽고 그대로 실행해라.
핵심: final-html 메타가 주는 url 을 StaticFiles 경로(/runs/{id}/final_output.html)에서
이미 살아있는 API 핸들러(/api/runs/{id}/output)로 교체한다. 백엔드 1줄 + StaticFiles mount 제거.
종료 조건·회귀 점검 섹션 반드시 충족. git add/commit 은 하지 마라(사용자가 직접).
````

---

## 배경 / 원인 (확정됨)

배포(Railway)에서 결과물 iframe 이 `{"detail":"Not Found"}` 로 뜸.

- `frontend/components/run/FinalHtmlPreview.tsx:104` → iframe `src = ${API_BASE}${data.url}`
- `data.url` 출처 = `backend/api/routers/judges.py:35` → `f"/runs/{session_id}/final_output.html"` (StaticFiles 경로)
- 그 StaticFiles mount = `backend/api/main.py:86-88` → **`if runs_dir.exists():` 조건부 mount**
- **근본 원인**: 컨테이너 기동 시 `runs/` 디렉토리가 없으면(repo 미포함/재배포 휘발) mount 자체가 스킵됨. mount 는 기동 시점 1회만 평가되므로, 이후 generate 가 `runs/{id}/` 를 만들어도 `/runs/...` 경로는 영원히 없음 → FastAPI 기본 404 `{"detail":"Not Found"}`.
- **반면** `/api/runs/{session_id}/output` (`runs.py:90`, HTMLResponse, `load_final_html()` 으로 파일 읽어 반환) 은 mount 와 무관하게 라우터에 항상 존재 → 살아있음.

즉 프론트 메타 경로만 살아있는 핸들러로 바꾸면 mount/디렉토리 존재/휘발성 전부 우회됨.

---

## 변경 사항

### [필수] 1. judges.py — 메타 url 을 API 핸들러 경로로 교체

`backend/api/routers/judges.py` 의 `get_final_html_meta` (현재 line 33-37):

**변경 전**
```python
    return {
        "available": True,
        "url": f"/runs/{session_id}/final_output.html",
        "size_bytes": final_path.stat().st_size,
    }
```

**변경 후**
```python
    return {
        "available": True,
        "url": f"/api/runs/{session_id}/output",
        "size_bytes": final_path.stat().st_size,
    }
```

- `available`/`size_bytes` 판정 로직(`final_path.exists()`)은 그대로 둔다. 파일 존재 여부 체크는 여전히 디스크 기준이라 정확하다.
- iframe 은 `${API_BASE}${url}` 이므로 결과 `https://<railway>/api/runs/{id}/output` 로 정상 호출됨.

### [권장] 2. main.py — 더 이상 안 쓰이는 StaticFiles mount 제거

변경 1 이후 `/runs` StaticFiles 경로를 참조하는 곳이 없어진다. `backend/api/main.py:84-88` 의 다음 블록 제거:

```python
    # /runs/<id>/final_output.html 정적 노출 (iframe 미리보기용).
    # StaticFiles 는 mount 디렉터리 외부로의 path traversal 을 자체 차단.
    runs_dir = _PROJECT_ROOT / "runs"
    if runs_dir.exists():
        app.mount("/runs", StaticFiles(directory=str(runs_dir)), name="runs")
```

- 같이 안 쓰이게 되는 `from fastapi.staticfiles import StaticFiles` import(main.py:27)도 **다른 곳에서 안 쓰면** 제거. 다른 곳에서 쓰면 남겨둔다(grep 확인 후 판단).
- 제거가 부담되면 이 항목은 스킵 가능(동작에는 영향 없음, dead code 만 남음). 단 dead code 를 남길 거면 그 사실을 보고에 명시.

### [확인만] 3. 프론트 — 변경 불필요

`FinalHtmlMeta.url` 은 `string | null` (`frontend/types/judge.ts:93`) 이고 iframe 은 `${API_BASE}${url}` 로 단순 연결하므로 **프론트 코드 변경 없음**. url 값만 바뀌면 그대로 동작. 확인만 하고 손대지 말 것.

---

## 종료 조건

1. `backend/api/routers/judges.py` 의 `get_final_html_meta` 가 `url` 로 `/api/runs/{session_id}/output` 반환.
2. (권장 적용 시) `backend/api/main.py` 에서 `/runs` StaticFiles mount 블록 제거, 미사용 import 정리.
3. 백엔드 회귀 전체 PASS (기존 56건 기준). 특히:
   - `test_judge_endpoint.py` 의 final-html 메타 테스트가 새 url 값을 기대하도록 갱신됐는지 확인. 기존 테스트가 `/runs/...` 를 하드코딩 assert 하면 `/api/runs/{id}/output` 으로 수정. 테스트가 url 값 자체를 assert 하지 않으면 변경 불필요.
   - `test_runs.py` 의 `/output` 핸들러 테스트 회귀 없음 확인.
4. 로컬 `python scripts/run_api_server.py` 기동 후 `/api/runs/<기존_run_id>/final-html` 호출 시 url 이 `/api/runs/<id>/output` 으로 나오고, 그 경로 직접 호출 시 HTML 200 반환.

## 회귀 점검

- `/api/runs/{id}/output` 핸들러(runs.py:90-95) 는 **변경 없음** — 기존 동작 그대로. 이번 패치는 "그 경로를 메타가 가리키게" 할 뿐.
- `/api/runs/{id}/judge`, `/api/runs/{id}` (RunDetail) 응답 스키마 영향 없음 확인.
- `final_output_html_url` (RunDetail, runs.py:84) 은 이미 `/api/runs/{id}/output` 을 쓰고 있었음 — 이번 변경으로 final-html 메타와 경로가 **일원화**됨(부수 효과: 일관성 향상).
- StaticFiles mount 제거가 path traversal 방어를 없애는 것 아닌지 우려 → 제거해도 `/runs` 경로 자체가 사라지는 것이라 공격면이 줄어듦. `load_final_html(session_id)` 가 session_id 기반 디렉토리 접근 시 traversal 방어하는지만 확인(기존 코드라 이미 안전할 가능성 높음).

## 배포 반영

이 fix 는 백엔드 변경이므로 **Railway 자동 재배포** 대상:
```
git add backend/api/routers/judges.py backend/api/main.py
git commit -m "fix(api): final-html 메타 url 을 /api/runs/{id}/output 으로 교체 (StaticFiles mount 우회)

배포 환경에서 컨테이너 기동 시 runs/ 부재로 /runs StaticFiles mount 가
스킵돼 iframe 이 404. 이미 살아있는 HTMLResponse 핸들러로 메타 url 일원화.
미사용 StaticFiles mount 제거. 회귀 56/56 PASS."
git push
```
push → Railway 자동 재배포 → Vercel 화면에서 generate 후 결과물 iframe 정상 표시 확인.

## 작업 보고 양식

- 변경 파일 목록 + 각 변경 라인.
- 권장 2(mount 제거) 적용했는지/스킵했는지 + 미사용 import 처리 결과.
- 회귀 결과(PASS/FAIL 건수), test_judge_endpoint.py 갱신 여부.
- 로컬 검증(종료조건 4) 결과.
- git 명령은 실행하지 말고 제안 커밋 메시지만 출력.
