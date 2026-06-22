"""통합 UI 기능 검증 (Playwright headless).

서버가 떠 있는 상태에서 각 페이지를 실제로 클릭/입력해 동적 기능이
정상 동작하는지 확인한다. 일회성 점검용 스크립트.

사용:
    uvicorn backend.app:app --port 8011   # 다른 터미널
    python backend/_verify_ui.py 8011
"""

import io
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = f"http://127.0.0.1:{sys.argv[1] if len(sys.argv) > 1 else '8011'}"
results = []
console_errors = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def make_png():
    img = Image.new("RGB", (320, 200), (90, 110, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))

    # 1) Dashboard ─ API 렌더링
    page.goto(f"{BASE}/pages/dashboard.html")
    page.wait_for_selector(".stat-grid .stat-card")
    cards = page.query_selector_all(".stat-grid .stat-card")
    bars = page.query_selector_all(".chart-bars .bar-item")
    models = page.query_selector_all(".model-card .model-row")
    acts = page.query_selector_all(".activity-card ul li")
    check("dashboard: 통계 카드 4개", len(cards) == 4, f"{len(cards)}개")
    check("dashboard: 주간 차트 7개", len(bars) == 7, f"{len(bars)}개")
    check("dashboard: 모델 상태 4행", len(models) == 4, f"{len(models)}행")
    check("dashboard: 최근 활동 4건", len(acts) == 4, f"{len(acts)}건")

    # 2) Query ─ 의도 라우팅 + 답변 렌더
    page.goto(f"{BASE}/pages/query.html")
    page.fill(".input-wrap input", "포트홀 영역을 찾아줘")
    page.click(".input-wrap button")
    page.wait_for_selector(".message.assistant .message-actions a")
    href = page.get_attribute(".message.assistant:last-child .message-actions a", "href")
    check("query: 답변 렌더 + 라벨링 링크", href == "labeling.html", f"href={href}")

    # 3) RAG ─ 검색 결과 갱신
    page.goto(f"{BASE}/pages/rag.html")
    before = page.inner_text(".answer p")
    page.fill(".ask-line input", "거북등 균열은 어떻게 보수해?")
    page.click(".ask-line .primary")
    page.wait_for_function(
        "(t) => document.querySelector('.answer p') && document.querySelector('.answer p').innerText !== t",
        arg=before,
    )
    srcs = page.query_selector_all(".source-list .source")
    conf = page.inner_text(".answer-head > .status")
    check("rag: 근거 3건 렌더", len(srcs) == 3, f"{len(srcs)}건")
    check("rag: 신뢰도 갱신", "신뢰도" in conf, conf)

    files_before = len(page.query_selector_all(".file-list li"))
    page.fill(".search-line input", "포트홀 보수 기준")
    page.click(".search-line button")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.file-list li').length > n", arg=files_before
    )
    files_after = len(page.query_selector_all(".file-list li"))
    check(
        "rag: 웹 검색 결과 추가", files_after == files_before + 3, f"{files_before}→{files_after}"
    )

    page.click(".index-actions .flat")
    page.wait_for_function("() => document.querySelector('.indexed').innerText.includes('초기화')")
    check("rag: 색인 초기화", "초기화" in page.inner_text(".indexed"), page.inner_text(".indexed"))

    page.click(".answer-actions button:has-text('복사')")
    check("rag: 답변 복사 동작", True)  # 예외 없이 핸들러 실행

    # 4) Labeling ─ 분석 + 이미지 교체
    page.goto(f"{BASE}/pages/labeling.html")
    page.click(".label-panel .primary")
    page.wait_for_selector(".finding-list li")
    findings = page.query_selector_all(".finding-list li")
    check("labeling: 분석 결과 렌더", len(findings) >= 1, f"{len(findings)}건")

    page.set_input_files(
        ".image-input",
        files=[
            {"name": "my_road.png", "mimeType": "image/png", "buffer": make_png()},
        ],
    )
    page.wait_for_selector(".road-preview.has-image .preview-img")
    img_hidden = page.get_attribute(".preview-img", "hidden")
    name_shown = page.inner_text(".sample-name")
    check(
        "labeling: 이미지 교체 표시",
        img_hidden is None and name_shown == "my_road.png",
        f"name={name_shown}",
    )

    page.click(".result-card .answer-actions button:has-text('박스')")
    box_active = page.eval_on_selector(
        ".mode-tabs",
        "el => [...el.querySelectorAll('button')].some(b => b.textContent.includes('박스') && b.classList.contains('active'))",
    )
    toolbar_visible = page.is_visible(".draw-toolbar")
    draw_mode = page.eval_on_selector(".road-preview", "el => el.classList.contains('draw-mode')")
    check("labeling: 박스 모드 전환", box_active and toolbar_visible and draw_mode)

    # 실제 드래그로 박스 그리기
    layer = page.locator(".box-layer").bounding_box()
    page.mouse.move(layer["x"] + 30, layer["y"] + 30)
    page.mouse.down()
    page.mouse.move(layer["x"] + 140, layer["y"] + 110, steps=6)
    page.mouse.up()
    page.wait_for_selector(".box-layer .draw-box")
    drawn = page.query_selector_all(".box-layer .draw-box")
    count_text = page.inner_text(".box-count")
    check("labeling: 박스 그리기 동작", len(drawn) == 1 and "1개" in count_text, count_text)

    page.click(".clear-boxes")
    page.wait_for_function("() => document.querySelectorAll('.box-layer .draw-box').length === 0")
    check("labeling: 박스 지우기", len(page.query_selector_all(".box-layer .draw-box")) == 0)

    page.click(".result-card .answer-actions button:has-text('저장')")
    page.wait_for_selector(".toast.show")
    toast_text = page.inner_text(".toast")
    check("labeling: 라벨 저장 동작", "저장" in toast_text, toast_text)

    # 5) Report ─ 보고서 생성
    page.goto(f"{BASE}/pages/report.html")
    page.click(".select-list button:nth-child(2)")  # 정책 브리핑
    page.click(".report-form .primary")
    page.wait_for_function(
        "() => document.querySelector('.report-page header h2').innerText.includes('정책 브리핑')"
    )
    title = page.inner_text(".report-page header h2")
    check("report: 제목 갱신", "정책 브리핑" in title, title)

    # 6) Data ─ 목록 로드 + 검색 필터
    page.goto(f"{BASE}/pages/data.html")
    page.wait_for_selector("tbody tr")
    rows = page.query_selector_all("tbody tr")
    check("data: 데이터셋 5행 로드", len(rows) == 5, f"{len(rows)}행")
    page.fill(".search-upload input", "cctv")
    page.wait_for_timeout(200)
    visible = [r for r in page.query_selector_all("tbody tr") if r.is_visible()]
    check("data: 검색 필터 동작", len(visible) == 1, f"{len(visible)}행 표시")

    browser.close()

print("\n=== 콘솔/페이지 에러 ===")
print("없음" if not console_errors else "\n".join(f"  - {e}" for e in console_errors))

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== 결과: {passed}/{len(results)} 통과 ===")
sys.exit(0 if passed == len(results) and not console_errors else 1)
