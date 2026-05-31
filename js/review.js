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
  dirty: false
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
  renderCounts();
  renderReviewList();
  renderReviewDetail();
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
        <strong>${escapeHtml(getDisplayTitle(override))}</strong>
        <span>${escapeHtml(getFileName(override))}</span>
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
    </section>

    ${reviewSection("기본 후보", `
      <div class="info-grid">
        ${reviewItem("PDF 파일명", getFileName(override))}
        ${reviewItem("제품명 후보", override.productNameCandidate)}
        ${reviewItem("제조사 후보", override.supplierCandidate)}
        ${reviewItem("MSDS번호 후보", override.msdsNoCandidate)}
        ${reviewItem("개정일 후보", override.revisionDateCandidate)}
        ${reviewItem("신호어 후보", override.signalWordCandidate)}
        ${reviewItem("추출 상태", override.extractStatus)}
      </div>
      ${renderPdfOpenButton(override)}
    `)}

    ${reviewSection("GHS 후보", renderGhsCandidates(override.ghsPictograms))}
    ${reviewSection("유해위험문구 후보", renderSimpleList(override.hazardStatements))}
    ${reviewSection("예방조치문구 후보", renderPrecautionCandidates(override.precautionaryStatements))}
    ${reviewSection("PPE 후보", renderSimpleList(override.ppeCandidates))}
    ${reviewSection("성분/CAS 후보", renderIngredientCandidates(override.ingredients))}
  `;

  reviewElements.detail.querySelector("#reviewStatusSelect")?.addEventListener("change", (event) => {
    reviewState.overrides[index].reviewStatus = event.target.value;
    reviewState.dirty = true;
    if (!getFilteredOverrides().some((entry) => getOverrideKey(entry.override, entry.index) === reviewState.selectedKey)) {
      selectFirstVisible();
    }
    renderReview();
  });
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

function renderGhsCandidates(items) {
  if (!items.length) return `<p class="summary-note">GHS 후보 없음</p>`;
  return `
    <div class="review-chip-list">
      ${items.map((item) => `<span class="review-chip">${escapeHtml(item.label || item.code || "GHS 후보")}</span>`).join("")}
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
