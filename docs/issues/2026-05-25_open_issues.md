# Open Issues (AIDEN)

마감 6/9 전 처리 여부 결정 또는 마감 후 처리할 누적 이슈 목록.

**작성일**: 2026-05-25
**기준 시점**: 묶음 3 Step 1 (재현성 E2E) 완료 직후

---

## #W-fc-empty — writer가 fact_claims를 빈 배열로 만드는 케이스

- **발견**: 묶음 2 E2E run 2 (편의점 디저트 TOP5)
- **현상**: editor가 "트렌드 문구 삭제" 지시 → writer iter3가 본문 수치·고유명사 제거하며 fact_claims도 모두 `[]`로 만듦
- **위험도**: 중. P2 R3로 FC가 confidence_score=1 부여하도록 막아둠. 다만 iter3까지 갔는데 결국 final 진입은 가능
- **재현성**: 묶음 3 Step 1 (3회 E2E) 에서 자연 재현 0회. 강제 재현 안 함
- **처리 방향 후보**:
  - A. writer.md에 "본문에 검증 가능한 사실 N개 이상 포함" 강제 (감각 묘사 카테고리에선 부자연)
  - B. 카테고리별 정책 분리 (맛집·안전·AI트렌드는 강제, 디저트 리뷰 같은 감각 콘텐츠는 면제)
  - C. 현재 P2 R3 가드만으로 충분하다고 보고 close
- **우선순위**: 마감 후 검토. 현재 P2 R3 가드로 격리됨.

---

## #docs-path-mismatch — 명세서와 실제 레포 경로 불일치

- **발견**: 묶음 3 Step 1 실행 보고
- **현상**:
  - 명세서: `prompts/05_fact_checker.md`, `traces/<session>/`
  - 실제: `backend/agents/prompts/05_fact_checker.md`, `runs/<session>/agents/`
- **위험도**: 낮음. Claude Code가 실제 경로 기준으로 해석해 진행. 다만 매번 경로 보정 비용 발생
- **처리**:
  - 다음 명세서부터 실제 레포 경로 사용
  - 기존 명세서 (P2 R3, B3-S1) 는 재작성 안 함 (이미 실행 완료)
- **우선순위**: P0 (즉시 적용 — 다음 명세서 작성 시점부터)

---

## #windows-tmp-path — Claude Code 임시 파일 Windows 경로 비호환

- **발견**: 묶음 3 Step 1 실행 중
- **현상**: Claude Code가 보고용 임시 파일을 `/tmp/run_titles.txt` 로 쓰려다 `FileNotFoundError`. Windows에는 `/tmp` 없음
- **위험도**: 낮음. 본 파이프라인 결과에 영향 없음. Claude Code 부수 작업만 실패
- **처리 방향 후보**:
  - A. Claude Code 실행 시 시스템 프롬프트에 "Windows path 사용" 추가
  - B. Claude Code가 `tempfile.gettempdir()` 또는 `os.environ['TEMP']` 쓰도록 지시
- **우선순위**: 마감 후. 영향 없음.

---

## #da-iter3-regression — Devil's Advocate 점수 iter2→iter3 하락

- **발견**: 묶음 3 Step 1 Run 1 (맛집)
- **현상**: Devil's Advocate 점수 추이 3.6 → 6.2 → **5.8**. iter3 재작성이 개선되지 않고 오히려 점수 하락
- **가능한 원인**:
  - Editor 지시 품질 (모호하거나 상충하는 지시)
  - Writer가 editor 지시 반영하면서 다른 영역 품질 떨어뜨림
  - DA의 평가 기준이 iter마다 가변 (자가 일관성 문제)
- **위험도**: 중. 토론 시스템의 핵심 가정 (iteration → 품질 향상) 이 깨질 수 있음
- **추가 관찰 필요**:
  - 다른 카테고리에서도 재발하는지 (안전·AI트렌드는 iter2 수렴으로 평가 불가)
  - 묶음 3 우선순위 2 추가 E2E 시 데이터 더 모이면 패턴 확인
- **처리 방향 후보**:
  - A. DA 프롬프트에 "이전 iter 점수 대비 일관성 유지" 명시
  - B. iter3에서 점수 하락 시 iter2 결과 채택하는 백트래킹 로직
  - C. 현상 추적만 하고 마감 후 검토
- **우선순위**: 마감 전 1회 추가 데이터 수집 필요. 즉시 패치는 보류.

---

## Issue 관리 규칙

- 신규 발견 시 본 파일에 누적
- close 시 항목 삭제하지 말고 `## ✅ [closed] #...` 형식으로 변경
- 마감 후 별도 ISSUES.md 또는 GitHub Issues 로 이관 검토
