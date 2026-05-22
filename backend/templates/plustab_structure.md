# PlusTap HTML Structure — Builder Spec

> **이 파일은 HTML Builder 에이전트가 매 호출마다 읽는 컨텍스트입니다.**
> 사람용 풀 레퍼런스는 `docs/samples/plustab_structure.md` 를 참고하세요.
> HTML Builder 는 **이 스펙을 그대로** 따라야 하며, 클래스명 발명을 금지합니다.

---

## 0. 산출물 형태

HTML Builder 의 최종 출력은 다음 둘 중 하나의 템플릿을 **변수 치환**으로 채워 완성합니다.

- **A 타입** → `backend/templates/type_a.html`
- **B 타입** → `backend/templates/type_b.html`
- **C 타입** → A 또는 B 위에 `.plustab-interactive` 컨테이너 추가

치환 방식은 단순 `str.replace("{{VAR}}", value)` 이므로
**Jinja/Mustache 같은 루프 문법은 사용 금지**입니다.
반복이 필요한 부분(callout, swiper slide, quote)은 에이전트가 *완성된 HTML 조각* 을
변수에 넣습니다 (예: `{{CALLOUT_ITEMS}}` 에는 `<div class="callout">…</div>` 여러 개).

---

## 1. 외부 의존성

A/B 양쪽 모두 Swiper CSS 를 head 에 포함합니다. B 타입은 추가로 Swiper JS + 초기화 스크립트가 필수입니다.

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<!-- B 타입에서만 -->
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
```

---

## 2. 디자인 토큰 (모든 값은 실측치)

### Colors
| 용도 | 값 |
|---|---|
| Point (강조/CTA) | `#ff2e98` |
| Body text | `#181a1b` |
| Sub text | `#66707a` |
| Sub text 2 | `#525960` |
| Card BG | `#f9fafb` |
| Border light | `#e7ebee` |
| Border strong | `#181a1b` |
| White | `#ffffff` |
| Key visual overlay | `#090708` 60% gradient |

### Typography
| 요소 | 크기 / 굵기 / 행간 |
|---|---|
| Key visual title | 36px / bold / 1.3 |
| Section title | 28px / 700 / 1.3 |
| Body intro | 18px / 500 / 1.5 |
| Body default | 16px / 500 / 1.5 |
| Subtitle | 16px / 600 / 1.4 |
| Sub-title | 14px / 600 / 1.4 |
| Image caption | 14px / 500 / 1.5 |
| Button | 14px / 600 |

### Spacing
- Card padding: `20px` (callout/quote), `24px 20px` (type-row)
- Border radius: `12px` (card), `8px` (button small)
- Button height: `42px` / `48px` / `56px`
- Section margin-top: `48px`
- Divider gray height: `12px`

---

## 3. 전체 골격

```html
<div class="plustab-article-wrap">

  <!-- 1. 히어로 -->
  <div class="plustab-article-key-visual" style="background-image:url('{{HERO_IMAGE_URL}}')">
    <div class="plustab-article-key-visual-tit">
      <strong class="plustab-title">{{TITLE}}</strong>
      <p class="plustab-sub-title">{{SUBTITLE}}</p>
    </div>
  </div>

  <!-- 2. 본문 섹션 -->
  <section class="plustab-article">
    <div class="title-box">
      <span class="subtitle">{{SECTION_SUBTITLE}}</span>  <!-- optional -->
      <strong class="title">{{SECTION_TITLE}}</strong>
    </div>
    <div class="article-content">
      <!-- 본문 컴포넌트 조합 -->
    </div>
  </section>

  <!-- 3. divider (선택) -->
  <div class="divider-gray"></div>

  <!-- 4. 마무리 + CTA -->
  <section class="plustab-article-intro">
    <div class="article-content">
      <div class="desc-box"><p class="desc">{{CLOSING_TEXT}}</p></div>
      <div class="button-box">
        <a data-route class="btn btn-large btn-fill" href="{{CTA_URL}}"><span>{{CTA_LABEL}}</span></a>
      </div>
    </div>
  </section>

</div>
```

---

## 4. 본문 컴포넌트 카탈로그

### A. 텍스트 (`.desc-box`)
```html
<div class="desc-box">
  <p class="desc">본문 텍스트 (3-5문장)</p>
  <p class="desc">두 번째 단락</p>
  <p class="sub-desc">보조 설명 (회색)</p>
</div>

<!-- 핫 키워드 강조 -->
<div class="desc-box">
  <span class="point-title">핫 키워드</span>
  <p class="desc">본문</p>
</div>
```

### B. 이미지 (`.img-figure`)
```html
<p class="img-figure"><img src="{{IMG_URL}}" alt="{{ALT}}" /></p>
<p class="img-caption">설명 (선택)</p>
```

### C. 인포 카드 (`.callout-box`)
```html
<div class="callout-box">
  <div class="callout">
    <strong><span class="emoji" aria-hidden="true">📍</span>주소</strong>
    <p>실제 주소</p>
  </div>
  <div class="callout">
    <strong><span class="emoji" aria-hidden="true">📞</span>전화</strong>
    <p>전화번호</p>
  </div>
</div>
```

### D. 인용 박스 (`.quote-box`) — 이벤트 정보 정리
```html
<div class="quote-box">
  <div class="quote">
    <span class="quote-label">기간</span>
    <span class="quote-text">날짜 범위</span>
  </div>
  <div class="quote">
    <span class="quote-label">경품</span>
    <ul class="quote-text">
      <li><span class="label">1등(1명) :</span><span>경품명</span></li>
    </ul>
  </div>
</div>
```

### E. 슬라이드 (`.swiper-box`) — **B 타입 전용**
```html
<div class="swiper-box">
  <div class="swiper">
    <div class="swiper-wrapper">
      <div class="swiper-slide"><img src="{{IMG_1}}" alt="..." /></div>
      <div class="swiper-slide"><img src="{{IMG_2}}" alt="..." /></div>
    </div>
    <div class="swiper-pagination"></div>
  </div>
</div>
```
→ **반드시** 페이지 하단에 Swiper 초기화 스크립트 추가 (type_b.html 의 `<script>` 블록 참고).

### F. 버튼 (`.button-box`)
```html
<!-- 메인 (포인트 핑크) -->
<a data-route class="btn btn-large btn-point" href="{{URL}}"><span>{{LABEL}}</span></a>

<!-- 검정 채움 -->
<a data-route class="btn btn-large btn-fill" href="{{URL}}"><span>{{LABEL}}</span></a>

<!-- 외부 링크 (B 타입 마무리 CTA 에 자주 사용) -->
<a data-route class="btn btn-large btn-fill btn-outlink" href="{{URL}}" target="_blank" title="새창열기">
  <span>{{LABEL}}</span><i class="ic ic-outlink">↗</i>
</a>
```

### G. 제휴 카드 (`.info-card-box`) — 광고/제휴 표기
```html
<div class="info-card-box">
  <div class="logo-box">
    <div class="logo uplus"><img src="..." alt="U+" /></div>
    <div class="logo affiliate"><img src="..." alt="제휴사" /></div>
  </div>
  <p class="text">제휴 설명</p>
</div>
```

---

## 5. 타입별 권장 조합

| 타입 | 구성 | swiper-box | 마무리 CTA |
|---|---|---|---|
| **A** | 히어로 + 섹션 N + 인트로 | 금지 | 내부 링크 (btn-fill) |
| **B** | A 구조 + swiper-box ≥1 | 필수 | 외부 랜딩 (btn-outlink) |
| **C** | A 또는 B + `.plustab-interactive` | 선택 | 인터랙티브 결과 처리 |

---

## 6. 절대 규칙 (DO / DON'T)

✅ **DO**
- 위에 정의된 클래스만 사용
- 이미지 src 가 없으면 `https://image.lguplus.com/static/placeholder.jpg` 사용
- 외부 링크는 `target="_blank" title="새창열기"` 필수
- emoji 에 `aria-hidden="true"` 추가
- B 타입은 Swiper 초기화 스크립트를 빠뜨리지 않기
- 모바일 폭(480-500px) 기준 작성

❌ **DON'T**
- 새로운 클래스명 발명 금지 (`.cool-card`, `.my-button` 등 금지)
- 인라인 style 남용 금지 — 색상/사이즈는 클래스로
- 자유 텍스트 출력 금지 — 반드시 위 골격을 그대로 따른 HTML
- A 타입에서 swiper-box 사용 금지
- "정말", "너무" 같은 영혼 없는 강조어 사용 금지 (`docs/samples/content_voice_examples.md` 참조)
