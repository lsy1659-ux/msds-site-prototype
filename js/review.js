const REVIEW_CONFIG = {
  localOverridesUrl: "data/msds-overrides.local.json",
  sampleOverridesUrl: "data/msds-overrides.sample.json",
  downloadFileName: "msds-overrides.reviewed.local.json",
  statuses: ["검토필요", "검토완료", "수정필요", "제외"]
};

const reviewState = {
  overrides: [],
  selectedKey: "",
  query: "",
  statusFilter: "all",
  dataMode: "데이터 확인 중",
  dirty: false,
  // 불러올 때의 검토 상태. 이번에 바꾼 것을 목록과 상세에 표시한다.
  originalStatus: new Map(),
  // 불러올 때의 고칠 수 있는 칸 값. 바꾼 것을 원래 값과 나란히 보인다.
  originalFields: new Map(),
  editing: null,
  pdfAvailability: {},
  pdfModal: {
    isOpen: false,
    title: "",
    path: ""
  }
};

const reviewElements = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindReviewElements();
  bindReviewEvents();
  const data = await loadReviewOverrides();
  reviewState.overrides = data.overrides;
  reviewState.dataMode = data.mode;
  reviewState.originalStatus = new Map(data.overrides.map((override, index) => [getOverrideKey(override, index), override.reviewStatus]));
  reviewState.originalFields = new Map(data.overrides.map((override, index) => [getOverrideKey(override, index), editableSnapshot(override)]));
  // 공개 주소에서는 샘플 1건이 실제 검토자료처럼 보였다. 샘플이면 크게 알린다.
  document.querySelector("#reviewSampleBanner")?.toggleAttribute("hidden", !data.mode.includes("샘플"));
  reviewState.selectedKey = getOverrideKey(reviewState.overrides[0], 0);
  renderReview();
});

function bindReviewElements() {
  reviewElements.search = document.querySelector("#reviewSearch");
  reviewElements.statusFilter = document.querySelector("#statusFilter");
  reviewElements.download = document.querySelector("#downloadReviewedJson");
  reviewElements.counts = document.querySelector("#reviewCounts");
  reviewElements.list = document.querySelector("#reviewList");
  reviewElements.listSummary = document.querySelector("#reviewListSummary");
  reviewElements.detail = document.querySelector("#reviewDetail");
  reviewElements.dataMode = document.querySelector("#reviewDataMode");
  reviewElements.dirtyNotice = document.querySelector("#reviewDirtyNotice");
}

function bindReviewEvents() {
  reviewElements.search.addEventListener("input", (event) => {
    reviewState.query = event.target.value;
    selectFirstVisible();
    renderReview();
  });

  reviewElements.statusFilter.addEventListener("change", (event) => {
    reviewState.statusFilter = event.target.value;
    selectFirstVisible();
    renderReview();
  });

  reviewElements.download.addEventListener("click", downloadReviewedJson);

  document.addEventListener("click", (event) => {
    const enlargeButton = event.target.closest("[data-review-open-pdf-modal]");
    if (enlargeButton) {
      openReviewPdfModal(enlargeButton.dataset.pdfTitle, enlargeButton.dataset.pdfPath);
      return;
    }

    const closeButton = event.target.closest("[data-review-close-pdf-modal]");
    if (closeButton || event.target.classList.contains("pdf-modal-backdrop")) {
      closeReviewPdfModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && reviewState.pdfModal.isOpen) {
      closeReviewPdfModal();
    }
  });
}

async function loadReviewOverrides() {
  const localOverrides = await fetchOverrideFile(REVIEW_CONFIG.localOverridesUrl);
  if (localOverrides) {
    return {
      mode: "로컬 override 검토 중",
      overrides: localOverrides.map(normalizeReviewOverride)
    };
  }

  const sampleOverrides = await fetchOverrideFile(REVIEW_CONFIG.sampleOverridesUrl);
  if (sampleOverrides) {
    return {
      mode: "샘플 override 검토 중",
      overrides: sampleOverrides.map(normalizeReviewOverride)
    };
  }

  return {
    mode: "override 없음",
    overrides: []
  };
}

async function fetchOverrideFile(url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to read ${url}`);
    const data = await response.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.overrides)) return data.overrides;
    return null;
  } catch (error) {
    return null;
  }
}

function normalizeReviewOverride(override) {
  const precautions = override.precautionaryStatements || {};
  return {
    ...override,
    match: override.match || {},
    sourcePdfPath: override.sourcePdfPath || "",
    extractStatus: override.extractStatus || "",
    reviewStatus: REVIEW_CONFIG.statuses.includes(override.reviewStatus) ? override.reviewStatus : "검토필요",
    productNameCandidate: override.productNameCandidate || "",
    supplierCandidate: override.supplierCandidate || "",
    msdsNoCandidate: override.msdsNoCandidate || "",
    revisionDateCandidate: override.revisionDateCandidate || "",
    signalWordCandidate: override.signalWordCandidate || "",
    ghsSource: override.ghsSource || "",
    labelGhsCodes: Array.isArray(override.labelGhsCodes) ? override.labelGhsCodes : [],
    labelGhsPictograms: Array.isArray(override.labelGhsPictograms) ? override.labelGhsPictograms : [],
    classificationGhsCodes: Array.isArray(override.classificationGhsCodes) ? override.classificationGhsCodes : [],
    classificationGhsPictograms: Array.isArray(override.classificationGhsPictograms) ? override.classificationGhsPictograms : [],
    ghsCodes: Array.isArray(override.ghsCodes) ? override.ghsCodes : [],
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

function renderReview() {
  const changed = countChangedReviews();
  reviewElements.dataMode.textContent = `${reviewState.dataMode}${changed ? ` / 바꾼 항목 ${changed}건` : ""}`;
  reviewElements.dataMode.classList.toggle("is-local", reviewState.dataMode.includes("로컬"));
  reviewElements.dirtyNotice.classList.toggle("is-hidden", !reviewState.dirty);
  renderCounts();
  renderReviewList();
  renderReviewDetail();
  renderReviewPdfModal();
}

function getOriginalStatus(override, index) {
  return reviewState.originalStatus.get(getOverrideKey(override, index)) || override.reviewStatus;
}

function countChangedReviews() {
  return reviewState.overrides.filter((override, index) => isChangedReview(override, index)).length;
}

function isChangedReview(override, index) {
  return getOriginalStatus(override, index) !== override.reviewStatus || getChangedFields(override, index).length > 0;
}

function renderCounts() {
  const counts = getStatusCounts();
  reviewElements.counts.innerHTML = [
    ["전체", counts.total],
    ...REVIEW_CONFIG.statuses.map((status) => [status, counts[status] || 0])
  ].map(([label, count]) => `
    <span class="review-count-pill">
      <strong>${escapeHtml(label)}</strong>
      <em>${count}</em>
    </span>
  `).join("");
}

function getStatusCounts() {
  return reviewState.overrides.reduce((counts, override) => {
    counts.total += 1;
    counts[override.reviewStatus] = (counts[override.reviewStatus] || 0) + 1;
    return counts;
  }, { total: 0 });
}

function renderReviewList() {
  const filtered = getFilteredOverrides();
  reviewElements.listSummary.textContent = `표시 ${filtered.length}건 / 전체 ${reviewState.overrides.length}건`;

  if (!reviewState.overrides.length) {
    reviewElements.list.innerHTML = `<div class="notice">검토할 override 데이터가 없습니다.</div>`;
    return;
  }

  if (!filtered.length) {
    reviewElements.list.innerHTML = `<div class="notice">검색 또는 상태 필터에 맞는 후보가 없습니다.</div>`;
    return;
  }

  reviewElements.list.innerHTML = filtered.map(({ override, index }) => {
    const key = getOverrideKey(override, index);
    const changed = isChangedReview(override, index);
    return `
      <button class="review-list-item ${key === reviewState.selectedKey ? "is-selected" : ""} ${changed ? "is-changed" : ""}" type="button" data-review-key="${escapeAttribute(key)}">
        <span class="review-status ${getStatusClass(override.reviewStatus)}">${escapeHtml(override.reviewStatus)}</span>
        ${changed ? `<span class="review-changed-mark">이번에 바꿈</span>` : ""}
        <strong class="text-break clamp-2">${escapeHtml(getDisplayTitle(override))}</strong>
        <span class="text-muted-path clamp-2">${escapeHtml(getFileName(override))}</span>
      </button>
    `;
  }).join("");

  reviewElements.list.querySelectorAll("[data-review-key]").forEach((button) => {
    button.addEventListener("click", () => {
      reviewState.selectedKey = button.dataset.reviewKey;
      renderReview();
    });
  });
}

function renderReviewDetail() {
  const selected = getSelectedEntry();
  if (!selected) {
    reviewElements.detail.className = "review-detail empty-detail";
    reviewElements.detail.innerHTML = `<p>선택된 후보가 없습니다.</p>`;
    return;
  }

  const { override, index } = selected;
  const pdfInfo = buildReviewPdfInfo(override);
  const conflict = getGhsConflict(override);
  const originalStatus = getOriginalStatus(override, index);
  // 넓은 화면에서는 후보 옆에 원문 PDF 를 붙여 두고 대조한다(css/tone.css .review-compare).
  reviewElements.detail.className = "review-detail";
  reviewElements.detail.innerHTML = `
    <section class="review-detail-block">
      <div class="review-status-row">
        <label for="reviewStatusSelect">검토 상태</label>
        <select id="reviewStatusSelect" class="review-select">
          ${REVIEW_CONFIG.statuses.map((status) => `
            <option value="${escapeAttribute(status)}" ${status === override.reviewStatus ? "selected" : ""}>${escapeHtml(status)}</option>
          `).join("")}
        </select>
      </div>
      <div class="quick-status-buttons" aria-label="빠른 검토 상태 변경">
        ${quickStatusButton("검토완료", override.reviewStatus)}
        ${quickStatusButton("수정필요", override.reviewStatus)}
        ${quickStatusButton("제외", override.reviewStatus)}
        ${quickStatusButton("검토필요", override.reviewStatus, "검토필요로 되돌리기")}
      </div>
      ${originalStatus !== override.reviewStatus ? `<p class="review-change-line">상태를 바꿨습니다: <s>${escapeHtml(originalStatus)}</s> → <strong>${escapeHtml(override.reviewStatus)}</strong> (수정 JSON 을 내려받아야 남습니다)</p>` : ""}
      <div class="review-navigation-buttons" aria-label="검토 항목 이동">
        <button class="result-nav-button" type="button" data-review-nav="previous">이전 항목</button>
        <button class="result-nav-button" type="button" data-review-nav="next">다음 항목</button>
        <button class="result-nav-button" type="button" data-review-nav="next-needed">다음 검토필요 항목</button>
      </div>
    </section>

    ${renderChangeSummary(override, index)}
    <div class="review-compare">
    <div class="review-compare-fields">
    ${reviewSection("기본 후보", `
      ${conflict ? `<div class="review-conflict-box">${escapeHtml(conflict)}</div>` : ""}
      <div class="info-grid">
        ${reviewItem("PDF 파일명", getFileName(override))}
        ${reviewItem("제품명 후보", override.productNameCandidate)}
        ${reviewItem("제조사 후보", override.supplierCandidate)}
        ${reviewItem("MSDS번호 후보", override.msdsNoCandidate)}
        ${reviewItem("개정일 후보", override.revisionDateCandidate)}
        ${reviewItem("신호어 후보", override.signalWordCandidate)}
        ${reviewItem("GHS 표시 기준", override.ghsSource)}
        ${reviewItem("추출 상태", override.extractStatus)}
        ${reviewItem("검토 상태", override.reviewStatus)}
      </div>
    `)}

    ${editableSection("label", "GHS 실제 표지/현장 표시 · 신호어", `${renderGhsCandidates(override, "label")}<p class="summary-note">신호어 후보: ${escapeHtml(override.signalWordCandidate || "없음")}</p>`, override)}
    ${reviewSection("GHS 분류문구 기준 후보", renderGhsCandidates(override, "classification"))}
    ${editableSection("hazard", "유해위험문구 후보", renderSimpleList(override.hazardStatements), override)}
    ${editableSection("precaution", "예방조치문구 후보", renderPrecautionCandidates(override.precautionaryStatements), override)}
    ${editableSection("ppe", "PPE 후보", renderSimpleList(override.ppeCandidates), override)}
    ${reviewSection("성분/CAS 후보", renderIngredientCandidates(override.ingredients))}
    </div>
    <div class="review-compare-pdf">
    ${reviewSection("원본 PDF 미리보기", renderReviewPdfPreview(pdfInfo))}
    </div>
    </div>
  `;

  reviewElements.detail.querySelector("#reviewStatusSelect")?.addEventListener("change", (event) => {
    setReviewStatus(index, event.target.value);
  });

  reviewElements.detail.querySelectorAll("[data-review-status]").forEach((button) => {
    button.addEventListener("click", () => setReviewStatus(index, button.dataset.reviewStatus));
  });

  reviewElements.detail.querySelectorAll("[data-review-nav]").forEach((button) => {
    button.addEventListener("click", () => moveReviewSelection(button.dataset.reviewNav));
  });

  reviewElements.detail.querySelectorAll("[data-review-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      reviewState.editing = { key: reviewState.selectedKey, group: button.dataset.reviewEdit };
      renderReview();
    });
  });
  reviewElements.detail.querySelector("[data-edit-cancel]")?.addEventListener("click", () => {
    reviewState.editing = null;
    renderReview();
  });
  reviewElements.detail.querySelector("[data-edit-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveReviewEdit(event.currentTarget, index);
  });
}

function quickStatusButton(status, currentStatus, label = status) {
  return `
    <button class="quick-status-button ${status === currentStatus ? "is-active" : ""}" type="button" data-review-status="${escapeAttribute(status)}">
      ${escapeHtml(label)}
    </button>
  `;
}

function setReviewStatus(index, status) {
  if (!REVIEW_CONFIG.statuses.includes(status)) return;
  reviewState.overrides[index].reviewStatus = status;
  reviewState.dirty = true;
  if (!getFilteredOverrides().some((entry) => getOverrideKey(entry.override, entry.index) === reviewState.selectedKey)) {
    selectFirstVisible();
  }
  renderReview();
}

function moveReviewSelection(action) {
  const filtered = getFilteredOverrides();
  if (!filtered.length) return;
  const currentIndex = filtered.findIndex((entry) => getOverrideKey(entry.override, entry.index) === reviewState.selectedKey);

  if (action === "previous") {
    const nextIndex = currentIndex <= 0 ? filtered.length - 1 : currentIndex - 1;
    reviewState.selectedKey = getOverrideKey(filtered[nextIndex].override, filtered[nextIndex].index);
    renderReview();
    return;
  }

  if (action === "next") {
    const nextIndex = currentIndex < 0 || currentIndex >= filtered.length - 1 ? 0 : currentIndex + 1;
    reviewState.selectedKey = getOverrideKey(filtered[nextIndex].override, filtered[nextIndex].index);
    renderReview();
    return;
  }

  if (action === "next-needed") {
    const allEntries = reviewState.overrides.map((override, index) => ({ override, index }));
    const selected = getSelectedEntry();
    const start = selected ? selected.index + 1 : 0;
    const ordered = [...allEntries.slice(start), ...allEntries.slice(0, start)];
    const nextNeeded = ordered.find((entry) => entry.override.reviewStatus === "검토필요");
    if (nextNeeded) {
      reviewState.selectedKey = getOverrideKey(nextNeeded.override, nextNeeded.index);
      reviewState.statusFilter = "all";
      reviewElements.statusFilter.value = "all";
      renderReview();
    }
  }
}

function getFilteredOverrides() {
  const query = normalizeText(reviewState.query);
  return reviewState.overrides
    .map((override, index) => ({ override, index }))
    .filter(({ override }) => {
      const statusMatch = reviewState.statusFilter === "all" || override.reviewStatus === reviewState.statusFilter;
      if (!statusMatch) return false;
      if (!query) return true;
      return normalizeText(buildReviewSearchSource(override)).includes(query);
    });
}

function buildReviewSearchSource(override) {
  return [
    getFileName(override),
    override.productNameCandidate,
    override.supplierCandidate,
    override.msdsNoCandidate,
    override.sourcePdfPath,
    (override.ingredients || []).map((ingredient) => [
      ingredient.chemicalName,
      ingredient.casNo,
      ingredient.content
    ].join(" ")).join(" ")
  ].join(" ");
}

function selectFirstVisible() {
  const first = getFilteredOverrides()[0];
  reviewState.selectedKey = first ? getOverrideKey(first.override, first.index) : "";
}

function getSelectedEntry() {
  return reviewState.overrides
    .map((override, index) => ({ override, index }))
    .find(({ override, index }) => getOverrideKey(override, index) === reviewState.selectedKey)
    || getFilteredOverrides()[0]
    || null;
}

function getOverrideKey(override, index) {
  return `${getFileName(override) || override.msdsNoCandidate || override.productNameCandidate || "override"}__${index}`;
}

function getFileName(override) {
  return override.match?.fileName || fileNameFromPath(override.sourcePdfPath) || "";
}

function fileNameFromPath(value) {
  const text = String(value || "");
  return text.split("/").filter(Boolean).pop() || "";
}

function getDisplayTitle(override) {
  return override.productNameCandidate || getFileName(override) || "이름 없는 후보";
}

function getStatusClass(status) {
  if (status === "검토완료") return "is-reviewed";
  if (status === "수정필요") return "is-edit-needed";
  if (status === "제외") return "is-excluded";
  return "is-review-needed";
}

function containsNoGhsLabelElement(value) {
  const normalized = normalizeText(value);
  return normalized.includes("해당없음")
    || normalized.includes("유해화학물질로분류되지않음")
    || normalized.includes("분류되지않음")
    || normalized.includes("notclassified")
    || normalized.includes("noghslabelelement")
    || normalized.includes("notapplicable");
}

function getGhsConflict(override) {
  if (!getReviewGhsItems(override).length) return "";
  const noLabelSignal = containsNoGhsLabelElement(override.signalWordCandidate);
  const noHazardStatements = !override.hazardStatements?.length;
  if (noLabelSignal || noHazardStatements) {
    return "확인 필요: 신호어 또는 유해위험문구가 해당없음 계열인데 GHS 후보가 있습니다. PDF 2번 항목의 그림문자/표지요소를 확인하세요.";
  }
  return "";
}

function reviewSection(title, content) {
  return `
    <section class="review-detail-block">
      <h3>${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;
}

function reviewItem(label, value) {
  return `
    <div class="info-item">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value">${escapeHtml(value || "정보 없음")}</span>
    </div>
  `;
}

function getReviewGhsItems(override, mode = "display") {
  let codes = Array.isArray(override?.ghsCodes) ? override.ghsCodes : [];
  let pictograms = Array.isArray(override?.ghsPictograms) ? override.ghsPictograms : [];
  if (mode === "label") {
    codes = Array.isArray(override?.labelGhsCodes) && override.labelGhsCodes.length
      ? override.labelGhsCodes
      : codes;
    pictograms = Array.isArray(override?.labelGhsPictograms) && override.labelGhsPictograms.length
      ? override.labelGhsPictograms
      : pictograms;
  }
  if (mode === "classification") {
    codes = Array.isArray(override?.classificationGhsCodes) ? override.classificationGhsCodes : [];
    pictograms = Array.isArray(override?.classificationGhsPictograms) ? override.classificationGhsPictograms : [];
  }
  const items = [
    ...codes.map((code) => ({ code, label: code })),
    ...pictograms
  ];
  const seen = new Set();
  return items.filter((item) => {
    const key = String(item.code || item.label || item || "").trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function renderGhsCandidates(override, mode = "display") {
  const items = getReviewGhsItems(override, mode);
  if (!items.length) return `<p class="summary-note">GHS 후보 없음</p>`;
  return `
    <div class="review-chip-list">
      ${items.map((item) => `<span class="review-chip">${escapeHtml([item.code, item.label].filter(Boolean).join(" "))}</span>`).join("")}
    </div>
  `;
}

function renderSimpleList(items) {
  if (!items.length) return `<p class="summary-note">후보 없음</p>`;
  return `<ul class="review-candidate-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderPrecautionCandidates(precautions) {
  const labels = {
    prevention: "예방",
    response: "대응",
    storage: "저장",
    disposal: "폐기"
  };
  const groups = Object.entries(labels).map(([key, label]) => {
    const items = Array.isArray(precautions[key]) ? precautions[key] : [];
    if (!items.length) return "";
    return `
      <div class="review-precaution-group">
        <strong>${escapeHtml(label)}</strong>
        ${renderSimpleList(items)}
      </div>
    `;
  }).join("");
  return groups || `<p class="summary-note">예방조치문구 후보 없음</p>`;
}

function renderIngredientCandidates(ingredients) {
  if (!ingredients.length) return `<p class="summary-note">성분/CAS 후보 없음</p>`;
  return `
    <div class="component-table-wrap">
      <table class="component-table review-component-table">
        <thead>
          <tr>
            <th>화학물질명</th>
            <th>CAS No.</th>
            <th>함유량</th>
          </tr>
        </thead>
        <tbody>
          ${ingredients.map((ingredient) => `
            <tr>
              <td>${escapeHtml(ingredient.chemicalName || "")}</td>
              <td>${escapeHtml(ingredient.casNo || "")}</td>
              <td>${escapeHtml(ingredient.content || "")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderPdfOpenButton(override) {
  const pdfPath = normalizeReviewPdfDisplayPath(override.sourcePdfPath || (getFileName(override) ? `pdf/${getFileName(override)}` : ""));
  if (!pdfPath) return `<p class="summary-note">원본 PDF 경로 정보가 없습니다.</p>`;
  return `
    <div class="review-actions">
      <a class="pdf-open-button" href="${escapeAttribute(encodePdfPath(pdfPath))}" target="_blank" rel="noopener">원본 PDF 열기</a>
    </div>
  `;
}

function buildReviewPdfInfo(override) {
  const displayPath = normalizeReviewPdfDisplayPath(override.sourcePdfPath || (getFileName(override) ? `pdf/${getFileName(override)}` : ""));
  if (!displayPath) {
    return {
      status: "no-path",
      displayPath: "",
      encodedPath: "",
      title: getDisplayTitle(override)
    };
  }
  const encodedPath = encodePdfPath(displayPath);
  return {
    status: reviewState.pdfAvailability[encodedPath] || "unchecked",
    displayPath,
    encodedPath,
    title: getDisplayTitle(override)
  };
}

function renderReviewPdfPreview(pdfInfo) {
  if (pdfInfo.status === "no-path") {
    return `
      <div class="pdf-preview is-missing">
        <p class="pdf-message">PDF 경로 정보가 없어 미리보기가 어렵습니다.</p>
        <div class="pdf-frame-placeholder">PDF 파일명 또는 sourcePdfPath 확인 필요</div>
      </div>
    `;
  }

  if (pdfInfo.status === "unchecked") {
    scheduleReviewPdfAvailabilityCheck(pdfInfo.encodedPath);
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
        <iframe class="pdf-frame review-pdf-frame" title="원본 PDF 미리보기" src="${escapeAttribute(pdfInfo.encodedPath)}"></iframe>
        <div class="pdf-actions">
          <button class="pdf-enlarge-button" type="button" data-review-open-pdf-modal data-pdf-title="${escapeAttribute(pdfInfo.title)}" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}">크게 보기</button>
          <a class="pdf-open-button" href="${escapeAttribute(pdfInfo.encodedPath)}" target="_blank" rel="noopener">새 탭에서 열기</a>
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
        <div class="pdf-actions">
          <a class="pdf-open-button" href="${escapeAttribute(pdfInfo.encodedPath)}" target="_blank" rel="noopener">새 탭에서 열기</a>
        </div>
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
      <div class="pdf-frame-placeholder">PDF 원본을 pdf 폴더에 추가하면 미리보기로 확인할 수 있습니다.</div>
    </div>
  `;
}

function scheduleReviewPdfAvailabilityCheck(path) {
  reviewState.pdfAvailability[path] = "checking";
  checkReviewPdfExists(path).then((exists) => {
    reviewState.pdfAvailability[path] = exists ? "available" : "missing";
    const selected = getSelectedEntry();
    if (selected && buildReviewPdfInfo(selected.override).encodedPath === path) renderReview();
  });
}

async function checkReviewPdfExists(path) {
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

function openReviewPdfModal(title, path) {
  if (!path) return;
  reviewState.pdfModal = {
    isOpen: true,
    title: title || "PDF 미리보기",
    path
  };
  renderReviewPdfModal();
}

function closeReviewPdfModal() {
  reviewState.pdfModal = {
    isOpen: false,
    title: "",
    path: ""
  };
  renderReviewPdfModal();
}

function ensureReviewPdfModalElement() {
  let modal = document.querySelector("#reviewPdfPreviewModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "reviewPdfPreviewModal";
    document.body.appendChild(modal);
  }
  return modal;
}

function renderReviewPdfModal() {
  const modal = ensureReviewPdfModalElement();
  document.body.classList.toggle("modal-open", reviewState.pdfModal.isOpen);

  if (!reviewState.pdfModal.isOpen) {
    modal.className = "pdf-modal is-hidden";
    modal.innerHTML = "";
    return;
  }

  modal.className = "pdf-modal";
  modal.innerHTML = `
    <div class="pdf-modal-backdrop">
      <section class="pdf-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="reviewPdfModalTitle">
        <header class="pdf-modal-toolbar">
          <div>
            <h2 id="reviewPdfModalTitle">PDF 미리보기</h2>
            <p>${escapeHtml(reviewState.pdfModal.title)}</p>
          </div>
          <button class="pdf-modal-close" type="button" data-review-close-pdf-modal aria-label="PDF 크게 보기 닫기">닫기</button>
        </header>
        <iframe class="pdf-modal-frame" title="${escapeAttribute(reviewState.pdfModal.title)} PDF 크게 보기" src="${escapeAttribute(reviewState.pdfModal.path)}"></iframe>
      </section>
    </div>
  `;
  modal.querySelector("[data-review-close-pdf-modal]")?.focus();
}

function downloadReviewedJson() {
  const content = JSON.stringify(reviewState.overrides, null, 2);
  const blob = new Blob([content], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = REVIEW_CONFIG.downloadFileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function normalizeReviewPdfDisplayPath(path) {
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

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\.pdf/gi, "")
    .replace(/[\s()[\]{}<>（）［］｛｝_\-\/\\]/g, "");
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


/* ── 문구 직접 고치기 ───────────────────────────────────────
 * 상태만 바꾸던 화면에서, 잘못 읽힌 문구·그림문자·신호어를 바로 고친다.
 * 고친 것은 그 항목의 reviewLog 에 남는다: 언제, 누가, 원문 몇 쪽을 보고,
 * 그때 PDF 의 지문(SHA-256), 바꾸기 전과 뒤. 같은 자리에 새 PDF 가 들어오면
 * 지문이 달라 다시 봐야 할 것을 알 수 있다.
 * 내려받은 파일은 scripts/apply_reviewed_overrides.py 가 검사해 반영한다. */
const REVIEW_EDIT_GROUPS = {
  hazard: { title: "유해위험문구", fields: [{ field: "hazardStatements", label: "유해위험문구", kind: "lines" }] },
  precaution: {
    title: "예방조치문구",
    fields: [
      { field: "precautionaryStatements.prevention", label: "예방", kind: "lines" },
      { field: "precautionaryStatements.response", label: "대응", kind: "lines" },
      { field: "precautionaryStatements.storage", label: "저장", kind: "lines" },
      { field: "precautionaryStatements.disposal", label: "폐기", kind: "lines" }
    ]
  },
  ppe: { title: "PPE 후보", fields: [{ field: "ppeCandidates", label: "PPE 후보", kind: "lines" }] },
  label: {
    title: "그림문자 · 신호어",
    fields: [
      { field: "labelGhsCodes", label: "실제 표지 그림문자", kind: "ghs" },
      { field: "signalWordCandidate", label: "신호어", kind: "signal" }
    ]
  }
};
const REVIEW_EDIT_FIELDS = Object.values(REVIEW_EDIT_GROUPS).flatMap((group) => group.fields);
const REVIEW_GHS_CODES = ["GHS01", "GHS02", "GHS03", "GHS04", "GHS05", "GHS06", "GHS07", "GHS08", "GHS09"];
const REVIEW_GHS_NAMES = {
  GHS01: "폭발성", GHS02: "인화성", GHS03: "산화성", GHS04: "고압가스", GHS05: "부식성",
  GHS06: "급성독성", GHS07: "유해/자극성", GHS08: "건강유해성", GHS09: "환경유해성"
};
const REVIEW_SIGNALS = ["", "위험", "경고", "해당없음"];
const REVIEWER_KEY = "msds.reviewer.v1";

function readField(override, field) {
  return field.split(".").reduce((value, key) => (value == null ? value : value[key]), override);
}

function writeField(override, field, value) {
  const keys = field.split(".");
  let target = override;
  keys.slice(0, -1).forEach((key) => {
    if (!target[key] || typeof target[key] !== "object") target[key] = {};
    target = target[key];
  });
  target[keys[keys.length - 1]] = value;
}

// 빈 목록과 빈 값은 같은 것으로 본다. 바꾸지 않은 칸이 바뀐 것으로 잡히지 않게.
function comparable(value) {
  if (Array.isArray(value)) return value.length ? JSON.stringify(value) : "";
  return value == null ? "" : JSON.stringify(value);
}

function editableSnapshot(override) {
  return Object.fromEntries(REVIEW_EDIT_FIELDS.map(({ field }) => [field, JSON.parse(JSON.stringify(readField(override, field) ?? null))]));
}

function getChangedFields(override, index) {
  const before = reviewState.originalFields.get(getOverrideKey(override, index));
  if (!before) return [];
  return REVIEW_EDIT_FIELDS.filter(({ field }) => comparable(before[field]) !== comparable(readField(override, field)));
}

function readReviewer() {
  try { return window.localStorage.getItem(REVIEWER_KEY) || ""; } catch (error) { return ""; }
}

function rememberReviewer(name) {
  try { window.localStorage.setItem(REVIEWER_KEY, name); } catch (error) { /* 저장소 차단 환경 */ }
}

async function pdfSha256(override) {
  const info = buildReviewPdfInfo(override);
  if (!info?.encodedPath || !window.crypto?.subtle) return "";
  try {
    const response = await fetch(info.encodedPath, { cache: "no-store" });
    if (!response.ok) return "";
    const digest = await window.crypto.subtle.digest("SHA-256", await response.arrayBuffer());
    return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  } catch (error) {
    return "";
  }
}

function editButton(groupKey) {
  return `<button type="button" class="review-edit-button" data-review-edit="${escapeAttribute(groupKey)}">고치기</button>`;
}

function editableSection(groupKey, title, content, override) {
  // 다른 항목으로 옮기면 열어 둔 편집 칸은 따라가지 않는다.
  const editing = reviewState.editing?.group === groupKey && reviewState.editing.key === reviewState.selectedKey;
  return `
    <section class="review-detail-block ${editing ? "is-editing" : ""}">
      <div class="review-block-head"><h3>${escapeHtml(title)}</h3>${editing ? "" : editButton(groupKey)}</div>
      ${editing ? renderEditor(override, groupKey) : content}
    </section>
  `;
}

function renderEditor(override, groupKey) {
  const group = REVIEW_EDIT_GROUPS[groupKey];
  const fields = group.fields.map(({ field, label, kind }) => {
    const value = readField(override, field);
    if (kind === "lines") {
      const lines = Array.isArray(value) ? value : [];
      return `<label class="review-edit-field"><span>${escapeHtml(label)}</span>
        <textarea data-edit-field="${escapeAttribute(field)}" rows="${Math.min(14, Math.max(3, lines.length + 1))}">${escapeHtml(lines.join("\n"))}</textarea></label>`;
    }
    if (kind === "ghs") {
      const codes = new Set(Array.isArray(value) && value.length ? value : (override.ghsCodes || []));
      return `<fieldset class="review-edit-field" data-edit-ghs="${escapeAttribute(field)}"><legend>${escapeHtml(label)}</legend>
        <div class="review-edit-ghs">${REVIEW_GHS_CODES.map((code) => `<label><input type="checkbox" value="${code}" ${codes.has(code) ? "checked" : ""}> ${code} ${escapeHtml(REVIEW_GHS_NAMES[code])}</label>`).join("")}</div></fieldset>`;
    }
    return `<label class="review-edit-field"><span>${escapeHtml(label)}</span>
      <select data-edit-field="${escapeAttribute(field)}">${REVIEW_SIGNALS.map((signal) => `<option value="${escapeAttribute(signal)}" ${signal === (value || "") ? "selected" : ""}>${escapeHtml(signal || "(비움)")}</option>`).join("")}</select></label>`;
  }).join("");
  return `
    <form class="review-editor" data-edit-form="${escapeAttribute(groupKey)}">
      ${fields}
      <p class="review-edit-hint">한 줄에 문구 하나. 코드(H225 · P210)를 앞에 두세요. 원문에 있는 글만 적습니다.</p>
      <div class="review-edit-evidence">
        <label><span>원문 쪽</span><input type="number" min="1" inputmode="numeric" data-edit-page placeholder="예: 2" required></label>
        <label><span>검토자</span><input type="text" data-edit-reviewer value="${escapeAttribute(readReviewer())}" placeholder="이름" required></label>
      </div>
      <div class="review-edit-actions">
        <button type="submit" class="quick-status-button is-active">저장</button>
        <button type="button" class="quick-status-button" data-edit-cancel>취소</button>
      </div>
    </form>
  `;
}

async function saveReviewEdit(form, index) {
  const override = reviewState.overrides[index];
  const group = REVIEW_EDIT_GROUPS[form.dataset.editForm];
  const page = Number(form.querySelector("[data-edit-page]")?.value || 0) || null;
  const reviewer = String(form.querySelector("[data-edit-reviewer]")?.value || "").trim();
  if (reviewer) rememberReviewer(reviewer);
  const next = {};
  group.fields.forEach(({ field, kind }) => {
    if (kind === "lines") {
      next[field] = String(form.querySelector(`[data-edit-field="${field}"]`)?.value || "")
        .split("\n").map((line) => line.trim()).filter(Boolean);
    } else if (kind === "ghs") {
      next[field] = [...form.querySelectorAll(`[data-edit-ghs="${field}"] input:checked`)].map((box) => box.value);
    } else {
      next[field] = String(form.querySelector(`[data-edit-field="${field}"]`)?.value || "");
    }
  });
  const changed = Object.keys(next).filter((field) => comparable(readField(override, field)) !== comparable(next[field]));
  if (!changed.length) {
    reviewState.editing = null;
    renderReview();
    return;
  }
  const sha = await pdfSha256(override);
  const at = new Date().toISOString();
  const pdf = buildReviewPdfInfo(override)?.displayPath || override.sourcePdfPath || "";
  override.reviewLog = Array.isArray(override.reviewLog) ? override.reviewLog : [];
  changed.forEach((field) => {
    override.reviewLog.push({ at, reviewer, field, page, pdf, pdfSha256: sha, before: readField(override, field) ?? null, after: next[field] });
    writeField(override, field, next[field]);
    // 실제 표지 그림문자를 고치면 화면이 같이 쓰는 칸도 맞춘다.
    if (field === "labelGhsCodes") {
      override.ghsCodes = next[field];
      override.labelGhsPictograms = next[field].map((code) => ({ code, label: REVIEW_GHS_NAMES[code] }));
    }
  });
  reviewState.dirty = true;
  reviewState.editing = null;
  renderReview();
}

// 바꾼 칸을 원래 값과 나란히 보인다. 지운 줄은 줄을 긋고, 넣은 줄은 밑줄을 친다.
function renderChangeSummary(override, index) {
  const changed = getChangedFields(override, index);
  if (!changed.length) return "";
  const before = reviewState.originalFields.get(getOverrideKey(override, index)) || {};
  const asLines = (value) => (Array.isArray(value) ? value : value ? [value] : []).map((item) => typeof item === "object" ? JSON.stringify(item) : String(item));
  const rows = changed.map(({ field, label }) => {
    const old = asLines(before[field]);
    const now = asLines(readField(override, field));
    const removed = old.filter((line) => !now.includes(line));
    const added = now.filter((line) => !old.includes(line));
    return `<li><strong>${escapeHtml(label)}</strong>
      ${removed.map((line) => `<del>${escapeHtml(line)}</del>`).join("")}
      ${added.map((line) => `<ins>${escapeHtml(line)}</ins>`).join("")}
      ${!removed.length && !added.length ? "<span>(차례만 바뀜)</span>" : ""}</li>`;
  }).join("");
  const log = (override.reviewLog || []).slice(-3).reverse().map((entry) =>
    `<li>${escapeHtml(String(entry.at || "").slice(0, 10))} · ${escapeHtml(entry.reviewer || "검토자 미기재")} · ${escapeHtml(entry.field)}${entry.page ? ` · 원문 ${escapeHtml(entry.page)}쪽` : ""}${entry.pdfSha256 ? "" : " · PDF 지문 없음"}</li>`).join("");
  return `
    <section class="review-detail-block review-change-block">
      <h3>바꾼 문구 (원래 → 지금)</h3>
      <ul class="review-change-list">${rows}</ul>
      ${log ? `<p class="summary-note">최근 기록</p><ul class="review-change-log">${log}</ul>` : ""}
    </section>
  `;
}
