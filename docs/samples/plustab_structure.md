# PlusTap HTML Structure Reference

> 이 문서는 LG U+ 플러스탭에 실제 사용되는 HTML 구조를 정의합니다.
> AIDEN의 HTML Builder 에이전트는 이 구조를 **반드시 그대로** 따라야 하며,
> 자체 클래스명 발명을 금지합니다.

---

## 외부 의존성 (필수)

콘텐츠 HTML 상단에 반드시 포함:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
```

---

## 디자인 토큰 (정확한 컬러/사이즈)

### Colors
| 용도 | 변수명 | 값 |
|---|---|---|
| Point (강조/CTA) | `--point` | `#ff2e98` |
| Body text | `--body` | `#181a1b` |
| Sub text | `--sub` | `#66707a` |
| Sub text 2 | `--sub2` | `#525960` |
| Card BG | `--card-bg` | `#f9fafb` |
| Border light | `--border-light` | `#e7ebee` |
| Border strong | `--border-strong` | `#181a1b` |
| White | `--white` | `#ffffff` |
| Key visual overlay | - | `#090708` (60% opacity gradient) |

### Typography
| 요소 | 크기 | 굵기 | 행간 |
|---|---|---|---|
| Key visual title | 36px | bold | 1.3 |
| Section title | 28px | 700 | 1.3 |
| Top section title | 24px | 700 | 1.3 |
| Body (intro) | 18px | 500 | 1.5 |
| Body (default) | 16px | 500 | 1.5 |
| Subtitle | 16px | 600 | 1.4 |
| Sub-title | 14px | 600 | 1.4 |
| Image caption | 14px | 500 | 1.5 |
| Button | 14px | 600 | - |

### Spacing
- Card padding: `20px` (callout-box, quote-box)
- Card padding (type-row): `24px 20px`
- Border radius (card): `12px`
- Border radius (button small): `8px`
- Button height: `42px` (default) / `48px` (medium) / `56px` (large)
- Section margin-top: `48px`
- Divider gray height: `12px`

---

## 전체 구조 (skeleton)

```html
<div class="plustab-article-wrap">

  <!-- 1. 히어로 (대표 이미지 + 제목) -->
  <div class="plustab-article-key-visual" style="background-image: url('...')">
    <div class="plustab-article-key-visual-tit">
      <strong class="plustab-title">{{TITLE}}</strong>
      <p class="plustab-sub-title">{{SUBTITLE}}</p>
    </div>
  </div>

  <!-- 2. 본문 섹션 1..N -->
  <section class="plustab-article">
    <div class="title-box">
      <strong class="title">{{SECTION_TITLE}}</strong>
      <span class="subtitle">{{SECTION_SUBTITLE}}</span>  <!-- optional -->
    </div>
    <div class="article-content">
      <!-- 본문 콘텐츠는 아래 컴포넌트들의 조합 -->
    </div>
  </section>

  <!-- 3. 섹션 간 회색 divider (선택) -->
  <div class="divider-gray"></div>

  <!-- 4. 마무리 인트로 박스 (선택) -->
  <section class="plustab-article-intro">
    <div class="article-content">
      <div class="desc-box">
        <p class="desc">{{CLOSING_TEXT}}</p>
      </div>
      <div class="button-box">
        <a class="btn btn-large btn-fill btn-outlink" href="{{CTA_URL}}" target="_blank">
          <span>{{CTA_LABEL}}</span>
          <i class="ic ic-outlink"></i>
        </a>
      </div>
    </div>
  </section>

</div>
```

---

## 본문 컴포넌트 카탈로그

### A. 텍스트 블록 (.desc-box)
```html
<div class="desc-box">
  <p class="desc">{{본문 텍스트, 줄바꿈은 \n 또는 <br>로}}</p>
</div>

<!-- 강조 포인트 텍스트 -->
<div class="desc-box">
  <span class="point-title">{{핫 키워드}}</span>
  <p class="desc">{{본문}}</p>
  <p class="sub-desc">{{보조 설명, 회색}}</p>
</div>
```

### B. 이미지 블록 (.img-figure)
```html
<p class="img-figure">
  <img src="{{IMAGE_URL}}" alt="{{ALT_TEXT}}" />
</p>
<p class="img-caption">{{이미지 설명}}</p>

<!-- 테두리 있는 이미지 -->
<p class="img-figure type-border">
  <img src="..." alt="..." />
</p>
```

### C. 인포 카드 박스 (.callout-box) - 여러 정보 나열
```html
<div class="callout-box">
  <div class="callout">
    <strong><span class="emoji" aria-hidden="true">📍</span>주소</strong>
    <p>{{주소}}</p>
  </div>
  <div class="callout">
    <strong><span class="emoji" aria-hidden="true">📞</span>전화</strong>
    <p>{{전화번호}}</p>
  </div>
  <div class="callout">
    <strong><span class="emoji" aria-hidden="true">📱</span>인스타그램</strong>
    <a data-route class="link" href="{{URL}}" target="_blank" title="새창열기">바로가기</a>
  </div>
</div>
```

### D. 인용 박스 (.quote-box) - 이벤트/정보 정리
```html
<div class="quote-box">
  <div class="quote">
    <span class="quote-label">기간</span>
    <span class="quote-text">{{기간}}</span>
  </div>
  <div class="quote">
    <span class="quote-label">경품</span>
    <ul class="quote-text">
      <li><span class="label">1등(1명) :</span><span>{{경품명}}</span></li>
    </ul>
  </div>
</div>
```

### E. 슬라이드 박스 (.swiper-box) - **B타입 전용**
```html
<div class="swiper-box">
  <div class="swiper">
    <div class="swiper-wrapper">
      <div class="swiper-slide"><img src="{{IMG_1}}" alt="..." /></div>
      <div class="swiper-slide"><img src="{{IMG_2}}" alt="..." /></div>
      <div class="swiper-slide"><img src="{{IMG_3}}" alt="..." /></div>
    </div>
    <div class="swiper-pagination"></div>
  </div>
</div>
```

**Swiper 초기화 스크립트 (B타입은 반드시 포함):**
```html
<script>
  setTimeout(function() {
    const swiper = new Swiper('.swiper', {
      direction: 'horizontal',
      slidesPerView: 1,
      spaceBetween: 0,
      loop: true,
      pagination: { el: '.swiper-pagination', clickable: true },
      keyboard: { enabled: true },
    });
  }, 1000);
</script>
```

### F. 버튼 박스 (.button-box)
```html
<!-- 메인 CTA (포인트 컬러) -->
<div class="button-box">
  <a data-route class="btn btn-large btn-point" href="{{URL}}">
    <span>{{LABEL}}</span>
  </a>
</div>

<!-- 외부 링크 (테두리 + 검정) -->
<div class="button-box">
  <a data-route class="btn btn-large btn-fill btn-outlink" 
     href="{{URL}}" target="_blank" title="새창열기">
    <span>{{LABEL}}</span>
    <i class="ic ic-outlink"></i>
  </a>
</div>
```

### G. 정보 카드 (.info-card-box) - 제휴/광고 표기
```html
<div class="info-card-box">
  <div class="logo-box">
    <div class="logo uplus"><img src="..." alt="U+" /></div>
    <div class="logo coll"><img src="..." alt="콜라보" /></div>
    <div class="logo affiliate"><img src="..." alt="제휴사" /></div>
  </div>
  <p class="text">{{제휴 설명}}</p>
</div>
```

---

## 콘텐츠 타입별 권장 조합

### A타입: 기본형 (이미지 + 글)
- 히어로 + 본문 섹션 N개 + 마무리 인트로
- 각 섹션: title-box + desc-box + img-figure + callout-box (선택) + button-box (선택)
- **swiper-box 사용 금지**

### B타입: 복합형 (이미지 + 글 + 본문 내 슬라이드 + 랜딩 URL)
- A타입 구조 + 본문 중간에 **swiper-box** 1개 이상 포함
- 마무리에 외부 랜딩 URL 버튼 (btn-outlink) 필수

### C타입: 인터랙티브 (인터랙티브 요소 포함)
- A 또는 B 구조 위에 인터랙티브 컴포넌트 삽입
- 인터랙티브 5종: Quiz / Calculator / Scenario Sim / Compare Slider / Checklist
- 인터랙티브는 plustab-article 내부 article-content 안에 배치
- 컨테이너 클래스: `.plustab-interactive` (신규, 자체 정의)

---

## 작성 시 절대 규칙

1. **클래스명 임의 발명 금지**: 위에 정의된 클래스만 사용
2. **인라인 스타일 최소화**: 색상/사이즈는 가급적 클래스로 제어
3. **이미지 src 처리**: 실제 이미지 없을 시 `https://image.lguplus.com/static/...` 형식 placeholder
4. **외부 링크**: `target="_blank" title="새창열기"` 필수
5. **모바일 우선**: max-width 480-500px 기준으로 작성
6. **swiper 초기화 누락 금지** (B타입에서 흔한 실수)
7. **emoji 사용 시 `aria-hidden="true"` 추가** (접근성)

---

## 참고: 실제 샘플

샘플 콘텐츠 예시는 `docs/samples/type_a_sample.html`, `docs/samples/type_b_sample.html` 참조.

샘플 콘텐츠 본문 톤 예시 (실제 사용 텍스트):

> "돌담통닭은 인공 조미료를 첨가하지 않고 국산 천일염으로만 염지한 닭을 사용한다.
> 야채를 갈아 숙성시킨 양념은 3대를 거쳐 내려오는 이곳의 비법이다.
> 특제 양념에 24시간 숙성한 닭을 튀겨 바삭하면서도 감칠맛 나는 치킨을 선보인다."

→ 정중하고 명료한 톤, "~다" 종결, 3-5문장 단락, 구체적 디테일 포함.
