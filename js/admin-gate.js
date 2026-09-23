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
  const PASS_HASH = "87bfeb70978b771de19d46f2d208cb7700a4e274d9accacd41710637ac097a4e";

  // 이 파일을 GitHub 에서 바로 여는 주소. 암호를 바꿀 때 열어 준다.
  const EDIT_URL = "https://github.com/lsy1659-ux/msds-site-prototype/edit/main/js/admin-gate.js";

  // 관리자만 쓰는 화면들. 여기 적으면 관리자 패널에 줄이 하나 생긴다.
  const ADMIN_PAGES = [
    { href: "register.html", name: "MSDS 번호 관리대장", note: "번호가 있어야 하는지, 없어도 되는지, 무엇을 더 받아야 하는지 봅니다" },
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
    if (!text || !window.crypto?.subtle) return false;
    return (await sha256(text)) === PASS_HASH;
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
        <div class="admin-buttons">
          <button type="button" class="admin-change" data-admin-change>암호 바꾸기</button>
          <button type="button" class="admin-logout" data-admin-logout>관리자 모드 끄기</button>
        </div>
        ${changeMarkup()}
      </div>`;
  }

  /* 암호 바꾸기.
   *
   * 서버가 없어서 이 단추가 사이트 파일을 고치지는 못한다. 브라우저가
   * 남의 서버에 있는 파일을 쓸 수는 없다. 그래서 손으로 하던 일 가운데
   * 기계가 할 수 있는 것만 맡는다. 해시를 만들고, 넣을 줄을 통째로
   * 보여 주고, 그 파일의 편집 화면까지 열어 준다. 남는 일은 붙여 넣고
   * 저장하는 것뿐이다.
   *
   * 새 암호는 아무 데도 저장하지 않는다. 해시를 만드는 그 순간에만 쓴다.
   */
  function changeMarkup() {
    return `
      <div class="admin-change-box" data-admin-change-box hidden>
        <form class="admin-change-form">
          <label class="admin-code-label">
            <span>새 암호 (여섯 글자 이상)</span>
            <input class="admin-new-code" type="password" autocomplete="new-password" placeholder="새 암호">
          </label>
          <button type="submit">넣을 줄 만들기</button>
        </form>
        <p class="admin-note">
          이 단추는 사이트 파일을 직접 고치지 못합니다. 서버가 없는 사이트라
          그렇습니다. 아래 줄을 파일에 넣어야 바뀝니다. 새 암호는 아무 데도
          저장하지 않고 해시를 만드는 데만 씁니다.
        </p>
        <div class="admin-result" data-admin-result hidden>
          <code class="admin-line" data-admin-line></code>
          <div class="admin-buttons">
            <button type="button" data-admin-copy>줄 복사</button>
            <a class="admin-edit-link" data-admin-edit target="_blank" rel="noopener noreferrer">GitHub 에서 이 파일 열기</a>
          </div>
          <p class="admin-note">
            연 화면에서 <strong>31번째 줄</strong>을 지우고 복사한 줄을 붙여 넣은 뒤
            <strong>Commit changes</strong> 를 누르면 끝입니다. 1~2분 뒤 새 암호로 열립니다.
          </p>
          <p class="admin-note">
            터미널이 편하시면 이 한 줄이 더 빠릅니다. 판 번호까지 같이 올려 줍니다.
            <code class="admin-line">py scripts/set_admin_passcode.py "새암호"</code>
          </p>
        </div>
      </div>`;
  }

  async function sha256(text) {
    const bytes = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(bytes)].map((n) => n.toString(16).padStart(2, "0")).join("");
  }

  function wireChange(root) {
    const box = root.querySelector("[data-admin-change-box]");
    const toggle = root.querySelector("[data-admin-change]");
    if (!box || !toggle) return;

    toggle.addEventListener("click", () => {
      const open = box.hasAttribute("hidden");
      box.toggleAttribute("hidden", !open);
      if (open) box.querySelector(".admin-new-code")?.focus();
    });

    const result = box.querySelector("[data-admin-result]");
    const line = box.querySelector("[data-admin-line]");
    const copy = box.querySelector("[data-admin-copy]");
    const edit = box.querySelector("[data-admin-edit]");

    box.querySelector(".admin-change-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const field = box.querySelector(".admin-new-code");
      const code = field.value;
      if (code.trim().length < 6) {
        window.alert("암호가 너무 짧습니다. 여섯 글자 이상으로 하세요.");
        field.select();
        return;
      }
      if (!window.crypto?.subtle) {
        window.alert("이 브라우저에서는 해시를 만들 수 없습니다. 주소가 https 인지 확인하세요.");
        return;
      }
      line.textContent = `  const PASS_HASH = "${await sha256(code)}";`;
      edit.href = EDIT_URL;
      result.hidden = false;
      field.value = "";   // 화면에 남겨 둘 까닭이 없다.
    });

    copy?.addEventListener("click", async () => {
      const show = (text) => {
        copy.textContent = text;
        window.setTimeout(() => { copy.textContent = "줄 복사"; }, 1600);
      };
      try {
        await navigator.clipboard.writeText(line.textContent);
        show("복사됨");
      } catch (error) {
        show("직접 복사");
        window.prompt("이 줄을 복사하세요", line.textContent);
      }
    });
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

    wireChange(root);

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
