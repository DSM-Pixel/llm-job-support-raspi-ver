"""통합 UI 기능 검증 (Playwright headless).

서버가 떠 있는 상태에서 각 페이지를 실제로 클릭/입력해 동적 기능이
정상 동작하는지 확인한다. 일회성 점검용 스크립트.

사용:
    uvicorn backend.app:app --port 8011   # 다른 터미널
    python backend/_verify_ui.py 8011
"""

import io
import sys
from urllib.parse import quote

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

    # Gemini 모델 행 클릭 → 무료 한도(RPD/RPM/TPM/컨텍스트) 기준 사용 현황 상세 모달
    page.click(".model-row-click")
    page.wait_for_selector(".mm-body .mm-row")
    mm = page.inner_text(".mm-body")
    check(
        "dashboard: Gemini 사용 현황 상세(클릭)",
        "일일 요청 한도(RPD)" in mm and "토큰" in mm and "컨텍스트" in mm,
        mm.replace("\n", " ")[:24],
    )
    page.click(".modal-overlay:not([hidden]) .modal-close")
    check("dashboard: 최근 활동 4건", len(acts) == 4, f"{len(acts)}건")

    # 활동 기록이 있으면 최근 활동·주간 처리량이 실데이터로 표시(통계 카드는 MOCK 유지)
    page.evaluate(
        "() => { const n=Date.now(); localStorage.setItem('gnsoft.activity', JSON.stringify(["
        "{ts:n-3600e3,page:'rag',type:'RAG 검색',label:'포트홀 위치'},"
        "{ts:n-120e3,page:'query',type:'자연어 질의',label:'포트홀이 뭐야?'}])); }"
    )
    page.reload()
    page.wait_for_selector(".activity-card ul li")
    act_text = page.inner_text(".activity-card ul")
    check(
        "dashboard: 활동 기록 실데이터 반영",
        "RAG 검색" in act_text and "자연어 질의" in act_text,
        act_text[:24].replace("\n", " "),
    )
    page.evaluate("() => localStorage.removeItem('gnsoft.activity')")

    # 상단 ? 사용법 모달 + 클로바(♧) 제거
    clover = page.evaluate(
        "() => [...document.querySelectorAll('.top-actions span')].some(s => s.textContent.trim()==='♧')"
    )
    check("topbar: 클로바(♧) 제거", not clover)
    page.click(".help-trigger")
    page.wait_for_selector("#help-modal:not([hidden])")
    slide1 = page.inner_text(".help-title")
    page.click(".help-next")
    slide2 = page.inner_text(".help-title")
    check("help: 사용법 모달 + 화살표 이동", slide1 != slide2, f"{slide1}→{slide2}")
    # 실제 화면 캡쳐 + '이 화면으로 이동' 버튼이 있는 가이드(이미지 로드 대기)
    shot_src = page.get_attribute("#help-modal .help-shot img", "src")
    page.wait_for_function(
        "() => { const i=document.querySelector('#help-modal .help-shot img'); "
        "return i && i.naturalWidth > 0; }",
        timeout=10000,
    )
    shot_w = page.evaluate(
        "() => { const i=document.querySelector('#help-modal .help-shot img'); return i?i.naturalWidth:0; }"
    )
    check(
        "help: 가이드 화면 캡쳐 + 이동 버튼",
        bool(shot_src)
        and "guide/" in shot_src
        and shot_w > 0
        and page.query_selector("#help-modal .help-go") is not None,
        f"{shot_src} w={shot_w}",
    )
    page.click("#help-modal .modal-close")

    # 2) Query ─ 질문 분류: 일반은 바로 답변, 데이터/이미지는 연계 안내
    page.goto(f"{BASE}/pages/query.html")
    # 이미지 작업 질문(영역) → 이미지 분석·라벨링으로 연계
    page.fill(".input-wrap input", "포트홀 영역을 찾아줘")
    page.click(".input-wrap button")
    page.wait_for_selector(".message.assistant .message-actions a")
    href = page.get_attribute(".message.assistant:last-child .message-actions a", "href")
    check("query: 이미지 질문 → 라벨링 연계", href == "labeling.html", f"href={href}")

    # 일반 지식 질문(뭐야?) → 라우팅 버튼 없이 바로 답변
    page.fill(".input-wrap input", "포트홀이 뭐야?")
    page.click(".input-wrap button")
    page.wait_for_function(
        "() => { const m=document.querySelectorAll('.message.assistant'); "
        "const last=m[m.length-1]; return last && !last.querySelector('.typing') "
        "&& last.querySelector('.message-body p'); }",
        timeout=70000,  # 일반 답변은 Gemini 웹검색을 거쳐 지연될 수 있음
    )
    gen_actions = page.query_selector_all(".message.assistant:last-child .message-actions a")
    check(
        "query: 일반 질문은 바로 답변(연계 없음)",
        len(gen_actions) == 0,
        f"actions={len(gen_actions)}",
    )

    # 데이터 조회 질문(날짜·위치) → RAG 공공데이터 검색으로 연계 안내 + 버튼
    page.fill(".input-wrap input", "2026.04.24 8시에 찍힌 포트홀 위치 알려줘")
    page.click(".input-wrap button")
    page.wait_for_function(
        "() => { const a=document.querySelector('.message.assistant:last-child .message-actions a'); "
        "return a && a.getAttribute('href').startsWith('rag.html?q='); }"
    )
    rag_href = page.get_attribute(".message.assistant:last-child .message-actions a", "href")
    ans_txt = page.inner_text(".message.assistant:last-child .message-body")
    check(
        "query: 데이터 질문 → RAG 연계 안내",
        rag_href.startswith("rag.html?q=") and "RAG 공공데이터 검색" in ans_txt,
        rag_href[:40],
    )

    # 연계: RAG 페이지가 ?q= 질문을 색인 데이터에서 자동 검색(탐지로그 매칭)
    page.goto(f"{BASE}/pages/rag.html?q=" + quote("2026.04.24 08시 포트홀 위치"))
    page.wait_for_function(
        "() => (document.querySelector('.source-list')?.innerText || '').includes('탐지로그')"
    )
    check(
        "query→rag: ?q 자동 검색(탐지로그 매칭)",
        "탐지로그" in page.inner_text(".source-list"),
    )

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

    # 문서 선택은 '스테이징'만(아직 참고중인 파일에 안 들어감) → 문서 색인 눌러야 추가
    files_pre = len(page.query_selector_all(".file-list li"))
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
    page.wait_for_selector(".staged-files:not([hidden])")
    staged_not_indexed = len(page.query_selector_all(".file-list li")) == files_pre
    check("rag: 선택만으론 미추가(스테이징)", staged_not_indexed)
    page.click(".index-btn")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.file-list li').length > n", arg=files_pre
    )
    check("rag: 문서 색인 시 추가됨", len(page.query_selector_all(".file-list li")) > files_pre)
    rag_query("특이키워드 자이로 지침")
    check(
        "rag: 업로드 문서가 근거에 표시",
        "myrule.txt" in page.inner_text(".source-list"),
        page.inner_text(".source-list .source:first-child b"),
    )

    # 전체 참고 파일 초기화(샘플 포함 0개) → 샘플 토글로 복원
    page.click(".reset-all")
    page.wait_for_function("() => document.querySelectorAll('.file-list li').length === 0")
    check("rag: 전체 초기화(샘플 포함 0개)", len(page.query_selector_all(".file-list li")) == 0)
    page.click(".toggle-row .switch")  # 샘플 토글 ON → 복원
    page.wait_for_function("() => document.querySelectorAll('.file-list li').length > 0")
    check("rag: 샘플 토글로 복원", len(page.query_selector_all(".file-list li")) > 0)

    # 참고중인 파일 클릭 → 문서 내용 열람
    page.locator(".file-list li").filter(has_text="포트홀_보수_기준").first.click()
    page.wait_for_selector(".modal-overlay:not([hidden]) .doc-chunk")
    doc_title = page.inner_text(".doc-title")
    doc_chunks = len(page.query_selector_all(".doc-chunk"))
    check(
        "rag: 참고 파일 열람",
        "포트홀" in doc_title and doc_chunks >= 1,
        f"{doc_title} / {doc_chunks}청크",
    )
    page.locator(".modal-overlay:not([hidden]) .modal-close").click()

    # 참고중인 파일 삭제(✕)
    files_n = len(page.query_selector_all(".file-list li"))
    page.locator(".file-list li .file-del").first.click()
    page.wait_for_function(
        "(n) => document.querySelectorAll('.file-list li').length === n - 1", arg=files_n
    )
    check("rag: 참고 파일 삭제", len(page.query_selector_all(".file-list li")) == files_n - 1)

    # 추천 질문이 참고 파일에 따라 변함(포트홀 파일 삭제 후 포트홀 추천 사라짐)
    page.wait_for_function("() => document.querySelectorAll('.chips .pill').length >= 1")
    chips_text = page.inner_text(".chips")
    check("rag: 추천 질문이 파일 따라 변화", "포트홀" not in chips_text, chips_text[:30])

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

    # 라벨 박스가 그려진 이미지 다운로드(샘플도 도로 배경 위에 박스로 생성)
    with page.expect_download() as di_img:
        page.click(".modal-export-img")
    check(
        "labeling: 라벨 이미지 다운로드",
        di_img.value.suggested_filename.endswith("_labeled.jpg"),
        di_img.value.suggested_filename,
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
    page.fill("#settings-modal [name=name]", "테스트유저")
    page.fill("#settings-modal [name=team]", "QA팀")
    page.select_option("#settings-modal [name=theme]", "dark")  # 다크 모드 선택
    page.click(".modal-save-settings")
    page.wait_for_selector("#settings-modal", state="hidden")
    saved = page.evaluate("() => JSON.parse(localStorage.getItem('gnsoft.settings')).name")
    check(
        "settings: 이름/소속 저장 + 사이드바 반영",
        saved == "테스트유저" and page.inner_text(".user-name") == "테스트유저",
        f"{saved} / {page.inner_text('.user-name')}",
    )
    # 다크 모드 저장 → <html data-theme=dark> 즉시 적용 + 영속(설정 다시 열면 dark)
    theme_applied = page.get_attribute("html", "data-theme")
    page.click(".gear")
    page.wait_for_selector("#settings-modal:not([hidden])")
    theme_val = page.input_value("#settings-modal [name=theme]")
    check(
        "settings: 다크 모드 적용·영속",
        theme_applied == "dark" and theme_val == "dark",
        f"applied={theme_applied} saved={theme_val}",
    )
    # 다시 라이트로 되돌려 이후 단계 영향 없게
    page.select_option("#settings-modal [name=theme]", "light")
    page.click(".modal-save-settings")
    page.wait_for_selector("#settings-modal", state="hidden")

    # 설정한 이름이 대시보드 인사말에도 반영되는지
    page.goto(f"{BASE}/pages/dashboard.html")
    page.wait_for_selector(".user-greet")
    check(
        "settings: 이름이 대시보드 인사말에 반영",
        page.inner_text(".user-greet") == "테스트유저",
        page.inner_text(".user-greet"),
    )

    # 5) Report ─ 내 웹 활동 기반 통계 보고서 + 시작/종료 날짜 + 편집 가능
    page.goto(f"{BASE}/pages/report.html")
    # 기본 진입 = 내 활동 분석 보고서(편집 가능 문서 즉시 렌더)
    page.wait_for_selector(".report-page section [contenteditable='true']")
    check(
        "report: 편집 가능 활동 보고서 렌더",
        page.query_selector(".report-page h2[contenteditable]") is not None,
    )

    # 제목 편집 시(어두운 헤더) 글자가 흰색으로 유지돼 보여야 함
    page.click(".report-page header h2")
    title_color = page.evaluate(
        "() => getComputedStyle(document.querySelector('.report-page header h2')).color"
    )
    check(
        "report: 제목 편집 글자 보임(흰색 유지)", title_color == "rgb(255, 255, 255)", title_color
    )

    # 시작/종료 날짜 입력이 기본값(최근 30일~오늘)으로 채워져 있음
    d_start = page.input_value(".date-start")
    d_end = page.input_value(".date-end")
    check(
        "report: 시작/종료 날짜 입력 기본값",
        bool(d_start) and bool(d_end) and d_start <= d_end,
        f"{d_start} ~ {d_end}",
    )

    # 내 활동 로그를 주입(질의 2 + 이미지 분석 1)하고 '보고서 생성' → 활동 통계 집계
    page.evaluate(
        "() => { const now = Date.now(); localStorage.setItem('gnsoft.activity', "
        "JSON.stringify([{ts:now,page:'query',type:'자연어 질의',label:'포트홀'},"
        "{ts:now,page:'query',type:'자연어 질의',label:'균열'},"
        "{ts:now,page:'labeling',type:'이미지 분석',label:'도로 파손/포트홀 찾기'}])); }"
    )
    before = page.inner_text(".report-page")
    page.click(".report-form .primary")
    page.wait_for_function(
        "(t) => { const r=document.querySelector('.report-page'); "
        "return r && r.innerText !== t && r.innerText.includes('총 활동 3건'); }",
        arg=before,
        timeout=70000,
    )
    rep = page.inner_text(".report-page")
    check(
        "report: 내 활동 기반 통계 보고서", "자연어 질의" in rep and "총 활동 3건" in rep, rep[:40]
    )

    # 활동 유형별 통계 표 렌더(통계 차트 포함 ON 기본)
    check("report: 활동 통계 표 렌더", page.query_selector(".report-page table") is not None)

    # 보고서 유형 전환(활동 통계) → 제목에 반영
    page.click(".select-list button:nth-child(2)")
    before2 = page.inner_text(".report-page")
    page.click(".report-form .primary")
    page.wait_for_function(
        "(t) => { const h=document.querySelector('.report-page header h2'); "
        "return h && h.innerText.includes('활동 통계') "
        "&& document.querySelector('.report-page').innerText !== t; }",
        arg=before2,
        timeout=70000,
    )
    check("report: 유형 전환 제목 반영", "활동 통계" in page.inner_text(".report-page header h2"))

    # 과거 날짜 범위로 좁히면 활동 0건 → '없습니다' 안내
    page.fill(".date-start", "2000-01-01")
    page.fill(".date-end", "2000-01-31")
    before3 = page.inner_text(".report-page")
    page.click(".report-form .primary")
    page.wait_for_function(
        "(t) => { const r=document.querySelector('.report-page'); "
        "return r && r.innerText !== t && r.innerText.includes('총 활동 0건'); }",
        arg=before3,
        timeout=70000,
    )
    check(
        "report: 날짜 범위 필터(과거→0건)",
        "총 활동 0건" in page.inner_text(".report-page"),
    )

    # 본문 직접 수정(편집 가능)
    p = page.query_selector(".report-page section p")
    p.click()
    page.evaluate("(el)=>{el.textContent='수정된 본문 테스트';}", p)
    check("report: 본문 편집 가능", "수정된 본문 테스트" in page.inner_text(".report-page"))

    # 섹션 휴지통 → 확인 모달 → 삭제(되돌릴 수 없음 안내)
    sec_n = len(page.query_selector_all(".report-page section"))
    first_sec = page.locator(".report-page section").first
    first_sec.hover()
    first_sec.locator(".sec-del").click()
    page.wait_for_selector(".confirm-modal:not([hidden]) .confirm-delete")
    check(
        "report: 섹션 삭제 확인 모달",
        page.is_visible(".confirm-modal")
        and len(page.query_selector_all(".report-page section")) == sec_n,
    )
    page.click(".confirm-modal .confirm-delete")
    page.wait_for_function(
        "(n) => document.querySelectorAll('.report-page section').length === n - 1", arg=sec_n
    )
    check(
        "report: 섹션 삭제(확인 후)",
        len(page.query_selector_all(".report-page section")) == sec_n - 1,
    )

    # 사진 첨부는 staged(생성 전엔 본문 미반영) → '보고서 생성' 시 본문에 들어감
    page.set_input_files(
        ".report-image-input",
        files=[{"name": "shot.png", "mimeType": "image/png", "buffer": make_png()}],
    )
    page.wait_for_selector(".report-thumbs .report-thumb img")
    staged_only = page.query_selector(".report-page .report-attachments") is None
    page.click(".report-form .primary")
    page.wait_for_selector(".report-page .report-attachments img")
    check(
        "report: 사진은 생성 시에만 반영(staged)",
        staged_only and page.query_selector(".report-page .report-attachments img") is not None,
    )

    # 내 작업 산출물(이미지+RAG) 주입 → 썸네일 클릭 시 상세 모달, '추가' → 생성 시 본문
    px = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAA"
        "C0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    page.evaluate(
        "(px) => localStorage.setItem('gnsoft.artifacts', JSON.stringify(["
        "{ts:Date.now(),kind:'image',title:'라벨링 · road.png',caption:'라벨 2개 · pothole',image:px},"
        "{ts:Date.now()-5000,kind:'rag',title:'RAG 검색 결과',question:'2026.04.24 포트홀 위치',"
        "answer:'문지로 272 부근 1건(심각 상)',source:'도로파손_탐지로그_2026Q2.csv'}]))",
        px,
    )
    page.reload()
    page.wait_for_selector(".artifact-list .artifact-item")
    # 이미지 자료 썸네일 클릭 → 상세 모달(사진 크게)
    page.click(".artifact-list .artifact-item:has(.artifact-thumb img) .artifact-thumb")
    page.wait_for_selector(".art-modal:not([hidden]) .art-detail")
    check(
        "report: 아티팩트 상세 모달(사진 크게)",
        page.is_visible(".art-modal")
        and page.query_selector(".art-modal .art-image img") is not None,
    )
    page.click(".art-modal .modal-cancel")
    page.wait_for_selector(".art-modal", state="hidden")
    # RAG 자료 추가 → 생성 시 본문 삽입
    page.click(".artifact-list .artifact-item:has(.artifact-ic) .artifact-add")
    page.wait_for_selector(".staged-note:not([hidden])")
    page.click(".report-form .primary")
    page.wait_for_selector(".report-page .report-attachments .report-finding")
    check(
        "report: 내 작업 자료(RAG 도출) 삽입",
        "문지로 272" in page.inner_text(".report-page .report-attachments"),
    )

    # AI 대화 패널(우측 슬라이드) — 본문이 왼쪽으로 밀리고, 보고서 내용 근거로 응답
    page.click(".ai-open")
    page.wait_for_selector(".ai-panel.open")
    check(
        "report: AI 패널 열 때 본문 밀림",
        page.evaluate("() => document.body.classList.contains('ai-pushed')"),
    )
    # 'AI와 대화하기'를 다시 누르면 닫힘(토글)
    page.click(".ai-open")
    page.wait_for_selector(".ai-panel", state="hidden")
    check(
        "report: AI 버튼 토글로 닫힘",
        not page.is_visible(".ai-panel")
        and not page.evaluate("() => document.body.classList.contains('ai-pushed')"),
    )
    page.click(".ai-open")  # 다시 열어 이후 테스트 진행
    page.wait_for_selector(".ai-panel.open")
    page.fill(".ai-chat-input input", "핵심 권고가 뭐야?")
    page.click(".ai-send")
    page.wait_for_function(
        "() => { const b=document.querySelector('.ai-msg.assistant:last-child .ai-bubble'); "
        "return b && !b.querySelector('.ai-typing') && b.innerText.trim().length>0; }",
        timeout=70000,
    )
    check("report: AI 대화 패널", len(page.query_selector_all(".ai-msg.assistant")) >= 2)

    # 화면과 무관한 일반 질문('포트홀이 뭐야?') → 자연어 질의로 연계 안내(라우팅 링크)
    page.fill(".ai-chat-input input", "포트홀이 뭐야?")
    page.click(".ai-send")
    page.wait_for_selector(".ai-chat-log .ai-route")
    route_href = page.get_attribute(".ai-chat-log .ai-route", "href")
    check(
        "report: 일반 질문은 자연어 질의로 연계",
        route_href.startswith("query.html?q="),
        route_href[:28],
    )

    # 대화 기록 영속 — 닫았다 다시 열어도 그대로
    msgs_before = len(page.query_selector_all(".ai-msg"))
    page.click(".ai-panel-close")
    page.wait_for_selector(".ai-panel", state="hidden")
    page.click(".ai-open")
    page.wait_for_selector(".ai-panel.open")
    check(
        "report: 대화 기록 영속(닫았다 켜도 유지)",
        len(page.query_selector_all(".ai-msg")) == msgs_before,
        f"{msgs_before}건",
    )

    # '지우기' → 인사말만 남기고 비움(이때만 기록 변경)
    page.click(".ai-panel-clear")
    page.wait_for_function("() => document.querySelectorAll('.ai-msg').length === 1")
    check("report: 대화 지우기", len(page.query_selector_all(".ai-msg")) == 1)
    page.click(".ai-panel-close")

    # RAG에서 ?q=질문 으로 넘어오면 그 주제로 보고서 생성(기능 연결)
    page.goto(f"{BASE}/pages/report.html?q=" + "포트홀 보수".replace(" ", "%20"))
    page.wait_for_selector(".report-page section [contenteditable='true']", timeout=70000)
    check("report: RAG 질문 연결(?q)", len(page.query_selector_all(".report-page section")) >= 1)

    # 6) Data ─ 목록 + 필터 + 업로드(행추가) + ⋮메뉴 삭제
    page.goto(f"{BASE}/pages/data.html")
    page.wait_for_selector("tbody tr")
    rows = page.query_selector_all("tbody tr")
    check("data: 데이터셋 5행 로드", len(rows) == 5, f"{len(rows)}행")
    page.fill(".search-upload input", "cctv")
    page.wait_for_timeout(200)
    visible = [r for r in page.query_selector_all("tbody tr") if r.is_visible()]
    check("data: 검색 필터 동작", len(visible) == 1, f"{len(visible)}행 표시")
    page.fill(".search-upload input", "")

    # 업로드: 파일 선택 → 표에 행 추가
    before_rows = len(page.query_selector_all("tbody tr"))
    page.set_input_files(
        "input[type=file]",
        files=[{"name": "newset.csv", "mimeType": "text/csv", "buffer": b"a,b,c"}],
    )
    page.wait_for_function(
        "(n) => document.querySelectorAll('tbody tr').length > n", arg=before_rows
    )
    check("data: 업로드 행 추가", len(page.query_selector_all("tbody tr")) == before_rows + 1)

    # ⋮ 메뉴 → 삭제 → 확인 모달에서 한 번 더 묻기
    now_rows = len(page.query_selector_all("tbody tr"))
    page.click("tbody tr:first-child .row-menu")
    page.wait_for_selector(".row-pop:not([hidden])")
    page.click(".row-pop button[data-act='delete']")
    # 바로 지우지 않고 확인 모달이 떠야 함
    page.wait_for_selector(".confirm-modal:not([hidden]) .confirm-delete")
    check(
        "data: 삭제 시 확인 모달",
        page.is_visible(".confirm-modal") and len(page.query_selector_all("tbody tr")) == now_rows,
    )
    # 취소하면 행 유지
    page.click(".confirm-modal .modal-cancel")
    page.wait_for_selector(".confirm-modal", state="hidden")
    check("data: 삭제 취소 시 행 유지", len(page.query_selector_all("tbody tr")) == now_rows)
    # 다시 삭제 → 확인 → 행 제거
    page.click("tbody tr:first-child .row-menu")
    page.wait_for_selector(".row-pop:not([hidden])")
    page.click(".row-pop button[data-act='delete']")
    page.wait_for_selector(".confirm-modal:not([hidden]) .confirm-delete")
    page.click(".confirm-modal .confirm-delete")
    page.wait_for_function(
        "(n) => document.querySelectorAll('tbody tr').length === n - 1", arg=now_rows
    )
    check("data: ⋮ 메뉴 삭제(확인 후)", len(page.query_selector_all("tbody tr")) == now_rows - 1)

    browser.close()

print("\n=== 콘솔/페이지 에러 ===")
print("없음" if not console_errors else "\n".join(f"  - {e}" for e in console_errors))

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== 결과: {passed}/{len(results)} 통과 ===")
sys.exit(0 if passed == len(results) and not console_errors else 1)
