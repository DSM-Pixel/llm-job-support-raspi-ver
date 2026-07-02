// 비밀번호 재설정 — 이메일 링크(?token=...)로 진입해 새 비밀번호를 설정한다.
(() => {
  const $ = (s) => document.querySelector(s);
  const form = $('[data-form="reset-confirm"]');
  const token = new URLSearchParams(location.search).get("token") || "";

  const alertIn = (msg, ok = false) => {
    const el = form.querySelector(".lg-alert");
    el.textContent = msg;
    el.classList.toggle("ok", ok);
    el.hidden = false;
  };

  // 토큰이 없으면 곧바로 안내하고 입력을 막는다.
  if (!token) {
    alertIn("유효하지 않은 접근입니다. 비밀번호 찾기를 다시 요청해주세요.");
    form.querySelectorAll("input, button").forEach((el) => (el.disabled = true));
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    if (f.password.value !== f.password2.value) return alertIn("비밀번호가 서로 다릅니다");
    try {
      const res = await fetch("/api/auth/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password: f.password.value }),
      });
      const r = await res.json();
      if (!r.ok) return alertIn(r.error || "재설정에 실패했습니다");
      alertIn(r.message || "비밀번호가 변경되었습니다. 로그인 화면으로 이동합니다.", true);
      setTimeout(() => location.replace("login.html"), 900);
    } catch {
      alertIn("서버 연결에 실패했습니다");
    }
  });
})();
