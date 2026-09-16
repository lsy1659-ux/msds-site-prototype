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

const labelState = { products: [], filtered: [], selected: new Set(), query: "", size: "mini", onlySelected: false,
  shorten: true, onlyPrintable: true, quantity: new Map() };
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
function getQuantity(productId) {
  const value = labelState.quantity.get(productId);
  return Number.isFinite(value) && value >= 1 ? Math.min(60, Math.round(value)) : 1;
}

function isPrintable(product) {
  if (isNotClassified(product)) return true;
  return cleanStatements(product.hazardStatements).length > 0;
}

function applyLabelFilter() {
  // 여러 번 찾아서 하나씩 고르는 일이 잦다. "고른 것만 보기"일 때는
  // 찾기 칸과 상관없이 지금까지 고른 것을 전부 보여 준다.
  if (labelState.onlySelected) {
    labelState.filtered = labelState.products.filter((product) => labelState.selected.has(product.id));
    return;
  }
  const needle = labelNormalize(labelState.query);
  let list = !needle
    ? [...labelState.products]
    : labelState.products.filter((product) => labelNormalize([
        product.productName, product.supplier, product.category, product.useCategory, product.msdsNo
      ].join(" ")).includes(needle));
  if (labelState.onlyPrintable) list = list.filter(isPrintable);
  labelState.filtered = list;
}

function applyLabelSize() {
  if (labelElements.sheet) {
    // 세로형은 가로형의 화면 배치를 그대로 쓰고 인쇄 규격만 덧입힌다.
    const sizeClass = labelState.size === "tall"
      ? "label-size-small label-size-tall"
      : `label-size-${labelState.size}`;
    labelElements.sheet.className = `label-sheet ${sizeClass}`;
  }
  // 100mL 초과 표지는 A4 를 가로로 쓴다. 용지 방향은 문서 전체에
  // 걸어야 앞에 빈 세로 페이지가 끼지 않는다.
  document.body.dataset.labelPage = labelState.size;
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
  // 100mL 초과 소분용기는 2단으로 압축한다. 가로형(small)과 세로형(tall)은
  // 본문이 같고 인쇄 규격만 다르다.
  const compact = size === "small" || size === "tall";

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
    // 고시가 정한 신호어는 "위험"과 "경고" 둘뿐이다. 추출이 실패해서
    // 붙은 임시 배지(MSDS)를 신호어 자리에 찍으면 잘못된 표시가 된다.
    const badge = String(product.hazardBadge || "").trim();
    const signal = badge === "위험" || badge === "경고" ? badge : "";
    const qr = `<div class="label-qr" data-label-qr="${labelEscape(product.id)}"></div>`;

    let body;
    if (mini) {
      // 고시상 100mL 이하 용기는 제품명·그림문자·신호어·공급자정보만으로 족하다.
      body = `<div class="label-mini-foot">
          ${renderSupplier(product)}
          ${qr}
        </div>
        <p class="label-compact-note">상세 유해·위험성 및 예방조치 사항은 QR코드 또는 MSDS를 확인하십시오.</p>`;
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

    const count = getQuantity(product.id);
    const head = `<label class="label-card-pick no-print">
          <input type="checkbox" data-label-check="${labelEscape(product.id)}"${checked ? " checked" : ""}>
          <span>인쇄 선택</span>
          <span class="label-qty">
            <span>장수</span>
            <input type="number" min="1" max="60" step="1" value="${count}" data-label-qty="${labelEscape(product.id)}" aria-label="${labelEscape(product.productName)} 인쇄 장수">
          </span>
        </label>`;
    // 100mL 이하는 H·P문구를 뺀 간이표시다. 왜 뺐는지 근거를 표지에 적어 두면
    // 현장 점검에서 "누락"이 아니라 "고시가 허용한 축약"임을 바로 보여 줄 수 있다.
    const legalNote = mini
      ? `<p class="label-legal-note">※ 100mL 이하 소분용기<br>고용노동부 고시 제6조제2항에 따라 축약 표시</p>`
      : "";
    // 적용차종 코드를 줄줄이 달아 100자가 넘는 제품명이 있다. 명칭은 법정
    // 필수 항목이라 줄일 수 없으니, 긴 이름만 글자를 줄여 칸 안에 담는다.
    const nameLength = String(product.productName || "").length;
    const nameClass = nameLength > 70 ? " is-verylong" : nameLength > 36 ? " is-long" : "";
    const face = `${legalNote}<h2 class="label-name${nameClass}">${labelEscape(product.productName)}</h2>
        ${renderPictograms(codes, product)}
        <p class="label-signal${signal === "위험" ? " is-danger" : ""}">${labelEscape(signal || "신호어 확인 필요")}</p>
        ${body}`;

    // 같은 표지를 여러 장 붙일 일이 잦다. 화면에는 한 장만 두고
    // 나머지는 숨겨 뒀다가 인쇄할 때만 꺼낸다.
    const copies = [];
    for (let index = 1; index < count; index += 1) {
      copies.push(`<article class="label-card is-copy${checked ? " is-selected" : ""}" data-label-id="${labelEscape(product.id)}" aria-hidden="true">${face}</article>`);
    }

    return `<article class="label-card${checked ? " is-selected" : ""}" data-label-id="${labelEscape(product.id)}">
        ${head}
        ${face}
      </article>${copies.join("")}`;
  }).join("");

  if (mini || compact) {
    labelState.filtered.forEach((product) => {
      if (typeof qrcode !== "function") return;
      let svg = "";
      try {
        const code = qrcode(0, "M");
        code.addData(buildProductUrl(product.id));
        code.make();
        svg = code.createSvgTag({ scalable: true, margin: 0 });
      } catch (error) {
        svg = "";
      }
      // 사본까지 모두 채운다.
      sheet.querySelectorAll(`[data-label-qr="${CSS.escape(product.id)}"]`)
        .forEach((slot) => { slot.innerHTML = svg; });
    });
  }

  updateLabelStatus();
}

function updateLabelStatus() {
  if (!labelElements.status) return;
  const notPrintable = labelState.products.filter((product) => !isPrintable(product)).length;
  const picked = labelState.selected.size;
  const parts = [`전체 ${labelState.products.length}건 중 ${labelState.filtered.length}건 표시`];
  parts.push(picked ? `고른 제품 ${picked}건(찾기를 바꿔도 남습니다)` : "고른 제품 없음(보이는 전체가 인쇄됩니다)");
  if (notPrintable) parts.push(`원문 확인 필요 ${notPrintable}건은 제외됨`);
  labelElements.status.textContent = parts.join(" · ");
}

// 찾기 칸을 바꾸면 앞서 고른 제품은 화면에서 사라진다. 무엇을 골라
// 뒀는지 눈으로 볼 수 있어야 여러 번 나눠 고를 수 있다.
function renderPickedList() {
  const box = labelElements.picked;
  if (!box) return;
  const picked = labelState.products.filter((product) => labelState.selected.has(product.id));
  box.toggleAttribute("hidden", picked.length === 0);
  if (labelElements.pickedCount) {
    labelElements.pickedCount.textContent = `고른 제품 ${picked.length}건`;
  }
  if (labelElements.onlySelected) {
    labelElements.onlySelected.setAttribute("aria-pressed", String(labelState.onlySelected));
    labelElements.onlySelected.textContent = labelState.onlySelected ? "전체 목록으로" : "고른 것만 보기";
  }
  if (labelElements.pickedChips) {
    labelElements.pickedChips.innerHTML = picked.map((product) => `
      <button type="button" class="label-chip" data-label-drop="${labelEscape(product.id)}"
        aria-label="${labelEscape(product.productName)} 고르기 취소">
        <span>${labelEscape(product.productName)}</span><b aria-hidden="true">×</b>
      </button>`).join("");
  }
}

function syncLabelSelection() {
  renderPickedList();
  labelElements.sheet?.classList.toggle("has-selection", labelState.selected.size > 0);
  labelElements.sheet?.querySelectorAll("[data-label-id]").forEach((card) => {
    card.classList.toggle("is-selected", labelState.selected.has(card.dataset.labelId));
  });
  updateLabelStatus();
}

function bindLabelEvents() {
  labelElements.search?.addEventListener("input", (event) => {
    labelState.query = event.target.value;
    // 다시 찾기 시작하면 전체 목록으로 돌아간다. 고른 것은 그대로 둔다.
    if (labelState.query) labelState.onlySelected = false;
    applyLabelFilter();
    renderLabelSheet();
    syncLabelSelection();
  });

  labelElements.size?.addEventListener("change", (event) => {
    labelState.size = event.target.value;
    applyLabelSize();
    renderLabelSheet();
    syncLabelSelection();
  });

  labelElements.sheet?.addEventListener("change", (event) => {
    const qty = event.target.closest("[data-label-qty]");
    if (qty) {
      const next = Math.max(1, Math.min(60, Math.round(Number(qty.value) || 1)));
      qty.value = next;
      labelState.quantity.set(qty.dataset.labelQty, next);
      renderLabelSheet();
      syncLabelSelection();
      return;
    }
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

  labelElements.onlySelected?.addEventListener("click", () => {
    labelState.onlySelected = !labelState.onlySelected;
    applyLabelFilter();
    renderLabelSheet();
    syncLabelSelection();
    labelElements.sheet?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // 고른 제품 칩의 × 는 그 제품만 고르기에서 뺀다.
  labelElements.pickedChips?.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-label-drop]");
    if (!chip) return;
    labelState.selected.delete(chip.dataset.labelDrop);
    if (labelState.onlySelected) applyLabelFilter();
    renderLabelSheet();
    syncLabelSelection();
  });

  labelElements.print?.addEventListener("click", () => {
    // 찾기 칸으로 걸러진 제품은 화면에 카드가 없다. 그대로 인쇄하면
    // 골라 둔 제품인데도 빠진다. 빠지는 게 있으면 먼저 전부 불러온다.
    const missing = labelState.selected.size
      && [...labelState.selected].some((id) => !labelState.filtered.some((product) => product.id === id));
    if (missing) {
      labelState.onlySelected = true;
      applyLabelFilter();
      renderLabelSheet();
      syncLabelSelection();
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => window.print()));
      return;
    }
    window.print();
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  labelElements.search = document.querySelector("#labelSearch");
  labelElements.size = document.querySelector("#labelSize");
  labelElements.sheet = document.querySelector("#labelSheet");
  labelElements.status = document.querySelector("#labelStatus");
  labelElements.picked = document.querySelector("#labelPicked");
  labelElements.pickedCount = document.querySelector("#labelPickedCount");
  labelElements.pickedChips = document.querySelector("#labelPickedChips");
  labelElements.onlySelected = document.querySelector("#labelOnlySelected");
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

  applyLabelSize();
  applyLabelFilter();
  renderLabelSheet();
});
