// Parse one timetable cell text into structured fields.
// Handles both notations: Automatică ("BSC L 309", "Algebra liniara AL 2C 356 (V. Pop)")
// and Calculatoare ("PL 204", "AM (s) - BT 5.02", "Fizica (F) - T. Petrisor - H11").

const NOT_PROF = /^(fr|en|ger|de|fac\.?|facultativ|opt|optional|ls|emerson|\d+h.*|s[ăa]pt.*|spt.*|c\+s|l\+p|c \+ s|l \+ p|c \+ p|curs|seminar|l|p|s|c|fac\.\)?|tuesday.*|bosch.*|cu anul.*|recontractare|isa|a|i|lab.*|sapt.*|\d.*)$/i;

export function normRoom(r) {
  if (!r) return null;
  let x = r.replace(/\s+/g, ' ').trim().replace(/[.,;:]+$/, '');
  x = x.replace(/^(sala|room)\s+/i, '');
  x = x.replace(/^amf\.?\s*/i, 'Amf. ');
  x = x.replace(/^Amf\. (F|40)$/i, '$1');
  x = x.replace(/^bt\s*\.?\s*(\d)\.?(\d{2})$/i, 'BT $1.$2');
  x = x.replace(/^bt\s*(\d\.\d{2})/i, 'BT $1');
  x = x.replace(/^h\.?\s*(\d{2})$/i, 'H$1');
  x = x.replace(/^s\s*3\.?5$/i, 'S3.5').replace(/^s\s*4\.?2$/i, 'S4.2').replace(/^s\s*4\.?1$/i, 'S4.1');
  x = x.replace(/^(\d+)\s*b$/i, '$1B');
  x = x.replace(/^(7)\s*obs$/i, '7 Obs');
  x = x.replace(/^aula\s*inst(\.|alatii|alații)?$/i, 'Aula Inst.');
  x = x.replace(/^c\s+(\d{2})$/i, 'C$1').replace(/^c(\d{2})$/i, 'C$1');
  x = x.replace(/^em\s*2$/i, 'EM2');
  if (/^(dor\.?|p|l|s|c)$/i.test(x)) return null;
  return x || null;
}

const LANG = [
  [/\(fr\)|franc(ez|ez)[aă]|french|\bfr\b/i, 'fr'],
  [/\(ger\)|german[aă]?|\bgerman\b|\(de\)|\bge\b\s+2c/i, 'de'],
  [/\(en\)|engl(ez|ish)[aă]?|\benglish\b|limba englez/i, 'en'],
];
const PED = /psiholog|pedagog|didactic|instruire asistat|managementul clasei|educational psych|computer assisted instr|\bIAC\b|\bPE 2C P03\b/i;
const FAC = /\(fac\.?\)|\bfac\.?\b|facultativ|\(opt\)|\boptional\b|\(optional\)|quantum|cuantic/i;

export function parseText(raw, cfg = {}) {
  let t = ' ' + raw.replace(/[`´*]+/g, ' ').replace(/\s+/g, ' ').trim() + ' ';
  const out = { k: null, a: null, t: null, r: null, prof: null, opt: null, lang: null, note: null, p: null, w: null, s: null, e: null, dur: null, complex: false };
  const notes = [];
  // --- parity words
  if (/s[ăa]pt\.?\s*,?\s*impar[ăa]?|impar[ăa] ?\)|\bodd\b/i.test(t)) out.p = 'odd';
  else if (/s[ăa]pt\.?\s*par[ăa]?\b|\(s[ăa]pt\.? par[ăa]?\)|\bin par\b|\beven\b/i.test(t)) out.p = 'even';
  t = t.replace(/\(?\s*s[ăa]pt\.?\s*,?\s*(im)?par[ăa]?\s*\)?/gi, ' ');
  // --- explicit hour ranges for another day are notes, not times
  const otherDay = /\((tuesday|monday|wednesday|thursday|friday|luni|marti|miercuri|joi|vineri)[^)]*\)/i.exec(t);
  if (otherDay) { notes.push(otherDay[0].replace(/[()]/g, '')); t = t.replace(otherDay[0], ' '); }
  // --- week lists
  const wre = /((?:[sS][ăa]pt|SAPT|[sS]pt|saptamanile)\.?\s*|st\.\s*)?(?<![\d.A-Za-z])((?:1[0-4]|[1-9])(?:\s*[,.]\s*(?:1[0-4]|[1-9]))*)(?![\d.]?\d)/gi;
  const wl = [];
  let wm;
  while ((wm = wre.exec(t))) {
    const kw = !!wm[1];
    const list = wm[2];
    const nums = list.split(/[,.]/).map((x) => +x.trim()).filter((x) => x >= 1 && x <= 14);
    const before = t[wm.index + (wm[1] ? wm[1].length : 0) - 1] || ' ';
    const after = t[wm.index + wm[0].length] || ' ';
    const okCtx = /[\s(,]/.test(before) && /[\s(),]/.test(after);
    if ((kw && nums.length >= 1) || (okCtx && nums.length >= 2 && list.includes(','))) wl.push({ m: wm[0], nums });
  }
  if (wl.length) {
    out.w = [...new Set(wl.flatMap((x) => x.nums))].sort((a, b) => a - b);
    if (wl.length > 1) out.complex = true;
    for (const x of wl) t = t.replace(x.m, ' ');
  }
  if ((t.match(/\(\s*\d{1,2}\s*-\s*\d{1,2}\s*\)/g) || []).length > 1) out.complex = true;
  // --- time overrides "(18-22)", "intre orele 18-22", "(3h 10-13)", "(17-18)"
  const tm = /(?:intre(?: orele)?|between)\s*(\d{1,2})\s*-\s*(\d{1,2})|\(\s*(?:\d\s*h\s*[: ,]*)?(\d{1,2})\s*-\s*(\d{1,2})\s*\)|(\d{1,2})\s*-\s*(\d{1,2})\s*\)|\b(\d{1,2})\s*-\s*(\d{1,2})\s*$/i.exec(t);
  if (tm) {
    const s = +(tm[1] || tm[3] || tm[5] || tm[7]), e = +(tm[2] || tm[4] || tm[6] || tm[8]);
    if (s >= 7 && s <= 22 && e > s && e <= 23) { out.s = s; out.e = e; t = t.replace(tm[0], ' '); }
  }
  const dm = /\(\s*(\d)\s*h\s*\)|\((\d)\s*h\b|\b(\d)\s*h\b/i.exec(t);
  if (dm) {
    const d = +(dm[1] || dm[2] || dm[3]);
    if (out.w && out.w.length > 1) notes.push(`în săptămâna ${out.w[out.w.length - 1]} doar ${d}h`);
    else if (out.s == null && d >= 1 && d <= 4) out.dur = d;
    t = t.replace(dm[0], dm[0].startsWith('(') && !dm[0].endsWith(')') ? '(' : ' ');
  }
  // --- language & optional categories
  for (const [re, l] of LANG) if (re.test(raw)) { out.lang = l; break; }
  if (/^\s*(LS|FL)\b|limbi? str[aă]in|foreign lang|^\s*(germana|franceza|limba )|limba (englez|franc|german)|\benglish\b.*\d|\(e\)/i.test(raw)) out.opt = 'lang';
  if (PED.test(raw)) out.opt = 'ped';
  if (/complemente de matematic/i.test(raw)) out.opt = 'cm';
  if (!out.opt && FAC.test(raw)) out.opt = 'fac';
  // --- special kinds
  if (/[îi]nt[aâ]lnire cu [îi]ndrum[aă]torul|study advisor/i.test(raw)) {
    out.k = 'X'; out.t = cfg.en ? 'Study advisor meeting' : 'Întâlnire cu îndrumătorul de an';
    const pm = /\(\s*([^)]+?)\s*\)/.exec(raw); if (pm && !/^\d/.test(pm[1])) out.prof = pm[1].trim();
    const rm = /(?:amf\.?\s*|[-–]\s*)?\b(F|H11|H21|D0[1-4]|D21|356|40|E15)\b/.exec(raw.replace(/\([^)]*\)/g, ' '));
    if (rm) out.r = normRoom(rm[0].replace(/^[-–]\s*/, ''));
    return finish(out, notes, t);
  }
  if (/^\s*sport\b/i.test(t)) { out.k = 'SP'; out.t = 'Sport'; return finish(out, notes, t); }
  if (/vor fi programate|de comun acord/i.test(raw)) { out.k = 'X'; out.t = raw.replace(/\s+/g, ' ').trim(); out.a = null; return finish(out, notes, t); }
  if (/^\s*etic|etica|ethics/i.test(t) && !/\(/.test(t.replace(/\(sapt[^)]*\)/i, ''))) {
    out.k = 'C'; out.a = 'ETICA'; out.t = 'Etică și integritate academică';
    const r = /\b(P03|D21|E15|F)\b/.exec(t); if (r) out.r = r[1];
  }
  if (cfg.dept === 'calc') parseCalc(t, out);
  else parseAut(t, out);
  return finish(out, notes, t);
}

function finish(out, notes, t) {
  if (out.a) out.a = out.a.replace(/[.:]$/, '');
  if (notes.length) out.note = notes.join('; ');
  if (!out.k) out.k = 'L';
  return out;
}

// ---------------- Automatică notation ----------------
function parseAut(t, out) {
  let s = t.trim();
  // professor in trailing parentheses
  const parens = [...s.matchAll(/\(([^()]*)\)/g)];
  for (const p of parens) {
    const inner = p[1].trim();
    if (!inner) continue;
    if (/^(fr|en|ger)$/i.test(inner)) continue;
    if (NOT_PROF.test(inner)) continue;
    if (/[A-ZĂÂÎȘȚ][a-zăâîșț.]/.test(inner) && /[.\s]/.test(inner) || /^[A-Z]\.\s?[A-Z]/.test(inner) || /\//.test(inner) && /[A-Z][a-z]/.test(inner)) {
      if (!out.prof && !/ (C|S|L)$/.test(inner) && !/^(Emerson|Bosch)/i.test(inner)) out.prof = inner.replace(/^\(+|\)+$/g, '').trim();
    }
  }
  const ub = /\s([A-Z]\.\s?[A-ZĂÂÎȘȚ][a-zăâîșț]+)\)\s*$/.exec(s);
  if (ub && !out.prof) { out.prof = ub[1]; s = s.replace(ub[0], ' '); }
  s = s.replace(/\(\s*\(/g, '(');
  const body = s.replace(/\([^()]*\)/g, ' ').replace(/\s+/g, ' ').trim();
  // short notation (no lowercase words): classify tokens instead of relying on order
  const lowerWords = (body.match(/\b[a-zăâîșț]{3,}\b/g) || []).filter((w) => !/^(sala|amf|inst|obs|dor|fac|si|spt|sapt)$/i.test(w));
  const capWords = (body.match(/\b[A-ZĂÂÎȘȚ][a-zăâîșț]{3,}\b(?!\.)/g) || []).filter((w) => !/^(Amf|Aula|Inst|Sala|Obs)$/i.test(w));
  const hasTitle = lowerWords.length >= 1 || capWords.length >= 1;
  if (!hasTitle) {
    const tk = body.replace(/\bL(\d{3}[A-Z]?)\b/g, 'L $1').replace(/\b(BT)\s*(\d)\.?(\d{2})\b/gi, 'BT_$2.$3').replace(/\bAmf\.?\s+/gi, 'Amf._').replace(/\bAula\s+Inst\.?/gi, 'Aula_Inst.').replace(/\bsala\s+/gi, '').replace(/\b7\s+Obs\b/gi, '7_Obs').split(/\s+/).filter(Boolean);
    let kind = null, acr = null; const rooms = [];
    const roomWord = (x) => /^(BT_|Amf\._|Aula_|7_Obs)/i.test(x) || /^\d{1,3}[A-Za-z]?$/.test(x) || /^[A-Z]\d{1,2}(\.\d)?$/i.test(x) || /^s\d\.?\d$/i.test(x) || /^H\.?\d{2}$/i.test(x) || /^(P03|EM2)$/i.test(x);
    const isKind = (x) => /^(\d?[CSLP]|L\/P|[CSLP]\/[CSLP])$/.test(x);
    const ai = tk.findIndex((x) => /^[A-Za-zĂÂÎȘȚ][A-Za-zĂÂÎȘȚ]{1,9}\d?\.?$/.test(x) && !roomWord(x) && !isKind(x) && !/^(Dor|OBS|Obs|sala|amf)\.?$/i.test(x));
    if (ai >= 0) acr = tk[ai].replace(/\.$/, '').toUpperCase();
    const ki2 = tk.findIndex((x, i) => i > ai && isKind(x));
    const kIdx = ki2 >= 0 ? ki2 : tk.findIndex((x, i) => i !== ai && isKind(x) && !(tk[i + 1] && /^\d{2}$/.test(tk[i + 1])));
    if (kIdx >= 0) { kind = tk[kIdx].replace(/\d/g, '')[0].toUpperCase(); const h = /^(\d)/.exec(tk[kIdx]); if (h) out.hours = +h[1]; }
    tk.forEach((x, i) => { if (i === ai || i === kIdx) return; if (/^(Dor\.?|OBS|Obs)$/i.test(x)) return; rooms.push(x.replace(/_/g, ' ')); });
    // "C 13" -> "C13"
    for (let i = 0; i < rooms.length - 1; i++) if (/^[A-Z]$/.test(rooms[i]) && /^\d{2}$/.test(rooms[i + 1])) { rooms.splice(i, 2, rooms[i] + rooms[i + 1]); }
    if (acr === 'FIZICA') acr = 'FIZ';
    if (acr === 'PHYS') acr = 'PH';
    out.a = acr; out.k = kind || 'L';
    out.r = normRoom(rooms.join(' '));
    return;
  }
  // glue "L192" -> "L 192", "2C(" etc
  const b2 = body.replace(/\bL(\d{3}[A-Z]?)\b/g, 'L $1').replace(/(\d[CSLP])(?=[A-Z(])/g, '$1 ').replace(/\b(ML|SSTR|SI)(\d)([LCSP])\b/g, '$1 $2$3');
  const toks = b2.split(' ').filter(Boolean);
  // find kind token
  let ki = toks.findIndex((x, i) => i > 0 && /^(\d?[CSLP]|[CSLP]\/[CSLP]|L\/P|\dC\/?|\d[CS]\/)$/.test(x));
  if (ki < 0 && toks.length >= 1 && /^(\d?[CSLP])$/.test(toks[0])) ki = 0;
  let acrIdx = -1;
  if (ki > 0) acrIdx = ki - 1;
  const isAcr = (x) => /^[A-Z][A-Za-z]{0,7}\d?(\.?\d)?$/.test(x) && /[A-Z]{2,}|^[A-Z][a-z]?$|^[A-Z]+[a-z]?$/.test(x) && x.length <= 8 && !/^(BT|Amf|H\d+|[A-Z]\d+|I{1,3}|IV)$/.test(x);
  if (acrIdx >= 0 && !isAcr(toks[acrIdx])) {
    // "Analiza si sinteza ... ASDN D03" (no kind token) – look back for an acronym
    acrIdx = -1;
  }
  if (ki < 0) {
    // no kind token: course written as "Title ACR room (prof)" or bare "ACR room"
    const ai = toks.findIndex((x, i) => isAcr(x) && x.length >= 2 && /^[A-Z]{2,}[0-9]?$/.test(x) && (i > 0 || toks.length <= 3));
    if (ai >= 0) acrIdx = ai;
  }
  let kind = ki >= 0 ? toks[ki].replace(/\d/g, '').replace(/\/.*/, '')[0] : null;
  if (ki >= 0) { const hh = /^(\d)/.exec(toks[ki]); if (hh) out.hours = +hh[1]; }
  let title = null, rest = [];
  if (acrIdx >= 0) {
    out.a = toks[acrIdx].toUpperCase().replace(/^PHYS\.?$/, 'PHYS');
    if (acrIdx > 0) title = toks.slice(0, acrIdx).join(' ');
    rest = toks.slice((ki >= 0 ? ki : acrIdx) + 1);
  } else if (ki > 0) {
    title = toks.slice(0, ki).join(' ');
    rest = toks.slice(ki + 1);
  } else {
    rest = toks.slice(0);
    if (rest.length && /^[A-Za-z]{2,}$/.test(rest[0]) && rest.length <= 3) { out.a = rest.shift().toUpperCase(); }
  }
  if (title && /^[A-Z]{2,6}$/.test(title) && !out.a) { out.a = title; title = null; }
  if (title) {
    title = title.replace(/\s*[-–]\s*$/, '').trim();
    if (title.length > 2) out.t = title;
  }
  if (!kind) {
    if (title && title.split(' ').length >= 2) kind = 'C';
    else kind = 'L';
  }
  out.k = kind;
  // room = remaining tokens
  const roomToks = rest.filter((x) => !/^[-–:,;]$/.test(x) && !/^(fac\.?|Dor\.?|2C|C|S|L|P)$/i.test(x));
  let room = roomToks.join(' ').replace(/^[-–]\s*/, '').trim();
  room = room.replace(/^(sala|amf\.)\s*/i, (m) => /amf/i.test(m) ? 'Amf. ' : '');
  if (room.length > 18) room = room.split(' ').slice(0, 2).join(' ');
  out.r = normRoom(room);
  if (out.a === 'FIZICA') { out.a = 'FIZ'; }
  if (out.a === 'PHYS') { out.a = 'PH'; }
}

// ---------------- Calculatoare notation ----------------
const CALC_TAG = /\(\s*(s|p|l|c\s*\+\s*s|l\s*\+\s*p|c\s*\+\s*p|curs|seminar|lab)\s*\)/i;
export function calcIsLong(t) {
  const s = t.replace(CALC_TAG, ' ').trim();
  const segs = s.split(/\s+[-–]\s*|\s*[-–]\s+/).filter(Boolean);
  const w0 = segs[0] ? segs[0].replace(/\([^)]*\)/g, '').trim().split(/\s+/).filter(Boolean).length : 0;
  if (/\([A-Za-z][A-Za-z0-9]{0,8}\)/.test(s) && (s.split('(')[0].trim().split(/\s+/).length >= 2 || /\([A-Z]{2,7}\)/.test(s) && s.split('(')[0].trim().length > 6)) return true;
  if (segs.length >= 3) return true;
  if (segs.length === 2 && w0 >= 2) return true;
  if (/^(psiholog|educational|managementul|didactic|intr|introduction|autonomous|dezvoltare|marketing|personal|etica|limba|germana|franceza|english)/i.test(s) && s.split(/\s+/).length >= 2) return true;
  return false;
}
function parseCalc(t, out) {
  let s = t.trim().replace(/\s+/g, ' ').replace(/\s*-\s*optional\s*-?\s*$/i, ' (optional)').replace(/\s*-\s*$/, '');
  const kt = CALC_TAG.exec(s);
  const tagKind = kt ? ({ s: 'S', seminar: 'S', p: 'P', l: 'L', lab: 'L', curs: 'C' }[kt[1].toLowerCase().replace(/\s/g, '')] || (/^c/i.test(kt[1]) ? 'C' : 'L')) : null;
  if (/^(limbi\s+str|limbi$|foreign)/i.test(s) || /^FL\b/.test(s)) {
    out.a = 'LS'; out.t = /^foreign|^FL/i.test(s) ? 'Foreign languages' : 'Limbi străine'; out.k = 'S';
    const lm = /\((german[aă]|franc\w*|engl\w*)\)/i.exec(s);
    if (lm) out.t += ` (${lm[1].toLowerCase()})`;
    let r = s.replace(/^(limbi?\s+str[aă]ine|foreign languages|FL)\s*/i, '').replace(CALC_TAG, ' ').replace(/\([^)]*\)/g, ' ').replace(/^[\s-–]+/, '').trim();
    r = r.replace(/english|german/ig, ' ').split(/\s*\/\s*/)[0].trim();
    out.r = normRoom(r.replace(/^BT\.?\s?(\d)(\d{2})$/i, 'BT $1.$2'));
    return;
  }
  if (/didact/i.test(s)) {
    out.a = 'DS'; out.t = 'Didactica specialității'; out.k = tagKind || (/seminar|\(s\)/i.test(s) ? 'S' : 'C'); out.opt = 'ped';
    const r = /(\d{3})\s*(\(turn\))?/.exec(s); if (r) out.r = r[1] + (r[2] ? ' (turn)' : '');
    const pm = /[-–]\s*([A-Z]\.\s?[A-ZĂÂÎȘȚ][a-zăâîșț]+)/.exec(s); if (pm) out.prof = pm[1];
    return;
  }
  s = s.replace(/\((optional|opt)\)/gi, ' ').replace(/\s+/g, ' ').trim();
  if (calcIsLong(s)) {
    const segs = s.split(/\s+[-–]\s*|\s*[-–]\s+/).map((x) => x.trim()).filter(Boolean);
    let head = segs[0];
    const am = /\(([A-Za-z][A-Za-z0-9]{0,8})\)/.exec(head);
    if (am && !/^(s|p|l|curs|opt|fac|seminar)$/i.test(am[1])) { out.a = am[1].toUpperCase(); head = head.replace(am[0], ' ').trim(); }
    head = head.replace(CALC_TAG, ' ').replace(/\((fac\.?|opt|optional|c\+s|c \+ s)\)/ig, ' ').replace(/\s+/g, ' ').trim();
    out.t = head;
    let room = null, prof = null;
    const tail = segs.slice(1).map((x) => x.replace(/\((?:opt|optional|fac\.?|cu anul[^)]*|sapt[^)]*)\)/gi, '').replace(CALC_TAG, ' ').replace(/^\s*(curs|seminar)\b/i, ' ').trim()).filter(Boolean);
    const ROOM = /^(BT\s?\d\.\d{2}|[A-Z]{1,2}\s?\d{1,3}[A-Za-z]?|\d{2,3}[A-Za-z]?(\s*\(turn\))?|Aula Inst\w*\.?|F|P03|EM\s?2|S\d\.\d)$/i;
    if (tail.length) {
      const last = tail[tail.length - 1];
      if (ROOM.test(last)) { room = last; prof = tail.slice(0, -1).join(', ') || null; }
      else {
        const m2 = /^(.*?)\s+(BT\s?\d\.\d{2}|[A-Z]{1,2}\d{1,3}|\d{2,3}[A-Za-z]?)$/.exec(last);
        if (m2) { room = m2[2]; prof = [...tail.slice(0, -1), m2[1]].join(', ') || null; }
        else if (/^[A-Z]\.?\s?[A-Z]?[a-z]/.test(last) || /\./.test(last)) prof = tail.join(', ');
        else room = last;
      }
    } else {
      const m4 = /\s(BT\s?\d\.\d{2}|[A-Z]\d{2}|\d{2,3}[A-Za-z]?)\s*$/.exec(head);
      if (m4) { room = m4[1]; out.t = head.replace(m4[0], '').trim(); }
    }
    out.r = normRoom(room);
    if (prof && /[a-z]/i.test(prof) && !/^(fac|opt)/i.test(prof)) out.prof = prof;
    out.k = tagKind || 'C';
    if (/limb|englez|franc|german|english|french/i.test(out.t || '')) { out.k = 'S'; out.a = out.a || 'LS'; }
    if (!out.a) out.a = (out.t || '').split(/\s+/).filter((w) => /^[A-Za-zĂÂÎȘȚăâîșț]/.test(w) && w.length > 2).map((w) => w[0].toUpperCase()).join('').slice(0, 6) || null;
    return;
  }
  // short: "PL 204", "AM (s) - BT 5.02", "Fizica(L) 192", "PT (p) 206", "SSC p 108", "OSD (L) 106", "Alg (L+P) - M3"
  s = s.replace(CALC_TAG, ' ').replace(/\s+/g, ' ').trim();
  const tk = s.split(' ').filter((x) => x && x !== '-' && x !== '–');
  let acr = tk.shift() || '';
  let kind = tagKind;
  if (tk.length && /^[psL]$/.test(tk[0])) { const k = tk.shift(); kind = kind || { p: 'P', s: 'S', L: 'L' }[k]; }
  acr = acr.replace(/[.\-]+$/, '');
  if (/^fizica$/i.test(acr)) acr = 'F';
  if (/^phys$/i.test(acr)) acr = 'P';
  out.a = acr.toUpperCase();
  out.k = kind || 'L';
  let room = tk.join(' ').replace(/\((?:recontractare|opt)\)/gi, '').replace(/^[-–]\s*/, '').trim();
  room = room.replace(/^BT\.?(\d)\.?(\d{2})$/i, 'BT $1.$2');
  out.r = normRoom(room.split(' ').slice(0, /^BT/i.test(room) || /\(turn\)/.test(room) ? 2 : 1).join(' '));
  if (/recontractare/i.test(t)) out.note = 'recontractare';
}
