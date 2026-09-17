/* 작업공정별 관리요령 만들기.
 *
 * 산업안전보건법 시행규칙 제167조는 대상 화학물질을 취급하는 작업공정별로
 * 다섯 가지를 적어 게시하도록 한다.
 *   ① 대상화학물질의 명칭
 *   ② 유해성·위험성
 *   ③ 취급상의 주의사항
 *   ④ 적절한 보호구
 *   ⑤ 응급조치 요령 및 사고 시 대처방법
 *
 * 벽에 붙는 게시물이라 글자가 많으면 아무도 읽지 않는다. 문구는 앞에서
 * 몇 개만 싣고 나머지는 QR 과 MSDS 원문으로 넘긴다. 값이 비어 있으면
 * 감추지 않고 "확인 필요"로 드러낸다.
 */

const GUIDE_DATA_SOURCES = [
  "data/msds.local.json",
  "data/msds.public.json",
  "data/msds-sample.json"
];

const GUIDE_OVERRIDE_SOURCES = [
  "data/msds-overrides.local.json",
  "data/msds-overrides.public.json"
];

const GUIDE_GHS = {
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

// 벽보는 멀리서 읽는다. 항목마다 이만큼만 싣는다.
const HAZARD_LIMIT = 5;
const PRECAUTION_LIMIT = 5;
const STORAGE_LIMIT = 2;
const FIRST_AID_LIMIT = 1;
const PICTOGRAM_LIMIT = 4;

const guideState = {
  products: [], filtered: [], selected: new Set(),
  query: "", paper: "a4", process: "", showProcess: false, onlySelected: false
};
const guideElements = {};

function guideNormalize(value) {
  return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
}

function guideEscape(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function guideCoerceList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.products)) return payload.products;
  return [];
}

async function loadFirstAvailable(sources, pick) {
  for (const source of sources) {
    try {
      const response = await fetch(source, { cache: "no-cache" });
      if (!response.ok) continue;
      const items = pick(await response.json());
      if (items.length) return items;
    } catch (error) {
      // 다음 후보 파일로 넘어간다.
    }
  }
  return [];
}

// 제품에 값이 없을 때만 추출본으로 메운다. 확정 정보를 덮지 않는다.
function guideMergeOverride(product, override) {
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
  if (!(merged.ppeCandidates || []).length && (override.ppeCandidates || []).length) {
    merged.ppeCandidates = override.ppeCandidates;
  }
  if (!String(merged.hazardBadge || "").trim() && String(override.signalWordCandidate || "").trim()) {
    merged.hazardBadge = override.signalWordCandidate;
  }
  return merged;
}

function guideProductUrl(productId) {
  const base = new URL(".", window.location.href);
  base.searchParams.set("product", productId);
  return base.toString();
}

function cleanList(items, limit) {
  const seen = new Set();
  const out = [];
  for (const item of Array.isArray(items) ? items : []) {
    const text = String(item || "").replace(/^[-•\s]+/, "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
    if (limit && out.length >= limit) break;
  }
  return out;
}

function missing(text) {
  return `<span class="guide-missing">${guideEscape(text)}</span>`;
}

function getPictogramCodes(product) {
  const source = (product.ghsCodes || []).length
    ? product.ghsCodes
    : (product.ghsPictograms || []).map((item) => item.code);
  const codes = [...new Set(source.map((code) => String(code || "").toUpperCase()))]
    .filter((code) => GUIDE_GHS[code]);
  return codes.slice(0, PICTOGRAM_LIMIT);
}

function getSignalWord(product) {
  const badge = String(product.hazardBadge || product.signalWord || "").trim();
  return badge === "위험" || badge === "경고" ? badge : "";
}

// ④ 보호구는 원문 문장에서 무엇을 쓰라고 했는지만 골라낸다.
const PPE_RULES = [
  { key: "goggles", label: "보안경", words: ["보안경", "고글", "안면보호", "눈 보호", "밀폐형"] },
  { key: "gloves", label: "보호장갑", words: ["장갑"] },
  { key: "mask", label: "호흡보호구", words: ["마스크", "호흡", "방독", "방진", "송기", "공기호흡기"] },
  { key: "suit", label: "보호복", words: ["보호복", "보호의", "앞치마", "보호의복"] },
  { key: "boots", label: "안전화", words: ["안전화", "장화"] }
];

function getPpeItems(product) {
  const text = [
    (product.ppeCandidates || []).join(" "),
    product.ppeSummary || "",
    Object.values(product.precautionaryStatements || {}).flat().join(" ")
  ].join(" ");
  return PPE_RULES.filter((rule) => rule.words.some((word) => text.includes(word)));
}

function getFirstAid(product) {
  const aid = product.firstAid || {};
  return [
    { label: "눈에 들어갔을 때", items: cleanList(aid.eye, FIRST_AID_LIMIT) },
    { label: "피부에 닿았을 때", items: cleanList(aid.skin, FIRST_AID_LIMIT) },
    { label: "마셨을 때(흡입)", items: cleanList(aid.inhalation, FIRST_AID_LIMIT) },
    { label: "삼켰을 때", items: cleanList(aid.ingestion, FIRST_AID_LIMIT) }
  ].filter((group) => group.items.length);
}

function getResponseItems(product) {
  const groups = product.precautionaryStatements || {};
  return cleanList([...(groups.response || []), ...(groups.disposal || [])], 2);
}

function renderList(items, emptyText) {
  if (!items.length) return `<p class="guide-empty">${missing(emptyText)}</p>`;
  return `<ul>${items.map((item) => `<li>${guideEscape(item)}</li>`).join("")}</ul>`;
}

function renderSheetCard(product) {
  const codes = getPictogramCodes(product);
  const signal = getSignalWord(product);
  const groups = product.precautionaryStatements || {};
  const hazards = cleanList(product.hazardStatements, HAZARD_LIMIT);
  const prevention = cleanList([...(groups.prevention || [])], PRECAUTION_LIMIT);
  const storage = cleanList(groups.storage, STORAGE_LIMIT);
  const ppe = getPpeItems(product);
  const firstAid = getFirstAid(product);
  const response = getResponseItems(product);

  const pictograms = codes.length
    ? codes.map((code) => `
        <figure class="guide-pictogram">
          <img src="${GUIDE_GHS[code].icon}" alt="${guideEscape(GUIDE_GHS[code].label)}">
          <figcaption>${guideEscape(GUIDE_GHS[code].label)}</figcaption>
        </figure>`).join("")
    : `<p class="guide-empty">${missing("그림문자 확인 필요")}</p>`;

  const processRow = guideState.showProcess
    ? `<tr><th>작업공정</th><td>${guideEscape(guideState.process) || missing("공정명을 적으세요")}</td></tr>`
    : "";

  return `
    <article class="guide-card" data-guide-id="${guideEscape(product.id)}">
      <label class="guide-card-pick no-print">
        <input type="checkbox" data-guide-check="${guideEscape(product.id)}"${guideState.selected.has(product.id) ? " checked" : ""}>
        <span>인쇄 선택</span>
      </label>

      <header class="guide-card-head">
        <h2>화학제품 작업공정별 관리요령</h2>
        <p>물질안전보건자료(MSDS) 관리요령 · 산업안전보건법 시행규칙 제167조</p>
      </header>

      <section class="guide-block guide-block-name">
        <h3><b>①</b> 제품명</h3>
        <table class="guide-table">
          <tbody>
            <tr><th>제품명</th><td class="is-strong">${guideEscape(product.productName)}</td></tr>
            ${processRow}
          </tbody>
        </table>
      </section>

      <section class="guide-block guide-block-hazard">
        <h3><b>②</b> 유해성 · 위험성</h3>
        <div class="guide-hazard-top">
          <div class="guide-pictograms">${pictograms}</div>
          <p class="guide-signal${signal === "위험" ? " is-danger" : ""}">${guideEscape(signal || "신호어 확인 필요")}</p>
        </div>
        <h4>유해 · 위험문구</h4>
        ${renderList(hazards, "유해·위험문구 확인 필요")}
      </section>

      <section class="guide-block guide-block-handling">
        <h3><b>③</b> 안전 및 보건상의 취급주의사항</h3>
        <h4>예방조치문구</h4>
        ${renderList(prevention, "예방조치문구 확인 필요")}
        <h4>취급 · 저장 시 주의사항</h4>
        ${renderList(storage, "저장 주의사항 확인 필요")}
      </section>

      <div class="guide-two-col">
        <section class="guide-block">
          <h3><b>④</b> 적절한 보호구</h3>
          ${ppe.length ? `
            <div class="guide-ppe">
              ${ppe.map((item) => `
                <div class="guide-ppe-item">
                  <img src="assets/ppe/${item.key}.svg" alt="">
                  <span>${guideEscape(item.label)}</span>
                </div>`).join("")}
            </div>` : `<p class="guide-empty">${missing("보호구 확인 필요")}</p>`}
        </section>

        <section class="guide-block">
          <h3><b>⑤</b> 응급조치 및 사고 대응</h3>
          ${firstAid.length ? `<ul class="guide-aid-list">${firstAid.map((group) => `
            <li><b>${guideEscape(group.label)}</b> ${guideEscape(group.items.join(" / "))}</li>`).join("")}
          </ul>` : `<p class="guide-empty">${missing("응급조치 확인 필요")}</p>`}
          ${response.length ? `<ul class="guide-aid-list">${response.map((item) => `
            <li><b>누출·화재</b> ${guideEscape(item)}</li>`).join("")}
          </ul>` : ""}
        </section>
      </div>

      <section class="guide-block guide-block-qr">
        <div class="guide-qr" data-guide-qr="${guideEscape(product.id)}"></div>
        <div class="guide-qr-text">
          <strong>물질안전보건자료(MSDS) 조회</strong>
          <p>QR코드를 스캔하여 해당 제품의 최신 MSDS를 확인하십시오.</p>
          <p class="guide-qr-caution">이 게시물은 요약본입니다. 작업 전 MSDS 원문을 반드시 확인하십시오.</p>
        </div>
      </section>

      <section class="guide-block guide-block-supplier">
        <h3>공급자 정보</h3>
        <div class="guide-supplier-grid">
          <div><span>공급업체명</span><b>${guideEscape(product.supplier) || missing("확인 필요")}</b></div>
          <div><span>긴급전화</span><b>${guideEscape(product.emergencyContact) || missing("확인 필요")}</b></div>
          <div class="is-wide"><span>주소</span><b>${guideEscape(product.supplierAddress) || missing("확인 필요")}</b></div>
          <div><span>MSDS 개정일</span><b>${guideEscape(product.revisionDate) || missing("확인 필요")}</b></div>
        </div>
      </section>
    </article>`;
}

function applyGuideFilter() {
  if (guideState.onlySelected) {
    guideState.filtered = guideState.products.filter((product) => guideState.selected.has(product.id));
    return;
  }
  const needle = guideNormalize(guideState.query);
  guideState.filtered = !needle
    ? [...guideState.products]
    : guideState.products.filter((product) => guideNormalize([
        product.productName, product.supplier, product.category, product.useCategory, product.msdsNo
      ].join(" ")).includes(needle));
}

function renderGuideSheet() {
  const sheet = guideElements.sheet;
  if (!sheet) return;
  sheet.className = `guide-sheet paper-${guideState.paper}`;
  if (!guideState.filtered.length) {
    sheet.innerHTML = '<p class="guide-empty-list">조건에 맞는 제품이 없습니다.</p>';
    return;
  }
  sheet.innerHTML = guideState.filtered.map(renderSheetCard).join("");

  guideState.filtered.forEach((product) => {
    if (typeof qrcode !== "function") return;
    let svg = "";
    try {
      const code = qrcode(0, "M");
      code.addData(guideProductUrl(product.id));
      code.make();
      svg = code.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
    } catch (error) {
      svg = "";
    }
    sheet.querySelectorAll(`[data-guide-qr="${CSS.escape(product.id)}"]`).forEach((slot) => {
      slot.innerHTML = svg;
    });
  });
}

function updateGuideStatus() {
  if (!guideElements.status) return;
  const picked = guideState.selected.size;
  const parts = [`전체 ${guideState.products.length}건 중 ${guideState.filtered.length}건 표시`];
  parts.push(picked ? `고른 제품 ${picked}건(찾기를 바꿔도 남습니다)` : "고른 제품 없음(보이는 전체가 인쇄됩니다)");
  guideElements.status.textContent = parts.join(" · ");
}

function renderGuidePicked() {
  const box = guideElements.picked;
  if (!box) return;
  const picked = guideState.products.filter((product) => guideState.selected.has(product.id));
  box.toggleAttribute("hidden", picked.length === 0);
  if (guideElements.pickedCount) guideElements.pickedCount.textContent = `고른 제품 ${picked.length}건`;
  if (guideElements.onlySelected) {
    guideElements.onlySelected.setAttribute("aria-pressed", String(guideState.onlySelected));
    guideElements.onlySelected.textContent = guideState.onlySelected ? "전체 목록으로" : "고른 것만 보기";
  }
  if (guideElements.pickedChips) {
    guideElements.pickedChips.innerHTML = picked.map((product) => `
      <button type="button" class="guide-chip" data-guide-drop="${guideEscape(product.id)}"
        aria-label="${guideEscape(product.productName)} 고르기 취소">
        <span>${guideEscape(product.productName)}</span><b aria-hidden="true">×</b>
      </button>`).join("");
  }
}

function syncGuideSelection() {
  renderGuidePicked();
  guideElements.sheet?.classList.toggle("has-selection", guideState.selected.size > 0);
  guideElements.sheet?.querySelectorAll("[data-guide-id]").forEach((card) => {
    card.classList.toggle("is-selected", guideState.selected.has(card.dataset.guideId));
  });
  updateGuideStatus();
}

function bindGuideEvents() {
  guideElements.search?.addEventListener("input", (event) => {
    guideState.query = event.target.value;
    if (guideState.query) guideState.onlySelected = false;
    applyGuideFilter();
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.paper?.addEventListener("change", (event) => {
    guideState.paper = event.target.value;
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.processOn?.addEventListener("change", (event) => {
    guideState.showProcess = event.target.checked;
    guideElements.processField?.toggleAttribute("hidden", !event.target.checked);
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.process?.addEventListener("input", (event) => {
    guideState.process = event.target.value;
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.sheet?.addEventListener("change", (event) => {
    const box = event.target.closest("[data-guide-check]");
    if (!box) return;
    if (box.checked) guideState.selected.add(box.dataset.guideCheck);
    else guideState.selected.delete(box.dataset.guideCheck);
    syncGuideSelection();
  });

  guideElements.onlySelected?.addEventListener("click", () => {
    guideState.onlySelected = !guideState.onlySelected;
    applyGuideFilter();
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.pickedChips?.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-guide-drop]");
    if (!chip) return;
    guideState.selected.delete(chip.dataset.guideDrop);
    if (guideState.onlySelected) applyGuideFilter();
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.selectAll?.addEventListener("click", () => {
    guideState.filtered.forEach((product) => guideState.selected.add(product.id));
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.clear?.addEventListener("click", () => {
    guideState.selected.clear();
    renderGuideSheet();
    syncGuideSelection();
  });

  guideElements.print?.addEventListener("click", () => {
    // 찾기로 걸러진 제품은 화면에 없다. 그대로 인쇄하면 골라 둔 것이 빠진다.
    const missingPicked = guideState.selected.size
      && [...guideState.selected].some((id) => !guideState.filtered.some((product) => product.id === id));
    if (missingPicked) {
      guideState.onlySelected = true;
      applyGuideFilter();
      renderGuideSheet();
      syncGuideSelection();
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => window.print()));
      return;
    }
    window.print();
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  guideElements.search = document.querySelector("#guideSearch");
  guideElements.paper = document.querySelector("#guidePaper");
  guideElements.processOn = document.querySelector("#guideProcessOn");
  guideElements.processField = document.querySelector("#guideProcessField");
  guideElements.process = document.querySelector("#guideProcess");
  guideElements.sheet = document.querySelector("#guideSheet");
  guideElements.status = document.querySelector("#guideStatus");
  guideElements.picked = document.querySelector("#guidePicked");
  guideElements.pickedCount = document.querySelector("#guidePickedCount");
  guideElements.pickedChips = document.querySelector("#guidePickedChips");
  guideElements.onlySelected = document.querySelector("#guideOnlySelected");
  guideElements.selectAll = document.querySelector("#guideSelectAll");
  guideElements.clear = document.querySelector("#guideClear");
  guideElements.print = document.querySelector("#guidePrint");

  bindGuideEvents();

  const [products, overrides] = await Promise.all([
    loadFirstAvailable(GUIDE_DATA_SOURCES, guideCoerceList),
    loadFirstAvailable(GUIDE_OVERRIDE_SOURCES, (data) => (Array.isArray(data) ? data : []))
  ]);

  const overrideByFile = new Map();
  overrides.forEach((item) => {
    const file = String(item.sourcePdfPath || item.sourceRelativePath || "").split("/").pop();
    if (file) overrideByFile.set(file, item);
  });

  guideState.products = products
    .filter((product) => product && product.id && product.productName)
    .map((product) => guideMergeOverride(product, overrideByFile.get(product.fileName)))
    .sort((a, b) => String(a.productName).localeCompare(String(b.productName), "ko"));

  if (!guideState.products.length) {
    guideElements.status.textContent = "제품 데이터를 불러오지 못했습니다.";
    guideElements.sheet.innerHTML = '<p class="guide-empty-list">제품 데이터를 불러오지 못했습니다.</p>';
    return;
  }

  // 조회 화면에서 제품을 보다가 넘어오면 그 제품을 골라 둔 채로 연다.
  const wanted = new URLSearchParams(window.location.search).get("product");
  if (wanted && guideState.products.some((product) => product.id === wanted)) {
    guideState.selected.add(wanted);
  }

  applyGuideFilter();
  renderGuideSheet();
  syncGuideSelection();
});
