/* MSDS 제품별 QR 코드 만들기 화면.
 * 조회 화면과 같은 공개 데이터를 읽어, 제품마다 ?product=<id> 링크를 QR로 만든다.
 * 인쇄용 화면이라 조회 화면(js/app.js)과는 상태를 공유하지 않는다.
 */

const QR_DATA_SOURCES = [
  "data/msds.local.json",
  "data/msds.public.json",
  "data/msds-sample.json"
];

const qrState = {
  products: [],
  filtered: [],
  selected: new Set(),
  query: ""
};

const qrElements = {};

function qrNormalize(value) {
  return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
}

function qrEscape(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function qrCoerceList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.products)) return payload.products;
  return [];
}

async function loadQrProducts() {
  for (const source of QR_DATA_SOURCES) {
    try {
      const response = await fetch(source, { cache: "no-cache" });
      if (!response.ok) continue;
      const items = qrCoerceList(await response.json());
      if (items.length) return items;
    } catch (error) {
      // 다음 후보 파일로 넘어간다.
    }
  }
  return [];
}

// 스캔했을 때 열릴 주소. 이 페이지가 올라가 있는 위치를 기준으로 만든다.
function buildProductUrl(productId) {
  const base = new URL(".", window.location.href);
  base.searchParams.set("product", productId);
  return base.toString();
}

function getProductSubtitle(product) {
  return [product.supplier, product.category || product.useCategory]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(" · ");
}

function applyQrFilter() {
  const needle = qrNormalize(qrState.query);
  qrState.filtered = !needle
    ? [...qrState.products]
    : qrState.products.filter((product) => qrNormalize([
        product.productName,
        product.erpName,
        product.supplier,
        product.category,
        product.useCategory,
        product.msdsNo
      ].join(" ")).includes(needle));
}

function renderQrSheet() {
  const sheet = qrElements.sheet;
  if (!sheet) return;

  if (!qrState.filtered.length) {
    sheet.innerHTML = '<p class="qr-empty">조건에 맞는 제품이 없습니다.</p>';
    updateQrStatus();
    return;
  }

  sheet.innerHTML = qrState.filtered.map((product) => {
    const checked = qrState.selected.has(product.id);
    const subtitle = getProductSubtitle(product);
    return `<article class="qr-card${checked ? " is-selected" : ""}" data-qr-id="${qrEscape(product.id)}">
        <label class="qr-card-pick no-print">
          <input type="checkbox" data-qr-check="${qrEscape(product.id)}"${checked ? " checked" : ""}>
          <span>인쇄 선택</span>
        </label>
        <div class="qr-card-image" data-qr-slot="${qrEscape(product.id)}"></div>
        <h2 class="qr-card-name">${qrEscape(product.productName)}</h2>
        ${subtitle ? `<p class="qr-card-sub">${qrEscape(subtitle)}</p>` : ""}
        <p class="qr-card-note">스캔하면 MSDS가 열립니다</p>
      </article>`;
  }).join("");

  qrState.filtered.forEach((product) => {
    const slot = sheet.querySelector(`[data-qr-slot="${CSS.escape(product.id)}"]`);
    if (!slot) return;
    try {
      // 타입 0 = 내용 길이에 맞춰 자동 선택, M = 25% 오염까지 복원.
      const code = qrcode(0, "M");
      code.addData(buildProductUrl(product.id));
      code.make();
      slot.innerHTML = code.createSvgTag({ scalable: true, margin: 0 });
    } catch (error) {
      slot.innerHTML = '<span class="qr-card-error">QR 생성 실패</span>';
    }
  });

  updateQrStatus();
}

function updateQrStatus() {
  if (!qrElements.status) return;
  const total = qrState.products.length;
  const shown = qrState.filtered.length;
  const picked = qrState.selected.size;
  qrElements.status.textContent = picked
    ? `전체 ${total}건 중 ${shown}건 표시 · ${picked}건 선택됨`
    : `전체 ${total}건 중 ${shown}건 표시 · 선택 없음(보이는 전체가 인쇄됩니다)`;
}

function syncPrintSelection() {
  const hasSelection = qrState.selected.size > 0;
  qrElements.sheet?.classList.toggle("has-selection", hasSelection);
  qrElements.sheet?.querySelectorAll("[data-qr-id]").forEach((card) => {
    card.classList.toggle("is-selected", qrState.selected.has(card.dataset.qrId));
  });
  updateQrStatus();
}

function bindQrEvents() {
  qrElements.search?.addEventListener("input", (event) => {
    qrState.query = event.target.value;
    applyQrFilter();
    renderQrSheet();
  });

  qrElements.size?.addEventListener("change", (event) => {
    qrElements.sheet.className = `qr-sheet qr-size-${event.target.value}`;
    syncPrintSelection();
  });

  qrElements.sheet?.addEventListener("change", (event) => {
    const box = event.target.closest("[data-qr-check]");
    if (!box) return;
    const id = box.dataset.qrCheck;
    if (box.checked) qrState.selected.add(id);
    else qrState.selected.delete(id);
    syncPrintSelection();
  });

  qrElements.selectAll?.addEventListener("click", () => {
    qrState.filtered.forEach((product) => qrState.selected.add(product.id));
    qrElements.sheet?.querySelectorAll("[data-qr-check]").forEach((box) => { box.checked = true; });
    syncPrintSelection();
  });

  qrElements.clear?.addEventListener("click", () => {
    qrState.selected.clear();
    qrElements.sheet?.querySelectorAll("[data-qr-check]").forEach((box) => { box.checked = false; });
    syncPrintSelection();
  });

  qrElements.print?.addEventListener("click", () => window.print());
}

document.addEventListener("DOMContentLoaded", async () => {
  qrElements.search = document.querySelector("#qrSearch");
  qrElements.size = document.querySelector("#qrSize");
  qrElements.sheet = document.querySelector("#qrSheet");
  qrElements.status = document.querySelector("#qrStatus");
  qrElements.selectAll = document.querySelector("#qrSelectAll");
  qrElements.clear = document.querySelector("#qrClear");
  qrElements.print = document.querySelector("#qrPrint");

  bindQrEvents();

  if (typeof qrcode !== "function") {
    qrElements.status.textContent = "QR 라이브러리를 불러오지 못했습니다. 새로고침해 주세요.";
    return;
  }

  const products = await loadQrProducts();
  qrState.products = products
    .filter((product) => product && product.id && product.productName)
    .sort((a, b) => String(a.productName).localeCompare(String(b.productName), "ko"));

  if (!qrState.products.length) {
    qrElements.status.textContent = "제품 데이터를 불러오지 못했습니다.";
    qrElements.sheet.innerHTML = '<p class="qr-empty">제품 데이터를 불러오지 못했습니다.</p>';
    return;
  }


  // 조회 화면에서 제품을 보다가 넘어오면 그 제품을 골라 둔 채로 연다.
  // 목록은 그대로 두므로 다른 제품을 더 고를 수도 있다.
  const wanted = new URLSearchParams(window.location.search).get("product");
  if (wanted && qrState.products.some((product) => product.id === wanted)) {
    qrState.selected.add(wanted);
  }

  applyQrFilter();
  renderQrSheet();
  // 골라 둔 카드가 화면 밖에 있을 때만 데려온다.
  const first = document.querySelector(".qr-card.is-selected");
  const top = first ? first.getBoundingClientRect().top : 0;
  if (first && (top < 0 || top >= window.innerHeight)) {
    window.requestAnimationFrame(() => first.scrollIntoView({ behavior: "smooth", block: "center" }));
  }
});
