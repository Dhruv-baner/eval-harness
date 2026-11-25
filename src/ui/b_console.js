/* ===== 01 CONSOLE ===== */
const STAGES = ['Parse', 'Normalize', 'Map', 'Dedupe', 'Balance', 'Triage'];
const KIND = {title: 'title', blank: 'blank', header: 'header', repeat_header: 'header', section_header: 'section', section_total: 'total', subtotal: 'subtotal', grand_total: 'total', footer: 'footer'};
const CON = {cid: 'northgate_construction', stage: 0, active: 0, running: false, mem: {}, hist: [], open: null, pp: null, fresh: false, T: DEMO.threshold, shown: 12};
const cd = () => DEMO.clients[CON.cid];
const labObj = l => cd().labels.find(x => x.label === l);
const maj = l => Object.entries(l.by_true).sort((a, b) => b[1] - a[1])[0][0];
const fa = (v, cur) => v == null ? '?' : (v < 0 ? '-' : '') + Math.abs(v).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
function viewOf(c) { const r = c.roles, g = k => r[k] != null ? r[k] : -1; return {date: g('date'), acct: g('label'), desc: r.desc != null ? r.desc : g('name'), debit: g('debit'), credit: g('credit'), amount: g('amount')}; }
function eff(r) {
  const m = r.label && CON.mem[r.label];
  if (m) return {code: m.code, conf: 1, src: 'MEMORY', auto: true, ok: m.code === r.true};
  return {code: r.pred, conf: r.conf, src: (r.src || '').toUpperCase(), auto: !!r.pred && r.conf >= CON.T, ok: r.pred === r.true};
}
const effectOf = (l, code) => { const bt = l.by_true[code] || 0; return {dc: bt - l.correct, dr: -l.review, dw: (l.n - bt) - l.wrong_auto}; };
function totals() {
  const b = cd().base; let dc = 0, dr = 0, dw = 0;
  Object.entries(CON.mem).forEach(([lab, m]) => { const e = effectOf(labObj(lab), m.code); dc += e.dc; dr += e.dr; dw += e.dw; });
  return {acc: (b.correct + dc) / b.n, review: (b.review + dr) / b.n, leak: (b.wrong_auto + dw) / b.n, b0: {acc: b.correct / b.n, review: b.review / b.n, leak: b.wrong_auto / b.n}};
}
function tick(el, to, fmt) {
  const from = el._v == null ? to : el._v; el._v = to;
  if (from === to || matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = fmt(to); return; }
  let i = 0; clearInterval(el._t); el._t = setInterval(() => { i++; el.textContent = fmt(from + (to - from) * i / 8); if (i >= 8) { clearInterval(el._t); el.textContent = fmt(to); } }, 28);
}

function renderIn() {
  const c = cd(), v = viewOf(c), one = v.amount >= 0, cs = one ? 7 : 8;
  let h = `<table class="raw"><thead><tr><th>Row</th><th>Date</th><th>Account</th><th>Description</th>${one ? '<th>Amount</th>' : '<th>Debit</th><th>Credit</th>'}<th></th></tr></thead><tbody>`, prev = 0;
  c.rows.forEach(r => {
    if (prev && r.n > prev + 1) h += `<tr class="gap"><td colspan="${cs}">. . .</td></tr>`;
    prev = r.n; const g = i => i >= 0 ? (r.cells[i] || '') : '';
    if (r.kind !== 'data') {
      const txt = r.cells.filter(x => x && x.trim()).slice(0, 3).join('   ') || '(blank)', sk = CON.stage >= 1;
      h += `<tr class="${sk ? 'skip' : ''}"><td class="rn">${r.n}</td><td colspan="${one ? 4 : 5}" class="d">${esc(txt)}</td><td class="tg">${sk ? `<span class="tag">skip ${KIND[r.kind] || r.kind}</span>` : ''}</td></tr>`; return;
    }
    const e = {}; r.tags.forEach(t => e[TAGCOL(t)] = true);
    const raw = g(v.acct), fill = !raw.trim() && CON.stage >= 1 && r.label, dup = CON.stage >= 4 && r.dup;
    const A = (x, k) => `<td class="${e[k] ? 'e' : ''}">${esc(x) || '&nbsp;'}</td>`;
    h += `<tr class="${dup ? 'dup' : ''}"><td class="rn">${r.n}</td>${A(g(v.date), 'date')}<td class="${e.acct ? 'e' : ''} d">${fill ? `<span class="faint">${esc(r.label)}</span>` : esc(raw) || '&nbsp;'}</td><td class="d ${e.desc ? 'e' : ''}">${esc(g(v.desc)) || '&nbsp;'}</td>`;
    h += one ? A(g(v.amount), 'amt') : A(g(v.debit), 'amt') + A(g(v.credit), 'amt');
    h += `<td class="tg">${dup ? '<span class="tag">dup</span>' : ''}</td></tr>`;
  });
  $('cIn').innerHTML = h + '</tbody></table>';
  $('cInMeta').textContent = `${c.rows.length} sample rows of ${num(c.base.n)} in the file`;
}

function whyMap(r, e) {
  if (e.src === 'MEMORY') return 'Reviewer confirmed this label; applied to every matching row.';
  if (e.src === 'DICT') return 'Label matches the standard vocabulary exactly.';
  if (e.src === 'FUZZY') return 'Label is close to a standard name (string similarity above cutoff).';
  return 'No trusted label match; text classifier read label, description and sibling lines.';
}
function passport(r, cols) {
  const c = cd(), e = eff(r), hd = c.header || [];
  const raw = r.cells.map((x, i) => x && x.trim() ? `${esc(hd[i] || 'col ' + (i + 1))}: ${esc(x)}` : '').filter(Boolean).join('<br>');
  const dOk = r.date === r.true_date, aOk = r.net != null && Math.abs(r.net - r.true_net) < .006;
  return `<tr class="pp"><td colspan="${cols}"><div class="pgrid"><div><h4>1 Raw</h4>${raw}</div><div><h4>2 Parsed</h4>account text: ${esc(r.label) || 'blank'}<br>date: ${esc(r.date) || 'none'}<br>amount: ${fa(r.net)}<br>ref: ${esc(r.ref)}${r.filled ? '<br>date filled from sibling line' : ''}</div>
    <div><h4>3 Mapped</h4>${esc(aname(e.code))} ${e.code ? '(' + e.code + ')' : ''}<br>confidence ${pct(e.conf, 0)}<br>source ${esc(e.src || 'none')}<br>${esc(whyMap(r, e))}</div>
    <div><h4>4 Truth</h4>${esc(aname(r.true))} (${r.true})<br>${esc(r.true_date)} / ${fa(r.true_net)}<br>account ${e.ok ? 'OK' : 'WRONG'} / date ${dOk ? 'OK' : 'WRONG'} / amount ${aOk ? 'OK' : 'WRONG'}${r.tags.length ? '<br>injected: ' + r.tags.map(tagText).join(', ') : ''}</div></div></td></tr>`;
}
function renderOut() {
  const c = cd(), S = CON.stage;
  if (S < 1) { $('cOut').innerHTML = '<p class="note" style="padding:14px 0">Run the pipeline to produce the graded ledger.</p>'; return; }
  let h = `<table class="out"><thead><tr><th>Row</th><th>Date</th><th>Account</th><th>${S >= 3 ? 'Conf' : ''}</th><th class="n">Amount</th><th>${S >= 3 ? 'Grade' : ''}</th></tr></thead><tbody>`, i = 0;
  c.rows.filter(r => r.kind === 'data').forEach(r => {
    const e = eff(r), dup = S >= 4 && r.dup, rv = S >= 6 && !e.auto && !dup, wipe = CON.fresh ? ` wipe" style="animation-delay:${(i++) * 14}ms` : '';
    let tg = ''; if (dup) tg = '<span class="tag">duplicate</span>'; else { if (S >= 5) { if (r.fixed) tg += '<span class="tag f">sign fixed</span>'; else if (r.flag) tg += '<span class="tag x">imbalance</span>'; } if (rv) tg += '<span class="tag r">review</span>'; }
    const acct = S >= 3 ? (e.code ? `${e.code} ${esc(aname(e.code))}` : '<span class="red">UNMAPPED</span>') : `<span class="faint">${esc(r.label) || 'blank'}</span>`;
    const cb = S >= 3 && e.code ? `<span class="cb ${e.conf < CON.T ? 'lo' : ''}" style="width:${Math.round(e.conf * 30)}px"></span>${(e.conf * 100).toFixed(0)}` : '';
    const g = S >= 3 && !dup ? (e.ok ? 'ok' : 'wrong ' + esc(r.true)) : '';
    h += `<tr class="click ${dup ? 'dup' : ''} ${rv ? 'rv' : ''} ${S >= 3 && !dup && !e.ok ? 'wrong' : ''}${wipe}" data-n="${r.n}"><td class="rn faint">${r.n}</td><td>${S >= 2 ? esc(r.date || '?') : '·'}</td><td class="acct">${acct}</td><td class="cf">${cb}</td><td class="n">${S >= 2 ? fa(r.net) : '·'}</td><td class="chk">${g}${tg}</td></tr>`;
    if (CON.pp === r.n) h += passport(r, 6);
  });
  $('cOut').innerHTML = h + '</tbody></table>';
  $('cOut').querySelectorAll('tr.click').forEach(tr => tr.onclick = () => { CON.pp = CON.pp === +tr.dataset.n ? null : +tr.dataset.n; renderOut(); });
}
function renderPipe() {
  const c = cd(), rows = c.rows, data = rows.filter(r => r.kind === 'data'), S = CON.stage;
  const eN = data.map(eff), auto = data.filter((r, i) => !r.dup && eN[i].auto).length;
  const stat = [`${rows.length - data.length} rows skipped, ${data.length} data rows`, `${data.filter(r => r.tags.some(t => /^(date|amount|credit|drcr|missing_date)/.test(t))).length} formats repaired`,
    `${eN.filter(e => e.code).length} mapped, mean confidence ${(eN.reduce((a, e) => a + e.conf, 0) / Math.max(1, data.length) * 100).toFixed(0)}%`, `${data.filter(r => r.dup).length} duplicates removed`,
    `${new Set(data.filter(r => r.flag || r.fixed).map(r => r.ref)).size} entries flagged, ${data.filter(r => r.fixed).length} signs fixed`, `${auto} accepted, ${data.filter(r => !r.dup).length - auto} to review`];
  $('cPipe').innerHTML = STAGES.map((n, i) => `<div class="stp ${S > i ? 'done' : ''} ${CON.active === i + 1 ? 'act' : ''}"><div class="sn">0${i + 1}</div><div class="nm">${n}</div><div class="sx">${S > i ? stat[i] : ''}</div><div class="pg"><span></span></div></div>`).join('');
  if (CON.active) requestAnimationFrame(() => { const el = $('cPipe').querySelector('.stp.act'); if (el) el.classList.add('go'); });
  $('cNext').innerHTML = S >= 6 ? '<span>Pipeline complete.</span><button class="primary" id="goTeach">Next: teach the agent a label</button>' : (CON.running || CON.active ? '<span class="dim">Running.</span>' : S === 0 ? '<span class="dim">Press Run to start the pipeline.</span>' : '<span class="dim">Press Step to continue, or Run to finish.</span>');
  if ($('goTeach')) $('goTeach').onclick = () => openTab('s01', 'teach');
}
function renderScore() {
  const t = totals(), S = CON.stage, b = cd().base;
  const set = (id, v, show, f, dEl, d, warn) => { const el = $(id); el.classList.toggle('empty', !show); if (!show) { el.textContent = '--'; el._v = null; $(dEl).textContent = ''; return; } tick(el, v, f); const de = $(dEl); de.textContent = Math.abs(d) < 1e-9 ? '' : d; de.className = 'sd ' + (warn ? 'warn' : 'up'); };
  const p = v => (v * 100).toFixed(1) + '%';
  set('sAcc', t.acc, S >= 3, p, 'sAccD', t.acc - t.b0.acc > 1e-9 ? pts(t.acc - t.b0.acc) + ' pts' : (t.acc - t.b0.acc < -1e-9 ? pts(t.acc - t.b0.acc) + ' pts' : ''), t.acc < t.b0.acc);
  set('sAuto', 1 - t.review, S >= 6, p, 'sAutoD', (1 - t.review) - (1 - t.b0.review) > 1e-9 ? pts((1 - t.review) - (1 - t.b0.review)) + ' pts' : '', false);
  set('sRev', t.review, S >= 6, p, 'sRevD', t.review - t.b0.review < -1e-9 ? pts(t.review - t.b0.review) + ' pts' : '', false);
  set('sLeak', t.leak, S >= 6, v => (v * 100).toFixed(2) + '%', 'sLeakD', t.leak - t.b0.leak > 1e-9 ? pts(t.leak - t.b0.leak, 2) + ' pts' : '', true);
  $('sN').textContent = `file: ${num(b.n)} rows`;
}
function renderQueue() {
  const c = cd(), S = CON.stage;
  if (S < 6) {
    $('cQ').innerHTML = '<div class="empty">Run the pipeline first. The queue lists labels the agent did not recognise, sorted by the number of rows each one affects.<div class="cta"><button class="primary" id="goRun">Run the pipeline</button></div></div>';
    $('goRun').onclick = () => { openTab('s01', 'run'); conRun(false); }; renderConfirm(); return;
  }
  const items = c.labels.slice(0, CON.shown);
  let h = `<div class="q"><div class="qh"><h3>Review queue <small>${c.labels.filter(l => !CON.mem[l.label]).length} unfamiliar labels</small></h3><span class="meta">sorted by rows affected</span></div>`;
  items.forEach(l => {
    const done = CON.mem[l.label], m = maj(l), e = effectOf(l, m);
    h += `<div class="qi ${CON.open === l.label ? 'cur' : ''} ${done ? 'done' : ''}" data-l="${esc(l.label)}"><span class="ql">${esc(l.label)}</span><span class="qr">${num(l.n)} rows<br>${done ? 'confirmed ' + done.code : pts(e.dc / c.base.n) + ' pts if confirmed'}</span><span class="qs">Agent suggests ${l.pred ? esc(aname(l.pred)) + ' at ' + (l.conf * 100).toFixed(0) + '% confidence' : 'nothing'}. Most rows belong to ${esc(aname(m))}.</span></div>`;
  });
  if (c.labels.length > CON.shown) h += '<div class="qi" id="qMore"><span class="ql">Show more labels</span></div>';
  $('cQ').innerHTML = h + '</div>';
  $('cQ').querySelectorAll('.qi[data-l]').forEach(q => q.onclick = () => { if (CON.mem[q.dataset.l]) return; CON.open = CON.open === q.dataset.l ? null : q.dataset.l; renderQueue(); const i = $('cfIn'); if (i) i.focus(); });
  const mo = $('qMore'); if (mo) mo.onclick = () => { CON.shown += 14; renderQueue(); };
  renderConfirm();
}
function renderConfirm() {
  const l = labObj(CON.open || ''), c = cd();
  if (!l || CON.stage < 6 || CON.mem[l.label]) { $('cConfirm').innerHTML = CON.stage < 6 ? '' : '<div class="cfp"><h3>Confirm a label</h3><p class="empty">Choose a label from the queue. One confirmation applies to every row in the file that carries it.</p></div>'; return; }
  const m = maj(l), tot = Object.values(l.by_true).reduce((a, b) => a + b, 0), dist = Object.entries(l.by_true).sort((a, b) => b[1] - a[1]).slice(0, 4);
  $('cConfirm').innerHTML = `<div class="cfp"><h3>Confirm a label</h3><div class="big">${esc(l.label)}</div><div class="meta">${num(l.n)} rows in the file, ${money(l.amount, c.currency)} absolute amount</div>
    <div class="dist">${dist.map(([k, v]) => `<div><span>${esc(aname(k))} <span class="faint mono" style="font-size:.7rem">${k}</span></span><b>${(v / l.n * 100).toFixed(0)}% of rows</b></div>`).join('')}</div>
    ${dist.length > 1 && dist[1][1] / l.n > .1 ? '<p class="note">These rows belong to more than one account. Confirming one account will misplace the rest.</p>' : ''}
    <div class="row"><input type="text" id="cfIn" list="acctList" value="${esc(aname(m))} (${m})" style="min-width:250px;flex:1" aria-label="Account for this label"><button class="primary" id="cfOk">Confirm <kbd>Enter</kbd></button><button id="cfNo">Cancel <kbd>Esc</kbd></button></div><div class="eff" id="cfEff"></div></div>`;
  $('cfIn').oninput = updateEff; $('cfIn').onkeydown = ev => { if (ev.key === 'Enter') { ev.preventDefault(); confirmOpen(); } if (ev.key === 'Escape') { CON.open = null; renderQueue(); } };
  $('cfOk').onclick = confirmOpen; $('cfNo').onclick = () => { CON.open = null; renderQueue(); }; updateEff();
}
function parseAcct(s) {
  const m = /\((\d{4})\)/.exec(s); if (m && ACCT[m[1]]) return m[1];
  const hit = DEMO.accounts.find(a => a[1].toLowerCase() === s.trim().toLowerCase()); return hit ? hit[0] : null;
}
function updateEff() {
  const l = labObj(CON.open); if (!l || !$('cfIn')) return; const code = parseAcct($('cfIn').value), b = cd().base;
  if (!code) { $('cfEff').textContent = 'Choose an account from the list.'; return; }
  const e = effectOf(l, code), bt = l.by_true[code] || 0;
  $('cfEff').innerHTML = `${num(bt)} of ${num(l.n)} rows truly belong to ${esc(aname(code))}. Accuracy ${pts(e.dc / b.n)} pts, review ${pts(e.dr / b.n)} pts, uncaught mistakes ${pts(e.dw / b.n, 2)} pts.`;
}
function confirmOpen() {
  const code = parseAcct($('cfIn').value); if (!code) return;
  CON.mem[CON.open] = {code}; CON.hist.push(CON.open); CON.open = null; renderAll();
}
function undo() { const l = CON.hist.pop(); if (l) { delete CON.mem[l]; renderAll(); } }
function renderReplay() {
  const pc = (X.cold_start.hybrid.all.per_client[CON.cid] || []), mth = +$('rpM').value, r = pc.find(m => m.month === mth) || pc[0];
  if (!r) return;
  $('rpA').textContent = pct(r.rev_base / r.n); $('rpB').textContent = pct(r.rev_mem / r.n); $('rpMl').textContent = 'M' + mth;
  const ymax = Math.max(...pc.map(m => m.rev_base / m.n)) * 1.15 || 0.2;
  $('rpC').innerHTML = plot({w: 640, h: 190, m: {l: 48, r: 90, t: 8, b: 32}, endLabels: true, xd: [1, 12], yd: [0, ymax], xt: [1, 3, 6, 9, 12], xf: v => 'M' + v, yt: [0, ymax / 2, ymax], yf: v => pct(v, 0), aria: 'review rate by month',
    series: [{pts: pc.map(m => [m.month, m.rev_base / m.n]), color: INK3, dash: '6 4', w: 2, label: 'no memory'}, {pts: pc.map(m => [m.month, m.rev_mem / m.n]), color: RED, w: 3.2, label: 'memory', dots: true, m: 'cir', r: 3}], refs: [[mth, 0, mth, ymax]]});
}
function renderAll() { renderIn(); renderPipe(); renderOut(); renderScore(); renderQueue(); renderReplay(); $('bUndo').disabled = !CON.hist.length; }
function conReset() { clearTimeout(CON.timer); CON.running = false; CON.stage = 0; CON.active = 0; CON.mem = {}; CON.hist = []; CON.open = null; CON.pp = null; CON.shown = 12; ['sAcc', 'sAuto', 'sRev', 'sLeak'].forEach(i => { $(i)._v = null; }); renderAll(); }
function advance(instant) {
  if (CON.stage >= 6) { CON.running = false; renderAll(); return; }
  CON.active = CON.stage + 1; renderPipe();
  CON.timer = setTimeout(() => { CON.stage = CON.active; CON.active = 0; CON.fresh = true; renderAll(); CON.fresh = false; if (CON.running) advance(); }, instant ? 0 : CON.running ? 520 : 260);
}
function conRun(instant) { if (CON.stage >= 6) conReset(); CON.running = true; if (instant) { clearTimeout(CON.timer); CON.stage = 6; CON.active = 0; CON.running = false; renderAll(); } else advance(); }
function conStep() { if (CON.running || CON.active) return; advance(); }
function initConsole() {
  $('cClient').innerHTML = CLIENTS.map(c => `<option value="${c.client_id}">${esc(c.client_name)}</option>`).join('');
  $('cClient').value = CON.cid; $('acctList').innerHTML = DEMO.accounts.map(a => `<option value="${esc(a[1])} (${a[0]})">`).join('');
  const meta = () => { const c = cd(), i = cinfo(CON.cid); $('cMeta').innerHTML = `${esc(LAYOUT[c.layout] || c.layout)} / ${c.currency} / messiness ${c.messiness} / ${TESTSET.has(CON.cid) ? 'test firm' : 'dev firm'}`; };
  $('cClient').onchange = e => { CON.cid = e.target.value; meta(); conReset(); };
  $('bRun').onclick = () => conRun(false); $('bStep').onclick = conStep; $('bReset').onclick = conReset; $('bUndo').onclick = undo;
  $('rpM').oninput = renderReplay; meta(); conReset();
}
