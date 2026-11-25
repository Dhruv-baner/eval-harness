/* ===== 05 AUDIT TRAIL ===== */
const AU = {cid: 'northgate_construction', sort: 'diff', open: null};
function srcBar(s, n) {
  if (!n) return '';
  const d = (s.dict || 0) / n * 96, f = (s.fuzzy || 0) / n * 96, m = (s.ml || 0) / n * 96;
  return `<svg width="96" height="8" viewBox="0 0 96 8" style="width:96px;height:8px;display:inline-block"><rect x="0" width="${d}" height="8" fill="${INK}"/><rect x="${d}" width="${f}" height="8" fill="${INK3}"/><rect x="${d + f}" width="${m}" height="8" fill="${RED}"/></svg>`;
}
function renderAudit() {
  const a = AUD[AU.cid], cur = a.currency, tie = x => Math.abs(x.diff) <= Math.max(1, 0.005 * Math.abs(x.truth));
  let list = a.accounts.filter(x => x.rows > 0 || Math.abs(x.truth) > .5);
  list = AU.sort === 'diff' ? list.slice().sort((p, q) => Math.abs(q.diff) - Math.abs(p.diff)) : list.slice().sort((p, q) => p.code.localeCompare(q.code));
  const bad = list.filter(x => !tie(x)).length;
  $('auHead').textContent = `${list.length} accounts, ${list.length - bad} tie out, ${bad} do not. Click an account for the rows behind it.`;
  $('auTable').innerHTML = `<table class="t"><thead><tr><th>Account</th><th class="n">Cleaned</th><th class="n">True</th><th class="n">Difference</th><th class="n">Rows</th><th style="padding-left:18px">Source</th></tr></thead><tbody>${list.map(x => `<tr class="click ${AU.open === x.code ? 'sel' : ''}" data-c="${x.code}"><td><span class="mono faint" style="font-size:.68rem">${x.code}</span> ${esc(x.name)}</td><td class="n">${money(x.cleaned, cur)}</td><td class="n">${money(x.truth, cur)}</td><td class="n ${tie(x) ? 'faint' : 'red'}"><b>${tie(x) ? 'ties' : money(x.diff, cur)}</b></td><td class="n">${num(x.rows)}</td><td style="padding-left:18px">${srcBar(x.src, x.rows)}</td></tr>`).join('')}</tbody></table><div class="legend" style="margin-top:10px"><span><svg width="12" height="8" style="display:inline-block;width:12px;height:8px"><rect width="12" height="8" fill="${INK}"/></svg>dictionary</span><span><svg width="12" height="8" style="display:inline-block;width:12px;height:8px"><rect width="12" height="8" fill="${INK3}"/></svg>fuzzy</span><span><svg width="12" height="8" style="display:inline-block;width:12px;height:8px"><rect width="12" height="8" fill="${RED}"/></svg>classifier</span></div>`;
  $('auTable').querySelectorAll('tr.click').forEach(tr => tr.onclick = () => { AU.open = tr.dataset.c; renderAudit(); });
  const d = a.accounts.find(x => x.code === AU.open);
  if (!d) { $('auDetail').innerHTML = '<p class="note">Select an account. The panel shows why the cleaned figure differs from the true one, and the raw rows behind it.</p>'; return; }
  const li = (arr, mode) => arr.length ? arr.map(g => `<div class="pr" style="grid-template-columns:1fr auto"><span><span class="mono" style="font-size:.7rem">${esc(g.label || 'blank')}</span><br><span class="faint" style="font-size:.7rem">${mode === 'in' ? 'belongs to ' + esc(aname(g.true)) : 'posted to ' + esc(aname(g.pred))}</span></span><span class="n mono" style="font-size:.72rem">${num(g.n)} rows<br>${money(g.amount, cur)}</span></div>`).join('') : '<p class="note" style="margin:0">None.</p>';
  const hd = (X.headers[Object.keys(X.headers).find(f => f.startsWith(AU.cid))] || {});
  const samp = d.samples.map(s => `<div style="border-top:1px solid var(--hair);padding:7px 0"><div class="mono" style="font-size:.68rem"><b>row ${s.n}</b> ${s.pred === s.true ? 'ok' : '<span class="red">wrong, belongs to ' + esc(aname(s.true)) + '</span>'} / conf ${(s.conf * 100).toFixed(0)}% / ${esc(s.src || 'none')} / ${money(s.amt, cur)}</div><div class="mono faint" style="font-size:.66rem;overflow-wrap:anywhere">${s.cells.filter(Boolean).map(esc).join('  |  ')}</div>${s.tags.length ? `<div style="margin-top:3px">${s.tags.map(tagChip).join('')}</div>` : ''}</div>`).join('');
  $('auDetail').innerHTML = `<h3>${esc(d.name)} <small>${d.code}</small></h3><div class="find" style="grid-template-columns:1fr;gap:4px;border-top:0;padding:10px 0 4px"><span class="fv" style="font-size:2.2rem">${tie(d) ? 'ties out' : money(d.diff, cur)}</span><span class="ft" style="font-size:.85rem">cleaned ${money(d.cleaned, cur)}, true ${money(d.truth, cur)}, ${num(d.rows)} rows${d.conf != null ? ', mean confidence ' + (d.conf * 100).toFixed(0) + '%' : ''}</span></div>
    <div class="lbl" style="margin:14px 0 4px">Posted here, belongs elsewhere</div>${li(d.wrong_in, 'in')}<div class="lbl" style="margin:14px 0 4px">Belongs here, posted elsewhere</div>${li(d.wrong_out, 'out')}
    ${(!d.wrong_in.length && !d.wrong_out.length && !tie(d)) ? '<p class="note">The gap is not account mapping. It comes from rows lost in the export, duplicates left in, or sign errors.</p>' : ''}
    <div class="lbl" style="margin:14px 0 4px">Rows behind the number</div>${samp || '<p class="note">No rows posted here.</p>'}`;
}
function initAudit() {
  $('auSel').innerHTML = CLIENTS.map(c => `<option value="${c.client_id}">${esc(c.client_name)}</option>`).join(''); $('auSel').value = AU.cid;
  $('auSel').onchange = e => { AU.cid = e.target.value; AU.open = AUD[AU.cid].accounts[0].code; renderAudit(); };
  tabs('auSort', [['diff', 'By difference'], ['code', 'By account']], AU.sort, k => { AU.sort = k; renderAudit(); });
  AU.open = AUD[AU.cid].accounts[0].code; renderAudit();
}

/* ===== 06 TRUST AND COST ===== */
const TR = {cal: 'hybrid'};
function drawCal() {
  const g = M(TR.cal, 'test').calibration, w = 480, h = 360, m = {l: 54, r: 16, t: 14, b: 48}, x = lin(0, 1, m.l, w - m.r), y = lin(0, 1, h - m.b, m.t), mx = Math.max(...g.bins.map(b => b.n)), big = g.bins.filter(b => b.n >= 150);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="reliability diagram">`;
  [0, .25, .5, .75, 1].forEach(t => s += `<line x1="${m.l}" x2="${w - m.r}" y1="${y(t)}" y2="${y(t)}" stroke="#EDEDED"/><text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end">${pct(t, 0)}</text><text x="${x(t)}" y="${h - m.b + 18}" text-anchor="middle">${pct(t, 0)}</text>`);
  s += `<line x1="${m.l}" x2="${w - m.r}" y1="${h - m.b}" y2="${h - m.b}" stroke="${INK}"/><line x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${h - m.b}" stroke="${INK}"/><line x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}" stroke="${INK3}" stroke-dasharray="2 4"/>`;
  s += `<polyline fill="none" stroke="${CS[TR.cal].color}" stroke-width="2" points="${big.map(b => x(b.mean_conf).toFixed(1) + ',' + y(b.acc).toFixed(1)).join(' ')}"/>`;
  g.bins.forEach(b => { const r = 4 + 9 * Math.sqrt(b.n / mx); s += `<circle cx="${x(b.mean_conf)}" cy="${y(b.acc)}" r="${r}" fill="${b.n >= 150 ? CS[TR.cal].color : '#fff'}" stroke="${CS[TR.cal].color}" stroke-width="1.5"><title>confidence ${pct(b.mean_conf, 0)}: right ${pct(b.acc, 0)} of ${num(b.n)} rows</title></circle>`; });
  s += `<text x="${(m.l + w - m.r) / 2}" y="${h - 6}" text-anchor="middle">Stated confidence</text><text transform="rotate(-90)" x="${-(m.t + h - m.b) / 2}" y="13" text-anchor="middle">Observed accuracy</text></svg>`;
  $('calChart').innerHTML = s;
  $('calNote').textContent = `ECE ${pct(g.ece, 1)}. Below the dotted line is over-confident. Bubble area is row count; hollow bubbles have fewer than 150 rows. ` + ({ml: 'The classifier is over-confident on firms whose vocabulary it has never seen.', rules: 'Rules emit two confidence levels, so there is nothing to triage on.', hybrid: 'Dictionary matches sit at 100% and are right. The uncertain middle is the classifier.', fuzzy: 'Fuzzy confidence is a string score, not a probability.'}[TR.cal]);
}
function renderTrust() {
  tabs('calSeg', CL.map(n => [n, CS[n].name]), TR.cal, k => { TR.cal = k; drawCal(); }); drawCal();
  $('covLeg').innerHTML = legendHTML();
  const ser = CL.map(n => { const c = X.fine_curves.test[n], op = X.operating[n].dev_best_threshold, mp = c.points.find(p => Math.abs(p[0] - op) < 1e-9);
    return {k: n, label: CS[n].name, pts: c.points.filter(p => p[1] > 0).map(p => [p[1] / c.rows, 1 - p[2] / p[1]]), marks: mp && mp[1] ? [[mp[1] / c.rows, 1 - mp[2] / mp[1], `${CS[n].name} at threshold ${op}`]] : []}; });
  $('covChart').innerHTML = plot({w: 720, h: 340, xd: [.5, 1], yd: [.85, 1], xt: [.5, .6, .7, .8, .9, 1], yt: [.85, .9, .95, 1], xf: v => pct(v, 0), yf: v => pct(v, 0), xl: 'Share of rows accepted without review', yl: 'Accuracy of accepted rows', aria: 'accuracy against automation', series: ser}) + '<p class="note">Squares mark the cost-optimal threshold chosen on dev firms. Zoomed to the useful region.</p>';
  const E = X.economics_defaults, sl = [['conf', 'Minutes to confirm a correct suggestion', .02, .5, .01, E.confirm_min, v => v.toFixed(2) + ' min'], ['fix', 'Minutes to fix a wrong or missing suggestion', .2, 3, .1, E.fix_min, v => v.toFixed(1) + ' min'],
    ['err', 'Minutes-equivalent of one mistake that slips through', 1, 120, 1, E.error_min_each, v => v + ' min'], ['rows', 'Rows per firm per year', 5000, 100000, 1000, 25000, num], ['rate', 'Reviewer cost per hour', 20, 150, 5, 60, v => '$' + v]];
  $('ecCtl').innerHTML = sl.map(([id, l, a, b, st, v, f]) => `<div class="sl-row"><span>${l}</span><b id="ev_${id}">${f(v)}</b><input type="range" id="e_${id}" min="${a}" max="${b}" step="${st}" value="${v}"></div>`).join('') + '<p class="note">Defaults are assumptions. A mistake that slips through costs far more than a review because it is found late, in someone else’s review, or never.</p>';
  sl.forEach(([id, , , , , , f]) => $('e_' + id).oninput = () => { $('ev_' + id).textContent = f(+$('e_' + id).value); drawEcon(); }); drawEcon();
}
function drawEcon() {
  const cf = +$('e_conf').value, fx = +$('e_fix').value, er = +$('e_err').value, yr = +$('e_rows').value, rate = +$('e_rate').value, man = yr * fx / 60;
  const res = CL.map(n => { const c = X.fine_curves.test[n], k = yr / c.rows; const pt = c.points.map(p => { const q = c.rows - p[1]; return {t: p[0], hrs: (p[4] * cf + (q - p[4]) * fx + p[2] * er) * k / 60, rev: q * k, wrong: p[2] * k, auto: p[1] / c.rows, ok: q ? p[4] / q : 1}; });
    return {n, pt, best: pt.reduce((a, b) => b.hrs < a.hrs ? b : a)}; });
  $('ecChart').innerHTML = legendHTML() + plot({w: 720, h: 330, endLabels: true, xd: [0, 1], yd: [0, man * 1.15], xt: [0, .25, .5, .75, 1], xf: v => v.toFixed(2), yt: [0, .25, .5, .75, 1].map(f => f * man * 1.15), yf: v => Math.round(v) + ' h', xl: 'Confidence threshold for auto-accept', yl: 'Reviewer hours per firm per year', aria: 'review hours by threshold',
    series: res.map(r => ({k: r.n, label: CS[r.n].name, pts: r.pt.map(p => [p.t, p.hrs]), marks: [[r.best.t, r.best.hrs, `${CS[r.n].name}: ${Math.round(r.best.hrs)} h at ${r.best.t.toFixed(2)}`]]})), refs: [[0, man, 1, man]]}) + '<p class="note">Dotted line: every row coded by hand.</p>';
  $('ecTable').innerHTML = `<table class="t"><thead><tr><th>Cleaner</th><th class="n">Threshold</th><th class="n">Auto</th><th class="n">Reviewed / yr</th><th class="n">Suggestion right</th><th class="n">Slipping through</th><th class="n">Hours / yr</th><th class="n">Cost / yr</th><th class="n">Saved</th></tr></thead><tbody>${res.map(r => `<tr><td>${CS[r.n].name}</td><td class="n">${r.best.t.toFixed(2)}</td><td class="n">${pct(r.best.auto, 0)}</td><td class="n">${num(r.best.rev)}</td><td class="n">${r.best.rev ? pct(r.best.ok, 0) : '--'}</td><td class="n">${num(r.best.wrong)}</td><td class="n">${num(r.best.hrs)}</td><td class="n">$${num(r.best.hrs * rate)}</td><td class="n ${r.n === 'hybrid' ? 'best' : ''}">${pct(1 - r.best.hrs / man, 0)}</td></tr>`).join('')}<tr><td>By hand</td><td class="n">--</td><td class="n">0%</td><td class="n">${num(yr)}</td><td class="n">--</td><td class="n">--</td><td class="n">${num(man)}</td><td class="n">$${num(man * rate)}</td><td class="n">--</td></tr></tbody></table><p class="note">Best threshold here is the minimum of the test curve at the costs set above. The headline figures use the threshold chosen on dev firms.</p>`;
}

/* ===== 07 LEARNING ===== */
const LN = {c: 'hybrid', s: 'all'};
function renderLearning() {
  tabs('lnSegC', [['hybrid', 'Hybrid'], ['rules', 'Rules']], LN.c, k => { LN.c = k; drawLearning(); }); tabs('lnSegS', [['all', 'All firms'], ['test', 'Test firms']], LN.s, k => { LN.s = k; drawLearning(); }); drawLearning();
  $('lnCurve').innerHTML = legendHTML() + plot({w: 640, h: 330, xd: [0, Math.log10(1300)], yd: [.75, 1], xt: [0, 5, 10, 20, 40, 80, 160, 320, 640, 1280].map(v => Math.log10(1 + v)).filter(v => v <= Math.log10(1300)), xf: v => Math.round(Math.pow(10, v) - 1), yt: [.75, .8, .85, .9, .95, 1], yf: v => pct(v, 0), xl: 'Labels a reviewer has confirmed (log scale)', yl: 'Account accuracy', aria: 'accuracy after reviewing labels',
    series: CL.map(n => ({k: n, label: CS[n].name, dots: true, r: 3.5, pts: M(n, 'test').review_curve.map(c => [Math.log10(1 + c.labels_reviewed), c.accuracy])}))});
}
function drawLearning() {
  const d = X.cold_start[LN.c][LN.s].months, f = k => d.map(m => [m.month, m[k] / m.n]);
  const P = [['rev_base', 'rev_mem', 'rev_audit'], ['wrong_base', 'wrong_mem', 'wrong_audit']];
  const sty = [{c: INK3, dash: '6 4', w: 2.4, l: 'no memory', m: 'sqo'}, {c: RED, dash: '', w: 3.4, l: 'memory', m: 'cir'}, {c: INK, dash: '9 3 2 3', w: 2.4, l: 'memory + audit', m: 'dia'}];
  const mkS = i => P[i].map((k, j) => ({pts: f(k), color: sty[j].c, dash: sty[j].dash, w: sty[j].w, label: sty[j].l, dots: j > 0, m: sty[j].m, r: 3.5}));
  const ym = Math.ceil(Math.max(...d.map(m => m.rev_base / m.n)) * 20) / 20 + .02, wm = Math.max(...d.map(m => Math.max(m.wrong_mem, m.wrong_audit, m.wrong_base) / m.n)) * 1.15;
  $('lnRev').innerHTML = plot({w: 640, h: 320, endLabels: true, m: {r: 120}, xd: [1, 12], yd: [0, ym], xt: [1, 3, 6, 9, 12], xf: v => 'M' + v, yt: [0, ym / 4, ym / 2, ym * .75, ym], yf: v => pct(v, 0), xl: 'Months since onboarding', yl: 'Rows sent to a reviewer', aria: 'review rate by month', series: mkS(0)});
  $('lnWrong').innerHTML = plot({w: 640, h: 320, endLabels: true, m: {r: 120}, xd: [1, 12], yd: [0, wm], xt: [1, 3, 6, 9, 12], xf: v => 'M' + v, yt: [0, .25, .5, .75, 1].map(v => v * wm), yf: v => pct(v, 2), xl: 'Months since onboarding', yl: 'Accepted rows that are wrong', aria: 'uncaught mistakes by month', series: mkS(1)});
  const h = X.cold_start.hybrid.all.months, a = h[0], l = h[h.length - 1], row = (nm, r, w) => `<tr><td>${nm}</td><td class="n">${pct(a[r] / a.n)}</td><td class="n">${pct(l[r] / l.n)}</td><td class="n">${pct(l[w] / l.n, 2)}</td></tr>`;
  $('lnTable').innerHTML = `<table class="t"><thead><tr><th>Policy, hybrid, all firms</th><th class="n">Review M1</th><th class="n">Review M12</th><th class="n">Uncaught M12</th></tr></thead><tbody>${row('No memory', 'rev_base', 'wrong_base')}${row('Memory', 'rev_mem', 'wrong_mem')}${row('Memory + 5% audit', 'rev_audit', 'wrong_audit')}</tbody></table><p class="note">Memory removes about nine in ten reviews but lets mistakes through for labels that map to more than one account, such as Travel and Meals. Auditing 5% of remembered rows finds those labels and retires them.</p>`;
}

/* ===== 08 INSPECTOR ===== */
const INS = {page: 0};
function renderInspector() {
  let seed = 7; const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let z = Math.imul(seed ^ seed >>> 15, 1 | seed); z = z + Math.imul(z ^ z >>> 7, 61 | z) ^ z; return ((z ^ z >>> 14) >>> 0) / 4294967296; };
  for (let i = X.inspector.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [X.inspector[i], X.inspector[j]] = [X.inspector[j], X.inspector[i]]; }
  const rows = X.inspector, cl = [...new Set(rows.map(r => r.client))];
  $('inC').innerHTML = '<option value="">All firms</option>' + cl.map(c => `<option value="${c}">${esc(cname(c))}</option>`).join('');
  $('inO').innerHTML = '<option value="">All outcomes</option><option value="wrong">Hybrid wrong</option><option value="right">Hybrid right</option><option value="dup">Duplicates</option>';
  $('inT').innerHTML = '<option value="">Any injected error</option><option value="__none">No injected error</option>' + [...new Set(rows.flatMap(r => r.tags.map(t => t.split(':')[0])))].sort().map(t => `<option value="${t}">${esc(tagText(t))}</option>`).join('');
  ['inC', 'inO', 'inT'].forEach(id => $(id).onchange = () => { INS.page = 0; drawInspector(); });
  $('inPrev').onclick = () => { INS.page--; drawInspector(); }; $('inNext').onclick = () => { INS.page++; drawInspector(); }; drawInspector();
}
function drawInspector() {
  const c = $('inC').value, o = $('inO').value, t = $('inT').value;
  const rows = X.inspector.filter(r => (!c || r.client === c) && (!t || (t === '__none' ? !r.tags.length : r.tags.some(x => x.split(':')[0] === t))) && (!o || (o === 'dup' ? r.dup : o === 'wrong' ? (!r.dup && r.preds.hybrid[0] !== r.truth.code) : (!r.dup && r.preds.hybrid[0] === r.truth.code))));
  const per = 5, pages = Math.max(1, Math.ceil(rows.length / per)); INS.page = clamp(INS.page, 0, pages - 1);
  $('inCount').textContent = `${rows.length} rows`; $('inPage').textContent = `${INS.page + 1} / ${pages}`; $('inPrev').disabled = INS.page === 0; $('inNext').disabled = INS.page >= pages - 1;
  $('inList').innerHTML = rows.slice(INS.page * per, INS.page * per + per).map(r => {
    const meta = X.headers[r.file][r.sheet] || Object.values(X.headers[r.file])[0], hd = meta.header || [], hl = {}; (r.hl || []).forEach(h => { if (h[0] >= 0) hl[h[0]] = 1; });
    const n = Math.max(r.cells.length, hd.length), tn = r.truth.net, dOk = r.hyb_date === r.truth.date, nOk = r.hyb_net != null && Math.abs(r.hyb_net - tn) < .006;
    const tbl = `<div class="sc"><table class="raw"><thead><tr>${Array.from({length: n}, (_, i) => `<th>${esc(hd[i]) || ''}</th>`).join('')}</tr></thead><tbody><tr>${Array.from({length: n}, (_, i) => `<td class="${hl[i] ? 'e' : ''}">${esc(r.cells[i]) || '&nbsp;'}</td>`).join('')}</tr></tbody></table></div>`;
    const pr = r.dup ? `<div class="pr"><b>Hybrid</b><span>${r.preds.hybrid[2] === 'dup' ? 'flagged as duplicate' : 'kept as a real row'}</span><span class="${r.preds.hybrid[2] === 'dup' ? 'ok' : 'no'}">${r.preds.hybrid[2] === 'dup' ? 'ok' : 'wrong'}</span></div>` :
      CL.map(k => { const p = r.preds[k], ok = p[0] === r.truth.code; return `<div class="pr"><b>${CS[k].name}</b><span>${p[0] ? esc(aname(p[0])) + ' <span class="mono faint" style="font-size:.68rem">' + p[0] + ' ' + (p[1] * 100).toFixed(0) + '%</span>' : '<span class="faint">unmapped</span>'}</span><span class="${ok ? 'ok' : 'no'}">${ok ? 'ok' : 'wrong'}</span></div>`; }).join('') +
      `<div class="pr"><b>Date</b><span class="mono">${esc(r.hyb_date) || 'none'}</span><span class="${dOk ? 'ok' : 'no'}">${dOk ? 'ok' : 'wrong'}</span></div><div class="pr"><b>Amount</b><span class="mono">${r.hyb_net == null ? 'none' : fa(r.hyb_net)}</span><span class="${nOk ? 'ok' : 'no'}">${nOk ? 'ok' : 'wrong'}</span></div>`;
    return `<div class="ins"><div><div class="meta"><span>${esc(cname(r.client))}</span><span class="mono faint">row ${r.row}</span>${r.dup ? '<span class="tag">duplicate row</span>' : ''}${r.tags.map(tagChip).join('')}</div>${tbl}</div><div><div class="truth">Truth: ${esc(r.truth.name)} <span class="mono faint" style="font-size:.68rem">${r.truth.code}</span><br><span class="mono dim" style="font-size:.7rem;font-weight:500">${r.truth.date} / ${tn >= 0 ? 'debit' : 'credit'} ${fa(Math.abs(tn))}</span></div>${pr}</div></div>`;
  }).join('') || '<p class="note">No rows match.</p>';
}

/* ===== 09 SPEC ===== */
function renderSpec() {
  const T = R.tuning, O = X.operating.hybrid, E = X.economics_defaults;
  const kv = [['Dataset', '8 synthetic firms, 57,165 journal entries, 152,409 ledger lines, 152,847 exported rows.', 'Generated. Real files will fail in ways this does not model.'],
    ['Answer key', 'Every export row maps to its true ledger line. Every injected error is logged.', 'Round-trip check passes on 142,904 rows.'],
    ['Split', 'Dev: harborview, brightleaf, lumen, sunrise. Test: northgate, alder and finch, rivera, kestrel.', 'Cleaner designs predate the split. Only numeric cutoffs were tuned on dev.'],
    ['Cleaners', 'Rules, fuzzy, ML, hybrid. One layout-agnostic parser that never reads the key.', 'Deliberately simple stand-ins.'],
    ['ML training', 'Trained on dev firms only, never the firm being scored.', 'Vendor names are shared across firms, so results are probably flattering.'],
    ['Tuning', `Fuzzy cutoff ${T.fuzzy_cutoff_chosen}, hybrid cutoff ${T.hybrid_cutoff_chosen}, threshold ${O.dev_best_threshold}. All chosen on dev.`, `Threshold minimises modelled time: ${E.confirm_min} min confirm, ${E.fix_min} min fix, ${E.error_min_each} min per slip.`],
    ['Intervals', 'Paired bootstrap over documents within firms, 400 resamples.', 'Excludes variation between firms. Four test firms.'],
    ['Network effect', 'Leave-one-firm-out, k other firms, at most 5,000 rows each.', 'Separate from the dev and test split. Random subsets.'],
    ['Unbalanced entries', 'Detected by grouping lines on document reference.', 'Near perfect because every synthetic entry started balanced.'],
    ['Economics', 'Arithmetic on measured curves.', 'Minutes and dollars are adjustable assumptions.']];
  $('spKv').innerHTML = '<table class="kv"><tbody>' + kv.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('') + '</tbody></table>';
  $('spNext').innerHTML = ['Replace the stand-in with the production agent. The harness needs one row per input: file, row, predicted account, confidence, date, amount.', 'Add a language-model cleaner that sees each distinct firm label once, and report cost and latency beside accuracy.', 'Score the review layer: seed duplicate vendor payments, weekend postings and amounts just under approval limits.', 'Calibrate the error model on fifty hand-labelled rows from one real firm.', 'Key memory on label plus description cluster so one label can map to two accounts.'].map(t => `<li>${t}</li>`).join('');
}
