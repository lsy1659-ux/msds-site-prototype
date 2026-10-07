/* 화면을 옮겨도 고른 제품이 따라가게 한다.
 *
 * 조회에서 제품을 보다가 경고표지로 가면 그 제품이 골라져 있었는데,
 * 관리요령으로 가면 전체 목록부터 다시 찾아야 했다. 세 화면(조회·경고표지·
 * 관리요령)의 위쪽 탭 주소에 지금 고른 제품을 실어 보낸다.
 *
 *  - 경고표지·관리요령은 여러 개를 고를 수 있어 모두 싣는다(?product=a,b).
 *  - 조회는 한 제품을 보는 화면이라 하나만 골랐을 때만 싣는다.
 *  - 오프라인 저장 탭(index.html?offline=1)은 건드리지 않는다.
 */
(function (global) {
  "use strict";

  const PAGES = ["index.html", "label.html", "guide.html"];
  const MAX_IDS = 40;

  function currentPage() {
    const name = global.location.pathname.split("/").pop() || "index.html";
    return PAGES.includes(name) ? name : "";
  }

  function requested() {
    const params = new URLSearchParams(global.location.search);
    const ids = params.getAll("product")
      .flatMap((value) => String(value || "").split(","))
      .map((value) => value.trim())
      .filter(Boolean);
    return [...new Set(ids)];
  }

  function carry(ids) {
    const list = [...new Set((ids || []).filter(Boolean))].slice(0, MAX_IDS);
    const here = currentPage();
    document.querySelectorAll("a.top-bar-tab[href], a[data-handoff][href]").forEach((tab) => {
      const href = tab.getAttribute("href") || "";
      const page = href.split("?")[0];
      if (!PAGES.includes(page) || page === here) return;
      if (href.includes("offline=1")) return;
      const send = page === "index.html" ? (list.length === 1 ? list : []) : list;
      tab.setAttribute("href", send.length ? `${page}?product=${send.map(encodeURIComponent).join(",")}` : page);
    });
  }

  global.MsdsHandoff = { requested, carry };
})(window);
