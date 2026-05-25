# P2 R3: Fact-Checker iter3 verification_log 누락 수정

- **ID**: P2-R3
- **우선순위**: P0
- **영향 범위**: `prompts/05_fact_checker.md` (단일 파일)
- **방식**: 옵션 C (FC.md만 수정, writer.md는 손대지 않음)

---

## 배경

묶음 2 E2E 2회 결과 `fact_checker iter3` 에서 `verification_log: []` 누락 패턴 재발.

### 패턴 A — FC 자체 버그 (run 1, 가족 식비)
- writer가 fact_claims 5개 정상 생성, FC가 grounding 호출도 수행 (iter2와 다른 출처 도메인 확인됨)
- `annotated_draft.fact_claims[].status = "verified"` 채움, 본문 `[출처:]` 마커도 삽입
- **`verification_log`만 빈 배열**
- iter2에선 정상, iter3에서만 누락
- 원인: 두 sibling 필드 (`verification_log` vs `annotated_draft.fact_claims[].status`) 관계가 프롬프트에 미정의 → 모델이 중복 회피로 한쪽 누락

### 패턴 B — 입력단 부재 (run 2, 편의점 디저트)
- writer iter3가 editor "트렌드 문구 삭제" 지시 반영하며 fact_claims를 모두 `[]`로 비움
- FC가 빈 fact_claims인데도 `confidence_score = 10` 부여 → 검증 안 된 글이 final 진입
- 원인: FC.md에 "빈 fact_claims 처리 규칙" 없음

본 패치는 FC.md 단일 파일만 수정. writer.md 변경 및 빈 fact_claims 사전 차단은 별도 이슈 **#W-fc-empty** 로 분리.

---

## 변경 대상

- **파일**: `prompts/05_fact_checker.md`
- **EOL**: LF (.gitattributes 준수)
- **commit**: 변경 후 사용자가 직접 `git add` & `git commit`. **자동 commit 금지**.

---

## 변경 내용

### 1. `## 검증 절차` 섹션 — step 6 추가

step 5 다음에 아래 항목 추가:

```markdown
6. **출력 직전 self-check (반드시 수행)**:
   - `len(verification_log)` == `sum(len(s.fact_claims) for s in input.sections)` 확인
   - 한쪽이라도 비어 있으면 누락 → 다시 채워서 출력
   - `annotated_draft.fact_claims[].status`만 채우고 `verification_log`를 비우는 것은 **명백한 오류**
```

### 2. `## 출력 형식` 섹션 — JSON 위에 필드 관계 명시

기존 `## 출력 형식 (반드시 이 JSON 그대로)` 줄 바로 다음, ` ```json ` 블록 시작 전에 삽입:

```markdown
**두 필드 관계**:
- `verification_log`: ground truth. 각 claim마다 evidence + source_url + source_date까지 기록. **빈 배열 불가** (단, 입력 fact_claims가 전부 비어있을 때만 빈 배열 허용 — 아래 규칙 참조)
- `annotated_draft.sections[].fact_claims[]`: 위 verification_log의 거울. claim과 status만 요약 표시
- 두 배열의 entry 수는 반드시 일치해야 함
```

### 3. `## 규칙` 섹션 — 마지막 항목 뒤에 추가

기존 마지막 줄 `- 본인 추측으로 사실 단정 금지. Grounding 결과만 신뢰.` 뒤에 추가:

```markdown
- **빈 fact_claims 처리**: 입력의 모든 섹션 `fact_claims`가 빈 배열일 때:
  - `verification_log`: 빈 배열로 둘 것
  - `confidence_score`: **1**로 고정 (검증할 사실 자체가 없는 글은 신뢰 불가)
  - `summary`: "본문에 검증 가능한 사실 주장이 없어 신뢰도 평가 불가. Writer 재작성 권장." 명시
  - iter < 3 인 경우 Editor가 재트리거 가능. iter == 3 인 경우 final 진입하나 본 score 1이 후속 Judge Panel 평가에 반영됨
```

---

## 검증 방법

### Step 1. 변경 적용
- 위 3개 수정사항을 `prompts/05_fact_checker.md` 에 반영
- LF EOL 유지 확인

### Step 2. E2E 재실행 (2회, 묶음 3 우선순위 2와 병합 가능)
- run A: 카테고리 "맛집" (가족 식비 시나리오 재현)
- run B: 다른 카테고리 1개 ("안전" 또는 "AI트렌드")

### Step 3. trace 검증 — `traces/<session>/05_fact_checker_iter3.json`

| 체크 항목 | 통과 기준 |
|---|---|
| verification_log 길이 | `sum(len(s.fact_claims))` 와 일치 |
| entry 필드 완전성 | 각 entry에 evidence, source_url, source_date 모두 채워짐 |
| 거울 일치 | `annotated_draft.sections[].fact_claims[].status` == `verification_log[i].status` |
| 빈 케이스 처리 | 빈 fact_claims라면 confidence_score == 1, summary에 경고 문구 포함 |

### Step 4. 통과 기준
- 4개 체크 모두 OK
- 1회 실패 시 패치 재검토. 2회 모두 실패 시 본 패치 롤백 후 재진단

---

## 롤백

```bash
git checkout HEAD -- prompts/05_fact_checker.md
```

단일 파일 수정이므로 영향 격리됨.

---

## Claude Code 실행 지시

1. `prompts/05_fact_checker.md` 파일 열기
2. 위 "변경 내용" 의 3개 섹션 수정사항을 순서대로 적용
3. 파일 저장 (LF EOL 유지)
4. **`git add` 및 `git commit` 자동 실행 금지**. 변경 완료만 보고
5. 사용자가 직접 diff 확인 후 commit

---

## 별도 이슈로 분리

**#W-fc-empty**: writer iter3에서 editor 지시 반영 시 fact_claims가 빈 배열로 떨어지는 케이스
- 카테고리별 정책 결정 필요 (감각 묘사 중심 콘텐츠는 fact_claims 없는 게 자연스러움)
- 묶음 3 이후 또는 마감 후 별도 검토
