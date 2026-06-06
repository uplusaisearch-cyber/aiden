# 패치: 위젯 풀 확대(TAB_SWITCHER + FLIP_CARD) + 매칭교정

작성일: 2026-06-06 (Phase 0 진단 반영 v3 — 최종)
대상: Format Architect(08) · HTML Builder(09) · 카탈로그
분류: 폴리싱 (P1, 마감 6/8). 목적은 데모·발표 위젯 다양성.

---

## 0. 진단 결과 (Phase 0, runs/ 43세션)

- CHECKLIST 23건 중 **진짜 체크리스트형 73.9%(17건)** = 08이 맞게 고름. "편향" 거의 허상.
- mismatch 26.1%(6건): **4건이 AI트렌드 "도구/분야 N종 소개"** = 카탈로그형 본문인데 매칭 위젯 부재 → CHECKLIST 흡수. 2건은 A 적합(C 과채택), 1건 혼합.
- CHECKLIST만 fit이 generic("X 하기") → 다른 4종이 다 unfit일 때 유일한 fallback.
- COMPARE_SLIDER 0건: 1차 원인 본문 공급 부재(Editor가 비교축 본문 거의 미생성), 2차 정의/트리거 부실.

**판정**: 순수 매칭 편향은 거의 0. 진짜 레버는 **TAB_SWITCHER 신설**(mismatch 4건 직격). FLIP_CARD는 과거 mismatch 0건이나 데모 다양성용으로 추가(사용자 결정).

---

## 1. 목표

데모·발표 다중 시연 시 위젯 다양성 확보. 구체:
- TAB_SWITCHER 신설 → 카탈로그형 본문이 CHECKLIST 대신 TAB으로 자연 이동 (매칭교정의 본체)
- FLIP_CARD 신설 → 풀 확대 (데모 토픽 통제로 노출)
- COMPARE_SLIDER 제외 → dead 정리
- CHECKLIST 직접 좁히기 ❌ (진짜 체크리스트형 73.9% 보존)

---

## 2. 작업 단위

### A. TAB_SWITCHER 신설
- 08 엔트리 + `fit_signals`: "도구/분야/대상 N종 카탈로그형 나열", "유형별 안내", "페르소나 분기"
- 09 렌더 case 1개 추가 (탭 선택 시 해당 패널만 노출)

### B. FLIP_CARD 신설
- 08 엔트리 + `fit_signals`: "용어 풀이", "미신 vs 사실", "퀴즈성 정보"
- 09 렌더 case 1개 추가 (front/back + CSS rotateY flip + 탭 토글)

### C. 매칭교정 (CHECKLIST fallback 완화)
- **CHECKLIST fit 문구 직접 축소 금지.** 대신:
  - TAB 신설로 카탈로그형 흡수 경로 제공 (A가 본체)
  - CHECKLIST에 약한 단서만 추가: "단순 N종 도구/분야 나열은 TAB 우선 고려"
  - 카테고리 트리거(L165-173)에 "AI트렌드 + N종 카탈로그형 → TAB 우선" 추가
- **목표는 분산이 아니라 정확 매칭.** 진짜 준비물/단계/자가진단형은 CHECKLIST 그대로 유지.

### D. COMPARE_SLIDER 제외
- 08 정의(L79-90) + 카테고리 트리거(L165-173)에서 제거.
- 사유: 본문 공급 부재가 1차라 08 단독 수정 효과 미미. 살리려면 Writer/Editor 본문 가이드 수정 필요(범위 초과, v2).

---

## 3. 카탈로그 스키마 (신규 2종)

```yaml
- id: TAB_SWITCHER
  label_ko: "상황별 보기"
  fit_signals: ["도구/분야/대상 N종 나열", "유형별 안내", "페르소나 분기"]
  data_schema: { tabs: [{ label, body_html }] }
  avoid_when: "대상 구분 없는 단일 내용 / 항목 1개"

- id: FLIP_CARD
  label_ko: "뒤집기 카드"
  fit_signals: ["용어 풀이", "미신 vs 사실", "퀴즈성 정보"]
  data_schema: { cards: [{ front, back }] }
  avoid_when: "숨길 뒷면 내용 없음"
```

기존 4종(QUIZ/CALCULATOR/SCENARIO_SIM/CHECKLIST) 정의 형식 그대로 따름. id 명명 컨벤션 = 기존 따름(확인 필요).

---

## 4. 09 — 기존 case 무변경 / 신규 2종 case만 추가

- 기존 QUIZ/CALCULATOR/SCENARIO_SIM/CHECKLIST case **절대 무변경.**
- TAB_SWITCHER case: 탭 버튼 + 패널 토글, 선택 탭만 노출. vanilla JS.
- FLIP_CARD case: front/back 2면, CSS transform rotateY, 탭 토글. vanilla JS.
- 공통: self-contained, 외부 의존 없음, 다크 / `#ff2e98` / 모바일 터치타겟 ≥ 44px.

---

## 5. 종료 조건

- 08 카탈로그에 TAB/FLIP 추가, COMPARE_SLIDER 제거 완료.
- 09에 TAB/FLIP case 추가, 기존 4종 case diff 없음.
- E2E 회귀 run:
  - AI트렌드 "도구 N종" 토픽 → TAB_SWITCHER 선택되는지 (매칭교정 검증)
  - 미신vs사실 류 토픽 → FLIP_CARD 선택/렌더되는지
  - 진짜 준비물/자가진단 토픽 → 여전히 CHECKLIST 선택되는지 (보존 검증)
- 회귀 0.

## 6. 회귀 점검

- [ ] **진짜 체크리스트형 본문에 CHECKLIST 여전히 선택** (73.9% 보존 — 최우선)
- [ ] A 타입 정상 출력 유지 (분포 급변 없어야)
- [ ] 기존 4종 위젯 동작 정상 (09 case diff 없음 확인)
- [ ] COMPARE_SLIDER 제거가 다른 분기/파싱 깨지 않음
- [ ] `final_output.html` 저장 정상
- [ ] 다크 / `#ff2e98` / 모바일 / iframe 렌더 정상
- [ ] `personas.yaml` `gameifier` 키 영향 없음

## 7. 시각 임팩트 체크리스트

- [ ] 데모용 토픽 3종(도구N종 / 미신vs사실 / 준비물) 연속 시연 시 TAB·FLIP·CHECKLIST 각각 다르게 노출
- [ ] TAB·FLIP이 본문에 자연 부합 (이질감 없음)
- [ ] `#ff2e98` 포인트 / 모바일 터치 / iframe 렌더 정상
- [ ] 위젯 초기 affordance 명확 (탭/뒤집기 유도)

---

## 8. 확인 필요 + 안전장치 (Claude Code)

- **위젯 종류 enum/리스트가 하드코딩된 지점 전수 조사 먼저** (08 / 09 / personas.yaml / frontend).
  - **4곳 이하면 그대로 진행. 5곳 이상이면 멈추고 영향 범위 보고** (D-2 회귀 면적 과대 시 축소 판단).
- 카탈로그 포맷 yaml/json 컨벤션 확인 (기존 `planning_presets.json` 참조)
- id 명명 컨벤션 (기존 `SCENARIO_SIM` 케이스)
- COMPARE_SLIDER 제거 시 09 case·프론트 표기·파싱 enum에 잔존 참조 없는지 확인
