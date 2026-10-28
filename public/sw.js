// Orar UTCN — merge și fără internet.
// Pagina: întâi de pe internet (ca să vezi imediat versiunea nouă), din cache doar fără semnal.
// Datele: din cache imediat, actualizate în fundal. Fonturile: din cache.
const V = "orar-v2-5";
const CORE = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/favicon.svg", "data/index.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(V).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== V && k !== "orar-meta").map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

async function networkFirst(req) {
  const c = await caches.open(V);
  try {
    const r = await fetch(req);
    if (r.ok) c.put(req, r.clone());
    return r;
  } catch {
    return (await c.match(req, { ignoreSearch: true })) || (await c.match("index.html")) || Response.error();
  }
}
async function staleWhileRevalidate(req, evt) {
  const c = await caches.open(V);
  const hit = await c.match(req);
  const net = fetch(req).then((r) => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => null);
  if (hit) { evt.waitUntil(net); return hit; }
  return (await net) || Response.error();
}
async function cacheFirst(req) {
  const c = await caches.open(V);
  const hit = await c.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok || r.type === "opaque") c.put(req, r.clone());
  return r;
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith(".html")) { e.respondWith(networkFirst(req)); return; }
    if (url.pathname.includes("/data/")) {
      // the data is cheap: try fresh first so a change shows up at once, fall back to cache offline
      e.respondWith(networkFirst(req)); return;
    }
    if (url.pathname.includes("/ics/")) return;
    e.respondWith(staleWhileRevalidate(req, e)); return;
  }
  if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) { e.respondWith(cacheFirst(req)); return; }
});

// ---- change notifications (when the user turned them on) ----
async function getPrefs() {
  const c = await caches.open("orar-meta");
  const r = await c.match("prefs");
  return r ? r.json() : null;
}
async function setPrefs(p) {
  const c = await caches.open("orar-meta");
  await c.put("prefs", new Response(JSON.stringify(p), { headers: { "content-type": "application/json" } }));
}
self.addEventListener("message", (e) => {
  const d = e.data || {};
  if (d.type === "prefs") e.waitUntil(getPrefs().then((old) => setPrefs(Object.assign({}, old || {}, d, { seen: d.seen || (old && old.seen) || null }))));
});
async function checkChanges() {
  const p = await getPrefs();
  if (!p || !p.notify || !p.group) return;
  const r = await fetch("data/changes.json", { cache: "no-store" });
  if (!r.ok) return;
  const changes = await r.json();
  const fresh = changes.filter((c) => !p.seen || c.at > p.seen);
  let n = 0;
  for (const c of fresh) for (const g of c.groups) if (g.g === p.group) for (const it of g.items) if (((it.to || it.from).sg || []).includes(p.sg)) n++;
  if (changes[0]) await setPrefs(Object.assign(p, { seen: changes[0].at }));
  if (n) await self.registration.showNotification("Orarul tău s-a schimbat", { body: `${n} ${n === 1 ? "modificare" : "modificări"} la grupa ${p.group}. Atinge ca să vezi.`, icon: "icons/icon-192.png", badge: "icons/icon-192.png", tag: "orar-change" });
}
self.addEventListener("periodicsync", (e) => { if (e.tag === "orar-check") e.waitUntil(checkChanges()); });
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: "window" }).then((cs) => (cs[0] ? cs[0].focus() : self.clients.openWindow("./"))));
});
