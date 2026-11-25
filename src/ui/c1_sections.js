/* ===== 02 NETWORK EFFECT ===== */
const NK = NET.ks;
function renderNetwork() {
  const mean = NET.mean, last = String(NK[NK.length - 1]), first = String(NK[0]);
  const thin = Object.entries(NET.clients).map(([cid, v]) => ({pts: NK.map(k => [k, v[String(k)].acc]), color: HAIR, w: 1.5}));
  $('netChart').innerHTML = plot({w: 760, h: 380, m: {l: 62, r: 150, t: 14, b: 48}, endLabels: true, xd: [0, 7], yd: [0, 1], xt: NK, yt: [0, .2, .4, .6, .8, 1], yf: v => pct(v, 0), xf: v => v, xl: 'Other firms the agent has learned from', yl: 'Account accuracy', aria: 'accuracy by number of firms learned from',
    series: thin.concat([{pts: NK.map(k => [k, mean[String(k)].acc]), color: RED, w: 4, dots: true, m: 'cir', r: 5.5, label: 'all rows'}, {pts: NK.map(k => [k, mean[String(k)].acc_client_vocab]), color: INK, w: 3, dash: '9 3 2 3', dots: true, m: 'dia', r: 5, label: 'client vocabulary'}])});
  const cvg = mean[last].acc_client_vocab - mean[first].acc_client_vocab;
  $('netFind').innerHTML = [
    ['F-01', '+' + (cvg * 100).toFixed(0) + ' pts', `Gain on client-specific vocabulary from zero to ${last} firms: ${pct(mean[first].acc_client_vocab, 0)} to ${pct(mean[last].acc_client_vocab, 0)}.`, 'Each firm teaches the agent vocabulary the next firm reuses.'],
    ['F-02', pct(mean[last].acc, 1), `Mean accuracy with ${last} firms in the network, against ${pct(mean[first].acc, 1)} with none.`, 'Overall accuracy plateaus near four firms. The gain sits in client vocabulary, where it is still rising. Leave-one-firm-out, at most 5,000 rows per firm.']]
    .map(f => `<div class="find"><span class="fc">${f[0]}</span><span class="fv">${f[1]}</span><span class="ft">${f[2]}<span>${f[3]}</span></span></div>`).join('');
  const sl = () => { const k = String(NK[+$('netSl').value]); $('netK').textContent = k + (k === '1' ? ' firm' : ' firms'); tick($('netAcc'), mean[k].acc, v => (v * 100).toFixed(1) + '%'); tick($('netCs'), mean[k].acc_client_vocab, v => (v * 100).toFixed(1) + '%'); $('netCov').textContent = `${pct(mean[k].coverage_80, 0)} of rows at confidence 0.80 or more, ${pct(mean[k].acc_at_80, 1)} correct`; };
  $('netSl').max = NK.length - 1; $('netSl').value = NK.length - 1; $('netSl').oninput = sl; sl();
}

/* ===== 03 SCOREBOARD ===== */
const SB = {split: 'test'};
const MET = [['Account accuracy', g => g.overall.acc, 1, 'acc'], ['Cost-weighted accuracy', g => g.overall.acc_cost_weighted, 1, 'cost'], ['Dollar-weighted accuracy', g => g.overall.acc_dollar_weighted_macro, 1, 'dollar'],
  ['Rows fully correct', g => g.overall.fully_correct, 1, 'fully'], ['Date accuracy', g => g.overall.date_acc, 1], ['Amount accuracy', g => g.overall.amount_acc, 1], ['Left unmapped', g => g.overall.unmapped, 0],
  ['Duplicate recall', g => g.duplicates.recall, 1], ['Duplicate precision', g => g.duplicates.precision, 1], ['Unbalanced entries found', g => g.imbalance.recall, 1],
  ['Trial-balance accounts within 1%', g => g.trial_balance_overall.within_1pct_macro, 1], ['Dollars misposted in trial balance', g => g.trial_balance_overall.misstatement_macro, 0], ['Calibration error', g => g.calibration.ece, 0]];
function renderScoreboard() {
  const sp = SB.split, bt = X.bootstrap[sp], H = M('hybrid', 'test'), B = X.bootstrap.test;
  const vt = n => H.by_label_tag.find(x => x.tag === n).acc, rc = H.review_curve.find(c => c.labels_reviewed === 10), cs = X.cold_start.hybrid.all.months, m12 = cs[cs.length - 1];
  $('sbFind').innerHTML = [
    ['F-03', pct(B.acc.hybrid.mean), 'Account accuracy, hybrid cleaner, four held-out firms.', `Fuzzy ${pct(M('fuzzy', 'test').overall.acc)}, rules ${pct(M('rules', 'test').overall.acc)}, ML ${pct(M('ml', 'test').overall.acc)}. 95% interval ${pct(B.acc.hybrid.lo)} to ${pct(B.acc.hybrid.hi)}.`],
    ['F-04', pct(vt('client_specific_vocabulary'), 0), 'Accuracy on labels a firm invented for itself.', `Standard account names map at ${pct(vt('standard_vocabulary'), 1)}. Noise (typos, case, renames) is mostly handled.`],
    ['F-05', pct(rc.accuracy), 'Accuracy after a reviewer confirms ten unfamiliar labels.', `From ${pct(H.overall.acc)}. Unfamiliar vocabulary is the bottleneck and a cheap one to fix.`],
    ['F-06', pct(m12.rev_mem / m12.n), 'Review rate by month twelve with client memory.', `${pct(m12.rev_base / m12.n, 0)} without memory. Memory leaks mistakes for labels that map to two accounts; a 5% audit sample recovers most of that.`]]
    .map(f => `<div class="find"><span class="fc">${f[0]}</span><span class="fv">${f[1]}</span><span class="ft">${f[2]}<span>${f[3]}</span></span></div>`).join('');
  $('sbNote').textContent = sp === 'test' ? 'TEST: northgate, alder and finch, rivera, kestrel. Never used for tuning or training.' : sp === 'dev' ? 'DEV: harborview, brightleaf, lumen, sunrise. Used to choose cutoffs and thresholds.' : 'ALL eight firms pooled. ML trained on dev firms only.';
  // dot plot with intervals
  const w = 640, rh = 54, m = {l: 90, r: 70, t: 8, b: 34}, h = m.t + m.b + rh * 4, x = lin(.5, 1, m.l, w - m.r);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="account accuracy by cleaner">`;
  for (let t = .5; t <= 1.0001; t += .1) s += `<line x1="${x(t)}" x2="${x(t)}" y1="${m.t}" y2="${h - m.b}" stroke="#EDEDED"/><text x="${x(t)}" y="${h - 12}" text-anchor="middle">${(t * 100).toFixed(0)}%</text>`;
  s += `<line x1="${m.l}" x2="${w - m.r}" y1="${h - m.b}" y2="${h - m.b}" stroke="${INK}"/>`;
  ['hybrid', 'fuzzy', 'rules', 'ml'].forEach((k, i) => { const y = m.t + i * rh + rh / 2, v = M(k, sp).overall.acc, ci = bt ? bt.acc[k] : null;
    s += `<text class="k" x="${m.l - 12}" y="${y + 4}" text-anchor="end" style="fill:${k === 'hybrid' ? RED : INK}">${CS[k].name}</text><line x1="${m.l}" x2="${x(v)}" y1="${y}" y2="${y}" stroke="${CS[k].color}" stroke-width="1" stroke-dasharray="${CS[k].dash}"/>`;
    if (ci) s += `<line x1="${x(ci.lo)}" x2="${x(ci.hi)}" y1="${y}" y2="${y}" stroke="${INK}" stroke-width="3"/>`;
    s += mk(CS[k].m, x(v), y, CS[k].color, 8) + `<text class="v" x="${x(v) + 16}" y="${y + 4}">${pct(v)}</text>`; });
  $('sbDot').innerHTML = s + '</svg>';
  const vis = CLIENTS.map(c => c.client_id).filter(id => sp === 'all' || (sp === 'test') === TESTSET.has(id)).sort((a, b) => TESTSET.has(b) - TESTSET.has(a));
  const acc = (n, id) => M(n, 'all').by_client.find(c => c.client_id === id).acc;
  const wins = vis.filter(id => CL.every(n => acc('hybrid', id) >= acc(n, id) - 1e-9)), lost = vis.filter(id => !wins.includes(id));
  $('sbMat').innerHTML = `<table class="t heat"><thead><tr><th>Firm</th>${CL.map(n => `<th class="n">${CS[n].name}</th>`).join('')}</tr></thead><tbody>${vis.map(id => `<tr><td>${esc(cname(id))} <span class="tag">${TESTSET.has(id) ? 'test' : 'dev'}</span><br><span class="mono faint" style="font-size:.65rem">${cinfo(id).export_layout}, ${cinfo(id).messiness}</span></td>${CL.map(n => `<td class="h" style="background:${heat(acc(n, id))}">${pct(acc(n, id))}</td>`).join('')}</tr>`).join('')}</tbody></table><p class="note">Hybrid is best on ${wins.length} of ${vis.length} firms${lost.length ? '; it loses on ' + lost.map(cname).join(', ') : ''}. Shading: darker red, lower accuracy.</p>`;
  $('sbMet').innerHTML = `<table class="t"><thead><tr><th>Metric</th>${CL.map(n => `<th class="n">${CS[n].name}</th>`).join('')}</tr></thead><tbody>${MET.map(([lab, f, hi, ck]) => { const vals = CL.map(n => f(M(n, sp))), best = hi ? Math.max(...vals) : Math.min(...vals);
    return `<tr><td>${lab}</td>${vals.map((v, i) => { const ci = ck && bt ? bt[ck][CL[i]] : null; return `<td class="n ${Math.abs(v - best) < 1e-9 ? 'best' : ''}">${pct(v)}${ci ? `<span class="ci">${(ci.lo * 100).toFixed(1)} to ${(ci.hi * 100).toFixed(1)}</span>` : ''}</td>`; }).join('')}</tr>`; }).join('')}</tbody></table>`;
  $('sbPair').innerHTML = `<table class="t"><thead><tr><th>Hybrid minus</th><th class="n">Account</th><th class="n">Cost-weighted</th><th class="n">Dollar-weighted</th><th class="n">Fully correct</th></tr></thead><tbody>${['fuzzy', 'rules', 'ml'].map(n => `<tr><td>${CS[n].name}</td>${['acc', 'cost', 'dollar', 'fully'].map(k => { const d = B[k].hybrid_minus[n]; return `<td class="n"><b>${pts(d.mean)} pts</b><span class="ci">${pts(d.lo)} to ${pts(d.hi)}</span></td>`; }).join('')}</tr>`).join('')}</tbody></table><p class="note">Paired bootstrap on the test set. Intervals cover sampling noise inside each firm. With four test firms, variation between firms is the larger uncertainty.</p>`;
}

/* ===== 04 FAILURE MODES ===== */
const TAGROWS = [['label_variant:typo', 'Typos'], ['label_variant:case', 'Case changes'], ['label_variant:abbrev', 'Abbreviations'], ['label_variant:alt_name', 'Alternate names'], ['label_variant:codeprefix', 'Code prefixes'], ['legacy_label', 'Renamed mid-year'], ['mojibake', 'Garbled encoding'],
  ['missing_account', 'Account blank'], ['uncategorized_label', 'Suspense, uncategorised'], ['inherently_ambiguous_label', 'Label maps to 2+ accounts'], ['standard_vocabulary', 'Standard vocabulary'], ['client_specific_vocabulary', 'Client vocabulary']];
const FL = {c: 'hybrid'};
function renderFailures() {
  $('fMat').innerHTML = `<table class="t heat"><thead><tr><th>Error type</th>${CL.map(n => `<th class="n">${CS[n].name}</th>`).join('')}</tr></thead><tbody>${TAGROWS.map(([t, l]) => { const c = CL.map(n => M(n, 'test').by_label_tag.find(x => x.tag === t) || {}); if (!c[0].n) return '';
    return `<tr><td>${l}<span class="mono faint" style="font-size:.65rem;display:block">${num(c[0].n)} rows</span></td>${c.map(x => `<td class="h" style="background:${heat(x.acc)}">${pct(x.acc, 0)}</td>`).join('')}</tr>`; }).join('')}</tbody></table>`;
  const g = (n, t) => M(n, 'test').by_label_tag.find(x => x.tag === t).acc, w = 560, rh = 62, m = {l: 84, r: 58, t: 22, b: 34}, x = lin(0, 1, m.l, w - m.r), h = m.t + m.b + rh * 4;
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="standard versus client vocabulary accuracy">`;
  [0, .25, .5, .75, 1].forEach(t => s += `<line x1="${x(t)}" x2="${x(t)}" y1="${m.t}" y2="${h - m.b}" stroke="#EDEDED"/><text x="${x(t)}" y="${h - 12}" text-anchor="middle">${t * 100}%</text>`);
  s += `<circle cx="${m.l + 4}" cy="8" r="5" fill="${INK}"/><text x="${m.l + 14}" y="12">standard names</text><circle cx="${m.l + 130}" cy="8" r="5" fill="${RED}"/><text x="${m.l + 140}" y="12">client names</text>`;
  CL.slice().reverse().forEach((k, i) => { const y = m.t + i * rh + rh / 2 + 4, a = g(k, 'standard_vocabulary'), b = g(k, 'client_specific_vocabulary');
    s += `<text class="k" x="${m.l - 12}" y="${y + 4}" text-anchor="end" style="fill:${k === 'hybrid' ? RED : INK}">${CS[k].name}</text><line x1="${x(b)}" x2="${x(a)}" y1="${y}" y2="${y}" stroke="${INK}" stroke-width="2"/><circle cx="${x(a)}" cy="${y}" r="7" fill="${INK}"/><circle cx="${x(b)}" cy="${y}" r="7" fill="${RED}"/><text class="v" x="${x(b)}" y="${y - 14}" text-anchor="middle">${pct(b, 0)}</text><text class="v" x="${x(a)}" y="${y - 14}" text-anchor="middle">${pct(a, 0)}</text>`; });
  $('fVoc').innerHTML = s + `</svg><p class="note">Rules and fuzzy matching are exact on standard names and fail on invented ones. ML generalises best to invented names but guesses wrong on ${pct(1 - g('ml', 'standard_vocabulary'), 0)} of standard ones. Hybrid keeps the dictionary and inherits some fuzzy errors.</p>`;
  tabs('fFlowSeg', CL.map(n => [n, CS[n].name]), FL.c, k => { FL.c = k; drawFlow(); }); drawFlow();
  $('fTop').innerHTML = `<table class="t"><thead><tr><th>Client label</th><th>True account</th><th class="n">Rows</th><th class="n">Hybrid</th></tr></thead><tbody>${M('hybrid', 'test').top_client_labels.map(t => `<tr><td class="mono" style="font-size:.7rem">${esc(t.label)}<span class="faint" style="display:block;font-family:var(--sans);font-size:.68rem">${esc(cname(t.client_id))}</span></td><td>${esc(t.true_name)}</td><td class="n">${num(t.n)}</td><td class="n ${t.acc < .9 ? 'red' : ''}"><b>${pct(t.acc, 0)}</b></td></tr>`).join('')}</tbody></table>`;
  const tc = X.tagCounts, order = ['label_variant', 'missing_account', 'uncategorized_label', 'legacy_label', 'mojibake', 'date_alt_format', 'missing_date', 'date_excel_serial', 'amount_format', 'credit_as_negative_debit', 'drcr_suffix', 'sign_flip', 'amount_digit_error', 'duplicate_exact', 'duplicate_near', 'blank_description', 'whitespace'];
  $('fInv').innerHTML = `<table class="t"><thead><tr><th>Injected error</th><th class="n">Rows</th></tr></thead><tbody>${order.filter(k => tc[k]).map(k => `<tr><td>${esc(tagText(k))}</td><td class="n">${num(tc[k])}</td></tr>`).join('')}</tbody></table><p class="note">Every injected error is logged against the answer key. Some rows never reach the file at all.</p>`;
}
function drawFlow() {
  const cf = M(FL.c, 'test').confusions.slice(0, 10), tot = cf.reduce((a, c) => a + c.n, 0), lt = {}, rt = {}, nm = {};
  cf.forEach(c => { lt[c.true] = (lt[c.true] || 0) + c.n; rt[c.pred] = (rt[c.pred] || 0) + c.n; nm[c.true] = c.true_name; nm[c.pred] = c.pred_name; });
  const LK = Object.keys(lt).sort((a, b) => lt[b] - lt[a]), RK = Object.keys(rt).sort((a, b) => rt[b] - rt[a]);
  const gap = 16, H = 320, k = (H - gap * (Math.max(LK.length, RK.length) - 1)) / tot, w = 800, xl = 250, xr = 560, nw = 10;
  const pos = (keys, tt) => { let y = 6; const o = {}; keys.forEach(key => { o[key] = {y, h: Math.max(3, tt[key] * k), off: 0}; y += o[key].h + gap; }); return [o, y]; };
  const [L, yl] = pos(LK, lt), [Rr, yr] = pos(RK, rt), h = Math.max(yl, yr) + 4, byL = {}, byR = {};
  cf.forEach(c => { (byL[c.true] = byL[c.true] || []).push(c); (byR[c.pred] = byR[c.pred] || []).push(c); });
  Object.values(byL).forEach(a => a.sort((p, q) => Rr[p.pred].y - Rr[q.pred].y)); Object.values(byR).forEach(a => a.sort((p, q) => L[p.true].y - L[q.true].y));
  const yL = {}, yR = {};
  LK.forEach(key => byL[key].forEach(c => { const hh = c.n * k; yL[c.true + '|' + c.pred] = [L[key].y + L[key].off + hh / 2, hh]; L[key].off += hh; }));
  RK.forEach(key => byR[key].forEach(c => { const hh = c.n * k; yR[c.true + '|' + c.pred] = Rr[key].y + Rr[key].off + hh / 2; Rr[key].off += hh; }));
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="misposting flows">`;
  cf.forEach(c => { const a = yL[c.true + '|' + c.pred], b = yR[c.true + '|' + c.pred], mid = (xl + xr) / 2; s += `<path d="M ${xl + nw} ${a[0]} C ${mid} ${a[0]}, ${mid} ${b}, ${xr} ${b}" fill="none" stroke="${RED}" stroke-opacity=".4" stroke-width="${Math.max(1.5, a[1])}"><title>${esc(c.true_name)} to ${esc(c.pred_name)}: ${num(c.n)} rows</title></path>`; });
  LK.forEach(key => { const v = L[key]; s += `<rect x="${xl}" y="${v.y}" width="${nw}" height="${v.h}" fill="${INK}"/><text class="k" x="${xl - 10}" y="${v.y + v.h / 2 + 4}" text-anchor="end">${esc(nm[key])} <tspan style="font-family:var(--mono);font-weight:500;fill:${INK2}">${num(lt[key])}</tspan></text>`; });
  RK.forEach(key => { const v = Rr[key]; s += `<rect x="${xr}" y="${v.y}" width="${nw}" height="${v.h}" fill="${INK}"/><text class="k" x="${xr + nw + 10}" y="${v.y + v.h / 2 + 4}">${esc(nm[key])} <tspan style="font-family:var(--mono);font-weight:500;fill:${INK2}">${num(rt[key])}</tspan></text>`; });
  $('fFlow').innerHTML = `<div class="legend"><span>Left: where the row belongs</span><span>Right: where ${CS[FL.c].name} posted it</span></div>` + s + '</svg>';
}
