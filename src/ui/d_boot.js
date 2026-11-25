/* ===== BOOT, PRESENTER, KEYS ===== */
const SECS = [['s01', 'Console'], ['s02', 'Network effect'], ['s03', 'Scoreboard'], ['s04', 'Failure modes'], ['s05', 'Audit trail'], ['s06', 'Trust and cost'], ['s07', 'Learning'], ['s08', 'Inspector'], ['s09', 'Spec']];
function setClient(cid) { $('cClient').value = cid; $('cClient').dispatchEvent(new Event('change')); }
function conOpenTop() { const l = cd().labels.find(x => !CON.mem[x.label]); if (l) { CON.open = l.label; renderQueue(); } }
const SCENES = [
  {sec: 's01', frame: 'cIn', title: 'Messy in', pts: ['Eight firms, eight export formats. This one is a Sage layout at high messiness.', 'Every underlined cell is a real injected error, known from the answer key.', 'Titles, subtotals and repeated headers are in the file too.'], act: () => { setClient('northgate_construction'); }},
  {sec: 's01', frame: 'cOutWrap', title: 'Clean it live', pts: ['Six stages in one pass: parse, normalize, map, dedupe, balance, triage.', 'Every row is graded against the key as it lands. Click a row for its passport.'], act: () => { conReset(); conRun(false); }},
  {sec: 's01', frame: 'cQ', title: 'Teach it once', pts: ['The queue is sorted by rows affected. Confirm the top label with Enter.', 'Every matching row flips, and the score moves for the whole file.', 'Then scrub the year: review rate with and without memory.'], act: () => { conRun(true); conOpenTop(); }},
  {sec: 's02', frame: 'netChart', title: 'Network effect', pts: ['Each firm the agent has seen makes the next firm easier.', 'Overall accuracy plateaus near four firms. Client vocabulary keeps rising.'], act: () => {}},
  {sec: 's03', frame: 'sbDot', title: 'Scoreboard', pts: ['Four held-out firms. Cutoffs and thresholds were tuned on the other four.', 'Hybrid leads on most firms. Read the matrix for where it does not.'], act: () => { SB.split = 'test'; renderScoreboard(); document.querySelectorAll('#sbSeg button').forEach(b => b.classList.toggle('on', b.dataset.k === 'test')); }},
  {sec: 's05', frame: 'auDetail', title: 'Audit trail', pts: ['Pick any account. The panel shows why it is off and the raw rows behind it.', 'Rows are labelled with the rule that mapped them.'], act: () => { AU.cid = 'northgate_construction'; $('auSel').value = AU.cid; AU.sort = 'diff'; AU.open = AUD[AU.cid].accounts[0].code; renderAudit(); }},
  {sec: 's06', frame: 'ecChart', title: 'Cost and limits', pts: ['Move the cost of a slip and watch the best threshold shift.', 'Limits are in the spec: synthetic errors, shared vendor names, four test firms.'], act: () => {}}];
const PR = {on: false, i: 0, talk: true};
function frameOn(id) { document.querySelectorAll('.frame').forEach(e => e.classList.remove('frame')); const e = id && $(id); if (e && PR.on) e.classList.add('frame'); }
function goSec(id) { const e = $(id); if (e) window.scrollTo({top: e.getBoundingClientRect().top + window.scrollY - 12, behavior: 'auto'}); }
function scene(i) {
  PR.i = clamp(i, 0, SCENES.length - 1); const s = SCENES[PR.i]; s.act(); goSec(s.sec); frameOn(s.frame);
  $('talk').innerHTML = `<h4><span>Scene ${PR.i + 1} / ${SCENES.length}: ${s.title}</span><span class="mono faint" style="letter-spacing:0">N next / B back / T hide</span></h4><ul>${s.pts.map(p => `<li>${p}</li>`).join('')}</ul>`;
}
function presenter(on) { PR.on = on == null ? !PR.on : on; $('btnPresent').classList.toggle('on', PR.on); $('talk').classList.toggle('on', PR.on && PR.talk); if (PR.on) scene(PR.i); else frameOn(null); }
function projector(on) { document.documentElement.classList.toggle('proj', on == null ? !document.documentElement.classList.contains('proj') : on); $('btnProj').classList.toggle('on', document.documentElement.classList.contains('proj')); }
function spy() { const y = window.scrollY + 140; let cur = SECS[0][0]; SECS.forEach(([id]) => { if ($(id).offsetTop <= y) cur = id; }); document.querySelectorAll('#railNav a').forEach(a => a.classList.toggle('on', a.dataset.s === cur)); }
document.addEventListener('keydown', ev => {
  const t = ev.target, typing = t && (t.tagName === 'INPUT' && t.type === 'text' || t.tagName === 'TEXTAREA');
  if (ev.key === 'Escape') { if (CON.open) { CON.open = null; renderQueue(); } else if (CON.pp) { CON.pp = null; renderOut(); } else if (PR.on) presenter(false); return; }
  if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === 'Enter' && CON.open && !(t && /BUTTON|SELECT/.test(t.tagName))) { ev.preventDefault(); confirmOpen(); return; }
  const k = ev.key.toLowerCase(); let h = true;
  if (/^[1-9]$/.test(k)) goSec('s0' + k); else if (k === 'r') conRun(ev.shiftKey); else if (k === 's') conStep(); else if (k === 'x') conReset(); else if (k === 'u') undo();
  else if (k === 'p') presenter(); else if (k === 'f') projector(); else if (k === 'n' && PR.on) scene(PR.i + 1); else if (k === 'b' && PR.on) scene(PR.i - 1);
  else if (k === 't' && PR.on) { PR.talk = !PR.talk; $('talk').classList.toggle('on', PR.talk); } else h = false;
  if (h) ev.preventDefault();
});
function boot() {
  $('railNav').innerHTML = SECS.map(([id, n], i) => `<a href="#${id}" data-s="${id}"><b>0${i + 1}</b><span>${n}</span></a>`).join('');
  $('railNav').querySelectorAll('a').forEach(a => a.onclick = ev => { ev.preventDefault(); goSec(a.dataset.s); });
  const H = M('hybrid', 'test').overall, Dv = M('hybrid', 'dev').overall;
  $('heroMeta').innerHTML = `<b>${num(R.dataset.rows)}</b> rows / <b>${CLIENTS.length}</b> firms / <b>${DEMO.accounts.length}</b> accounts<br>4 cleaners / 20 injected error types<br>TEST <b>n=${num(H.n)}</b> / DEV <b>n=${num(Dv.n)}</b><br>Synthetic data. Exact answer key.`;
  initConsole(); renderNetwork();
  tabs('sbSeg', [['test', 'Held-out test'], ['dev', 'Dev'], ['all', 'All firms']], SB.split, k => { SB.split = k; renderScoreboard(); }); renderScoreboard();
  renderFailures(); initAudit(); renderTrust(); renderLearning(); renderInspector(); renderSpec();
  $('btnPresent').onclick = () => presenter(); $('btnProj').onclick = () => projector();
  window.addEventListener('scroll', spy, {passive: true}); spy();
  window.__lce = {CON, conRun, conReset, conStep, confirm: (l, c) => { CON.mem[l] = {code: c}; CON.hist.push(l); renderAll(); }, totals, scene, presenter, effectOf, cd};
}
boot();
