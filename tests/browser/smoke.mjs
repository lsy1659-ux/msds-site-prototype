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
import { createReadStream, existsSync, mkdirSync, mkdtempSync, rmSync, statSync, writeFileSync } from "node:fs";
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
  // GitHub 러너에서 첫 실행이 10초를 넘긴 적이 있다(2026-10-08). 30초까지 기다린다.
  for (let i = 0; i < 150; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return { proc, port, profile };
    } catch (error) { /* 아직 안 떴다 */ }
    await sleep(200);
  }
  throw new Error("Chrome 이 30초 안에 뜨지 않았다.");
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
// 배포 후에는 같은 회귀 경로를 실제 공개 주소에서 읽기 전용으로 확인할 수 있다.
const BASE = (process.env.MSDS_SMOKE_BASE || `http://127.0.0.1:${server.address().port}`).replace(/\/$/, "");
// 로컬 PC 에는 공개되지 않는 로컬 자료가 있다. 공개 자료로 맞춰 본다.
const INDEX = `${BASE}/index.html?dataMode=public`;
const chrome = await launchChrome();
const page = await Page.open(chrome.port);
const ARTIFACTS = process.env.MSDS_SMOKE_ARTIFACTS;
if (ARTIFACTS) mkdirSync(ARTIFACTS, { recursive: true });
async function screenshot(name) {
  if (!ARTIFACTS) return;
  // 화면 진입 애니메이션과 부드러운 스크롤이 끝난 모습을 기록한다.
  await sleep(1200);
  const { data } = await page.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(ARTIFACTS, `${name}.png`), Buffer.from(data, "base64"));
}

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
    await screenshot("desktop-summary");
  });

  await check("TC-317 요약판: 그림문자 3개, 보호구 4개(보호장갑 포함)", async () => {
    const ghs = await page.eval("return document.querySelectorAll('.poster-ghs-row .ghs-item').length;");
    const ppe = await page.eval("return [...document.querySelectorAll('.ppe-card .ppe-name')].map((e) => e.textContent);");
    expect(ghs === 3, `그림문자 ${ghs}개`);
    expect(ppe.length === 4 && ppe.includes("보호장갑"), `보호구 ${ppe.join(",")}`);
  });

  await check("응급조치(삼켰을 때) 옆에 같은 MSDS 의 대응 문구(P331)", async () => {
    const note = await page.eval("return document.querySelector('.first-aid-related')?.textContent || '';");
    expect(note.includes("P331"), `표시: ${note.slice(0, 60)}`);
  });

  // 공식 사이트다. 외부 사람이 보면 자료를 의심하게 되는 말은 화면에 없어야 한다.
  const UNEASY = ["확인 필요", "확인 권장", "확인 중", "미확인", "검토 필요", "검토필요", "공급사", "참고용",
    "자동 추출", "맞지 않", "년 경과", "원문 확인", "반드시 확인"];
  const uneasyOn = async () => page.eval(`const text = document.body.innerText;
    return ${JSON.stringify(UNEASY)}.filter((word) => text.includes(word));`);
  await check("조회 화면에 불안한 말이 없다", async () => {
    const found = await uneasyOn();
    expect(found.length === 0, found.join(", "));
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
    await screenshot("mobile-first-aid");
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
    await page.go(`${BASE}/guide.html?dataMode=public&product=msds-033`);
    await page.until("document.querySelector('#guidePrint') && !document.querySelector('#guidePrint').disabled");
    await page.eval("document.querySelector('#guideClear').click();");
    await page.until("document.querySelector('#guidePrint').disabled");
    const all = await page.eval("return document.querySelector('#guidePrintAll').textContent;");
    expect(/보이는 전체 \d+건 인쇄/.test(all), all);
  });

  await check("관리요령 화면·인쇄 면에 불안한 말이 없다", async () => {
    await page.go(`${BASE}/guide.html?dataMode=public&product=msds-033`);
    await page.until("document.querySelector('.guide-card')");
    const found = await uneasyOn();
    expect(found.length === 0, found.join(", "));
  });

  await check("경고표지: 2차이형제(S6)는 원문대로 그림문자 2개(인화성·건강유해성)", async () => {
    await page.go(`${BASE}/label.html?dataMode=public&product=msds-077`);
    await page.until("document.querySelector('[data-label-id=\"msds-077\"] .label-pictograms')");
    const pics = await page.eval("return [...document.querySelectorAll('[data-label-id=\"msds-077\"] .label-pictogram figcaption')].map((e) => e.textContent);");
    expect(pics.length === 2 && pics.includes("인화성") && pics.includes("건강유해성"), pics.join(","));
  });

  await check("경고표지: 백양퐁은 원문대로 느낌표 1개와 유해·위험문구(코드 없는 문장)", async () => {
    await page.go(`${BASE}/label.html?dataMode=public&product=msds-155`);
    await page.until("document.querySelector('[data-label-id=\"msds-155\"] .label-pictograms')");
    const pics = await page.eval("return [...document.querySelectorAll('[data-label-id=\"msds-155\"] .label-pictogram figcaption')].map((e) => e.textContent);");
    expect(pics.length === 1 && pics[0] === "유해/자극성", pics.join(","));
    // 기본 크기(100mL 이하 간이표시)는 문구를 싣지 않으므로 일반용기로 바꿔 본다.
    await page.eval("const s = document.querySelector('#labelSize'); s.value = 'medium'; s.dispatchEvent(new Event('change')); return true;");
    await page.until("document.querySelector('[data-label-id=\"msds-155\"]')?.textContent.includes('유해·위험 문구')");
    const text = await page.eval("return document.querySelector('[data-label-id=\"msds-155\"]').textContent;");
    expect(text.includes("삼키면 유해함"), "유해·위험문구 없음");
  });

  await check("경고표지: 유해·위험문구가 없는 MSDS(GHP 그리스)도 표지가 열리고 빈 칸 없이 찍힌다", async () => {
    await page.go(`${BASE}/label.html?dataMode=public&product=msds-pdf-d53b862679ad3157`);
    await page.until("document.querySelector('[data-label-id=\"msds-pdf-d53b862679ad3157\"] .label-pictogram')");
    await page.eval("const s = document.querySelector('#labelSize'); s.value = 'medium'; s.dispatchEvent(new Event('change')); return true;");
    await page.until("document.querySelector('[data-label-id=\"msds-pdf-d53b862679ad3157\"]')?.textContent.includes('예방조치 문구')");
    const card = await page.eval(`const c = document.querySelector('[data-label-id="msds-pdf-d53b862679ad3157"]');
      return { signal: c.querySelector('.label-signal')?.textContent.trim(), missing: c.querySelectorAll('.label-missing').length };`);
    expect(card.signal === "경고" && card.missing === 0, JSON.stringify(card));
  });

  await check("경고표지: 분류 대상이 아닌 제품은 '그림문자 없음'", async () => {
    await page.go(`${BASE}/label.html?dataMode=public&product=msds-064`);
    await page.until("document.querySelector('[data-label-id=\"msds-064\"] .label-pictograms')");
    const text = await page.eval("return document.querySelector('[data-label-id=\"msds-064\"] .label-pictograms').textContent.trim();");
    expect(text === "그림문자 없음", text);
  });

  await check("경고표지: 처음에는 '고른 표지 인쇄'를 누를 수 없다", async () => {
    await page.go(`${BASE}/label.html`);
    await page.until("document.querySelector('#labelStatus')?.textContent.includes('건')");
    expect(await page.eval("return document.querySelector('#labelPrint').disabled;"), "눌린다");
  });

  await check("경고표지: 전체 선택 뒤 화면 아래 표지도 모두 인쇄한다", async () => {
    await page.go(`${BASE}/label.html?dataMode=public`);
    await page.until("document.querySelector('#labelStatus')?.textContent.includes('건')");
    const count = await page.eval(`return labelState.filtered.length;`);
    expect(count > 12, "가상 목록보다 많은 제품이 필요하다");
    await page.eval(`window.print = () => { window.printedIds = [...document.querySelectorAll('.label-card.is-selected:not(.is-copy)')].map((c) => c.dataset.labelId); };
      document.querySelector('#labelSelectAll').click();
      document.querySelector('#labelPrint').click();`);
    await page.until("Array.isArray(window.printedIds)");
    const actual = await page.eval("return window.printedIds.length;");
    expect(actual === count, `선택 ${count}건 / 인쇄 ${actual}건`);
  });

  for (const kind of ["label", "guide"]) {
    await check(`${kind}: 고른 것만 보기에서 전체 인쇄는 그 제품만 포함한다`, async () => {
      await page.go(`${BASE}/${kind}.html?dataMode=public&product=msds-033`);
      await page.until(`document.querySelector('#${kind}Print') && !document.querySelector('#${kind}Print').disabled`);
      await page.eval(`window.confirm = () => true;
        window.print = () => { window.printedIds = [...document.querySelectorAll('.${kind}-card:not(.is-copy)')].map((c) => c.dataset.${kind}Id); };
        const toggle = document.querySelector('#${kind}OnlySelected');
        if (toggle.getAttribute('aria-pressed') !== 'true') toggle.click();
        document.querySelector('#${kind}PrintAll').click();`);
      await page.until("Array.isArray(window.printedIds)");
      const actual = await page.eval("return window.printedIds;");
      expect(actual.length === 1 && actual[0] === "msds-033", `인쇄 대상 ${actual.length}건`);
    });

    await check(`${kind}: 공급사 안내 검색명 MRM·ISM이 원문 제품으로 연결된다`, async () => {
      await page.go(`${BASE}/${kind}.html?dataMode=public`);
      await page.until(`document.querySelector('#${kind}Status')?.textContent.includes('건')`);
      for (const [alias, id] of [["MRM", "msds-060"], ["ISM", "msds-061"]]) {
        await page.eval(`const input = document.querySelector('#${kind}Search'); input.value = '${alias}'; input.dispatchEvent(new Event('input', { bubbles: true }));`);
        const match = await page.eval(`return { card: Boolean(document.querySelector('[data-${kind}-id="${id}"]')), suggestion: document.querySelector('.pick-assist')?.textContent || '' };`);
        expect(match.card && match.suggestion.includes(alias === "MRM" ? "OVR" : "ISG"), JSON.stringify(match));
      }
    });

    await check(`${kind}: 키보드로 검색 제안을 선택하고 닫힌 상태를 알린다`, async () => {
      await page.eval(`const input = document.querySelector('#${kind}Search');
        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));`);
      const active = await page.eval(`const input = document.querySelector('#${kind}Search');
        return { expanded: input.getAttribute('aria-expanded'), option: document.getElementById(input.getAttribute('aria-activedescendant'))?.getAttribute('aria-selected') };`);
      expect(active.expanded === "true" && active.option === "true", JSON.stringify(active));
      await page.eval(`document.querySelector('#${kind}Search').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));`);
      const picked = await page.eval(`return { closed: document.querySelector('#${kind}Search').getAttribute('aria-expanded'), picked: document.querySelector('[data-${kind}-id="msds-061"]')?.classList.contains('is-selected') };`);
      expect(picked.closed === "false" && picked.picked, JSON.stringify(picked));
    });

    await check(`${kind}: 공개 자료가 실패하면 샘플 표지 없이 인쇄를 막는다`, async () => {
      await page.send("Network.enable");
      await page.send("Network.setBypassServiceWorker", { bypass: true });
      await page.send("Network.setBlockedURLs", { urls: ["*msds.public.json*"] });
      try {
        await page.go(`${BASE}/${kind}.html?dataMode=public`);
        await page.until(`document.querySelector('#${kind}Status')?.textContent.includes('불러오지 못')`);
        const state = await page.eval(`return { cards: document.querySelectorAll('.${kind}-card').length, blocked: document.querySelector('#${kind}Print').disabled && document.querySelector('#${kind}PrintAll').disabled };`);
        expect(state.cards === 0 && state.blocked, JSON.stringify(state));
      } finally {
        await page.send("Network.setBlockedURLs", { urls: [] });
        await page.send("Network.setBypassServiceWorker", { bypass: false });
      }
    });
  }

  await check("긴 제품명·성분명: 320·390px 폰에서도 화면 폭을 넘지 않는다", async () => {
    for (const width of [320, 390]) {
      await page.size(width, 844, true);
      await page.go(INDEX);
      await page.until("state.products.length > 0");
      const overflow = await page.eval(`const ingredientLength = p => Math.max(0, ...(p.ingredients || p.components || []).map(c => String(c.chemicalName || '').length));
        const candidates = [...new Set([
          ...[...state.products].sort((a,b) => b.productName.length - a.productName.length).slice(0,3),
          ...[...state.products].sort((a,b) => ingredientLength(b) - ingredientLength(a)).slice(0,3)
        ].map(p => p.id))];
        const failures = [];
        for (const id of candidates) {
          state.selectedId = id; render();
          await new Promise(ok => requestAnimationFrame(() => requestAnimationFrame(ok)));
          if (document.documentElement.scrollWidth > window.innerWidth + 1) failures.push({id, width: document.documentElement.scrollWidth, viewport: window.innerWidth});
        }
        document.querySelector('.detail-block-components')?.scrollIntoView();
        return failures;`);
      expect(overflow.length === 0, JSON.stringify(overflow));
    }
    await screenshot("mobile-long-ingredients");
  });

  await check("작은 병 라벨: 어두운 화면에서도 92×64mm 표지 8개를 흰 바탕으로 인쇄한다", async () => {
    await page.size(1280, 900);
    await page.go(`${BASE}/label.html?dataMode=public&product=msds-033`);
    await page.until("document.querySelector('[data-label-id=\"msds-033\"]')");
    await page.eval(`document.documentElement.dataset.theme = 'dark';
      const size = document.querySelector('#labelSize'); size.value = 'bottle'; size.dispatchEvent(new Event('change'));
      const qty = document.querySelector('[data-label-qty="msds-033"]'); qty.value = 8; qty.dispatchEvent(new Event('change', { bubbles: true }));
      document.querySelectorAll('[data-label-qr]').forEach(drawLabelQr);
      await document.fonts.ready;`);
    await sleep(250);
    await page.send("Emulation.setEmulatedMedia", { media: "print" });
    try {
      const cards = await page.eval(`return [...document.querySelectorAll('.label-card.is-selected')].map(c => {
        const r = c.getBoundingClientRect(), s = getComputedStyle(c);
        return { width: r.width, height: r.height, background: s.backgroundColor, overflow: c.scrollHeight > c.clientHeight + 1, qr: Boolean(c.querySelector('.label-qr svg')) };
      });`);
      expect(cards.length === 8 && cards.every(c => Math.abs(c.width - 92 * 96 / 25.4) < 1 && Math.abs(c.height - 64 * 96 / 25.4) < 1 && c.background === "rgb(255, 255, 255)" && !c.overflow && c.qr), JSON.stringify(cards));
      const { data } = await page.send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true, displayHeaderFooter: false });
      if (ARTIFACTS) writeFileSync(join(ARTIFACTS, "bottle-labels-a4.pdf"), Buffer.from(data, "base64"));
    } finally {
      await page.send("Emulation.setEmulatedMedia", { media: "screen" });
    }
  });

  await check("오프라인 저장 칸에 지금 자료판이 보인다", async () => {
    await page.go(`${INDEX}&offline=1`);
    await page.until("(document.querySelector('#offlinePanel')?.textContent || '').includes('지금 자료판')");
  });

  if (process.env.MSDS_CHECK_PUBLIC === "1") {
    await check("공개 사이트: 219개 제품과 최신 MRM·ISM 공급사 안내가 실제로 표시된다", async () => {
      const PUBLIC = "https://lsy1659-ux.github.io/msds-site-prototype/";
      await page.go(PUBLIC);
      await page.until("document.querySelectorAll('.quick-search button').length > 0", 30000);
      await page.until("state.products.length > 0 || state.dataLoadError", 30000);
      const count = await page.eval("return state.products.length;");
      expect(count === 219, `공개 제품 ${count}개`);
      for (const [alias, id, code] of [["MRM", "msds-060", "OVR"], ["ISM", "msds-061", "ISG"]]) {
        await page.eval(`const input = document.querySelector('#searchInput'); input.value = '${alias}'; input.dispatchEvent(new Event('input', { bubbles: true }));`);
        await page.until(`document.querySelector('.selection-item[data-product-id="${id}"]')`);
        await page.eval(`document.querySelector('.selection-item[data-product-id="${id}"]').click();`);
        const detail = await page.eval("return document.querySelector('.detail-block-msds-use-advice')?.textContent || '';");
        expect(detail.includes(alias) && detail.includes(code) && detail.includes("2026-10-13"), detail);
      }
      await screenshot("public-supplier-advice");
    });
  }

  if (process.env.MSDS_EXPECT_ASSET_VERSION) {
    await check("화면 자산과 서비스워커 판 번호가 기대값과 일치한다", async () => {
      await page.go(INDEX);
      await page.until("state.products.length > 0", 30000);
      const versions = await page.eval(`const asset = document.querySelector('script[src^="js/app.js"]');
        const sw = await (await fetch('sw.js', { cache: 'reload' })).text();
        return { asset: new URL(asset.src).searchParams.get('v'), cache: sw.match(/const CACHE_VERSION = "([^\"]+)"/)?.[1] };`);
      const expected = process.env.MSDS_EXPECT_ASSET_VERSION;
      expect(versions.asset === expected && versions.cache === `msds-${expected}`, JSON.stringify(versions));
    });
  }

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
if (ARTIFACTS) writeFileSync(join(ARTIFACTS, "results.json"), JSON.stringify(results, null, 2));
console.log(`\n${results.length - failed.length}/${results.length} 통과`);
process.exit(failed.length ? 1 : 0);
