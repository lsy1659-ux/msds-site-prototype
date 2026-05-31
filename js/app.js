"use strict";

const APP_CONFIG = {
  localDataUrl: "data/msds.local.json",
  sampleDataUrl: "data/msds-sample.json",
  localOverridesUrl: "data/msds-overrides.local.json",
  sampleOverridesUrl: "data/msds-overrides.sample.json",
  minSearchCharacters: 2,
  initialResultLimit: 8,
  showDownloadButton: false,
  showPdfIframeWhenAvailable: true,
  fieldDisplayMode: true,
  showReviewStatusOnFieldPoster: false,
  showExtractionStatusInDetail: false,
  allowCandidateOverrideDisplay: true
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
  resultOffset: 0,
  showAllResults: false,
  selectionCollapsed: false,
  dataMode: "샘플 데이터 모드",
  pdfAvailability: {},
  pdfModal: {
    isOpen: false,
    title: "",
    path: ""
  }
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
    resetResultWindow();
    state.selectionCollapsed = false;
    updateSelectedProductForQuery();
    render();
  });

  elements.clearSearch.addEventListener("click", () => {
    state.query = "";
    elements.searchInput.value = "";
    resetResultWindow();
    state.selectedId = state.products[0]?.id || null;
    state.selectionCollapsed = false;
    elements.searchInput.focus();
    render();
  });

  elements.quickSearch.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-query]");
    if (!button) return;
    state.query = button.dataset.query;
    elements.searchInput.value = state.query;
    resetResultWindow();
    state.selectionCollapsed = false;
    updateSelectedProductForQuery();
    render();
  });

  document.addEventListener("click", (event) => {
    const enlargeButton = event.target.closest("[data-open-pdf-modal]");
    if (enlargeButton) {
      openPdfModal(enlargeButton.dataset.pdfTitle, enlargeButton.dataset.pdfPath);
      return;
    }

    const closeButton = event.target.closest("[data-close-pdf-modal]");
    if (closeButton || event.target.classList.contains("pdf-modal-backdrop")) {
      closePdfModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.pdfModal.isOpen) {
      closePdfModal();
    }
  });
}

function resetResultWindow() {
  state.resultLimit = APP_CONFIG.initialResultLimit;
  state.resultOffset = 0;
  state.showAllResults = false;
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
    const overrides = await loadOverrides();
    return {
      mode: "로컬 변환 데이터 모드",
      products: applyOverrides(localData.map(normalizeProduct), overrides)
    };
  }

  const sampleData = await fetchProducts(APP_CONFIG.sampleDataUrl);
  if (sampleData) {
    const overrides = await loadOverrides();
    return {
      mode: "샘플 데이터 모드",
      products: applyOverrides(sampleData.map(normalizeProduct), overrides)
    };
  }

  const overrides = await loadOverrides();
  return {
    mode: "샘플 데이터 모드",
    products: applyOverrides(FALLBACK_PRODUCTS.map(normalizeProduct), overrides)
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

async function loadOverrides() {
  const localOverrides = await fetchOverrides(APP_CONFIG.localOverridesUrl);
  if (localOverrides) return localOverrides.map(normalizeOverride);

  const sampleOverrides = await fetchOverrides(APP_CONFIG.sampleOverridesUrl);
  if (sampleOverrides) return sampleOverrides.map(normalizeOverride);

  return [];
}

async function fetchOverrides(url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Override request failed: ${url}`);
    const data = await response.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.overrides)) return data.overrides;
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

function normalizeOverride(override) {
  const precautions = override.precautionaryStatements || {};
  return {
    ...override,
    match: override.match || {},
    sourcePdfPath: override.sourcePdfPath || "",
    extractStatus: override.extractStatus || "",
    reviewStatus: override.reviewStatus || "검토필요",
    signalWordCandidate: override.signalWordCandidate || "",
    ghsPictograms: Array.isArray(override.ghsPictograms) ? override.ghsPictograms : [],
    hazardStatements: Array.isArray(override.hazardStatements) ? override.hazardStatements : [],
    precautionaryStatements: {
      prevention: Array.isArray(precautions.prevention) ? precautions.prevention : [],
      response: Array.isArray(precautions.response) ? precautions.response : [],
      storage: Array.isArray(precautions.storage) ? precautions.storage : [],
      disposal: Array.isArray(precautions.disposal) ? precautions.disposal : []
    },
    ingredients: Array.isArray(override.ingredients) ? override.ingredients : [],
    ppeCandidates: Array.isArray(override.ppeCandidates) ? override.ppeCandidates : [],
    notes: override.notes || ""
  };
}

function applyOverrides(products, overrides) {
  if (!overrides.length) return products;

  return products.map((product) => {
    const override = findOverrideForProduct(product, overrides);
    if (!override) return product;
    return {
      ...product,
      pdfSummaryOverride: override
    };
  });
}

function findOverrideForProduct(product, overrides) {
  return findOverrideByField(product, overrides, "fileName")
    || findOverrideByField(product, overrides, "msdsNo")
    || findOverrideByField(product, overrides, "productName")
    || null;
}

function findOverrideByField(product, overrides, field) {
  const productValue = normalizeSearchText(product[field]);
  if (!productValue) return null;
  return overrides.find((override) => normalizeSearchText(override.match?.[field]) === productValue);
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
    product.pdfSummaryOverride?.reviewStatus,
    product.pdfSummaryOverride?.extractStatus,
    product.pdfSummaryOverride?.signalWordCandidate,
    (product.pdfSummaryOverride?.hazardStatements || []).join(" "),
    flattenPrecautions(product.pdfSummaryOverride?.precautionaryStatements),
    (product.pdfSummaryOverride?.ppeCandidates || []).join(" "),
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
  renderPdfModal();
}

function getResultSubtitle(hasQuery, canShowCandidates, totalCount) {
  if (!hasQuery) return "검색어를 입력하면 후보 제품이 표시됩니다.";
  if (!canShowCandidates) return `${APP_CONFIG.minSearchCharacters}글자 이상 입력하면 후보 제품을 표시합니다.`;
  if (!totalCount) return "제품명, 용도, CAS No. 등으로 다시 검색해보세요.";
  if (state.showAllResults) return "전체 결과 표시 중";
  const start = Math.min(state.resultOffset + 1, totalCount);
  const end = Math.min(state.resultOffset + state.resultLimit, totalCount);
  return `현재 ${start}~${end}건 표시`;
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

  const selectedProduct = getSelectedProduct(results);
  if (state.selectionCollapsed && selectedProduct) {
    elements.selectionList.innerHTML = `
      <div class="selection-collapsed-card">
        <div>
          <span class="selection-collapsed-label">선택된 제품</span>
          <strong>${escapeHtml(selectedProduct.productName)}</strong>
          <span>${escapeHtml(selectedProduct.useCategory)} · ${escapeHtml(selectedProduct.supplier)}</span>
        </div>
        <button class="show-more-button" type="button" id="expandSelectionList">다른 제품 선택</button>
      </div>
    `;
    elements.selectionList.querySelector("#expandSelectionList")?.addEventListener("click", () => {
      state.selectionCollapsed = false;
      render();
    });
    return;
  }

  const maxOffset = Math.max(0, results.length - 1);
  state.resultOffset = Math.min(state.resultOffset, maxOffset);
  const startIndex = state.showAllResults ? 0 : state.resultOffset;
  const endIndex = state.showAllResults ? results.length : Math.min(results.length, startIndex + state.resultLimit);
  const visibleResults = results.slice(startIndex, endIndex);
  const hasPrevious = !state.showAllResults && startIndex > 0;
  const hasNext = !state.showAllResults && endIndex < results.length;
  const hasMore = !state.showAllResults && state.resultLimit < results.length;
  elements.selectionList.innerHTML = `
    <div class="result-range">
      ${state.showAllResults
        ? `전체 ${results.length}건 표시 중`
        : `현재 ${startIndex + 1}~${endIndex}건 표시 / 전체 ${results.length}건`}
    </div>
    <div class="selection-scroll">
      ${visibleResults.map((product) => `
        <button class="selection-item ${product.id === state.selectedId ? "is-selected" : ""}" type="button" data-product-id="${escapeAttribute(product.id)}">
          <span class="selection-name">${escapeHtml(product.productName)}</span>
          <span class="selection-meta">${escapeHtml(product.useCategory)} · ${escapeHtml(product.supplier)}</span>
        </button>
      `).join("")}
    </div>
    <div class="result-navigation" aria-label="제품 검색 결과 이동">
      ${state.showAllResults
        ? `<button class="result-nav-button result-collapse-button" type="button" id="collapseResults">접기</button>`
        : `
          ${hasPrevious ? `<button class="result-nav-button" type="button" id="showPreviousResults">위로</button>` : ""}
          ${hasNext ? `<button class="result-nav-button" type="button" id="showNextResults">아래로</button>` : ""}
          ${hasMore ? `<button class="result-nav-button" type="button" id="showMoreResults">더보기</button>` : ""}
          ${results.length > APP_CONFIG.initialResultLimit ? `<button class="result-nav-button" type="button" id="showAllResults">모두보기</button>` : ""}
        `}
    </div>
  `;

  elements.selectionList.querySelectorAll("[data-product-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.productId;
      state.selectionCollapsed = true;
      render();
    });
  });

  elements.selectionList.querySelector("#showMoreResults")?.addEventListener("click", () => {
    state.resultLimit += APP_CONFIG.initialResultLimit;
    state.resultOffset = 0;
    render();
  });

  elements.selectionList.querySelector("#showPreviousResults")?.addEventListener("click", () => {
    state.resultOffset = Math.max(0, state.resultOffset - state.resultLimit);
    render();
  });

  elements.selectionList.querySelector("#showNextResults")?.addEventListener("click", () => {
    state.resultOffset = Math.min(results.length - 1, state.resultOffset + state.resultLimit);
    render();
  });

  elements.selectionList.querySelector("#showAllResults")?.addEventListener("click", () => {
    state.showAllResults = true;
    state.resultOffset = 0;
    render();
  });

  elements.selectionList.querySelector("#collapseResults")?.addEventListener("click", () => {
    resetResultWindow();
    render();
  });
}

function renderPoster(product) {
  if (!product) {
    elements.posterPanel.className = "poster-board";
    elements.posterPanel.innerHTML = `<div class="poster-empty">선택된 제품이 없습니다.</div>`;
    return;
  }

  const posterData = getPosterData(product);
  elements.posterPanel.className = `poster-board ${posterData.statusClass}`;
  elements.posterPanel.innerHTML = `
    ${posterData.showReviewStrip ? `
      <div class="poster-review-strip">
        <span class="review-badge ${posterData.statusClass}">${escapeHtml(posterData.reviewBadge)}</span>
        <span>${escapeHtml(posterData.reviewMessage)}</span>
      </div>
    ` : ""}
    <div class="poster-product-row">
      <h2>${escapeHtml(product.productName)}</h2>
      <span class="hazard-badge">${escapeHtml(posterData.hazardBadge)}</span>
    </div>
    <div class="poster-ghs-row">
      ${renderGhsListFromItems(posterData.ghsPictograms, "poster")}
    </div>
    ${posterSection(posterData.hazardTitle, renderBulletList(posterData.hazardStatements, posterData.isCandidate), "poster-hazard-statements")}
    ${posterSection(posterData.precautionTitle, renderPrecautions(posterData.precautionaryStatements, posterData.isCandidate), "poster-precaution-statements")}
    ${posterData.ppeCandidates.length ? posterSection(posterData.ppeTitle, renderBulletList(posterData.ppeCandidates, posterData.isCandidate), "poster-ppe-candidates") : ""}
    <footer class="poster-footer">
      ${posterData.footerNotice.map((notice) => `<p>${escapeHtml(notice)}</p>`).join("")}
      <p>공급자 정보: ${escapeHtml(product.supplier)}</p>
      ${posterData.showSourcePdfPath && posterData.sourcePdfPath ? `<p>PDF 출처: ${escapeHtml(posterData.sourcePdfPath)}</p>` : ""}
    </footer>
  `;
}

function getPosterData(product) {
  const override = product.pdfSummaryOverride;
  if (canUseOverride(override) && hasOverrideSummary(override)) {
    const isReviewed = override.reviewStatus === "검토완료";
    const showReviewStatus = shouldShowReviewStatusOnFieldPoster();
    return {
      statusClass: isReviewed ? "is-reviewed" : "is-review-needed",
      showReviewStrip: showReviewStatus,
      reviewBadge: isReviewed ? "검토완료" : "PDF 추출 후보 / 검토 필요",
      reviewMessage: isReviewed
        ? "검토 완료된 PDF 기반 요약정보입니다."
        : "PDF 자동 추출 후보입니다. 현장 사용 전 검토가 필요합니다.",
      hazardBadge: override.signalWordCandidate || product.hazardBadge || "확인",
      ghsPictograms: override.ghsPictograms || [],
      hazardStatements: override.hazardStatements || [],
      precautionaryStatements: override.precautionaryStatements || {},
      ppeCandidates: limitList(override.ppeCandidates || [], 5),
      ppeTitle: "PPE 및 보호구",
      hazardTitle: "유해 위험 문구",
      precautionTitle: "예방조치 문구",
      footerNotice: [
        "이 자료는 현장 확인용 요약본입니다.",
        "상세 사항은 우측 PDF 또는 정식 MSDS를 참고하세요."
      ],
      sourcePdfPath: override.sourcePdfPath || "",
      showSourcePdfPath: !APP_CONFIG.fieldDisplayMode,
      isCandidate: !isReviewed && showReviewStatus
    };
  }

  const hasProductSummary = hasAnySummary(product.ghsPictograms, product.hazardStatements, product.precautionaryStatements);
  const showUnregisteredStatus = !APP_CONFIG.fieldDisplayMode;
  return {
    statusClass: hasProductSummary ? "" : "is-unregistered-summary",
    showReviewStrip: !hasProductSummary && showUnregisteredStatus,
    reviewBadge: hasProductSummary ? "" : "요약정보 미등록",
    reviewMessage: hasProductSummary ? "" : "정식 MSDS PDF를 확인하세요.",
    hazardBadge: product.hazardBadge || "확인",
    ghsPictograms: product.ghsPictograms || [],
    hazardStatements: product.hazardStatements || [],
    precautionaryStatements: product.precautionaryStatements || {},
    ppeCandidates: [],
    ppeTitle: "PPE 및 보호구",
    hazardTitle: "유해 위험 문구",
    precautionTitle: "예방조치 문구",
    footerNotice: [
      "이 자료는 현장 확인용 요약본입니다.",
      "상세 사항은 우측 PDF 또는 정식 MSDS를 참고하세요."
    ],
    sourcePdfPath: "",
    showSourcePdfPath: false,
    isCandidate: false
  };
}

function shouldShowReviewStatusOnFieldPoster() {
  return !APP_CONFIG.fieldDisplayMode || APP_CONFIG.showReviewStatusOnFieldPoster;
}

function shouldShowExtractionStatusInDetail() {
  return !APP_CONFIG.fieldDisplayMode || APP_CONFIG.showExtractionStatusInDetail;
}

function canUseOverride(override) {
  if (!override) return false;
  return override.reviewStatus === "검토완료" || APP_CONFIG.allowCandidateOverrideDisplay;
}

function hasOverrideSummary(override) {
  return hasAnySummary(override.ghsPictograms, override.hazardStatements, override.precautionaryStatements)
    || Boolean(override.signalWordCandidate)
    || Boolean(override.sourcePdfPath)
    || Boolean((override.ppeCandidates || []).length);
}

function hasAnySummary(ghsPictograms = [], hazardStatements = [], precautions = {}) {
  return Boolean((ghsPictograms || []).length)
    || Boolean((hazardStatements || []).length)
    || Object.values(precautions || {}).some((items) => Array.isArray(items) && items.length);
}

function renderDetail(product) {
  if (!product) {
    elements.detailPanel.className = "detail-panel empty-detail";
    elements.detailPanel.innerHTML = `<p>선택할 제품이 없습니다.</p>`;
    return;
  }

  const pdfInfo = buildPdfInfo(product);
  const override = product.pdfSummaryOverride;
  const detailData = getDetailData(product);
  const workerCautions = buildWorkerCautionPoints(product, detailData);
  const isFieldMode = APP_CONFIG.fieldDisplayMode;
  elements.detailPanel.className = `detail-panel ${isFieldMode ? "is-field-mode" : "is-review-mode"}`;
  elements.detailPanel.innerHTML = `
    ${detailSection("제품 기본정보", `
      <div class="info-grid">
        ${detailItem("제품명", detailData.productName)}
        ${detailItem("ERP 품명", product.erpName)}
        ${detailItem("MSDS번호", detailData.msdsNo)}
        ${detailItem("파일명", product.fileName)}
        ${detailItem("용도분류", product.useCategory)}
        ${detailItem("권고용도/사용용도", product.recommendedUse)}
        ${detailItem("제조사/공급업체", detailData.supplier)}
        ${detailItem("정보제공 및 긴급연락처", product.emergencyContact)}
        ${detailItem("개정일", detailData.revisionDate)}
      </div>
    `)}

    ${!isFieldMode ? detailSection("핵심 위험 요약", `
      <div class="risk-summary-grid">
        ${summaryItem("주요 유해성 분류", detailData.hazardSummary, "danger")}
        ${summaryItem("위험물 구분", product.dangerousGoods, "warning")}
        ${summaryItem("PPE 요약", detailData.ppeSummary, "protect")}
      </div>
      ${detailData.overrideApplied && APP_CONFIG.fieldDisplayMode ? `<p class="summary-note pdf-summary-applied">PDF 기반 요약정보 반영됨</p>` : ""}
    `) : ""}

    ${shouldRenderExtractionStatusSection(override) ? detailSection("PDF 요약 추출 상태", renderOverrideDetail(override)) : ""}

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

    ${detailSection("작업자 주의 포인트", `
      ${renderWorkerCautionPoints(workerCautions)}
      ${!isFieldMode ? `
        ${detailData.signalWord ? `<p class="summary-note"><strong>신호어:</strong> ${escapeHtml(detailData.signalWord)}</p>` : ""}
        <div class="ghs-grid">${renderGhsListFromItems(detailData.ghsPictograms, "large")}</div>
        <h4 class="detail-subheading">유해 위험 문구</h4>
        ${renderDetailList(detailData.hazardStatements)}
        <h4 class="detail-subheading">예방조치 문구</h4>
        ${renderPrecautions(detailData.precautionaryStatements)}
        ${detailData.ppeCandidates.length ? `<h4 class="detail-subheading">PPE 및 보호구</h4>${renderDetailList(detailData.ppeCandidates)}` : ""}
      ` : ""}
    `)}

    ${detailSection("PDF 미리보기", `
      ${renderPdfPreview(pdfInfo)}
    `)}
  `;
}

function getDetailData(product) {
  const override = canUseOverride(product.pdfSummaryOverride) ? product.pdfSummaryOverride : null;
  const overrideApplied = Boolean(override && hasOverrideSummary(override));
  const hazardStatements = override?.hazardStatements?.length ? override.hazardStatements : (product.hazardStatements || []);
  const precautionaryStatements = hasPrecautionSummary(override?.precautionaryStatements)
    ? override.precautionaryStatements
    : (product.precautionaryStatements || {});
  const ppeCandidates = override?.ppeCandidates?.length ? override.ppeCandidates : [];

  return {
    overrideApplied,
    productName: displayValue(override?.productNameCandidate, product.productName),
    supplier: displayValue(override?.supplierCandidate, product.supplier),
    msdsNo: displayValue(override?.msdsNoCandidate, product.msdsNo),
    revisionDate: displayValue(override?.revisionDateCandidate, product.revisionDate),
    signalWord: override?.signalWordCandidate || "",
    hazardSummary: displayValue(summarizeItems(hazardStatements, 2, " / "), product.hazardSummary),
    ppeSummary: displayValue(summarizeItems(ppeCandidates, 3, ", "), product.ppeSummary),
    ghsPictograms: override?.ghsPictograms?.length ? override.ghsPictograms : (product.ghsPictograms || []),
    hazardStatements,
    precautionaryStatements,
    ppeCandidates
  };
}

function buildWorkerCautionPoints(product, detailData) {
  const groups = {
    work: [],
    ppe: [],
    ventilation: [],
    fireStorage: [],
    legal: []
  };
  const componentText = (product.components || []).map((component) => [
    component.chemicalName,
    component.casNo,
    component.controlledSubstance ? `관리대상 ${component.controlledSubstance}` : "",
    component.workEnvironmentMeasurement ? `작업환경측정 ${component.workEnvironmentMeasurement}` : "",
    component.specialHealthExam ? `특수건강진단 ${component.specialHealthExam}` : ""
  ].join(" ")).join(" ");
  const text = normalizeSearchText([
    product.productName,
    product.erpName,
    product.useCategory,
    product.recommendedUse,
    product.hazardSummary,
    product.dangerousGoods,
    product.ppeSummary,
    detailData.hazardSummary,
    detailData.ppeSummary,
    detailData.signalWord,
    (detailData.hazardStatements || []).join(" "),
    flattenPrecautions(detailData.precautionaryStatements),
    (detailData.ppeCandidates || []).join(" "),
    (detailData.ghsPictograms || []).map((item) => `${item.code || ""} ${item.label || ""}`).join(" "),
    componentText
  ].join(" "));

  addCautionIf(groups.work, text, ["인화", "가연", "화재", "스파크", "화염", "flam", "fire"], "화기, 스파크, 고온 표면 근처에서 사용하지 말고 점화원을 관리하세요.");
  addCautionIf(groups.work, text, ["분사", "도포", "혼합", "미스트", "mist"], "분사, 도포, 혼합 작업 시 증기나 미스트 발생 여부를 확인하세요.");
  addCautionIf(groups.work, text, ["고압가스", "gas", "cylinder"], "고압가스 용기는 충격과 고온 노출을 피하고 고정 상태를 확인하세요.");

  addCautionIf(groups.ppe, text, ["보안경", "보호장갑", "호흡보호구", "보호구", "ppe", "goggle", "glove", "respir"], "작업 전 지정된 보호구 착용 상태를 확인하세요.");
  addCautionIf(groups.ppe, text, ["눈", "피부", "자극", "부식", "corros", "irrit"], "눈과 피부 접촉을 피하고 보안경과 보호장갑을 착용하세요.");
  addCautionIf(groups.ppe, text, ["호흡", "흡입", "유기용제", "용제", "vapor", "respir"], "필요 시 유기용제용 호흡보호구 착용을 검토하세요.");

  addCautionIf(groups.ventilation, text, ["증기", "미스트", "분진", "흡입", "호흡", "환기", "국소배기", "vapor", "mist", "dust", "inhal"], "작업장은 충분히 환기하고 필요 시 국소배기 상태를 확인하세요.");
  addCautionIf(groups.ventilation, text, ["톨루엔", "자일렌", "mibk", "butylacetate", "nbutylacetate", "ethylbenzene", "에틸벤젠", "부틸아세테이트", "유기용제", "용제"], "유기용제 증기 노출을 줄이고 장시간 흡입을 피하세요.");
  addCautionIf(groups.ventilation, text, ["반복노출", "장기간", "신체손상", "노출"], "반복 노출 가능성이 있는 작업은 작업시간과 환기 상태를 함께 확인하세요.");

  addCautionIf(groups.fireStorage, text, ["제4류", "위험물", "인화성액체", "flammableliquid"], "위험물 보관 기준에 맞게 관리하고 주변 점화원을 제거하세요.");
  addCautionIf(groups.fireStorage, text, ["인화", "고온", "직사광선", "화기", "보관", "storage"], "인화성 물질은 고온, 직사광선, 화기 근처에 보관하지 마세요.");
  addCautionIf(groups.fireStorage, text, ["밀폐", "용기", "폐기", "disposal"], "사용 후 용기는 밀폐하고 지정 보관장소에 보관하세요.");

  addCautionIf(groups.legal, text, ["관리대상", "작업환경측정", "특수건강진단"], "관리대상 유해물질 여부를 확인하세요.");
  addCautionIf(groups.legal, text, ["작업환경측정", "특수건강진단"], "작업환경측정 및 특수건강진단 대상 여부를 확인하세요.");
  addCautionIf(groups.legal, text, ["cas", "casno", "관리대상", "성분"], "성분정보와 CAS No. 기준으로 관리대상 여부를 확인하세요.");

  const totalCount = Object.values(groups).reduce((sum, items) => sum + items.length, 0);
  if (!totalCount) {
    return {
      emptyMessage: "현재 데이터만으로 자동 주의 포인트를 충분히 생성하기 어렵습니다. 정식 MSDS PDF를 확인하세요.",
      sections: []
    };
  }

  return {
    emptyMessage: "",
    sections: [
      { key: "work", title: "현장 작업 중 주의사항", items: groups.work },
      { key: "ppe", title: "보호구 착용사항", items: groups.ppe },
      { key: "ventilation", title: "환기 및 노출관리", items: groups.ventilation },
      { key: "fireStorage", title: "화재·보관 관리", items: groups.fireStorage },
      { key: "legal", title: "법적관리 확인사항", items: groups.legal }
    ].map((section) => ({
      ...section,
      items: section.items.slice(0, 5)
    })).filter((section) => section.items.length)
  };
}

function addCautionIf(points, normalizedText, keywords, message) {
  if (points.includes(message)) return;
  if (keywords.some((keyword) => normalizedText.includes(normalizeSearchText(keyword)))) {
    points.push(message);
  }
}

function renderWorkerCautionPoints(cautionData) {
  const sections = cautionData.sections || [];
  return `
    <div class="worker-caution-box">
      <p class="worker-caution-subtitle">MSDS 및 성분정보를 바탕으로 정리한 참고용 안내입니다.</p>
      ${sections.length ? `
        <div class="worker-caution-categories">
          ${sections.map((section) => `
            <section class="worker-caution-category">
              <h4>${escapeHtml(section.title)}</h4>
              <ul class="worker-caution-list">
                ${section.items.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}
              </ul>
            </section>
          `).join("")}
        </div>
      ` : `<p class="summary-note">${escapeHtml(cautionData.emptyMessage)}</p>`}
    </div>
  `;
}

function displayValue(preferred, fallback) {
  const preferredText = Array.isArray(preferred) ? preferred.filter(Boolean).join(", ") : String(preferred || "").trim();
  if (preferredText) return preferredText;
  const fallbackText = String(fallback || "").trim();
  return fallbackText || "정보 없음";
}

function summarizeItems(items = [], limit = 3, separator = ", ") {
  if (!Array.isArray(items) || !items.length) return "";
  const visible = items.filter(Boolean).slice(0, limit);
  const suffix = items.length > visible.length ? ` 외 ${items.length - visible.length}건` : "";
  return `${visible.join(separator)}${suffix}`;
}

function limitList(items = [], limit = 5) {
  if (!Array.isArray(items) || items.length <= limit) return items || [];
  return [...items.slice(0, limit), `외 ${items.length - limit}건은 PDF 원본에서 확인하세요.`];
}

function hasPrecautionSummary(precautions = {}) {
  return Object.values(precautions || {}).some((items) => Array.isArray(items) && items.length);
}

function shouldRenderExtractionStatusSection(override) {
  return Boolean(override) && shouldShowExtractionStatusInDetail();
}

function renderOverrideDetail(override) {
  if (!override) {
    return `<p class="summary-note">PDF 요약 후보가 아직 연결되지 않았습니다.</p>`;
  }

  return `
    <div class="override-status-box ${override.reviewStatus === "검토완료" ? "is-reviewed" : "is-review-needed"}">
      ${detailItem("PDF 요약 추출 상태", override.extractStatus || "미확인")}
      ${detailItem("검토 상태", override.reviewStatus || "검토필요")}
      ${detailItem("PDF 출처", override.sourcePdfPath || "")}
      ${detailItem("후보 항목", `GHS ${override.ghsPictograms.length}건 / 유해문구 ${override.hazardStatements.length}건 / 구성성분 후보 ${override.ingredients.length}건`)}
    </div>
  `;
}

function buildPdfInfo(product) {
  const fileName = String(product.fileName || "").trim();
  if (!fileName) {
    return {
      status: "no-file-name",
      displayPath: "",
      encodedPath: "",
      title: product.productName || "PDF 미리보기"
    };
  }

  const displayPath = product.pdfPath || `/pdf/${fileName}`;
  return {
    status: state.pdfAvailability[encodePdfPath(displayPath)] || "unchecked",
    displayPath,
    encodedPath: encodePdfPath(displayPath),
    title: product.productName || fileName
  };
}

function encodePdfPath(path) {
  return String(path || "")
    .split("/")
    .map((part, index) => {
      if (index === 0 && part === "") return "";
      try {
        return encodeURIComponent(decodeURIComponent(part));
      } catch (error) {
        return encodeURIComponent(part);
      }
    })
    .join("/");
}

function renderPdfPreview(pdfInfo) {
  if (pdfInfo.status === "no-file-name") {
    return `
      <div class="pdf-preview is-missing">
        <p class="pdf-message">파일명 정보가 없어 PDF 자동 연결이 어렵습니다.</p>
        <div class="pdf-frame-placeholder">파일명 컬럼 확인 필요</div>
        ${renderDownloadButton("")}
      </div>
    `;
  }

  if (pdfInfo.status === "unchecked") {
    schedulePdfAvailabilityCheck(pdfInfo.encodedPath);
    pdfInfo.status = "checking";
  }

  if (pdfInfo.status === "available") {
    return `
      <div class="pdf-preview is-connected">
        <p class="pdf-message">PDF 연결 완료</p>
        <div class="info-item">
          <span class="info-label">PDF 경로</span>
          <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
        </div>
        ${APP_CONFIG.showPdfIframeWhenAvailable ? `<iframe class="pdf-frame" title="PDF 미리보기" src="${escapeAttribute(pdfInfo.encodedPath)}"></iframe>` : `<div class="pdf-frame-placeholder">PDF 연결이 확인되었습니다.</div>`}
        <div class="pdf-actions">
          <button class="pdf-enlarge-button" type="button" data-open-pdf-modal data-pdf-title="${escapeAttribute(pdfInfo.title)}" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}">크게 보기</button>
          <a class="pdf-open-button" href="${escapeAttribute(pdfInfo.encodedPath)}" target="_blank" rel="noopener">새 탭에서 열기</a>
          ${renderDownloadButton(pdfInfo.encodedPath)}
        </div>
      </div>
    `;
  }

  if (pdfInfo.status === "checking") {
    return `
      <div class="pdf-preview">
        <p class="pdf-message">PDF 파일 연결 상태 확인 중입니다.</p>
        <div class="info-item">
          <span class="info-label">확인 경로</span>
          <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
        </div>
        <div class="pdf-frame-placeholder">PDF 원본을 확인하고 있습니다.</div>
        ${renderDownloadButton("")}
      </div>
    `;
  }

  return `
    <div class="pdf-preview is-missing">
      <p class="pdf-message">PDF 파일이 아직 등록되지 않았습니다.</p>
      <div class="info-item">
        <span class="info-label">예상 경로</span>
        <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
      </div>
      <div class="pdf-frame-placeholder">PDF 원본을 pdf 폴더에 추가하면 자동 연결됩니다.</div>
      ${renderDownloadButton("")}
    </div>
  `;
}

function renderDownloadButton(path) {
  if (!APP_CONFIG.showDownloadButton) {
    return `<a class="download-button is-hidden" href="${escapeAttribute(path)}" download>다운로드</a>`;
  }
  return `<a class="download-button" href="${escapeAttribute(path)}" download>다운로드</a>`;
}

function schedulePdfAvailabilityCheck(path) {
  state.pdfAvailability[path] = "checking";
  checkPdfExists(path).then((exists) => {
    state.pdfAvailability[path] = exists ? "available" : "missing";
    const selected = state.products.find((product) => product.id === state.selectedId);
    if (selected && buildPdfInfo(selected).encodedPath === path) render();
  });
}

async function checkPdfExists(path) {
  if (!path || window.location.protocol === "file:") return false;

  try {
    const response = await fetch(path, { method: "HEAD", cache: "no-store" });
    if (response.ok) return true;
    if (response.status !== 405) return false;
  } catch (error) {
    return false;
  }

  try {
    const response = await fetch(path, {
      method: "GET",
      cache: "no-store",
      headers: { Range: "bytes=0-0" }
    });
    return response.ok || response.status === 206;
  } catch (error) {
    return false;
  }
}

function openPdfModal(title, path) {
  if (!path) return;
  state.pdfModal = {
    isOpen: true,
    title: title || "PDF 미리보기",
    path
  };
  renderPdfModal();
}

function closePdfModal() {
  state.pdfModal = {
    isOpen: false,
    title: "",
    path: ""
  };
  renderPdfModal();
}

function ensurePdfModalElement() {
  let modal = document.querySelector("#pdfPreviewModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "pdfPreviewModal";
    document.body.appendChild(modal);
  }
  return modal;
}

function renderPdfModal() {
  const modal = ensurePdfModalElement();
  document.body.classList.toggle("modal-open", state.pdfModal.isOpen);

  if (!state.pdfModal.isOpen) {
    modal.className = "pdf-modal is-hidden";
    modal.innerHTML = "";
    return;
  }

  modal.className = "pdf-modal";
  modal.innerHTML = `
    <div class="pdf-modal-backdrop">
      <section class="pdf-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="pdfModalTitle">
        <header class="pdf-modal-toolbar">
          <div>
            <h2 id="pdfModalTitle">PDF 미리보기</h2>
            <p>${escapeHtml(state.pdfModal.title)}</p>
          </div>
          <button class="pdf-modal-close" type="button" data-close-pdf-modal aria-label="PDF 크게 보기 닫기">닫기</button>
        </header>
        <iframe class="pdf-modal-frame" title="${escapeAttribute(state.pdfModal.title)} PDF 크게 보기" src="${escapeAttribute(state.pdfModal.path)}"></iframe>
      </section>
    </div>
  `;
  modal.querySelector("[data-close-pdf-modal]")?.focus();
}

function posterSection(title, content, className) {
  return `
    <section class="poster-block ${escapeAttribute(className)}">
      <h3><span aria-hidden="true">■</span> ${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;
}

function renderBulletList(items, isCandidate = false) {
  if (!items.length) return `<p class="empty-text">등록된 문구가 없습니다.</p>`;
  return `<ul class="poster-list ${isCandidate ? "is-candidate" : ""}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDetailList(items) {
  if (!items.length) return `<p class="summary-note">정보 없음</p>`;
  const visible = items.slice(0, 5);
  const moreCount = items.length - visible.length;
  return `
    <ul class="detail-list">${visible.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    ${moreCount > 0 ? `<p class="summary-note">외 ${moreCount}건은 PDF 원본에서 확인하세요.</p>` : ""}
  `;
}

function renderPrecautions(precautions, isCandidate = false) {
  const groups = Object.entries(PRECAUTION_LABELS).map(([key, label]) => {
    const items = Array.isArray(precautions[key]) ? precautions[key] : [];
    if (!items.length) return "";
    return `
      <div class="precaution-group ${isCandidate ? "is-candidate" : ""}">
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
  return renderGhsListFromItems(product.ghsPictograms, size);
}

function renderGhsListFromItems(items, size) {
  const list = normalizeGhsList({ ghsPictograms: items || [] });
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
