'use strict';
const DATA = /*__DATA__*/;
const R = DATA.results, X = DATA.extras, NET = DATA.network, AUD = DATA.audit, DEMO = DATA.demo;
const CL = ['rules', 'fuzzy', 'ml', 'hybrid'];
const INK = '#0A0A0A', INK2 = '#4A4A4A', INK3 = '#8A8A8A', HAIR = '#D9D9D9', RED = '#E8381B';
const CS = {rules: {name: 'Rules', color: INK3, dash: '1.5 4', w: 2, m: 'sqo'}, fuzzy: {name: 'Fuzzy', color: INK2, dash: '7 4', w: 2, m: 'tri'},
  ml: {name: 'ML', color: INK, dash: '9 3 2 3', w: 2, m: 'dia'}, hybrid: {name: 'Hybrid', color: RED, dash: '', w: 3.4, m: 'cir'}};
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const pct = (x, d = 1) => x == null || isNaN(x) ? '--' : (x * 100).toFixed(d) + '%';
const pts = (x, d = 1) => (x >= 0 ? '+' : '-') + Math.abs(x * 100).toFixed(d);
const num = x => x == null || isNaN(x) ? '--' : Math.round(x).toLocaleString('en-US');
const SYM = {USD: '$', GBP: '£', EUR: '€'};
const money = (v, cur) => (v < 0 ? '-' : '') + (SYM[cur] || '') + Math.abs(Math.round(v)).toLocaleString('en-US');
const CLIENTS = R.dataset.clients, TESTSET = new Set(R.split.test);
const cinfo = id => CLIENTS.find(c => c.client_id === id) || {};
const cname = id => cinfo(id).client_name || id;
const LAYOUT = {qb: 'QuickBooks, grouped by account', xero: 'Xero, flat by account', sage: 'Sage, signed amount', netsuite: 'NetSuite, hierarchical accounts', euro: 'DATEV style, EUR', cashbook: 'Excel cash book'};
const ACCT = Object.fromEntries(DEMO.accounts.map(a => [a[0], a[1]])); ACCT.UNMAPPED = 'Unmapped';
const aname = c => c ? (ACCT[c] || c) : 'Unmapped';
const M = (n, sp) => R.cleaners[n][sp];
const lin = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const heat = (v, lo = .5) => { const a = clamp((1 - v) / (1 - lo), 0, 1) * 0.6; return a < 0.03 ? 'transparent' : `rgba(232,56,26,${a.toFixed(2)})`; };

/* ---- svg primitives ---- */
function mk(t, x, y, c, r = 5) {
  if (t === 'cir') return `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;
  if (t === 'sqo') return `<rect x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" fill="#fff" stroke="${c}" stroke-width="2"/>`;
  if (t === 'tri') return `<path d="M${x} ${y - r * 1.25} L${x + r * 1.15} ${y + r * .85} L${x - r * 1.15} ${y + r * .85}Z" fill="${c}"/>`;
  return `<path d="M${x} ${y - r * 1.3} L${x + r * 1.25} ${y} L${x} ${y + r * 1.3} L${x - r * 1.25} ${y}Z" fill="${c}"/>`;
}
function legendHTML(keys = CL) {
  return '<div class="legend">' + keys.map(k => `<span><svg class="mk" width="26" height="12" viewBox="0 0 26 12" style="display:inline-block;width:26px;height:12px"><line x1="0" y1="6" x2="26" y2="6" stroke="${CS[k].color}" stroke-width="${CS[k].w}" stroke-dasharray="${CS[k].dash}"/>${mk(CS[k].m, 13, 6, CS[k].color, 4)}</svg>${CS[k].name}</span>`).join('') + '</div>';
}
function plot(o) {
  const w = o.w || 720, h = o.h || 320, m = Object.assign({l: 58, r: o.endLabels ? 96 : 20, t: 12, b: 46}, o.m || {});
  const x = lin(o.xd[0], o.xd[1], m.l, w - m.r), y = lin(o.yd[0], o.yd[1], h - m.b, m.t);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(o.aria || 'chart')}">`;
  (o.yt || []).forEach(t => s += `<line x1="${m.l}" x2="${w - m.r}" y1="${y(t)}" y2="${y(t)}" stroke="#EDEDED"/><text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end">${o.yf(t)}</text>`);
  (o.xt || []).forEach(t => s += `<line x1="${x(t)}" x2="${x(t)}" y1="${h - m.b}" y2="${h - m.b + 5}" stroke="${INK}"/><text x="${x(t)}" y="${h - m.b + 19}" text-anchor="middle">${o.xf ? o.xf(t) : t}</text>`);
  s += `<line x1="${m.l}" x2="${w - m.r}" y1="${h - m.b}" y2="${h - m.b}" stroke="${INK}"/><line x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${h - m.b}" stroke="${INK}"/>`;
  if (o.xl) s += `<text x="${(m.l + w - m.r) / 2}" y="${h - 6}" text-anchor="middle">${o.xl}</text>`;
  if (o.yl) s += `<text transform="rotate(-90)" x="${-(m.t + h - m.b) / 2}" y="13" text-anchor="middle">${o.yl}</text>`;
  (o.refs || []).forEach(r => s += `<line x1="${x(r[0])}" y1="${y(r[1])}" x2="${x(r[2])}" y2="${y(r[3])}" stroke="${INK3}" stroke-dasharray="2 4"/>`);
  const ends = [];
  (o.series || []).forEach(se => {
    const P = se.pts.filter(p => p[1] != null && isFinite(p[1]) && p[0] >= o.xd[0] - 1e-9 && p[0] <= o.xd[1] + 1e-9).map(p => [p[0], clamp(p[1], Math.min(o.yd[0], o.yd[1]), Math.max(o.yd[0], o.yd[1]))]);
    if (!P.length) return;
    const st = se.k ? CS[se.k] : {};
    const col = se.color || st.color || INK, wd = se.w || st.w || 2, da = se.dash != null ? se.dash : (st.dash || ''), mt = se.m || st.m;
    s += `<polyline fill="none" stroke="${col}" stroke-width="${wd}" ${da ? `stroke-dasharray="${da}"` : ''} stroke-linejoin="miter" points="${P.map(p => x(p[0]).toFixed(1) + ',' + y(p[1]).toFixed(1)).join(' ')}"/>`;
    if (se.dots && mt) P.forEach(p => s += `<g><title>${esc(se.label || '')} ${o.yf(p[1])}</title>${mk(mt, x(p[0]), y(p[1]), col, se.r || 4.5)}</g>`);
    (se.marks || []).filter(p => p[0] >= o.xd[0] && p[0] <= o.xd[1] && p[1] >= Math.min(...o.yd) && p[1] <= Math.max(...o.yd)).forEach(p => s += `<g><title>${esc(p[2] || '')}</title><rect x="${x(p[0]) - 6}" y="${y(p[1]) - 6}" width="12" height="12" fill="#fff" stroke="${col}" stroke-width="2.5"/></g>`);
    if (se.label && o.endLabels) { const L = P[P.length - 1]; ends.push({y: y(L[1]), x: x(L[0]), t: se.label, c: col}); }
  });
  ends.sort((a, b) => a.y - b.y); for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;
  ends.forEach(e => s += `<text x="${e.x + 10}" y="${e.y + 4}" class="k" style="fill:${e.c === INK3 ? INK2 : e.c}">${esc(e.t)}</text>`);
  return s + '</svg>';
}
function tabs(id, opts, cur, cb) {
  $(id).innerHTML = opts.map(([k, l]) => `<button data-k="${k}" class="${k === cur ? 'on' : ''}">${l}</button>`).join('');
  $(id).querySelectorAll('button').forEach(b => b.onclick = () => { cb(b.dataset.k); $(id).querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); });
}
const tagText = t => t.replace('label_variant:', 'label ').replace(/_/g, ' ');
const tagChip = t => `<span class="tag r">${esc(tagText(t))}</span>`;
const TAGCOL = t => { const b = t.split(':')[0]; return /^date|missing_date/.test(b) ? 'date' : /^(label_variant|missing_account|uncategorized_label|legacy_label|mojibake)$/.test(b) ? 'acct' : /^(sign_flip|amount_|credit_as|drcr|swapped)/.test(b) ? 'amt' : /^(blank_desc|whitespace)/.test(b) ? 'desc' : 'row'; };
