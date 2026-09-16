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

// 조회 화면과 마찬가지로 자동 추출본을 함께 읽는다.
// 이걸 빼면 추출로 채운 유해문구가 표지에서만 빈칸으로 보인다.
const LABEL_OVERRIDE_SOURCES = [
  "data/msds-overrides.local.json",
  "data/msds-overrides.public.json"
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

const labelState = { products: [], filtered: [], selected: new Set(), query: "", size: "mini",
  shorten: true, onlyPrintable: true };
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

async function loadLabelOverrides() {
  for (const source of LABEL_OVERRIDE_SOURCES) {
    try {
      const response = await fetch(source, { cache: "no-cache" });
      if (!response.ok) continue;
      const items = await response.json();
      if (Array.isArray(items) && items.length) return items;
    } catch (error) {
      // 다음 후보 파일로 넘어간다.
    }
  }
  return [];
}

// 제품에 값이 없을 때만 추출본으로 메운다. 확정 정보를 덮지 않는다.
function mergeOverride(product, override) {
  if (!override) return product;
  const merged = { ...product };
  if (!(merged.hazardStatements || []).length && (override.hazardStatements || []).length) {
    merged.hazardStatements = override.hazardStatements;
  }
  if (!(merged.ghsPictograms || []).length && (override.ghsPictograms || []).length) {
    merged.ghsPictograms = override.ghsPictograms;
  }
  if (!(merged.ghsCodes || []).length && (override.ghsCodes || []).length) {
    merged.ghsCodes = override.ghsCodes;
  }
  const groups = merged.precautionaryStatements || {};
  const hasPrecautions = ["prevention", "response", "storage", "disposal"]
    .some((key) => (groups[key] || []).length);
  if (!hasPrecautions && override.precautionaryStatements) {
    merged.precautionaryStatements = override.precautionaryStatements;
  }
  if (!String(merged.hazardBadge || "").trim() && String(override.signalWordCandidate || "").trim()) {
    merged.hazardBadge = override.signalWordCandidate;
  }
  return merged;
}

function buildProductUrl(productId) {
  const base = new URL(".", window.location.href);
  base.searchParams.set("product", productId);
  return base.toString();
}

// 고시는 그림문자가 다섯 개 이상이면 네 개까지만 표시하는 것을 허용한다.
const PICTOGRAM_LIMIT = 4;

function getPictogramCodes(product, limit = 0) {
  const source = Array.isArray(product.ghsPictograms) && product.ghsPictograms.length
    ? product.ghsPictograms.map((item) => item && item.code)
    : (product.ghsCodes || []);
  const codes = [...new Set(source.map((code) => String(code || "").toUpperCase()))]
    .filter((code) => GHS_PICTOGRAMS[code]);
  return limit && codes.length >= 5 ? codes.slice(0, limit) : codes;
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

function noneNotice(text) {
  return `<span class="label-none">해당없음${text ? ` — ${labelEscape(text)}` : ""}</span>`;
}

// 원문이 분류 대상이 아니라고 적은 제품은 "확인 필요"가 아니라 "해당없음"이다.
// 둘을 섞으면 확인이 끝난 제품까지 다시 뒤지게 된다.
function isNotClassified(product) {
  return product?.hazardNotClassified === true;
}

function renderPictograms(codes, product) {
  if (!codes.length) {
    if (isNotClassified(product)) {
      return `<div class="label-pictograms is-empty">${noneNotice("분류 대상 아님")}</div>`;
    }
    // 유해문구가 있는데 그림문자만 없으면, 그림문자가 붙지 않는 분류다.
    if (cleanStatements(product?.hazardStatements).length) {
      return `<div class="label-pictograms is-empty">${noneNotice("그림문자가 붙지 않는 분류")}</div>`;
    }
    return `<div class="label-pictograms is-empty">${missingNotice("그림문자")}</div>`;
  }
  return `<div class="label-pictograms">${codes.map((code) => {
    const item = GHS_PICTOGRAMS[code];
    return `<figure class="label-pictogram">
        <img src="${labelEscape(item.icon)}" alt="${labelEscape(code + " " + item.label)}">
        <figcaption>${labelEscape(item.label)}</figcaption>
      </figure>`;
  }).join("")}</div>`;
}

function renderStatementBlock(title, items, missingLabel, product, note = "") {
  if (!items.length) {
    const body = isNotClassified(product) ? noneNotice("분류 대상 아님") : missingNotice(missingLabel);
    return `<section class="label-block"><h3>${labelEscape(title)}</h3>${body}</section>`;
  }
  return `<section class="label-block">
      <h3>${labelEscape(title)}</h3>
      <ul>${items.map((item) => `<li>${labelEscape(item)}</li>`).join("")}</ul>
      ${note ? `<p class="label-block-note">${labelEscape(note)}</p>` : ""}
    </section>`;
}

/* 예방조치 문구를 용기에 다 적을 수 없는 제품이 있다. T-308은 30개가 넘는다.
 * 고용노동부 고시는 문구가 여섯 개를 넘으면 예방·대응·저장·폐기에서 고루 골라
 * 여섯 개만 적고 나머지는 물질안전보건자료를 참조하도록 안내하는 것을 허용한다.
 * 그 방식대로 줄인다. */
const PRECAUTION_GROUPS = ["prevention", "response", "storage", "disposal"];
const PRECAUTION_LIMIT = 6;

function getShortPrecautions(product) {
  const groups = product.precautionaryStatements || {};
  const picked = [];
  // 구분마다 한 개씩 먼저 확보한다.
  PRECAUTION_GROUPS.forEach((key) => {
    const first = cleanStatements(groups[key])[0];
    if (first) picked.push(first);
  });
  // 남는 자리는 앞에서부터 채운다.
  for (const key of PRECAUTION_GROUPS) {
    for (const item of cleanStatements(groups[key])) {
      if (picked.length >= PRECAUTION_LIMIT) break;
      if (!picked.includes(item)) picked.push(item);
    }
  }
  return picked.slice(0, PRECAUTION_LIMIT);
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

/* 표지에 "확인 필요"가 찍히면 용기에 붙일 수 없다.
 * 붙일 수 있는 것과 원문을 더 봐야 하는 것을 나눠서, 기본은 붙일 수 있는 것만 보여준다. */
function isPrintable(product) {
  if (isNotClassified(product)) return true;
  return cleanStatements(product.hazardStatements).length > 0;
}

function applyLabelFilter() {
  const needle = labelNormalize(labelState.query);
  let list = !needle
    ? [...labelState.products]
    : labelState.products.filter((product) => labelNormalize([
        product.productName, product.supplier, product.category, product.useCategory, product.msdsNo
      ].join(" ")).includes(needle));
  if (labelState.onlyPrintable) list = list.filter(isPrintable);
  labelState.filtered = list;
}

function renderLabelSheet() {
  const sheet = labelElements.sheet;
  if (!sheet) return;

  if (!labelState.filtered.length) {
    sheet.innerHTML = '<p class="label-empty">조건에 맞는 제품이 없습니다.</p>';
    updateLabelStatus();
    return;
  }

  const size = labelState.size;
  const mini = size === "mini";      // 100mL 이하: 고시가 허용하는 간이표시
  const compact = size === "small";  // 100mL 초과 소분용기: 2단으로 압축

  sheet.innerHTML = labelState.filtered.map((product) => {
    const checked = labelState.selected.has(product.id);
    const codes = getPictogramCodes(product, PICTOGRAM_LIMIT);
    const hazards = cleanStatements(product.hazardStatements);
    const allPrecautions = getPrecautionList(product);
    const shortenPrecautions = labelState.shorten && allPrecautions.length > PRECAUTION_LIMIT;
    const precautions = shortenPrecautions ? getShortPrecautions(product) : allPrecautions;
    const precautionNote = shortenPrecautions
      ? `그 밖의 예방조치 문구는 물질안전보건자료(MSDS)를 참조하십시오.`
      : "";
    const signal = String(product.hazardBadge || "").trim();
    const qr = `<div class="label-qr" data-label-qr="${labelEscape(product.id)}"></div>`;

    let body;
    if (mini) {
      // 고시상 100mL 이하 용기는 제품명·그림문자·신호어·공급자정보만으로 족하다.
      body = `<div class="label-mini-foot">
          ${renderSupplier(product)}
          ${qr}
        </div>
        <p class="label-compact-note">유해·위험 문구와 예방조치 문구는 QR 또는 물질안전보건자료(MSDS)에서 확인하십시오.</p>`;
    } else if (compact) {
      // 유해·위험 문구는 임의로 고르지 않고 모두 싣는다. 대신 두 단으로 좁혀 담는다.
      body = `<div class="label-two-col">
          ${renderStatementBlock("유해·위험 문구", hazards, "유해·위험 문구", product)}
          ${renderStatementBlock("예방조치 문구", precautions, "예방조치 문구", product, precautionNote)}
        </div>
        <div class="label-compact-foot">
          ${renderSupplier(product)}
          ${qr}
        </div>`;
    } else {
      body = `${renderStatementBlock("유해·위험 문구", hazards, "유해·위험 문구", product)}
        ${renderStatementBlock("예방조치 문구", precautions, "예방조치 문구", product, precautionNote)}
        ${renderSupplier(product)}`;
    }

    return `<article class="label-card${checked ? " is-selected" : ""}" data-label-id="${labelEscape(product.id)}">
        <label class="label-card-pick no-print">
          <input type="checkbox" data-label-check="${labelEscape(product.id)}"${checked ? " checked" : ""}>
          <span>인쇄 선택</span>
        </label>
        <h2 class="label-name">${labelEscape(product.productName)}</h2>
        ${renderPictograms(codes, product)}
        <p class="label-signal${signal === "위험" ? " is-danger" : ""}">${labelEscape(signal || "신호어 확인 필요")}</p>
        ${body}
      </article>`;
  }).join("");

  if (mini || compact) {
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
  const notPrintable = labelState.products.filter((product) => !isPrintable(product)).length;
  const picked = labelState.selected.size;
  const parts = [`전체 ${labelState.products.length}건 중 ${labelState.filtered.length}건 표시`];
  parts.push(picked ? `${picked}건 선택됨` : "선택 없음(보이는 전체가 인쇄됩니다)");
  if (notPrintable) parts.push(`원문 확인 필요 ${notPrintable}건은 제외됨`);
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

  labelElements.shorten?.addEventListener("change", (event) => {
    labelState.shorten = event.target.checked;
    renderLabelSheet();
    syncLabelSelection();
  });

  labelElements.onlyPrintable?.addEventListener("change", (event) => {
    labelState.onlyPrintable = event.target.checked;
    applyLabelFilter();
    renderLabelSheet();
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
  labelElements.shorten = document.querySelector("#labelShorten");
  labelElements.onlyPrintable = document.querySelector("#labelOnlyPrintable");

  bindLabelEvents();

  const [products, overrides] = await Promise.all([loadLabelProducts(), loadLabelOverrides()]);
  const overrideByFile = new Map();
  overrides.forEach((item) => {
    const file = String(item.sourcePdfPath || item.sourceRelativePath || "").split("/").pop();
    if (file) overrideByFile.set(file, item);
  });
  labelState.products = products
    .filter((product) => product && product.id && product.productName)
    .map((product) => mergeOverride(product, overrideByFile.get(product.fileName)))
    .sort((a, b) => String(a.productName).localeCompare(String(b.productName), "ko"));

  if (!labelState.products.length) {
    labelElements.status.textContent = "제품 데이터를 불러오지 못했습니다.";
    labelElements.sheet.innerHTML = '<p class="label-empty">제품 데이터를 불러오지 못했습니다.</p>';
    return;
  }

  applyLabelFilter();
  renderLabelSheet();
});
