// Fit Radar front end. Plain JavaScript, no build step. All data comes from /api/state.
// With no server (a static host such as GitHub Pages) it opens in Replay mode: it shows the saved demo run
// and keeps tags and approvals in this browser only.
const S = { tab: 'week', sel: null, filter: 'all', cSel: null, shownQueue: 8, data: null, poll: null, replay: false };
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const api = (path, body) => fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then((r) => { if (!r.ok) throw new Error(`${path}: ${r.status}`); return r.json(); });

// ---- Replay mode: no server, the saved run, tags and approvals kept in this browser ----
const REPLAY_RUN = 'demo_run/run.json';
const local = {
  get(key) { try { return JSON.parse(localStorage.getItem(`fitradar.${key}`)) || {}; } catch { return {}; } },
  set(key, value) { try { localStorage.setItem(`fitradar.${key}`, JSON.stringify(value)); } catch { /* storage blocked: kept for this visit only */ } return value; },
};
async function replayState() {
  const run = await fetch(REPLAY_RUN).then((r) => { if (!r.ok) throw new Error(`${REPLAY_RUN}: ${r.status}`); return r.json(); });
  const reader = run.provider === 'offline' ? 'Offline keyword rules (no model, no cost)' : `${run.models.fast} + ${run.models.strong}`;
  return { run, tags: local.get('tags'), actions: local.get('actions'), status: { running: false, step: 0, note: '', error: '' },
    steps: run.steps, next_reader: 'not available in Replay mode', run_reader: reader, stand_in: true, replay: true,
    follow_up_days: 28 };   // Replay has no server: keep equal to FOLLOW_UP_DAYS in config.py
}
function saveTag(id, tag) {
  if (!S.replay) return api('/api/tag', { comment_id: id, tag });
  const tags = { ...S.data.tags }; if (tag) tags[id] = tag; else delete tags[id];
  return Promise.resolve(local.set('tags', tags));
}
function saveAction(body) {
  if (!S.replay) return api('/api/action', body);
  const acts = { ...S.data.actions };
  if (body.decision) acts[body.key] = { decision: body.decision, fix: body.fix, label: body.label, note: body.note || '', when: new Date().toISOString().slice(0, 10) };
  else delete acts[body.key];
  return Promise.resolve(local.set('actions', acts));
}
function saveFixed(key, fixed) {
  if (!S.replay) return api('/api/fixed', { key, fixed });
  const acts = { ...S.data.actions };
  if (!acts[key] || acts[key].decision !== 'ok') return Promise.resolve(acts);
  const a = { ...acts[key] };
  if (fixed) {
    const today = new Date(); const due = new Date(today.getTime() + S.data.follow_up_days * 86400000);
    a.fixed_on = today.toISOString().slice(0, 10); a.result_due = due.toISOString().slice(0, 10);
  } else { delete a.fixed_on; delete a.result_due; }
  acts[key] = a;
  return Promise.resolve(local.set('actions', acts));
}

const REASONS = [
  { key: 'fit', label: 'Fit', color: 'var(--accent)' }, { key: 'quality', label: 'Quality', color: 'var(--accent-2)' },
  { key: 'colour', label: 'Colour differs', color: 'var(--amber)' }, { key: 'late', label: 'Arrived late', color: 'var(--amber-2)' },
  { key: 'other', label: 'Other', color: 'var(--grey)' }, { key: 'person', label: 'Unreadable or unclear', color: 'var(--ink)' },
];
const STATUS = { flag: ['Flag', 'p-flag'], watch: ['Watch', 'p-blue'], ok: ['OK', 'p-grey'], too_few: ['No call', 'p-grey'] };
const BY = { Code: 'p-code', Fast: 'p-blue', Strong: 'p-dark', Person: 'p-flag', 'Fast + code': 'p-blue' };
const TAGS = ['Fit: too small', 'Fit: too large', 'Fit: too short', 'Fit: too long', 'Quality', 'Colour', 'Changed mind', 'Cannot tell'];
const pillFor = (c) => (c.status === 'unreadable_rule' ? 'p-grey' : c.status === 'queued' ? 'p-dark' : c.group === 'fit' ? 'p-solid'
  : c.group === 'quality' ? 'p-blue' : c.group === 'other' ? 'p-grey' : 'p-flag');

async function load() {
  try {
    S.data = await api('/api/state');
  } catch {
    try {
      S.data = await replayState(); S.replay = true;
    } catch {
      $('week').textContent = '';
      $('main').innerHTML = '<p class="empty">Fit Radar could not load any data. Check your connection and reload the page.</p>';
      return;
    }
  }
  const run = S.data.run;
  if (run && !S.sel) S.sel = run.groups[0]?.key;
  render();
  if (S.data.status.running) startPolling();
}

function queueItems() {
  return (S.data.run?.comments || []).filter((c) => c.status === 'queued');
}
function queueLeft() {
  return queueItems().filter((c) => !S.data.tags[c.comment_id]).length;
}

function render() {
  const d = S.data, run = d.run;
  $('week').textContent = run ? `Week of ${run.week_of} · return comments and reviews` : 'No run yet';
  $('badge').hidden = !d.stand_in;
  $('reader').textContent = run ? `${S.replay ? 'Replay: saved demo run · ' : ''}Read by: ${d.run_reader}` : '';
  const approved = Object.values(d.actions).filter((a) => a.decision === 'ok').length;
  const tabs = [['week', 'This week'], ['comments', 'Comments'], ['queue', 'Review queue', run ? queueLeft() : ''],
    ['actions', 'Actions', approved || ''], ['run', 'Run and cost']];
  $('tabs').innerHTML = tabs.map(([k, label, n]) => `<button class="tab ${S.tab === k ? 'on' : ''}" data-tab="${k}">${label}${n !== undefined && n !== '' ? `<span class="count">${n}</span>` : ''}</button>`).join('');
  if (!run && S.tab !== 'run') { $('main').innerHTML = '<p class="empty">No run has finished yet. Open Run and cost and press Run.</p>'; return; }
  $('main').innerHTML = { week: viewWeek, comments: viewComments, queue: viewQueue, actions: viewActions, run: viewRun }[S.tab]();
}

// ---- This week -----------------------------------------------------------
function viewWeek() {
  const run = S.data.run, c = run.counts;
  const g = run.groups.find((x) => x.key === S.sel) || run.groups[0];
  const rows = run.groups.map((x) => `<button class="row g-vendors ${x.key === g.key ? 'on' : ''}" data-sel="${esc(x.key)}" aria-label="Open ${esc(x.vendor_id)} ${esc(x.category)}">
      <span class="mono"><b>${esc(x.vendor_id)}</b></span><span>${esc(x.category)}</span><span>${esc(x.signal)}</span>
      <span class="mono r"><b>${x.status === 'too_few' ? '–' : x.fit_return_rate_pct + '%'}</b></span><span class="mono r" style="color:var(--muted)">${x.category_median_pct}%</span>
      <span class="mono r">${x.returns_read}</span><span><span class="pill ${STATUS[x.status][1]}">${STATUS[x.status][0]}</span></span></button>`).join('');
  const share = run.reason_share;
  return `<div class="kpis">
    <div class="card kpi"><div class="l">Comments read (of ${c.in_file.toLocaleString()} in the file)</div><div class="v">${c.read.toLocaleString()}</div></div>
    <div class="card kpi"><div class="l">About fit</div><div class="v a">${c.fit_share_pct}%</div></div>
    <div class="card kpi"><div class="l">Vendors flagged</div><div class="v">${c.flagged}</div></div>
    <div class="card kpi"><div class="l">Need a person to read</div><div class="v">${queueLeft()}</div></div></div>
  <div class="split">
    <div class="card col"><h2>Where fit returns cluster</h2>
      <div class="tablewrap"><div class="rows">
        <div class="head g-vendors cap"><span>Vendor</span><span>Category</span><span>Signal</span><span class="r">Fit-return rate</span><span class="r">Category median</span><span class="r">Returns</span><span>Status</span></div>
        ${rows}</div></div>
      <div class="note" style="padding:2px 8px">A vendor is flagged when it has 30 or more returns, its fit-return rate is at least 1.5 times the category median, and one direction dominates.</div>
      <div class="col" style="border-top:1px solid var(--line);padding:10px 8px 0">
        <div class="h">Why this week's returns came back. Click a reason to read its comments.</div>
        <div class="bar">${REASONS.map((r) => `<button data-reason="${r.key}" aria-label="Show ${r.label} comments" style="width:${share[r.key]}%;background:${r.color}"></button>`).join('')}</div>
        <div class="chips">${REASONS.map((r) => `<button class="chip" data-reason="${r.key}"><span class="dot" style="background:${r.color}"></span><b>${r.label}</b> ${share[r.key]}%</button>`).join('')}</div>
      </div></div>
    <div class="card focus col">${detail(g)}</div></div>`;
}

function detail(g) {
  const act = S.data.actions[g.key];
  const top = `<div class="between"><div class="eyebrow">${esc(g.vendor_id)} · ${esc(g.category)} · ${esc(g.vendor_city)}</div><div class="note">${g.returns_read} returns read</div></div>`;
  if (g.status === 'too_few') {
    return `${top}<div class="headline">Only ${g.returns_read} returns from ${esc(g.vendor_id)} this period.</div>
      <div class="warnbox"><b>No recommendation shown.</b> Fit Radar needs at least 30 returns from a vendor before it calls a pattern. It says so here instead of guessing.</div>
      <div class="note">This vendor is checked again automatically each week.</div>`;
  }
  const max = Math.max(1, ...g.rate_by_size.map((s) => s.rate_pct));
  const sizes = g.rate_by_size.map((s) => `<div class="sizebar"><b style="width:26px">${esc(s.size)}</b><div class="t"><div class="f" style="width:${Math.round(95 * s.rate_pct / max)}%"></div></div><span class="mono r" style="width:36px">${s.rate_pct}%</span></div>`).join('');
  const tmax = Math.max(1, ...g.trend_6w);
  const charts = `<div class="pair"><div class="col grow" style="gap:5px"><div class="h">Fit-return rate by size bought</div>${sizes}</div>
    <div class="col" style="width:170px;gap:5px"><div class="h">Last 6 weeks</div><div class="trend">${g.trend_6w.map((t) => `<div style="height:${Math.round(68 * t / tmax)}px"></div>`).join('')}</div><div class="note" style="color:var(--ink)">${esc(g.trend_text)}</div></div></div>`;
  const numbers = `${g.fit_returns} of ${g.returns_read} returns are about fit. Fit-return rate ${g.fit_return_rate_pct}% against a category median of ${g.category_median_pct}%.`;
  if (g.status === 'ok') {
    return `${top}<div class="headline">Close to the category median. Nothing to act on.</div><div>${numbers}</div>${charts}`;
  }
  if (!g.finding) {
    return `${top}<div class="headline">Finding could not be verified.</div><div class="warnbox">The written finding failed its check twice, so only the numbers are shown.</div><div>${numbers}</div>${charts}`;
  }
  const f = g.finding;
  const quotes = g.quotes.slice(0, 2).map((q) => `<div class="quote">“${esc(q)}”</div>`).join('');
  const undo = `<button class="btn small" data-act="undo" data-key="${esc(g.key)}" style="margin-left:8px">Undo</button>`;
  let buttons = `<div class="col" style="gap:8px">
      <label class="h" for="fixtext">Wording for the listing team. Edit it if you want to change it.</label>
      <textarea id="fixtext" rows="3">${esc(f.suggested_fix)}</textarea>
      <label class="h" for="notetext">Your note (optional). If you send it back, say why.</label>
      <input id="notetext" type="text" maxlength="300" placeholder="For example: the vendor already changed this chart last week">
      <div class="btns"><button class="btn primary" data-act="ok" data-key="${esc(g.key)}">Approve size-chart fix</button><button class="btn" data-act="back" data-key="${esc(g.key)}">Send back</button></div>
      <div class="note">Approve adds the fix to the Actions tab for the listing team. Send back records your note and adds nothing to Actions. Neither sends a message to anyone.</div></div>`;
  if (g.status === 'watch') buttons = '<div class="note">Watch only. Nothing to approve yet.</div>';
  const noteLine = act?.note ? `<div style="font-weight:400;margin-top:6px">Your note: ${esc(act.note)}</div>` : '';
  if (act?.decision === 'ok') buttons = `<div class="okbox">Approved. Added to Actions for the listing team. ${undo}${noteLine}</div>`;
  if (act?.decision === 'back') buttons = `<div class="warnbox"><b>Sent back.</b> Nothing was added to Actions. The finding shows again whenever the data is read again. ${undo}${noteLine}</div>`;
  return `${top}<div class="headline">${esc(f.headline)}</div><div>${esc(f.evidence)}</div>${charts}
    <div class="col" style="gap:5px"><div class="h">What customers wrote</div>${quotes}</div>
    <div class="fix"><b>Suggested fix:</b> ${esc(f.suggested_fix)}</div>
    <div class="check"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg>
      <span>Checked: every figure in this finding matches the data${g.check === 'rewritten' ? ' (rewritten once)' : ''}</span></div>${buttons}`;
}

// ---- Comments ------------------------------------------------------------
function viewComments() {
  const all = S.data.run.comments;
  const list = all.filter((c) => S.filter === 'all' || c.group === S.filter);
  const shown = list.slice(0, 150);
  const sel = shown.find((c) => c.comment_id === S.cSel) || shown[0];
  const filters = [['all', 'All'], ...REASONS.map((r) => [r.key, r.label])];
  const rows = shown.map((c) => `<button class="row g-comments ${sel && c.comment_id === sel.comment_id ? 'on' : ''}" data-comment="${c.comment_id}" style="min-height:44px;font-size:14px">
      <i>“${esc(c.text)}”</i><span><span class="pill ${pillFor(c)}">${esc(c.reason_label)}</span></span>
      <span class="mono r">${c.confidence ? Math.round(c.confidence * 100) + '%' : '–'}</span><span class="note">${esc(c.read_by)}</span></button>`).join('');
  let side = '<p class="empty">No comments match.</p>';
  if (sel) {
    const kv = [['Reason', sel.reason_label], ['Body area', sel.body_area.replace('_', ' ')], ['Size bought', sel.size], ['Language', sel.language || '–'],
      ['How sure', sel.confidence ? Math.round(sel.confidence * 100) + '%' : '–'], ['Phrase it relied on', sel.evidence_phrase || '–']];
    side = `<div class="eyebrow">${sel.comment_id} · ${esc(sel.source)} · ${esc(sel.vendor_id)} ${esc(sel.category)}</div>
      <div class="qtext">“${esc(sel.text)}”</div><div class="note" style="font-size:14px">${esc(sel.meaning_en)}</div>
      <div><div class="h">What Fit Radar recorded</div>${kv.map(([k, v]) => `<div class="kv"><span>${k}</span><span>${esc(v)}</span></div>`).join('')}</div>
      <div class="col" style="gap:6px"><div class="h">The path it took</div>${sel.path.map((p) => `<div class="path"><span class="pill ${BY[p.by] || 'p-code'}">${esc(p.by)}</span><span>${esc(p.note)}</span></div>`).join('')}</div>`;
  }
  return `<div class="split"><div class="card col">
      <div class="between" style="padding:0 6px"><h2 style="padding:0">Every comment, and how it was read</h2><span class="note">Showing ${shown.length} of ${list.length.toLocaleString()}</span></div>
      <div class="chips" style="padding:0 6px">${filters.map(([k, l]) => `<button class="chip round ${S.filter === k ? 'on' : ''}" data-filter="${k}">${l}</button>`).join('')}</div>
      <div class="tablewrap"><div class="rows scroll"><div class="head g-comments cap"><span>What the customer wrote</span><span>Reason</span><span class="r">Sure?</span><span>Read by</span></div>${rows}</div></div>
    </div><div class="card focus col">${side}</div></div>`;
}

// ---- Review queue --------------------------------------------------------
function viewQueue() {
  const items = queueItems();
  const cards = items.slice(0, S.shownQueue).map((c) => {
    const tag = S.data.tags[c.comment_id];
    const foot = tag
      ? `<div class="tagged"><span>Tagged: ${esc(tag)}</span><button class="btn small" data-tag="" data-id="${c.comment_id}" style="border:none;min-height:36px">Undo</button></div>`
      : `<div class="btns" style="gap:8px">${TAGS.map((t) => `<button class="btn small" data-tag="${t}" data-id="${c.comment_id}">${t}</button>`).join('')}</div>`;
    return `<div class="card qcard"><div class="note">${esc(c.source)} · ${esc(c.vendor_id)} ${esc(c.category)} · size ${esc(c.size)}</div>
      <div class="qtext">“${esc(c.text)}”</div><div class="note" style="font-size:14px">${esc(c.meaning_en)}</div>
      <div style="font-size:14px">Model's best guess: <b>${esc(c.reason === 'unclear' ? 'none' : c.reason.replace('_', ' '))}</b> · ${Math.round(c.confidence * 100)}% sure</div>${foot}</div>`;
  }).join('');
  const more = items.length > S.shownQueue ? `<button class="btn" data-more="1" style="align-self:center">Show more</button>` : '';
  return `<div class="card between" style="padding:14px 18px;align-items:center"><div><div style="font-size:16px;font-weight:700">${queueLeft()} comments need a person this week</div>
      <div class="note" style="font-size:14px">Both readers were less than 70% sure. They are shown here, not guessed. Your tag is saved and used the next time the data is read.</div></div>
      <span class="note">Showing ${Math.min(S.shownQueue, items.length)} of ${items.length}</span></div>
    <div class="qgrid">${cards || '<p class="empty">Nothing is waiting.</p>'}</div>${more}`;
}

// ---- Actions -------------------------------------------------------------
function viewActions() {
  const acts = Object.entries(S.data.actions).filter(([, a]) => a.decision === 'ok');
  const days = S.data.follow_up_days || 28, weeks = Math.round(days / 7);
  const rows = acts.map(([key, a]) => {
    const fixed = !!a.fixed_on;
    const status = fixed ? `<span class="pill p-solid">Fixed on ${esc(a.fixed_on)}</span><div class="note">Result due ${esc(a.result_due)}</div>`
      : '<span class="pill p-flag">With listing team</span>';
    const progress = fixed
      ? `Not measured yet. Fit Radar compares this vendor's fit-return rate before and after, ${weeks} weeks from ${esc(a.fixed_on)}, against similar vendors that were not changed. The result is due ${esc(a.result_due)}.`
      : '';
    const button = fixed ? `<button class="btn small" data-fixed="0" data-key="${esc(key)}">Undo</button>`
      : `<button class="btn small primary" data-fixed="1" data-key="${esc(key)}">Mark as fixed</button>`;
    return `<div class="step"><div class="row g-actions" style="border:none;padding:0;min-height:0">
      <span class="mono"><b>${esc(a.label)}</b></span><span>${esc(a.fix)}</span><span class="note">${esc(a.when)}</span><span>${status}</span></div>
      ${a.note ? `<div class="note" style="margin-top:6px">Note: ${esc(a.note)}</div>` : ''}
      ${progress ? `<div class="quote" style="font-style:normal;margin-top:6px">${progress}</div>` : ''}<div style="margin-top:8px">${button}</div></div>`;
  }).join('');
  return `<div class="split"><div class="card col"><h2>Approved fixes, and whether they worked</h2>
      <div class="head g-actions cap"><span>Vendor</span><span>Fix</span><span>Approved</span><span>Status</span></div>
      ${rows || '<p class="empty">Nothing approved yet. Approve a finding on the This week tab and it appears here.</p>'}</div>
    <div class="card col" style="padding:18px 20px;gap:12px"><h2 style="padding:0">How a fix is judged</h2>
      <div>1. The listing team corrects the size chart for the flagged vendor and category.</div>
      <div>2. When it is marked as fixed, the ${weeks} weeks start. After that Fit Radar compares that vendor's fit-return rate before and after.</div>
      <div>3. It sets that against similar vendors that were not changed, so a general rise or fall is not counted as a win.</div>
      <div class="fix">All of this uses orders and returns data the business already holds.</div>
      <div class="note">Findings are reported by vendor, category and size chart, so they still apply when individual products are replaced.</div></div></div>`;
}

// ---- Run and cost --------------------------------------------------------
function viewRun() {
  const d = S.data, run = d.run, st = d.status;
  const steps = (run ? run.steps : d.steps).map((s) => {
    const done = st.running ? s.n < st.step : !!run, now = st.running && s.n === st.step;
    const count = st.running ? (done ? 'Done' : now ? (st.note || 'Working…') : 'Waiting') : (s.count || '');
    return `<div class="step row g-steps ${now ? 'now' : ''}" style="cursor:default"><span class="num ${done ? 'done' : now ? 'now' : ''}">${s.n}</span>
      <span><b>${esc(s.title)}</b><br><span class="note">${esc(s.desc)}</span></span>
      <span><span class="pill ${BY[s.by] || 'p-code'}">${esc(s.by)}</span></span>
      <span class="mono r" style="font-size:14px"><b>${esc(count)}</b></span><span class="mono r note">${!st.running && run ? s.seconds + 's' : ''}</span></div>`;
  }).join('');
  let cost = '<p class="empty">No run yet.</p>';
  if (run) {
    const c = run.cost;
    cost = c.lines.map((l) => `<div class="kv"><span style="color:var(--ink)"><b>${esc(l.label)}</b><br><span class="note">${l.calls} calls · ${esc(l.sum)} · ${l.seconds}s</span></span><span class="mono">$${l.usd.toFixed(4)}</span></div>`).join('')
      + `<div class="between" style="padding-top:6px"><b>Total for ${run.counts.read.toLocaleString()} comments</b><span class="total">$${c.usd.toFixed(2)} ≈ ₹${Math.round(c.inr).toLocaleString()}</span></div>
      <div class="note">${run.provider === 'offline' ? 'This run used offline keyword rules, so it cost nothing. A model run shows real token counts here.'
        : c.priced ? `At about ${c.weekly_comments.toLocaleString()} comments a week: roughly ₹${c.weekly_inr.toLocaleString()} a week. ₹${c.usd_to_inr} to the dollar.`
          : 'Prices for this provider are not set, so cost shows as zero. Set them in the environment (see docs/MODEL_OPTIONS.md).'}</div>`;
  }
  const err = (S.replay ? '<div class="warnbox"><b>Replay mode.</b> This is a saved run, shown without a server. Tags and approvals are kept in this browser only. To read new data, run Fit Radar on your own machine (see the README).</div>' : '')
    + (st.error ? `<div class="warnbox">${esc(st.error)}</div>` : '');
  const runButton = S.replay ? '' : `<button class="btn primary" data-run="1" ${st.running ? 'disabled' : ''}>${st.running ? 'Running…' : run ? 'Run again' : 'Run'}</button>`;
  const upload = S.replay ? '<div class="note">Uploading files needs Fit Radar running on your own machine.</div>'
    : `<label class="h" for="fc">Comments file (CSV)</label><input type="file" id="fc" accept=".csv">
        <label class="h" for="fu">Units-sold file (CSV)</label><input type="file" id="fu" accept=".csv">
        <div class="btns"><button class="btn small" data-upload="1">Use these files</button>${d.stand_in ? '' : '<button class="btn small" data-bundled="1">Back to bundled files</button>'}</div>
        <div class="note" id="upmsg"></div>`;
  return `${err}<div class="split"><div class="card col" style="padding:16px 18px">
      <div class="between" style="align-items:center"><div><div style="font-size:16px;font-weight:700">The run, step by step</div>
        <div class="note" style="font-size:14px">${st.running ? `Running step ${Math.min(st.step, 7)} of 7…` : run ? `Last run finished ${esc(run.finished_at)}.` : 'Nothing has run yet.'} Next run uses: ${esc(d.next_reader)}.</div></div>
        ${runButton}</div>
      <div class="tablewrap"><div class="rows">${steps}</div></div></div>
    <div class="col"><div class="card col" style="padding:16px 18px;gap:6px"><h2 style="padding:0">What this run cost</h2>${cost}</div>
      <div class="card col" style="padding:16px 18px;gap:8px"><h2 style="padding:0">Who does what</h2>
        <div class="path"><span class="pill p-code">Code</span><span>Joins, counts, rates, thresholds. Exact and free.</span></div>
        <div class="path"><span class="pill p-blue">Fast</span><span>Reads every comment and checks every finding.${run ? ' ' + esc(run.models.fast) + '.' : ''}</span></div>
        <div class="path"><span class="pill p-dark">Strong</span><span>Re-reads unclear comments and writes findings.${run ? ' ' + esc(run.models.strong) + '.' : ''}</span></div>
        <div class="path"><span class="pill p-flag">Person</span><span>Reads what neither reader could, and approves every fix.</span></div></div>
      <div class="card col" style="padding:16px 18px;gap:8px"><h2 style="padding:0">Data</h2>
        <div class="note">${d.stand_in ? 'Using the bundled stand-in files in data/.' : 'Using the files you uploaded.'}</div>
        ${upload}</div></div></div>`;
}

function startPolling() {
  clearInterval(S.poll);
  S.poll = setInterval(async () => {
    S.data.status = await api('/api/status');
    if (!S.data.status.running) { clearInterval(S.poll); await load(); return; }
    if (S.tab === 'run') render();
  }, 700);
}

document.addEventListener('click', async (e) => {
  const t = e.target.closest('button'); if (!t) return;
  const ds = t.dataset;
  if (ds.tab) { S.tab = ds.tab; render(); }
  else if (ds.sel) { S.sel = ds.sel; render(); }
  else if (ds.reason) { S.tab = 'comments'; S.filter = ds.reason; S.cSel = null; render(); }
  else if (ds.filter) { S.filter = ds.filter; S.cSel = null; render(); }
  else if (ds.comment) { S.cSel = ds.comment; render(); }
  else if (ds.more) { S.shownQueue += 8; render(); }
  else if (ds.tag !== undefined) { S.data.tags = await saveTag(ds.id, ds.tag || null); render(); }
  else if (ds.fixed !== undefined) {
    try { S.data.actions = await saveFixed(ds.key, ds.fixed === '1'); } catch { /* not approved: nothing to mark */ }
    render();
  } else if (ds.act) {
    const g = S.data.run.groups.find((x) => x.key === ds.key);
    const fix = ($('fixtext')?.value || '').trim() || g.finding?.suggested_fix || '';
    const note = ($('notetext')?.value || '').trim();
    const body = { key: ds.key, decision: ds.act === 'undo' ? null : ds.act, fix, note, label: `${g.vendor_id} ${g.category}` };
    S.data.actions = await saveAction(body); render();
  } else if (ds.run && !S.replay) { S.data.status = await api('/api/run', {}); render(); startPolling(); }
  else if (ds.upload) {
    const fc = $('fc').files[0], fu = $('fu').files[0];
    if (!fc || !fu) { $('upmsg').textContent = 'Choose both files first.'; return; }
    const form = new FormData(); form.append('comments', fc); form.append('units', fu);
    await fetch('/api/upload', { method: 'POST', body: form }); await load(); $('upmsg').textContent = 'Files saved. Press Run to read them.';
  } else if (ds.bundled) { await api('/api/use-bundled', {}); await load(); }
});

load();
