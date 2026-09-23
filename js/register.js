/* MSDS 번호 관리대장.
 *
 * 2026-09-23 전수조사에서 제품마다 MSDS 번호가 있어야 하는지, 없어도 되는지,
 * 무엇을 더 받아야 하는지를 정했다. 그 결과를 data/msds-register.json 에
 * 두고, 이 화면은 그것을 표로 보여 준다.
 *
 * 번호가 비었다고 다 누락은 아니다. 원문이 분류기준 비해당이라고 적은 제품,
 * 다른 법률로 관리되는 제품, 시험용 시약은 번호가 없어도 된다. 반대로 번호가
 * 있다고 다 의무 대상인 것도 아니다. 그래서 번호 칸만 보지 않고 상태·까닭·
 * 법적 근거를 같이 둔다.
 *
 * 이 화면은 보기만 한다. 서버가 없는 사이트라 여기서 고쳐 저장할 수는 없다.
 * 고치는 곳은 관리대장 파일 하나다.
 */

const REGISTER_SOURCE = "data/msds-register.json";
const REGISTER_PRODUCTS = "data/msds.public.json";

const STATUS_ORDER = ["required", "pending", "not_required", "submission_exempt", "verified", "retired"];
const STATUS_HINT = {
  required: "번호가 있어야 하는데 가진 MSDS 에 없음. 공급사에서 번호가 적힌 최신본을 받아야 함",
  pending: "원문만으로 판단할 수 없음. 라벨·용도·수입자 자료 등을 더 확인해야 함",
  not_required: "법적으로 번호가 필요 없음. 까닭과 근거가 있음",
  submission_exempt: "MSDS 는 게시·비치해야 하지만 공단 제출(번호)만 면제되는 시험용 시약",
  verified: "사이트 번호가 원본 PDF 번호와 같음",
  retired: "구판·중복이라 목록에서 뺌. 새 판으로 이어짐"
};

const registerState = {
  data: null,
  rows: [],
  status: "",
  query: ""
};

const registerElements = {};

function rEscape(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function rNormalize(value) {
  return String(value || "").toLowerCase().replace(/[\s()[\]{}_\-/\\]/g, "");
}

async function rFetch(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

function buildRows(register, products) {
  const live = new Map((Array.isArray(products) ? products : products.products || []).map((p) => [p.id, p]));
  const labels = register.statusLabels || {};
  const legal = register.legalBasis || {};
  return Object.entries(register.products || {}).map(([id, entry]) => {
    const product = live.get(id);
    const replacement = entry.replacedBy ? live.get(entry.replacedBy) : null;
    return {
      id,
      entry,
      product,
      name: entry.productName || product?.productName || id,
      supplier: entry.supplier || product?.supplier || "",
      number: entry.msdsNo || "",
      asWritten: entry.msdsNoAsWritten || "",
      docNo: entry.supplierDocNo || "",
      status: entry.status || "pending",
      statusLabel: labels[entry.status] || entry.status || "",
      kind: entry.kind || "",
      reason: entry.reason || "",
      basis: (entry.basis || []).map((key) => legal[key] || key),
      need: entry.need || "",
      action: entry.action || "",
      certainty: entry.certainty || "",
      checkedOn: entry.checkedOn || "",
      signalWord: entry.signalWord || "",
      replacement,
      pdf: product?.pdfPath || "",
      haystack: rNormalize([entry.productName, entry.supplier, entry.msdsNo, entry.supplierDocNo, entry.kind].join(" "))
    };
  }).sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
    || a.supplier.localeCompare(b.supplier, "ko") || a.name.localeCompare(b.name, "ko"));
}

function visibleRows() {
  const needle = rNormalize(registerState.query);
  return registerState.rows.filter((row) => {
    if (registerState.status && row.status !== registerState.status) return false;
    if (needle && !row.haystack.includes(needle)) return false;
    return true;
  });
}

function renderTiles() {
  const counts = {};
  registerState.rows.forEach((row) => { counts[row.status] = (counts[row.status] || 0) + 1; });
  const labels = registerState.data.statusLabels || {};
  const total = registerState.rows.length;
  registerElements.tiles.innerHTML = STATUS_ORDER.map((status) => `
    <button type="button" class="register-tile is-${status}${registerState.status === status ? " is-on" : ""}"
      data-register-status="${status}" title="${rEscape(STATUS_HINT[status])}">
      <strong>${counts[status] || 0}</strong>
      <span>${rEscape(labels[status] || status)}</span>
    </button>`).join("") + `
    <button type="button" class="register-tile is-all${registerState.status ? "" : " is-on"}" data-register-status="">
      <strong>${total}</strong><span>전체</span>
    </button>`;
}

function numberCell(row) {
  if (row.number) {
    return `<code>${rEscape(row.number)}</code>${row.status === "pending" ? '<span class="register-sub">원본 대조 중</span>' : ""}`;
  }
  if (row.asWritten) return `<span class="register-sub">원문 표기</span><code>${rEscape(row.asWritten)}</code>`;
  return '<span class="register-sub">없음</span>';
}

function nameCell(row) {
  const doc = row.docNo ? `<span class="register-sub">공급사 문서번호 ${rEscape(row.docNo)}</span>` : "";
  if (row.status === "retired") {
    const next = row.replacement
      ? `<a href="index.html?product=${encodeURIComponent(row.replacement.id)}">→ ${rEscape(row.replacement.productName)}</a>`
      : "";
    return `<span class="register-retired">${rEscape(row.name)}</span>${next ? `<span class="register-sub">${next}</span>` : ""}${doc}`;
  }
  return `<a href="index.html?product=${encodeURIComponent(row.id)}&q=${encodeURIComponent(row.name)}">${rEscape(row.name)}</a>${doc}`;
}

function renderTable() {
  const rows = visibleRows();
  registerElements.count.textContent = rows.length === registerState.rows.length
    ? `${rows.length}건 모두`
    : `${registerState.rows.length}건 가운데 ${rows.length}건`;
  registerElements.body.innerHTML = rows.map((row) => `
    <tr class="is-${row.status}">
      <td class="register-name">${nameCell(row)}</td>
      <td>${rEscape(row.supplier)}</td>
      <td class="register-number">${numberCell(row)}</td>
      <td><span class="register-status is-${row.status}">${rEscape(row.statusLabel)}</span>
        ${row.kind ? `<span class="register-sub">${rEscape(row.kind)}</span>` : ""}
        ${row.certainty ? `<span class="register-sub">자료 충분도 ${rEscape(row.certainty)}</span>` : ""}</td>
      <td class="register-long">${rEscape(row.reason)}</td>
      <td class="register-long">${row.basis.map((b) => `<span class="register-basis">${rEscape(b)}</span>`).join("")}</td>
      <td class="register-long">${rEscape(row.need)}</td>
      <td class="register-long">${rEscape(row.action)}</td>
      <td class="register-date">${rEscape(row.checkedOn)}</td>
    </tr>`).join("") || '<tr><td colspan="9" class="register-empty">걸리는 제품이 없습니다.</td></tr>';
}

/* 할 일을 공급사별로 묶는다. 전화 한 통, 메일 한 통에 여러 제품을 같이
 * 물어볼 수 있게. */
function renderTodo() {
  const groups = new Map();
  registerState.rows
    .filter((row) => row.status === "required" || row.status === "pending")
    .forEach((row) => {
      const key = row.supplier || "공급사 불명";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    });
  const ordered = [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], "ko"));
  registerElements.todo.innerHTML = ordered.map(([supplier, rows]) => {
    const needs = [...new Set(rows.map((row) => row.need).filter(Boolean))];
    return `
      <details class="register-todo-item">
        <summary><strong>${rEscape(supplier)}</strong><span>${rows.length}건</span>
          <span class="register-todo-kinds">${[...new Set(rows.map((r) => r.statusLabel))].map(rEscape).join(" · ")}</span></summary>
        <ul>${rows.map((row) => `<li>${rEscape(row.name)} <span class="register-sub">${rEscape(row.kind || row.statusLabel)}</span></li>`).join("")}</ul>
        ${needs.length ? `<p class="register-todo-need"><b>받을 것</b> ${needs.map(rEscape).join(" / ")}</p>` : ""}
      </details>`;
  }).join("") || '<p class="register-empty">남은 할 일이 없습니다.</p>';
}

function renderLegal() {
  const legal = registerState.data.legalBasis || {};
  registerElements.legal.innerHTML = `
    <p class="register-sub">${rEscape(registerState.data.legalVersions || "")}</p>
    <ul>${Object.values(legal).map((text) => `<li>${rEscape(text)}</li>`).join("")}</ul>`;
}

function render() {
  renderTiles();
  renderTable();
}

function exportRegisterCsv() {
  const header = ["제품명", "공급사", "MSDS 번호", "원문 표기", "공급사 문서번호", "상태", "분류", "사유",
    "법적 근거", "추가 필요자료", "조치안", "자료 충분도", "신호어(원문)", "확인일", "대체 제품", "id"];
  const rows = visibleRows().map((row) => [
    row.name, row.supplier, row.number, row.asWritten, row.docNo, row.statusLabel, row.kind, row.reason,
    row.basis.join(" / "), row.need, row.action, row.certainty, row.signalWord, row.checkedOn,
    row.replacement?.productName || "", row.id
  ]);
  window.downloadCsv(`MSDS번호관리대장_${window.csvStamp()}.csv`, header, rows);
}

async function initRegisterPage() {
  registerElements.tiles = document.querySelector("#registerTiles");
  registerElements.body = document.querySelector("#registerBody");
  registerElements.count = document.querySelector("#registerCount");
  registerElements.search = document.querySelector("#registerSearch");
  registerElements.todo = document.querySelector("#registerTodo");
  registerElements.legal = document.querySelector("#registerLegal");
  registerElements.checked = document.querySelector("#registerChecked");

  const [register, products] = await Promise.all([rFetch(REGISTER_SOURCE), rFetch(REGISTER_PRODUCTS)]);
  registerState.data = register;
  registerState.rows = buildRows(register, products);

  const dates = registerState.rows.map((row) => row.checkedOn).filter(Boolean).sort();
  registerElements.checked.textContent = dates.length ? `마지막 확인 ${dates[dates.length - 1]}` : "";

  registerElements.tiles.addEventListener("click", (event) => {
    const tile = event.target.closest("[data-register-status]");
    if (!tile) return;
    registerState.status = tile.dataset.registerStatus;
    render();
  });
  registerElements.search.addEventListener("input", (event) => {
    registerState.query = event.target.value;
    renderTable();
  });
  document.querySelector("#registerExport").addEventListener("click", exportRegisterCsv);

  render();
  renderTodo();
  renderLegal();
}

/* 물질 화면과 같이 관리자 모드에서만 연다. 감춘 채로 데이터를 읽지 않는다. */
let registerStarted = false;
function startRegisterPage() {
  if (registerStarted || document.documentElement.getAttribute("data-admin") !== "on") return;
  registerStarted = true;
  initRegisterPage().catch((error) => {
    console.error(error);
    const count = document.querySelector("#registerCount");
    if (count) count.textContent = "관리대장을 불러오지 못했습니다.";
  });
}

document.addEventListener("DOMContentLoaded", startRegisterPage);
document.addEventListener("msds:admin-changed", (event) => {
  if (event.detail?.on) startRegisterPage();
});
