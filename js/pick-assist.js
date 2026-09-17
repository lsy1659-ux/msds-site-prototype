/* 제품 찾기 칸 아래에 뜨는 연관 검색.
 *
 * 227건에서 이름을 정확히 쳐 넣기는 어렵다. 몇 글자만 치면 걸리는
 * 제품을 밑에 띄워 고르게 한다. 조회 화면에 있는 것과 같은 방식이다.
 *
 * 경고표지와 관리요령이 함께 쓴다. 두 화면의 상태 모양이 달라서
 * 목록을 가져오는 방법과 골랐을 때 할 일만 밖에서 받는다.
 */

(function () {
  "use strict";

  const LIMIT = 8;

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  window.attachPickAssist = function attachPickAssist({ input, getProducts, onPick }) {
    if (!input || typeof getProducts !== "function") return;

    const box = document.createElement("div");
    box.className = "pick-assist";
    box.setAttribute("role", "listbox");
    box.hidden = true;

    // 칸 바로 아래에 띄운다. 칸을 감싸는 label 이 기준이 된다.
    const anchor = input.closest("label") || input.parentElement;
    anchor.classList.add("pick-assist-anchor");
    anchor.appendChild(box);

    let matches = [];
    let active = -1;

    function close() {
      box.hidden = true;
      active = -1;
    }

    function draw() {
      const needle = normalize(input.value);
      matches = [];
      if (needle.length >= 1) {
        const seen = new Set();
        for (const product of getProducts()) {
          const name = String(product.productName || "");
          const hay = normalize([name, product.supplier, product.msdsNo].join(" "));
          if (!hay.includes(needle) || seen.has(name)) continue;
          seen.add(name);
          matches.push(product);
          if (matches.length >= LIMIT) break;
        }
      }
      if (!matches.length) return close();

      box.innerHTML = matches.map((product, index) => `
        <button type="button" class="pick-assist-item" role="option"
          aria-selected="${index === active}" data-pick-index="${index}">
          <span>${escapeHtml(product.productName)}</span>
          <b>${escapeHtml(product.supplier || "")}</b>
        </button>`).join("");
      box.hidden = false;
    }

    function choose(index) {
      const product = matches[index];
      if (!product) return;
      input.value = product.productName;
      close();
      onPick(product);
    }

    input.addEventListener("input", draw);
    input.addEventListener("focus", draw);

    input.addEventListener("keydown", (event) => {
      if (box.hidden) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        active = event.key === "ArrowDown"
          ? Math.min(active + 1, matches.length - 1)
          : Math.max(active - 1, 0);
        box.querySelectorAll(".pick-assist-item").forEach((item, index) => {
          item.classList.toggle("is-active", index === active);
          item.setAttribute("aria-selected", String(index === active));
        });
        return;
      }
      if (event.key === "Enter" && active >= 0) {
        event.preventDefault();
        choose(active);
        return;
      }
      if (event.key === "Escape") close();
    });

    box.addEventListener("mousedown", (event) => {
      const item = event.target.closest("[data-pick-index]");
      if (!item) return;
      event.preventDefault();   // 칸에서 초점이 빠지기 전에 고른다.
      choose(Number(item.dataset.pickIndex));
    });

    document.addEventListener("click", (event) => {
      if (!anchor.contains(event.target)) close();
    });
  };
})();
