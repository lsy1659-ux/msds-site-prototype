"use strict";

const APP_CONFIG = {
  localDataUrl: "data/msds.local.json",
  sampleDataUrl: "data/msds-sample.json",
  minSearchCharacters: 2,
  initialResultLimit: 10,
  showDownloadButton: false,
  showPdfIframeWhenAvailable: false
};

const FALLBACK_PRODUCTS = [
  {
    id: "sample-msds-001",
    siteLabel: "사출구역 부착(NO.1)",
    hazardBadge: "위험",
    productName: "2차이형제 (S6)",
    erpName: "샘플 ERP 품명 - 2차 이형제 S6",
    msdsNo: "SAMPLE-MSDS-0001",
    fileName: "2차이형제(S6) 2024.pdf",
    pdfPath: "/pdf/2차이형제(S6) 2024.pdf",
    useCategory: "사출 소모품/이형제",
    recommendedUse: "사출 공정에서 금형과 제품의 분리를 돕는 샘플 용도",
    supplier: "샘플 제조사",
    emergencyContact: "샘플 안전보건 담당 연락처",
    hazardSummary: "인화성 에어로졸 등 샘플",
    dangerousGoods: "제4류 위험물 등 샘플",
    ppeSummary: "보안경, 보호장갑, 호흡보호구",
    revisionDate: "2024-04-01",
    ghsPictograms: [
      { code: "flame", label: "인화성" },
      { code: "exclamation", label: "유해/자극성" }
    ],
    hazardStatements: [
      "고인화성 에어로졸 및 증기 샘플",
      "눈에 자극을 일으킬 수 있음",
      "흡입 시 졸음 또는 현기증을 일으킬 수 있음"
    ],
    precautionaryStatements: {
      prevention: [
        "열, 스파크, 화염으로부터 멀리하시오.",
        "보호장갑, 보안경, 호흡보호구를 착용하시오.",
        "작업장은 충분히 환기하시오."
      ],
      response: [
        "피부에 묻으면 비누와 물로 씻으시오.",
        "흡입한 경우 신선한 공기가 있는 곳으로 이동하시오."
      ],
      storage: [
        "환기가 잘 되는 곳에 보관하시오.",
        "직사광선과 고온을 피하시오."
      ],
      disposal: [
        "관련 법규에 따라 폐기하시오."
      ]
    },
    components: [
      {
        chemicalName: "샘플 탄화수소 혼합물",
        casNo: "64742-49-0",
        content: "30~40%",
        controlledSubstance: "해당 없음",
        workEnvironmentMeasurement: "검토 필요",
        specialHealthExam: "해당 없음"
      }
    ]
  },
  {
    id: "sample-msds-002",
    siteLabel: "도장부스 부착(NO.2)",
    hazardBadge: "위험",
    productName: "신너 샘플 A",
    erpName: "샘플 ERP 품명 - 일반 신너",
    msdsNo: "SAMPLE-MSDS-0002",
    fileName: "신너샘플A 2024.pdf",
    pdfPath: "/pdf/신너샘플A 2024.pdf",
    useCategory: "도장 보조재/신너",
    recommendedUse: "도료 점도 조정을 위한 샘플 용도",
    supplier: "샘플 공급업체",
    emergencyContact: "샘플 안전보건 담당 연락처",
    hazardSummary: "인화성 액체 및 흡입 유해성 샘플",
    dangerousGoods: "제4류 위험물 등 샘플",
    ppeSummary: "보안경, 보호장갑, 방독마스크",
    revisionDate: "2024-03-15",
    ghsPictograms: [
      { code: "flame", label: "인화성" },
      { code: "health", label: "건강유해성" }
    ],
    hazardStatements: [
      "고인화성 액체 및 증기 샘플",
      "흡입 시 신체에 유해할 수 있음"
    ],
    precautionaryStatements: {
      prevention: ["화기와 점화원을 피하시오.", "증기 흡입을 피하고 보호구를 착용하시오."],
      response: ["흡입한 경우 신선한 공기가 있는 곳으로 이동하시오."],
      storage: ["용기를 밀폐하고 환기가 잘 되는 곳에 보관하시오."],
      disposal: ["내용물과 용기는 관련 법규에 따라 폐기하시오."]
    },
    components: [
      {
        chemicalName: "샘플 톨루엔",
        casNo: "108-88-3",
        content: "10~20%",
        controlledSubstance: "샘플 해당",
        workEnvironmentMeasurement: "샘플 대상",
        specialHealthExam: "샘플 대상"
      }
    ]
  },
  {
    id: "sample-msds-003",
    siteLabel: "세척구역 부착(NO.3)",
    hazardBadge: "경고",
    productName: "세척제 샘플 C",
    erpName: "샘플 ERP 품명 - 금형 세척제",
    msdsNo: "SAMPLE-MSDS-0003",
    fileName: "세척제샘플C 2024.pdf",
    pdfPath: "/pdf/세척제샘플C 2024.pdf",
    useCategory: "세척제/표면 세정",
    recommendedUse: "장비 표면 오염 제거를 위한 샘플 용도",
    supplier: "샘플 케미칼",
    emergencyContact: "샘플 안전보건 담당 연락처",
    hazardSummary: "피부 부식성 및 눈 손상성 샘플",
    dangerousGoods: "부식성 물질 샘플",
    ppeSummary: "보안면, 내화학 장갑, 앞치마",
    revisionDate: "2024-02-28",
    ghsPictograms: [
      { code: "corrosion", label: "부식성" },
      { code: "exclamation", label: "유해/자극성" }
    ],
    hazardStatements: [
      "피부와 눈에 심한 손상을 일으킬 수 있음",
      "금속을 부식시킬 수 있음",
      "삼키거나 흡입하면 유해할 수 있음"
    ],
    precautionaryStatements: {
      prevention: ["보안면, 내화학 장갑, 보호복을 착용하시오.", "분무 또는 증기를 흡입하지 마시오."],
      response: ["피부에 묻으면 오염된 의복을 벗고 물로 씻으시오.", "눈에 들어가면 몇 분간 물로 조심해서 씻으시오."],
      storage: ["내부식성 용기에 보관하시오."],
      disposal: ["폐액은 지정된 용기에 모아 처리하시오."]
    },
    components: [
      {
        chemicalName: "샘플 수산화나트륨",
        casNo: "1310-73-2",
        content: "1~5%",
        controlledSubstance: "샘플 해당",
        workEnvironmentMeasurement: "검토 필요",
        specialHealthExam: "해당 없음"
      }
    ]
  },
  {
    id: "sample-msds-004",
    siteLabel: "도료보관구역 부착(NO.4)",
    hazardBadge: "위험",
    productName: "도료 샘플 B",
    erpName: "샘플 ERP 품명 - 유성 도료",
    msdsNo: "SAMPLE-MSDS-0004",
    fileName: "도료샘플B 2024.pdf",
    pdfPath: "/pdf/도료샘플B 2024.pdf",
    useCategory: "도료/표면처리",
    recommendedUse: "금속 표면 보호용 샘플 도료",
    supplier: "샘플 제조사",
    emergencyContact: "샘플 안전보건 담당 연락처",
    hazardSummary: "인화성 및 수생환경 유해성 샘플",
    dangerousGoods: "제4류 위험물 등 샘플",
    ppeSummary: "보안경, 보호장갑, 환기설비",
    revisionDate: "2024-02-20",
    ghsPictograms: [
      { code: "flame", label: "인화성" },
      { code: "environment", label: "환경유해성" }
    ],
    hazardStatements: [
      "인화성 액체 및 증기 샘플",
      "수생생물에 유해할 수 있음",
      "눈과 피부에 자극을 일으킬 수 있음"
    ],
    precautionaryStatements: {
      prevention: ["화기와 점화원을 피하시오.", "옥외 또는 환기가 잘 되는 곳에서만 사용하시오."],
      response: ["누출 시 배수구로 유입되지 않게 하시오.", "오염된 보호구는 재사용 전 세척하시오."],
      storage: ["용기를 단단히 밀폐하고 서늘한 곳에 보관하시오."],
      disposal: ["잔량과 용기는 관련 법규에 따라 폐기하시오."]
    },
    components: [
      {
        chemicalName: "샘플 아크릴 수지",
        casNo: "9003-01-4",
        content: "20~30%",
        controlledSubstance: "해당 없음",
        workEnvironmentMeasurement: "해당 없음",
        specialHealthExam: "해당 없음"
      }
    ]
  },
  {
    id: "sample-msds-005",
    siteLabel: "에어로졸 보관구역 부착(NO.5)",
    hazardBadge: "경고",
    productName: "고압가스 샘플 D",
    erpName: "샘플 ERP 품명 - 에어로졸 보조제",
    msdsNo: "SAMPLE-MSDS-0005",
    fileName: "고압가스샘플D 2024.pdf",
    pdfPath: "/pdf/고압가스샘플D 2024.pdf",
    useCategory: "소모품/에어로졸",
    recommendedUse: "장비 보조 분사용 샘플 용도",
    supplier: "샘플 가스",
    emergencyContact: "샘플 안전보건 담당 연락처",
    hazardSummary: "고압가스 및 인화성 에어로졸 샘플",
    dangerousGoods: "고압가스 샘플",
    ppeSummary: "보안경, 보호장갑, 환기",
    revisionDate: "2024-01-12",
    ghsPictograms: [
      { code: "gas", label: "고압가스" },
      { code: "flame", label: "인화성" }
    ],
    hazardStatements: [
      "가열하면 폭발할 수 있음",
      "고압가스를 포함하고 있음",
      "인화성 에어로졸 샘플"
    ],
    precautionaryStatements: {
      prevention: ["고온과 직사광선을 피하시오.", "사용 후에도 용기에 구멍을 뚫거나 태우지 마시오."],
      response: ["누출 시 점화원을 제거하고 환기하시오."],
      storage: ["50도 이상 온도에 노출하지 마시오."],
      disposal: ["빈 용기도 관련 기준에 따라 폐기하시오."]
    },
    components: [
      {
        chemicalName: "샘플 프로판",
        casNo: "74-98-6",
        content: "20~30%",
        controlledSubstance: "해당 없음",
        workEnvironmentMeasurement: "검토 필요",
        specialHealthExam: "해당 없음"
      }
    ]
  }
];

const GHS_ICON_PARTS = {
  flame: `<path d="M49 71c10-7 17-15 17-27 0-12-7-20-14-28 1 12-5 17-11 23-5 5-10 10-10 19 0 10 8 16 18 13Z"/><path d="M49 70c-6-5-8-10-5-17 2-4 5-7 8-11 4 7 10 15 5 23-2 3-5 5-8 5Z" fill="#fff"/>`,
  exclamation: `<rect x="44" y="20" width="10" height="36" rx="5"/><circle cx="49" cy="68" r="6"/>`,
  health: `<circle cx="49" cy="25" r="10"/><path d="M27 76c2-18 11-29 22-29s20 11 22 29H27Z"/><path d="M43 52l6 9 6-9 8 24H35l8-24Z" fill="#fff"/>`,
  corrosion: `<path d="M20 58h34v8H20z"/><path d="M24 71h26v5H24z"/><path d="M56 27l23 11-4 8-23-11z"/><path d="M22 28l23 11-4 8-23-11z"/><path d="M63 48c5 2 7 4 7 7 0 4-3 7-7 7s-7-3-7-7c0-3 2-5 7-7Z"/><path d="M36 50c5 2 7 4 7 7 0 4-3 7-7 7s-7-3-7-7c0-3 2-5 7-7Z"/>`,
  environment: `<path d="M16 66c15 4 24 0 34-12 7-8 15-12 31-10-12 7-16 20-29 27-12 6-24 5-36-5Z"/><path d="M22 30c12 2 20 8 24 20-13-2-22-8-24-20Z"/><path d="M49 51c4-18 13-28 28-32-1 16-11 27-28 32Z"/>`,
  gas: `<rect x="31" y="18" width="36" height="61" rx="13"/><rect x="39" y="12" width="20" height="9" rx="3"/><path d="M34 34h30M34 63h30"/>`,
  oxidizer: `<circle cx="49" cy="59" r="14" fill="#fff"/><path d="M49 73c10-7 17-15 17-27 0-10-6-18-12-25 1 10-4 15-9 20-5 5-10 10-10 18 0 8 6 13 14 14Z"/><circle cx="49" cy="59" r="12"/>`,
  skull: `<circle cx="49" cy="35" r="21"/><circle cx="41" cy="33" r="5" fill="#fff"/><circle cx="57" cy="33" r="5" fill="#fff"/><path d="M45 47h8l-4-6Z" fill="#fff"/><path d="M31 66l36 10M67 66L31 76" stroke="#111" stroke-width="7" stroke-linecap="round"/>`,
  explosive: `<path d="M49 17l7 19 19-8-9 18 18 7-19 5 8 19-18-10-7 18-6-19-19 9 10-18-19-7 19-5-9-18 18 9 7-19Z"/>`
};

const PRECAUTION_LABELS = {
  prevention: "예방",
  response: "대응",
  storage: "저장",
  disposal: "폐기"
};

const state = {
  products: [],
  selectedId: null,
  query: "",
  resultLimit: APP_CONFIG.initialResultLimit,
  dataMode: "샘플 데이터 모드"
};

const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  const data = await loadProducts();
  state.products = data.products;
  state.dataMode = data.mode;
  state.selectedId = state.products[0]?.id || null;
  render();
});

function bindElements() {
  elements.searchInput = document.querySelector("#searchInput");
  elements.clearSearch = document.querySelector("#clearSearch");
  elements.resultCount = document.querySelector("#resultCount");
  elements.resultSubtitle = document.querySelector("#resultSubtitle");
  elements.selectionList = document.querySelector("#selectionList");
  elements.selectionPanel = document.querySelector(".selection-panel");
  elements.currentSelection = document.querySelector("#currentSelection");
  elements.posterPanel = document.querySelector("#posterPanel");
  elements.detailPanel = document.querySelector("#detailPanel");
  elements.quickSearch = document.querySelector(".quick-search");
  elements.emptySearchGuide = document.querySelector("#emptySearchGuide");
  elements.dataMode = document.querySelector("#dataMode");
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    state.resultLimit = APP_CONFIG.initialResultLimit;
    updateSelectedProductForQuery();
    render();
  });

  elements.clearSearch.addEventListener("click", () => {
    state.query = "";
    elements.searchInput.value = "";
    state.resultLimit = APP_CONFIG.initialResultLimit;
    state.selectedId = state.products[0]?.id || null;
    elements.searchInput.focus();
    render();
  });

  elements.quickSearch.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-query]");
    if (!button) return;
    state.query = button.dataset.query;
    elements.searchInput.value = state.query;
    state.resultLimit = APP_CONFIG.initialResultLimit;
    updateSelectedProductForQuery();
    render();
  });
}

function updateSelectedProductForQuery() {
  const normalizedQuery = normalizeSearchText(state.query);
  if (!normalizedQuery) {
    state.selectedId = state.products[0]?.id || null;
    return;
  }
  if (normalizedQuery.length < APP_CONFIG.minSearchCharacters) return;
  state.selectedId = getFilteredProducts()[0]?.id || state.selectedId;
}

async function loadProducts() {
  const localData = await fetchProducts(APP_CONFIG.localDataUrl);
  if (localData) {
    return {
      mode: "로컬 변환 데이터 모드",
      products: localData.map(normalizeProduct)
    };
  }

  const sampleData = await fetchProducts(APP_CONFIG.sampleDataUrl);
  if (sampleData) {
    return {
      mode: "샘플 데이터 모드",
      products: sampleData.map(normalizeProduct)
    };
  }

  return {
    mode: "샘플 데이터 모드",
    products: FALLBACK_PRODUCTS.map(normalizeProduct)
  };
}

async function fetchProducts(url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Data request failed: ${url}`);
    const data = await response.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.products)) return data.products;
    return null;
  } catch (error) {
    return null;
  }
}

function normalizeProduct(product) {
  const ingredients = product.ingredients || product.components || [];
  return {
    ...product,
    productName: product.productName || "",
    erpName: product.erpName || "",
    msdsNo: product.msdsNo || "",
    fileName: product.fileName || "",
    pdfPath: product.pdfPath || (product.fileName ? `/pdf/${product.fileName}` : ""),
    useCategory: product.useCategory || product.category || "",
    recommendedUse: product.recommendedUse || "",
    supplier: product.supplier || "",
    emergencyContact: product.emergencyContact || "",
    hazardSummary: product.hazardSummary || product.hazardClassification || "",
    dangerousGoods: product.dangerousGoods || "",
    ppeSummary: product.ppeSummary || "",
    revisionDate: product.revisionDate || "",
    hazardBadge: product.hazardBadge || "확인",
    ghsPictograms: product.ghsPictograms || [],
    hazardStatements: product.hazardStatements || [],
    precautionaryStatements: {
      prevention: product.precautionaryStatements?.prevention || [],
      response: product.precautionaryStatements?.response || [],
      storage: product.precautionaryStatements?.storage || [],
      disposal: product.precautionaryStatements?.disposal || []
    },
    components: ingredients.map((ingredient) => ({
      chemicalName: ingredient.chemicalName || "",
      casNo: ingredient.casNo || "",
      content: ingredient.content || "",
      controlledSubstance: ingredient.controlledSubstance || ingredient.managementTarget || "",
      workEnvironmentMeasurement: ingredient.workEnvironmentMeasurement || ingredient.workplaceMonitoringTarget || "",
      specialHealthExam: ingredient.specialHealthExam || ingredient.specialHealthCheckTarget || ""
    }))
  };
}

function normalizeSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\.pdf/gi, "")
    .replace(/[\s()[\]{}<>（）［］｛｝_\-\/\\]/g, "");
}

function normalizeGhsList(product) {
  return (product.ghsPictograms || []).map((item) => {
    if (typeof item === "string") {
      const code = item === "불꽃" ? "flame" : item === "느낌표" ? "exclamation" : "health";
      return { code, label: item };
    }
    return {
      code: item.code || "exclamation",
      label: item.label || "유해/자극성"
    };
  });
}

function buildSearchSource(product) {
  const componentText = (product.components || [])
    .map((component) => [
      component.chemicalName,
      component.casNo,
      component.content,
      component.controlledSubstance,
      component.workEnvironmentMeasurement,
      component.specialHealthExam
    ].join(" "))
    .join(" ");

  const ghsText = normalizeGhsList(product)
    .map((item) => `${item.code} ${item.label}`)
    .join(" ");

  return [
    product.siteLabel,
    product.hazardBadge,
    product.productName,
    product.erpName,
    product.msdsNo,
    product.fileName,
    product.useCategory,
    product.supplier,
    product.recommendedUse,
    product.hazardSummary,
    product.dangerousGoods,
    product.ppeSummary,
    ghsText,
    (product.hazardStatements || []).join(" "),
    flattenPrecautions(product.precautionaryStatements),
    componentText
  ].join(" ");
}

function flattenPrecautions(precautions = {}) {
  return Object.values(precautions)
    .flatMap((items) => Array.isArray(items) ? items : [])
    .join(" ");
}

function getFilteredProducts() {
  const normalizedQuery = normalizeSearchText(state.query);
  if (!normalizedQuery) return state.products;

  return state.products.filter((product) => {
    const normalizedSource = normalizeSearchText(buildSearchSource(product));
    return normalizedSource.includes(normalizedQuery);
  });
}

function getSelectedProduct(results) {
  return results.find((product) => product.id === state.selectedId) || results[0] || null;
}

function render() {
  const normalizedQuery = normalizeSearchText(state.query);
  const hasQuery = Boolean(normalizedQuery);
  const canShowCandidates = normalizedQuery.length >= APP_CONFIG.minSearchCharacters;
  const results = hasQuery ? getFilteredProducts() : [];
  const selectedPool = canShowCandidates ? results : state.products;
  const selected = getSelectedProduct(selectedPool);
  if (selected) state.selectedId = selected.id;

  elements.emptySearchGuide.classList.toggle("is-hidden", Boolean(state.query.trim()));
  elements.selectionPanel.classList.toggle("is-collapsed", !hasQuery);
  elements.resultCount.textContent = hasQuery ? `검색 결과 ${results.length}건` : "검색 전";
  elements.dataMode.textContent = state.dataMode;
  elements.dataMode.classList.toggle("is-local", state.dataMode.includes("로컬"));
  elements.currentSelection.textContent = selected
    ? `현재 선택 제품: ${selected.productName}`
    : "현재 선택 제품: 없음";
  elements.resultSubtitle.textContent = getResultSubtitle(hasQuery, canShowCandidates, results.length);

  renderSelectionList(results, hasQuery, canShowCandidates);
  renderPoster(selected);
  renderDetail(selected);
}

function getResultSubtitle(hasQuery, canShowCandidates, totalCount) {
  if (!hasQuery) return "검색어를 입력하면 후보 제품이 표시됩니다.";
  if (!canShowCandidates) return `${APP_CONFIG.minSearchCharacters}글자 이상 입력하면 후보 제품을 표시합니다.`;
  if (!totalCount) return "제품명, 용도, CAS No. 등으로 다시 검색해보세요.";
  return `상위 ${Math.min(totalCount, state.resultLimit)}건을 먼저 표시합니다.`;
}

function renderSelectionList(results, hasQuery, canShowCandidates) {
  if (!hasQuery) {
    elements.selectionList.innerHTML = "";
    return;
  }

  if (!canShowCandidates) {
    elements.selectionList.innerHTML = `<div class="notice">검색어가 너무 짧습니다. 2글자 이상 입력하면 후보 제품이 표시됩니다.</div>`;
    return;
  }

  if (!results.length) {
    elements.selectionList.innerHTML = `<div class="notice">검색 결과가 없습니다. 제품명, 용도, CAS No. 등으로 다시 검색해보세요.</div>`;
    return;
  }

  const visibleResults = results.slice(0, state.resultLimit);
  const hasMore = results.length > visibleResults.length;
  elements.selectionList.innerHTML = `
    <div class="selection-scroll">
      ${visibleResults.map((product) => `
        <button class="selection-item ${product.id === state.selectedId ? "is-selected" : ""}" type="button" data-product-id="${escapeAttribute(product.id)}">
          <span class="selection-name">${escapeHtml(product.productName)}</span>
          <span class="selection-meta">${escapeHtml(product.useCategory)} · ${escapeHtml(product.supplier)}</span>
        </button>
      `).join("")}
    </div>
    ${hasMore ? `<button class="show-more-button" type="button" id="showMoreResults">더보기 (${results.length - visibleResults.length}건)</button>` : ""}
  `;

  elements.selectionList.querySelectorAll("[data-product-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.productId;
      render();
    });
  });

  elements.selectionList.querySelector("#showMoreResults")?.addEventListener("click", () => {
    state.resultLimit += APP_CONFIG.initialResultLimit;
    render();
  });
}

function renderPoster(product) {
  if (!product) {
    elements.posterPanel.innerHTML = `<div class="poster-empty">선택된 제품이 없습니다.</div>`;
    return;
  }

  elements.posterPanel.innerHTML = `
    <div class="poster-product-row">
      <h2>${escapeHtml(product.productName)}</h2>
      <span class="hazard-badge">${escapeHtml(product.hazardBadge || "주의")}</span>
    </div>
    <div class="poster-ghs-row">
      ${renderGhsList(product, "poster")}
    </div>
    ${posterSection("유해 위험 문구", renderBulletList(product.hazardStatements || []), "poster-hazard-statements")}
    ${posterSection("예방조치 문구", renderPrecautions(product.precautionaryStatements || {}), "poster-precaution-statements")}
    <footer class="poster-footer">
      <p>현장 확인용 요약본이며, 상세 사항은 우측 PDF 또는 정식 MSDS를 참고하세요.</p>
      <p>공급자 정보: ${escapeHtml(product.supplier)}</p>
    </footer>
  `;
}

function renderDetail(product) {
  if (!product) {
    elements.detailPanel.className = "detail-panel empty-detail";
    elements.detailPanel.innerHTML = `<p>선택할 제품이 없습니다.</p>`;
    return;
  }

  const pdfPath = product.pdfPath || `/pdf/${product.fileName}`;
  elements.detailPanel.className = "detail-panel";
  elements.detailPanel.innerHTML = `
    ${detailSection("제품 기본정보", `
      <div class="info-grid">
        ${detailItem("제품명", product.productName)}
        ${detailItem("ERP 품명", product.erpName)}
        ${detailItem("MSDS번호", product.msdsNo)}
        ${detailItem("파일명", product.fileName)}
        ${detailItem("용도분류", product.useCategory)}
        ${detailItem("권고용도/사용용도", product.recommendedUse)}
        ${detailItem("제조사/공급업체", product.supplier)}
        ${detailItem("정보제공 및 긴급연락처", product.emergencyContact)}
        ${detailItem("개정일", product.revisionDate)}
      </div>
    `)}

    ${detailSection("핵심 위험 요약", `
      <div class="risk-summary-grid">
        ${summaryItem("주요 유해성 분류", product.hazardSummary, "danger")}
        ${summaryItem("위험물 구분", product.dangerousGoods, "warning")}
        ${summaryItem("PPE 요약", product.ppeSummary, "protect")}
      </div>
    `)}

    ${detailSection("GHS 그림문자", `
      <div class="ghs-grid">${renderGhsList(product, "large")}</div>
    `)}

    ${detailSection("성분정보", `
      <div class="component-table-wrap">
        <table class="component-table">
          <thead>
            <tr>
              <th>화학물질명</th>
              <th>CAS No.</th>
              <th>함유량(%)</th>
              <th>관리대상</th>
              <th>작업환경측정</th>
              <th>특수건강진단</th>
            </tr>
          </thead>
          <tbody>
            ${(product.components || []).map((component) => `
              <tr>
                <td>${escapeHtml(component.chemicalName)}</td>
                <td>${escapeHtml(component.casNo)}</td>
                <td>${escapeHtml(component.content)}</td>
                <td>${escapeHtml(component.controlledSubstance)}</td>
                <td>${escapeHtml(component.workEnvironmentMeasurement)}</td>
                <td>${escapeHtml(component.specialHealthExam)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `)}

    ${detailSection("PDF 미리보기", `
      <div class="pdf-preview">
        <p class="pdf-message">샘플 단계라 실제 PDF는 연결되지 않았습니다.</p>
        <div class="info-item">
          <span class="info-label">향후 연결 경로</span>
          <span class="info-value">${escapeHtml(pdfPath)}</span>
        </div>
        ${APP_CONFIG.showPdfIframeWhenAvailable ? `<iframe title="PDF 미리보기" src="${escapeAttribute(pdfPath)}"></iframe>` : `<div class="pdf-frame-placeholder">PDF 파일을 배치하면 이 영역에서 미리보기로 확인합니다.</div>`}
        <button class="download-button ${APP_CONFIG.showDownloadButton ? "" : "is-hidden"}" type="button">다운로드</button>
      </div>
    `)}
  `;
}

function posterSection(title, content, className) {
  return `
    <section class="poster-block ${escapeAttribute(className)}">
      <h3><span aria-hidden="true">■</span> ${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;
}

function renderBulletList(items) {
  if (!items.length) return `<p class="empty-text">등록된 문구가 없습니다.</p>`;
  return `<ul class="poster-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderPrecautions(precautions) {
  const groups = Object.entries(PRECAUTION_LABELS).map(([key, label]) => {
    const items = Array.isArray(precautions[key]) ? precautions[key] : [];
    if (!items.length) return "";
    return `
      <div class="precaution-group">
        <strong>${escapeHtml(label)}</strong>
        <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
    `;
  }).join("");

  return groups || `<p class="empty-text">등록된 예방조치 문구가 없습니다.</p>`;
}

function summaryItem(label, value, tone) {
  return `
    <div class="summary-item ${tone}">
      <span class="summary-label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function detailSection(title, content) {
  return `
    <section class="detail-block">
      <h3>${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;
}

function detailItem(label, value) {
  return `
    <div class="info-item">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderGhsList(product, size) {
  const list = normalizeGhsList(product);
  if (!list.length) return `<span class="no-ghs">GHS 정보 없음</span>`;
  return list.map((item) => renderGhsPictogram(item, size)).join("");
}

function renderGhsPictogram(item, size) {
  const iconPart = GHS_ICON_PARTS[item.code] || GHS_ICON_PARTS.exclamation;
  return `
    <figure class="ghs-item ${size}">
      <span class="ghs-diamond" aria-hidden="true">
        <svg viewBox="0 0 98 98" focusable="false">
          <rect class="diamond-border" x="15" y="15" width="68" height="68" transform="rotate(45 49 49)"/>
          <g class="ghs-symbol">${iconPart}</g>
        </svg>
      </span>
      <figcaption>${escapeHtml(item.label)}</figcaption>
    </figure>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}
