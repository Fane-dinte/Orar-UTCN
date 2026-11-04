// Search-engine pages: one static, crawlable page per faculty (groups + links into the app and its .ics calendars),
// plus sitemap.xml. The app itself is a single client-rendered page, so these are what a search result can land on.
import fs from 'node:fs';
import path from 'node:path';

const SITE = (process.env.SITE_URL || 'https://utcna.pages.dev').replace(/\/$/, '');
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const LEVEL = { lic: 'Licență', master: 'Master' };

const CSS = `*{box-sizing:border-box}body{margin:0;font:16px/1.55 "Space Grotesk",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#14151a;background:#fbfbfd}
main{max-width:860px;margin:0 auto;padding:28px 18px 56px}nav a{color:#3a2fb0;text-decoration:none;font-weight:600}h1{font-size:2rem;line-height:1.15;margin:.5em 0 .3em}
h2{font-size:1.15rem;margin:1.8em 0 .5em}h3{font-size:.95rem;color:#555a66;margin:1.1em 0 .4em;font-weight:600}p{margin:.5em 0;color:#2c2f38}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none}.chips a{display:inline-block;padding:7px 13px;border-radius:999px;background:#ece9ff;color:#2d2490;text-decoration:none;font-weight:600}
.chips a:hover{background:#3a2fb0;color:#fff}.cta{display:inline-block;margin:10px 0;padding:12px 20px;border-radius:14px;background:#3a2fb0;color:#fff;text-decoration:none;font-weight:700}
small,.note{color:#555a66;font-size:.9rem}footer{margin-top:3em;border-top:1px solid #e6e7ee;padding-top:1em}
@media(prefers-color-scheme:dark){body{background:#0f1014;color:#ececf1}p{color:#c9cbd3}.chips a{background:#262447;color:#cfc9ff}.cta{background:#8f7bff;color:#0f1014}nav a{color:#a99bff}footer{border-color:#2a2c35}small,.note,h3{color:#9a9ead}}`;

function facultyPage(f, groups, programs, source) {
  const name = f.name;
  const total = groups.length;
  const progIds = [...new Set(groups.map((g) => g.prog))];
  const title = `Orar ${name} UTCN Cluj, ${total} grupe | Orar UTCN`;
  const desc = `Orarul Facultății de ${name} de la UTCN Cluj-Napoca: ${total} grupe și semigrupe, cu săli, profesori și paritatea săptămânilor. Se actualizează singur din orarul oficial.`;
  const url = `${SITE}/facultati/${f.id}/`;
  let body = '';
  for (const level of ['lic', 'master']) {
    const ps = progIds.filter((p) => (programs[p] || {}).level === level);
    if (!ps.length) continue;
    body += `<h2>${LEVEL[level]}</h2>`;
    for (const p of ps) {
      const pr = programs[p] || { name: p };
      body += `<h3>${esc(pr.long || pr.name)}</h3>`;
      const years = [...new Set(groups.filter((g) => g.prog === p).map((g) => g.year))].sort();
      for (const y of years) {
        const gs = groups.filter((g) => g.prog === p && g.year === y).sort((a, b) => String(a.label).localeCompare(String(b.label), 'ro', { numeric: true }));
        body += `<p class="note">Anul ${y}</p><ul class="chips">` + gs.map((g) => `<li><a href="${SITE}/#${esc(g.id)}" title="Orar grupa ${esc(g.label)}, ${esc(pr.name)}, anul ${y}">${esc(g.label)}</a></li>`).join('') + '</ul>';
      }
    }
  }
  const ld = {
    '@context': 'https://schema.org',
    '@graph': [
      { '@type': 'BreadcrumbList', itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Orar UTCN', item: SITE + '/' },
        { '@type': 'ListItem', position: 2, name: `Orar ${name}`, item: url } ] },
      { '@type': 'WebPage', name: title, description: desc, url, inLanguage: 'ro', isPartOf: { '@type': 'WebSite', name: 'Orar UTCN', url: SITE + '/' } },
    ],
  };
  return `<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#fbfbfd">
<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Orar UTCN">
<meta property="og:locale" content="ro_RO">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<style>${CSS}</style>
</head>
<body>
<main>
<nav><a href="${SITE}/">← Orar UTCN</a></nav>
<h1>Orar ${esc(name)}, UTCN Cluj</h1>
<p>Alege grupa ta și vezi orarul pe zi sau pe săptămână, cu paritatea săptămânilor (impară/pară), sălile, profesorii și clădirile pe hartă. Orarul se citește singur, din oră în oră, din orarele oficiale ale facultății, deci rămâne la zi.</p>
<p><a class="cta" href="${SITE}/">Deschide aplicația</a></p>
${body}
<h2>Cum funcționează</h2>
<p>Apeși pe grupa ta, alegi semigrupa și, dacă vrei, adaugi orarul în Google Calendar sau Apple Calendar (abonare la fișierul .ics al grupei). Aplicația se poate instala pe telefon și merge și fără internet.</p>
<footer>
<p class="note">${total} grupe${source ? ` · sursa: <a href="${esc(source)}" rel="noopener">orarul oficial al facultății</a>` : ''}. Pagină neoficială, făcută de un student. La o nepotrivire, orarul oficial are dreptate.</p>
</footer>
</main>
</body>
</html>
`;
}

export function writeSeo(root, index) {
  const pub = path.join(root, 'public');
  const faculties = (index.faculties || []).filter((f) => f.ready);
  const urls = [{ loc: SITE + '/', pri: '1.0' }];
  for (const f of faculties) {
    const groups = Object.values(index.depts || {}).flatMap((d) => d.groups || []).filter((g) => (g.fac || 'ac') === f.id);
    if (!groups.length) continue;
    const source = Object.values(index.depts || {}).find((d) => (d.groups || []).some((g) => (g.fac || 'ac') === f.id))?.source?.page;
    const dir = path.join(pub, 'facultati', f.id);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'index.html'), facultyPage(f, groups, index.programs || {}, source));
    urls.push({ loc: `${SITE}/facultati/${f.id}/`, pri: '0.8' });
  }
  const day = (index.checkedAt || new Date().toISOString()).slice(0, 10);
  fs.writeFileSync(path.join(pub, 'sitemap.xml'),
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.map((u) => `  <url><loc>${u.loc}</loc><lastmod>${day}</lastmod><changefreq>daily</changefreq><priority>${u.pri}</priority></url>`).join('\n') + '\n</urlset>\n');
}
