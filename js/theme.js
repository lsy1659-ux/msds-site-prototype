/* 밝은 화면 / 어두운 화면.
 *
 * 상단 바를 세 화면이 같이 쓰게 되면서 이 버튼도 세 화면에 다 있다.
 * 그래서 조회 화면 코드에서 떼어내 따로 뒀다.
 *
 * 고른 값은 이 기기에만 저장하고, 고른 적이 없으면 기기 설정을 따른다.
 * 첫 화면이 번쩍이지 않도록 저장값을 적용하는 일은 각 페이지 <head>
 * 안에서 먼저 한 번 한다. 여기서는 버튼 표시와 누름 처리를 맡는다.
 */

(function () {
  "use strict";

  const THEME_KEY = "msds.theme.v1";

  function readStoredTheme() {
    try {
      const value = window.localStorage.getItem(THEME_KEY);
      return value === "dark" || value === "light" ? value : "";
    } catch (error) {
      return "";
    }
  }

  function storeTheme(value) {
    try {
      window.localStorage.setItem(THEME_KEY, value);
    } catch (error) {
      // 저장이 막힌 환경에서는 이번 방문에만 적용된다.
    }
  }

  function prefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function applyTheme(theme) {
    const dark = theme === "dark";
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.querySelectorAll(".theme-toggle").forEach((button) => {
      button.setAttribute("aria-pressed", String(dark));
      const icon = button.querySelector(".theme-toggle-icon");
      const label = button.querySelector(".theme-toggle-label");
      if (icon) icon.textContent = dark ? "☀" : "🌙";
      if (label) label.textContent = dark ? "밝은 화면" : "어두운 화면";
      button.title = dark ? "밝은 화면으로 바꾸기" : "어두운 화면으로 바꾸기";
    });
  }

  // 버튼에 직접 걸지 않고 문서에서 받는다. 버튼이 다시 그려져도,
  // 다른 초기화가 실패해도 화면 전환은 계속 눌린다.
  document.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest(".theme-toggle") : null;
    if (!button) return;
    event.preventDefault();
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    storeTheme(next);
    applyTheme(next);
  });

  // 고른 적이 없을 때만 기기 설정 변화를 따라간다.
  window.matchMedia?.("(prefers-color-scheme: dark)")?.addEventListener?.("change", (event) => {
    if (readStoredTheme()) return;
    applyTheme(event.matches ? "dark" : "light");
  });

  applyTheme(readStoredTheme() || (prefersDark() ? "dark" : "light"));
})();
