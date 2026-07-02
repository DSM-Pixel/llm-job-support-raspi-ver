// 로그인·회원가입 — 필수 동의(이용약관·개인정보) 없으면 가입 불가.
// 성공 시 gnsoft.auth 에 세션 저장 → 프로젝트 선택 화면으로.
(() => {
  const $ = (s) => document.querySelector(s);

  // 이미 로그인돼 있으면 바로 프로젝트 선택으로.
  try {
    if (localStorage.getItem("gnsoft.auth")) {
      location.replace("projects.html");
      return;
    }
  } catch {
    /* 무시 */
  }

  // ── 약관·개인정보 전문 (개인정보보호법 제15조 고지 항목 포함) ──
  const DOCS = {
    terms: {
      title: "서비스 이용약관",
      body: `제1조 (목적)
이 약관은 지엔소프트(주)(이하 "회사")가 제공하는 GNSoft AI 플랫폼(이하 "서비스")의 이용 조건 및 절차, 회사와 회원 간의 권리·의무를 규정함을 목적으로 합니다.

제2조 (정의)
"서비스"란 자연어 질의, 문서 지식 검색, 공공데이터 통계, 이미지 분석·라벨링, 업무 자동화, 보고서 생성 등 회사가 제공하는 일체의 기능을 말합니다. "회원"이란 본 약관에 동의하고 계정을 등록한 자를 말합니다.

제3조 (약관의 효력과 변경)
회사는 약관을 변경할 수 있으며, 변경 시 적용일 7일 전부터 서비스 내 공지합니다. 회원이 변경 약관에 동의하지 않는 경우 탈퇴할 수 있습니다.

제4조 (서비스의 제공과 중단)
회사는 시스템 점검·장애 등 부득이한 경우 서비스 제공을 일시 중단할 수 있으며, 사전 또는 사후에 공지합니다. 본 서비스는 프로젝트형 일경험 데모 플랫폼으로, AI가 생성한 결과(분석·라벨·보고서)는 참고용이며 정확성을 보증하지 않습니다.

제5조 (회원의 의무)
회원은 타인의 정보 도용, 서비스의 부정 이용, 개인정보(차량번호·얼굴 등)가 포함된 데이터의 무단 업로드를 해서는 안 됩니다. 업로드 데이터의 권리·라이선스 책임은 회원에게 있습니다.

제6조 (지식재산권)
서비스와 그 구성요소에 대한 권리는 회사에 있으며, 회원이 업로드한 데이터의 권리는 회원에게 있습니다.

제7조 (면책)
회사는 천재지변, 회원의 귀책사유로 인한 손해에 대해 책임지지 않습니다.

제8조 (준거법)
본 약관은 대한민국 법률에 따라 해석됩니다.`,
    },
    privacy: {
      title: "개인정보 수집·이용 동의",
      body: `지엔소프트(주)는 「개인정보 보호법」 제15조에 따라 아래와 같이 개인정보를 수집·이용합니다.

1. 수집 항목
- (필수) 이메일 주소, 이름, 비밀번호(암호화하여 저장)
- (선택) 회사·기관명, 부서·직함

2. 수집·이용 목적
- 회원 식별 및 로그인 등 서비스 제공
- 프로젝트·작업 기록의 계정 연결
- 문의 대응 및 공지 전달

3. 보유·이용 기간
- 회원 탈퇴 시 지체 없이 파기합니다.
- 단, 관계 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다.

4. 제3자 제공
- 수집한 개인정보를 제3자에게 제공하지 않습니다.

5. 동의 거부 권리 및 불이익
- 귀하는 개인정보 수집·이용에 동의하지 않을 권리가 있습니다.
- 다만 필수 항목 동의를 거부할 경우 회원가입 및 서비스 이용이 제한됩니다.

6. 개인정보 처리 위탁
- 서비스 운영을 위한 처리 위탁이 발생할 경우 사전 고지합니다.

문의: 지엔소프트(주) 개인정보 보호책임자 (대전 유성구 문지로 272-16 AI인공지능센터)`,
    },
  };

  // ── 간단 토스트(이 페이지는 common.js 미포함) ──
  const toast = (msg) => {
    let el = $(".toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(el.timer);
    el.timer = setTimeout(() => el.classList.remove("show"), 2200);
  };

  const api = async (path, body) => {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  // ── 성공 처리: 세션 저장 + 프로필 설정 동기화 → 프로젝트 선택 ──
  const enter = (data) => {
    try {
      localStorage.setItem(
        "gnsoft.auth",
        JSON.stringify({ token: data.token, ...data.user }),
      );
      // 사이드바 프로필(이름·소속)을 계정 정보로 동기화.
      const s = JSON.parse(localStorage.getItem("gnsoft.settings") || "{}");
      s.name = data.user.name;
      s.team = [data.user.company, data.user.team].filter(Boolean).join(" · ");
      localStorage.setItem("gnsoft.settings", JSON.stringify(s));
    } catch {
      /* 무시 */
    }
    location.replace("projects.html");
  };

  // ── 탭 전환 ──
  const showTab = (tab) => {
    document.querySelectorAll(".lg-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
    document.querySelectorAll(".lg-form").forEach((f) => (f.hidden = f.dataset.form !== tab));
  };
  document.querySelectorAll(".lg-tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
  document.querySelectorAll(".lg-switch").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.to)));

  // ── 동의 체크(전체 동의 연동) ──
  const consents = () => [...document.querySelectorAll('[data-consent]:not([data-consent="all"])')];
  const allBox = $('[data-consent="all"]');
  allBox?.addEventListener("change", () => {
    consents().forEach((c) => (c.checked = allBox.checked));
  });
  consents().forEach((c) =>
    c.addEventListener("change", () => {
      allBox.checked = consents().every((x) => x.checked);
    }),
  );

  // ── 약관 전문 모달 ──
  const docModal = $("#doc-modal");
  let curDoc = null;
  document.querySelectorAll(".lg-view").forEach((b) =>
    b.addEventListener("click", () => {
      curDoc = b.dataset.doc;
      docModal.querySelector(".doc-title").textContent = DOCS[curDoc].title;
      docModal.querySelector(".doc-body").textContent = DOCS[curDoc].body;
      docModal.hidden = false;
    }),
  );
  docModal.querySelector(".modal-close").addEventListener("click", () => (docModal.hidden = true));
  docModal.addEventListener("click", (e) => {
    if (e.target === docModal) docModal.hidden = true;
  });
  docModal.querySelector(".doc-agree").addEventListener("click", () => {
    const cb = document.querySelector(`[data-consent="${curDoc}"]`);
    if (cb) {
      cb.checked = true;
      cb.dispatchEvent(new Event("change"));
    }
    docModal.hidden = true;
  });

  // ── 로그인 ──
  $('[data-form="login"]').addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    try {
      const r = await api("/api/auth/login", {
        email: f.email.value.trim(),
        password: f.password.value,
      });
      if (!r.ok) return toast(r.error || "로그인에 실패했습니다");
      enter(r);
    } catch {
      toast("서버 연결에 실패했습니다");
    }
  });

  // ── 회원가입 ──
  $('[data-form="signup"]').addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    if (f.password.value !== f.password2.value) return toast("비밀번호가 서로 다릅니다");
    const agree = (k) => document.querySelector(`[data-consent="${k}"]`).checked;
    if (!agree("terms") || !agree("privacy")) {
      return toast("필수 약관(이용약관·개인정보 수집이용)에 동의해주세요");
    }
    try {
      const r = await api("/api/auth/signup", {
        email: f.email.value.trim(),
        password: f.password.value,
        name: f.name.value.trim(),
        company: f.company.value.trim(),
        team: f.team.value.trim(),
        agree_terms: agree("terms"),
        agree_privacy: agree("privacy"),
        agree_marketing: agree("marketing"),
      });
      if (!r.ok) return toast(r.error || "가입에 실패했습니다");
      toast("가입 완료! 프로젝트 선택으로 이동합니다");
      setTimeout(() => enter(r), 400);
    } catch {
      toast("서버 연결에 실패했습니다");
    }
  });
})();
