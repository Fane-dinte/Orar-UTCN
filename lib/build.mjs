// Turn the two official workbooks into the site's data files.
import ExcelJS from 'exceljs';
import { buildModel, cellText } from './sheet.mjs';
import { analyzeSheet } from './parse.mjs';
import { placeOf } from './rooms.mjs';
import TITLES_AUT from './titles-aut.json' with { type: 'json' };

export const FACULTIES = [
  { id: 'ac', name: 'Automatică și Calculatoare', short: 'AC', keys: 'automatica calculatoare ac aia cti ti informatica', ready: true, desc: 'Automatică · Calculatoare · TI · master' },
  { id: 'etti', name: 'Electronică, Telecomunicații și Tehnologia Informației', short: 'ETTI', keys: 'etti electronica telecomunicatii tehnologia informatiei', ready: true, desc: 'Electronică · Telecomunicații · Ing. economică · English · master' },
  { id: 'ie', name: 'Inginerie Electrică', short: 'IE', keys: 'inginerie electrica ie medicala energetica economica', ready: true, desc: 'Electrică · Energetică · Medicală · Economică · master' },
  { id: 'armm', name: 'Autovehicule Rutiere, Mecatronică și Mecanică', short: 'ARMM', keys: 'mecatronica autovehicule armm mecanica transporturi', ready: true, desc: 'Autovehicule · Mecatronică · ITT · Mecanică · master' },
  { id: 'iirmp', name: 'Inginerie Industrială, Robotică și Managementul Producției', short: 'IIRMP', keys: 'robotica industriala iirmp tcm constructii de masini design industrial inginerie economica', ready: true, desc: 'Robotică · TCM · Ing. economică · Design industrial · licență' },
  { id: 'imm', name: 'Ingineria Materialelor și a Mediului', short: 'IMM', keys: 'materialelor mediului imm ingineria materialelor protectia mediului ipmi', ready: true, desc: 'Ingineria materialelor · Protecția mediului în industrie · licență' },
  { id: 'constr', name: 'Construcții', short: 'CONSTR', keys: 'constructii civile cadastru drumuri poduri', ready: true, desc: 'Inginerie civilă · IMC · Cadastru · Civil Eng. · master' },
  { id: 'inst', name: 'Instalații', short: 'INST', keys: 'instalatii ingineria instalatiilor', ready: true, desc: 'Ingineria instalațiilor · licență' },
  { id: 'fau', name: 'Arhitectură și Urbanism', short: 'FAU', keys: 'arhitectura urbanism', ready: false },
];

export const PROGRAMS = {
  aia: { name: 'Automatică', long: 'Automatică și Informatică Aplicată', fac: 'ac', dept: 'aut', lang: 'ro', level: 'lic' },
  'aia-en': { name: 'Automatică (EN)', long: 'Automation and Applied Informatics (English)', fac: 'ac', dept: 'aut', lang: 'en', level: 'lic' },
  cti: { name: 'Calculatoare', long: 'Calculatoare', fac: 'ac', dept: 'calc', lang: 'ro', level: 'lic' },
  'cti-en': { name: 'Calculatoare (EN)', long: 'Computer Science (English)', fac: 'ac', dept: 'calc', lang: 'en', level: 'lic' },
  ti: { name: 'Tehnologia informației', long: 'Tehnologia Informației', fac: 'ac', dept: 'calc', lang: 'ro', level: 'lic' },
  'm-aut': { name: 'Master Automatică', long: 'Master — Automatică și Informatică Aplicată', fac: 'ac', dept: 'aut', lang: 'ro', level: 'master' },
  'm-cti': { name: 'Master Calculatoare', long: 'Master — Calculatoare și Tehnologia Informației', fac: 'ac', dept: 'calc', lang: 'ro', level: 'master' },
  'ie-el': { name: 'Inginerie electrică', long: 'Inginerie electrică', fac: 'ie', dept: 'ie', lang: 'ro', level: 'lic' },
  'ie-en': { name: 'Inginerie energetică', long: 'Inginerie energetică (Ingineria sistemelor electroenergetice)', fac: 'ie', dept: 'ie', lang: 'ro', level: 'lic' },
  'ie-med': { name: 'Inginerie medicală', long: 'Inginerie medicală', fac: 'ie', dept: 'ie', lang: 'ro', level: 'lic' },
  'ie-econ': { name: 'Inginerie economică', long: 'Inginerie economică în domeniul electric, electronic și energetic', fac: 'ie', dept: 'ie', lang: 'ro', level: 'lic' },
  'm-ie': { name: 'Master', long: 'Master — Inginerie Electrică', fac: 'ie', dept: 'ie', lang: 'ro', level: 'master' },
  'etti-ro': { name: 'Electronică și telecomunicații', long: 'Inginerie electronică, telecomunicații și tehnologii informaționale', fac: 'etti', dept: 'etti', lang: 'ro', level: 'lic' },
  'etti-en': { name: 'English', long: 'Electronics and Telecommunications (English)', fac: 'etti', dept: 'etti', lang: 'en', level: 'lic' },
  'etti-ie': { name: 'Inginerie economică', long: 'Inginerie economică în domeniul electric, electronic și energetic', fac: 'etti', dept: 'etti', lang: 'ro', level: 'lic' },
  'constr-ic': { name: 'Inginerie civilă', long: 'Inginerie civilă (CCIA, CFDP, ACH, IUDR)', fac: 'constr', dept: 'constr', lang: 'ro', level: 'lic' },
  'constr-imc': { name: 'Inginerie și management', long: 'Inginerie și management în construcții', fac: 'constr', dept: 'constr', lang: 'ro', level: 'lic' },
  'constr-mtc': { name: 'Cadastru (MTC)', long: 'Măsurători terestre și cadastru', fac: 'constr', dept: 'constr', lang: 'ro', level: 'lic' },
  'constr-ce': { name: 'Civil Engineering', long: 'Civil Engineering (English)', fac: 'constr', dept: 'constr', lang: 'en', level: 'lic' },
  'm-constr': { name: 'Master', long: 'Master — Construcții', fac: 'constr', dept: 'constr', lang: 'ro', level: 'master' },
  'imm-im': { name: 'Ingineria materialelor', long: 'Ingineria materialelor', fac: 'imm', dept: 'imm', lang: 'ro', level: 'lic' },
  'imm-ipmi': { name: 'Protecția mediului în industrie', long: 'Ingineria și protecția mediului în industrie', fac: 'imm', dept: 'imm', lang: 'ro', level: 'lic' },
  'inst-ii': { name: 'Ingineria instalațiilor', long: 'Ingineria instalațiilor', fac: 'inst', dept: 'inst', lang: 'ro', level: 'lic' },
  'armm-ar': { name: 'Autovehicule rutiere', long: 'Ingineria autovehiculelor — Autovehicule rutiere', fac: 'armm', dept: 'armm', lang: 'ro', level: 'lic' },
  'armm-escca': { name: 'ESCCA', long: 'Echipamente și sisteme de comandă și control pentru autovehicule', fac: 'armm', dept: 'armm', lang: 'ro', level: 'lic' },
  'armm-itt': { name: 'Transporturi (ITT)', long: 'Ingineria transporturilor și a traficului', fac: 'armm', dept: 'armm', lang: 'ro', level: 'lic' },
  'armm-im': { name: 'Inginerie mecanică', long: 'Inginerie mecanică', fac: 'armm', dept: 'armm', lang: 'ro', level: 'lic' },
  'armm-mtr': { name: 'Mecatronică', long: 'Mecatronică', fac: 'armm', dept: 'armm', lang: 'ro', level: 'lic' },
  'armm-mtr-en': { name: 'Mecatronică (EN)', long: 'Mechatronics (English)', fac: 'armm', dept: 'armm', lang: 'en', level: 'lic' },
  'iirmp-rob': { name: 'Robotică', long: 'Robotică', fac: 'iirmp', dept: 'iirmp', lang: 'ro', level: 'lic' },
  'iirmp-rob-en': { name: 'Robotică (EN)', long: 'Robotics (English)', fac: 'iirmp', dept: 'iirmp', lang: 'en', level: 'lic' },
  'iirmp-tcm': { name: 'TCM', long: 'Tehnologia construcțiilor de mașini', fac: 'iirmp', dept: 'iirmp', lang: 'ro', level: 'lic' },
  'iirmp-tcm-en': { name: 'TCM (EN)', long: 'Manufacturing Engineering (English)', fac: 'iirmp', dept: 'iirmp', lang: 'en', level: 'lic' },
  'iirmp-tcm-de': { name: 'TCM (DE)', long: 'Fertigungstechnik (Deutsch)', fac: 'iirmp', dept: 'iirmp', lang: 'de', level: 'lic' },
  'iirmp-iei': { name: 'Inginerie economică', long: 'Inginerie economică industrială', fac: 'iirmp', dept: 'iirmp', lang: 'ro', level: 'lic' },
  'iirmp-di': { name: 'Design industrial', long: 'Design industrial', fac: 'iirmp', dept: 'iirmp', lang: 'ro', level: 'lic' },
  'm-armm': { name: 'Master', long: 'Master — ARMM', fac: 'armm', dept: 'armm', lang: 'ro', level: 'master' },
  'm-etti': { name: 'Master', long: 'Master — ETTI', fac: 'etti', dept: 'etti', lang: 'ro', level: 'master' },
};

const AUT_SHEETS = [
  ['AN I', 1, 'aia'], ['AN I En', 1, 'aia-en'], ['AN II', 2, 'aia'], ['AN II En', 2, 'aia-en'],
  ['AN III', 3, 'aia'], ['AN III En', 3, 'aia-en'], ['AN IV', 4, 'aia'], ['AN IV En', 4, 'aia-en'],
  ['MASTER AN I', 1, 'm-aut'], ['MASTER AN II', 2, 'm-aut'],
];
const CALC_SHEETS = [
  ['1r', 1, null], ['1e', 1, 'cti-en'], ['2r', 2, null], ['2e', 2, 'cti-en'], ['3r', 3, null], ['3e', 3, 'cti-en'],
  ['4r', 4, null], ['4e', 4, 'cti-en'], ['1M', 1, 'm-cti'], ['2M', 2, 'm-cti'], ['1MC', 1, 'm-cti'], ['2MC', 2, 'm-cti'],
];

// --- semester calendar (UTCN, sem. I 2026–2027, from the official timetable & the university's year structure)
export const CALENDAR = {
  weeks: [
    ['2026-09-28', 1], ['2026-10-05', 2], ['2026-10-12', 3], ['2026-10-19', 4], ['2026-10-26', 5], ['2026-11-02', 6], ['2026-11-09', 7],
    ['2026-11-16', 8], ['2026-11-23', 9], ['2026-11-30', 10], ['2026-12-07', 11], ['2026-12-14', 12], ['2027-01-04', 13], ['2027-01-11', 14],
  ],
  holidays: [['2026-11-30', 'Sf. Andrei'], ['2026-12-01', 'Ziua Națională'], ['2027-01-01', 'Anul Nou'], ['2027-01-06', 'Boboteaza'], ['2027-01-07', 'Sf. Ioan']],
  vacation: ['2026-12-21', '2027-01-03'],
  session: ['2027-01-18', '2027-02-07'],
  retake: ['2027-02-15', '2027-02-21'],
  sem2: '2027-02-22',
};

// --- titles: Romanian diacritics and sentence case for the official (often diacritic-less) names
const WORDS = {
  si: 'și', algebra: 'algebră', liniara: 'liniară', analitica: 'analitică', matematica: 'matematică', fizica: 'fizică', electronica: 'electronică', digitala: 'digitală',
  computationale: 'computaționale', masurari: 'măsurări', reglarii: 'reglării', educatiei: 'educației', educatie: 'educației', retele: 'rețele', retelelor: 'rețelelor',
  inteligenta: 'inteligența', artificiala: 'artificială', grafica: 'grafică', logica: 'logică', diferential: 'diferențial', orientata: 'orientată',
  functionala: 'funcțională', 'functională': 'funcțională', recunoastere: 'recunoaștere', informatica: 'informatică', industriala: 'industrială', legislatie: 'legislație',
  economica: 'economică', specialitatii: 'specialității', asistata: 'asistată', aplicatii: 'aplicații', aplicatiilor: 'aplicațiilor', informatiei: 'informației',
  diagnoza: 'diagnoză', achizitii: 'achiziții', actionari: 'acționări', masini: 'mașini', etica: 'etică', academica: 'academică', personala: 'personală',
  profesionala: 'profesională', robotilor: 'roboților', interfete: 'interfețe', mentenanta: 'mentenanța', germana: 'germană', franceza: 'franceză', engleza: 'engleză',
  straina: 'străină', straine: 'străine', invatare: 'învățare', aplicata: 'aplicată', masurari_: 'măsurări', comunicatii: 'comunicații', calitate: 'calitate',
  analiza: 'analiza', fiabilitate: 'fiabilitate', translatoarelor: 'translatoarelor', programarii: 'programării', distribuite: 'distribuite', tranzactionale: 'tranzacționale',
  securitate: 'securitate', criptografie: 'criptografie', diferentiala: 'diferențială', geometrie: 'geometrie', campului: 'câmpului', masurari: 'măsurări',
  electrice: 'electrice', electronice: 'electronice', masini: 'mașini', masurarea: 'măsurarea', tractiune: 'tracțiune', electrica: 'electrică', energetica: 'energetică',
  utilizarea: 'utilizarea', interfete: 'interfețe', achizitii: 'achiziții', distributia: 'distribuția', statistica: 'statistică', medicala: 'medicală',
  imagistica: 'imagistică', biomecanica: 'biomecanică', clinica: 'clinică', piata: 'piața', termotehnica: 'termotehnică', mentenanta: 'mentenanța', actionari: 'acționări',
  electromagnetica: 'electromagnetică', compatibilitate: 'compatibilitate', servomecanisme: 'servomecanisme', regenerabile: 'regenerabile', antreprenoriat: 'antreprenoriat',
  antrepreniorat: 'antreprenoriat', integritate: 'integritate', etica: 'etică', calitatea: 'calitatea', inginerie: 'inginerie', ingineria: 'ingineria', energetic: 'energetic',
  sisteme: 'sisteme', procesarea: 'procesarea', protocoale: 'protocoale', anat: 'anat', fizio: 'fizio', economie: 'economie', fizica: 'fizică', mecanica: 'mecanică',
  bazele: 'bazele', electrotehnicii: 'electrotehnicii', programarea: 'programarea', calculatoarelor: 'calculatoarelor', limbaje: 'limbaje', programare: 'programare',
  arhitecturi: 'arhitecturi', operare: 'operare', complemente: 'complemente', matematici: 'matematici', aplicate: 'aplicate', standardizare: 'standardizare', si: 'și', in: 'în',
  testare: 'testare', biologice: 'biologice', electrotehnice: 'electrotehnice', metode: 'metode', introducere: 'introducere', managementul: 'managementul', proiectelor: 'proiectelor',
  producerea: 'producerea', transportul: 'transportul', energiei: 'energiei', echipamente: 'echipamente', parametrilor: 'parametrilor', biomedicali: 'biomedicali',
  tehnici: 'tehnici', securitatea: 'securitatea', electromagnetic: 'electromagnetic', expert: 'expert', instrumente: 'instrumente', integrare: 'integrare', stiinta: 'știința', in: 'în', comunicatii_: 'comunicații', numerica: 'numerică', numerice: 'numerice', proiectarea: 'proiectarea', baze: 'baze',
};
export function prettyTitle(t, lang = 'ro') {
  if (!t) return t;
  let s = t.replace(/ţ/g, 'ț').replace(/Ţ/g, 'Ț').replace(/ş/g, 'ș').replace(/Ş/g, 'Ș').replace(/\s+/g, ' ').trim().replace(/^[`´'"]+\s*/, '');
  s = s.replace(/^Contolul/, 'Controlul');
  if (lang === 'en' && !/[ăâîșț]/i.test(s) && !/\b(si|de|cu|pentru|în|in)\b/.test(s)) return s;
  if (/\b(and|of|the|for|with|engineering|science|systems|data|security|intelligence|learning|design|computer|networks?)\b/i.test(s) && !/\b(si|și|de|pentru)\b/i.test(s)) return s;
  const words = s.split(' ');
  const out = words.map((w, i) => {
    const m = /^([A-Za-zĂÂÎȘȚăâîșț]+)(.*)$/.exec(w);
    if (!m) return w;
    let [, core, rest] = m;
    if (/^[A-Z0-9]{2,}$/.test(core) && core.length <= 6) return w; // acronyms
    const low = core.toLowerCase();
    let rep = WORDS[low] || low;
    if (i === 0) rep = rep[0].toUpperCase() + rep.slice(1);
    else if (/^(I|II|III|IV)$/.test(core)) rep = core;
    return rep + rest;
  });
  return out.join(' ');
}

const LANG_NAME = { fr: 'franceză', en: 'engleză', de: 'germană' };

function pickProgram(code, sheetProg, dept) {
  if (sheetProg) return sheetProg;
  if (!code) return dept === 'aut' ? 'm-aut' : 'm-cti';
  if (/^306/.test(code)) return 'ti';
  if (/^304/.test(code)) return 'cti-en';
  if (/^302/.test(code)) return 'cti';
  if (/^303/.test(code)) return 'aia-en';
  if (/^301/.test(code)) return 'aia';
  if (/^31/.test(code)) return 'm-aut';
  if (/^32/.test(code)) return 'm-cti';
  return dept === 'aut' ? 'aia' : 'cti';
}

async function loadWb(buf) {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(buf);
  return wb;
}

function findStamp(wb, dept) {
  if (dept === 'aut') {
    const ws = wb.worksheets.find((w) => /anunt/i.test(w.name));
    if (ws) for (const row of ws.getSheetValues()) if (row) for (const v of row) { const t = cellText(v); if (/\d{2}\.\d{2}\.\d{4},?\s*ora/.test(t)) return t.trim(); }
  } else {
    const ws = wb.worksheets.find((w) => w.name === '1r');
    if (ws) for (const row of ws.getSheetValues()) if (row) for (const v of row) { const t = cellText(v); if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(t.trim())) return t.trim(); }
  }
  return null;
}

export async function buildDept(buf, dept) {
  const wb = await loadWb(buf);
  const sheets = dept === 'aut' ? AUT_SHEETS : CALC_SHEETS;
  const groups = []; const entries = {}; const notes = {}; const warnings = [];
  const used = new Set();
  for (const [name, year, sheetProg] of sheets) {
    const ws = wb.worksheets.find((w) => w.name.trim() === name);
    if (!ws) { warnings.push(`lipsește foaia ${name}`); continue; }
    const lang = / En$|e$/.test(name) && !/^\d?M/.test(name) ? 'en' : 'ro';
    const res = analyzeSheet(buildModel(ws), { dept, diagonals: dept === 'aut', slashParity: dept === 'calc', en: lang === 'en', sheetKey: name, allowPseudo: /M/.test(name) && dept === 'calc' });
    warnings.push(...res.warnings.map((w) => `${name}: ${w}`));
    // titles known in this sheet: acronym -> long title
    const local = new Map();
    for (const e of res.entries) if (e.a && e.t && e.k !== 'X' && !e.choice) { if (!local.has(e.a) || e.t.length > local.get(e.a).length) local.set(e.a, e.t); }
    const fix = (a) => {
      if (!a || local.has(a)) return a;
      const sorted = [...a].sort().join('');
      for (const k of local.keys()) if (k.length === a.length && [...k].sort().join('') === sorted) return k; // BCS -> BSC
      return a;
    };
    for (const g of res.groups) {
      const prog = pickProgram(g.code, sheetProg, dept);
      let id = g.code || g.key;
      if (used.has(id)) id = `${id}-a${year}`;
      used.add(id);
      const label = g.code ? g.code : g.label || g.key;
      const TAGS = { A: 'Automatică', I: 'Informatică aplicată', ISA: '', '': '' };
      let sub = g.section || (g.tag in TAGS ? TAGS[g.tag] : g.tag) || '';
      if (/semigrup/i.test(sub)) sub = g.section || '';
      if (g.pseudo) sub = g.label;
      sub = prettyTitle(sub.replace(/\s*-\s*/, '-').replace(/^seria\s*/i, 'seria ').replace(/^\((.*)\)$/, '$1'), 'ro').replace(/^Seria /, 'seria ').replace(/^(Automatica|Automatică)-A$/, 'Automatică').replace(/-IA$/, '');
      groups.push({ id, label, prog, year, sgs: g.sgs, sub, sheet: name, dept, fac: 'ac' });
      const list = res.entries.filter((e) => e.g === g.key).map((e) => {
        const a = fix(e.a);
        let t = e.t || local.get(a) || (dept === 'aut' ? TITLES_AUT[`${name}|${a}`] : null) || null;
        if (a === 'LS' || e.opt === 'lang') {
          const base = lang === 'en' ? 'Foreign language' : 'Limbă străină';
          t = e.t && !/^(limbi|foreign)/i.test(e.t) ? e.t : base + (e.lang ? ` (${lang === 'en' ? { fr: 'French', en: 'English', de: 'German' }[e.lang] : LANG_NAME[e.lang]})` : '');
        }
        if (!t && a) t = a;
        const out = {
          d: e.d, s: e.s, e: e.e, p: e.p, k: e.k, a: a || null, t: prettyTitle(t, lang), r: e.r || null,
          sg: e.sg, all: e.all,
        };
        if (e.w) out.w = e.w;
        if (e.prof) out.prof = e.prof.replace(/\s+/g, ' ').trim();
        if (e.opt) out.opt = e.opt;
        if (e.lang) out.lang = e.lang;
        if (e.note) out.note = e.note;
        if (e.cx) out.cx = 1;
        if (e.choice) out.choice = 1;
        const pl = placeOf(out.r, { dept, ped: e.opt === 'ped' });
        if (pl) out.pl = pl.k;
        out.raw = e.raw.replace(/\s+/g, ' ').trim();
        out.src = e.src.replace(/^[^!]*!/, '');
        return out;
      }).sort((x, y) => x.d - y.d || x.s - y.s || x.e - y.e);
      // drop exact duplicates
      const seen = new Set();
      entries[id] = list.filter((x) => { const k = JSON.stringify([x.d, x.s, x.e, x.p, x.w, x.sg, x.a, x.r, x.k]); if (seen.has(k)) return false; seen.add(k); return true; });
    }
    notes[name] = res.notes.filter((n) => !n.startsWith('dupgroup:'));
    for (const n of res.notes.filter((n) => n.startsWith('dupgroup:'))) warnings.push(`${name}: grupa ${n.slice(9)} apare de două ori în antet; am tratat coloanele ca semigrupele 1 și 2`);
  }
  // how many groups share each activity (same source cell): "toată seria" vs "toată grupa"
  const share = new Map();
  for (const [gid, list] of Object.entries(entries)) for (const e of list) { const k = `${groups.find((g) => g.id === gid).sheet}!${e.src}`; share.set(k, (share.get(k) || new Set()).add(gid)); }
  for (const [gid, list] of Object.entries(entries)) { const sh = groups.find((g) => g.id === gid).sheet; for (const e of list) { const n = share.get(`${sh}!${e.src}`).size; if (n > 1) e.n = n; } }
  // foreign-language classes are per language, not per group: pool them per year so a student can pick their own slot
  const langs = {};
  for (const g of groups) {
    for (const e of entries[g.id]) {
      if (e.opt !== 'lang' || !e.lang) continue;
      const pool = (langs[g.sheet] = langs[g.sheet] || []);
      const k = [e.lang, e.d, e.s, e.e, e.p, (e.w || []).join(','), e.r || ''].join('|');
      let slot = pool.find((x) => x.id === k);
      if (!slot) { slot = { id: k, lang: e.lang, d: e.d, s: e.s, e: e.e, p: e.p, k: e.k, a: e.a, t: e.t, r: e.r, opt: 'lang', raw: e.raw, src: e.src, groups: [] }; if (e.w) slot.w = e.w; if (e.prof) slot.prof = e.prof; if (e.pl) slot.pl = e.pl; pool.push(slot); }
      if (!slot.groups.includes(g.label)) slot.groups.push(g.label);
    }
  }
  for (const k of Object.keys(langs)) langs[k].sort((a, b) => a.lang.localeCompare(b.lang) || a.d - b.d || a.s - b.s);
  return { dept, stamp: findStamp(wb, dept), groups, entries, notes, langs, warnings };
}

// --- change detection between two builds of the same department
const sig = (e) => `${e.d}|${e.s}|${e.e}|${e.p}|${(e.w || []).join(',')}|${e.sg.join('')}|${e.k}|${e.a || e.t}|${e.r || ''}`;
export function diffDept(prev, next) {
  const out = [];
  if (!prev) return out;
  for (const g of next.groups) {
    const a = prev.entries[g.id] || [];
    const b = next.entries[g.id] || [];
    const A = new Map(a.map((e) => [sig(e), e])), Bm = new Map(b.map((e) => [sig(e), e]));
    const removed = a.filter((e) => !Bm.has(sig(e)));
    const added = b.filter((e) => !A.has(sig(e)));
    const items = [];
    for (const n of added) {
      const i = removed.findIndex((o) => o.d === n.d && (o.a || o.t) === (n.a || n.t) && o.k === n.k && o.sg.join() === n.sg.join());
      if (i >= 0) { const o = removed.splice(i, 1)[0]; items.push({ type: 'mod', from: brief(o), to: brief(n) }); }
      else items.push({ type: 'add', to: brief(n) });
    }
    for (const o of removed) items.push({ type: 'del', from: brief(o) });
    if (items.length) out.push({ g: g.id, items });
  }
  return out;
}
const brief = (e) => ({ d: e.d, s: e.s, e: e.e, p: e.p, w: e.w, k: e.k, a: e.a, t: e.t, r: e.r, sg: e.sg });
