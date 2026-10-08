// 실제 브라우저로 화면을 눌러 보는 점검. 따로 설치할 것이 없다(Node 22 + Chrome).
//
//   node tests/browser/smoke.mjs
//
// 계약 테스트(파이썬)는 파일 글자만 본다. 화면이 겹치거나, 눌렀는데 안 되거나,
// 폰에서 옆으로 밀리는 것은 브라우저로 열어 봐야 안다. 여기서는 헤드리스 Chrome 을
// DevTools 프로토콜로 직접 움직인다(Playwright 같은 꾸러미 없이).
//
// 보는 것: 검색→제품 선택, 요약판(그림문자·보호구), 응급조치 원문 확인 표시,
// 탭이 고른 제품을 이어받는지, PDF 미리보기·쪽 이동·원문 찾기, 폰 폭에서 옆으로
// 밀림, 어두운 화면, 큰 글자, 경고표지·관리요령 인쇄 단추, 오프라인 저장 칸.
//
// CHROME 환경변수로 Chrome 위치를 줄 수 있다. 없으면 흔한 자리를 찾아본다.

import { spawn } from "node:child_process";
import { createReadStream, existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
  ".css": "text/css", ".json": "application/json", ".pdf": "application/pdf", ".svg": "image/svg+xml",
  ".png": "image/png", ".webmanifest": "application/manifest+json", ".txt": "text/plain" };

function findChrome() {
  const candidates = [
    process.env.CHROME,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  ].filter(Boolean);
  const found = candidates.find((path) => existsSync(path));
  if (!found) throw new Error("Chrome 을 못 찾았다. CHROME 환경변수에 위치를 주세요.");
  return found;
}

// 이 저장소를 그대로 내보내는 작은 서버. 캐시를 쓰지 않는다.
function startServer() {
  const server = createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    let path = normalize(join(ROOT, decodeURIComponent(url.pathname)));
    if (!path.startsWith(ROOT)) { res.writeHead(403).end(); return; }
    if (existsSync(path) && statSync(path).isDirectory()) path = join(path, "index.html");
    if (!existsSync(path)) { res.writeHead(404).end(); return; }
    res.writeHead(200, { "Content-Type": TYPES[extname(path)] || "application/octet-stream", "Cache-Control": "no-store" });
    createReadStream(path).pipe(res);
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

const sleep = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function launchChrome() {
  const profile = mkdtempSync(join(tmpdir(), "msds-smoke-"));
  const port = 9300 + Math.floor(Math.random() * 500);
  const proc = spawn(findChrome(), [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"
  ], { stdio: "ignore" });
  for (let i = 0; i < 50; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return { proc, port, profile };
    } catch (error) { /* 아직 안 떴다 */ }
    await sleep(200);
  }
  throw new Error("Chrome 이 뜨지 않았다.");
}

class Page {
  static async open(port) {
    const res = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
    const { webSocketDebuggerUrl } = await res.json();
    const page = new Page(new WebSocket(webSocketDebuggerUrl));
    await new Promise((ok, fail) => { page.ws.onopen = ok; page.ws.onerror = fail; });
    await page.send("Page.enable");
    await page.send("Runtime.enable");
    return page;
  }

  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.waiting = new Map();
    this.errors = [];
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.waiting.has(msg.id)) {
        const { ok, fail } = this.waiting.get(msg.id);
        this.waiting.delete(msg.id);
        msg.error ? fail(new Error(msg.error.message)) : ok(msg.result);
      } else if (msg.method === "Runtime.exceptionThrown") {
        this.errors.push(msg.params.exceptionDetails?.exception?.description || msg.params.exceptionDetails?.text);
      } else if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
        this.errors.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
      }
    };
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((ok, fail) => this.waiting.set(id, { ok, fail }));
  }

  async size(width, height, mobile = false) {
    await this.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile });
  }

  async scheme(dark) {
    await this.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: dark ? "dark" : "light" }] });
  }

  async go(url) {
    await this.send("Page.navigate", { url });
    await sleep(400);
    await this.until("document.readyState === 'complete'");
  }

  async eval(expression) {
    const { result, exceptionDetails } = await this.send("Runtime.evaluate", {
      expression: `(async () => { ${expression} })()`, awaitPromise: true, returnByValue: true
    });
    if (exceptionDetails) throw new Error(exceptionDetails.exception?.description || exceptionDetails.text);
    return result.value;
  }

  async until(condition, timeout = 15000) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      if (await this.eval(`return Boolean(${condition});`)) return;
      await sleep(150);
    }
    throw new Error(`기다렸지만 안 됨: ${condition}`);
  }
}

const results = [];
async function check(name, run) {
  try {
    await run();
    results.push({ name, ok: true });
    console.log(`  ok   ${name}`);
  } catch (error) {
    results.push({ name, ok: false, error: error.message });
    console.log(`  FAIL ${name}\n       ${error.message}`);
  }
}

function expect(value, message) {
  if (!value) throw new Error(message);
}

const server = await startServer();
const BASE = `http://127.0.0.1:${server.address().port}`;
// 로컬 PC 에는 공개되지 않는 로컬 자료가 있다. 공개 자료로 맞춰 본다.
const INDEX = `${BASE}/index.html?dataMode=public`;
const chrome = await launchChrome();
const page = await Page.open(chrome.port);

try {
  console.log(`MSDS 화면 점검 (${BASE})`);
  await page.scheme(false);
  await page.size(1280, 900);

  await check("검색해서 제품을 고르면 후보를 접고 요약판을 보인다", async () => {
    await page.go(INDEX);
    await page.until("document.querySelectorAll('.quick-search button').length > 0");
    await page.eval(`document.querySelector('#searchInput').value = 'TC-317';
      document.querySelector('#searchInput').dispatchEvent(new Event('input', { bubbles: true }));`);
    await page.until("document.querySelector('.selection-item')");
    await page.eval("document.querySelector('.selection-item').click();");
    await page.until("document.querySelector('.selection-collapsed-card')");
    const title = await page.eval("return document.querySelector('.poster-product-title h2')?.textContent || '';");
    expect(title.includes("TC-317"), `요약판 제목: ${title}`);
  });

  await check("TC-317 요약판: 그림문자 3개, 보호구 4개(보호장갑 포함)", async () => {
    const ghs = await page.eval("return document.querySelectorAll('.poster-ghs-row .ghs-item').length;");
    const ppe = await page.eval("return [...document.querySelectorAll('.ppe-card .ppe-name')].map((e) => e.textContent);");
    expect(ghs === 3, `그림문자 ${ghs}개`);
    expect(ppe.length === 4 && ppe.includes("보호장갑"), `보호구 ${ppe.join(",")}`);
  });

  await check("응급조치(삼켰을 때)에 원문 확인 중 표시", async () => {
    const note = await page.eval("return document.querySelector('.first-aid-conflict')?.textContent || '';");
    expect(note.includes("P331") && note.includes("공급사"), `표시: ${note.slice(0, 60)}`);
  });

  await check("경고표지·관리요령 탭이 고른 제품을 이어받는다", async () => {
    const tabs = await page.eval("return [...document.querySelectorAll('.top-bar-tab')].map((a) => a.getAttribute('href'));");
    expect(tabs.includes("label.html?product=msds-033") && tabs.includes("guide.html?product=msds-033"), tabs.join(" "));
  });

  await check("PDF 미리보기: 열기·쪽 번호로 이동·원문에서 찾기", async () => {
    await page.eval("document.querySelector('.detail-block-pdf [data-preview-pdf]').click();");
    await page.until("document.querySelector('.detail-block-pdf canvas')", 30000);
    await page.eval(`const input = document.querySelector('.detail-block-pdf [data-pdf-page-input]');
      input.value = '3'; input.dispatchEvent(new Event('change', { bubbles: true }));`);
    await page.until("document.querySelector('.detail-block-pdf .pdf-js-page-label')?.textContent.startsWith('3 /')");
    await page.eval(`const form = document.querySelector('.detail-block-pdf [data-pdf-search-form]');
      form.querySelector('input').value = '법적규제'; form.requestSubmit();`);
    await page.until("/쪽 ·/.test(document.querySelector('.detail-block-pdf [data-pdf-search-status]')?.textContent || '')", 30000);
    // 찾은 말이 원문 글자층에서 칠해진다(고르기·복사도 이 층으로 된다).
    await page.until("document.querySelectorAll('.detail-block-pdf .textLayer .highlight').length > 0", 15000);
  });

  await check("어두운 화면으로 바꾸기", async () => {
    await page.eval("document.querySelector('.theme-toggle').click();");
    await page.until("document.documentElement.dataset.theme === 'dark'");
    await page.eval("document.querySelector('.theme-toggle').click();");
    await page.until("document.documentElement.dataset.theme === 'light'");
  });

  await page.size(390, 844, true);
  await check("폰 폭(390px): 옆으로 밀리지 않고 머리글이 짧다", async () => {
    await page.go(`${INDEX}&product=msds-033`);
    await page.until("document.querySelector('.poster-product-title h2')");
    const wide = await page.eval(`return [...document.querySelectorAll('body *')]
      .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1 && getComputedStyle(el).position !== 'fixed'
        && !el.closest('.component-table-wrap, .pdf-js-page-stage, .selection-scroll'))
      .slice(0, 3).map((el) => el.className || el.tagName);`);
    expect(wide.length === 0, `화면 밖으로 나간 것: ${wide.join(", ")}`);
    const header = await page.eval("return document.querySelector('.site-header').getBoundingClientRect().height;");
    expect(header < 150, `머리글 높이 ${header}px`);
  });

  await check("폰에서 아래 바로가기로 응급조치에 바로 간다", async () => {
    await page.eval("window.scrollTo(0, 600);");
    await page.until("document.querySelector('#scrollQuickNav [data-scroll-target=\"firstAid\"]')");
    await page.eval("document.querySelector('#scrollQuickNav [data-scroll-target=\"firstAid\"]').click();");
    await page.until("Math.abs(document.querySelector('.detail-block-first-aid').getBoundingClientRect().top) < 160", 5000);
  });

  await check("큰 글자 보기를 켜면 본문 글자가 커지고 저장된다", async () => {
    const before = await page.eval("return parseFloat(getComputedStyle(document.documentElement).fontSize);");
    await page.eval("document.querySelector('[data-text-size-toggle]').click();");
    await page.until("document.documentElement.dataset.textSize === 'large'");
    const after = await page.eval("return parseFloat(getComputedStyle(document.documentElement).fontSize);");
    expect(after > before, `글자 ${before} → ${after}`);
    await page.go(`${INDEX}&product=msds-033`);
    await page.until("document.documentElement.dataset.textSize === 'large'");
    await page.eval("document.querySelector('[data-text-size-toggle]').click();");
  });

  await page.size(1280, 900);
  await check("관리요령: 고른 것이 있을 때만 '고른 … 인쇄'가 눌린다", async () => {
    await page.go(`${BASE}/guide.html?product=msds-033`);
    await page.until("document.querySelector('#guidePrint') && !document.querySelector('#guidePrint').disabled");
    await page.eval("document.querySelector('#guideClear').click();");
    await page.until("document.querySelector('#guidePrint').disabled");
    const all = await page.eval("return document.querySelector('#guidePrintAll').textContent;");
    expect(/보이는 전체 \d+건 인쇄/.test(all), all);
  });

  await check("경고표지: 처음에는 '고른 표지 인쇄'를 누를 수 없다", async () => {
    await page.go(`${BASE}/label.html`);
    await page.until("document.querySelector('#labelStatus')?.textContent.includes('건')");
    expect(await page.eval("return document.querySelector('#labelPrint').disabled;"), "눌린다");
  });

  await check("오프라인 저장 칸에 지금 자료판이 보인다", async () => {
    await page.go(`${INDEX}&offline=1`);
    await page.until("(document.querySelector('#offlinePanel')?.textContent || '').includes('지금 자료판')");
  });

  await check("화면 오류(스크립트 예외) 없음", async () => {
    const errors = page.errors.filter((text) => text && !/favicon|Failed to load resource|ServiceWorker|Transition was skipped/i.test(text));
    expect(errors.length === 0, errors.slice(0, 3).join(" | "));
  });
} finally {
  page.ws.close();
  chrome.proc.kill();
  server.close();
  await sleep(300);
  try { rmSync(chrome.profile, { recursive: true, force: true }); } catch (error) { /* 아직 쥐고 있으면 둔다 */ }
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} 통과`);
process.exit(failed.length ? 1 : 0);
