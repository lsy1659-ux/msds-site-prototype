/* 화면 아이콘. 이모지(🌙 👁 ✋ 🫁 ☆)는 기기마다 모양·색이 달라 화면이
 * 들쑥날쑥했다. 선 굵기가 같은 그림 하나로 맞춘다. 색은 글자색을 따른다.
 *
 * GHS 그림문자와 ISO 7010 보호구 표지는 여기 넣지 않는다. 그것들은 원본
 * 그림을 그대로 써야 하는 표지다(assets/ghs, assets/ppe). */
(function (global) {
  "use strict";

  const PATHS = {
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
    hand: '<path d="M7 11V6.5a1.5 1.5 0 0 1 3 0V11M10 10V4.5a1.5 1.5 0 0 1 3 0V10M13 10V5.5a1.5 1.5 0 0 1 3 0V11M16 11V8.5a1.5 1.5 0 0 1 3 0V14a7 7 0 0 1-7 7h-.5a6.5 6.5 0 0 1-5.4-2.9L3.5 14a1.6 1.6 0 0 1 2.6-1.8L7 13.5"/>',
    wind: '<path d="M3 8h11a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7"/>',
    cup: '<path d="M5 4h14l-1.6 14.2A2 2 0 0 1 15.4 20H8.6a2 2 0 0 1-2-1.8z"/><path d="M5.5 9h13"/>',
    medical: '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M12 8v8M8 12h8"/>',
    phone: '<path d="M5 3.5h3.2l1.6 4.3-2.2 1.4a11 11 0 0 0 5.2 5.2l1.4-2.2 4.3 1.6V17a2.5 2.5 0 0 1-2.7 2.5A16 16 0 0 1 2.5 6.2 2.5 2.5 0 0 1 5 3.5z"/>',
    print: '<path d="M7 9V3.5h10V9M7 17H4.5V10a1 1 0 0 1 1-1h13a1 1 0 0 1 1 1v7H17"/><path d="M7 14h10v6.5H7z"/>',
    tag: '<path d="M3.5 12.3V4.5a1 1 0 0 1 1-1h7.8l8.2 8.2a1.5 1.5 0 0 1 0 2.1l-5.8 5.8a1.5 1.5 0 0 1-2.1 0z"/><circle cx="8" cy="8" r="1.5"/>'
  };

  function uiIcon(name, { filled = false } = {}) {
    const body = PATHS[name];
    if (!body) return "";
    const fill = filled ? "currentColor" : "none";
    return `<svg class="ui-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false" fill="${fill}" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
  }

  global.uiIcon = uiIcon;
})(window);
