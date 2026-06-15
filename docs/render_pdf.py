"""HTML → PDF 렌더러 (Microsoft Edge 헤드리스 인쇄 사용).

Windows에 기본 설치된 서명된 Edge를 써서 HTML 파일을 PDF로 뽑는다.
별도 패키지(reportlab/weasyprint) 없이 동작하고, 한글 폰트(맑은 고딕)도 그대로 렌더된다.

사용:
    python docs/render_pdf.py docs/gstack-loop-guide.html
    python docs/render_pdf.py docs/gstack-loop-guide.html docs/원하는이름.pdf
"""

import os
import subprocess
import sys
import tempfile
import time

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge() -> str:
    for path in EDGE_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("[X] Microsoft Edge 를 찾을 수 없습니다.")


def render(html_path: str, pdf_path: str) -> None:
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.exists(html_path):
        raise SystemExit(f"[X] HTML 없음: {html_path}")

    url = "file:///" + html_path.replace("\\", "/")
    user_dir = tempfile.mkdtemp(prefix="edge_pdf_")

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    args = [
        find_edge(),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        f"--user-data-dir={user_dir}",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    subprocess.run(args, timeout=120, check=False)

    # Edge가 파일을 닫는 데 약간의 여유.
    for _ in range(20):
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            break
        time.sleep(0.3)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"[O] PDF 생성 완료: {pdf_path} ({size_kb:,.0f} KB)")
    else:
        raise SystemExit("[X] PDF 생성 실패 — Edge 인쇄가 끝나지 않았거나 차단됐습니다.")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    html = sys.argv[1]
    pdf = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(html)[0] + ".pdf"
    render(html, pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
