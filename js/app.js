"use strict";

const APP_CONFIG = {
  localDataUrl: "data/msds.local.json",
  publicDataUrl: "data/msds.public.json",
  sampleDataUrl: "data/msds-sample.json",
  localOverridesUrl: "data/msds-overrides.local.json",
  publicOverridesUrl: "data/msds-overrides.public.json",
  sampleOverridesUrl: "data/msds-overrides.sample.json",
  localInventoryUrl: "data/pdf-inventory.local.json",
  sampleInventoryUrl: "data/pdf-inventory.sample.json",
  pdfJsModuleUrl: "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.mjs",
  pdfJsWorkerUrl: "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.mjs",
  minSearchCharacters: 2,
  initialResultLimit: 8,
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
        workEnvironmentMeasurement: "",
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
        workEnvironmentMeasurement: "",
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
        workEnvironmentMeasurement: "",
        specialHealthExam: "해당 없음"
      }
    ]
  }
];

const GHS_DEFINITIONS = {
  GHS01: { label: "폭발성", icon: "assets/ghs/ghs01.svg", order: 1 },
  GHS02: { label: "인화성", icon: "assets/ghs/ghs02.svg", order: 2 },
  GHS03: { label: "산화성", icon: "assets/ghs/ghs03.svg", order: 3 },
  GHS04: { label: "고압가스", icon: "assets/ghs/ghs04.svg", order: 4 },
  GHS05: { label: "부식성", icon: "assets/ghs/ghs05.svg", order: 5 },
  GHS06: { label: "급성독성", icon: "assets/ghs/ghs06.svg", order: 6 },
  GHS07: { label: "유해/자극성", icon: "assets/ghs/ghs07.svg", order: 7 },
  GHS08: { label: "건강유해성", icon: "assets/ghs/ghs08.svg", order: 8 },
  GHS09: { label: "환경유해성", icon: "assets/ghs/ghs09.svg", order: 9 }
};

const GHS_CODE_ALIASES = {
  explosive: "GHS01",
  explosion: "GHS01",
  flame: "GHS02",
  flammable: "GHS02",
  oxidizer: "GHS03",
  oxidizing: "GHS03",
  gas: "GHS04",
  cylinder: "GHS04",
  corrosion: "GHS05",
  corrosive: "GHS05",
  skull: "GHS06",
  skullcrossbones: "GHS06",
  exclamation: "GHS07",
  irritant: "GHS07",
  harmful: "GHS07",
  health: "GHS08",
  healthhazard: "GHS08",
  environment: "GHS09",
  aquatic: "GHS09",
  "폭발성": "GHS01",
  "인화성": "GHS02",
  "산화성": "GHS03",
  "고압가스": "GHS04",
  "부식성": "GHS05",
  "급성독성": "GHS06",
  "유해자극성": "GHS07",
  "건강유해성": "GHS08",
  "환경유해성": "GHS09",
  "??": "GHS07",
  "???": "GHS07"
};

const HAZARD_CLASSIFICATION_GHS_RULES = [
  {
    code: "GHS01",
    reason: "explosive",
    matches: (segments) => hasAnySegment(segments, ["폭발성"], ["구분1", "구분2", "구분3", "구분4", "구분5"])
      || hasAnySegment(segments, ["자기반응성", "유기과산화물"], ["구분a", "구분b"])
      || hasAnyText(segments, ["h200", "h201", "h202", "h203", "h204", "h205"])
  },
  {
    code: "GHS02",
    reason: "flammable",
    matches: (segments) => hasAnySegment(segments, ["인화성액체"], ["구분1", "구분2", "구분3"])
      || hasAnySegment(segments, ["인화성가스", "인화성에어로졸", "인화성고체", "가연성가스", "자연발화성", "자기발열성", "물반응성"], ["구분1", "구분2"])
      || hasAnyText(segments, ["h220", "h221", "h222", "h223", "h224", "h225", "h226", "h228", "h240", "h241", "h242", "h250", "h251", "h252", "h260", "h261"])
  },
  {
    code: "GHS03",
    reason: "oxidizing",
    matches: (segments) => hasAnySegment(segments, ["산화성"], ["구분1", "구분2", "구분3"])
      || hasAnyText(segments, ["h270", "h271", "h272"])
  },
  {
    code: "GHS04",
    reason: "gas-cylinder",
    matches: (segments) => hasAnyText(segments, ["고압가스", "압축가스", "액화가스", "냉동액화가스", "용해가스", "h280", "h281"])
  },
  {
    code: "GHS05",
    reason: "corrosion",
    matches: (segments) => hasAnySegment(segments, ["금속부식성", "금속부식성물질"], ["구분1"])
      || hasAnySegment(segments, ["피부부식성", "피부부식성피부자극성"], ["구분1", "구분1a", "구분1b", "구분1c"])
      || hasAnySegment(segments, ["심한눈손상성", "눈손상성눈자극성", "심한눈손상성눈자극성"], ["구분1"])
      || hasAnyText(segments, ["h290", "h314", "h318"])
  },
  {
    code: "GHS06",
    reason: "acute-toxic-severe",
    matches: (segments) => hasAnySegment(segments, ["급성독성"], ["구분1", "구분2", "구분3"])
      || hasAnyText(segments, ["h300", "h301", "h310", "h311", "h330", "h331"])
  },
  {
    code: "GHS07",
    reason: "harmful-irritant",
    matches: (segments) => hasAnySegment(segments, ["급성독성"], ["구분4"])
      || hasAnySegment(segments, ["피부자극성", "피부부식성피부자극성"], ["구분2"])
      || hasAnySegment(segments, ["눈자극성", "눈손상성눈자극성", "심한눈손상성눈자극성"], ["구분2", "구분2a"])
      || hasAnySegment(segments, ["피부과민성"], ["구분1", "구분1a", "구분1b"])
      || hasAnySegment(segments, ["특정표적장기독성1회노출"], ["구분3"])
      || hasAnyText(segments, ["h302", "h312", "h315", "h317", "h319", "h332", "h335", "h336"])
  },
  {
    code: "GHS08",
    reason: "health-hazard",
    matches: (segments) => hasAnySegment(segments, ["호흡기과민성"], ["구분1", "구분1a", "구분1b"])
      || hasAnySegment(segments, ["생식세포변이원성", "변이원성"], ["구분1", "구분1a", "구분1b", "구분2"])
      || hasAnySegment(segments, ["발암성"], ["구분1", "구분1a", "구분1b", "구분2"])
      || hasAnySegment(segments, ["생식독성"], ["구분1", "구분1a", "구분1b", "구분2"])
      || hasAnySegment(segments, ["특정표적장기독성1회노출", "특정표적장기독성반복노출"], ["구분1", "구분2"])
      || hasAnySegment(segments, ["흡인유해성"], ["구분1", "구분2"])
      || hasAnyText(segments, ["h304", "h334", "h340", "h341", "h350", "h351", "h360", "h361", "h370", "h371", "h372", "h373"])
  },
  {
    code: "GHS09",
    reason: "environment",
    matches: (segments) => hasAnySegment(segments, ["수생환경유해성급성", "급성수생환경유해성"], ["구분1"])
      || hasAnySegment(segments, ["수생환경유해성만성", "만성수생환경유해성"], ["구분1", "구분2"])
      || hasAnyText(segments, ["h400", "h410", "h411"])
  }
];

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
  showFullList: false,
  showBackToFullList: false,
  fullListReturnY: 0,
  selectionCollapsed: false,
  dataMode: "샘플 데이터 모드",
  publicNotice: "",
  pdfOverrides: [],
  pdfInventory: [],
  pdfOnlyProducts: [],
  pdfPreview: {
    path: "",
    title: "",
    status: "idle",
    error: "",
    totalPages: 0,
    renderedPages: 0,
    scale: 1,
    fitRatio: 0.88,
    fitToWidth: true,
    expanded: false,
    currentPage: 1,
    restorePage: null,
    restoreOffsetRatio: 0,
    document: null,
    renderToken: 0,
    suppressPageTracking: false
  },
  pdfFullView: {
    isOpen: false,
    path: "",
    title: "",
    status: "idle",
    error: "",
    totalPages: 0,
    renderedPages: 0,
    scale: 1,
    fitRatio: 0.92,
    fitToWidth: true,
    currentPage: 1,
    restorePage: null,
    restoreOffsetRatio: 0,
    document: null,
    renderToken: 0,
    suppressPageTracking: false
  }
};

const elements = {};
let pdfJsModulePromise = null;

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  const data = await loadProducts();
  state.pdfOverrides = data.overrides || [];
  state.pdfInventory = data.inventory || [];
  state.products = data.products;
  state.pdfOnlyProducts = buildPdfOnlyProducts(state.products, state.pdfInventory, state.pdfOverrides);
  state.dataMode = data.mode;
  state.publicNotice = data.publicNotice || "";
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
  elements.publicDeployNotice = document.querySelector("#publicDeployNotice");
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    state.showFullList = false;
    resetFullListNavigation();
    resetResultWindow();
    state.selectionCollapsed = false;
    updateSelectedProductForQuery();
    render();
  });

  elements.clearSearch.addEventListener("click", () => {
    state.query = "";
    elements.searchInput.value = "";
    state.showFullList = false;
    resetFullListNavigation();
    resetResultWindow();
    state.selectedId = state.products[0]?.id || null;
    state.selectionCollapsed = false;
    elements.searchInput.focus();
    render();
  });

  elements.quickSearch.addEventListener("click", (event) => {
    const showAllButton = event.target.closest("button[data-action='show-all']");
    if (showAllButton) {
      state.query = "";
      elements.searchInput.value = "";
      state.showFullList = true;
      resetFullListNavigation();
      resetResultWindow();
      state.selectionCollapsed = false;
      state.selectedId = state.selectedId || state.products[0]?.id || null;
      render();
      return;
    }

    const button = event.target.closest("button[data-query]");
    if (!button) return;
    state.query = button.dataset.query;
    elements.searchInput.value = state.query;
    state.showFullList = false;
    resetFullListNavigation();
    resetResultWindow();
    state.selectionCollapsed = false;
    updateSelectedProductForQuery();
    render();
  });

  document.addEventListener("click", (event) => {
    const returnButton = event.target.closest("[data-return-full-list]");
    if (returnButton) {
      scrollBackToFullList();
      return;
    }

    const detailButton = event.target.closest("[data-view-detail]");
    if (detailButton) {
      selectFullListProduct(detailButton.dataset.productId, true);
      return;
    }

    const viewerControl = event.target.closest("[data-pdf-viewer-action]");
    if (viewerControl) {
      handlePdfViewerAction(viewerControl.dataset.pdfViewerAction, viewerControl.closest("[data-pdfjs-preview-mount]"));
      return;
    }

    const closeFullViewButton = event.target.closest("[data-close-pdf-full-view]");
    if (closeFullViewButton) {
      closePdfFullView();
      return;
    }

    const fullViewButton = event.target.closest("[data-pdf-full-view]");
    if (fullViewButton) {
      startPdfFullView(fullViewButton.dataset.pdfTitle, fullViewButton.dataset.pdfPath);
      return;
    }

    const previewButton = event.target.closest("[data-preview-pdf]");
    if (previewButton) {
      startPdfPreview(previewButton.dataset.pdfTitle, previewButton.dataset.pdfPath);
      return;
    }

  });
}

function resetResultWindow() {
  state.resultLimit = APP_CONFIG.initialResultLimit;
  state.resultOffset = 0;
  state.showAllResults = false;
}

function resetFullListNavigation() {
  state.showBackToFullList = false;
  state.fullListReturnY = 0;
}

function selectFullListProduct(productId, shouldScrollToDetail = false) {
  if (!productId) return;
  if (state.selectedId !== productId) resetPdfPreviewState();
  state.selectedId = productId;
  state.selectionCollapsed = false;
  if (shouldScrollToDetail) {
    state.fullListReturnY = window.scrollY || 0;
    state.showBackToFullList = true;
  }
  render();
  if (shouldScrollToDetail) {
    document.querySelector(".detail-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function scrollBackToFullList() {
  const listTop = elements.selectionList
    ? elements.selectionList.getBoundingClientRect().top + window.scrollY
    : 0;
  const targetY = state.fullListReturnY || listTop;
  state.showBackToFullList = false;
  render();
  window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
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
  const pdfLookupData = await loadPdfLookupData();

  const localData = await fetchProducts(APP_CONFIG.localDataUrl);
  if (localData) {
    return {
      mode: "로컬 변환 데이터 모드",
      publicNotice: "",
      products: applyOverrides(localData.map(normalizeProduct), pdfLookupData.overrides),
      ...pdfLookupData
    };
  }

  const publicData = await fetchProducts(APP_CONFIG.publicDataUrl);
  if (publicData) {
    return {
      mode: "공개 운영 데이터 모드",
      publicNotice: "",
      products: applyOverrides(publicData.map(normalizeProduct), pdfLookupData.overrides),
      ...pdfLookupData
    };
  }

  const sampleData = await fetchProducts(APP_CONFIG.sampleDataUrl);
  if (sampleData) {
    return {
      mode: "샘플 데이터 모드",
      publicNotice: "샘플 데이터 화면입니다. 실제 운영 데이터가 로드되지 않았습니다.",
      products: applyOverrides(sampleData.map(normalizeProduct), pdfLookupData.overrides),
      ...pdfLookupData
    };
  }

  return {
    mode: "샘플 데이터 모드",
    publicNotice: "샘플 데이터 화면입니다. 실제 운영 데이터가 로드되지 않았습니다.",
    products: applyOverrides(FALLBACK_PRODUCTS.map(normalizeProduct), pdfLookupData.overrides),
    ...pdfLookupData
  };
}

async function loadPdfLookupData() {
  const [overrides, inventory] = await Promise.all([
    loadOverrides(),
    loadInventory()
  ]);
  return { overrides, inventory };
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

  const publicOverrides = await fetchOverrides(APP_CONFIG.publicOverridesUrl);
  if (publicOverrides) return publicOverrides.map(normalizeOverride);

  const sampleOverrides = await fetchOverrides(APP_CONFIG.sampleOverridesUrl);
  if (sampleOverrides) return sampleOverrides.map(normalizeOverride);

  return [];
}

async function loadInventory() {
  const localInventory = await fetchInventory(APP_CONFIG.localInventoryUrl);
  if (localInventory) return localInventory.map(normalizeInventoryItem);

  const sampleInventory = await fetchInventory(APP_CONFIG.sampleInventoryUrl);
  if (sampleInventory) return sampleInventory.map(normalizeInventoryItem);

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

async function fetchInventory(url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Inventory request failed: ${url}`);
    const data = await response.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.pdfs)) return data.pdfs;
    if (Array.isArray(data.inventory)) return data.inventory;
    return null;
  } catch (error) {
    return null;
  }
}

function normalizeProduct(product) {
  const ingredients = product.ingredients || product.components || [];
  const relativePdfPath = product.relativePath ? `pdf/${String(product.relativePath).replace(/^\/?pdf\//, "")}` : "";
  return {
    ...product,
    productName: product.productName || "",
    erpName: product.erpName || "",
    msdsNo: product.msdsNo || "",
    fileName: product.fileName || "",
    pdfPath: product.pdfPath || relativePdfPath || (product.fileName ? `pdf/${product.fileName}` : ""),
    useCategory: product.useCategory || product.category || "",
    recommendedUse: product.recommendedUse || "",
    supplier: product.supplier || "",
    emergencyContact: product.emergencyContact || "",
    hazardSummary: product.hazardSummary || product.hazardClassification || "",
    dangerousGoods: product.dangerousGoods || "",
    ppeSummary: product.ppeSummary || "",
    issueDate: product.issueDate || product.preparationDate || "",
    revisionDate: product.revisionDate || "",
    hazardBadge: product.hazardBadge || "확인",
    labelGhsCodes: normalizeGhsCodeList(product.labelGhsCodes || product.labelGhsPictograms || []),
    labelGhsPictograms: Array.isArray(product.labelGhsPictograms) ? product.labelGhsPictograms : [],
    classificationGhsCodes: normalizeGhsCodeList(product.classificationGhsCodes || product.classificationGhsPictograms || []),
    classificationGhsPictograms: Array.isArray(product.classificationGhsPictograms) ? product.classificationGhsPictograms : [],
    ghsCodes: normalizeGhsCodeList(product.ghsCodes || product.ghsPictograms || []),
    ghsPictograms: normalizeGhsList(product),
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
    ghsSource: override.ghsSource || "",
    labelGhsCodes: normalizeGhsCodeList(override.labelGhsCodes || override.labelGhsPictograms || []),
    labelGhsPictograms: Array.isArray(override.labelGhsPictograms) ? override.labelGhsPictograms : [],
    classificationGhsCodes: normalizeGhsCodeList(override.classificationGhsCodes || override.classificationGhsPictograms || []),
    classificationGhsPictograms: Array.isArray(override.classificationGhsPictograms) ? override.classificationGhsPictograms : [],
    ghsCodes: normalizeGhsCodeList(override.ghsCodes || override.ghsPictograms || []),
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

function normalizeInventoryItem(item) {
  return {
    ...item,
    fileName: item.fileName || getPathBasename(item.relativePath || item.pdfPath || ""),
    relativePath: item.relativePath || "",
    pdfPath: item.pdfPath || ""
  };
}

function buildPdfOnlyProducts(products = [], inventory = [], overrides = []) {
  const pdfSourceItems = getPdfSourceItems(inventory, overrides);
  const productPdfKeys = new Set(products.flatMap(getProductPdfNameKeys).filter(Boolean));
  const overrideProductKeys = new Set(
    overrides
      .filter((override) => products.some((product) => findOverrideForProduct(product, [override])))
      .flatMap(getOverridePdfKeys)
      .filter(Boolean)
  );
  const seenKeys = new Set();

  return pdfSourceItems.reduce((items, inventoryItem) => {
    if (shouldExcludeInventoryPdf(inventoryItem)) return items;

    const keys = getInventoryPdfKeys(inventoryItem);
    if (!keys.length) return items;
    if (keys.some((key) => productPdfKeys.has(key) || overrideProductKeys.has(key))) return items;
    if (keys.some((key) => seenKeys.has(key))) return items;

    keys.forEach((key) => seenKeys.add(key));
    items.push(createPdfOnlyProduct(inventoryItem, items.length, findOverrideForPdfSourceItem(inventoryItem, overrides)));
    return items;
  }, []);
}

function findOverrideForPdfSourceItem(item = {}, overrides = []) {
  const itemKeys = new Set(getInventoryPdfKeys(item));
  return overrides.find((override) => getOverridePdfKeys(override).some((key) => itemKeys.has(key))) || null;
}

function getPdfSourceItems(inventory = [], overrides = []) {
  const overrideItems = overrides.map((override) => {
    const match = override.match || {};
    const sourcePath = override.sourceRelativePath || override.sourcePdfPath || match.relativePath || match.fileName || "";
    const fileName = getPathBasename(sourcePath);
    return {
      fileName,
      relativePath: sourcePath,
      pdfPath: sourcePath,
      normalizedFileName: fileName,
      productNameCandidates: [override.productNameCandidate].filter(Boolean),
      msdsNoCandidates: [override.msdsNoCandidate].filter(Boolean),
      inventoryStatus: override.extractStatus || ""
    };
  }).filter((item) => item.fileName || item.relativePath || item.pdfPath);

  return [...inventory, ...overrideItems];
}

function getOverridePdfKeys(override = {}) {
  const match = override.match || {};
  return [
    match.fileName,
    match.relativePath,
    override.sourceRelativePath,
    override.sourcePdfPath
  ].map(getPdfIdentityKey).filter(Boolean);
}

function getInventoryPdfKeys(item = {}) {
  return [
    item.sha256,
    item.firstPagesTextFingerprint,
    item.relativePath,
    item.pdfPath,
    item.fileName,
    item.normalizedFileName
  ].map(getPdfIdentityKey).filter(Boolean);
}

function getPdfIdentityKey(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^[a-f0-9]{64}$/i.test(text)) return `hash:${text.toLowerCase()}`;
  return normalizeSearchText(getPathBasename(text) || text);
}

function shouldExcludeInventoryPdf(item = {}) {
  const text = [
    item.fileName,
    item.relativePath,
    item.pdfPath,
    item.normalizedFileName,
    item.inventoryStatus,
    item.textExtractStatus
  ].join(" ").toLowerCase();
  return text.includes("qr")
    || text.includes("non-msds")
    || text.includes("nonmsds")
    || text.includes("비msds")
    || text.includes("제외");
}

function createPdfOnlyProduct(item, index, override = null) {
  const fileName = item.fileName || getPathBasename(item.relativePath || item.pdfPath || "") || `MSDS ${index + 1}`;
  const candidateName = Array.isArray(item.productNameCandidates) ? item.productNameCandidates.find(Boolean) : "";
  const displayName = getPdfOnlyDisplayName({
    overrideName: override?.productNameCandidate,
    candidateName,
    fileName
  });
  const relativePath = item.relativePath || item.pdfPath || fileName;
  const supplierName = cleanPdfSupplierName(override?.supplierCandidate) || supplierFromPath(relativePath) || "업체 미확인";
  const revisionDate = cleanPdfRevisionDate(override?.revisionDateCandidate);

  return normalizeProduct({
    id: `msds-pdf-${item.sha256 || item.normalizedFileName || index}`,
    isPdfAbsorbed: true,
    productName: displayName,
    erpName: "",
    msdsNo: override?.msdsNoCandidate || (Array.isArray(item.msdsNoCandidates) ? item.msdsNoCandidates.find(Boolean) || "" : ""),
    fileName,
    pdfPath: normalizePdfDisplayPath(relativePath),
    relativePath,
    useCategory: "",
    recommendedUse: "",
    supplier: supplierName,
    emergencyContact: "",
    hazardSummary: "",
    dangerousGoods: "",
    ppeSummary: "",
    revisionDate,
    hazardBadge: "PDF",
    dataSource: "msds_pdf",
    ingredients: override?.ingredients || [],
    components: override?.ingredients || [],
    hazardStatements: override?.hazardStatements || [],
    precautionaryStatements: override?.precautionaryStatements || {},
    classificationGhsCodes: override?.classificationGhsCodes || [],
    classificationGhsPictograms: override?.classificationGhsPictograms || [],
    pdfSummaryOverride: override || null
  });
}

function getPdfOnlyDisplayName({ overrideName = "", candidateName = "", fileName = "" } = {}) {
  return cleanPdfProductName(overrideName)
    || cleanPdfProductName(candidateName)
    || cleanPdfFileNameForProduct(fileName)
    || String(fileName || "").replace(/\.pdf$/i, "")
    || "MSDS";
}

function supplierFromPath(path) {
  const folder = String(path || "").replace(/\\/g, "/").split("/")[0] || "";
  return normalizeSupplierDisplay(folder);
}

function getCompanyFromProductPath(product = {}) {
  const path = String(product.sourceRelativePath || product.relativePath || product.pdfPath || product.sourcePdfPath || "")
    .replace(/\\/g, "/")
    .replace(/^\/?pdf\//, "");
  const parts = path.split("/").filter(Boolean);
  if (parts.length < 2) return "";
  return cleanCompanyDisplayName(parts[parts.length - 2]);
}

function cleanCompanyDisplayName(value) {
  let text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text) return "";
  text = text
    .replace(/^(?:\/|제조사\/공급업체|제조자\/공급업체|공급자\s*정보|제조자\s*정보|회사명)\s*[:：]?/i, "")
    .replace(/^\d+_\s*/, "")
    .replace(/\([^)]*\)/g, "")
    .replace(/㈜|\(주\)|주식회사|\(유\)|유한회사/g, "")
    .trim();

  const stopPatterns = [
    /(서울|경기|경기도|인천|강원|충북|충청북도|충남|충청남도|대전|세종|전북|전라북도|전남|전라남도|광주|경북|경상북도|경남|경상남도|대구|울산|부산|제주|제주도|\(\d{5}\))/,
    /(주소|주\s*소|긴급|전화|전화번호|TEL|FAX|담당|연락|정보제공|제품명|권고|사용상|유해|위험|2\.|나\.|다\.|○)/i
  ];
  stopPatterns.forEach((pattern) => {
    const match = text.match(pattern);
    if (match && match.index > 0) text = text.slice(0, match.index).trim();
  });

  text = text.replace(/[,:：;/]+$/g, "").trim();
  if (isInvalidCompanyDisplayName(text)) return "";
  return text;
}

function isInvalidCompanyDisplayName(value) {
  const text = String(value || "").trim();
  if (!text) return true;
  if (text.length > 45) return true;
  if (/범위\s*\d{2,7}-\d{2,3}-\d{1,4}/.test(text)) return true;
  if (/^\d{2,7}-\d{2,3}-\d{1,4}$/.test(text)) return true;
  if (/CAS\s*(?:No\.?)?\s*(?:미기재|없음)|자료없음|해당없음|업체\s*미확인|제품정보\s*미등록/i.test(text)) return true;
  if (/\d{2,4}\)?\s*\d{3,4}[-\s]\d{4}/.test(text)) return true;
  if (/(도로|로\s*\d|길\s*\d|번길|산단로)/.test(text)) return true;
  return false;
}

function getDisplaySupplierName(product = {}) {
  const candidates = [
    product.supplier,
    product.manufacturer,
    product.maker,
    product.vendor,
    product.companyName
  ];
  const directName = candidates.map(cleanCompanyDisplayName).find(Boolean);
  return directName || getCompanyFromProductPath(product) || cleanCompanyDisplayName(product.siteLabel) || "업체 미확인";
}

function normalizeSupplierDisplay(value) {
  const text = String(value || "").trim();
  if (!text || text.toLowerCase() === "pdf") return "";
  return text
    .replace(/\(주\)|㈜|주식회사|\(주식회사\)/g, "")
    .replace(/\((그리스|구두약|파워피엔비)\)/g, "")
    .trim();
}

function cleanPdfProductName(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (!/[0-9A-Za-z가-힣]/.test(text) || normalizeSearchText(text).length <= 1) return "";
  if (!isReliablePdfProductName(text)) return "";
  if (looksLikeCompanyOnlyName(text)) return "";
  return text
    .replace(/\s+/g, " ")
    .replace(/\s*[:：]\s*$/, "")
    .trim();
}

function cleanPdfSupplierName(value) {
  const text = String(value || "").trim();
  if (!text || normalizeSearchText(text).length <= 1) return "";
  if (["정보", "정보:", "회사", "공급자", "제조자", "/유통업자 정보"].includes(text)) return "";
  if (/자료\s*없음|유통업자\s*정보|공급자\s*\/\s*유통업자\s*정보|권고\s*용도|보관하시오|safety\s+data\s+sheet|information/i.test(text)) return "";
  return text;
}

function cleanPdfRevisionDate(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/자료\s*없음|해당\s*없음|개정\s*횟수\s*및\s*최종\s*개정일자|목록번호\s*최초\s*작성일자\s*최종\s*개정일자/.test(text)) return "";
  if (/^\s*(?:-|자\s*:?\s*|년\s*월\s*일|신규\s*생산일|개정\s*횟수|최종\s*개정일)\s*$/.test(text)) return "";

  const withoutPrefix = text
    .replace(/^(?:최종\s*)?개정\s*일자?\s*[:：]?\s*/u, "")
    .replace(/^자\s*[:：]?\s*/u, "")
    .trim();

  const ymd = withoutPrefix.match(/(19\d{2}|20\d{2})\s*(?:[.\-/]|년)\s*(\d{1,2})\s*(?:[.\-/]|월)\s*(\d{1,2})\s*(?:일)?/);
  if (ymd) return `${ymd[1]}-${String(Number(ymd[2])).padStart(2, "0")}-${String(Number(ymd[3])).padStart(2, "0")}`;

  const dmy = withoutPrefix.match(/(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(19\d{2}|20\d{2})/);
  if (dmy) return `${dmy[3]}-${String(Number(dmy[2])).padStart(2, "0")}-${String(Number(dmy[1])).padStart(2, "0")}`;

  const koreanMonth = withoutPrefix.match(/(\d{1,2})\s*(\d{1,2})\s*월\s*(19\d{2}|20\d{2})/);
  if (koreanMonth) return `${koreanMonth[3]}-${String(Number(koreanMonth[2])).padStart(2, "0")}-${String(Number(koreanMonth[1])).padStart(2, "0")}`;

  return "";
}

function isReliablePdfProductName(value) {
  const text = String(value || "").trim();
  const normalized = normalizeSearchText(text);
  if (!text || text.length > 80 || normalized.length > 70) return false;
  const forbiddenPhrases = [
    "제품의용도",
    "권고용도",
    "사용상의제한",
    "제조자",
    "공급자",
    "전화번호",
    "긴급연락",
    "작성일자",
    "개정일자",
    "유해성",
    "위험성",
    "예방조치",
    "응급조치",
    "취급",
    "저장",
    "폐기",
    "제품에대한기술",
    "화학제품과회사에관한정보",
    "구성성분",
    "그림문자"
  ];
  if (forbiddenPhrases.some((phrase) => normalized.includes(normalizeSearchText(phrase)))) return false;
  if (/(^|\s)(2|3|4|5|6|7|8|9|10|11|12|13|14|15|16)\s*[.．]/.test(text)) return false;
  if (/(^|\s)[나다라마바사아자차카타파하]\s*[.．]/.test(text)) return false;
  if (/(TEL|FAX|E-?mail|http|www\.|주소|경기도|서울시|부산|전화|팩스|@)/i.test(text)) return false;
  if (/\d{2,4}[-.)]\d{2,4}[-.)]\d{2,4}/.test(text)) return false;
  if (/[가-힣]{12,}/.test(text) && !/\s/.test(text)) return false;
  const punctuationCount = (text.match(/[.:：;,/|]/g) || []).length;
  if (punctuationCount >= 5) return false;
  return true;
}

function looksLikeCompanyOnlyName(value) {
  const text = normalizeSearchText(value);
  if (!text) return true;
  return ["주식회사", "유한회사", "공급자", "제조자", "회사명", "상호명"].some((keyword) => text.includes(normalizeSearchText(keyword)))
    && !["제품", "품명", "도료", "페인트", "신너", "세척", "구두약"].some((keyword) => text.includes(normalizeSearchText(keyword)));
}

function cleanPdfFileNameForProduct(fileName) {
  const withoutExtension = String(fileName || "").replace(/\.pdf$/i, "");
  const withoutDuplicatePrefix = withoutExtension.replace(/^\[([^\]]+)\]\s*(.+)$/u, (match, prefix, rest) => {
    const normalizedPrefix = normalizeSearchText(prefix);
    const normalizedRest = normalizeSearchText(rest);
    return normalizedPrefix && normalizedRest.startsWith(normalizedPrefix) ? rest : `${prefix} ${rest}`;
  });

  return polishKoreanProductName(
    withoutDuplicatePrefix
    .replace(/[_]+/g, " ")
    .replace(/\bmsds\b/ig, " ")
    .replace(/\bghs\b/ig, " ")
    .replace(/\bmaterial\s+safety\s+data\s+sheet\b/ig, " ")
    .replace(/\b\d{4}[-_.]?\d{2}[-_.]?\d{2}\b/g, " ")
    .replace(/\b\d{2}[-_.]\d{2}[-_.]\d{2}\b/g, " ")
    .replace(/\d{4}\.\d{1,2}\.\d{1,2}\s*\([^)]*\)/g, " ")
    .replace(/\bver(?:sion)?\s*\d+[a-z]?\b/ig, " ")
    .replace(/\brev(?:ision)?\s*\d+[a-z]?\b/ig, " ")
    .replace(/\d+\s*차\s*개정/g, " ")
    .replace(/\s+[-–—]+\s+/g, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([)])/, "$1")
    .replace(/([(])\s+/g, "$1")
    .trim()
  );
}

function polishKoreanProductName(value) {
  let text = String(value || "").trim();
  const compact = normalizeSearchText(text);
  if (compact.includes("캉가루구두약가정용")) return "캉가루 구두약 (가정용)";
  text = text.replace(/^.*?(GHP\s+[A-Z0-9][A-Z0-9\s.-]*\d(?:\s*\([^)]*\))?)$/i, "$1");
  text = text.replace(/^.*?(S-\d{2,}(?:\.\d+[A-Z0-9]*)?)$/i, "$1");

  [
    "구두약",
    "세척제",
    "접착제",
    "이형제",
    "방청제",
    "윤활제",
    "페인트",
    "프라이머",
    "신너"
  ].forEach((term) => {
    text = text.replace(new RegExp(`([^\\s(])(${term})`, "gu"), "$1 $2");
  });
  text = text.replace(/\s+(가정용|공업용|산업용|업소용)$/u, " ($1)");
  text = text.replace(/\(([A-Za-z]+)\s+(\d+)\)/g, "($1-$2)");
  text = text.replace(/\s{2,}/g, " ").trim();
  if (!isReliablePdfProductName(text) && text.length > 80) return text.slice(0, 80).trim();
  return text.replace(/\s{2,}/g, " ").trim();
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
    || findOverrideByPdfName(product, overrides)
    || null;
}

function findOverrideByField(product, overrides, field) {
  const productValue = normalizeSearchText(product[field]);
  if (!productValue) return null;
  return overrides.find((override) => normalizeSearchText(override.match?.[field]) === productValue);
}

function findOverrideByPdfName(product, overrides = []) {
  const productNames = getProductPdfNameKeys(product);
  if (!productNames.length) return null;

  return overrides.find((override) => {
    const match = override.match || {};
    const overrideNames = [
      match.fileName,
      getPathBasename(match.relativePath),
      getPathBasename(override.sourceRelativePath),
      getPathBasename(override.sourcePdfPath)
    ].map(normalizeSearchText).filter(Boolean);

    return overrideNames.some((name) => productNames.includes(name));
  }) || null;
}

function findInventoryForProduct(product) {
  const productNames = getProductPdfNameKeys(product);
  if (!productNames.length || !state.pdfInventory.length) return null;

  return state.pdfInventory.find((item) => {
    const itemNames = [
      item.fileName,
      getPathBasename(item.relativePath),
      getPathBasename(item.pdfPath)
    ].map(normalizeSearchText).filter(Boolean);

    return itemNames.some((name) => productNames.includes(name));
  }) || null;
}

function findPdfOverrideForProduct(product) {
  return product.pdfSummaryOverride || findOverrideForProduct(product, state.pdfOverrides);
}

function getProductPdfNameKeys(product) {
  return [
    product.fileName,
    getPathBasename(product.pdfPath),
    getPathBasename(product.relativePath),
    getPathBasename(product.sourceRelativePath)
  ].map(normalizeSearchText).filter(Boolean);
}

function getPathBasename(path) {
  const value = String(path || "").replace(/\\/g, "/").trim();
  if (!value) return "";
  const cleanValue = value.split("?")[0].split("#")[0].replace(/\/$/, "");
  try {
    return decodeURIComponent(cleanValue.split("/").pop() || "");
  } catch (error) {
    return cleanValue.split("/").pop() || "";
  }
}

function normalizeSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\.pdf/gi, "")
    .replace(/[\s()[\]{}<>（）［］｛｝_\-\/\\]/g, "");
}

function normalizeGhsCode(value) {
  const raw = typeof value === "string" ? value : (value?.code || value?.label || "");
  const text = String(raw || "").trim();
  if (!text) return "";
  const upper = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const direct = upper.match(/^GHS0[1-9]$/)?.[0];
  if (direct && GHS_DEFINITIONS[direct]) return direct;
  const normalized = normalizeSearchText(text).replace(/[^a-z0-9?-?]/gi, "");
  return GHS_CODE_ALIASES[normalized] || GHS_CODE_ALIASES[normalized.toLowerCase()] || "";
}

function normalizeGhsCodeList(items = []) {
  const list = Array.isArray(items) ? items : [];
  return [...new Set(list.map(normalizeGhsCode).filter(Boolean))]
    .sort((a, b) => GHS_DEFINITIONS[a].order - GHS_DEFINITIONS[b].order);
}

function normalizeGhsList(source = {}) {
  const rawCodes = Array.isArray(source.ghsCodes) ? source.ghsCodes : [];
  const rawItems = Array.isArray(source.ghsPictograms)
    ? source.ghsPictograms
    : (Array.isArray(source) ? source : []);
  const codes = normalizeGhsCodeList([...rawCodes, ...rawItems]);
  return codes.map((code) => ({
    code,
    label: GHS_DEFINITIONS[code].label,
    icon: GHS_DEFINITIONS[code].icon
  }));
}

function mergeGhsItems(...groups) {
  const codeMap = new Map();
  groups.flat().filter(Boolean).forEach((item) => {
    const code = normalizeGhsCode(item.code || item.label || item);
    if (code && GHS_DEFINITIONS[code] && !codeMap.has(code)) {
      codeMap.set(code, {
        code,
        label: GHS_DEFINITIONS[code].label,
        icon: GHS_DEFINITIONS[code].icon
      });
    }
  });
  return [...codeMap.values()].sort((a, b) => GHS_DEFINITIONS[a.code].order - GHS_DEFINITIONS[b.code].order);
}

function inferGhsItemsFromHazardClassification(product = {}, override = null) {
  const rawText = [
    product.hazardClassification,
    product.hazardSummary,
    product.dangerousGoods,
    (product.hazardStatements || []).join(" "),
    (override?.hazardStatements || []).join(" ")
  ].join(" ");
  const text = normalizeSearchText(rawText);

  if (!text || containsNoGhsLabelElement(text)) return [];

  const segments = getHazardClassificationSegments(rawText);
  return HAZARD_CLASSIFICATION_GHS_RULES
    .filter((rule) => rule.matches(segments))
    .map((rule) => ({
      code: rule.code,
      label: GHS_DEFINITIONS[rule.code].label,
      icon: GHS_DEFINITIONS[rule.code].icon,
      reason: rule.reason
    }));
}

function getHazardClassificationSegments(value) {
  return String(value || "")
    .split(/\n|(?:\s-\s)|(?:^-\s)|;|ㆍ|•|·/g)
    .map(normalizeSearchText)
    .filter(Boolean);
}

function hasAnyText(segments, keywords) {
  return segments.some((segment) => keywords.some((keyword) => segment.includes(normalizeSearchText(keyword))));
}

function hasAnySegment(segments, names, categories = []) {
  const normalizedNames = names.map(normalizeSearchText);
  const normalizedCategories = categories.map(normalizeSearchText);
  return segments.some((segment) => {
    const hasName = normalizedNames.some((name) => segment.includes(name));
    if (!hasName) return false;
    if (!normalizedCategories.length) return true;
    return normalizedCategories.some((category) => segment.includes(category));
  });
}

function getExplicitGhsItems(product = {}, override = null) {
  const overrideLabelGhs = normalizeLabelGhsList(override || {});
  if (overrideLabelGhs.length) return overrideLabelGhs;

  const productLabelGhs = normalizeLabelGhsList(product || {});
  if (productLabelGhs.length) return productLabelGhs;

  const overrideGhsSource = normalizeSearchText(override?.ghsSource || "");
  const overrideGeneralGhs = normalizeGhsList(override || {});
  if (overrideGeneralGhs.length && !overrideGhsSource.includes("classificationfallback")) {
    return overrideGeneralGhs;
  }

  const productClassificationGhs = normalizeClassificationGhsList(product || {});
  if (productClassificationGhs.length) return productClassificationGhs;

  return normalizeGhsList(product || {});
}

function normalizeLabelGhsList(source = {}) {
  return normalizeGhsList({
    ghsCodes: source?.labelGhsCodes || [],
    ghsPictograms: source?.labelGhsPictograms || []
  });
}

function normalizeClassificationGhsList(source = {}) {
  return normalizeGhsList({
    ghsCodes: source?.classificationGhsCodes || [],
    ghsPictograms: source?.classificationGhsPictograms || []
  });
}

function getOverrideGhsItems(override) {
  const labelItems = normalizeLabelGhsList(override || {});
  return labelItems.length ? labelItems : normalizeGhsList(override || {});
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
    getDisplaySupplierName(product),
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

const SEARCH_SYNONYM_GROUPS = [
  ["신너", "신나", "시너", "thinner", "희석제", "solvent"],
  ["세정제", "세척제", "클리너", "크리너", "cleaner"],
  ["페인트", "도료", "paint", "coating"],
  ["경화제", "경화재", "hardener"],
  ["프라이머", "프라이마", "primer"],
  ["그리스", "구리스", "grease"],
  ["오일", "oil", "윤활유"],
  ["클리어", "clear"],
  ["그레이", "그래이", "gray", "grey"],
  ["블랙", "black"],
  ["화이트", "white"],
  ["실버", "silver"],
  ["락카", "라카", "lacquer"],
  ["우레탄", "urethane"]
].map((group) => group.map(normalizeSearchText).filter(Boolean));

const SEARCH_FUZZY_SOURCE_TERMS = [...new Set(SEARCH_SYNONYM_GROUPS.flat())];

function getSearchQueryInfo(rawQuery) {
  const raw = String(rawQuery || "").trim();
  const normalized = normalizeSearchText(raw);
  const tokenParts = raw
    .split(/[\s,;]+/)
    .map(normalizeSearchText)
    .filter(Boolean);
  const tokens = [...new Set(tokenParts.length ? tokenParts : [normalized].filter(Boolean))];
  const units = [
    ...(normalized ? [{ value: normalized, isWhole: true }] : []),
    ...tokens
      .filter((token) => token && token !== normalized)
      .map((token) => ({ value: token, isWhole: false }))
  ];
  const normalizedRawCode = raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const synonymTermsByToken = new Map();
  const fuzzyTermsByToken = new Map();

  tokens.forEach((token) => {
    if (!canUseLinguisticExpansion(token)) return;
    const synonymTerms = getSynonymTermsForToken(token);
    if (synonymTerms.length) synonymTermsByToken.set(token, synonymTerms);
    const fuzzyTerms = getFuzzyTermsForToken(token, synonymTerms);
    if (fuzzyTerms.length) fuzzyTermsByToken.set(token, fuzzyTerms);
  });

  return {
    raw,
    normalized,
    tokens,
    units,
    isNumericOnly: /^[0-9]+$/.test(normalized),
    isHazardCodeQuery: /^[HP][0-9]{3}$/.test(normalizedRawCode),
    hazardCode: normalizedRawCode,
    isCasQuery: /^\d{2,7}-\d{2}-\d$/.test(raw.replace(/\s/g, "")),
    casRaw: raw.replace(/\s/g, ""),
    casCompact: raw.replace(/\D/g, ""),
    synonymTermsByToken,
    fuzzyTermsByToken
  };
}

function canUseLinguisticExpansion(token) {
  return Boolean(token)
    && token.length >= 2
    && !/[0-9]/.test(token)
    && !/^[hp]\d{3}$/i.test(token);
}

function getSynonymTermsForToken(token) {
  const terms = new Set();
  SEARCH_SYNONYM_GROUPS
    .filter((group) => group.includes(token))
    .flat()
    .forEach((term) => terms.add(term));
  return [...terms];
}

function getFuzzyTermsForToken(token, synonymTerms = []) {
  if (!/[가-힣]/.test(token) || token.length <= 1) return [];
  const synonymSet = new Set(synonymTerms);
  return SEARCH_FUZZY_SOURCE_TERMS
    .filter((term) => term !== token)
    .filter((term) => /[가-힣]/.test(term))
    .filter((term) => !synonymSet.has(term))
    .filter((term) => Math.abs(term.length - token.length) <= 1)
    .filter((term) => getEditDistance(token, term) <= 1);
}

function getEditDistance(a, b) {
  const left = Array.from(String(a || ""));
  const right = Array.from(String(b || ""));
  const rows = Array.from({ length: left.length + 1 }, () => []);
  for (let i = 0; i <= left.length; i += 1) rows[i][0] = i;
  for (let j = 0; j <= right.length; j += 1) rows[0][j] = j;
  for (let i = 1; i <= left.length; i += 1) {
    for (let j = 1; j <= right.length; j += 1) {
      const cost = left[i - 1] === right[j - 1] ? 0 : 1;
      rows[i][j] = Math.min(
        rows[i - 1][j] + 1,
        rows[i][j - 1] + 1,
        rows[i - 1][j - 1] + cost
      );
    }
  }
  return rows[left.length][right.length];
}

function getProductSearchFields(product = {}) {
  const componentItems = [
    ...(Array.isArray(product.components) ? product.components : []),
    ...(Array.isArray(product.ingredients) ? product.ingredients : [])
  ];
  const componentNames = componentItems.map((component) => component.chemicalName);
  const casNumbers = componentItems.map((component) => component.casNo).filter(Boolean);
  const hazardStatements = [
    ...(Array.isArray(product.hazardStatements) ? product.hazardStatements : []),
    ...(Array.isArray(product.pdfSummaryOverride?.hazardStatements) ? product.pdfSummaryOverride.hazardStatements : [])
  ];
  const precautionText = [
    flattenPrecautions(product.precautionaryStatements),
    flattenPrecautions(product.pdfSummaryOverride?.precautionaryStatements)
  ].join(" ");
  const ppeText = [
    product.ppeSummary,
    ...(Array.isArray(product.ppeCandidates) ? product.ppeCandidates : []),
    ...(Array.isArray(product.pdfSummaryOverride?.ppeCandidates) ? product.pdfSummaryOverride.ppeCandidates : [])
  ].join(" ");
  const fileNames = [
    product.fileName,
    getPathBasename(product.pdfPath),
    getPathBasename(product.relativePath),
    getPathBasename(product.sourceRelativePath)
  ];
  const codeCandidates = extractProductCodeCandidates([
    product.productName,
    product.erpName,
    product.fileName,
    product.pdfPath,
    product.relativePath,
    product.sourceRelativePath
  ].join(" "));

  return {
    productNames: getUniqueSearchValues([product.productName]),
    productCodes: codeCandidates,
    erpNames: getUniqueSearchValues([product.erpName]),
    fileNames: getUniqueSearchValues(fileNames),
    metaFields: getUniqueSearchValues([
      product.category,
      product.useCategory,
      product.recommendedUse,
      product.siteLabel,
      getDisplaySupplierName(product),
      product.supplier
    ]),
    componentNames: getUniqueSearchValues(componentNames),
    casNumbers: getUniqueSearchValues(casNumbers),
    hazardCodes: extractHazardCodes([hazardStatements.join(" "), precautionText].join(" ")),
    detailTexts: getUniqueSearchValues([
      product.hazardSummary,
      product.hazardClassification,
      product.dangerousGoods,
      product.ppeSummary,
      hazardStatements.join(" "),
      precautionText,
      ppeText
    ])
  };
}

function getUniqueSearchValues(values = []) {
  return [...new Set(values.map((value) => String(value || "").trim()).filter(Boolean))];
}

function getNormalizedValues(values = []) {
  return values.map(normalizeSearchText).filter(Boolean);
}

function extractProductCodeCandidates(text) {
  const raw = String(text || "");
  const candidates = new Set();
  const codeMatches = raw.match(/[A-Za-z]{1,10}\s*[-_./]?\s*\d{1,8}(?:\s*[-_./]?\s*[A-Za-z0-9]{1,12})*/g) || [];
  codeMatches.forEach((match) => {
    const normalized = normalizeSearchText(match);
    if (normalized.length >= 2) candidates.add(match);
  });
  return [...candidates];
}

function extractHazardCodes(text) {
  const matches = String(text || "").match(/\b[HP]\s*[-_]?\s*\d{3}\b/gi) || [];
  return [...new Set(matches.map((match) => match.toUpperCase().replace(/[^A-Z0-9]/g, "")))];
}

function hasNormalizedMatch(values, query, mode = "contains") {
  if (!query) return false;
  const normalizedValues = getNormalizedValues(values);
  if (mode === "exact") return normalizedValues.some((value) => value === query);
  return normalizedValues.some((value) => value.includes(query));
}

function hasCasMatch(casNumbers, queryInfo, mode = "exact") {
  if (!queryInfo.casRaw && !queryInfo.normalized) return false;
  return casNumbers.some((casNo) => {
    const compact = String(casNo || "").replace(/\D/g, "");
    const raw = String(casNo || "").replace(/\s/g, "");
    if (mode === "exact") {
      return queryInfo.isCasQuery
        ? raw === queryInfo.casRaw
        : compact === queryInfo.casCompact && queryInfo.casCompact.length >= 5;
    }
    return !queryInfo.isNumericOnly && queryInfo.casCompact.length >= 5 && compact.includes(queryInfo.casCompact);
  });
}

function getSearchReasonLabel(reason) {
  const labels = {
    productExact: "제품명 정확 일치",
    productCodeExact: "제품코드 일치",
    productContains: "제품명 일치",
    fileMatch: "파일명 일치",
    erpMatch: "ERP 품명 일치",
    metaMatch: "분류/업체 일치",
    synonymMatch: "동의어 일치",
    fuzzyMatch: "오타 보정",
    componentMatch: "성분명 일치",
    casExact: "CAS 일치",
    casPartial: "CAS 후보",
    hazardCodeMatch: "유해문구 코드 일치",
    detailMatch: "상세문구 일치"
  };
  return labels[reason] || "";
}

function findMatchedSearchTerm(values, terms = []) {
  return terms.find((term) => hasNormalizedMatch(values, term, "contains")) || "";
}

function getExpansionReasonLabel(reason, queryToken, matchedTerm) {
  const baseLabel = getSearchReasonLabel(reason);
  if (!queryToken || !matchedTerm || queryToken === matchedTerm) return baseLabel;
  return `${baseLabel}: ${queryToken} → ${matchedTerm}`;
}

function scoreProductForQuery(product, queryInfo) {
  const fields = getProductSearchFields(product);
  const scoreState = {
    score: 0,
    reasons: [],
    reasonLabels: [],
    matchedTokens: new Set(),
    directMatch: false,
    exactMatch: false,
    containsMatch: false,
    detailOnly: true
  };

  const addScore = (points, reason, unit, options = {}) => {
    if (!points) return;
    scoreState.score += points;
    if (!scoreState.reasons.includes(reason)) scoreState.reasons.push(reason);
    const label = options.reasonLabel || getSearchReasonLabel(reason);
    if (label && !scoreState.reasonLabels.includes(label)) scoreState.reasonLabels.push(label);
    if (unit?.isWhole) {
      queryInfo.tokens.forEach((token) => scoreState.matchedTokens.add(token));
    } else if (unit?.value) {
      scoreState.matchedTokens.add(unit.value);
    }
    if (options.direct) {
      scoreState.directMatch = true;
      scoreState.detailOnly = false;
    }
    if (options.exact) scoreState.exactMatch = true;
    if (options.contains) scoreState.containsMatch = true;
  };

  queryInfo.units.forEach((unit) => {
    if (hasNormalizedMatch(fields.productNames, unit.value, "exact")) {
      addScore(1200, "productExact", unit, { direct: true, exact: true });
    }
    if (hasNormalizedMatch(fields.productCodes, unit.value, "exact")) {
      addScore(1100, "productCodeExact", unit, { direct: true, exact: true });
    }
    if (hasNormalizedMatch([...fields.productNames, ...fields.productCodes], unit.value, "contains")) {
      addScore(800, "productContains", unit, { direct: true, contains: true });
    }
    if (hasNormalizedMatch(fields.fileNames, unit.value, "contains")) {
      addScore(600, "fileMatch", unit, { direct: true, contains: true });
    }
    if (hasNormalizedMatch(fields.erpNames, unit.value, "contains")) {
      addScore(500, "erpMatch", unit, { direct: true, contains: true });
    }
    if (hasNormalizedMatch(fields.metaFields, unit.value, "contains")) {
      addScore(300, "metaMatch", unit, { contains: true });
      scoreState.detailOnly = false;
    }
    if (!queryInfo.isNumericOnly && hasNormalizedMatch(fields.componentNames, unit.value, "contains")) {
      addScore(120, "componentMatch", unit, { contains: true });
    }
    if (!queryInfo.isNumericOnly && !queryInfo.isHazardCodeQuery && unit.value.length >= 2 && hasNormalizedMatch(fields.detailTexts, unit.value, "contains")) {
      addScore(60, "detailMatch", unit, { contains: true });
    }
  });

  queryInfo.tokens.forEach((token) => {
    const synonymTerms = queryInfo.synonymTermsByToken.get(token) || [];
    const synonymFields = [
      ...fields.productNames,
      ...fields.erpNames,
      ...fields.fileNames,
      ...fields.metaFields
    ];
    const matchedSynonymTerm = findMatchedSearchTerm(synonymFields, synonymTerms);
    if (matchedSynonymTerm) {
      addScore(220, "synonymMatch", { value: token }, {
        contains: true,
        reasonLabel: getExpansionReasonLabel("synonymMatch", token, matchedSynonymTerm)
      });
      scoreState.detailOnly = false;
    }

    const fuzzyTerms = queryInfo.fuzzyTermsByToken.get(token) || [];
    const matchedFuzzyTerm = findMatchedSearchTerm(synonymFields, fuzzyTerms);
    if (matchedFuzzyTerm) {
      addScore(160, "fuzzyMatch", { value: token }, {
        contains: true,
        reasonLabel: getExpansionReasonLabel("fuzzyMatch", token, matchedFuzzyTerm)
      });
      scoreState.detailOnly = false;
    }
  });

  if (hasCasMatch(fields.casNumbers, queryInfo, "exact")) {
    addScore(350, "casExact", { value: queryInfo.normalized }, { exact: true });
  } else if (hasCasMatch(fields.casNumbers, queryInfo, "partial")) {
    addScore(25, "casPartial", { value: queryInfo.normalized }, { contains: true });
  }

  if (queryInfo.isHazardCodeQuery && fields.hazardCodes.includes(queryInfo.hazardCode)) {
    addScore(200, "hazardCodeMatch", { value: queryInfo.normalized }, { exact: true });
  }

  return {
    score: scoreState.score,
    directMatch: scoreState.directMatch,
    exactMatch: scoreState.exactMatch,
    containsMatch: scoreState.containsMatch,
    detailOnly: scoreState.detailOnly,
    matchedTokenCount: scoreState.matchedTokens.size,
    reason: scoreState.reasonLabels[0] || getSearchReasonLabel(scoreState.reasons[0])
  };
}

function rankProductsForQuery(products, queryInfo) {
  const isMultiTokenQuery = queryInfo.tokens.length > 1;
  return products
    .map((product) => {
      const result = scoreProductForQuery(product, queryInfo);
      return {
        ...product,
        __searchScore: result.score,
        __searchReason: result.reason,
        __searchDirectMatch: result.directMatch,
        __searchExactMatch: result.exactMatch,
        __searchContainsMatch: result.containsMatch,
        __searchDetailOnly: result.detailOnly,
        __searchMatchedTokenCount: result.matchedTokenCount
      };
    })
    .filter((product) => product.__searchScore > 0)
    .sort((a, b) => (
      (isMultiTokenQuery ? b.__searchMatchedTokenCount - a.__searchMatchedTokenCount : 0)
      || b.__searchScore - a.__searchScore
      || Number(b.__searchDirectMatch) - Number(a.__searchDirectMatch)
      || b.__searchMatchedTokenCount - a.__searchMatchedTokenCount
      || Number(b.__searchExactMatch) - Number(a.__searchExactMatch)
      || Number(b.__searchContainsMatch) - Number(a.__searchContainsMatch)
      || Number(a.__searchDetailOnly) - Number(b.__searchDetailOnly)
      || String(a.productName || "").localeCompare(String(b.productName || ""), "ko")
    ));
}

function getFilteredProducts() {
  const queryInfo = getSearchQueryInfo(state.query);
  if (!queryInfo.normalized) return state.products;
  return rankProductsForQuery(state.products, queryInfo);
}

function getSelectedProduct(results) {
  return results.find((product) => product.id === state.selectedId) || results[0] || null;
}

function getAllSelectableProducts() {
  return [...state.products, ...state.pdfOnlyProducts];
}

function render() {
  const normalizedQuery = normalizeSearchText(state.query);
  const hasQuery = Boolean(normalizedQuery);
  const canShowCandidates = normalizedQuery.length >= APP_CONFIG.minSearchCharacters;
  const results = hasQuery ? getFilteredProducts() : [];
  const selectedPool = canShowCandidates ? results : getAllSelectableProducts();
  const selected = getSelectedProduct(selectedPool);
  if (selected) state.selectedId = selected.id;

  elements.emptySearchGuide.classList.toggle("is-hidden", Boolean(state.query.trim()));
  elements.selectionPanel.classList.toggle("is-collapsed", !hasQuery && !state.showFullList);
  elements.resultCount.textContent = state.showFullList ? `전체 MSDS ${getAllSelectableProducts().length}건` : (hasQuery ? `검색 결과 ${results.length}건` : "검색 전");
  elements.dataMode.textContent = state.dataMode;
  elements.dataMode.classList.toggle("is-local", state.dataMode.includes("로컬"));
  if (elements.publicDeployNotice) {
    elements.publicDeployNotice.textContent = state.publicNotice;
    elements.publicDeployNotice.classList.toggle("is-hidden", !state.publicNotice);
  }
  elements.currentSelection.textContent = selected
    ? `현재 선택 제품: ${selected.productName}`
    : "현재 선택 제품: 없음";
  elements.resultSubtitle.textContent = getResultSubtitle(hasQuery, canShowCandidates, results.length);

  renderSelectionList(results, hasQuery, canShowCandidates);
  renderPoster(selected);
  renderDetail(selected);
  document.body.classList.toggle("is-pdf-full-view-open", state.pdfFullView.isOpen);
  hydrateRequestedPdfPreview();
}

function getResultSubtitle(hasQuery, canShowCandidates, totalCount) {
  if (state.showFullList && !hasQuery) return "전체 MSDS 자료를 업체별로 정리해 표시합니다.";
  if (!hasQuery) return "검색어를 입력하면 후보 제품이 표시됩니다.";
  if (!canShowCandidates) return `${APP_CONFIG.minSearchCharacters}글자 이상 입력하면 후보 제품을 표시합니다.`;
  if (!totalCount) return "제품명, 용도, CAS No. 등으로 다시 검색해보세요.";
  if (state.showAllResults) return "전체 결과 표시 중";
  const start = Math.min(state.resultOffset + 1, totalCount);
  const end = Math.min(state.resultOffset + state.resultLimit, totalCount);
  return `현재 ${start}~${end}건 표시`;
}

function renderSelectionList(results, hasQuery, canShowCandidates) {
  if (state.showFullList && !hasQuery) {
    renderFullProductList();
    return;
  }

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
          <span>${escapeHtml([selectedProduct.useCategory, getDisplaySupplierName(selectedProduct)].filter(Boolean).join(" · "))}</span>
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
          <span class="selection-name text-break clamp-2">${escapeHtml(product.productName)}</span>
          <span class="selection-meta text-muted-path clamp-2">${escapeHtml([product.useCategory, getDisplaySupplierName(product)].filter(Boolean).join(" · "))}</span>
          ${product.__searchReason ? `<span class="selection-match-reason">${escapeHtml(product.__searchReason)}</span>` : ""}
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
          ${results.length > APP_CONFIG.initialResultLimit ? `<button class="result-nav-button" type="button" id="showAllResults">검색결과 전체 보기</button>` : ""}
        `}
    </div>
  `;

  elements.selectionList.querySelectorAll("[data-product-id]").forEach((button) => {
    button.addEventListener("click", () => {
      if (state.selectedId !== button.dataset.productId) resetPdfPreviewState();
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

function renderFullProductList() {
  const allProducts = getAllSelectableProducts();
  const groups = buildProductGroups(allProducts);
  elements.selectionList.innerHTML = `
    <div class="full-list-panel">
      <div class="full-list-summary">
        <strong>전체 MSDS 보기</strong>
        <span>업체별 MSDS ${allProducts.length}개 표시 중</span>
      </div>
      <div class="full-product-groups">
        ${groups.map((group) => `
          <section class="product-company-group">
            <header class="product-company-header">
              <h3>${escapeHtml(group.name)}</h3>
              <span>${group.products.length}개 제품</span>
            </header>
            <div class="product-company-list">
              ${group.products.map((product, index) => renderFullProductItem(product, index)).join("")}
            </div>
          </section>
        `).join("")}
      </div>
      <button class="full-list-floating-collapse" type="button" id="collapseFullProductList">전체 MSDS 접기</button>
    </div>
  `;

  elements.selectionList.querySelector("#collapseFullProductList")?.addEventListener("click", () => {
    state.showFullList = false;
    resetResultWindow();
    resetFullListNavigation();
    render();
    elements.currentSelection?.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  elements.selectionList.querySelectorAll("[data-product-id]").forEach((item) => {
    item.addEventListener("click", (event) => {
      if (event.target.closest("[data-view-detail]")) return;
      selectFullListProduct(item.dataset.productId, false);
    });
    item.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectFullListProduct(item.dataset.productId, false);
    });
  });
}

function buildProductGroups(products = []) {
  const groupMap = new Map();
  products.forEach((product) => {
    const groupName = getProductCompanyName(product);
    if (!groupMap.has(groupName)) groupMap.set(groupName, []);
    groupMap.get(groupName).push(product);
  });

  return [...groupMap.entries()]
    .map(([name, groupProducts]) => ({
      name,
      products: groupProducts.slice().sort((a, b) => String(a.productName || "").localeCompare(String(b.productName || ""), "ko"))
    }))
    .sort((a, b) => {
      if (a.name === "업체 미확인") return 1;
      if (b.name === "업체 미확인") return -1;
      return a.name.localeCompare(b.name, "ko");
    });
}

function getProductCompanyName(product) {
  return getDisplaySupplierName(product);
}

function renderFullProductItem(product, index) {
  const pdfInfo = buildPdfInfo(product);
  const isPdfBased = Boolean(product.dataSource === "msds_pdf" || product.isPdfAbsorbed);
  const casItems = (product.components || [])
    .map((component) => component.casNo)
    .filter(Boolean)
    .slice(0, 2);
  const casText = casItems.length ? casItems.join(", ") : "CAS No. 미확인";
  const pdfLabel = pdfInfo.status === "connected" ? "PDF 연결됨" : "MSDS 원본 기준";
  const metaText = [
    product.useCategory || product.recommendedUse || "",
    casText !== "CAS No. 미확인" ? casText : ""
  ].filter(Boolean).join(" · ") || (isPdfBased ? "MSDS 원본 기준" : "용도 미확인");

  return `
    <div class="full-product-item ${isPdfBased ? "is-pdf-based" : ""} ${product.id === state.selectedId ? "is-selected" : ""}" role="button" tabindex="0" data-product-id="${escapeAttribute(product.id)}">
      <span class="full-product-number">${index + 1}</span>
      <span class="full-product-main">
        <strong title="${escapeAttribute(product.productName)}">${escapeHtml(product.productName || "제품명 미확인")}</strong>
        <span>${escapeHtml(metaText)}</span>
      </span>
      <span class="full-product-tags">
        <span class="full-risk-badge">${escapeHtml(product.hazardBadge || "확인")}</span>
        <span class="full-pdf-badge ${pdfInfo.status === "connected" ? "is-connected" : ""}">${pdfLabel}</span>
      </span>
      <button class="full-detail-button" type="button" data-view-detail data-product-id="${escapeAttribute(product.id)}">상세정보 보기</button>
    </div>
  `;
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
      <h2 title="${escapeAttribute(product.productName)}">${escapeHtml(product.productName)}</h2>
      <span class="hazard-badge">${escapeHtml(posterData.hazardBadge)}</span>
    </div>
    <div class="poster-ghs-row">
      ${renderGhsListFromItems(posterData.ghsPictograms, "poster", hasLinkedPdf(product))}
    </div>
    ${posterSection(posterData.hazardTitle, renderBulletList(posterData.hazardStatements, posterData.isCandidate), "poster-hazard-statements")}
    ${posterSection(posterData.precautionTitle, renderPrecautions(posterData.precautionaryStatements, posterData.isCandidate), "poster-precaution-statements")}
    ${posterData.ppeCandidates.length ? posterSection(posterData.ppeTitle, renderBulletList(posterData.ppeCandidates, posterData.isCandidate), "poster-ppe-candidates") : ""}
    <footer class="poster-footer">
      ${posterData.footerNotice.map((notice) => `<p>${escapeHtml(notice)}</p>`).join("")}
      <p>공급자 정보: ${escapeHtml(getDisplaySupplierName(product))}</p>
      ${posterData.showSourcePdfPath && posterData.sourcePdfPath ? `<p>PDF 출처: ${escapeHtml(posterData.sourcePdfPath)}</p>` : ""}
    </footer>
  `;
}

function getPosterData(product) {
  const override = product.pdfSummaryOverride;
  if (canUseOverride(override) && hasOverrideSummary(override)) {
    const isReviewed = override.reviewStatus === "검토완료";
    const showReviewStatus = shouldShowReviewStatusOnFieldPoster();
    const ghsPictograms = getDisplayGhsPictograms(product);
    return {
      statusClass: isReviewed ? "is-reviewed" : "is-review-needed",
      showReviewStrip: showReviewStatus,
      reviewBadge: isReviewed ? "검토완료" : "MSDS 원본 기준",
      reviewMessage: isReviewed
        ? "검토 완료된 MSDS 요약정보입니다."
        : "MSDS 원본 기준으로 정리한 안전정보입니다.",
      hazardBadge: override.signalWordCandidate || product.hazardBadge || "확인",
      ghsPictograms,
      hazardStatements: override.hazardStatements || [],
      precautionaryStatements: override.precautionaryStatements || {},
      ppeCandidates: limitList(override.ppeCandidates || [], 5),
      ppeTitle: "PPE 및 보호구",
      hazardTitle: "유해 위험 문구",
      precautionTitle: "예방조치 문구",
      footerNotice: [
        "이 자료는 현장 확인용 요약본입니다.",
        "상세 사항은 하단 MSDS 원본자료를 반드시 확인하세요."
      ],
      sourcePdfPath: override.sourcePdfPath || "",
      showSourcePdfPath: !APP_CONFIG.fieldDisplayMode,
      isCandidate: !isReviewed && showReviewStatus
    };
  }

  const hasProductSummary = hasAnySummary(normalizeGhsList(product), product.hazardStatements, product.precautionaryStatements);
  const showUnregisteredStatus = !APP_CONFIG.fieldDisplayMode;
  return {
    statusClass: hasProductSummary ? "" : "is-unregistered-summary",
    showReviewStrip: !hasProductSummary && showUnregisteredStatus,
    reviewBadge: hasProductSummary ? "" : "MSDS 원본 기준",
    reviewMessage: hasProductSummary ? "" : "정식 MSDS PDF를 확인하세요.",
    hazardBadge: product.hazardBadge || "확인",
    ghsCodes: normalizeGhsCodeList(product.ghsCodes || product.ghsPictograms || []),
    ghsPictograms: normalizeGhsList(product),
    hazardStatements: product.hazardStatements || [],
    precautionaryStatements: product.precautionaryStatements || {},
    ppeCandidates: [],
    ppeTitle: "PPE 및 보호구",
    hazardTitle: "유해 위험 문구",
    precautionTitle: "예방조치 문구",
    footerNotice: [
      "이 자료는 현장 확인용 요약본입니다.",
      "상세 사항은 하단 MSDS 원본자료를 반드시 확인하세요."
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
  return hasAnySummary(getOverrideGhsItems(override), override.hazardStatements, override.precautionaryStatements)
    || Boolean(override.signalWordCandidate)
    || Boolean(override.sourcePdfPath)
    || Boolean((override.ppeCandidates || []).length);
}

function containsNoGhsLabelElement(value) {
  const text = String(value || "").toLowerCase();
  const normalized = normalizeSearchText(text);
  return normalized.includes("해당없음")
    || normalized.includes("유해화학물질로분류되지않음")
    || normalized.includes("분류되지않음")
    || normalized.includes("notclassified")
    || normalized.includes("noghslabelelement")
    || normalized.includes("notapplicable");
}

function shouldSuppressGhsPictograms(product) {
  const override = canUseOverride(product.pdfSummaryOverride) ? product.pdfSummaryOverride : null;
  if (getExplicitGhsItems(product, override).length) return false;
  return containsNoGhsLabelElement(override?.signalWordCandidate)
    || containsNoGhsLabelElement(product.hazardSummary)
    || containsNoGhsLabelElement(product.hazardClassification);
}

function getDisplayGhsPictograms(product) {
  if (shouldSuppressGhsPictograms(product)) return [];
  const override = canUseOverride(product.pdfSummaryOverride) ? product.pdfSummaryOverride : null;
  const explicitGhs = getExplicitGhsItems(product, override);
  if (explicitGhs.length) return explicitGhs;
  const inferredGhs = inferGhsItemsFromHazardClassification(product, override);
  return mergeGhsItems(inferredGhs);
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
  syncPdfPreviewForProduct(pdfInfo);
  const override = product.pdfSummaryOverride;
  const detailData = getDetailData(product);
  const workerCautions = buildWorkerCautionPoints(product, detailData);
  const isFieldMode = APP_CONFIG.fieldDisplayMode;
  elements.detailPanel.className = `detail-panel ${isFieldMode ? "is-field-mode" : "is-review-mode"}`;
  elements.detailPanel.innerHTML = `
    ${renderBackToFullListButton()}
    ${detailSection("제품 기본정보", `
      <div class="info-grid">
        ${detailItem("제품명", detailData.productName)}
        ${detailItem("ERP 품명", product.erpName)}
        ${detailItem("MSDS번호", detailData.msdsNo)}
        ${detailItem("파일명", product.fileName)}
        ${detailItem("용도분류", product.useCategory)}
        ${detailItem("권고용도/사용용도", product.recommendedUse)}
        ${detailItem("제조사/공급업체", detailData.supplier)}
        ${detailItem("주소", product.supplierAddress)}
        ${detailItem("정보제공 및 긴급연락처", product.emergencyContact)}
        ${detailItem("최초 작성일 / 최종 개정일", detailData.dateSummary)}
      </div>
    `)}

    ${!isFieldMode ? detailSection("핵심 위험 요약", `
      <div class="risk-summary-grid">
        ${summaryItem("주요 유해성 분류", detailData.hazardSummary, "danger")}
        ${summaryItem("위험물 구분", product.dangerousGoods, "warning")}
        ${summaryItem("PPE 요약", detailData.ppeSummary, "protect")}
      </div>
      ${detailData.overrideApplied && APP_CONFIG.fieldDisplayMode ? `<p class="summary-note pdf-summary-applied">MSDS 원본 기준 요약정보 반영됨</p>` : ""}
    `) : ""}

    ${shouldRenderExtractionStatusSection(override) ? detailSection("MSDS 요약 확인 상태", renderOverrideDetail(override)) : ""}

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
        <div class="ghs-grid">${renderGhsListFromItems(detailData.ghsPictograms, "large", hasLinkedPdf(product))}</div>
        <h4 class="detail-subheading">유해 위험 문구</h4>
        ${renderDetailList(detailData.hazardStatements)}
        <h4 class="detail-subheading">예방조치 문구</h4>
        ${renderPrecautions(detailData.precautionaryStatements)}
        ${detailData.ppeCandidates.length ? `<h4 class="detail-subheading">PPE 및 보호구</h4>${renderDetailList(detailData.ppeCandidates)}` : ""}
      ` : ""}
    `)}

    ${detailSection("MSDS 원본자료 필수 확인", `
      ${renderPdfPreview(pdfInfo)}
    `)}
  `;
}

function renderBackToFullListButton() {
  if (!state.showFullList || !state.showBackToFullList) return "";
  return `
    <button class="detail-return-button" type="button" data-return-full-list>
      목록으로 돌아가기
    </button>
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
  const overrideProductName = product.isPdfAbsorbed
    ? cleanPdfProductName(override?.productNameCandidate)
    : override?.productNameCandidate;
  const overrideSupplier = cleanPdfSupplierName(override?.supplierCandidate);
  const overrideRevisionDate = cleanPdfRevisionDate(override?.revisionDateCandidate);
  const detailSupplier = getDisplaySupplierName({
    ...product,
    supplier: displayValue(overrideSupplier, product.supplier)
  });

  return {
    overrideApplied,
    productName: displayValue(overrideProductName, product.productName),
    supplier: detailSupplier,
    msdsNo: displayValue(override?.msdsNoCandidate, product.msdsNo),
    revisionDate: displayValue(overrideRevisionDate, product.revisionDate),
    dateSummary: buildDateSummary(product.issueDate || product.preparationDate, displayValue(overrideRevisionDate, product.revisionDate)),
    signalWord: override?.signalWordCandidate || "",
    hazardSummary: displayValue(summarizeItems(hazardStatements, 2, " / "), product.hazardSummary),
    ppeSummary: displayValue(summarizeItems(ppeCandidates, 3, ", "), product.ppeSummary),
    ghsPictograms: getDisplayGhsPictograms(product),
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

  addCautionIf(groups.work, text, ["인화", "가연", "화재", "스파크", "화염", "flam", "fire"], "화기·스파크·고온 표면을 피하고 점화원을 관리하세요.");
  addCautionIf(groups.work, text, ["분사", "도포", "혼합", "미스트", "mist"], "분사·도포·혼합 작업 시 증기나 미스트 발생을 확인하세요.");
  addCautionIf(groups.work, text, ["고압가스", "gas", "cylinder"], "고압가스 용기는 충격과 고온 노출을 피하고 고정하세요.");

  addCautionIf(groups.ppe, text, ["보안경", "보호장갑", "호흡보호구", "보호구", "ppe", "goggle", "glove", "respir"], "작업 전 지정된 보호구 착용 상태를 확인하세요.");
  addCautionIf(groups.ppe, text, ["눈", "피부", "자극", "부식", "corros", "irrit"], "눈·피부 접촉을 피하고 보안경과 보호장갑을 착용하세요.");
  addCautionIf(groups.ppe, text, ["호흡", "흡입", "유기용제", "용제", "vapor", "respir"], "필요 시 유기용제용 호흡보호구를 착용하세요.");

  addCautionIf(groups.ventilation, text, ["증기", "미스트", "분진", "흡입", "호흡", "환기", "국소배기", "vapor", "mist", "dust", "inhal"], "작업장을 충분히 환기하고 국소배기 상태를 확인하세요.");
  addCautionIf(groups.ventilation, text, ["톨루엔", "자일렌", "mibk", "butylacetate", "nbutylacetate", "ethylbenzene", "에틸벤젠", "부틸아세테이트", "유기용제", "용제"], "유기용제 증기 노출을 줄이고 장시간 흡입을 피하세요.");
  addCautionIf(groups.ventilation, text, ["반복노출", "장기간", "신체손상", "노출"], "반복 노출 작업은 작업시간과 환기 상태를 함께 확인하세요.");

  addCautionIf(groups.fireStorage, text, ["제4류", "위험물", "인화성액체", "flammableliquid"], "위험물 보관 기준을 지키고 주변 점화원을 제거하세요.");
  addCautionIf(groups.fireStorage, text, ["인화", "고온", "직사광선", "화기", "보관", "storage"], "인화성 물질은 고온, 직사광선, 화기 근처에 보관하지 마세요.");
  addCautionIf(groups.fireStorage, text, ["밀폐", "용기", "폐기", "disposal"], "사용 후 용기는 밀폐하여 지정 장소에 보관하세요.");

  addCautionIf(groups.legal, text, ["관리대상", "작업환경측정", "특수건강진단"], "관리대상 유해물질 여부를 확인하세요.");
  addCautionIf(groups.legal, text, ["작업환경측정", "특수건강진단"], "작업환경측정 및 특수건강진단 대상 여부를 확인하세요.");
  addCautionIf(groups.legal, text, ["cas", "casno", "관리대상", "성분"], "성분정보와 CAS No.로 관리대상 여부를 확인하세요.");

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
    <div class="worker-caution-wrap">
      <h4 class="worker-caution-outside-title">현장 작업 중 주의사항</h4>
      <div class="worker-caution-box">
        <p class="worker-caution-subtitle">MSDS와 성분정보 기준의 현장 참고 안내입니다.</p>
        ${sections.length ? `
        <div class="worker-caution-categories">
          ${sections.map((section) => `
              <section class="worker-caution-group ${section.key === "work" ? "is-primary" : ""}">
                <h5>${escapeHtml(section.key === "work" ? "화기·스파크·고온 주의" : section.title)}</h5>
                <div class="worker-caution-category">
                <ul class="worker-caution-list">
                  ${section.items.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}
                </ul>
                </div>
              </section>
            `).join("")}
        </div>
        ` : `<p class="summary-note">${escapeHtml(cautionData.emptyMessage)}</p>`}
      </div>
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
    return `<p class="summary-note">MSDS 요약 정보가 아직 연결되지 않았습니다.</p>`;
  }

  return `
    <div class="override-status-box ${override.reviewStatus === "검토완료" ? "is-reviewed" : "is-review-needed"}">
      ${detailItem("MSDS 요약 확인 상태", override.extractStatus || "미확인")}
      ${detailItem("검토 상태", override.reviewStatus || "검토필요")}
      ${detailItem("PDF 출처", override.sourcePdfPath || "")}
      ${detailItem("후보 항목", `GHS ${getOverrideGhsItems(override).length}건 / 유해문구 ${override.hazardStatements.length}건 / 구성성분 후보 ${override.ingredients.length}건`)}
    </div>
  `;
}

function buildPdfInfo(product) {
  const fileName = String(product.fileName || "").trim();
  const override = findPdfOverrideForProduct(product) || {};
  const overrideMatch = override.match || {};
  const inventoryItem = findInventoryForProduct(product) || {};
  const displayPath = normalizePdfDisplayPath(override.sourcePdfPath)
    || normalizePdfDisplayPath(override.sourceRelativePath || overrideMatch.relativePath)
    || normalizePdfDisplayPath(inventoryItem.pdfPath)
    || normalizePdfDisplayPath(inventoryItem.relativePath)
    || normalizePdfDisplayPath(product.relativePath || product.sourceRelativePath)
    || normalizePdfDisplayPath(product.pdfPath)
    || (fileName ? normalizePdfDisplayPath(fileName) : "");

  if (!fileName && !displayPath) {
    return {
      status: "no-file-name",
      displayPath: "",
      encodedPath: "",
      title: product.productName || "PDF 미리보기"
    };
  }

  return {
    status: "connected",
    displayPath,
    encodedPath: encodePdfPath(displayPath),
    title: product.productName || fileName || displayPath
  };
}

function normalizePdfDisplayPath(path) {
  const value = String(path || "").trim().replace(/\\/g, "/");
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith("/pdf/")) return value.replace(/^\/+/, "");
  if (value.startsWith("pdf/")) return value;
  if (value.startsWith("/")) return value.replace(/^\/+/, "");
  return `pdf/${value.replace(/^\/?pdf\//, "")}`;
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
        <div class="pdf-frame-placeholder">파일명 정보를 확인하세요.</div>
      </div>
    `;
  }

  if (pdfInfo.status === "missing") {
    return `
      <div class="pdf-preview is-missing">
      <p class="pdf-message">PDF 파일이 아직 등록되지 않았습니다.</p>
      <div class="info-item">
        <span class="info-label">예상 경로</span>
        <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
      </div>
      <div class="pdf-frame-placeholder">PDF 원본을 pdf 폴더에 추가하면 자동 연결됩니다.</div>
    </div>
    `;
  }

  return `
    <div class="pdf-preview is-connected">
      <div class="pdf-required-callout">
        <strong>MSDS 원본자료 필수 확인</strong>
        <span>아래 미리보기에서 원본 MSDS 전체 내용을 확인하세요.</span>
      </div>
      <p class="pdf-message">PDF 파일이 연결되어 있습니다.</p>
      <div class="info-item">
        <span class="info-label">PDF 경로</span>
        <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
      </div>
      ${renderPdfPreviewBody(pdfInfo)}
      <div class="pdf-actions">
        <button class="pdf-preview-button" type="button" data-preview-pdf data-pdf-title="${escapeAttribute(pdfInfo.title)}" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}">PDF 미리보기</button>
        <button class="pdf-preview-button is-secondary" type="button" data-pdf-full-view data-pdf-title="${escapeAttribute(pdfInfo.title)}" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}">원본자료 전체보기</button>
      </div>
      ${state.pdfFullView.isOpen && state.pdfFullView.path === pdfInfo.encodedPath ? renderPdfFullView(pdfInfo) : ""}
    </div>
  `;
}

function renderPdfFullView(pdfInfo) {
  return `
    <div class="pdf-full-view" role="dialog" aria-modal="true" aria-label="MSDS 원본자료 전체보기">
      <div class="pdf-full-view-panel">
        <div class="pdf-full-view-header">
          <div>
            <strong>MSDS 원본자료 전체보기</strong>
            <span>${escapeHtml(pdfInfo.title || "MSDS 원본자료")}</span>
          </div>
          <button class="pdf-full-view-close" type="button" data-close-pdf-full-view>닫기</button>
        </div>
        <div class="pdf-js-preview is-full-view" data-pdfjs-preview-mount data-pdf-viewer-mode="full" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}" data-pdf-title="${escapeAttribute(pdfInfo.title)}">
          <div class="pdf-frame-placeholder">PDF.js 미리보기를 준비하고 있습니다.</div>
        </div>
      </div>
    </div>
  `;
}

function renderPdfPreviewBody(pdfInfo) {
  const isRequested = state.pdfPreview.path === pdfInfo.encodedPath && state.pdfPreview.status !== "idle";

  if (!isRequested) {
    return `
      <div class="pdf-frame-placeholder">
        PDF 미리보기를 보려면 아래 버튼을 눌러주세요.
      </div>
    `;
  }

  if (state.pdfPreview.status === "error") {
    return `
      <div class="pdf-frame-placeholder is-error">
        <p>PDF 미리보기를 불러오지 못했습니다. 관리자에게 문의해주세요.</p>
        ${state.pdfPreview.error ? `<p class="pdf-error-text">${escapeHtml(state.pdfPreview.error)}</p>` : ""}
      </div>
    `;
  }

  return `
    <div class="pdf-js-preview" data-pdfjs-preview-mount data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}" data-pdf-title="${escapeAttribute(pdfInfo.title)}">
      <div class="pdf-frame-placeholder">PDF.js 미리보기를 준비하고 있습니다.</div>
    </div>
  `;
}

function syncPdfPreviewForProduct(pdfInfo) {
  if (state.pdfPreview.path && state.pdfPreview.path !== pdfInfo.encodedPath) {
    resetPdfPreviewState();
  }
}

function startPdfPreview(title, path) {
  if (!path) return;
  state.pdfPreview = {
    path,
    title: title || "PDF 미리보기",
    status: "loading",
    error: "",
    totalPages: 0,
    renderedPages: 0,
    scale: 1,
    fitRatio: 0.88,
    fitToWidth: true,
    expanded: false,
    currentPage: 1,
    restorePage: null,
    restoreOffsetRatio: 0,
    document: null,
    renderToken: 0
  };
  render();
}

function startPdfFullView(title, path) {
  if (!path) return;
  const previewMount = document.querySelector('.pdf-preview [data-pdfjs-preview-mount]:not([data-pdf-viewer-mode="full"])');
  const position = state.pdfPreview.path === path
    ? capturePdfScrollPosition(previewMount, state.pdfPreview)
    : { page: 1, offsetRatio: 0 };
  state.pdfFullView = createPdfViewerState({
    isOpen: true,
    path,
    title: title || state.pdfPreview.title || "PDF 미리보기",
    fitRatio: 0.92,
    restorePage: position.page || 1,
    restoreOffsetRatio: position.offsetRatio || 0
  });
  render();
}

function closePdfFullView() {
  state.pdfFullView = createPdfViewerState();
  render();
  document.querySelector(".pdf-preview.is-connected")?.scrollIntoView({ behavior: "auto", block: "start" });
}

function resetPdfPreviewState() {
  state.pdfPreview = createPdfViewerState();
  state.pdfFullView = createPdfViewerState();
}

function createPdfViewerState(overrides = {}) {
  return {
    isOpen: false,
    path: "",
    title: "",
    status: "idle",
    error: "",
    totalPages: 0,
    renderedPages: 0,
    scale: 1,
    fitRatio: 0.88,
    fitToWidth: true,
    currentPage: 1,
    restorePage: null,
    restoreOffsetRatio: 0,
    document: null,
    renderToken: 0,
    ...overrides
  };
}

function hydrateRequestedPdfPreview() {
  const mounts = [...document.querySelectorAll("[data-pdfjs-preview-mount]")];
  if (!mounts.length) return;
  mounts.forEach((mount) => {
    const viewer = getPdfViewerStateForMount(mount);
    const path = mount.dataset.pdfPath || "";
    if (!viewer.path || path !== viewer.path) return;
    if (viewer.status === "rendering" && mount.dataset.previewStarted === "true") return;
    if (viewer.status === "rendered" && mount.dataset.viewerReady === "true") return;

    preparePdfJsPreview(mount, path, mount.dataset.pdfTitle || viewer.title);
  });
}

function getPdfViewerStateForMount(mount) {
  return mount?.dataset?.pdfViewerMode === "full" ? state.pdfFullView : state.pdfPreview;
}

async function loadPdfJsModule() {
  if (!pdfJsModulePromise) {
    pdfJsModulePromise = import(APP_CONFIG.pdfJsModuleUrl).then((pdfjs) => {
      pdfjs.GlobalWorkerOptions.workerSrc = APP_CONFIG.pdfJsWorkerUrl;
      return pdfjs;
    });
  }
  return pdfJsModulePromise;
}

async function preparePdfJsPreview(mount, path, title) {
  const viewer = getPdfViewerStateForMount(mount);
  viewer.status = "rendering";
  mount.dataset.previewStarted = "true";
  mount.innerHTML = `<div class="pdf-frame-placeholder">PDF.js 미리보기를 불러오는 중입니다.</div>`;

  try {
    if (viewer.document && viewer.path === path) {
      mount.dataset.viewerReady = "true";
      renderPdfViewerShell(mount);
      await renderAllPdfPages(mount);
      return;
    }

    const pdfjs = await loadPdfJsModule();
    const pdf = await pdfjs.getDocument({ url: path }).promise;
    viewer.document = pdf;
    viewer.totalPages = pdf.numPages;
    viewer.renderedPages = 0;
    viewer.title = title || viewer.title;
    mount.dataset.viewerReady = "true";
    renderPdfViewerShell(mount);
    await renderAllPdfPages(mount);
  } catch (error) {
    viewer.status = "error";
    viewer.error = "PDF.js 미리보기 로딩에 실패했습니다.";
    mount.innerHTML = `
      <div class="pdf-frame-placeholder is-error">
        <p>PDF 미리보기를 불러오지 못했습니다. 관리자에게 문의해주세요.</p>
        <p class="pdf-error-text">PDF.js 미리보기 로딩에 실패했습니다.</p>
      </div>
    `;
  }
}

function renderPdfViewerShell(mount) {
  const viewer = getPdfViewerStateForMount(mount);
  mount.innerHTML = `
    <div class="pdf-viewer-toolbar" aria-label="PDF 미리보기 조작">
      <div class="pdf-viewer-group is-page-nav" aria-label="PDF 페이지 이동">
        <button class="pdf-viewer-button is-edge-control" type="button" data-pdf-viewer-action="first-page" aria-label="첫 페이지">
          <span class="pdf-control-full">처음</span><span class="pdf-control-compact" aria-hidden="true">«</span>
        </button>
        <button class="pdf-viewer-button" type="button" data-pdf-viewer-action="prev-page" aria-label="이전 페이지">
          <span class="pdf-control-full">이전</span><span class="pdf-control-compact" aria-hidden="true">‹</span>
        </button>
        <span class="pdf-page-status" data-pdf-page-status>0 / ${viewer.totalPages || 1}쪽</span>
        <button class="pdf-viewer-button" type="button" data-pdf-viewer-action="next-page" aria-label="다음 페이지">
          <span class="pdf-control-full">다음</span><span class="pdf-control-compact" aria-hidden="true">›</span>
        </button>
        <button class="pdf-viewer-button is-edge-control" type="button" data-pdf-viewer-action="last-page" aria-label="마지막 페이지">
          <span class="pdf-control-full">마지막</span><span class="pdf-control-compact" aria-hidden="true">»</span>
        </button>
      </div>
      <div class="pdf-viewer-group is-view-control" aria-label="PDF 보기 조정">
        <button class="pdf-viewer-button" type="button" data-pdf-viewer-action="zoom-out" aria-label="축소">
          <span class="pdf-control-full">축소</span><span class="pdf-control-compact" aria-hidden="true">−</span>
        </button>
        <span class="pdf-zoom-status" data-pdf-zoom-status>100%</span>
        <button class="pdf-viewer-button" type="button" data-pdf-viewer-action="zoom-in" aria-label="확대">
          <span class="pdf-control-full">확대</span><span class="pdf-control-compact" aria-hidden="true">＋</span>
        </button>
        <button class="pdf-viewer-button" type="button" data-pdf-viewer-action="fit" aria-label="화면 맞춤">
          <span class="pdf-control-full">화면 맞춤</span><span class="pdf-control-compact" aria-hidden="true">맞춤</span>
        </button>
      </div>
    </div>
    <div class="pdf-js-page-stage" data-pdf-page-stage>
      <div class="pdf-frame-placeholder">PDF 페이지를 불러오는 중입니다.</div>
    </div>
  `;
  if (!mount.dataset.viewerScrollBound) {
    mount.addEventListener("scroll", () => updatePdfViewerControls(mount), { passive: true });
    mount.dataset.viewerScrollBound = "true";
  }
  updatePdfViewerControls(mount);
}

function updatePdfViewerControls(mount) {
  const viewer = getPdfViewerStateForMount(mount);
  const { renderedPages, totalPages, status } = viewer;
  const isBusy = status === "rendering";
  const pageStatus = mount.querySelector("[data-pdf-page-status]");
  const currentPosition = status === "rendered" && !viewer.suppressPageTracking
    ? capturePdfScrollPosition(mount, viewer)
    : { page: viewer.currentPage || renderedPages || 0 };
  const currentPage = Math.max(0, currentPosition.page || 0);
  if (currentPage > 0) viewer.currentPage = currentPage;
  if (pageStatus) pageStatus.textContent = `${currentPage || renderedPages || 0} / ${totalPages || 1}쪽`;

  const firstButton = mount.querySelector('[data-pdf-viewer-action="first-page"]');
  const prevButton = mount.querySelector('[data-pdf-viewer-action="prev-page"]');
  const nextButton = mount.querySelector('[data-pdf-viewer-action="next-page"]');
  const lastButton = mount.querySelector('[data-pdf-viewer-action="last-page"]');
  const zoomOutButton = mount.querySelector('[data-pdf-viewer-action="zoom-out"]');
  const zoomInButton = mount.querySelector('[data-pdf-viewer-action="zoom-in"]');
  const fitButton = mount.querySelector('[data-pdf-viewer-action="fit"]');
  const zoomStatus = mount.querySelector("[data-pdf-zoom-status]");

  if (firstButton) firstButton.disabled = isBusy || currentPage <= 1;
  if (prevButton) prevButton.disabled = isBusy || currentPage <= 1;
  if (nextButton) nextButton.disabled = isBusy || currentPage >= totalPages;
  if (lastButton) lastButton.disabled = isBusy || currentPage >= totalPages;
  if (zoomOutButton) zoomOutButton.disabled = isBusy || viewer.scale <= 0.6;
  if (zoomInButton) zoomInButton.disabled = isBusy || viewer.scale >= 2.8;
  if (fitButton) fitButton.disabled = isBusy || (viewer.fitToWidth && viewer.fitRatio === 1);
  if (zoomStatus) zoomStatus.textContent = `${Math.round((viewer.scale || 1) * 100)}%`;
}

async function handlePdfViewerAction(action, mount = null) {
  mount = mount || document.querySelector("[data-pdfjs-preview-mount]");
  const preview = getPdfViewerStateForMount(mount);
  if (!mount || !preview.document) return;

  if (action === "first-page" || action === "prev-page" || action === "next-page" || action === "last-page") {
    const position = capturePdfScrollPosition(mount, preview);
    let nextPage = position.page;
    if (action === "first-page") nextPage = 1;
    if (action === "prev-page") nextPage = Math.max(1, position.page - 1);
    if (action === "next-page") nextPage = Math.min(preview.totalPages || 1, position.page + 1);
    if (action === "last-page") nextPage = preview.totalPages || 1;
    scrollPdfPageIntoView(mount, nextPage, 0);
    updatePdfViewerControls(mount);
    return;
  }

  const restorePosition = capturePdfScrollPosition(mount, preview);
  if (action === "zoom-in") {
    preview.fitToWidth = false;
    preview.fitRatio = 1;
    preview.scale = Math.min(2.8, Number((preview.scale + 0.2).toFixed(2)));
  } else if (action === "zoom-out") {
    preview.fitToWidth = false;
    preview.fitRatio = 1;
    preview.scale = Math.max(0.6, Number((preview.scale - 0.2).toFixed(2)));
  } else if (action === "fit") {
    preview.fitToWidth = true;
    preview.fitRatio = 1;
  }

  await renderAllPdfPages(mount, restorePosition);
}

async function renderAllPdfPages(mount, restorePosition = null) {
  const preview = getPdfViewerStateForMount(mount);
  const stage = mount.querySelector("[data-pdf-page-stage]");
  if (!stage || !preview.document) return;
  const hasRenderedContent = Boolean(stage.querySelector("[data-pdf-page-number]"));
  const pendingRestore = restorePosition || (
    preview.restorePage
      ? { page: preview.restorePage, offsetRatio: preview.restoreOffsetRatio || 0 }
      : null
  );

  const renderToken = preview.renderToken + 1;
  preview.renderToken = renderToken;
  preview.status = "rendering";
  preview.suppressPageTracking = true;
  preview.renderedPages = 0;
  mount.classList.add("is-rendering");
  updatePdfViewerControls(mount);
  if (!hasRenderedContent) {
    stage.innerHTML = `<div class="pdf-frame-placeholder">PDF 전체 미리보기를 불러오는 중입니다...</div>`;
  }

  try {
    const nextStage = document.createElement("div");
    nextStage.className = "pdf-js-page-stage";
    for (let pageNumber = 1; pageNumber <= preview.totalPages; pageNumber += 1) {
      if (renderToken !== preview.renderToken) return;
      await renderPdfPageIntoStage(nextStage, pageNumber, renderToken, mount);
      preview.renderedPages = pageNumber;
      updatePdfViewerControls(mount);
      if (!hasRenderedContent) await nextFrame();
    }
    stage.replaceChildren(...Array.from(nextStage.childNodes));
    preview.status = "rendered";
    if (pendingRestore) {
      scrollPdfPageIntoView(mount, pendingRestore.page, pendingRestore.offsetRatio);
      preview.restorePage = null;
      preview.restoreOffsetRatio = 0;
    }
    await nextFrame();
    preview.suppressPageTracking = false;
    mount.classList.remove("is-rendering");
    updatePdfViewerControls(mount);
  } catch (error) {
    preview.status = "error";
    preview.suppressPageTracking = false;
    mount.classList.remove("is-rendering");
    preview.error = "PDF 페이지 렌더링에 실패했습니다.";
    stage.innerHTML = `
      <div class="pdf-frame-placeholder is-error">
        <p>PDF 미리보기를 불러오지 못했습니다.</p>
        <p class="pdf-error-text">관리자에게 문의해주세요.</p>
      </div>
    `;
    updatePdfViewerControls(mount);
  }
}

async function renderPdfPageIntoStage(stage, pageNumber, renderToken, mountOverride = null) {
  const mount = mountOverride || stage.closest("[data-pdfjs-preview-mount]");
  const preview = getPdfViewerStateForMount(mount);
  const page = await preview.document.getPage(pageNumber);
  const baseViewport = page.getViewport({ scale: 1 });
  const isMobileViewer = window.matchMedia?.("(max-width: 679px)")?.matches;
  const horizontalChrome = isMobileViewer ? 18 : 56;
  const availableWidth = Math.max(240, (mount?.clientWidth || stage.parentElement?.clientWidth || 720) - horizontalChrome);
  const fitRatio = Number(preview.fitRatio || 1);
  const scale = preview.fitToWidth ? (availableWidth * fitRatio) / baseViewport.width : preview.scale;
  const viewport = page.getViewport({ scale });
  const pixelRatio = window.devicePixelRatio || 1;
  const canvas = document.createElement("canvas");
  const pageWrap = document.createElement("section");
  const pageLabel = document.createElement("div");
  const context = canvas.getContext("2d");

  if (preview.fitToWidth && pageNumber === 1) preview.scale = scale;
  pageWrap.className = "pdf-js-page";
  pageWrap.dataset.pdfPageNumber = String(pageNumber);
  pageLabel.className = "pdf-js-page-label";
  pageLabel.textContent = `${pageNumber} / ${preview.totalPages}쪽`;
  canvas.width = Math.floor(viewport.width * pixelRatio);
  canvas.height = Math.floor(viewport.height * pixelRatio);
  canvas.style.width = `${Math.floor(viewport.width)}px`;
  canvas.style.height = `${Math.floor(viewport.height)}px`;
  canvas.setAttribute("aria-label", `${preview.title || "PDF"} ${pageNumber}쪽 미리보기`);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  pageWrap.appendChild(pageLabel);
  pageWrap.appendChild(canvas);
  stage.appendChild(pageWrap);
  await page.render({ canvasContext: context, viewport }).promise;
  if (renderToken !== preview.renderToken) return;
}

function capturePdfScrollPosition(mount, viewer = null) {
  viewer = viewer || getPdfViewerStateForMount(mount);
  if (!mount) return { page: viewer.currentPage || 1, offsetRatio: 0 };
  const pages = [...mount.querySelectorAll("[data-pdf-page-number]")];
  if (!pages.length) return { page: viewer.currentPage || 1, offsetRatio: 0 };
  const mountRect = mount.getBoundingClientRect();
  const toolbarHeight = mount.querySelector(".pdf-viewer-toolbar")?.offsetHeight || 0;
  const visibleTop = mountRect.top + toolbarHeight;
  const visibleHeight = Math.max(1, mount.clientHeight - toolbarHeight);
  const targetY = visibleTop + (visibleHeight / 2);
  let currentPage = pages[0];
  let bestDistance = Number.POSITIVE_INFINITY;

  pages.forEach((page) => {
    const rect = page.getBoundingClientRect();
    const overlaps = rect.bottom >= mountRect.top && rect.top <= mountRect.bottom;
    if (!overlaps) return;
    const pageCenter = rect.top + (rect.height / 2);
    const distance = Math.abs(pageCenter - targetY);
    if (distance < bestDistance) {
      currentPage = page;
      bestDistance = distance;
    }
  });

  if (!Number.isFinite(bestDistance)) {
    const fallbackPage = Number(viewer.currentPage || 1);
    return { page: fallbackPage, offsetRatio: viewer.restoreOffsetRatio || 0 };
  }

  const pageNumber = Number(currentPage.dataset.pdfPageNumber || 1);
  const pageTop = getOffsetTopWithin(currentPage, mount);
  const centerInPage = Math.max(0, mount.scrollTop + toolbarHeight + (visibleHeight / 2) - pageTop);
  const offsetRatio = currentPage.offsetHeight ? Math.min(1, centerInPage / currentPage.offsetHeight) : 0;
  return { page: pageNumber, offsetRatio };
}

function scrollPdfPageIntoView(mount, pageNumber, offsetRatio = 0) {
  if (!mount) return;
  const viewer = getPdfViewerStateForMount(mount);
  const page = mount.querySelector(`[data-pdf-page-number="${pageNumber}"]`);
  if (!page) return;
  const toolbarHeight = mount.querySelector(".pdf-viewer-toolbar")?.offsetHeight || 0;
  const visibleHeight = Math.max(1, mount.clientHeight - toolbarHeight);
  const offset = Math.max(0, page.offsetHeight * Math.max(0, Math.min(1, offsetRatio || 0)));
  const pageTop = getOffsetTopWithin(page, mount);
  mount.scrollTop = Math.max(0, pageTop + offset - toolbarHeight - (visibleHeight / 2));
  viewer.currentPage = pageNumber;
}

function getOffsetTopWithin(element, ancestor) {
  let top = 0;
  let node = element;
  while (node && node !== ancestor) {
    top += node.offsetTop || 0;
    node = node.offsetParent;
  }
  if (node === ancestor) return top;
  const elementRect = element.getBoundingClientRect();
  const ancestorRect = ancestor.getBoundingClientRect();
  return elementRect.top - ancestorRect.top + ancestor.scrollTop;
}

function nextFrame() {
  return new Promise((resolve) => window.requestAnimationFrame(resolve));
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
  const displayItems = normalizeDisplayItems(items);
  if (!displayItems.length) return `<p class="empty-text">등록된 문구가 없습니다.</p>`;
  return `<ul class="poster-list ${isCandidate ? "is-candidate" : ""}">${displayItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDetailList(items) {
  const displayItems = normalizeDisplayItems(items);
  if (!displayItems.length) return `<p class="summary-note">정보 없음</p>`;
  const visible = displayItems.slice(0, 5);
  const moreCount = displayItems.length - visible.length;
  return `
    <ul class="detail-list">${visible.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    ${moreCount > 0 ? `<p class="summary-note">외 ${moreCount}건은 PDF 원본에서 확인하세요.</p>` : ""}
  `;
}

function renderPrecautions(precautions, isCandidate = false) {
  const groups = Object.entries(PRECAUTION_LABELS).map(([key, label]) => {
    const items = normalizeDisplayItems(Array.isArray(precautions[key]) ? precautions[key] : []);
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

function normalizeDisplayItems(items = []) {
  return (items || [])
    .flatMap(splitDisplayItem)
    .map(formatDisplayText)
    .filter(Boolean);
}

function splitDisplayItem(value) {
  const text = formatDisplayText(value);
  if (!text) return [];
  const noInfoSummary = summarizeNoInfoText(text);
  if (noInfoSummary) return [noInfoSummary];
  return text
    .split(/\s*(?:\n+|[;；]|ㆍ|•)\s*/g)
    .map(formatDisplayText)
    .filter(Boolean);
}

function formatDisplayText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/([.!?。])(?=\S)/g, "$1 ")
    .replace(/([가-힣)])(P\d{3})/g, "$1 $2")
    .replace(/([가-힣)])(H\d{3})/g, "$1 $2")
    .replace(/\)\s*\(/g, ") (")
    .trim();
}

function summarizeNoInfoText(value) {
  const text = String(value || "").trim();
  const normalized = normalizeSearchText(text);
  const noInfoKeywords = ["없음", "해당없음", "알려진바없음", "분류기준에포함되지않음", "자료없음"];
  const hitCount = noInfoKeywords.filter((keyword) => normalized.includes(normalizeSearchText(keyword))).length;
  if (hitCount >= 2 && normalized.length > 22) {
    return "원문 기준으로 해당 항목은 없음 또는 해당 없음으로 표시되어 있습니다.";
  }
  return "";
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
  const text = String(value || "").trim();
  const isEmpty = !text || text === "-" || text === "정보 없음";
  return `
    <div class="info-item ${isEmpty ? "is-empty" : ""}">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value ${isEmpty ? "is-empty" : ""}">${isEmpty ? "" : escapeHtml(text)}</span>
    </div>
  `;
}

function buildDateSummary(issueDate, revisionDate) {
  const issue = cleanPdfRevisionDate(issueDate) || String(issueDate || "").trim();
  const revision = cleanPdfRevisionDate(revisionDate);
  const parts = [];
  if (issue && issue !== "-" && issue !== "정보 없음") parts.push(`최초 작성일: ${issue}`);
  if (revision && revision !== "-" && revision !== "정보 없음") parts.push(`최종 개정일: ${revision}`);
  return parts.join(" / ");
}

function renderGhsList(product, size) {
  return renderGhsListFromItems(product, size);
}

function renderGhsListFromItems(items, size, usePdfFallback = false) {
  const list = normalizeGhsList(Array.isArray(items) ? { ghsPictograms: items || [] } : (items || {}));
  if (!list.length) return `<span class="no-ghs">${usePdfFallback ? "PDF 원본 확인 필요" : "GHS 정보 없음"}</span>`;
  return list.map((item) => renderGhsPictogram(item, size)).join("");
}

function hasLinkedPdf(product) {
  if (!product) return false;
  const override = product.pdfSummaryOverride || {};
  return Boolean(
    product.pdfPath
    || product.relativePath
    || product.sourceRelativePath
    || product.fileName
    || override.sourcePdfPath
    || override.sourceRelativePath
  );
}

function renderGhsPictogram(item, size) {
  const definition = GHS_DEFINITIONS[item.code] || GHS_DEFINITIONS.GHS07;
  return `
    <figure class="ghs-item ${size}">
      <span class="ghs-diamond" aria-hidden="true">
        <img src="${escapeAttribute(definition.icon)}" alt="" loading="lazy">
      </span>
      <figcaption>${escapeHtml(definition.label)}</figcaption>
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
