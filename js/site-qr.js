/* 지금 보는 화면을 QR 로 보여 주기.
 *
 * 옆 사람에게 주소를 불러 주거나 메신저로 보내기가 번거롭다. 화면에
 * QR 을 띄워 폰으로 찍게 하면 바로 같은 화면이 열린다.
 *
 * 가리키는 주소는 "지금 보고 있는 주소"다. 제품을 보다가 띄우면 그
 * 제품 화면이 열린다. 아무것도 안 고른 상태면 첫 화면이 열린다.
 */

(function () {
  "use strict";

  const button = document.querySelector("#siteQrButton");
  const panel = document.querySelector("#siteQrPanel");
  const holder = document.querySelector("#siteQrCode");
  const urlBox = document.querySelector("#siteQrUrl");
  const note = document.querySelector("#siteQrNote");
  const copyButton = document.querySelector("#siteQrCopy");
  if (!button || !panel || !holder) return;

  let shownUrl = "";

  // 이 PC 안에서만 통하는 주소는 옆 사람 폰으로 열리지 않는다.
  function isLocalOnly() {
    const host = window.location.hostname;
    return !host || host === "localhost" || host === "127.0.0.1" || host.endsWith(".local");
  }

  function draw() {
    const url = window.location.href;
    if (url === shownUrl) return;
    shownUrl = url;

    if (urlBox) urlBox.textContent = url;
    if (note) {
      note.textContent = isLocalOnly()
        ? "지금 주소는 이 PC 안에서만 열립니다. 배포된 주소에서 띄워야 옆 사람 폰에서 열립니다."
        : "옆 사람이 폰 카메라로 찍으면 지금 보는 화면이 그대로 열립니다.";
      note.classList.toggle("is-warning", isLocalOnly());
    }

    if (typeof qrcode !== "function") {
      holder.innerHTML = '<p class="site-qr-fail">QR을 만들지 못했습니다. 아래 주소를 알려 주세요.</p>';
      return;
    }
    try {
      // 주소가 길어지면 자동으로 촘촘한 판을 쓰도록 0 을 넘긴다.
      const code = qrcode(0, "M");
      code.addData(url);
      code.make();
      holder.innerHTML = code.createSvgTag({ cellSize: 6, margin: 1, scalable: true });
    } catch (error) {
      holder.innerHTML = '<p class="site-qr-fail">주소가 너무 길어 QR로 담지 못했습니다.</p>';
    }
  }

  function setOpen(open) {
    panel.toggleAttribute("hidden", !open);
    button.setAttribute("aria-expanded", String(open));
    if (open) draw();
  }

  button.addEventListener("click", () => setOpen(panel.hasAttribute("hidden")));

  // 열어 둔 채로 다른 제품을 고르면 주소가 바뀐다. 그때마다 다시 그린다.
  window.addEventListener("popstate", () => { if (!panel.hasAttribute("hidden")) draw(); });
  window.setInterval(() => { if (!panel.hasAttribute("hidden")) draw(); }, 700);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hasAttribute("hidden")) setOpen(false);
  });

  copyButton?.addEventListener("click", async () => {
    const value = window.location.href;
    const show = (message) => {
      copyButton.textContent = message;
      window.setTimeout(() => { copyButton.textContent = "주소 복사"; }, 1600);
    };
    try {
      await navigator.clipboard.writeText(value);
      show("복사됨");
      return;
    } catch (error) {
      // 복사가 막힌 환경에서는 골라 긁을 수 있게 띄운다.
    }
    show("직접 복사");
    window.prompt("이 주소를 복사하세요", value);
  });
})();
