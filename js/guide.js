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

/* 항목별 개수 기준.
 *
 * 벽보는 멀리서 읽으므로 글자가 많으면 아무도 읽지 않는다. 다만 법이
 * 요구하는 최소치는 지켜야 하므로 "몇 개 이상"과 "몇 개까지"를 함께 둔다.
 *   H문구  최소 2개(하나뿐이면 하나), 최대 6개. 중대한 위험을 먼저 싣는다.
 *   P문구  최소 4개, 최대 6개. 예방·대응·저장·폐기를 하나씩 먼저 채운다.
 *   응급   최소 4개. 흡입·피부·눈·누출·화재·섭취 순으로 싣는다.
 *   그림문자는 생략하지 않는다.
 */
const HAZARD_MIN = 2;
const HAZARD_MAX = 6;
const PRECAUTION_MIN = 4;
const PRECAUTION_MAX = 6;
const HANDLING_MIN = 2;
const HANDLING_MAX = 3;
const FIRST_AID_MIN = 4;
const FIRST_AID_LIMIT = 1;

// 중대한 위험부터 싣는다. 앞에 있을수록 먼저 고른다.
const SEVERE_HAZARD_CODES = [
  "H200", "H201", "H202", "H203", "H204", "H205",       // 폭발성
  "H220", "H221", "H222", "H223", "H224", "H225", "H226", // 인화성
  "H240", "H241", "H242",                                  // 자기반응성
  "H250", "H251", "H252", "H260", "H261",                  // 자연발화·물반응성
  "H270", "H271", "H272",                                  // 산화성
  "H280", "H281",                                          // 고압가스
  "H300", "H301", "H310", "H311", "H330", "H331",          // 급성독성
  "H340", "H341", "H350", "H351", "H360", "H361",          // 발암·변이원·생식독성
  "H334", "H335",                                          // 호흡기 과민성·자극
  "H370", "H371", "H372", "H373",                          // 장기 독성
  "H314", "H318"                                           // 부식·심한 눈손상
];

const guideState = {
  products: [], filtered: [], selected: new Set(),
  query: "", paper: "a4", process: "", showProcess: false, onlySelected: false, onlyPostable: true
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

/* 종이에 찍힌 QR 은 몇 년을 벽에 붙어 있는다. 그 사이 자료가 바뀌어
 * 제품 번호가 달라지거나 제품이 빠지면 QR 이 죽는다. 그래서 번호와
 * 함께 제품명도 실어 둔다. 번호로 못 찾으면 이름으로 찾아 준다. */
function guideProductUrl(product) {
  const base = new URL(".", window.location.href);
  base.searchParams.set("product", product.id);
  base.searchParams.set("q", product.productName);
  return base.toString();
}

/* 원문 추출이 실패해 한 칸에 수백 자가 통째로 들어간 제품이 있다.
 * 그대로 실으면 게시물이 글씨 벽이 된다. 문장 끝에서 쪼개고, 그래도
 * 긴 것은 잘라 낸다. 지어내지 않고 자르기만 한다. */
const ITEM_MAX_LENGTH = 90;

// 문장이 끝나는 자리에서 자른다. 마침표가 없는 원문도 있어 어미로 가른다.
const SENTENCE_SPLIT = /(?<=(?:시오|하십시오|합니다|됩니다|있음|없음|금연)\.?)(?=\S)|(?<=\.)\s+/;

// 목차나 다른 절 제목이 섞여 들어온 조각은 지시문이 아니다.
const NOT_INSTRUCTION = /신호어|그림\s*문자|유해\s*[·ㆍ]?\s*위험\s*문구|예방조치\s*문구|구성성분|^\s*[○●◎]|^\s*\d{1,2}\s*[.．]/;
const INSTRUCTION_END = /(시오|마시오|하십시오|주십시오|금연|없음|있음)\.?$/;

function splitLongText(raw) {
  if (raw.length <= ITEM_MAX_LENGTH) return [raw];
  // 한 칸에 절 전체가 들어온 경우다. 쪼갠 뒤 지시문만 남긴다.
  return raw
    .split(SENTENCE_SPLIT)
    .map((part) => part.replace(/^[-•○\s]+/, "").trim())
    .filter((part) => part && !NOT_INSTRUCTION.test(part) && INSTRUCTION_END.test(part));
}

function cleanList(items, limit) {
  const seen = new Set();
  const out = [];
  for (const item of Array.isArray(items) ? items : []) {
    const raw = String(item || "").replace(/^[-•○\s]+/, "").trim();
    if (!raw) continue;
    for (let text of splitLongText(raw)) {
      if (text.length > ITEM_MAX_LENGTH) text = text.slice(0, ITEM_MAX_LENGTH).trim() + "…";
      if (!text || seen.has(text)) continue;
      seen.add(text);
      out.push(text);
      if (limit && out.length >= limit) return out;
    }
  }
  return out;
}

/* 값이 없으면 그냥 없는 것이다. 붉은 글씨로 크게 알리면 자료가 잘못된
 * 것처럼 보인다. 조용히 줄만 남기고, 만들 수 없는 제품은 아예 목록에서
 * 빼는 쪽으로 거른다. */
function blankMark() {
  return '<span class="guide-blank">—</span>';
}

/* 게시물로 쓸 수 있는 제품인지 본다. 명칭 말고 알맹이가 하나도 없으면
 * 종이만 버리게 되므로 기본 목록에서 뺀다. */
function isPostable(product) {
  const groups = product.precautionaryStatements || {};
  return Boolean(
    getPictogramCodes(product).length
    || cleanList(product.hazardStatements, 1).length
    || PRECAUTION_GROUPS.some((key) => cleanList(groups[key], 1).length)
  );
}

/* 긴급전화 칸에 "전화번호 : 02-1234-5678 / 긴급 전화번호 : 02-1234-5679"
 * 처럼 두 번호가 이름표와 함께 한 줄로 들어와 있다. 갈라서 제자리에 넣는다. */
const PHONE_LIKE = /(?:\+?\d[\d\s().-]{6,}\d)/;

function splitContacts(raw) {
  const text = String(raw || "").replace(/\s+/g, " ").trim();
  if (!text) return { phone: "", emergency: "" };

  const parts = text.split(/\s*[/|·]\s*/).filter(Boolean);
  let phone = "";
  let emergency = "";

  for (const part of parts) {
    const value = part.replace(/^[^:：]{0,26}[:：]\s*/, "").trim();
    if (!value) continue;
    if (/긴급|젂급|응급|emergency/i.test(part)) {
      if (!emergency) emergency = value;
    } else if (!phone) {
      phone = value;
    }
  }

  // 이름표가 없이 번호만 들어온 경우.
  if (!phone && !emergency) {
    const found = text.match(PHONE_LIKE);
    if (found) emergency = text.replace(/^[^:：]{0,26}[:：]\s*/, "").trim();
  }
  if (!emergency && phone) { emergency = phone; phone = ""; }
  return { phone, emergency };
}

// 그림문자는 임의로 빼지 않는다. MSDS 에 있는 것을 그대로 싣는다.
function getPictogramCodes(product) {
  const source = (product.ghsCodes || []).length
    ? product.ghsCodes
    : (product.ghsPictograms || []).map((item) => item.code);
  return [...new Set(source.map((code) => String(code || "").toUpperCase()))]
    .filter((code) => GUIDE_GHS[code]);
}

// 중대한 위험을 앞에 싣는다. 순서표에 없는 문구는 원래 차례대로 뒤에 붙는다.
function getHazardStatements(product) {
  const all = cleanList(product.hazardStatements, 0);
  const rank = (text) => {
    const code = (String(text).match(/H\d{3}/) || [])[0];
    const at = code ? SEVERE_HAZARD_CODES.indexOf(code) : -1;
    return at === -1 ? SEVERE_HAZARD_CODES.length : at;
  };
  const sorted = all
    .map((text, index) => ({ text, index, rank: rank(text) }))
    .sort((a, b) => (a.rank - b.rank) || (a.index - b.index))
    .map((item) => item.text);
  return sorted.slice(0, HAZARD_MAX);
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

/* 실제로 크게 다치는 순서대로 싣는다. 흡입과 피부 접촉이 가장 흔하고,
 * 누출·화재는 사람이 여럿 다치는 사고다. 섭취는 마지막에 둔다. */
function getEmergencyItems(product) {
  const aid = product.firstAid || {};
  const groups = product.precautionaryStatements || {};
  const spill = cleanList(groups.response, 1)[0] || "";
  const order = [
    { label: "마셨을 때(흡입)", text: cleanList(aid.inhalation, FIRST_AID_LIMIT)[0] },
    { label: "피부에 닿았을 때", text: cleanList(aid.skin, FIRST_AID_LIMIT)[0] },
    { label: "눈에 들어갔을 때", text: cleanList(aid.eye, FIRST_AID_LIMIT)[0] },
    { label: "누출 · 화재", text: spill },
    { label: "삼켰을 때", text: cleanList(aid.ingestion, FIRST_AID_LIMIT)[0] }
  ];
  return order.filter((group) => group.text);
}

/* 예방조치문구는 한 갈래만 실으면 반쪽이 된다. 고시도 일곱 개가 넘을 때
 * 예방·대응·저장·폐기를 하나씩 포함해 여섯 개로 줄이는 것을 허용한다.
 * 그 방식대로 각 갈래에서 하나씩 먼저 뽑고 남는 자리를 순서대로 채운다. */
const PRECAUTION_GROUPS = ["prevention", "response", "storage", "disposal"];

function getPrecautionStatements(product) {
  const groups = product.precautionaryStatements || {};
  const picked = [];
  const seen = new Set();
  const add = (text) => {
    if (!text || seen.has(text) || picked.length >= PRECAUTION_MAX) return;
    seen.add(text);
    picked.push(text);
  };
  PRECAUTION_GROUPS.forEach((key) => add(cleanList(groups[key], 1)[0]));
  PRECAUTION_GROUPS.forEach((key) => cleanList(groups[key], 0).forEach(add));
  return picked;
}

/* 취급·저장 주의사항은 MSDS 7항이 원문이지만 공개 데이터에는 그 항이
 * 없다. 저장·취급에 해당하는 예방조치문구로 대신 채우고, 그마저 없으면
 * 비었다고 드러낸다. 없는 값을 지어내지 않는다. */
const HANDLING_WORDS = ["보관", "저장", "환기", "밀폐", "정전기", "접지", "화기", "열", "직사광선", "용기"];

function getHandlingItems(product) {
  const groups = product.precautionaryStatements || {};
  const storage = cleanList(groups.storage, 0);
  const related = cleanList(groups.prevention, 0)
    .filter((text) => HANDLING_WORDS.some((word) => text.includes(word)));
  const seen = new Set();
  const out = [];
  [...storage, ...related].forEach((text) => {
    if (seen.has(text) || out.length >= HANDLING_MAX) return;
    seen.add(text);
    out.push(text);
  });
  return out;
}

function renderList(items) {
  if (!items.length) return `<p class="guide-blank-line">${blankMark()}</p>`;
  return `<ul>${items.map((item) => `<li>${guideEscape(item)}</li>`).join("")}</ul>`;
}

function renderSheetCard(product) {
  const codes = getPictogramCodes(product);
  const signal = getSignalWord(product);
  const hazards = getHazardStatements(product);
  const prevention = getPrecautionStatements(product);
  const handling = getHandlingItems(product);
  const ppe = getPpeItems(product);
  const aid = getEmergencyItems(product);
  const contacts = splitContacts(product.emergencyContact);

  const pictograms = codes.length
    ? codes.map((code) => `
        <figure class="guide-pictogram">
          <img src="${GUIDE_GHS[code].icon}" alt="${guideEscape(GUIDE_GHS[code].label)}">
          <figcaption>${guideEscape(GUIDE_GHS[code].label)}</figcaption>
        </figure>`).join("")
    : `<p class="guide-blank-line">${blankMark()}</p>`;

  const processRow = guideState.showProcess
    ? `<tr><th>작업공정</th><td>${guideEscape(guideState.process) || blankMark()}</td></tr>`
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
          <p class="guide-signal${signal === "위험" ? " is-danger" : ""}">${guideEscape(signal) || blankMark()}</p>
        </div>
        <h4>유해 · 위험문구</h4>
        ${renderList(hazards)}
      </section>

      <section class="guide-block guide-block-handling">
        <h3><b>③</b> 안전 및 보건상의 취급주의사항</h3>
        <h4>예방조치문구</h4>
        ${renderList(prevention)}
        <h4>취급 · 저장 시 주의사항</h4>
        ${renderList(handling)}
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
            </div>` : `<p class="guide-blank-line">${blankMark()}</p>`}
        </section>

        <section class="guide-block">
          <h3><b>⑤</b> 응급조치 및 사고 대응</h3>
          ${aid.length ? `<ul class="guide-aid-list">${aid.map((group) => `
            <li><b>${guideEscape(group.label)}</b> ${guideEscape(group.text)}</li>`).join("")}
          </ul>` : `<p class="guide-blank-line">${blankMark()}</p>`}
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
        <dl class="guide-supplier-grid">
          <dt>공급업체명</dt><dd>${guideEscape(product.supplier) || blankMark()}</dd>
          <dt>전화번호</dt><dd>${guideEscape(contacts.phone) || blankMark()}</dd>
          <dt>주소</dt><dd class="is-wide">${guideEscape(product.supplierAddress) || blankMark()}</dd>
          <dt>긴급전화번호</dt><dd>${guideEscape(contacts.emergency) || blankMark()}</dd>
          <dt>MSDS 개정일</dt><dd>${guideEscape(product.revisionDate) || blankMark()}</dd>
        </dl>
      </section>
    </article>`;
}

function applyGuideFilter() {
  if (guideState.onlySelected) {
    guideState.filtered = guideState.products.filter((product) => guideState.selected.has(product.id));
    return;
  }
  const needle = guideNormalize(guideState.query);
  let list = !needle
    ? [...guideState.products]
    : guideState.products.filter((product) => guideNormalize([
        product.productName, product.supplier, product.category, product.useCategory, product.msdsNo
      ].join(" ")).includes(needle));
  if (guideState.onlyPostable) list = list.filter(isPostable);
  guideState.filtered = list;
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
      code.addData(guideProductUrl(product));
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
  const hidden = guideState.products.filter((product) => !isPostable(product)).length;
  if (guideState.onlyPostable && hidden) parts.push(`원문에서 내용이 안 나온 ${hidden}건은 제외됨`);
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

  guideElements.onlyPostable?.addEventListener("change", (event) => {
    guideState.onlyPostable = event.target.checked;
    applyGuideFilter();
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
  guideElements.onlyPostable = document.querySelector("#guideOnlyPostable");
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
