/* MSDS 경고표지 만들기 화면.
 *
 * 고용노동부 고시가 요구하는 6개 항목(명칭·그림문자·신호어·유해위험문구·
 * 예방조치문구·공급자정보)을 조회 화면과 같은 공개 데이터에서 그대로 가져와
 * 인쇄용으로 배치한다. 값이 비어 있으면 감추지 않고 "확인 필요"로 드러낸다.
 */

const LABEL_DATA_SOURCES = [
  "data/msds.local.json",
  "data/msds.public.json",
  "data/msds-sample.json"
];

const GHS_PICTOGRAMS = {
  GHS01: { label: "폭발성", icon: "assets/ghs/ghs01.svg" },
  GHS02: { label: "인화성", icon: "assets/ghs/ghs02.svg" },
  GHS03: { label: "산화성", icon: "assets/ghs/ghs03.svg" },
  GHS04: { label: "고압가스", icon: "assets/ghs/ghs04.svg" },
  GHS05: { label: "부식성", icon: "assets/ghs/ghs05.svg" },
  GHS06: { label: "급성독성", icon: "assets/ghs/ghs06.svg" },
  GHS07: { label: "유해/자극성", icon: "assets/ghs/ghs07.svg" },
  GHS08: { label: "건강유해성", icon: "assets/ghs/ghs08.svg" },
  GHS09: { label: "환경유해성", icon: "assets/ghs/ghs09.svg" }
};

const labelState = { products: [], filtered: [], selected: new Set(), query: "", size: "medium" };
const labelElements = {};

function labelNormalize(value) {
  return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
}

function labelEscape(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function labelCoerceList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.products)) return payload.products;
  return [];
}

async function loadLabelProducts() {
  for (const source of LABEL_DATA_SOURCES) {
    try {
      const response = await fetch(source, { cache: "no-cache" });
      if (!response.ok) continue;
      const items = labelCoerceList(await response.json());
      if (items.length) return items;
    } catch (error) {
      // 다음 후보 파일로 넘어간다.
    }
  }
  return [];
}

function buildProductUrl(productId) {
  const base = new URL(".", window.location.href);
  base.searchParams.set("product", productId);
  return base.toString();
}

function getPictogramCodes(product) {
  const source = Array.isArray(product.ghsPictograms) && product.ghsPictograms.length
    ? product.ghsPictograms.map((item) => item && item.code)
    : (product.ghsCodes || []);
  return [...new Set(source.map((code) => String(code || "").toUpperCase()))]
    .filter((code) => GHS_PICTOGRAMS[code]);
}

// 문구 앞에 붙은 "- " 를 떼고 비어 있으면 빈 배열로 돌려준다.
function cleanStatements(items) {
  return (Array.isArray(items) ? items : [])
    .map((item) => String(item || "").replace(/^[-\s]+/, "").trim())
    .filter(Boolean);
}

function getPrecautionList(product) {
  const groups = product.precautionaryStatements || {};
  return ["prevention", "response", "storage", "disposal"].flatMap((key) => cleanStatements(groups[key]));
}

function missingNotice(text) {
  return `<span class="label-missing">확인 필요 — MSDS 원문에서 ${labelEscape(text)}을(를) 확인하세요</span>`;
}

function renderPictograms(codes) {
  if (!codes.length) return `<div class="label-pictograms is-empty">${missingNotice("그림문자")}</div>`;
  return `<div class="label-pictograms">${codes.map((code) => {
    const item = GHS_PICTOGRAMS[code];
    return `<figure class="label-pictogram">
        <img src="${labelEscape(item.icon)}" alt="${labelEscape(code + " " + item.label)}">
        <figcaption>${labelEscape(item.label)}</figcaption>
      </figure>`;
  }).join("")}</div>`;
}

function renderStatementBlock(title, items, missingLabel) {
  if (!items.length) return `<section class="label-block"><h3>${labelEscape(title)}</h3>${missingNotice(missingLabel)}</section>`;
  return `<section class="label-block">
      <h3>${labelEscape(title)}</h3>
      <ul>${items.map((item) => `<li>${labelEscape(item)}</li>`).join("")}</ul>
    </section>`;
}

function renderSupplier(product) {
  const lines = [
    product.supplier,
    product.supplierAddress,
    product.emergencyContact
  ].map((value) => String(value || "").trim()).filter(Boolean);
  if (!lines.length) return `<section class="label-supplier">${missingNotice("공급자 정보")}</section>`;
  return `<section class="label-supplier">
      <h3>공급자 정보</h3>
      ${lines.map((line) => `<p>${labelEscape(line)}</p>`).join("")}
    </section>`;
}

function applyLabelFilter() {
  const needle = labelNormalize(labelState.query);
  labelState.filtered = !needle
    ? [...labelState.products]
    : labelState.products.filter((product) => labelNormalize([
        product.productName, product.supplier, product.category, product.useCategory, product.msdsNo
      ].join(" ")).includes(needle));
}

function renderLabelSheet() {
  const sheet = labelElements.sheet;
  if (!sheet) return;

  if (!labelState.filtered.length) {
    sheet.innerHTML = '<p class="label-empty">조건에 맞는 제품이 없습니다.</p>';
    updateLabelStatus();
    return;
  }

  const compact = labelState.size === "small";

  sheet.innerHTML = labelState.filtered.map((product) => {
    const checked = labelState.selected.has(product.id);
    const codes = getPictogramCodes(product);
    const hazards = cleanStatements(product.hazardStatements);
    const precautions = getPrecautionList(product);
    const signal = String(product.hazardBadge || "").trim();

    const body = compact
      ? `${renderStatementBlock("유해·위험 문구", hazards, "유해·위험 문구")}
         <div class="label-qr" data-label-qr="${labelEscape(product.id)}"></div>
         <p class="label-compact-note">QR을 스캔하면 예방조치문구와 전체 MSDS를 볼 수 있습니다.</p>`
      : `${renderStatementBlock("유해·위험 문구", hazards, "유해·위험 문구")}
         ${renderStatementBlock("예방조치 문구", precautions, "예방조치 문구")}
         ${renderSupplier(product)}`;

    return `<article class="label-card${checked ? " is-selected" : ""}" data-label-id="${labelEscape(product.id)}">
        <label class="label-card-pick no-print">
          <input type="checkbox" data-label-check="${labelEscape(product.id)}"${checked ? " checked" : ""}>
          <span>인쇄 선택</span>
        </label>
        <h2 class="label-name">${labelEscape(product.productName)}</h2>
        ${renderPictograms(codes)}
        <p class="label-signal${signal === "위험" ? " is-danger" : ""}">${labelEscape(signal || "신호어 확인 필요")}</p>
        ${body}
      </article>`;
  }).join("");

  if (compact) {
    labelState.filtered.forEach((product) => {
      const slot = sheet.querySelector(`[data-label-qr="${CSS.escape(product.id)}"]`);
      if (!slot || typeof qrcode !== "function") return;
      try {
        const code = qrcode(0, "M");
        code.addData(buildProductUrl(product.id));
        code.make();
        slot.innerHTML = code.createSvgTag({ scalable: true, margin: 0 });
      } catch (error) {
        slot.innerHTML = "";
      }
    });
  }

  updateLabelStatus();
}

function updateLabelStatus() {
  if (!labelElements.status) return;
  const incomplete = labelState.filtered.filter((product) =>
    !getPictogramCodes(product).length || !cleanStatements(product.hazardStatements).length).length;
  const picked = labelState.selected.size;
  const parts = [`전체 ${labelState.products.length}건 중 ${labelState.filtered.length}건 표시`];
  parts.push(picked ? `${picked}건 선택됨` : "선택 없음(보이는 전체가 인쇄됩니다)");
  if (incomplete) parts.push(`안전정보 확인 필요 ${incomplete}건`);
  labelElements.status.textContent = parts.join(" · ");
}

function syncLabelSelection() {
  labelElements.sheet?.classList.toggle("has-selection", labelState.selected.size > 0);
  labelElements.sheet?.querySelectorAll("[data-label-id]").forEach((card) => {
    card.classList.toggle("is-selected", labelState.selected.has(card.dataset.labelId));
  });
  updateLabelStatus();
}

function bindLabelEvents() {
  labelElements.search?.addEventListener("input", (event) => {
    labelState.query = event.target.value;
    applyLabelFilter();
    renderLabelSheet();
  });

  labelElements.size?.addEventListener("change", (event) => {
    labelState.size = event.target.value;
    labelElements.sheet.className = `label-sheet label-size-${labelState.size}`;
    renderLabelSheet();
    syncLabelSelection();
  });

  labelElements.sheet?.addEventListener("change", (event) => {
    const box = event.target.closest("[data-label-check]");
    if (!box) return;
    if (box.checked) labelState.selected.add(box.dataset.labelCheck);
    else labelState.selected.delete(box.dataset.labelCheck);
    syncLabelSelection();
  });

  labelElements.selectAll?.addEventListener("click", () => {
    labelState.filtered.forEach((product) => labelState.selected.add(product.id));
    labelElements.sheet?.querySelectorAll("[data-label-check]").forEach((box) => { box.checked = true; });
    syncLabelSelection();
  });

  labelElements.clear?.addEventListener("click", () => {
    labelState.selected.clear();
    labelElements.sheet?.querySelectorAll("[data-label-check]").forEach((box) => { box.checked = false; });
    syncLabelSelection();
  });

  labelElements.print?.addEventListener("click", () => window.print());
}

document.addEventListener("DOMContentLoaded", async () => {
  labelElements.search = document.querySelector("#labelSearch");
  labelElements.size = document.querySelector("#labelSize");
  labelElements.sheet = document.querySelector("#labelSheet");
  labelElements.status = document.querySelector("#labelStatus");
  labelElements.selectAll = document.querySelector("#labelSelectAll");
  labelElements.clear = document.querySelector("#labelClear");
  labelElements.print = document.querySelector("#labelPrint");

  bindLabelEvents();

  const products = await loadLabelProducts();
  labelState.products = products
    .filter((product) => product && product.id && product.productName)
    .sort((a, b) => String(a.productName).localeCompare(String(b.productName), "ko"));

  if (!labelState.products.length) {
    labelElements.status.textContent = "제품 데이터를 불러오지 못했습니다.";
    labelElements.sheet.innerHTML = '<p class="label-empty">제품 데이터를 불러오지 못했습니다.</p>';
    return;
  }

  applyLabelFilter();
  renderLabelSheet();
});
