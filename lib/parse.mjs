// Generic timetable parser for UTCN Excel timetables (AC faculty: Automatică dept + Calculatoare dept).
// Input: a sheet model from sheet.mjs. Output: { groups, entries, notes, warnings }.
import { parseText } from './text.mjs';

const DAY_RE = [
  [/^(luni|monday|mon)\b/i, 0],
  [/^(mar[tţț]i|tuesday|tue)\b/i, 1],
  [/^(miercuri|mierc\.?|miercuri|wednesday|wed)/i, 2],
  [/^(joi|thursday|thu)\b/i, 3],
  [/^(vineri|friday|fri)\b/i, 4],
];
const dayOf = (t) => { const s = t.trim(); for (const [re, d] of DAY_RE) if (re.test(s)) return d; return null; };
const TIME_RE = /^\s*0?(\d{1,2})\s*[:.]?\s*(?:00)?\s*-\s*0?(\d{1,2})\s*[:.]?\s*(?:00)?\s*$/;
const timeOf = (t) => { const m = TIME_RE.exec(t.replace(/\s+/g, ' ')); if (!m) return null; const s = +m[1], e = +m[2]; if (s < 7 || s > 22 || e <= s || e > 23) return null; return [s, e]; };
const GROUP_RE = /^(3\d{4,5})(?:\.0)?(?:\s*(.*))?$/;
const SG_RE = /^([12])(?:\.0)?$/;

export function analyzeSheet(model, cfg) {
  const warnings = [];
  const B = model.boxes;
  // --- axis: days & times
  const dayBoxes = B.filter((b) => dayOf(b.text) != null && b.text.length < 14);
  if (!dayBoxes.length) return { groups: [], entries: [], notes: [], warnings: ['no days'] };
  const dayCol = Math.min(...dayBoxes.map((b) => b.c0));
  const days = dayBoxes.filter((b) => b.c0 === dayCol).map((b) => ({ d: dayOf(b.text), r0: b.r0, r1: b.r1 })).sort((a, b) => a.r0 - b.r0);
  // a day lasts until the next day label (merged day cells are sometimes shorter than the time rows)
  const timeLike = B.filter((b) => timeOf(b.text) && b.c0 > dayCol);
  days.forEach((d, i) => {
    const next = days[i + 1] ? days[i + 1].r0 - 1 : Math.max(d.r1, ...timeLike.filter((t) => t.r0 >= d.r0 && t.r0 <= d.r1 + 4).map((t) => t.r1));
    d.r1 = Math.max(d.r1, next);
  });
  const firstDayRow = Math.min(...days.map((d) => d.r0));
  const lastDayRow = Math.max(...days.map((d) => d.r1));
  const timeBoxesAll = B.filter((b) => timeOf(b.text) && b.r0 >= firstDayRow && b.r1 <= lastDayRow && b.c0 !== dayCol);
  const tcols = [...new Set(timeBoxesAll.map((b) => b.c0))].sort((a, b) => Math.abs(a - dayCol) - Math.abs(b - dayCol));
  const timeCol = tcols[0];
  const axisCols = new Set([dayCol, ...tcols, ...dayBoxes.map((b) => b.c0)]);
  const times = timeBoxesAll.filter((b) => b.c0 === timeCol).map((b) => { const [s, e] = timeOf(b.text); return { s, e, r0: b.r0, r1: b.r1 }; });
  const rowInfo = new Map(); // row -> {d, slot}
  for (const t of times) {
    const d = days.find((x) => t.r0 >= x.r0 && t.r0 <= x.r1);
    if (!d) continue;
    for (let r = t.r0; r <= t.r1; r++) rowInfo.set(r, { d: d.d, slot: t });
  }
  // --- header: groups and semigroups
  const header = B.filter((b) => b.r1 < firstDayRow && !axisCols.has(b.c0));
  const gBoxes = header.filter((b) => GROUP_RE.test(b.text.replace(/\s+/g, ' ')));
  const groups = [];
  const seenIds = new Map();
  for (const b of gBoxes.sort((a, b) => a.c0 - b.c0)) {
    const m = GROUP_RE.exec(b.text.replace(/\s+/g, ' '));
    let id = m[1];
    const n = (seenIds.get(id) || 0) + 1; seenIds.set(id, n);
    const key = n > 1 ? `${id}_${n}` : id;
    groups.push({ key, code: id, tag: (m[2] || '').replace(/[()]/g, '').trim(), c0: b.c0, c1: b.c1, r: b.r1, sgCols: [] });
  }
  // programmes without a group code (master programmes, "Complemente de Știința Calculatoarelor"): pseudo-groups
  {
    const covered = (c) => groups.some((g) => c >= g.c0 && c <= g.c1);
    const isTitle = (b) => /orar|schedule|semestr|an universitar|academic year|master an|^\s*an \d/i.test(b.text) || (b.c1 - b.c0 + 1) > model.nCols * 0.6;
    const contentCols = new Set();
    for (const b of B) if (b.r0 >= firstDayRow && b.r1 <= lastDayRow && !axisCols.has(b.c0) && b.text && !timeOf(b.text) && dayOf(b.text) == null) for (let c = b.c0; c <= b.c1; c++) contentCols.add(c);
    const heads = header.filter((b) => !isTitle(b) && !SG_RE.test(b.text) && !GROUP_RE.test(b.text) && b.text.length > 3 && !/restan|recontract|discipline op|comune cu|responsabil/i.test(b.text));
    const made = new Map();
    for (const c of [...contentCols].sort((a, b) => a - b)) {
      if (covered(c) || axisCols.has(c) || !cfg.allowPseudo) continue;
      const hs = heads.filter((h) => c >= h.c0 && c <= h.c1).sort((a, b) => a.r0 - b.r0);
      if (!hs.length) continue;
      const top = hs[0];
      const k = top.addr;
      if (!made.has(k)) {
        const label = hs.map((h) => h.text).join(' ').replace(/\(facultativ\)/i, '').replace(/\s+/g, ' ').trim();
        const abbr = label.split(/\s+/).filter((w) => /^[A-ZĂÂÎȘȚ]/.test(w)).map((w) => w[0]).join('').slice(0, 6) || 'P';
        made.set(k, { key: `${cfg.sheetKey || model.name.trim()}-${abbr}`, code: null, tag: '', label, c0: c, c1: c, r: top.r1, sgCols: [], pseudo: true });
      }
      const g = made.get(k); g.c0 = Math.min(g.c0, c); g.c1 = Math.max(g.c1, c);
    }
    for (const g of made.values()) { g.sgCols = [{ sg: 1, c0: g.c0, c1: g.c1 }]; groups.push(g); }
    groups.sort((a, b) => a.c0 - b.c0);
  }
  if (!groups.length) return { groups: [], entries: [], notes: [], warnings: ['no groups'] };
  const mergedDup = [];
  for (let i = groups.length - 1; i > 0; i--) {
    const a = groups[i - 1], b = groups[i];
    if (a.code && a.code === b.code && b.c0 === a.c1 + 1) { a.c1 = b.c1; a.dupMerged = true; mergedDup.push(a.code); groups.splice(i, 1); }
  }
  // ignore groups right of a second time axis (duplicated right block)
  const rightTime = timeBoxesAll.filter((b) => b.c0 > timeCol + 1).map((b) => b.c0);
  const sgBoxes = header.filter((b) => SG_RE.test(b.text));
  for (const g of groups) {
    if (g.pseudo) { g.sgs = [1]; g.section = ''; continue; }
    const sgs = sgBoxes.filter((b) => b.r0 > g.r - 1 && b.c0 >= g.c0 && b.c1 <= g.c1);
    if (g.dupMerged && sgs.length === 2) { g.sgCols = sgs.sort((a, b) => a.c0 - b.c0).map((x, i) => ({ sg: i + 1, c0: x.c0, c1: x.c1 })); }
    else if (sgs.length) {
      for (const s of sgs) g.sgCols.push({ sg: +SG_RE.exec(s.text)[1], c0: s.c0, c1: s.c1 });
      // extend: columns of the group not covered by any sg box go to the nearest sg on the left
      for (let c = g.c0; c <= g.c1; c++) {
        if (!g.sgCols.some((s) => c >= s.c0 && c <= s.c1)) {
          const left = g.sgCols.filter((s) => s.c1 < c).sort((a, b) => b.c1 - a.c1)[0] || g.sgCols[0];
          left.c1 = Math.max(left.c1, c); left.c0 = Math.min(left.c0, c);
        }
      }
    } else g.sgCols.push({ sg: 1, c0: g.c0, c1: g.c1, inferred: true });
    // duplicated sg numbers (e.g. two "2"): keep distinct by order
    const uniq = [...new Set(g.sgCols.map((s) => s.sg))];
    g.sgs = uniq.sort();
    // section label = header box above covering the group
    const above = header.filter((b) => b.r1 < g.r && b.c0 <= g.c0 && b.c1 >= g.c1 && !GROUP_RE.test(b.text) && b.c1 - b.c0 < 60 && !/orar|schedule|year|an universitar|academic|\d{2}\.\d{2}\.\d{4}|^=|master an/i.test(b.text));
    g.section = above.sort((a, b) => b.r1 - a.r1)[0]?.text || '';
  }
  // groups without semigroup labels: if siblings are split in two 2-column semigroups and this group is as wide, split it too
  const twoSg = groups.filter((g) => !g.sgCols[0].inferred && g.sgCols.length === 2);
  for (const g of groups) {
    if (!g.sgCols[0].inferred) continue;
    const w = g.c1 - g.c0 + 1;
    if (/2\s*semigrup/i.test(g.tag) && w >= 2) { const h = Math.floor(w / 2); g.sgCols = [{ sg: 1, c0: g.c0, c1: g.c0 + h - 1 }, { sg: 2, c0: g.c0 + h, c1: g.c1 }]; g.sgs = [1, 2]; }
  }
  for (const g of groups) {
    if (!g.sgCols[0].inferred) continue;
    const w = g.c1 - g.c0 + 1;
    if (twoSg.length && twoSg.length >= groups.length / 2 && twoSg.some((x) => x.c1 - x.c0 + 1 === w) && w % 2 === 0) {
      g.sgCols = [{ sg: 1, c0: g.c0, c1: g.c0 + w / 2 - 1 }, { sg: 2, c0: g.c0 + w / 2, c1: g.c1 }];
      g.sgs = [1, 2];
    }
  }
  const colUnit = new Map(); // col -> {group, sg}
  for (const g of groups) for (const s of g.sgCols) for (let c = s.c0; c <= s.c1; c++) colUnit.set(c, { g, sg: s.sg });
  const minGC = Math.min(...groups.map((g) => g.c0)), maxGC = Math.max(...groups.map((g) => g.c1));

  // --- content boxes
  const content = B.filter((b) => rowInfo.has(b.r0) && b.c1 >= minGC && b.c0 <= maxGC && !axisCols.has(b.c0) && !(timeOf(b.text) || dayOf(b.text) != null && b.text.length < 14));
  const isBlank = (t) => !t || /^[\s`'´.,\-–/|*]*$/.test(t);
  const diag = content.filter((b) => b.dUp);
  const texts = content.filter((b) => !isBlank(b.text));

  // --- diagonal blocks (Automatică layout): chain diag segments going up-right
  const used = new Set();
  const blocks = [];
  if (cfg.diagonals) {
    const segs = [...diag].sort((a, b) => a.c0 - b.c0 || b.r1 - a.r1);
    const taken = new Set();
    for (const s of segs) {
      if (taken.has(s)) continue;
      const chain = [s]; taken.add(s);
      let cur = s;
      for (;;) {
        const day = rowInfo.get(cur.r0).d;
        const ucur = colUnit.get(cur.c0);
        const nxt = segs.find((n) => {
          if (taken.has(n) || !(n.c0 > cur.c1 && n.c0 <= cur.c1 + 2 && n.r1 < cur.r0 && n.r1 >= cur.r0 - 2)) return false;
          if (rowInfo.get(n.r0)?.d !== day) return false;
          const un = colUnit.get(n.c0);
          if (!un || !ucur || un.g !== ucur.g) return false; // never across groups
          // across semigroups only inside one time slot (whole-group block)
          const curSg = ucur.g.sgCols.find((x) => x.sg === ucur.sg && cur.c0 >= x.c0 && cur.c0 <= x.c1);
          if (un.sg !== ucur.sg || n.c0 > curSg.c1) {
            const fullWidth = cur.c0 <= curSg.c0 && cur.c1 >= curSg.c1;
            const sameSize = n.c1 - n.c0 === cur.c1 - cur.c0 && n.r1 - n.r0 === cur.r1 - cur.r0;
            if (!sameSize) return false;
            if (!fullWidth && rowInfo.get(n.r0).slot !== rowInfo.get(chain[0].r1).slot) return false;
          }
          return true;
        });
        if (!nxt) break;
        chain.push(nxt); taken.add(nxt); cur = nxt;
      }
      let r0 = Math.min(...chain.map((x) => x.r0)), r1 = Math.max(...chain.map((x) => x.r1));
      let c0 = Math.min(...chain.map((x) => x.c0)), c1 = Math.max(...chain.map((x) => x.c1));
      // snap rows to slots
      r0 = rowInfo.get(r0).slot.r0; r1 = rowInfo.get(r1).slot.r1;
      // snap columns to semigroup units
      const u0 = colUnit.get(c0), u1 = colUnit.get(c1);
      if (!u0 || !u1) { warnings.push(`diag outside groups ${s.addr}`); continue; }
      c0 = u0.g.sgCols.find((x) => x.sg === u0.sg && c0 >= x.c0 && c0 <= x.c1).c0;
      c1 = u1.g.sgCols.find((x) => x.sg === u1.sg && c1 >= x.c0 && c1 <= x.c1).c1;
      blocks.push({ r0, r1, c0, c1, chain, ul: [], lr: [] });
    }
    for (const bl of blocks) {
      const H = bl.r1 - bl.r0 + 1, W = bl.c1 - bl.c0 + 1;
      for (const t of texts) {
        if (used.has(t)) continue;
        if (t.r0 < bl.r0 || t.r1 > bl.r1 || t.c0 < bl.c0 || t.c1 > bl.c1) continue;
        used.add(t);
        let side;
        const gap = t.dUp && /\S\s{4,}\S/.test(t.rawText || '') ? (t.rawText || '').trim().split(/\s{4,}/) : null;
        if (gap && gap.length === 2) {
          bl.ul.push({ ...t, text: gap[0].replace(/\s+/g, ' ').trim(), dUp: false });
          bl.lr.push({ ...t, text: gap[1].replace(/\s+/g, ' ').trim(), dUp: false });
          continue;
        }
        if (t.dUp) side = t.align === 'right' ? 'lr' : 'ul';
        else {
          const cx = (t.c0 + t.c1 + 1) / 2 - bl.c0, cy = (t.r0 + t.r1 + 1) / 2 - bl.r0;
          const lineY = H - (cx / W) * H; // y of diagonal at cx (0 = top)
          side = cy < lineY ? 'ul' : 'lr';
        }
        bl[side].push(t);
      }
    }
  }

  // --- units for a column span
  function unitsFor(c0, c1) {
    const map = new Map();
    for (let c = c0; c <= c1; c++) {
      const u = colUnit.get(c); if (!u) continue;
      if (!map.has(u.g.key)) map.set(u.g.key, { g: u.g, sgs: new Set() });
      map.get(u.g.key).sgs.add(u.sg);
    }
    return [...map.values()].map((x) => ({ g: x.g, sgs: [...x.sgs].sort() }));
  }
  const entries = [];
  function mkEntry(u, d, s, e, parity, info, raw, src, extra = {}) {
    return {
      g: u.g.key, sg: u.sgs, all: u.sgs.length === u.g.sgs.length,
      d, s, e, p: info.p || parity, w: info.w || null,
      k: info.k, a: info.a, t: info.t, r: info.r, prof: info.prof, opt: info.opt, lang: info.lang, note: info.note,
      raw, src: `${model.name}!${src}`, cx: info.complex || undefined, ...extra,
    };
  }
  function emit(textParts, r0, r1, c0, c1, parity, src, extra = {}) {
    const raw = textParts.map((t) => t.text).join(' ').replace(/\s+/g, ' ').trim();
    if (isBlank(raw)) return;
    const ri0 = rowInfo.get(r0), ri1 = rowInfo.get(r1);
    const base = { d: ri0.d, s: ri0.slot.s, e: ri1.slot.e };
    const units = unitsFor(c0, c1);
    if (!units.length) return;
    let pieces = cfg.slashParity && parity === 'all' ? splitSlash(raw) : [{ text: raw, p: parity }];
    // "A - room ; B - room ; C - room": alternatives (optional courses) in one cell
    pieces = pieces.flatMap((pc) => pc.text.includes(' ; ') ? pc.text.split(/\s*;\s*/).filter(Boolean).map((x) => ({ ...pc, text: x, choice: true })) : [pc]);
    // a parity piece without a subject inherits it from its sibling ("Instr. asistata de calc.(fac) - curs 356 / (seminar) 356")
    if (pieces.length === 2 && /^\(/.test(pieces[1].text.trim())) { const head = pieces[0].text.split(/\s+[-–]\s+/)[0]; pieces[1].text = head + ' - ' + pieces[1].text; }
    pieces.forEach((pc, i) => {
      const info = parseText(pc.text, cfg);
      let us = units;
      // a lab/project spanning both semigroups of ONE group, written as "X / X": sg1 odd, sg2 even
      if (pc.alt && units.length === 1 && units[0].sgs.length === 2 && ['L', 'P'].includes(info.k)) {
        us = [{ g: units[0].g, sgs: [pc.p === 'odd' ? 1 : 2] }];
      }
      const s = info.s ?? base.s;
      const e = info.e ?? (info.dur ? s + info.dur : base.e);
      if (info.hours && info.hours < base.e - base.s && info.s == null) info.note = [info.note, `${info.hours}h din intervalul ${base.s}–${base.e}`].filter(Boolean).join('; ');
      for (const u of us) entries.push(mkEntry(u, base.d, s, e, pc.p, info, pc.text, src, { choice: pc.choice || undefined, ...extra }));
    });
  }
  // diag blocks: each half may hold several activities (e.g. "SCD 2P 310" 8-10 and "SCPC 2P 304" 10-12)
  const startsItem = (txt) => {
    const tok = txt.trim().split(/\s+/)[0] || '';
    if (/^(spt|sapt|săpt|st|in|intre|between|sala|amf|aula)\b/i.test(txt.trim())) return false;
    if (/^(BT|H\.?\d|S\d|P0\d|[A-Z]\d{1,3}[A-Z]?$|\d)/i.test(tok)) return false;
    return /^[A-Za-zĂÂÎȘȚ]{2,}/.test(tok);
  };
  for (const bl of blocks) {
    const both = bl.ul.length && bl.lr.length;
    const units = unitsFor(bl.c0, bl.c1);
    const bs = rowInfo.get(bl.r0).slot.s, be = rowInfo.get(bl.r1).slot.e;
    for (const side of ['ul', 'lr']) {
      const parts = bl[side].sort((a, b) => a.r0 - b.r0 || a.c0 - b.c0);
      if (!parts.length) continue;
      const parity = side === 'ul' ? 'odd' : 'even';
      const items = []; const pending = [];
      for (const p of parts) {
        if (startsItem(p.text) || !items.length && !pending.length && parts.length === 1) items.push({ parts: [...pending.splice(0), p], head: p });
        else if (items.length) items[items.length - 1].parts.push(p);
        else pending.push(p);
      }
      if (pending.length) { if (items.length) items[0].parts.unshift(...pending); else items.push({ parts: pending, head: pending[0] }); }
      for (const it of items) {
        const raw = it.parts.map((p) => p.text).join(' ').replace(/\s+/g, ' ').trim();
        const info = parseText(raw, cfg);
        let s = bs, e = be;
        if (info.s != null) { s = info.s; e = info.e; }
        else if (items.length > 1 || (info.hours && info.hours < be - bs)) {
          const cr = Math.round((it.head.r0 + it.head.r1) / 2);
          const sl = (rowInfo.get(cr) || rowInfo.get(it.head.r0)).slot;
          const dur = info.hours && info.hours <= be - bs ? info.hours : sl.e - sl.s;
          s = sl.s; e = s + dur;
          if (e > be) { e = be; s = Math.max(bs, be - dur); }
        } else if (info.dur) e = s + info.dur;
        let c0 = bl.c0, c1 = bl.c1;
        if (both && units.length === 1 && units[0].sgs.length === 2 && (info.k === 'L' || info.k === 'P')) {
          const sc = units[0].g.sgCols.find((x) => x.sg === (side === 'ul' ? 1 : 2));
          c0 = sc.c0; c1 = sc.c1;
        }
        for (const u of unitsFor(c0, c1)) entries.push(mkEntry(u, rowInfo.get(bl.r0).d, s, e, parity, info, raw, it.parts.map((p) => p.addr).join('+'), { blk: true }));
      }
    }
  }
  // remaining text boxes: merge fragments inside the same slot & same column span
  const rest = texts.filter((t) => !used.has(t));
  const bucket = new Map();
  for (const t of rest) {
    const ri = rowInfo.get(t.r0); const ri1 = rowInfo.get(t.r1);
    if (!ri || !ri1) continue;
    const k = `${ri.slot.r0}:${ri1.slot.r1}:${t.c0}:${t.c1}`;
    if (!bucket.has(k)) bucket.set(k, []);
    bucket.get(k).push(t);
  }
  const frags = [];
  for (const [k, arr] of bucket) {
    arr.sort((a, b) => a.r0 - b.r0);
    const [sr0, sr1] = k.split(':').map(Number);
    frags.push({ parts: arr, r0: sr0, r1: sr1, c0: arr[0].c0, c1: arr[0].c1 });
  }
  // attach room-only / type-only fragments to a neighbour in the same slot that lacks a room
  const lone = (f) => !/[A-Za-zĂÂÎȘȚăâîșț]{2,}/.test(f.parts.map((p) => p.text).join(' ').replace(/\b(BT|bt|amf|Amf|sala|s|S|L|P|C|Dor|OBS|Obs)\b\.?/g, ''));
  for (const f of frags) {
    if (!lone(f) || f.done) continue;
    const cand = frags.filter((o) => o !== f && !o.done && !lone(o) && o.r0 === f.r0 && o.r1 === f.r1 && Math.abs(o.c0 - f.c1) <= 1 + (f.c1 - f.c0) && (o.c1 >= f.c0 - 1 && o.c0 <= f.c1 + 1));
    if (cand.length === 1) { cand[0].parts.push(...f.parts); f.done = true; cand[0].c0 = Math.min(cand[0].c0, f.c0); cand[0].c1 = Math.max(cand[0].c1, f.c1); }
  }
  for (const f of frags) {
    if (f.done) continue;
    // a slot made of two row-halves: keep the box's own rows if it does not cover the full slot
    emit(f.parts, f.r0, f.r1, f.c0, f.c1, 'all', f.parts.map((p) => p.addr).join('+'));
  }
  // --- orphan room-only entries: attach to the activity right above in the same group/semigroup
  const roomOnly = (e) => !e.a && !e.t && /^[A-Za-z]{0,2}\s?\d[\d.]*[A-Za-z]?$|^BT\s?\d/.test(e.raw.trim());
  for (const o of entries.filter(roomOnly)) {
    const host = entries.find((e) => e !== o && !roomOnly(e) && e.g === o.g && e.d === o.d && e.sg.some((x) => o.sg.includes(x)) && !e.r && (e.e === o.s || e.s <= o.s && e.e >= o.s));
    if (host) { host.r = o.raw.trim(); host.raw += ' ' + o.raw; o.drop = true; }
  }
  for (let i = entries.length - 1; i >= 0; i--) if (entries[i].drop) entries.splice(i, 1);
  // --- notes: footer text below the grid
  const notes = B.filter((b) => b.r0 > lastDayRow && b.text.length > 25 && !/^https?:|link varianta|responsabil|forms\./i.test(b.text)).map((b) => b.text);
  return {
    groups: groups.map((g) => ({ key: g.key, code: g.code, tag: g.tag, section: g.section, sgs: g.sgs, label: g.label || null, pseudo: !!g.pseudo })),
    entries, notes: mergedDup.length ? [...notes, ...mergedDup.map((c) => `dupgroup:${c}`)] : notes, warnings,
  };
}

// CALC notation: "A / B" -> A odd, B even ; "A /" -> odd ; "/ B" -> even
function splitSlash(raw) {
  const t = raw.trim();
  if (!t.includes('/')) return [{ text: t, p: 'all' }];
  // slashes that are part of names ("L+P", "C/S", "1C / 1S", English/German) are not parity markers
  const parts = t.split(/\s*\/\s*/);
  if (/\b\d[CS]\s*\/\s*\d[CS]\b/.test(t)) return [{ text: t, p: 'all' }];
  if (/^\//.test(t) && parts.filter(Boolean).length === 1) return [{ text: parts.filter(Boolean)[0], p: 'even' }];
  if (/\/$/.test(t) && parts.filter(Boolean).length === 1) return [{ text: parts.filter(Boolean)[0], p: 'odd' }];
  const nonEmpty = parts.filter((x) => x.trim());
  if (nonEmpty.length === 2 && parts.length === 2) {
    const [a, b] = nonEmpty;
    const lang = (x) => /(engl|franc|german|limb|english|french)/i.test(x);
    if (lang(a) && lang(b)) return [{ text: a, p: 'all', choice: true }, { text: b, p: 'all', choice: true }];
    return [{ text: a, p: 'odd', alt: a.replace(/\s/g, '') === b.replace(/\s/g, '') }, { text: b, p: 'even', alt: a.replace(/\s/g, '') === b.replace(/\s/g, '') }];
  }
  if (nonEmpty.length === 2) return [{ text: nonEmpty[0], p: 'odd' }, { text: nonEmpty[1], p: 'even' }];
  return [{ text: t, p: 'all' }];
}
