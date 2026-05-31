const QUEUE_CONFIG = {
  localQueueUrl: "data/pdf-registration-queue.local.json",
  sampleQueueUrl: "data/pdf-registration-queue.sample.json",
  downloadFileName: "pdf-registration-queue.reviewed.local.json",
  decisions: ["미검토", "엑셀등록필요", "기존제품매핑필요", "중복의심", "제외", "보류"]
};

const queueState = {
  items: [],
  selectedKey: "",
  query: "",
  decisionFilter: "all",
  dataMode: "데이터 확인 중",
  dirty: false,
  pdfAvailability: {},
  pdfModal: {
    isOpen: false,
    title: "",
    path: ""
  }
};

const queueElements = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindQueueElements();
  bindQueueEvents();
  const data = await loadQueueData();
  queueState.items = data.items;
  queueState.dataMode = data.mode;
  queueState.selectedKey = getQueueKey(queueState.items[0], 0);
  renderQueue();
});

function bindQueueElements() {
  queueElements.search = document.querySelector("#queueSearch");
  queueElements.decisionFilter = document.querySelector("#queueDecisionFilter");
  queueElements.download = document.querySelector("#downloadQueueJson");
  queueElements.counts = document.querySelector("#queueCounts");
  queueElements.list = document.querySelector("#queueList");
  queueElements.listSummary = document.querySelector("#queueListSummary");
  queueElements.detail = document.querySelector("#queueDetail");
  queueElements.dataMode = document.querySelector("#queueDataMode");
  queueElements.dirtyNotice = document.querySelector("#queueDirtyNotice");
}

function bindQueueEvents() {
  queueElements.search.addEventListener("input", (event) => {
    queueState.query = event.target.value;
    selectFirstVisibleQueueItem();
    renderQueue();
  });

  queueElements.decisionFilter.addEventListener("change", (event) => {
    queueState.decisionFilter = event.target.value;
    selectFirstVisibleQueueItem();
    renderQueue();
  });

  queueElements.download.addEventListener("click", downloadQueueJson);

  document.addEventListener("click", (event) => {
    const enlargeButton = event.target.closest("[data-queue-open-pdf-modal]");
    if (enlargeButton) {
      openQueuePdfModal(enlargeButton.dataset.pdfTitle, enlargeButton.dataset.pdfPath);
      return;
    }

    const closeButton = event.target.closest("[data-queue-close-pdf-modal]");
    if (closeButton || event.target.classList.contains("pdf-modal-backdrop")) {
      closeQueuePdfModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && queueState.pdfModal.isOpen) {
      closeQueuePdfModal();
    }
  });
}

async function loadQueueData() {
  const localQueue = await fetchQueueFile(QUEUE_CONFIG.localQueueUrl);
  if (localQueue) {
    return {
      mode: "로컬 큐 검토 중",
      items: localQueue.map(normalizeQueueItem)
    };
  }

  const sampleQueue = await fetchQueueFile(QUEUE_CONFIG.sampleQueueUrl);
  if (sampleQueue) {
    return {
      mode: "샘플 큐 검토 중",
      items: sampleQueue.map(normalizeQueueItem)
    };
  }

  return {
    mode: "큐 데이터 없음",
    items: []
  };
}

async function fetchQueueFile(url) {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Failed to read ${url}`);
    const data = await response.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.items)) return data.items;
    return null;
  } catch (error) {
    return null;
  }
}

function normalizeQueueItem(item) {
  return {
    ...item,
    relativePath: item.relativePath || "",
    fileName: item.fileName || fileNameFromPath(item.relativePath) || "",
    status: item.status || "excel_missing_pdf",
    reviewDecision: QUEUE_CONFIG.decisions.includes(item.reviewDecision) ? item.reviewDecision : "미검토",
    suggestedAction: item.suggestedAction || "엑셀등록검토",
    tempProductName: item.tempProductName || "",
    supplier: item.supplier || "",
    category: item.category || "",
    note: item.note || "",
    matchedExcelCandidate: item.matchedExcelCandidate || "",
    duplicateCandidate: Boolean(item.duplicateCandidate),
    excludeReason: item.excludeReason || "",
    duplicateStatuses: Array.isArray(item.duplicateStatuses) ? item.duplicateStatuses : []
  };
}

function renderQueue() {
  queueElements.dataMode.textContent = `${queueState.dataMode}${queueState.dirty ? " / 수정됨" : ""}`;
  queueElements.dataMode.classList.toggle("is-local", queueState.dataMode.includes("로컬"));
  queueElements.dirtyNotice.classList.toggle("is-hidden", !queueState.dirty);
  renderQueueCounts();
  renderQueueList();
  renderQueueDetail();
  renderQueuePdfModal();
}

function renderQueueCounts() {
  const counts = getDecisionCounts();
  queueElements.counts.innerHTML = [
    ["전체", counts.total],
    ...QUEUE_CONFIG.decisions.map((decision) => [decision, counts[decision] || 0])
  ].map(([label, count]) => `
    <button class="review-count-pill queue-count-pill" type="button" data-queue-filter="${escapeAttribute(label === "전체" ? "all" : label)}">
      <strong>${escapeHtml(label)}</strong>
      <em>${count}</em>
    </button>
  `).join("");

  queueElements.counts.querySelectorAll("[data-queue-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      queueState.decisionFilter = button.dataset.queueFilter;
      queueElements.decisionFilter.value = queueState.decisionFilter;
      selectFirstVisibleQueueItem();
      renderQueue();
    });
  });
}

function getDecisionCounts() {
  return queueState.items.reduce((counts, item) => {
    counts.total += 1;
    counts[item.reviewDecision] = (counts[item.reviewDecision] || 0) + 1;
    return counts;
  }, { total: 0 });
}

function renderQueueList() {
  const filtered = getFilteredQueueItems();
  queueElements.listSummary.textContent = `표시 ${filtered.length}건 / 전체 ${queueState.items.length}건`;

  if (!queueState.items.length) {
    queueElements.list.innerHTML = `<div class="notice">검토할 PDF 등록 큐 데이터가 없습니다.</div>`;
    return;
  }

  if (!filtered.length) {
    queueElements.list.innerHTML = `<div class="notice">검색 또는 상태 필터에 맞는 항목이 없습니다.</div>`;
    return;
  }

  queueElements.list.innerHTML = filtered.map(({ item, index }) => {
    const key = getQueueKey(item, index);
    return `
      <button class="review-list-item pdf-queue-list-item ${key === queueState.selectedKey ? "is-selected" : ""}" type="button" data-queue-key="${escapeAttribute(key)}">
        <span class="review-status ${getDecisionClass(item.reviewDecision)}">${escapeHtml(item.reviewDecision)}</span>
        <strong class="text-break clamp-2">${escapeHtml(item.fileName || "파일명 없음")}</strong>
        <span class="text-muted-path clamp-3">${escapeHtml(item.relativePath || "상대경로 없음")}</span>
        <small class="text-muted-path clamp-2">${escapeHtml(item.suggestedAction || "")}${item.duplicateCandidate ? " · 중복 후보" : ""}${item.note ? ` · ${truncateText(item.note, 40)}` : ""}</small>
      </button>
    `;
  }).join("");

  queueElements.list.querySelectorAll("[data-queue-key]").forEach((button) => {
    button.addEventListener("click", () => {
      queueState.selectedKey = button.dataset.queueKey;
      renderQueue();
    });
  });
}

function renderQueueDetail() {
  const selected = getSelectedQueueEntry();
  if (!selected) {
    queueElements.detail.className = "review-detail empty-detail";
    queueElements.detail.innerHTML = `<p>선택된 PDF 큐 항목이 없습니다.</p>`;
    return;
  }

  const { item, index } = selected;
  const pdfInfo = buildQueuePdfInfo(item);
  queueElements.detail.className = "review-detail pdf-queue-detail";
  queueElements.detail.innerHTML = `
    <section class="review-detail-block">
      <div class="review-status-row">
        <label for="queueDecisionSelect">검토 결정</label>
        <select id="queueDecisionSelect" class="review-select">
          ${QUEUE_CONFIG.decisions.map((decision) => `
            <option value="${escapeAttribute(decision)}" ${decision === item.reviewDecision ? "selected" : ""}>${escapeHtml(decision)}</option>
          `).join("")}
        </select>
      </div>
      <div class="quick-status-buttons" aria-label="빠른 검토 결정 변경">
        ${quickDecisionButton("엑셀등록필요", item.reviewDecision)}
        ${quickDecisionButton("기존제품매핑필요", item.reviewDecision)}
        ${quickDecisionButton("중복의심", item.reviewDecision)}
        ${quickDecisionButton("제외", item.reviewDecision)}
        ${quickDecisionButton("보류", item.reviewDecision)}
        ${quickDecisionButton("미검토", item.reviewDecision, "미검토로 되돌리기")}
      </div>
      <div class="review-navigation-buttons" aria-label="검토 항목 이동">
        <button class="result-nav-button" type="button" data-queue-nav="previous">이전 항목</button>
        <button class="result-nav-button" type="button" data-queue-nav="next">다음 항목</button>
        <button class="result-nav-button" type="button" data-queue-nav="next-unreviewed">다음 미검토 항목</button>
      </div>
    </section>

    ${queueSection("기본 정보", `
      <div class="info-grid">
        ${queueItem("파일명", item.fileName)}
        ${queueItem("상대경로", item.relativePath)}
        ${queueItem("상태", item.status)}
        ${queueItem("검토 결정", item.reviewDecision)}
        ${queueItem("권장 작업", item.suggestedAction)}
        ${queueItem("중복 후보 여부", item.duplicateCandidate ? "예" : "아니오")}
      </div>
    `)}

    ${queueSection("검토 입력", renderQueueForm(item))}
    ${queueSection("원본 PDF 미리보기", renderQueuePdfPreview(pdfInfo))}
  `;

  queueElements.detail.querySelector("#queueDecisionSelect")?.addEventListener("change", (event) => {
    updateQueueItem(index, { reviewDecision: event.target.value });
  });

  queueElements.detail.querySelectorAll("[data-queue-decision]").forEach((button) => {
    button.addEventListener("click", () => updateQueueItem(index, { reviewDecision: button.dataset.queueDecision }));
  });

  queueElements.detail.querySelectorAll("[data-queue-field]").forEach((field) => {
    const eventName = field.type === "checkbox" ? "change" : "input";
    field.addEventListener(eventName, () => {
      updateQueueItem(index, {
        [field.dataset.queueField]: field.type === "checkbox" ? field.checked : field.value
      }, false);
    });
  });

  queueElements.detail.querySelectorAll("[data-queue-nav]").forEach((button) => {
    button.addEventListener("click", () => moveQueueSelection(button.dataset.queueNav));
  });
}

function renderQueueForm(item) {
  return `
    <div class="queue-edit-grid">
      ${textInput("suggestedAction", "권장 작업", item.suggestedAction)}
      ${textInput("tempProductName", "임시 제품명", item.tempProductName)}
      ${textInput("supplier", "공급업체", item.supplier)}
      ${textInput("category", "분류", item.category)}
      ${textInput("matchedExcelCandidate", "매칭 후보", item.matchedExcelCandidate)}
      ${textInput("excludeReason", "제외 사유", item.excludeReason)}
      <label class="queue-checkbox">
        <input type="checkbox" data-queue-field="duplicateCandidate" ${item.duplicateCandidate ? "checked" : ""}>
        중복 후보로 표시
      </label>
      <label class="queue-textarea-label">
        <span>메모</span>
        <textarea data-queue-field="note" rows="4">${escapeHtml(item.note)}</textarea>
      </label>
    </div>
  `;
}

function textInput(field, label, value) {
  return `
    <label class="queue-input-label">
      <span>${escapeHtml(label)}</span>
      <input type="text" data-queue-field="${escapeAttribute(field)}" value="${escapeAttribute(value || "")}">
    </label>
  `;
}

function quickDecisionButton(decision, currentDecision, label = decision) {
  return `
    <button class="quick-status-button ${decision === currentDecision ? "is-active" : ""}" type="button" data-queue-decision="${escapeAttribute(decision)}">
      ${escapeHtml(label)}
    </button>
  `;
}

function updateQueueItem(index, changes, rerender = true) {
  queueState.items[index] = {
    ...queueState.items[index],
    ...changes
  };
  queueState.dirty = true;
  if (changes.reviewDecision && !getFilteredQueueItems().some((entry) => getQueueKey(entry.item, entry.index) === queueState.selectedKey)) {
    selectFirstVisibleQueueItem();
  }
  if (rerender) renderQueue();
  else {
    queueElements.dataMode.textContent = `${queueState.dataMode} / 수정됨`;
    queueElements.dirtyNotice.classList.remove("is-hidden");
    renderQueueCounts();
    renderQueueList();
  }
}

function moveQueueSelection(action) {
  const filtered = getFilteredQueueItems();
  if (!filtered.length) return;
  const currentIndex = filtered.findIndex((entry) => getQueueKey(entry.item, entry.index) === queueState.selectedKey);

  if (action === "previous") {
    const nextIndex = currentIndex <= 0 ? filtered.length - 1 : currentIndex - 1;
    queueState.selectedKey = getQueueKey(filtered[nextIndex].item, filtered[nextIndex].index);
    renderQueue();
    return;
  }

  if (action === "next") {
    const nextIndex = currentIndex < 0 || currentIndex >= filtered.length - 1 ? 0 : currentIndex + 1;
    queueState.selectedKey = getQueueKey(filtered[nextIndex].item, filtered[nextIndex].index);
    renderQueue();
    return;
  }

  if (action === "next-unreviewed") {
    const allEntries = queueState.items.map((item, index) => ({ item, index }));
    const selected = getSelectedQueueEntry();
    const start = selected ? selected.index + 1 : 0;
    const ordered = [...allEntries.slice(start), ...allEntries.slice(0, start)];
    const nextUnreviewed = ordered.find((entry) => entry.item.reviewDecision === "미검토");
    if (nextUnreviewed) {
      queueState.selectedKey = getQueueKey(nextUnreviewed.item, nextUnreviewed.index);
      queueState.decisionFilter = "all";
      queueElements.decisionFilter.value = "all";
      renderQueue();
    }
  }
}

function getFilteredQueueItems() {
  const query = normalizeText(queueState.query);
  return queueState.items
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => {
      const decisionMatch = queueState.decisionFilter === "all" || item.reviewDecision === queueState.decisionFilter;
      if (!decisionMatch) return false;
      if (!query) return true;
      return normalizeText(buildQueueSearchSource(item)).includes(query);
    });
}

function buildQueueSearchSource(item) {
  return [
    item.fileName,
    item.relativePath,
    item.tempProductName,
    item.supplier,
    item.category,
    item.note,
    item.matchedExcelCandidate,
    item.suggestedAction,
    item.excludeReason
  ].join(" ");
}

function selectFirstVisibleQueueItem() {
  const first = getFilteredQueueItems()[0];
  queueState.selectedKey = first ? getQueueKey(first.item, first.index) : "";
}

function getSelectedQueueEntry() {
  return queueState.items
    .map((item, index) => ({ item, index }))
    .find(({ item, index }) => getQueueKey(item, index) === queueState.selectedKey)
    || getFilteredQueueItems()[0]
    || null;
}

function getQueueKey(item, index) {
  if (!item) return "";
  return `${item.relativePath || item.fileName || "queue"}__${index}`;
}

function getDecisionClass(decision) {
  if (decision === "엑셀등록필요") return "is-reviewed";
  if (decision === "기존제품매핑필요") return "is-mapped";
  if (decision === "중복의심") return "is-edit-needed";
  if (decision === "제외") return "is-excluded";
  if (decision === "보류") return "is-hold";
  return "is-review-needed";
}

function queueSection(title, content) {
  return `
    <section class="review-detail-block">
      <h3>${escapeHtml(title)}</h3>
      ${content}
    </section>
  `;
}

function queueItem(label, value) {
  return `
    <div class="info-item">
      <span class="info-label">${escapeHtml(label)}</span>
      <span class="info-value">${escapeHtml(value || "정보 없음")}</span>
    </div>
  `;
}

function buildQueuePdfInfo(item) {
  const relativePath = String(item.relativePath || "").trim();
  const displayPath = relativePath ? `/pdf/${relativePath.replace(/^\/?pdf\//, "")}` : "";
  if (!displayPath) {
    return {
      status: "no-path",
      displayPath: "",
      encodedPath: "",
      title: item.fileName || "PDF 미리보기"
    };
  }
  const encodedPath = encodePdfPath(displayPath);
  return {
    status: queueState.pdfAvailability[encodedPath] || "unchecked",
    displayPath,
    encodedPath,
    title: item.fileName || relativePath
  };
}

function renderQueuePdfPreview(pdfInfo) {
  if (pdfInfo.status === "no-path") {
    return `
      <div class="pdf-preview is-missing">
        <p class="pdf-message">PDF 상대경로 정보가 없어 미리보기가 어렵습니다.</p>
        <div class="pdf-frame-placeholder">relativePath 확인 필요</div>
      </div>
    `;
  }

  if (pdfInfo.status === "unchecked") {
    scheduleQueuePdfAvailabilityCheck(pdfInfo.encodedPath);
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
          <button class="pdf-enlarge-button" type="button" data-queue-open-pdf-modal data-pdf-title="${escapeAttribute(pdfInfo.title)}" data-pdf-path="${escapeAttribute(pdfInfo.encodedPath)}">크게 보기</button>
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
      <p class="pdf-message">PDF 파일을 찾지 못했습니다.</p>
      <div class="info-item">
        <span class="info-label">예상 경로</span>
        <span class="info-value">${escapeHtml(pdfInfo.displayPath)}</span>
      </div>
      <div class="pdf-frame-placeholder">PDF 경로 또는 파일 배치 상태를 확인하세요.</div>
    </div>
  `;
}

function scheduleQueuePdfAvailabilityCheck(path) {
  queueState.pdfAvailability[path] = "checking";
  checkQueuePdfExists(path).then((exists) => {
    queueState.pdfAvailability[path] = exists ? "available" : "missing";
    const selected = getSelectedQueueEntry();
    if (selected && buildQueuePdfInfo(selected.item).encodedPath === path) renderQueue();
  });
}

async function checkQueuePdfExists(path) {
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

function openQueuePdfModal(title, path) {
  if (!path) return;
  queueState.pdfModal = {
    isOpen: true,
    title: title || "PDF 미리보기",
    path
  };
  renderQueuePdfModal();
}

function closeQueuePdfModal() {
  queueState.pdfModal = {
    isOpen: false,
    title: "",
    path: ""
  };
  renderQueuePdfModal();
}

function ensureQueuePdfModalElement() {
  let modal = document.querySelector("#queuePdfPreviewModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "queuePdfPreviewModal";
    document.body.appendChild(modal);
  }
  return modal;
}

function renderQueuePdfModal() {
  const modal = ensureQueuePdfModalElement();
  document.body.classList.toggle("modal-open", queueState.pdfModal.isOpen);

  if (!queueState.pdfModal.isOpen) {
    modal.className = "pdf-modal is-hidden";
    modal.innerHTML = "";
    return;
  }

  modal.className = "pdf-modal";
  modal.innerHTML = `
    <div class="pdf-modal-backdrop">
      <section class="pdf-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="queuePdfModalTitle">
        <header class="pdf-modal-toolbar">
          <div>
            <h2 id="queuePdfModalTitle">PDF 미리보기</h2>
            <p>${escapeHtml(queueState.pdfModal.title)}</p>
          </div>
          <button class="pdf-modal-close" type="button" data-queue-close-pdf-modal aria-label="PDF 크게 보기 닫기">닫기</button>
        </header>
        <iframe class="pdf-modal-frame" title="${escapeAttribute(queueState.pdfModal.title)} PDF 크게 보기" src="${escapeAttribute(queueState.pdfModal.path)}"></iframe>
      </section>
    </div>
  `;
  modal.querySelector("[data-queue-close-pdf-modal]")?.focus();
}

function downloadQueueJson() {
  const content = JSON.stringify(queueState.items, null, 2);
  const blob = new Blob([content], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = QUEUE_CONFIG.downloadFileName;
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
    .replace(/[\s()[\]{}<>_\-\/\\]/g, "");
}

function fileNameFromPath(value) {
  const text = String(value || "");
  return text.split("/").filter(Boolean).pop() || "";
}

function truncateText(value, length) {
  const text = String(value || "");
  return text.length > length ? `${text.slice(0, length)}...` : text;
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
