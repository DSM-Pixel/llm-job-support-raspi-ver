# 규칙: web/ 프론트엔드 (frontend)

> 적용 대상: `web/**` (HTML/CSS/JS) 를 읽거나 수정할 때.

## 기존 디자인 구조 유지

- `web/`은 이다연(디자인)의 HTML/CSS 산출물이 기반이다. **기존 멀티페이지 구조를 유지한다**:
  - `index.html` → `pages/<화면>.html` 리다이렉트
  - `assets/css/common.css` + 페이지별 css, `assets/js/common.js` + 페이지별 js
- 디자인이 잡아둔 클래스명·레이아웃·색상 토큰을 임의로 갈아엎지 말 것. 로직을 채울 때는 **HTML 구조는 그대로 두고 JS에서 DOM을 채우는** 방식으로.
- 새 화면 추가 시 같은 패턴: `pages/<name>.html` + `assets/css/<name>.css` + `assets/js/<name>.js`.

## 프레임워크 신규 도입 금지

- **React/Vue/Svelte/jQuery/Tailwind/번들러(webpack, vite) 등 어떤 프레임워크·빌드 도구도 새로 넣지 않는다.** Vanilla HTML/CSS/JS 유지.
- CDN 스크립트 추가도 원칙적으로 금지 (오프라인 RPi5 시연에서 깨진다). 꼭 필요하면 파일을 `assets/`에 받아서 로컬 서빙.
- npm/package.json을 만들지 말 것.

## backend API 연동

- 서버 호출은 **`fetch()` + 상대경로 `/api/...`** 만 사용한다 (호스트/포트 하드코딩 금지 — 통합 서버가 같은 오리진에서 서빙).
- 공통 fetch 헬퍼·인증 처리는 `assets/js/common.js`에 두고 페이지 js에서 재사용.
- API 실패 시 화면이 깨지지 않게 **HTML 기본값으로 폴백** (정적으로만 열어도 페이지가 보여야 한다 — 기존 컨벤션).
- 응답의 `"backend": "MOCK"` 필드가 있으면 UI에 MOCK 표시를 유지한다.
- API 키·시크릿을 JS에 넣지 말 것 — 외부 API는 전부 백엔드가 프록시한다.

## 확인 방법

- 수정 후 `uvicorn backend.app:app --reload` (또는 `./run_web.sh`) 로 띄워 http://localhost:8000 에서 실제 화면을 확인한다.
- 브라우저 캐시 무효화는 서버 미들웨어(no-cache)가 처리하므로 쿼리스트링 버전 태그를 붙일 필요 없다.
