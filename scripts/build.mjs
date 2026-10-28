#!/usr/bin/env node
// Build the site data from the official timetables.
//   node scripts/build.mjs --fetch            download both workbooks, then build
//   node scripts/build.mjs --aut a.xlsx --calc c.xlsx
// Writes public/data/{index,aut,calc,changes}.json and keeps a change history.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildDept, diffDept, FACULTIES, PROGRAMS, CALENDAR } from '../lib/build.mjs';
import { PLACES } from '../lib/rooms.mjs';
import { writeIcs } from '../lib/ics.mjs';
import { execFileSync } from 'node:child_process';
import { prettyTitle } from '../lib/build.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'public', 'data');
export const SOURCES = {
  aut: { name: 'Departamentul de Automatică', page: 'https://aut.utcluj.ro/index.php/anunturi.ro/orar-semestrul-i-2026-2027-2026-2027-semester-i-timetable.html',
    url: 'https://didatec-my.sharepoint.com/:x:/g/personal/iulia_stefan_campus_utcluj_ro/IQBvxXDDB6pWT4IXYVSygc5EAbsObMVYUC6KHcblr3n-Kl4?download=1' },
  calc: { name: 'Departamentul de Calculatoare', page: 'https://cs.utcluj.ro/orar.html',
    url: 'https://docs.google.com/spreadsheets/d/1xssn6PC5ODqIjowpPb8lQ6zphXDOzZsYR4wOw9yPfEI/export?format=xlsx' },
  ie: { name: 'Facultatea de Inginerie Electrică', page: 'https://ie.utcluj.ro/schedule.html', url: 'https://ie.utcluj.ro/schedule.html', py: 'ie.py' },
  constr: { name: 'Facultatea de Construcții', page: 'https://constructiicluj.edupage.org/timetable/', url: 'https://constructiicluj.edupage.org/timetable/', py: 'constr.py' },
  inst: { name: 'Facultatea de Inginerie a Instalațiilor', page: 'https://instalatii.utcluj.ro/studenti/orar.html', url: 'https://instalatii.utcluj.ro/studenti/orar.html', py: 'inst.py' },
  armm: { name: 'Facultatea de Autovehicule Rutiere, Mecatronică și Mecanică', page: 'https://armm.utcluj.ro/orar.html', url: 'https://armm.utcluj.ro/orar.html', py: 'armm.py' },
  iirmp: { name: 'Facultatea de Inginerie Industrială, Robotică și Managementul Producției', page: 'https://iirmp.utcluj.ro/orar.html', url: 'https://iirmp.utcluj.ro/orar.html', py: 'iirmp.py' },
  etti: { name: 'Facultatea de Electronică, Telecomunicații și Tehnologia Informației', page: 'https://etti.utcluj.ro/orar.html', url: 'https://etti.utcluj.ro/orar.html', py: 'etti.py' },
};
const DEPTS = Object.keys(SOURCES);

// titles typed in capitals -> lower case (prettyTitle then restores the first letter and diacritics)
function deCaps(t) {
  const letters = t.replace(/[^A-Za-zĂÂÎȘȚăâîșț]/g, '');
  const up = letters.replace(/[^A-ZĂÂÎȘȚ]/g, '').length;
  if (up < letters.length * 0.7) return t;
  const s = t.split(' ').map((w) => (/^(I|II|III|IV|V|VI|SCADA|CAD|MS|IT|&)$/.test(w.replace(/[^\w&]/g, '')) ? w : w.toLowerCase())).join(' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// PDF faculties are read by a Python script (pdfplumber); it prints the same shape buildDept() returns
function buildPy(dept) {
  const p = arg('--' + dept);
  if (!p && !args.includes('--fetch')) throw new Error(`lipsește --${dept} sau --fetch`);
  const out = execFileSync('python3', [path.join(ROOT, 'pdf', SOURCES[dept].py), p || '--fetch'], { maxBuffer: 1 << 28, encoding: 'utf8' });
  const res = JSON.parse(out);
  for (const list of Object.values(res.entries)) for (const e of list) {
    if (e.t) e.t = prettyTitle(deCaps(e.t), 'ro');
    if (!e.opt && /psihologia educa|pedagogi|didactica (special|gener)|modulul? pedagogic/i.test(e.t || '')) e.opt = 'ped';
  }
  return { res, lastModified: null };
}

const args = process.argv.slice(2);
const arg = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };

// SharePoint/OneDrive share links set a guest cookie on a redirect before serving the file: follow redirects by hand, keeping cookies
async function fetchKeepingCookies(url) {
  const jar = new Map();
  for (let i = 0; i < 12; i++) {
    const r = await fetch(url, { redirect: 'manual', headers: { 'user-agent': 'Mozilla/5.0 (orar-utcn; +https://utcna.pages.dev)', cookie: [...jar].map(([k, v]) => `${k}=${v}`).join('; ') } });
    for (const sc of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) {
      const kv = sc.split(';')[0];
      const j = kv.indexOf('=');
      if (j > 0) jar.set(kv.slice(0, j).trim(), kv.slice(j + 1));
    }
    const loc = r.headers.get('location');
    if (r.status >= 300 && r.status < 400 && loc) { url = new URL(loc, url).toString(); continue; }
    return r;
  }
  throw new Error('prea multe redirecționări');
}
function candidates(url) {
  const out = [];
  const u = new URL(url);
  u.searchParams.set('download', '1');
  out.push(u.toString());
  // personal OneDrive links: /:x:/g/personal/<user>/<token> -> /personal/<user>/_layouts/15/download.aspx?share=<token>
  const m = /^\/:[a-z]:\/[a-z]\/personal\/([^/]+)\/([^/?]+)/.exec(new URL(url).pathname);
  if (m) out.push(`${new URL(url).origin}/personal/${m[1]}/_layouts/15/download.aspx?share=${m[2]}`);
  return out;
}

async function getBuf(dept) {
  const p = arg('--' + dept);
  if (p) return { buf: fs.readFileSync(p), lastModified: fs.statSync(p).mtime.toISOString() };
  if (!args.includes('--fetch')) throw new Error(`lipsește --${dept} sau --fetch`);
  // the Automatică link can be changed without touching code (GitHub variable ORAR_URL)
  const url = (dept === 'aut' && process.env.ORAR_URL) || SOURCES[dept].url;
  const tried = [];
  for (const u of /sharepoint\.com/.test(url) ? candidates(url) : [url]) {
    const r = await fetchKeepingCookies(u);
    const buf = Buffer.from(await r.arrayBuffer());
    if (r.ok && buf.slice(0, 2).toString() === 'PK') return { buf, lastModified: r.headers.get('last-modified') };
    tried.push(`${r.status} ${r.headers.get('content-type') || ''} ${buf.length} B`);
  }
  throw new Error(`${dept}: nu am primit fișierul xlsx (${tried.join(' | ')})`);
}

const readJson = (f, d = null) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };

fs.mkdirSync(OUT, { recursive: true });
const now = new Date().toISOString();
const index = readJson(path.join(OUT, 'index.json'), { depts: {} });
let changes = readJson(path.join(OUT, 'changes.json'), []);
let changed = false;

const only = arg('--only');
for (const dept of DEPTS) {
  if (only && !only.split(',').includes(dept)) continue;
  let src, next;
  try {
    if (SOURCES[dept].py) { const r = buildPy(dept); next = r.res; src = { lastModified: r.lastModified }; }
    else { src = await getBuf(dept); next = await buildDept(src.buf, dept); }
  } catch (e) { console.error(`! ${dept}: ${e.message.split('\n')[0]} — păstrez datele vechi`); continue; }
  const prev = readJson(path.join(OUT, `${dept}.json`));
  const diff = diffDept(prev, next);
  const same = prev && JSON.stringify(prev.entries) === JSON.stringify(next.entries) && JSON.stringify(prev.groups) === JSON.stringify(next.groups) && JSON.stringify(prev.langs) === JSON.stringify(next.langs);
  const data = { dept, stamp: next.stamp, builtAt: same && prev.builtAt ? prev.builtAt : now, sourceModified: src.lastModified, groups: next.groups, entries: next.entries, langs: next.langs, notes: next.notes };
  if (!same) {
    fs.writeFileSync(path.join(OUT, `${dept}.json`), JSON.stringify(data));
    changed = true;
    if (diff.length) changes.unshift({ at: now, dept, stamp: next.stamp, groups: diff });
    writeIcs(path.join(ROOT, 'public', 'ics'), data, CALENDAR);
  }
  index.depts[dept] = {
    stamp: next.stamp, builtAt: data.builtAt, checkedAt: now, source: { name: SOURCES[dept].name, page: SOURCES[dept].page, url: SOURCES[dept].url },
    groups: next.groups.map(({ id, label, prog, year, sgs, sub, fac }) => ({ id, label, prog, year, sgs, sub, fac: fac || 'ac' })),
  };
  for (const w of next.warnings) console.log(`  ~ ${w}`);
  console.log(`${dept}: ${next.groups.length} grupe, ${Object.values(next.entries).reduce((n, l) => n + l.length, 0)} ore, ${same ? 'neschimbat' : 'actualizat'}${diff.length ? `, ${diff.length} grupe cu modificări` : ''}`);
}
// calendars for every group, rebuilt each run (they are not kept in git)
for (const dept of DEPTS) {
  const d = readJson(path.join(OUT, `${dept}.json`));
  if (d) writeIcs(path.join(ROOT, 'public', 'ics'), d, CALENDAR);
}
changes = changes.slice(0, 60);
Object.assign(index, { v: 2, faculties: FACULTIES, programs: PROGRAMS, calendar: CALENDAR, places: PLACES, checkedAt: now });
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
fs.writeFileSync(path.join(OUT, 'changes.json'), JSON.stringify(changes));
console.log(changed ? 'date noi scrise' : 'nicio schimbare');
