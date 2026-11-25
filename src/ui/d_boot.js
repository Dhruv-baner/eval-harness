/* ===== VIEWS, MENU, PRESENTER, KEYS ===== */
const VIEWS = [['s00', 'Overview', 'The result in four findings.'], ['s01', 'Console', 'Run the pipeline, then teach the agent a label.'], ['s02', 'Network effect', 'Accuracy against firms learned from.'], ['s03', 'Scoreboard', 'Four cleaners on held-out firms.'],
  ['s04', 'Failure modes', 'What breaks, and where the amounts went.'], ['s05', 'Audit trail', 'From a trial-balance line to the raw rows.'], ['s06', 'Trust and cost', 'Confidence, triage and reviewer hours.'], ['s07', 'Learning a firm', 'Memory and audit sampling.'],
  ['s08', 'Inspector', '516 sampled rows, one at a time.'], ['s09', 'Spec', 'Method, limits and next steps.']];
const VW = {cur: 's00', tabs: {}};
const panelsOf = id => [...document.querySelectorAll(`#${id} > .panel`)];
function setTab(id, key) {
  const ps = panelsOf(id); if (!ps.length) return; const k = key && ps.some(p => p.dataset.p === key) ? key : ps[0].dataset.p; VW.tabs[id] = k;
  ps.forEach(p => p.classList.toggle('on', p.dataset.p === k));
  document.querySelectorAll(`#${id} .subtabs button`).forEach(b => b.classList.toggle('on', b.dataset.k === k));
}
function openView(id, tab) {
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === id)); VW.cur = id;
  if (panelsOf(id).length) setTab(id, tab || VW.tabs[id]);
  window.scrollTo(0, 0); closeMenu(); frameOn(null);
  const i = VIEWS.findIndex(v => v[0] === id), v = VIEWS[i];
  $('where').innerHTML = i === 0 ? '' : `<b>${String(i).padStart(2, '0')}</b> ${v[1]}`;
  document.querySelectorAll('#menuNav a').forEach(a => a.classList.toggle('on', a.dataset.s === id));
  const vn = $('vnav'); vn.classList.toggle('wide', $(id).classList.contains('wide')); vn.hidden = i === 0;
  const pv = VIEWS[i - 1], nx = VIEWS[i + 1];
  vn.innerHTML = (i > 1 ? `<button data-go="${pv[0]}">&larr; ${String(i - 1).padStart(2, '0')} ${pv[1]}</button>` : '<span></span>') + (nx ? `<button class="primary" data-go="${nx[0]}">${String(i + 1).padStart(2, '0')} ${nx[1]} &rarr;</button>` : '<span></span>');
  vn.querySelectorAll('button').forEach(b => b.onclick = () => openView(b.dataset.go));
  try { history.replaceState(null, '', '#' + id + (VW.tabs[id] ? '/' + VW.tabs[id] : '')); } catch (e) { /* file origin */ }
}
const openTab = (id, key) => openView(id, key);
function openMenu() { $('menu').classList.add('on'); $('scrim').classList.add('on'); $('menu').setAttribute('aria-hidden', 'false'); $('menuBtn').setAttribute('aria-expanded', 'true'); }
function closeMenu() { $('menu').classList.remove('on'); $('scrim').classList.remove('on'); $('menu').setAttribute('aria-hidden', 'true'); $('menuBtn').setAttribute('aria-expanded', 'false'); }
function setClient(cid) { $('cClient').value = cid; $('cClient').dispatchEvent(new Event('change')); }
function conOpenTop() { const l = cd().labels.find(x => !CON.mem[x.label]); if (l) { CON.open = l.label; renderQueue(); } }

/* ---- overview ---- */
function renderHome() {
  const H = M('hybrid', 'test'), B = X.bootstrap.test, vt = n => H.by_label_tag.find(x => x.tag === n).acc, rc = H.review_curve.find(c => c.labels_reviewed === 10), cs = X.cold_start.hybrid.all.months, m12 = cs[cs.length - 1];
  $('homeFind').innerHTML = [
    ['F-01', pct(B.acc.hybrid.mean), 'Account accuracy of the hybrid cleaner on four held-out firms.', `Fuzzy ${pct(M('fuzzy', 'test').overall.acc)}, rules ${pct(M('rules', 'test').overall.acc)}, ML ${pct(M('ml', 'test').overall.acc)}. 95% interval ${pct(B.acc.hybrid.lo)} to ${pct(B.acc.hybrid.hi)}.`],
    ['F-02', pct(vt('client_specific_vocabulary'), 0), 'Accuracy on labels a firm invented for itself.', `Standard account names map at ${pct(vt('standard_vocabulary'), 1)}. Typos, case changes and renames are mostly handled.`],
    ['F-03', pct(rc.accuracy), 'Accuracy after a reviewer confirms ten unfamiliar labels.', `From ${pct(H.overall.acc)}. Unfamiliar vocabulary is the bottleneck, and a cheap one to fix.`],
    ['F-04', pct(m12.rev_mem / m12.n), 'Review rate by month twelve once the agent remembers confirmed labels.', `${pct(m12.rev_base / m12.n, 0)} without memory. Memory leaks mistakes for labels that map to two accounts; a 5% audit sample recovers most of that.`]]
    .map(f => `<div class="find"><span class="fc">${f[0]}</span><span class="fv">${f[1]}</span><span class="ft">${f[2]}<span>${f[3]}</span></span></div>`).join('');
  $('homeIdx').innerHTML = VIEWS.slice(1).map((v, i) => `<a href="#${v[0]}" data-s="${v[0]}"><b>0${i + 1}</b><span>${v[1]}</span><small>${v[2]}</small></a>`).join('');
  $('homeIdx').querySelectorAll('a').forEach(a => a.onclick = ev => { ev.preventDefault(); openView(a.dataset.s); });
  $('homeMeta').textContent = `${num(R.dataset.rows)} rows, ${CLIENTS.length} firms, ${DEMO.accounts.length} standard accounts, 20 injected error types. Test n=${num(H.overall.n)}, dev n=${num(M('hybrid', 'dev').overall.n)}. Synthetic data with an exact answer key.`;
}

/* ---- presenter ---- */
const SCENES = [
  {v: 's01', tab: 'run', frame: 'cIn', title: 'Messy in', pts: ['Eight firms, eight export formats. This one is a Sage layout at high messiness.', 'Every red underline is a real injected error, known from the answer key.', 'Titles, subtotals and repeated headers are in the file too.'], act: () => { setClient('northgate_construction'); }},
  {v: 's01', tab: 'run', frame: 'cPipe', title: 'Clean it live', pts: ['Six stages in one pass: parse, normalize, map, dedupe, balance, triage.', 'Every row is graded against the key as it lands. Click a row for its passport.'], act: () => { conReset(); conRun(false); }},
  {v: 's01', tab: 'teach', frame: 'cConfirm', title: 'Teach it once', pts: ['The queue is sorted by rows affected. Confirm the top label with Enter.', 'Every matching row flips, and the score moves for the whole file.'], act: () => { conRun(true); conOpenTop(); }},
  {v: 's01', tab: 'replay', frame: 'rpC', title: 'Replay the year', pts: ['Drag the month. Review rate with memory against without.', 'This is what confirming labels once buys over a year.'], act: () => {}},
  {v: 's02', frame: 'netChart', title: 'Network effect', pts: ['Each firm the agent has seen makes the next firm easier.', 'Overall accuracy plateaus near four firms. Client vocabulary keeps rising.'], act: () => {}},
  {v: 's03', tab: 'summary', frame: 'sbDot', title: 'Scoreboard', pts: ['Four held-out firms. Cutoffs and thresholds were tuned on the other four.', 'Hybrid leads on most firms. The by-firm tab shows where it does not.'], act: () => { SB.split = 'test'; renderScoreboard(); document.querySelectorAll('#sbSeg button').forEach(b => b.classList.toggle('on', b.dataset.k === 'test')); }},
  {v: 's05', frame: 'auDetail', title: 'Audit trail', pts: ['Pick any account. The panel shows why it is off and the raw rows behind it.', 'Each row carries the rule that mapped it.'], act: () => { AU.cid = 'northgate_construction'; $('auSel').value = AU.cid; AU.sort = 'diff'; AU.open = AUD[AU.cid].accounts[0].code; renderAudit(); }},
  {v: 's06', tab: 'econ', frame: 'ecChart', title: 'Cost and limits', pts: ['Move the cost of a slip and watch the best threshold shift.', 'Limits are in the spec: synthetic errors, shared vendor names, four test firms.'], act: () => {}}];
const PR = {on: false, i: 0, talk: true};
function frameOn(id) { document.querySelectorAll('.frame').forEach(e => e.classList.remove('frame')); const e = id && $(id); if (e && PR.on) e.classList.add('frame'); }
function scene(i) {
  PR.i = clamp(i, 0, SCENES.length - 1); const s = SCENES[PR.i];
  openView(s.v, s.tab); s.act(); frameOn(s.frame);
  $('talk').innerHTML = `<h4><span>Scene ${PR.i + 1} / ${SCENES.length}: ${s.title}</span><span class="mono faint" style="letter-spacing:0">N next, B back, T hide</span></h4><ul>${s.pts.map(p => `<li>${p}</li>`).join('')}</ul>`;
}
function presenter(on) { PR.on = on == null ? !PR.on : on; $('btnPresent').classList.toggle('on', PR.on); $('talk').classList.toggle('on', PR.on && PR.talk); closeMenu(); if (PR.on) scene(PR.i); else frameOn(null); }
function projector(on) { document.documentElement.classList.toggle('proj', on == null ? !document.documentElement.classList.contains('proj') : on); $('btnProj').classList.toggle('on', document.documentElement.classList.contains('proj')); }
const step = d => { const i = clamp(VIEWS.findIndex(v => v[0] === VW.cur) + d, 0, VIEWS.length - 1); openView(VIEWS[i][0]); };
document.addEventListener('keydown', ev => {
  const t = ev.target, typing = t && (t.tagName === 'INPUT' && t.type === 'text' || t.tagName === 'TEXTAREA');
  if (ev.key === 'Escape') { if ($('menu').classList.contains('on')) closeMenu(); else if (CON.open) { CON.open = null; renderQueue(); } else if (CON.pp) { CON.pp = null; renderOut(); } else if (PR.on) presenter(false); return; }
  if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === 'Enter' && CON.open && VW.cur === 's01' && !(t && /BUTTON|SELECT/.test(t.tagName))) { ev.preventDefault(); confirmOpen(); return; }
  const k = ev.key.toLowerCase(); let h = true;
  if (/^[0-9]$/.test(k)) openView('s0' + k); else if (ev.key === 'ArrowRight' && !(t && /SELECT|INPUT/.test(t.tagName))) step(1); else if (ev.key === 'ArrowLeft' && !(t && /SELECT|INPUT/.test(t.tagName))) step(-1);
  else if (k === 'm') ($('menu').classList.contains('on') ? closeMenu() : openMenu());
  else if (k === 'r') { openView('s01', 'run'); conRun(ev.shiftKey); } else if (k === 's') { openView('s01', 'run'); conStep(); } else if (k === 'x') conReset(); else if (k === 'u') undo();
  else if (k === 'p') presenter(); else if (k === 'f') projector(); else if (k === 'n' && PR.on) scene(PR.i + 1); else if (k === 'b' && PR.on) scene(PR.i - 1);
  else if (k === 't' && PR.on) { PR.talk = !PR.talk; $('talk').classList.toggle('on', PR.talk); } else h = false;
  if (h) ev.preventDefault();
});
function boot() {
  $('menuNav').innerHTML = VIEWS.map(([id, n, d], i) => `<a href="#${id}" data-s="${id}"><b>0${i}</b><span>${n}</span><small>${d}</small></a>`).join('');
  $('menuNav').querySelectorAll('a').forEach(a => a.onclick = ev => { ev.preventDefault(); openView(a.dataset.s); });
  document.querySelectorAll('.subtabs').forEach(st => { const id = st.dataset.view; st.innerHTML = panelsOf(id).map(p => `<button data-k="${p.dataset.p}">${p.dataset.label}</button>`).join(''); st.querySelectorAll('button').forEach(b => b.onclick = () => { setTab(id, b.dataset.k); frameOn(null); try { history.replaceState(null, '', '#' + id + '/' + b.dataset.k); } catch (e) { /* file origin */ } }); });
  $('menuBtn').onclick = () => $('menu').classList.contains('on') ? closeMenu() : openMenu(); $('menuClose').onclick = closeMenu; $('scrim').onclick = closeMenu;
  $('brand').onclick = () => openView('s00'); document.querySelectorAll('[data-go]').forEach(b => b.onclick = () => openView(b.dataset.go)); $('homeMenu').onclick = openMenu;
  renderHome(); initConsole(); renderNetwork();
  tabs('sbSeg', [['test', 'Held-out test'], ['dev', 'Dev'], ['all', 'All firms']], SB.split, k => { SB.split = k; renderScoreboard(); }); renderScoreboard();
  renderFailures(); initAudit(); renderTrust(); renderLearning(); renderInspector(); renderSpec();
  $('btnPresent').onclick = () => presenter(); $('btnProj').onclick = () => projector();
  const m = /^#(s0\d)(?:\/(\w+))?$/.exec(location.hash || ''); openView(m ? m[1] : 's00', m && m[2]);
  window.__lce = {CON, conRun, conReset, conStep, confirm: (l, c) => { CON.mem[l] = {code: c}; CON.hist.push(l); renderAll(); }, totals, scene, presenter, effectOf, cd, openView, openTab};
}
boot();
