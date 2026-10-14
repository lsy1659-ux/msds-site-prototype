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
import { createReadStream, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("../..", import.meta.url)));
// 제품 수는 배포 기준(data/release-policy.json) 한 곳에서 읽는다. 숫자를 박아 두면 제품을 하나 더할 때마다 점검이 깨진다.
const EXPECTED = JSON.parse(readFileSync(join(ROOT, "data", "release-policy.json"), "utf8")).expectedProducts;
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
  if (process.env.MSDS_BOUNDARY_ONLY && !name.includes(process.env.MSDS_BOUNDARY_ONLY)) return;
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

const evidence = {};
async function indexReady(query = "") {
  await page.go(`${INDEX}${query}`);
  await page.until("typeof state !== 'undefined' && state.products.length === 220 && document.querySelectorAll('.quick-search button').length > 0");
}
async function printReady(kind, query = "") {
  await page.go(`${BASE}/${kind}.html?dataMode=public${query}`);
  await page.until(`typeof ${kind}State !== 'undefined' && ${kind}State.products.length === 220 && document.querySelector('#${kind}Status')?.textContent.includes('건')`);
}
try {
  await page.scheme(false);
  await page.size(1280,900);
  await check('잘못된 ID와 잘못된 퍼센트 입력은 제품을 임의로 열지 않는다',async()=>{
    const values=[];
    for(const id of ['not-a-product','%E0%A4%A','msds-033,missing']) {
      await indexReady(`&product=${encodeURIComponent(id)}`);
      values.push(await page.eval(`return {id:state.selectedId,notice:state.publicNotice};`));
    }
    evidence.invalidIds=values;
    expect(values.every(v=>!v.id&&v.notice.includes('찾지 못')),JSON.stringify(values));
  });
  await check('유효한 제품 ID는 URL의 다른 제품명보다 우선한다',async()=>{
    await indexReady('&product=msds-033&q=DR-174');
    expect(await page.eval("return state.selectedId === 'msds-033';"),'valid ID was replaced');
  });
  await check('끊어진 QR의 부분 제품명이 여러 제품에 맞으면 자동 선택하지 않는다',async()=>{
    await indexReady('&product=not-a-product&q=DR-174');
    const result=await page.eval(`return {id:state.selectedId,notice:state.publicNotice,matches:state.products.filter(p=>normalizeSearchText(p.productName).includes(normalizeSearchText('DR-174'))).length};`);
    evidence.ambiguousPartial=result;
    await screenshot('ambiguous-name');
    expect(result.matches>1&&!result.id,JSON.stringify(result));
    expect(result.notice.includes('여러')||result.notice.includes('고르'),result.notice);
  });
  await check('동일 제품명이 둘 이상인 QR 대체 검색도 임의 선택하지 않는다',async()=>{
    await indexReady();
    const result=await page.eval(`const u=new URL(location.href);u.searchParams.set('product','missing');u.searchParams.set('q','same-name');history.replaceState({},'',u);
      const id=getRequestedProductId([{id:'fixture-a',productName:'same-name'},{id:'fixture-b',productName:'same-name'}]);return {id,notice:state.publicNotice};`);
    evidence.ambiguousExact=result;expect(!result.id,JSON.stringify(result));
  });
  await check('한글·괄호·샵이 있는 정확한 원문명은 QR 대체 검색에서 맞는 제품을 연다',async()=>{
    await indexReady();
    const p=await page.eval("return state.products.find(p=>p.productName.includes('#'))||state.products.find(p=>p.productName.includes('('));");
    await indexReady(`&product=missing&q=${encodeURIComponent(p.productName)}`);
    expect(await page.eval(`return state.selectedId===${JSON.stringify(p.id)};`),p.productName);
  });
  await check('220개 원문 링크는 새 파일명·한글·샵·퍼센트를 정확히 인코딩한다',async()=>{
    await indexReady();
    const result=await page.eval(`const bad=[];let special=0;
      for(const p of state.products){const info=buildPdfInfo(p);const href=new URL(info.encodedPath,document.baseURI);const expected=new URL(p.pdfPath.split('/').map(encodeURIComponent).join('/'),document.baseURI);
        if(href.href!==expected.href||href.hash)bad.push({id:p.id,actual:href.href,expected:expected.href});if(/[#%]/.test(p.pdfPath))special++;}
      return {bad,special};`);
    evidence.pdfEncoding=result;expect(!result.bad.length&&result.special>0,JSON.stringify(result));
  });
  await check('샵이 있는 새 PDF 파일도 실제 미리보기에서 열리고 끝 쪽으로 이동한다',async()=>{
    await indexReady();const p=await page.eval("return state.products.find(p=>p.pdfPath.includes('#'));");
    await indexReady(`&product=${encodeURIComponent(p.id)}`);
    await page.eval("document.querySelector('.detail-block-pdf [data-preview-pdf]').click();");
    await page.until("document.querySelector('.detail-block-pdf canvas')",30000);
    const label=await page.eval("return document.querySelector('.detail-block-pdf .pdf-js-page-label').textContent;");
    const last=parseInt(label.split('/')[1],10);expect(last>1,label);
    await page.eval(`const input=document.querySelector('.detail-block-pdf [data-pdf-page-input]');input.value=${last};input.dispatchEvent(new Event('change',{bubbles:true}));`);
    await page.until(`document.querySelector('.detail-block-pdf .pdf-js-page-label')?.textContent.startsWith('${last} /')`);
  });
  await check('선택 제품 띠의 경고표지·관리요령 바로가기도 공개 모드를 유지한다',async()=>{
    await indexReady('&product=msds-033');
    const urls=await page.eval("return [...document.querySelectorAll('.selected-product-bar-print a')].map(a=>a.href);");
    evidence.printShortcuts=urls;
    expect(urls.length===2&&urls.every(href=>{const u=new URL(href);return u.searchParams.get('product')==='msds-033'&&u.searchParams.get('dataMode')==='public';}),JSON.stringify(urls));
  });
  for(const kind of ['label','guide']) {
    await check(`${kind}: QR 주소는 제품명과 명시한 공개 자료 모드를 보존한다`,async()=>{
      await printReady(kind,'&product=msds-pdf-f5a05b27dd78d893');
      const result=await page.eval(kind==='label'?`return buildProductUrl('msds-pdf-f5a05b27dd78d893');`:`return guideProductUrl(guideState.products.find(p=>p.id==='msds-pdf-f5a05b27dd78d893'));`);
      evidence[kind+'Qr']=result;const u=new URL(result);
      expect(u.searchParams.get('product')==='msds-pdf-f5a05b27dd78d893'&&u.searchParams.get('q').includes('OV1K-CAR')&&u.searchParams.get('dataMode')==='public',result);
    });
    await check(`${kind}: 중복·빈·없는 ID가 섞인 URL은 실제 두 제품만 선택한다`,async()=>{
      await printReady(kind,'&product=msds-033,msds-033,,missing&product=msds-077');
      const ids=await page.eval(`return [...${kind}State.selected];`);
      expect(ids.length===2&&ids.includes('msds-033')&&ids.includes('msds-077'),JSON.stringify(ids));
    });
    await check(`${kind}: 검색 결과가 없어도 이전에 고른 두 제품의 인쇄는 빠지지 않는다`,async()=>{
      await printReady(kind,'&product=msds-033,msds-077');
      await page.eval(`const input=document.querySelector('#${kind}Search');input.value='NO-RESULT-BOUNDARY-98765';input.dispatchEvent(new Event('input',{bubbles:true}));
        window.print=()=>{window.printed=[...document.querySelectorAll('.${kind}-card.is-selected:not(.is-copy)')].map(c=>c.dataset.${kind}Id);};`);
      expect(await page.eval(`return ${kind}State.filtered.length===0&&document.querySelector('#${kind}PrintAll').disabled&&!document.querySelector('#${kind}Print').disabled;`),'empty/selected print state wrong');
      await page.eval(`document.querySelector('#${kind}Print').click();`);
      await page.until('Array.isArray(window.printed)');const ids=await page.eval('return window.printed;');
      evidence[kind+'EmptySelectedPrint']=ids;expect(ids.length===2&&ids.includes('msds-033')&&ids.includes('msds-077'),JSON.stringify(ids));
      await page.eval("window.dispatchEvent(new Event('afterprint'));");
    });
    await check(`${kind}: 빈 선택·빈 결과에서는 인쇄 버튼 둘 다 닫힌다`,async()=>{
      await printReady(kind,'&product=missing');
      await page.eval(`document.querySelector('#${kind}Clear').click();const input=document.querySelector('#${kind}Search');input.value='NO-RESULT-98765';input.dispatchEvent(new Event('input',{bubbles:true}));`);
      expect(await page.eval(`return document.querySelector('#${kind}Print').disabled&&document.querySelector('#${kind}PrintAll').disabled;`),'empty result can print');
    });
    await check(`${kind}: 전체 인쇄 취소는 인쇄·선택·목록 범위를 바꾸지 않는다`,async()=>{
      await printReady(kind,'&product=msds-033');
      const before=await page.eval(`if(${kind}State.onlySelected)document.querySelector('#${kind}OnlySelected').click();window.calls=0;window.confirm=()=>false;window.print=()=>window.calls++;return {selected:[...${kind}State.selected],filtered:${kind}State.filtered.length};`);
      await page.eval(`document.querySelector('#${kind}PrintAll').click();`);await sleep(150);
      const after=await page.eval(`return {selected:[...${kind}State.selected],filtered:${kind}State.filtered.length,calls:window.calls};`);
      expect(!after.calls&&JSON.stringify(before.selected)===JSON.stringify(after.selected)&&before.filtered===after.filtered,JSON.stringify({before,after}));
    });
  }
  await check('서로 다른 라벨 수량 3+2장의 실제 인쇄 표시와 QR가 정확하다',async()=>{
    await printReady('label','&product=msds-033,msds-077');
    await page.eval(`const size=document.querySelector('#labelSize');size.value='bottle';size.dispatchEvent(new Event('change'));
      for(const[id,n]of [['msds-033',3],['msds-077',2]]){const input=document.querySelector('[data-label-qty="'+id+'"]');input.value=n;input.dispatchEvent(new Event('change',{bubbles:true}));}
      window.print=()=>{window.called=true;};document.querySelector('#labelPrint').click();`);
    await page.until('window.called');await page.send('Emulation.setEmulatedMedia',{media:'print'});
    try{
      const cards=await page.eval(`return [...document.querySelectorAll('.label-card')].filter(c=>getComputedStyle(c).display!=='none').map(c=>({id:c.dataset.labelId,qr:!!c.querySelector('.label-qr svg')}));`);
      evidence.mixedQuantity=cards;expect(cards.length===5&&cards.every(c=>c.qr)&&cards.filter(c=>c.id==='msds-033').length===3&&cards.filter(c=>c.id==='msds-077').length===2,JSON.stringify(cards));
    }finally{await page.send('Emulation.setEmulatedMedia',{media:''});}
  });
  await check('조회 빈 검색 결과와 초기화는 잘못된 상세나 PDF를 남기지 않는다',async()=>{
    await indexReady('&product=msds-033');
    await page.eval("const input=document.querySelector('#searchInput');input.value='NO-RESULT-98765';input.dispatchEvent(new Event('input',{bubbles:true}));");
    expect(await page.eval("return !state.selectedId&&getFilteredProducts().length===0&&!document.querySelector('.selected-product-bar');"),'stale selection');
    await page.eval("document.querySelector('#clearSearch').click();");
    expect(await page.eval("return !state.selectedId&&state.query==='';"),'reset failed');
  });
  for(const [width,height]of [[320,820],[360,740],[568,320]]) {
    await check(`큰 글자·긴 제품명·구판 표시: ${width}×${height} 화면에서 링크와 정보가 화면 폭 안에 있다`,async()=>{
      await page.size(width,height,true);await indexReady('&product=msds-pdf-3cf931eec9be742d');
      await page.eval("document.documentElement.dataset.textSize='large';");
      const old=await page.eval(`const link=document.querySelector('.old-version-link');const rect=link.getBoundingClientRect();return {overflow:document.documentElement.scrollWidth-innerWidth,linkWidth:rect.width};`);
      const next=await page.eval("return [...state.products].sort((a,b)=>b.productName.length-a.productName.length)[0].id;");
      await indexReady(`&product=${encodeURIComponent(next)}`);await page.eval("document.documentElement.dataset.textSize='large';");
      const long=await page.eval(`return {overflow:document.documentElement.scrollWidth-innerWidth,text:document.querySelector('.selected-product-bar').textContent};`);
      evidence['mobile'+width]={old,long};expect(old.overflow<=2&&old.linkWidth<=width&&long.overflow<=2,JSON.stringify({old,long}));
      await screenshot('large-text-'+width);
    });
  }
  await check('예외와 콘솔 오류가 없다',async()=>{
    const errors=page.errors.filter(t=>t&&!/favicon|Failed to load resource|ServiceWorker|Transition was skipped/i.test(t));expect(!errors.length,errors.join(' | '));
  });
}finally{
  page.ws.close();chrome.proc.kill();server.close();await sleep(300);
  try{rmSync(chrome.profile,{recursive:true,force:true});}catch{}
}
if(ARTIFACTS){writeFileSync(join(ARTIFACTS,'results.json'),JSON.stringify(results,null,2));writeFileSync(join(ARTIFACTS,'observations.json'),JSON.stringify(evidence,null,2));}
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 통과`);
process.exit(results.some(r=>!r.ok)?1:0);
