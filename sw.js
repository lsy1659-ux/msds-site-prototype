/* MSDS 현장 조회 서비스워커.
 *
 * 현장과 창고는 신호가 약한 곳이 많은데 MSDS는 작업 전에 바로 볼 수 있어야 한다.
 * 그래서 화면과 제품 데이터를 캐시해 두고, 연결이 끊겨도 조회가 되게 한다.
 *
 * 규칙은 세 가지다.
 *  - 화면 파일: 캐시 우선. 버전을 올리면 새로 받는다.
 *  - 제품 데이터: 네트워크 우선. 새 제품이 등록되면 바로 반영되고, 끊기면 마지막 사본을 쓴다.
 *  - PDF: 열어본 것만 캐시. 전체는 80MB가 넘어 미리 담지 않는다.
 */

const CACHE_VERSION = "msds-2026-09-21-51";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const DATA_CACHE = `${CACHE_VERSION}-data`;
const PDF_CACHE = `${CACHE_VERSION}-pdf`;
const PDF_CACHE_LIMIT = 300;

const SHELL_ASSETS = [
  "./",
  "index.html",
  "label.html",
  "guide.html",
  "substance.html",
  "css/style.css",
  "css/label.css",
  "css/guide.css",
  "css/substance.css",
  "css/topbar.css",
  "js/app.js",
  "js/page-transition.js",
  "js/site-qr.js",
  "js/admin-gate.js",
  "js/label.js",
  "js/guide.js",
  "js/substance.js",
  "js/csv-export.js",
  "js/pick-assist.js",
  "vendor/qrcode.min.js",
  "vendor/pdf.mjs",
  "vendor/pdf.worker.mjs",
  "manifest.webmanifest",
  "assets/icons/icon-192.png",
  "assets/icons/icon-512.png",
  "assets/icons/icon-maskable-512.png",
  "assets/ppe/goggles.svg",
  "assets/ppe/gloves.svg",
  "assets/ppe/mask.svg",
  "assets/ppe/suit.svg",
  "assets/ppe/boots.svg",
  "assets/ghs/ghs01.svg",
  "assets/ghs/ghs02.svg",
  "assets/ghs/ghs03.svg",
  "assets/ghs/ghs04.svg",
  "assets/ghs/ghs05.svg",
  "assets/ghs/ghs06.svg",
  "assets/ghs/ghs07.svg",
  "assets/ghs/ghs08.svg",
  "assets/ghs/ghs09.svg"
];

const DATA_ASSETS = [
  "data/msds.public.json",
  "data/msds-overrides.public.json",
  "data/release-manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const shell = await caches.open(SHELL_CACHE);
    // 파일 하나가 없어도 설치가 통째로 실패하지 않게 개별로 담는다.
    await Promise.allSettled(SHELL_ASSETS.map((asset) => shell.add(asset)));
    const data = await caches.open(DATA_CACHE);
    await Promise.allSettled(DATA_ASSETS.map((asset) => data.add(asset)));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(
      names.filter((name) => !name.startsWith(CACHE_VERSION)).map((name) => caches.delete(name))
    );
    await self.clients.claim();
  })());
});

function isDataRequest(url) {
  return url.pathname.endsWith(".json");
}

function isPdfRequest(url) {
  return url.pathname.toLowerCase().endsWith(".pdf");
}

async function trimCache(cacheName, limit) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length <= limit) return;
  await Promise.all(keys.slice(0, keys.length - limit).map((key) => cache.delete(key)));
}

const NETWORK_TIMEOUT_MS = 2000;

// 신호가 약한 현장에서는 응답 없이 오래 매달릴 수 있어 제한시간을 둔다.
function fetchWithTimeout(request, timeout) {
  return Promise.race([
    fetch(request),
    new Promise((_, reject) => setTimeout(() => reject(new Error("network timeout")), timeout))
  ]);
}

// 끊긴 것이 확실하면 네트워크를 아예 시도하지 않는다. 기다리는 시간이 곧 대기시간이다.
function isKnownOffline() {
  return self.navigator && self.navigator.onLine === false;
}

// 제품 데이터는 최신이 우선이다. 끊겼거나 느리면 마지막 사본을 돌려준다.
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  if (isKnownOffline()) {
    const offlineCached = await cache.match(request, { ignoreSearch: true });
    if (offlineCached) return offlineCached;
  }
  try {
    const response = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    throw error;
  }
}

/* 화면 파일은 주소가 정확히 같을 때만 저장본을 쓴다.
 *
 * 전에는 ?v= 를 무시하고 맞췄는데, 그러면 새 판을 올려도 옛 파일이 계속 나갔다.
 * 이제 ?v= 가 바뀌면 새로 받고, 끊겼을 때만 판이 다른 사본이라도 꺼내 쓴다.
 */
async function cacheFirst(request, cacheName, { limit = 0 } = {}) {
  const cache = await caches.open(cacheName);
  const exact = await cache.match(request);
  if (exact) return exact;

  if (!isKnownOffline()) {
    try {
      const response = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
      if (response && response.ok) {
        await cache.put(request, response.clone());
        if (limit) await trimCache(cacheName, limit);
      }
      return response;
    } catch (error) {
      // 아래에서 저장본을 찾아본다.
    }
  }

  const loose = await cache.match(request, { ignoreSearch: true });
  if (loose) return loose;
  return fetch(request);
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isDataRequest(url)) {
    event.respondWith(networkFirst(request, DATA_CACHE));
    return;
  }

  if (isPdfRequest(url)) {
    event.respondWith(cacheFirst(request, PDF_CACHE, { limit: PDF_CACHE_LIMIT }));
    return;
  }

  // 주소창이나 링크로 들어온 화면 요청.
  // 끊긴 상태면 네트워크를 건너뛰고 바로 저장본을 띄워 대기시간을 없앤다.
  if (request.mode === "navigate") {
    event.respondWith((async () => {
      const cache = await caches.open(SHELL_CACHE);
      const cached = async () => (await cache.match(request, { ignoreSearch: true }))
        || (await cache.match("index.html"));
      if (isKnownOffline()) {
        const hit = await cached();
        if (hit) return hit;
      }
      try {
        return await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
      } catch (error) {
        return (await cached()) || Response.error();
      }
    })());
    return;
  }

  event.respondWith(cacheFirst(request, SHELL_CACHE));
});
