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
  const MAX_QUERY_LENGTH = 1800;
  const STORAGE_PREFIX = "msds.handoff.v1.";
  let lastStored = null;

  function uniqueIds(ids) {
    return [...new Set((ids || []).filter(id => typeof id === "string").map(id => id.trim()).filter(Boolean))];
  }

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
    const token = params.get("selection") || "";
    if (/^[a-z0-9-]{1,80}$/i.test(token)) {
      try {
        const stored = JSON.parse(global.sessionStorage.getItem(STORAGE_PREFIX + token) || "null");
        if (Array.isArray(stored)) ids.push(...uniqueIds(stored));
      } catch (error) { /* 저장소가 없거나 잘못된 기록이면 직접 전달된 ID를 유지한다. */ }
    }
    return uniqueIds(ids);
  }

  function carry(ids) {
    const list = uniqueIds(ids);
    const query = `product=${list.map(encodeURIComponent).join(",")}`;
    let token = "";
    if (query.length > MAX_QUERY_LENGTH) {
      try {
        const signature = JSON.stringify(list);
        if (lastStored?.signature === signature && global.sessionStorage.getItem(STORAGE_PREFIX + lastStored.token) === signature) {
          token = lastStored.token;
        } else {
          token = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
          global.sessionStorage.setItem(STORAGE_PREFIX + token, signature);
          // 쓰기가 허용된 것처럼 보여도 저장되지 않는 브라우저가 있다.
          if (global.sessionStorage.getItem(STORAGE_PREFIX + token) !== signature) throw new Error("selection storage unavailable");
          lastStored = {signature, token};
        }
      } catch (error) { token = ""; /* 전체 URL로 넘긴다. 저장소 실패를 이유로 선택을 자르지 않는다. */ }
    }
    const here = currentPage();
    document.querySelectorAll("a.top-bar-tab[href], a[data-handoff][href]").forEach((tab) => {
      const href = tab.getAttribute("href") || "";
      const page = href.split("?")[0];
      if (!PAGES.includes(page) || page === here) return;
      if (href.includes("offline=1")) return;
      const send = page === "index.html" ? (list.length === 1 ? list : []) : list;
      const mode = new URLSearchParams(global.location.search).get("dataMode");
      const query = send.length ? (send.length > 1 && token ? `selection=${encodeURIComponent(token)}` : `product=${send.map(encodeURIComponent).join(",")}`) : "";
      const next = [query, mode === "public" ? "dataMode=public" : ""].filter(Boolean).join("&");
      tab.setAttribute("href", next ? `${page}?${next}` : page);
    });
  }

  global.MsdsHandoff = { requested, carry };
})(window);
