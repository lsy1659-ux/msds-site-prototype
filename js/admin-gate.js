/* 관리자 화면 가림막.
 *
 * 먼저 분명히 해 둔다. 이것은 잠금이 아니라 가림막이다.
 *
 * 이 사이트는 GitHub Pages 정적 사이트라 서버가 없다. 암호를 확인해 줄
 * 곳이 없어서 확인하는 코드가 이 파일 안에 들어가고, 저장소가 공개라
 * 그 코드는 누구나 읽을 수 있다. 브라우저 개발자 도구로 저장값을 직접
 * 바꾸는 것도 막을 수 없다. 암호를 그대로 적지 않고 해시만 두는 것은
 * 어깨너머로 보이는 것을 줄일 뿐, 작정한 사람을 막지는 못한다.
 *
 * 그러면 왜 두는가. 이 사이트를 실제로 쓰는 사람은 현장에서 QR 을 찍는
 * 작업자다. 그 사람에게 물질 대장이나 PDF 검토 화면은 쓸 일이 없고,
 * 탭에 있으면 헷갈리기만 한다. 담당자만 쓰는 화면을 평소에 접어 두는
 * 것이 목적이다.
 *
 * 그러니 여기 뒤에는 감춰서 아쉬운 것만 둔다. 새어 나가면 안 되는 것은
 * 애초에 이 사이트에 올리지 않는다.
 */

(function () {
  "use strict";

  const FLAG = "msds.admin.v1";

  /* 암호의 SHA-256 값. 암호 자체는 여기에 적지 않는다. 저장소가 공개라
   * 평문으로 적으면 가림막 구실조차 못 한다.
   *
   * 바꾸려면 아래 한 줄을 돌린다. PASS_HASH 만 갈아 끼워 준다.
   *   py scripts/set_admin_passcode.py "새암호"
   */
  const PASS_HASH = "8c420cf6567aba1df07da50e0955c1e2132769b5b8c1cf51abc3754f7f8236c8";

  // 관리자만 쓰는 화면들. 여기 적으면 관리자 패널에 줄이 하나 생긴다.
  const ADMIN_PAGES = [
    { href: "substance.html", name: "물질 찾기", note: "CAS 로 묶어 어느 물질이 어느 제품에 들었는지 봅니다" },
    { href: "review.html", name: "PDF 추출 후보 검토", note: "PDF 에서 뽑은 요약 후보를 확인합니다" },
    { href: "pdf-queue.html", name: "PDF 미등록 자료 검토", note: "아직 제품에 붙지 않은 PDF 를 봅니다" }
  ];

  function isAdmin() {
    try {
      return window.localStorage.getItem(FLAG) === "on";
    } catch (error) {
      return false;   // 저장소가 막힌 환경
    }
  }

  function applyAdminState(on) {
    document.documentElement.setAttribute("data-admin", on ? "on" : "off");
  }

  function setAdmin(on) {
    try {
      if (on) window.localStorage.setItem(FLAG, "on");
      else window.localStorage.removeItem(FLAG);
    } catch (error) {
      // 저장이 막히면 이번 화면에서만 열린다.
    }
    applyAdminState(on);
  }

  async function matches(code) {
    const text = String(code || "").trim();
    if (!text) return false;
    if (!window.crypto?.subtle) return false;
    const bytes = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    const hex = [...new Uint8Array(bytes)].map((n) => n.toString(16).padStart(2, "0")).join("");
    return hex === PASS_HASH;
  }

  function panelMarkup() {
    const links = ADMIN_PAGES.map((page) => `
      <a class="admin-link" href="${page.href}">
        <strong>${page.name}</strong>
        <span>${page.note}</span>
      </a>`).join("");

    // 위쪽 패널과 감춘 화면 두 군데에 같은 꼴이 들어간다. id 를 쓰면
    // 문서에 같은 id 가 둘이 되므로 이름표가 입력칸을 감싸게 한다.
    return `
      <form class="admin-form" data-admin-locked>
        <label class="admin-code-label">
          <span>관리자 암호</span>
          <input class="admin-code" type="password" autocomplete="current-password" placeholder="암호">
        </label>
        <button type="submit">들어가기</button>
        <p class="admin-note" data-admin-message role="status" aria-live="polite">
          담당자만 쓰는 화면을 열어 둡니다. 현장 조회에는 필요하지 않습니다.
        </p>
      </form>
      <div class="admin-open" data-admin-only>
        <strong class="admin-open-title">관리자 화면</strong>
        ${links}
        <button type="button" class="admin-logout" data-admin-logout>관리자 모드 끄기</button>
      </div>`;
  }

  function wire(root) {
    const form = root.querySelector(".admin-form");
    const input = root.querySelector(".admin-code");
    const message = root.querySelector("[data-admin-message]");

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (await matches(input.value)) {
        setAdmin(true);
        input.value = "";
        if (message) message.textContent = "관리자 화면을 열었습니다.";
        document.dispatchEvent(new CustomEvent("msds:admin-changed", { detail: { on: true } }));
        return;
      }
      if (message) {
        message.textContent = window.crypto?.subtle
          ? "암호가 맞지 않습니다."
          : "이 브라우저에서는 암호를 확인할 수 없습니다. 주소가 https 인지 확인하세요.";
      }
      input.select();
    });

    root.querySelector("[data-admin-logout]")?.addEventListener("click", () => {
      setAdmin(false);
      if (message) message.textContent = "관리자 모드를 껐습니다.";
      document.dispatchEvent(new CustomEvent("msds:admin-changed", { detail: { on: false } }));
    });
  }

  function init() {
    applyAdminState(isAdmin());

    const button = document.querySelector("#adminButton");
    const panel = document.querySelector("#adminPanel");
    if (panel) {
      panel.innerHTML = panelMarkup();
      wire(panel);
    }

    button?.addEventListener("click", () => {
      const open = panel.hasAttribute("hidden");
      panel.toggleAttribute("hidden", !open);
      button.setAttribute("aria-expanded", String(open));
      if (open) panel.querySelector(".admin-code")?.focus();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && panel && !panel.hasAttribute("hidden")) {
        panel.setAttribute("hidden", "");
        button?.setAttribute("aria-expanded", "false");
      }
    });

    // 관리자 전용 화면을 주소로 바로 열었을 때 그 자리에서 풀 수 있게 한다.
    const gate = document.querySelector("#adminGate");
    if (gate) {
      gate.innerHTML = panelMarkup();
      wire(gate);
    }
  }

  window.msdsIsAdmin = isAdmin;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
