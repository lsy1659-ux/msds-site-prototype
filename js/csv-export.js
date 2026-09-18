/* 화면에 보이는 목록을 엑셀로 빼기.
 *
 * 점검 나왔을 때 "보유 화학물질 목록 주세요" 하면 바로 줄 수 있어야 한다.
 * 조회 화면과 물질 화면이 같이 쓴다.
 *
 * 엑셀 때문에 두 가지를 지킨다.
 *
 *  - 맨 앞에 BOM 을 붙인다. 안 붙이면 한글이 ê°€ë‚˜ë‹¤ 로 깨진다.
 *  - = + - @ 로 시작하는 값 앞에 작은따옴표를 넣는다. 그냥 두면 엑셀이
 *    수식으로 실행한다. 물질명에 그런 게 올 일은 드물지만, 남이 만든
 *    MSDS 에서 긁어 온 값이라 무엇이 들어 있을지 장담할 수 없다.
 */

(function () {
  "use strict";

  // 엑셀이 수식으로 읽는 첫 글자. 탭과 캐리지리턴도 같은 구멍이다.
  const FORMULA_START = /^[=+\-@\t\r]/;

  function cell(value) {
    let text = value === null || value === undefined ? "" : String(value);
    if (FORMULA_START.test(text)) text = `'${text}`;
    if (/[",\r\n]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
    return text;
  }

  function toCsv(header, rows) {
    return [header, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
  }

  window.downloadCsv = function downloadCsv(fileName, header, rows) {
    // ﻿ 가 BOM 이다. 이게 있어야 엑셀이 UTF-8 로 읽는다.
    const blob = new Blob(["﻿" + toCsv(header, rows)], {
      type: "text/csv;charset=utf-8;"
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // 바로 지우면 사파리에서 내려받기가 끊긴다.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  window.csvStamp = function csvStamp() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  };
})();
