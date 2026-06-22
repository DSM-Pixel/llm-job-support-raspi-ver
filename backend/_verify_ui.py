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

    # 3) RAG ─ 질의 연관도 검색 + 질문별 답변 + 업로드/웹 문서
    page.goto(f"{BASE}/pages/rag.html")

    def rag_query(q):
        prev = page.inner_text(".answer p")
        page.fill(".ask-line input", q)
        page.click(".ask-line .primary")
        page.wait_for_function(
            "(t) => document.querySelector('.answer p').innerText !== t", arg=prev
        )

    # 질문 A
    rag_query("포트홀 긴급 보수 기한은?")
    srcs = page.query_selector_all(".source-list .source")
    top_a = page.inner_text(".source-list .source:first-child b")
    score_text = page.inner_text(".source-list .source:first-child em").strip()
    conf = page.inner_text(".answer-head > .status")
    check("rag: 근거 렌더", len(srcs) >= 1, f"{len(srcs)}건")
    check(
        "rag: 연관도 0~100 표기", score_text.endswith("%") and score_text[:-1].isdigit(), score_text
    )
    check("rag: 연관도 헤더(% 기준)", "%" in conf, conf)

    # 질문 B (다른 주제) → 근거 문서가 달라져야 함(질문별 검색)
    rag_query("가드레일 점검 주기는?")
    top_b = page.inner_text(".source-list .source:first-child b")
    check("rag: 질문별 근거 변화", top_b != top_a, f"A={top_a} / B={top_b}")

    # 참고 문서에 없는 질문 → 억지 유사답변 대신 "근거 없음"
    rag_query("우주 비행사의 우주선 연료 종류는?")
    none_srcs = page.query_selector_all(".source-list .source")
    none_ans = page.inner_text(".answer p")
    none_conf = page.inner_text(".answer-head > .status")
    check(
        "rag: 무관 질문은 근거 없음",
        len(none_srcs) == 0
        and ("찾지 못" in none_ans or "없습니다" in none_ans)
        and "근거 없음" in none_conf,
        f"sources={len(none_srcs)} / {none_conf}",
    )

    # 웹에서 찾아 넣기 → 결과 선택 → 색인 추가
    page.fill(".search-line input", "포트홀 보수 공법")
    page.click(".search-line button")
    page.wait_for_selector(".web-results .web-item")
    web_items = len(page.query_selector_all(".web-results .web-item"))
    files_before = len(page.query_selector_all(".file-list li"))
    page.click(".web-results .add-web")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.file-list li').length > n", arg=files_before
    )
    check("rag: 웹 결과 선택 추가", web_items == 3, f"{web_items}건 표시")

    # 업로드 문서가 검색 근거에 포함되는지
    page.set_input_files(
        ".upload-input",
        files=[
            {
                "name": "myrule.txt",
                "mimeType": "text/plain",
                "buffer": "특이키워드 자이로 보수 지침".encode(),
            }
        ],
    )
    page.wait_for_function("() => document.querySelector('.indexed').innerText.includes('색인')")
    rag_query("특이키워드 자이로 지침")
    check(
        "rag: 업로드 문서가 근거에 표시",
        "myrule.txt" in page.inner_text(".source-list"),
        page.inner_text(".source-list .source:first-child b"),
    )

    # 답변 복사 + 색인 초기화
    page.click(".answer-actions button:has-text('복사')")
    page.click(".index-actions .flat")
    page.wait_for_function("() => document.querySelector('.indexed').innerText.includes('초기화')")
    check("rag: 색인 초기화", "초기화" in page.inner_text(".indexed"), page.inner_text(".indexed"))

    # 4) Labeling ─ 설명 분석 + 모달(그리기/AI탐지/중복방지/저장→미리보기 유지)
    page.goto(f"{BASE}/pages/labeling.html")
    page.click(".label-panel .primary")
    page.wait_for_selector(".finding-list li")
    findings = page.query_selector_all(".finding-list li")
    check("labeling: 설명 분석 렌더", len(findings) >= 1, f"{len(findings)}건")

    # 모달 열기(이미지 없음 → AI 자동탐지는 프리셋 MOCK)
    page.click(".open-label-modal")
    page.wait_for_selector("#label-modal:not([hidden])")
    page.wait_for_function(
        "() => { const b=document.querySelector('.canvas-boxes'); return b && b.getBoundingClientRect().width > 50; }"
    )
    check("labeling: 모달 열림", page.is_visible(".label-modal"))
    check("labeling: 신뢰도 필터 제거됨", page.query_selector(".modal-conf") is None)

    # AI 자동 탐지 → 박스 추가
    page.click(".modal-detect")
    page.wait_for_function("() => document.querySelectorAll('.box-list li').length >= 1")
    n1 = len(page.query_selector_all(".box-list li"))
    # 같은 이미지로 다시 탐지 → 중복 추가 안 됨
    page.click(".modal-detect")
    page.wait_for_timeout(400)
    n2 = len(page.query_selector_all(".box-list li"))
    check("labeling: AI 자동 탐지", n1 >= 1, f"{n1}개")
    check("labeling: 중복 박스 방지", n2 == n1, f"{n1}→{n2}")

    # 드래그로 박스 그리기(+1)
    layer = page.locator(".canvas-boxes").bounding_box()
    page.mouse.move(layer["x"] + 20, layer["y"] + 20)
    page.mouse.down()
    page.mouse.move(layer["x"] + 120, layer["y"] + 90, steps=6)
    page.mouse.up()
    page.wait_for_function(
        "(n) => document.querySelectorAll('.box-list li').length === n + 1", arg=n2
    )
    drawn_total = len(page.query_selector_all(".box-list li"))

    # 개별 삭제(-1)
    page.click(".box-list li:first-child .del")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.box-list li').length === n - 1", arg=drawn_total
    )
    check(
        "labeling: 박스 개별 삭제", len(page.query_selector_all(".box-list li")) == drawn_total - 1
    )

    # COCO 내보내기
    with page.expect_download() as di:
        page.click(".modal-export-coco")
    check(
        "labeling: COCO 내보내기",
        di.value.suggested_filename.endswith(".coco.json"),
        di.value.suggested_filename,
    )

    saved_count = len(page.query_selector_all(".box-list li"))

    # 저장 안 한 채 닫기 → 확인 다이얼로그(자동 저장 안 함)
    page.click(".label-modal .modal-close")
    page.wait_for_selector(".confirm-save:not([hidden])")
    check(
        "labeling: 미저장 닫기 시 확인창",
        page.is_visible(".confirm-save") and page.is_visible(".label-modal"),
    )
    page.click(".confirm-cancel")
    page.wait_for_selector(".confirm-save", state="hidden")
    check("labeling: 확인창 취소 시 모달 유지", page.is_visible(".label-modal"))

    # 저장 → 모달 닫힘 + 미리보기 반영
    page.click(".modal-save")
    page.wait_for_selector("#label-modal", state="hidden")
    pbox = len(page.query_selector_all(".preview-boxes .pbox"))
    check("labeling: 저장 시 모달 닫힘+미리보기 반영", pbox == saved_count, f"{pbox}/{saved_count}")

    # 재열기 → 복원
    page.click(".open-label-modal")
    page.wait_for_selector("#label-modal:not([hidden])")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.box-list li').length === n", arg=saved_count
    )
    check("labeling: 재열기 시 복원", len(page.query_selector_all(".box-list li")) == saved_count)

    # 새 박스 그린 뒤 '저장 안 함'으로 닫기 → 미반영(저장 안 눌렀으니)
    page.wait_for_function(
        "() => { const b=document.querySelector('.canvas-boxes'); return b && b.getBoundingClientRect().width > 50; }"
    )
    lay2 = page.locator(".canvas-boxes").bounding_box()
    page.mouse.move(lay2["x"] + 200, lay2["y"] + 30)
    page.mouse.down()
    page.mouse.move(lay2["x"] + 260, lay2["y"] + 80, steps=4)
    page.mouse.up()
    page.wait_for_function(
        "(n) => document.querySelectorAll('.box-list li').length === n + 1", arg=saved_count
    )
    page.click(".label-modal .modal-close")
    page.wait_for_selector(".confirm-save:not([hidden])")
    page.click(".confirm-discard")
    page.wait_for_selector("#label-modal", state="hidden")
    pbox2 = len(page.query_selector_all(".preview-boxes .pbox"))
    check("labeling: 저장 안 함 선택 시 미반영", pbox2 == saved_count, f"{pbox2}/{saved_count}")

    # 이미지 교체(인라인)
    page.set_input_files(
        ".image-input",
        files=[{"name": "my_road.png", "mimeType": "image/png", "buffer": make_png()}],
    )
    page.wait_for_selector(".road-preview.has-image .preview-img")
    check(
        "labeling: 이미지 교체 표시",
        page.inner_text(".sample-name") == "my_road.png",
        page.inner_text(".sample-name"),
    )

    # 설정(⚙) 모달
    page.click(".gear")
    page.wait_for_selector("#settings-modal:not([hidden])")
    check("settings: 모달 열림", page.is_visible("#settings-modal"))
    page.fill("#settings-modal [name=defaultClass]", "균열")
    page.click(".modal-save-settings")
    page.wait_for_selector("#settings-modal", state="hidden")
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('gnsoft.settings')).defaultClass")
    check("settings: 저장/영속", saved == "균열", f"defaultClass={saved}")

    # 5) Report ─ 유형별 내용 변화 + 편집 가능
    page.goto(f"{BASE}/pages/report.html")
    # 첫 진입 시 자동 렌더(현황 분석)
    page.wait_for_selector(".report-page section [contenteditable='true']")
    check(
        "report: 편집 가능 문서 렌더",
        page.query_selector(".report-page h2[contenteditable]") is not None,
    )

    # 정책 브리핑
    page.click(".select-list button:nth-child(2)")
    page.click(".report-form .primary")
    page.wait_for_function(
        "() => document.querySelector('.report-page header h2').innerText.includes('정책 브리핑')"
    )
    brief_text = page.inner_text(".report-page")
    secs = len(page.query_selector_all(".report-page section"))
    check("report: 정책 브리핑 내용", "정책 제언" in brief_text and secs >= 4, f"sections={secs}")

    # 검수 요약 → 내용이 달라짐
    page.click(".select-list button:nth-child(3)")
    page.click(".report-form .primary")
    page.wait_for_function(
        "() => document.querySelector('.report-page header h2').innerText.includes('검수 요약')"
    )
    audit_text = page.inner_text(".report-page")
    check("report: 유형별 내용 변화", "라벨 정확도" in audit_text and "정책 제언" not in audit_text)

    # 본문 직접 수정(편집 가능)
    p = page.query_selector(".report-page section p")
    p.click()
    page.evaluate("(el)=>{el.textContent='수정된 본문 테스트';}", p)
    check("report: 본문 편집 가능", "수정된 본문 테스트" in page.inner_text(".report-page"))

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
