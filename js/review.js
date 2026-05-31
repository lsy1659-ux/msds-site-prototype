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
  reviewElements.dataMode.textContent = `${reviewState.dataMode}${reviewState.dirty ? " / 수정됨" : ""}`;
  reviewElements.dataMode.classList.toggle("is-local", reviewState.dataMode.includes("로컬"));
  reviewElements.dirtyNotice.classList.toggle("is-hidden", !reviewState.dirty);
  renderCounts();
  renderReviewList();
  renderReviewDetail();
  renderReviewPdfModal();
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
    return `
      <button class="review-list-item ${key === reviewState.selectedKey ? "is-selected" : ""}" type="button" data-review-key="${escapeAttribute(key)}">
        <span class="review-status ${getStatusClass(override.reviewStatus)}">${escapeHtml(override.reviewStatus)}</span>
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
      <div class="review-navigation-buttons" aria-label="검토 항목 이동">
        <button class="result-nav-button" type="button" data-review-nav="previous">이전 항목</button>
        <button class="result-nav-button" type="button" data-review-nav="next">다음 항목</button>
        <button class="result-nav-button" type="button" data-review-nav="next-needed">다음 검토필요 항목</button>
      </div>
    </section>

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

    ${reviewSection("GHS 실제 표지/현장 표시", renderGhsCandidates(override, "label"))}
    ${reviewSection("GHS 분류문구 기준 후보", renderGhsCandidates(override, "classification"))}
    ${reviewSection("유해위험문구 후보", renderSimpleList(override.hazardStatements))}
    ${reviewSection("예방조치문구 후보", renderPrecautionCandidates(override.precautionaryStatements))}
    ${reviewSection("PPE 후보", renderSimpleList(override.ppeCandidates))}
    ${reviewSection("성분/CAS 후보", renderIngredientCandidates(override.ingredients))}
    ${reviewSection("원본 PDF 미리보기", renderReviewPdfPreview(pdfInfo))}
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
  const pdfPath = override.sourcePdfPath || (getFileName(override) ? `/pdf/${getFileName(override)}` : "");
  if (!pdfPath) return `<p class="summary-note">원본 PDF 경로 정보가 없습니다.</p>`;
  return `
    <div class="review-actions">
      <a class="pdf-open-button" href="${escapeAttribute(encodePdfPath(pdfPath))}" target="_blank" rel="noopener">원본 PDF 열기</a>
    </div>
  `;
}

function buildReviewPdfInfo(override) {
  const displayPath = override.sourcePdfPath || (getFileName(override) ? `/pdf/${getFileName(override)}` : "");
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
