// Generic sheet model: visible cells (print area, hidden rows/cols removed) as boxes.
// A box = one master cell (merged range or single cell) clipped to the visible grid.

const colToNum = (s) => [...s.toUpperCase()].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0);
export const numToCol = (n) => { let s = ''; while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); } return s; };

function parseRange(a) {
  const m = /\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)/.exec(a || '');
  if (!m) return null;
  return { c0: colToNum(m[1]), r0: +m[2], c1: colToNum(m[3]), r1: +m[4] };
}

export function cellText(v) {
  if (v == null) return '';
  if (typeof v === 'object') {
    if (v.richText) return v.richText.map((t) => t.text).join('');
    if (v.text != null) return String(v.text);
    if (v.result != null) return String(v.result);
    if (v.formula) return '';
    if (v instanceof Date) return v.toISOString();
    return '';
  }
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(v);
  return String(v);
}

export function buildModel(ws, opts = {}) {
  let area = parseRange(ws.pageSetup && ws.pageSetup.printArea);
  const dim = { r0: 1, c0: 1, r1: ws.rowCount, c1: ws.columnCount };
  if (!area || opts.ignorePrintArea) area = dim;
  area.r1 = Math.min(area.r1, dim.r1); area.c1 = Math.min(area.c1, dim.c1);
  const visCols = []; const visRows = [];
  for (let c = area.c0; c <= area.c1; c++) if (!ws.getColumn(c).hidden) visCols.push(c);
  for (let r = area.r0; r <= area.r1; r++) if (!ws.getRow(r).hidden) visRows.push(r);
  const colIdx = new Map(visCols.map((c, i) => [c, i]));
  const rowIdx = new Map(visRows.map((r, i) => [r, i]));
  // merged ranges
  const merges = [];
  const mm = ws._merges || {};
  for (const k of Object.keys(mm)) {
    const m = mm[k].model || mm[k];
    merges.push({ r0: m.top, c0: m.left, r1: m.bottom, c1: m.right });
  }
  const masterOf = new Map();
  for (const m of merges) for (let r = m.r0; r <= m.r1; r++) for (let c = m.c0; c <= m.c1; c++) masterOf.set(r * 10000 + c, m);
  const boxes = [];
  const seen = new Set();
  for (const r of visRows) {
    for (const c of visCols) {
      const m = masterOf.get(r * 10000 + c);
      let r0 = r, c0 = c, r1 = r, c1 = c, mr = r, mc = c;
      if (m) { r0 = m.r0; c0 = m.c0; r1 = m.r1; c1 = m.c1; mr = m.r0; mc = m.c0; }
      const key = mr * 10000 + mc;
      if (seen.has(key)) continue;
      seen.add(key);
      // master cell may be hidden: content still shows in visible part of the merge
      const cell = ws.getCell(mr, mc);
      const rawText = cellText(cell.value).replace(/\u00a0/g, ' ');
      const text = rawText.replace(/[ \t]+/g, ' ').trim();
      const diag = cell.border && cell.border.diagonal && cell.border.diagonal.style ? cell.border.diagonal : null;
      const dUp = !!(diag && diag.up), dDown = !!(diag && diag.down);
      if (!text && !dUp && !dDown) continue;
      // clip to visible
      const vr = []; const vc = [];
      for (let rr = r0; rr <= r1; rr++) if (rowIdx.has(rr)) vr.push(rowIdx.get(rr));
      for (let cc = c0; cc <= c1; cc++) if (colIdx.has(cc)) vc.push(colIdx.get(cc));
      if (!vr.length || !vc.length) continue;
      let fill = null;
      try { const f = cell.fill; if (f && f.type === 'pattern' && f.fgColor && f.fgColor.argb) fill = f.fgColor.argb; } catch {}
      boxes.push({
        addr: numToCol(mc) + mr, text, rawText, dUp, dDown, merged: !!m,
        align: (cell.alignment && cell.alignment.horizontal) || null,
        r0: Math.min(...vr), r1: Math.max(...vr), c0: Math.min(...vc), c1: Math.max(...vc),
        fill,
      });
    }
  }
  // Excel shows long text of an unmerged cell over empty neighbours on the right: model that
  const occupied = new Set();
  for (const b of boxes) for (let r = b.r0; r <= b.r1; r++) for (let c = b.c0; c <= b.c1; c++) occupied.add(r * 10000 + c);
  for (const b of boxes) {
    if (b.merged || !b.text || b.text.length < 22 || b.dUp || b.align === 'right' || b.align === 'center') continue;
    let need = b.text.length * 0.95;
    let have = ws.getColumn(visCols[b.c0]).width || 8.43;
    let c = b.c0;
    while (have < need && c + 1 < visCols.length && !occupied.has(b.r0 * 10000 + c + 1)) { c++; have += ws.getColumn(visCols[c]).width || 8.43; }
    if (c > b.c0) { b.overflowTo = c; b.c1 = c; }
  }
  return { name: ws.name, boxes, nRows: visRows.length, nCols: visCols.length, visRows, visCols };
}
