/* 물질 기준으로 뒤집어 보기.
 *
 * 조회 화면은 제품에서 성분으로 내려간다. 그런데 안전보건관리자가 하는
 * 일은 대개 물질에서 시작한다. 작업환경측정 계획을 짜려면 측정해야 할
 * 유해인자가 어느 제품에 들어 있는지 알아야 하고, 특수건강진단 대상자를
 * 고르려면 그 물질을 쓰는 공정을 알아야 한다. 제품을 하나씩 열어서는
 * 답이 안 나온다.
 *
 * 그래서 같은 데이터를 CAS 번호로 묶어 반대로 세운다.
 *
 * 묶는 기준은 CAS 번호 하나뿐이다. 이름으로는 묶지 않는다. 업체마다
 * 자일렌을 자일렌, 크실렌, Xylene, 자일롤 로 제각각 적어서 이름으로
 * 묶으면 같은 물질이 넷으로 갈라진다. 반대로 CAS 가 없거나 영업비밀인
 * 성분은 아예 묶지 않는다. 억지로 묶으면 엉뚱한 성분끼리 한 덩어리가
 * 된다.
 *
 * 법정 유해인자 표시는 원본 MSDS 제3항 표에 적힌 것을 그대로 옮긴 것이다.
 * 이 사이트가 판정하는 것이 아니다. 실제로 측정을 해야 하는지 건강진단을
 * 해야 하는지는 취급 공정과 노출 여부, 법령상 예외를 따로 따져야 한다.
 */

const SUBSTANCE_DATA_SOURCES = [
  "data/msds.local.json",
  "data/msds.public.json",
  "data/msds-sample.json"
];

/* 원본 MSDS 제3항 표의 법정분류 칸. 표시 문구를 "대상"이 아니라
 * "유해인자"로 적는다. 제품에 자일렌이 들어 있다는 것과 그 작업장을
 * 측정해야 한다는 것은 다른 이야기인데, "대상"이라고 적으면 사이트가
 * 법정 의무를 판정해 준 것처럼 읽힌다. */
const FLAGS = [
  { key: "workplaceMonitoringTarget", alt: "workEnvironmentMeasurement", short: "작업환경측정", label: "작업환경측정 유해인자" },
  { key: "specialHealthCheckTarget", alt: "specialHealthExam", short: "특수건강진단", label: "특수건강진단 유해인자" },
  { key: "managementTarget", alt: "controlledSubstance", short: "관리대상", label: "관리대상 유해물질" }
];

/* 같은 칸이 제품에 따라 두 이름으로 들어 있다. 엑셀에서 옮긴 제품은
 * managementTarget 을, PDF 에서 바로 뽑은 제품은 controlledSubstance 를
 * 쓴다. 한쪽만 읽었더니 제품 20건의 작업환경측정 표시 74행이 이 화면에서
 * 빠졌다. 조회 화면(app.js)은 처음부터 둘 다 읽고 있었다. */
function flagValue(ingredient, flag) {
  const primary = ingredient[flag.key];
  if (primary !== undefined && primary !== null && String(primary).trim() !== "") return primary;
  return ingredient[flag.alt];
}

const CAS_SHAPE = /^\d{2,7}-\d{2}-\d$/;

// CAS 칸에 번호 대신 들어오는 말들. 이런 성분은 묶지 않는다.
const NOT_A_CAS = ["미기재", "영업비밀", "비공개", "해당없음", "없음", "mixture", "혼합물"];

const RENDER_STEP = 40;

const substanceState = {
  products: [],
  substances: [],
  orphans: [],
  visible: [],
  query: "",
  filters: new Set(),
  showOrphans: false,
  renderCount: RENDER_STEP
};

const substanceElements = {};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeSearch(value) {
  return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
}

function coerceList(payload) {
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

// 대표 이름으로 세우기 어려운 표기. 이명을 ; 로 줄줄이 적었거나 KE 번호·CAS 가 섞인 것, 너무 긴 것.
function isClumsyName(name) {
  const text = String(name || "");
  return /;|KE-\d|\d{2,7}-\d{2}-\d/.test(text) || text.length > 40;
}

function cleanCas(raw) {
  const text = String(raw || "").trim().replace(/^CAS\s*(No\.?|번호)?\s*[:.]?\s*/i, "");
  if (!CAS_SHAPE.test(text)) return "";
  if (NOT_A_CAS.some((word) => text.toLowerCase().includes(word))) return "";
  return text;
}

// 원본이 적은 값 그대로 본다. 빈칸은 "해당없음"이 아니라 "원본에 표기 없음"이다.
function flagState(raw) {
  const text = String(raw || "").trim();
  if (!text) return "unstated";
  if (/^[○Oo●ㅇ]/.test(text)) return "marked";
  return "cleared";
}

/* 제품과 성분을 CAS 번호로 묶는다. CAS 가 없는 성분은 따로 모아 둔다. */
function buildSubstances(products) {
  const byCas = new Map();
  const orphans = [];

  products.forEach((product) => {
    (product.ingredients || []).forEach((ingredient) => {
      const name = String(ingredient.chemicalName || "").trim();
      const use = {
        productId: product.id,
        productName: product.productName || "",
        supplier: product.supplier || "",
        content: String(ingredient.content || "").trim(),
        writtenName: name
      };
      const cas = cleanCas(ingredient.casNo);
      if (!cas) {
        orphans.push({ ...use, casRaw: String(ingredient.casNo || "").trim() });
        return;
      }

      let entry = byCas.get(cas);
      if (!entry) {
        entry = { cas, names: new Map(), uses: [], flags: {} };
        FLAGS.forEach((flag) => { entry.flags[flag.key] = { marked: 0, cleared: 0, unstated: 0 }; });
        byCas.set(cas, entry);
      }
      if (name) entry.names.set(name, (entry.names.get(name) || 0) + 1);
      entry.uses.push(use);
      FLAGS.forEach((flag) => { entry.flags[flag.key][flagState(flagValue(ingredient, flag))] += 1; });
    });
  });

  const substances = [...byCas.values()].map((entry) => {
    // 가장 많이 쓰인 표기를 대표 이름으로 삼는다. 나머지는 동의어로 남긴다.
    // 다만 이명 목록·KE 번호가 붙은 표기("자일렌 자일롤 ; 메틸톨루엔 … / KE-35427")는 대표로 세우지 않는다.
    const spellings = [...entry.names.entries()].sort((a, b) =>
      Number(isClumsyName(a[0])) - Number(isClumsyName(b[0])) || b[1] - a[1] || a[0].localeCompare(b[0], "ko"));
    // 한 제품이 같은 CAS 를 두 줄에 걸쳐 적는 일이 있다. 목록에는 한 번만 싣는다.
    const seen = new Set();
    const uses = entry.uses
      .filter((use) => !seen.has(use.productId) && seen.add(use.productId))
      .sort((a, b) => a.productName.localeCompare(b.productName, "ko"));
    return {
      cas: entry.cas,
      name: spellings.length ? spellings[0][0] : "(원본에 이름 없음)",
      spellings: spellings.map(([text]) => text),
      uses,
      productCount: new Set(uses.map((use) => use.productId)).size,
      flags: entry.flags,
      haystack: normalizeSearch([entry.cas, ...spellings.map(([text]) => text)].join(" "))
    };
  });

  substances.sort((a, b) => b.productCount - a.productCount || a.name.localeCompare(b.name, "ko"));
  orphans.sort((a, b) => a.productName.localeCompare(b.productName, "ko"));
  return { substances, orphans };
}

function hasFlag(substance, key) {
  return substance.flags[key].marked > 0;
}

function applyFilter() {
  const needle = normalizeSearch(substanceState.query);
  substanceState.visible = substanceState.substances.filter((substance) => {
    if (needle && !substance.haystack.includes(needle)) return false;
    for (const key of substanceState.filters) {
      if (!hasFlag(substance, key)) return false;
    }
    return true;
  });
  substanceState.renderCount = RENDER_STEP;
  render();
}

function badgeRow(substance) {
  const badges = FLAGS.filter((flag) => hasFlag(substance, flag.key)).map((flag) => {
    const counts = substance.flags[flag.key];
    const total = counts.marked + counts.cleared + counts.unstated;
    return `<span class="substance-badge" title="이 물질이 든 성분행 ${total}개 중 ${counts.marked}개에 표기">
      ${escapeHtml(flag.label)}</span>`;
  });
  return badges.length
    ? `<div class="substance-badges">${badges.join("")}</div>`
    : '<div class="substance-badges"><span class="substance-badge is-quiet">원본에 법정분류 표기 없음</span></div>';
}

function useRows(substance) {
  return substance.uses.map((use) => `
    <a class="substance-use" href="index.html?product=${encodeURIComponent(use.productId)}&q=${encodeURIComponent(use.productName)}">
      <span class="substance-use-name">${escapeHtml(use.productName)}</span>
      <span class="substance-use-supplier">${escapeHtml(use.supplier)}</span>
      <span class="substance-use-content">${escapeHtml(use.content ? `${use.content}%` : "")}</span>
    </a>`).join("");
}

function substanceCard(substance) {
  const others = substance.spellings.slice(1);
  return `
    <details class="substance-card" data-cas="${escapeHtml(substance.cas)}">
      <summary class="substance-head">
        <span class="substance-title">
          <strong>${escapeHtml(substance.name)}</strong>
          <code>CAS ${escapeHtml(substance.cas)}</code>
        </span>
        ${badgeRow(substance)}
        <span class="substance-count">제품 ${substance.productCount}건</span>
      </summary>
      <div class="substance-body">
        ${others.length ? `<p class="substance-spellings"><span>MSDS 표기명</span>${escapeHtml(others.join(" · "))}</p>` : ""}
        <div class="substance-uses">${useRows(substance)}</div>
      </div>
    </details>`;
}

function orphanBlock() {
  if (!substanceState.showOrphans) return "";
  const rows = substanceState.orphans.map((row) => `
    <a class="substance-use" href="index.html?product=${encodeURIComponent(row.productId)}&q=${encodeURIComponent(row.productName)}">
      <span class="substance-use-name">${escapeHtml(row.writtenName || "(원본에 이름 없음)")}</span>
      <span class="substance-use-supplier">${escapeHtml(row.productName)}</span>
      <span class="substance-use-content">${escapeHtml(row.casRaw)}</span>
    </a>`).join("");
  return `
    <section class="substance-orphans">
      <h2>CAS 번호가 없어 묶지 못한 성분 ${substanceState.orphans.length}건</h2>
      <p>원본 MSDS 가 CAS 를 안 적었거나 영업비밀로 가린 성분입니다.
         이름만으로 묶으면 다른 물질끼리 섞이므로 묶지 않고 그대로 둡니다.</p>
      <div class="substance-uses">${rows}</div>
    </section>`;
}

function render() {
  const total = substanceState.substances.length;
  const shown = substanceState.visible.length;
  substanceElements.status.textContent = shown === total
    ? `${total}종 모두 보는 중`
    : `${total}종 가운데 ${shown}종 보는 중`;

  if (!shown) {
    substanceElements.list.innerHTML =
      '<p class="substance-empty">걸리는 물질이 없습니다. 찾는 말이나 조건을 바꿔 보세요.</p>' + orphanBlock();
    return;
  }

  const slice = substanceState.visible.slice(0, substanceState.renderCount);
  const more = shown - slice.length;
  substanceElements.list.innerHTML =
    slice.map(substanceCard).join("")
    + (more > 0 ? `<button type="button" class="substance-more" id="substanceMore">남은 ${more}종 더 보기</button>` : "")
    + orphanBlock();

  document.querySelector("#substanceMore")?.addEventListener("click", () => {
    substanceState.renderCount += RENDER_STEP;
    render();
  });
}

/* 물질 하나에 제품 하나씩 한 줄로 내보낸다.
 *
 * 한 줄에 제품 일흔일곱 개를 몰아넣으면 엑셀에서 아무것도 못 한다.
 * 이렇게 풀어 두면 거르기도 되고 피벗도 된다. 작업환경측정 계획을
 * 짤 때 공정별로 추리는 것이 이 표에서 바로 된다. */
function flagText(substance, key) {
  const counts = substance.flags[key];
  if (counts.marked) return "해당";
  if (counts.cleared) return "원본에 해당없음으로 표기";
  return "원본에 표기 없음";
}

function exportCsv() {
  const header = [
    "물질명", "CAS", ...FLAGS.map((flag) => flag.label),
    "이 물질을 쓰는 제품 수", "제품명", "공급업체", "함유량(%)", "MSDS 표기명"
  ];
  const rows = [];
  substanceState.visible.forEach((substance) => {
    const flags = FLAGS.map((flag) => flagText(substance, flag.key));
    const spellings = substance.spellings.join(" / ");
    substance.uses.forEach((use) => {
      rows.push([
        substance.name, substance.cas, ...flags,
        substance.productCount, use.productName, use.supplier, use.content, spellings
      ]);
    });
  });
  window.downloadCsv(`물질별제품목록_${window.csvStamp()}.csv`, header, rows);
}

async function initSubstancePage() {
  substanceElements.search = document.querySelector("#substanceSearch");
  substanceElements.list = document.querySelector("#substanceList");
  substanceElements.status = document.querySelector("#substanceStatus");
  substanceElements.export = document.querySelector("#substanceExport");
  substanceElements.orphanToggle = document.querySelector("#substanceShowOrphans");

  const products = await loadFirstAvailable(SUBSTANCE_DATA_SOURCES, coerceList);
  substanceState.products = products.filter((product) => product && product.id && product.productName);

  if (!substanceState.products.length) {
    substanceElements.status.textContent = "제품 데이터를 불러오지 못했습니다.";
    return;
  }

  const built = buildSubstances(substanceState.products);
  substanceState.substances = built.substances;
  substanceState.orphans = built.orphans;

  substanceElements.search.addEventListener("input", (event) => {
    substanceState.query = event.target.value;
    applyFilter();
  });

  document.querySelectorAll("[data-substance-filter]").forEach((box) => {
    box.addEventListener("change", () => {
      const key = box.dataset.substanceFilter;
      if (box.checked) substanceState.filters.add(key);
      else substanceState.filters.delete(key);
      applyFilter();
    });
  });

  substanceElements.orphanToggle?.addEventListener("change", (event) => {
    substanceState.showOrphans = event.target.checked;
    render();
  });

  substanceElements.export.addEventListener("click", exportCsv);

  // 조회 화면과 같은 연관 검색. 물질 이름으로 찾는다.
  window.attachPickAssist?.({
    input: substanceElements.search,
    getProducts: () => substanceState.substances.map((substance) => ({
      id: substance.cas,
      productName: substance.name,
      supplier: `CAS ${substance.cas} · 제품 ${substance.productCount}건`,
      msdsNo: substance.spellings.join(" ")
    })),
    onPick: (picked) => {
      substanceState.query = picked.productName;
      applyFilter();
    }
  });

  applyFilter();
}

/* 이 화면은 관리자 모드에서만 연다. 감춰 둔 채로 227개 제품을 읽고
 * 274종을 묶는 것은 헛일이라, 열렸을 때만 시작한다. 감춘 화면에서
 * 암호를 풀면 그때 시작한다. */
let substanceStarted = false;

function startSubstancePage() {
  if (substanceStarted) return;
  if (document.documentElement.getAttribute("data-admin") !== "on") return;
  substanceStarted = true;
  initSubstancePage().catch((error) => {
    console.error(error);
    const status = document.querySelector("#substanceStatus");
    if (status) status.textContent = "물질 목록을 만들지 못했습니다.";
  });
}

document.addEventListener("DOMContentLoaded", startSubstancePage);
document.addEventListener("msds:admin-changed", (event) => {
  if (event.detail?.on) startSubstancePage();
});
