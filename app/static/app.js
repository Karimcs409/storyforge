// StoryForge front-end (vanilla JS, no build step)
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const S = { tab: "studio", src: "match", voice: "official", lang: "en", lvoice: "official", llang: "en",
  data: null, sid: null, cur: 0, live: { pages: [], extras: null, theme: null, lang: "en", es: null, minute: 0 } };

function toast(t) { const el = $("#toast"); el.textContent = t; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2200); }
async function api(url, opt = {}) {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opt, body: opt.body ? JSON.stringify(opt.body) : undefined });
  if (!r.ok) throw new Error((await r.text()).slice(0, 200));
  return r.json();
}
function seg(id, key) {
  $(id).addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    $(id).querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
    S[key] = b.dataset.v; if (key === "src") { $("#srcMatch").hidden = S.src !== "match"; $("#srcArticle").hidden = S.src !== "article"; }
  });
}

// ---------------- icons ----------------
const ICON = {
  ball: '<circle cx="32" cy="32" r="26" fill="#fff"/><path d="M32 18l10 7-4 12H26l-4-12z" fill="#111"/><path d="M32 6v12M42 25l13-4M38 37l8 12M26 37l-8 12M22 25L9 21" stroke="#111" stroke-width="3"/>',
  "card-yellow": '<rect x="18" y="8" width="28" height="44" rx="4" fill="#ffd400" transform="rotate(12 32 30)"/>',
  "card-red": '<rect x="18" y="8" width="28" height="44" rx="4" fill="#ff3b3b" transform="rotate(12 32 30)"/>',
  whistle: '<circle cx="24" cy="38" r="14" fill="none" stroke="#fff" stroke-width="5"/><path d="M30 26h26v12H36" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><path d="M24 12v8M12 16l5 6M36 16l-5 6" stroke="#fff" stroke-width="4" stroke-linecap="round"/>',
  swap: '<path d="M10 22h40l-10-10M54 42H14l10 10" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>',
  stat: '<rect x="10" y="34" width="10" height="20" rx="2" fill="#fff"/><rect x="27" y="20" width="10" height="34" rx="2" fill="#fff"/><rect x="44" y="10" width="10" height="44" rx="2" fill="#fff"/>',
  quote: '<path d="M12 40c0-12 6-20 16-24l2 5c-6 3-8 7-8 11h8v16H12zM36 40c0-12 6-20 16-24l2 5c-6 3-8 7-8 11h8v16H36z" fill="#fff"/>',
  ticket: '<path d="M8 20h48v8a5 5 0 000 10v8H8v-8a5 5 0 000-10z" fill="#fff"/><path d="M38 20v26" stroke="#111" stroke-width="2" stroke-dasharray="3 3"/>',
  none: ""
};
const icon = n => ICON[n] ? `<svg class="ico" viewBox="0 0 64 64">${ICON[n]}</svg>` : "";
const initials = n => n === "own goal" ? "OG" : n.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase();
function shade(hex, f) { const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  [r, g, b] = [r, g, b].map(c => Math.max(0, Math.min(255, Math.round(c * f)))); return `rgb(${r},${g},${b})`; }

function rgba(hex, f, a) { const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [n >> 16, (n >> 8) & 255, n & 255].map(c => Math.max(0, Math.min(255, Math.round(c * f)))); return `rgba(${r},${g},${b},${a})`; }

// ---------------- phone rendering ----------------
function deck() {
  if (S.tab === "live") {
    const L = S.live, d = L.pages.map(p => ({ kind: "page", page: p, flags: [], photo: p.photo }));
    if (L.extras && L.extras.approved) { L.extras.quiz.forEach((q, i) => d.push({ kind: "quiz", q, i, n: L.extras.quiz.length })); d.push({ kind: "poll", poll: L.extras.poll }); }
    return { items: d, theme: L.theme, lang: L.lang };
  }
  if (!S.data) return { items: [] };
  const st = S.data.story, rep = S.data.report, items = st.pages.map((p, i) => ({ kind: "page", page: p, idx: i, flags: rep.page_flags[i] || [], photo: (st.media || {})[i] }));
  const cta = items.findIndex(x => x.page.type === "cta");
  const extra = st.quiz.map((q, i) => ({ kind: "quiz", q, i, n: st.quiz.length })).concat([{ kind: "poll", poll: st.poll }]);
  if (cta >= 0) items.splice(cta, 0, ...extra); else items.push(...extra);
  return { items, theme: S.data.theme, lang: S.data.lang };
}

function renderPhone() {
  const { items, theme, lang } = deck();
  const view = $("#pageView");
  if (!items.length) { $("#bars").innerHTML = ""; if (!view.querySelector(".skeleton")) view.innerHTML = `<div class="emptyMsg">${S.tab === "live" ? "Approved live pages appear here" : "Pick a match and draft a Story"}</div>`; view.className = "empty"; return; }
  S.cur = Math.max(0, Math.min(S.cur, items.length - 1));
  $("#bars").innerHTML = items.map((_, i) => `<i class="${i < S.cur ? "done" : i === S.cur ? "cur" : ""}"></i>`).join("");
  view.className = ""; view.innerHTML = pageHTML(items[S.cur], theme, lang);
  view.querySelectorAll(".opt").forEach(b => b.onclick = e => { e.stopPropagation(); answer(b, items[S.cur]); });
  document.querySelectorAll("#pagesEd .card").forEach(c => c.classList.toggle("cur", items[S.cur].idx === +c.dataset.i));
}

function pageHTML(it, th, lang) {
  th = th || { colors: ["#1f2a44", "#c9a227"] };
  const c0 = th.colors[0], rtl = lang === "ar" ? 'dir="rtl"' : "";
  // keep minutes like 16' as one LTR run inside Arabic text (LRI ... PDI)
  const T = s => lang === "ar" ? esc(s).replace(/(\d+)(['’′])/g, "⁦$1$2⁩").replace(/(\d+\s*[-‑–]\s*\d+)/g, "⁦$1⁩") : esc(s);
  const tone = { cover: [1, .35], moment: [.9, .25], stat: [.45, .15], quote: [.6, .2], cta: [1.1, .4], quiz: [.55, .18], poll: [.7, .22] };
  const type = it.kind === "page" ? it.page.type : it.kind, [a, b] = tone[type] || [1, .3];
  const bg = `background:linear-gradient(160deg,${shade(c0, a)} 0%,${shade(c0, b)} 70%,#000 100%)`;
  const club = `<div class="club"><span>${esc(th.home_short || "")}${S.tab === "live" ? ' <span class="live">LIVE</span>' : ""}</span><span>${esc(type)}</span></div>`;
  if (it.kind === "quiz") {
    return `<div class="pg" ${rtl} style="${bg}">${club}<div class="mid">${icon("stat").replace('class="ico"', 'class="ico" style="width:40px;height:40px"')}
      <div style="font-size:12px;opacity:.75;font-weight:700;letter-spacing:.1em">TRIVIA QUIZ ${it.i + 1}/${it.n}</div>
      <h1 style="font-size:22px">${T(it.q.question)}</h1>
      <div>${it.q.options.map((o, i) => `<button class="opt" data-i="${i}">${esc(o)}</button>`).join("")}</div></div><div class="tpl">template: quiz</div></div>`;
  }
  if (it.kind === "poll") {
    return `<div class="pg" ${rtl} style="${bg}">${club}<div class="mid"><div style="font-size:12px;opacity:.75;font-weight:700;letter-spacing:.1em">POLL</div>
      <h1 style="font-size:24px">${T(it.poll.question)}</h1>
      <div>${it.poll.options.map((o, i) => `<button class="opt" data-i="${i}"><span class="bar"></span><span style="position:relative">${esc(o)}</span></button>`).join("")}</div></div><div class="tpl">template: poll</div></div>`;
  }
  const p = it.page, who = (p.players_mentioned || []).slice(0, 3);
  let mid = "";
  if (p.type === "cover") {
    const sc = (p.headline.match(/\d+\s*[-–]\s*\d+/) || [th.score || ""])[0];
    mid = `${th.home ? `<div class="teams" ${rtl}><span>${esc(th.home)}</span><span>${esc(th.away)}</span></div>` : ""}
      <div class="score">${esc(sc)}</div><h1>${T(p.headline)}</h1><p>${T(p.caption)}</p>`;
  } else if (p.type === "cta") {
    mid = `${icon(p.icon || "ticket")}<h1>${T(p.headline)}</h1><p>${T(p.caption)}</p><div class="cta">${esc(p.cta_text || "Learn more")}</div>`;
  } else {
    mid = `<div style="display:flex;align-items:center;gap:14px">${p.minute != null ? `<div class="minute" dir="ltr">${p.minute}'</div>` : ""}${icon(p.icon)}</div>
      <h1>${T(p.headline)}</h1><p>${T(p.caption)}</p>
      ${who.length ? `<div class="who">${who.map(n => `<div class="ini" title="${esc(n)}">${esc(initials(n))}</div>`).join("")}</div>` : ""}`;
  }
  const ph = it.photo;
  // AI-picked photo: team-colour wash on top, dark fade at the bottom so white text stays readable
  const pbg = ph ? `background:linear-gradient(180deg,${rgba(c0, .9, .8)} 0%,${rgba(c0, .6, .3)} 28%,rgba(0,0,0,.15) 45%,rgba(0,0,0,.82) 75%,#000 100%),url('/media/${ph.file}') center/cover` : bg;
  const chip = ph ? `🤖 <span><b>${ph.guarded ? "Swapped by code guard:" : "AI-picked:"}</b> ${esc(ph.reason || p.media_hint)}</span>`
                  : `📷 <span>${esc(p.media_hint)}</span>`;
  return `<div class="pg ${ph ? "photo" : ""} ${it.flags && it.flags.length ? "flagged" : ""}" ${rtl} style="${pbg}">${club}<div class="mid">${mid}</div>
    <div class="media" dir="ltr">${chip}</div><div class="tpl">template: ${esc(p.template)}${ph ? " · photo: Pexels" : ""}</div></div>`;
}

function answer(btn, it) {
  const opts = btn.parentElement.querySelectorAll(".opt");
  if (it.kind === "quiz") {
    opts.forEach((o, i) => { if (i === it.q.correct_index) o.classList.add("right"); else if (o === btn) o.classList.add("wrong"); });
  } else {  // poll: fake demo distribution
    const n = opts.length, pick = +btn.dataset.i, w = [...Array(n)].map((_, i) => i === pick ? 45 : Math.round(55 / (n - 1)));
    opts.forEach((o, i) => { o.querySelector(".bar").style.width = w[i] + "%"; o.querySelector("span:last-child").textContent += `  ${w[i]}%`; o.onclick = null; });
  }
}
$("#tapNext").onclick = () => { S.cur++; renderPhone(); };
$("#tapPrev").onclick = () => { S.cur--; renderPhone(); };
document.addEventListener("keydown", e => { if (e.target.matches("input,textarea,select")) return;
  if (e.key === "ArrowRight") { S.cur++; renderPhone(); } if (e.key === "ArrowLeft") { S.cur--; renderPhone(); } });

// ---------------- studio ----------------
async function loadMatches(feedSel, matchSel) {
  matchSel.innerHTML = "<option>loading…</option>";
  try { const ms = await api(`/api/matches?feed=${feedSel.value}`); matchSel.innerHTML = ms.map(m => `<option value="${m.id}">${esc(m.label)}</option>`).join(""); }
  catch (e) { matchSel.innerHTML = "<option>feed unavailable</option>"; toast("Feed unavailable (network?)"); }
}

$("#gen").onclick = async () => {
  const btn = $("#gen"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Drafting…';
  $("#pageView").innerHTML = `<div class="skeleton"><div><span class="spin"></span><br><br>Drafting Story, Trivia Quiz, Poll &amp; categories…</div></div>`;
  $("#bars").innerHTML = ""; const t0 = performance.now();
  try {
    const body = { voice: S.voice, lang: S.lang, short_title_max: +$("#shortMax").value || 20, ...(S.src === "article" ? { article: $("#article").value } : { feed: $("#feed").value, match_id: $("#match").value }) };
    const d = await api("/api/story", { method: "POST", body });
    S.data = d; S.sid = d.id; S.cur = 0; S.wall = ((performance.now() - t0) / 1000).toFixed(1);
    renderAll();
  } catch (e) { toast("Error: " + e.message); renderPhone(); }
  btn.disabled = false; btn.textContent = "✦ Draft Story";
};

function renderAll() { renderPhone(); renderEditor(); renderCost(); if (S.right === "cms") renderCms(); }

// ---------------- CMS export: what an editor would otherwise type into the CMS ----------------
S.right = "review";
$("#rightSeg").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  S.right = b.dataset.v;
  $("#rightSeg").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
  $("#reviewPane").hidden = S.right !== "review"; $("#cmsPane").hidden = S.right !== "cms";
  if (S.right === "cms") renderCms();
});
const TITLE_META = {
  internal_title: ["Internal Title", "built in code (identifier)"],
  long_display_title: ["Long Display Title", "rectangular thumbnails"],
  short_display_title: ["Short Display Title", "circular thumbnails, max set per category"],
  eyebrow: ["Eyebrow", "tagline, soft limit 20"],
  seo_title: ["SEO title", "Google Web Story metadata"],
  seo_description: ["SEO description", "Google Web Story metadata"],
};
async function renderCms() {
  const d = S.data, pane = $("#cmsPane");
  if (!d || !S.sid) { pane.innerHTML = '<p class="hint">Draft a Story first.</p>'; return; }
  let ex;
  try { ex = await api(`/api/story/${S.sid}/cms`); } catch (e) { pane.innerHTML = '<p class="hint">Could not build the export.</p>'; return; }
  const tf = (d.report && d.report.title_flags) || {};
  const lim = { short_display_title: d.story.short_title_max || 20, internal_title: 250, long_display_title: 60,
                eyebrow: 20, seo_title: 60, seo_description: 155 };
  const dir = d.lang === "ar" ? 'dir="rtl"' : "";
  const titles = Object.keys(TITLE_META).filter(k => (ex.titles || {})[k] !== undefined).map(k => {
    const v = ex.titles[k], f = tf[k] || [], ro = k === "internal_title";
    const field = k === "seo_description"
      ? `<textarea ${dir} rows="2" data-t="${k}" ${ro ? "readonly" : ""}>${esc(v)}</textarea>`
      : `<input ${dir} data-t="${k}" value="${esc(v)}" ${ro ? "readonly" : ""}>`;
    return `<div class="card tcard"><div class="row"><b>${TITLE_META[k][0]}</b><span class="hint">${TITLE_META[k][1]}</span>
      <span style="margin-left:auto" class="chip ${f.length ? "bad" : "ok"}">${f.length ? "⚑ " + f.length : "✓"}</span></div>
      ${field}<div class="cnt ${v.length > lim[k] ? "over" : ""}">${v.length}/${lim[k]}</div>
      ${f.length ? `<div class="flags">${f.map(x => `<div>${esc(x)}</div>`).join("")}</div>` : ""}</div>`;
  }).join("");
  const quiz = ex.engagement_units[0], poll = ex.engagement_units[1];
  const thumb = b => b ? `<img class="bgthumb" src="/media/${b.file}" alt="">` : "";
  const quizHTML = `<div class="card"><div class="row"><b>Trivia Quiz</b><span class="chip">${quiz.questions.length} questions</span>
      <span style="margin-left:auto" class="chip ${quiz.rule_issues.length ? "bad" : "ok"}">${quiz.rule_issues.length ? "⚑ " + quiz.rule_issues.length : "ready ✓"}</span></div>
    <div class="row" style="margin-top:6px">${thumb(quiz.default_background)}${thumb(quiz.results_background)}<span class="hint">Default and results backgrounds, picked from the media library</span></div>
    ${quiz.questions.map((q, i) => `<div class="qrow" ${dir}><div><b>Q${i + 1}.</b> ${esc(q.title)}</div>
      ${q.answers.map(a => `<div class="ans ${a.correct ? "ok" : ""}">${a.correct ? "● correct" : "○"} ${esc(a.text)}</div>`).join("")}
      <div class="${q.verified_in_code ? "ver" : "ver no"}">${q.verified_in_code ? "✓ correct answer verified in code (" + esc(q.check) + ")" : "⚑ " + q.flags.map(esc).join("; ")}</div></div>`).join("")}
    ${quiz.rule_issues.length ? `<div class="flags">${quiz.rule_issues.map(x => `<div>${esc(x)}</div>`).join("")}</div>` : ""}</div>`;
  const pollHTML = `<div class="card"><div class="row"><b>Poll</b><span class="chip">${poll.answers.length} text answers</span>
      ${poll.side_by_side ? '<span class="chip">side by side</span>' : ""}
      <span style="margin-left:auto" class="chip ${poll.rule_issues.length ? "bad" : "ok"}">${poll.rule_issues.length ? "⚑" : "ready ✓"}</span></div>
    <div class="row" style="margin-top:6px">${thumb(poll.background)}<span class="hint">Question text added to the background</span></div>
    <div class="qrow" ${dir}><b>${esc(poll.question)}</b>${poll.answers.map(a => `<div class="ans">○ ${esc(a)}</div>`).join("")}</div></div>`;
  pane.innerHTML = `<p class="hint">Everything an editor would otherwise type into the CMS by hand, checked the same way as the pages.</p>
    <div class="row" style="gap:6px;margin:8px 0"><button class="ghost" id="cmsCopy">Copy JSON</button><button class="ghost" id="cmsDl">Download JSON</button></div>
    <h3>Titles</h3>${titles}<h3>Engagement Units</h3>${quizHTML}${pollHTML}
    <h3>Categories</h3><div class="tags">${(ex.categories || []).map(c => `<span class="cat">${esc(c)}</span>`).join("")}${(ex.tags || []).map(t => `<span>#${esc(t)}</span>`).join("")}</div>`;
  pane.querySelectorAll("[data-t]").forEach(inp => inp.oninput = () => {
    d.story.titles[inp.dataset.t] = inp.value;
    inp.parentElement.querySelector(".cnt").textContent = `${inp.value.length}/${lim[inp.dataset.t]}`;
    clearTimeout(S.titleT);
    S.titleT = setTimeout(async () => { await save(); if (S.right === "cms") renderCms(); }, 700);
  });
  $("#cmsCopy").onclick = async () => {
    try { await navigator.clipboard.writeText(JSON.stringify(ex, null, 2)); toast("CMS export copied"); } catch (e) { toast("Copy failed"); }
  };
  $("#cmsDl").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(ex, null, 2)], { type: "application/json" }));
    a.download = `storyforge-cms-${S.sid}.json`; a.click();
  };
}

function renderCost() {
  if (S.tab === "live") { const L = S.live; $("#cost").innerHTML = L.n ? `live pages: <b>${L.n}</b> drafted · avg <b>${(L.ms / L.n / 1000).toFixed(1)} s</b>/page · <b>$${L.usd.toFixed(4)}</b> total` : ""; return; }
  if (!S.data) return $("#cost").innerHTML = "";
  const L = S.data.logs, usd = L.reduce((a, l) => a + l.usd, 0), tin = L.reduce((a, l) => a + l.tokens_in, 0), tout = L.reduce((a, l) => a + l.tokens_out, 0);
  const first = L[0], r = S.data.report;
  $("#cost").innerHTML = `Story drafted in <b>${(first.ms / 1000).toFixed(1)} s</b> · <b>$${usd.toFixed(4)}</b> · ${tin.toLocaleString()} in / ${tout.toLocaleString()} out tokens · ${L.length} call${L.length > 1 ? "s" : ""} · ${esc(first.model)}`
    + (S.data.theme.credit ? `<br><span style="opacity:.7">${esc(S.data.theme.credit)}</span>` : "");
}

function renderEditor() {
  const d = S.data; if (!d) return;
  const r = d.report, nflag = Object.values(r.page_flags).filter(x => x.length).length + r.story_flags.length;
  const appr = d.approved.filter(Boolean).length;
  $("#status").className = "chip " + (appr === d.approved.length ? "ok" : nflag ? "bad" : "warn");
  $("#status").textContent = appr === d.approved.length ? "approved ✓" : `${appr}/${d.approved.length} approved`;
  $("#report").innerHTML = `<div class="report">
    <div><b class="${nflag ? "" : "ver"}">${nflag}</b><span>fact flags</span></div>
    <div><b class="ver ${r.quiz_verified < r.quiz_total ? "no" : ""}">${r.quiz_verified}/${r.quiz_total}</b><span>quiz verified</span></div>
    <div><b>${d.story.pages.length}</b><span>pages</span></div></div>
    ${r.story_flags.length ? `<div class="flags">${r.story_flags.map(f => `<div>${esc(f)}</div>`).join("")}</div>` : ""}
    <div style="margin-top:8px;font-weight:700">${esc(d.story.title)}</div>
    <div class="tags">${d.story.categories.map(c => `<span class="cat">${esc(c)}</span>`).join("")}${d.story.tags.map(t => `<span>#${esc(t)}</span>`).join("")}</div>
    <div style="display:flex;gap:6px;margin-top:10px"><button class="ghost" id="apprAll">Approve all</button></div>`;
  $("#apprAll").onclick = () => { d.approved = d.approved.map(() => true); save(); };
  const dir = d.lang === "ar" ? 'dir="rtl"' : "";
  $("#pagesEd").innerHTML = d.story.pages.map((p, i) => {
    const fl = r.page_flags[i] || [];
    return `<div class="card ${d.approved[i] ? "appr" : ""}" data-i="${i}">
      <div class="row"><b>${i + 1}</b><span class="chip">${p.type}</span><span class="chip">${p.template}</span>${p.minute != null ? `<span class="chip">${p.minute}'</span>` : ""}
        <span style="margin-left:auto" class="chip ${fl.length ? "bad" : "ok"}">${fl.length ? "⚑ " + fl.length : "facts ✓"}</span></div>
      ${(d.story.media || {})[i] ? `<div class="thumb"><img src="/media/${d.story.media[i].file}" alt=""><span>${d.story.media[i].guarded ? '<b class="g">code guard swap:</b> ' : "🤖 "}${esc(d.story.media[i].reason)}</span></div>` : ""}
      <input ${dir} data-f="headline" value="${esc(p.headline)}"><div class="cnt ${p.headline.length > 40 ? "over" : ""}">${p.headline.length}/40</div>
      <textarea ${dir} data-f="caption" rows="2">${esc(p.caption)}</textarea><div class="cnt ${p.caption.length > 140 ? "over" : ""}">${p.caption.length}/140</div>
      ${fl.length ? `<div class="flags">${fl.map(f => `<div>${esc(f)}</div>`).join("")}</div>` : ""}
      <input data-note placeholder="Note for regenerate (optional), e.g. 'more dramatic'">
      <div class="acts"><button class="btn-ok ${d.approved[i] ? "on" : ""}" data-a="ok">${d.approved[i] ? "✓ Approved" : "Approve"}</button>
        <button class="ghost" data-a="regen">↻ Regenerate</button></div></div>`;
  }).join("");
  $("#pagesEd").querySelectorAll(".card").forEach(card => {
    const i = +card.dataset.i;
    card.onclick = e => { if (!e.target.closest("input,textarea,button")) { S.cur = deck().items.findIndex(x => x.idx === i); renderPhone(); } };
    card.querySelectorAll("[data-f]").forEach(inp => inp.oninput = () => {
      d.story.pages[i][inp.dataset.f] = inp.value; d.approved[i] = false;
      inp.nextElementSibling.textContent = `${inp.value.length}/${inp.dataset.f === "headline" ? 40 : 140}`;
      S.cur = deck().items.findIndex(x => x.idx === i); renderPhone(); debounceSave();
    });
    card.querySelector('[data-a="ok"]').onclick = () => { d.approved[i] = !d.approved[i]; save(); };
    card.querySelector('[data-a="regen"]').onclick = async e => {
      const b = e.target; b.innerHTML = '<span class="spin"></span>'; b.disabled = true;
      try { const nd = await api(`/api/story/${S.sid}/page/${i}/regenerate`, { method: "POST", body: { note: card.querySelector("[data-note]").value } });
        Object.assign(d, { story: nd.story, report: nd.report, logs: nd.logs, approved: nd.approved });
        toast(`Page ${i + 1} regenerated in ${(nd.log.ms / 1000).toFixed(1)} s`); S.cur = deck().items.findIndex(x => x.idx === i); renderAll();
      } catch (err) { toast("Error: " + err.message); b.textContent = "↻ Regenerate"; b.disabled = false; }
    };
  });
  renderExtrasEditor(d, r, dir);
}

// Trivia Quiz + Poll are editable too; every edit is re-checked against the source data in code
function renderExtrasEditor(d, r, dir) {
  const quizHTML = d.story.quiz.map((q, i) => { const f = r.quiz_flags[i] || [];
    return `<div class="card qz" data-q="${i}">
      <div class="row"><b>Q${i + 1}</b><span class="chip">${esc(q.kind)}</span>
        <span style="margin-left:auto" class="chip ${f.length ? "bad" : "ok"}">${f.length ? "⚑ not provable" : "✓ verified in code"}</span></div>
      <textarea ${dir} data-qf="question" rows="2">${esc(q.question)}</textarea>
      ${q.options.map((o, j) => `<label class="opt-ed"><input type="radio" name="qc${i}" value="${j}" ${j === q.correct_index ? "checked" : ""} title="correct answer">
        <input ${dir} data-qo="${j}" value="${esc(o)}"></label>`).join("")}
      <div class="${f.length ? "ver no" : "ver"}">${f.length ? "⚑ " + f.map(esc).join("; ") : `source answer: ${esc(q.answer_canonical)}`}</div></div>`; }).join("");
  const po = d.story.poll;
  $("#extrasEd").innerHTML = `<h3>Trivia Quiz <span class="hint" style="text-transform:none;letter-spacing:0">· ● = correct answer</span></h3>${quizHTML}
    <h3>Poll</h3><div class="card" data-poll>
      <textarea ${dir} data-pf="question" rows="2">${esc(po.question)}</textarea>
      ${po.options.map((o, j) => `<input ${dir} data-po="${j}" value="${esc(o)}">`).join("")}</div>`;
  const showQuiz = i => { S.cur = deck().items.findIndex(x => x.kind === "quiz" && x.i === i); renderPhone(); };
  $("#extrasEd").querySelectorAll(".qz").forEach(card => {
    const i = +card.dataset.q, q = d.story.quiz[i];
    const sync = () => {  // for EN the editor's chosen option becomes the answer the code verifies
      if (d.lang === "en") q.answer_canonical = q.options[q.correct_index];
      showQuiz(i); debounceSave();
    };
    card.querySelector("[data-qf]").oninput = e => { q.question = e.target.value; sync(); };
    card.querySelectorAll("[data-qo]").forEach(inp => inp.oninput = () => { q.options[+inp.dataset.qo] = inp.value; sync(); });
    card.querySelectorAll("input[type=radio]").forEach(rb => rb.onchange = () => { q.correct_index = +rb.value; sync(); });
  });
  const pc = $("#extrasEd").querySelector("[data-poll]"), showPoll = () => { S.cur = deck().items.findIndex(x => x.kind === "poll"); renderPhone(); };
  pc.querySelector("[data-pf]").oninput = e => { po.question = e.target.value; showPoll(); debounceSave(); };
  pc.querySelectorAll("[data-po]").forEach(inp => inp.oninput = () => { po.options[+inp.dataset.po] = inp.value; showPoll(); debounceSave(); });
}

let saveT; function debounceSave() { clearTimeout(saveT); saveT = setTimeout(save, 600); }
async function save() {
  const d = S.data;
  try { const nd = await api(`/api/story/${S.sid}`, { method: "PUT", body: { story: d.story, approved: d.approved } });
    const ae = document.activeElement, qcard = ae && ae.closest && ae.closest(".qz, [data-poll]");
    const focusKey = qcard && ae.matches("input:not([type=radio]),textarea") ? { pos: ae.selectionStart,
      sel: (qcard.dataset.q !== undefined ? `.qz[data-q="${qcard.dataset.q}"] ` : "[data-poll] ") +
           ["qf", "qo", "pf", "po"].map(k => ae.dataset[k] !== undefined ? `[data-${k}="${ae.dataset[k]}"]` : "").join("") } : null;
    d.report = nd.report; const active = document.activeElement, sel = active && active.dataset ? [active.closest(".card")?.dataset.i, active.dataset.f, active.selectionStart] : null;
    renderEditor(); renderPhone();
    if (sel && sel[1]) { const el = document.querySelector(`#pagesEd .card[data-i="${sel[0]}"] [data-f="${sel[1]}"]`); if (el) { el.focus(); el.setSelectionRange(sel[2], sel[2]); } }
    if (focusKey) { const el = document.querySelector(focusKey.sel); if (el) { el.focus(); try { el.setSelectionRange(focusKey.pos, focusKey.pos); } catch (e) {} } }
    if (nd.status === "approved") toast("Story approved ✓ — ready to publish");
  } catch (e) { toast("Save failed"); }
}

// ---------------- live ----------------
$("#liveGo").onclick = () => {
  const L = S.live;
  if (L.es) { L.es.close(); L.es = null; $("#liveGo").textContent = "● Go live"; return; }
  Object.assign(L, { pages: [], extras: null, n: 0, ms: 0, usd: 0, lang: S.llang, feed: $("#lfeed").value, match: $("#lmatch").value });
  $("#ticker").innerHTML = ""; $("#queueList").innerHTML = ""; S.cur = 0; renderPhone(); renderCost();
  const q = new URLSearchParams({ feed: $("#lfeed").value, match_id: $("#lmatch").value, voice: S.lvoice, lang: S.llang, interval: $("#speed").value });
  const es = new EventSource("/api/live/stream?" + q); L.es = es; $("#liveGo").textContent = "■ Stop";
  es.addEventListener("meta", e => { L.theme = JSON.parse(e.data).theme; });
  es.addEventListener("event", e => {
    const ev = JSON.parse(e.data), key = ["goal", "red_card", "sub", "half_time", "full_time"].includes(ev.type);
    const txt = { goal: `⚽ GOAL ${ev.player} (${ev.score_after})`, red_card: `🟥 Red card ${ev.player}`, yellow_card: `🟨 ${ev.player}`,
      sub: `🔁 ${ev.player_in} for ${ev.player_out}`, half_time: `Half-time ${ev.score}`, full_time: `Full-time ${ev.score}` }[ev.type] || ev.type;
    $("#ticker").insertAdjacentHTML("afterbegin", `<li class="new ${key ? "key" : ""}"><b>${ev.minute}'</b>${esc(txt)}${key ? ' <span class="spin" style="width:10px;height:10px"></span>' : ""}</li>`);
    $("#meter").innerHTML = `<span style="color:var(--bad)">● LIVE</span> ${ev.minute}'`;
  });
  es.addEventListener("draft", e => {
    const d = JSON.parse(e.data); L.n++; L.ms += d.latency_ms; L.usd += d.log.usd; renderCost();
    document.querySelectorAll("#ticker .spin").forEach(s => s.remove());
    queueCard(d);
  });
  es.addEventListener("extras", e => { const x = JSON.parse(e.data); L.extras = x; L.usd += x.log.usd; renderCost(); extrasCard(x); });
  es.addEventListener("error", e => { if (e.data) toast("LLM error: " + JSON.parse(e.data).msg); });
  es.addEventListener("done", () => { es.close(); L.es = null; $("#liveGo").textContent = "● Go live"; $("#meter").textContent = "Full-time"; $("#saveLive").disabled = false; });
};

function queueCard(d) {
  // Live approval card. Every edit is re-checked by the fact guard on the server, and a page with an open
  // flag can't be approved (same rule as the Editor tab): the editor fixes it, regenerates nothing, or skips it.
  const p = d.page, dir = S.live.lang === "ar" ? 'dir="rtl"' : "", L = S.live;
  let flags = d.flags.slice(), editing = false, checkT;
  const el = document.createElement("div"); el.className = "card";
  el.innerHTML = `<div class="row"><b>${d.event.minute}'</b><span class="chip">${d.event.type.replace("_", " ")}</span>
    <span class="lat">⚡ ${(d.latency_ms / 1000).toFixed(1)} s</span><span style="margin-left:auto" class="chip st"></span></div>
    <div class="view" ${dir}><div style="font-weight:800;margin-top:6px">${esc(p.headline)}</div><div class="hint">${esc(p.caption)}</div></div>
    <div class="flags"></div>
    <div class="acts"><button class="btn-ok" data-a="ok">Approve</button><button class="ghost" data-a="edit">Edit</button><button class="ghost" data-a="skip">Skip</button></div>`;
  const ok = el.querySelector('[data-a="ok"]');
  const paint = (checking) => {
    const st = el.querySelector(".st");
    st.className = "chip st " + (checking ? "warn" : flags.length ? "bad" : "ok");
    st.textContent = checking ? "checking…" : flags.length ? "⚑ " + flags.length : "facts ✓";
    el.querySelector(".flags").innerHTML = flags.map(f => `<div>${esc(f)}</div>`).join("");
    ok.disabled = checking || flags.length > 0;
    ok.textContent = flags.length ? "Fix flags to approve" : "Approve";
    ok.title = flags.length ? "This page has a fact flag: edit it or skip it" : "";
  };
  const current = () => {
    const h = el.querySelector("[data-f=headline]"), c = el.querySelector("[data-f=caption]");
    return h ? { ...p, headline: h.value, caption: c.value } : p;
  };
  const recheck = async () => {
    paint(true);
    try {
      const r = await api("/api/live/check", { method: "POST", body: { feed: L.feed, match_id: L.match, event_minute: d.event.minute, page: current(), lang: L.lang } });
      flags = r.flags;
    } catch (e) { flags = ["could not re-check this edit (server error)"]; }
    paint(false);
  };
  ok.onclick = async () => {
    if (editing) await recheck();  // never trust an edit that wasn't checked
    if (flags.length) return toast("Fix the flagged facts first");
    Object.assign(p, current());
    L.pages.push(p); S.cur = L.pages.length - 1; renderPhone(); el.remove(); toast("Page added to live Story");
  };
  el.querySelector('[data-a="edit"]').onclick = () => {
    if (editing) return;
    editing = true;
    el.querySelector(".view").innerHTML = `<input ${dir} data-f="headline" value="${esc(p.headline)}"><textarea ${dir} data-f="caption" rows="2">${esc(p.caption)}</textarea>`;
    el.querySelectorAll("[data-f]").forEach(inp => inp.oninput = () => { paint(true); clearTimeout(checkT); checkT = setTimeout(recheck, 500); });
  };
  el.querySelector('[data-a="skip"]').onclick = () => el.remove();
  paint(false);
  $("#queueList").prepend(el);
}

function extrasCard(x) {
  const ok = Object.values(x.quiz_flags).filter(f => !f.length).length, dir = S.live.lang === "ar" ? 'dir="rtl"' : "";
  const el = document.createElement("div"); el.className = "card";
  el.innerHTML = `<div class="row"><b>FT</b><span class="chip">Trivia Quiz + Poll</span><span style="margin-left:auto" class="chip ${ok === x.quiz.length ? "ok" : "bad"}">${ok}/${x.quiz.length} verified</span></div>
    <div ${dir} class="hint" style="margin-top:6px">${x.quiz.map(q => "• " + esc(q.question)).join("<br>")}<br>Poll: ${esc(x.poll.question)}</div>
    <div class="tags">${x.categories.map(c => `<span class="cat">${esc(c)}</span>`).join("")}</div>
    <div class="acts"><button class="btn-ok" data-a="ok">Approve</button><button class="ghost" data-a="skip">Skip</button></div>`;
  el.querySelector('[data-a="ok"]').onclick = () => { x.approved = true; S.cur = S.live.pages.length; renderPhone(); el.remove(); };
  el.querySelector('[data-a="skip"]').onclick = () => el.remove();
  $("#queueList").prepend(el);
}

$("#saveLive").onclick = async () => {
  const L = S.live, x = L.extras || { quiz: [], poll: { question: "", options: [] }, categories: [], tags: [] };
  const r = await api("/api/story/save", { method: "POST", body: { data: { story: { title: "Live Story", pages: L.pages, quiz: x.approved ? x.quiz : [], poll: x.poll, categories: x.categories, tags: x.tags }, voice: S.lvoice, lang: L.lang, theme: L.theme } } });
  toast(`Live Story saved (#${r.id})`);
};

// ---------------- tabs & init ----------------
document.querySelector(".tabs").onclick = e => {
  const b = e.target.closest("button"); if (!b) return; S.tab = b.dataset.tab;
  document.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x === b));
  const live = S.tab === "live";
  $("#studioCtl").hidden = live; $("#liveCtl").hidden = !live; $("#editor").hidden = live; $("#queue").hidden = !live;
  S.cur = live ? Math.max(0, S.live.pages.length - 1) : 0; renderPhone(); renderCost();
};

(async () => {
  seg("#srcSeg", "src"); seg("#voiceSeg", "voice"); seg("#langSeg", "lang"); seg("#lvoiceSeg", "lvoice"); seg("#llangSeg", "llang");
  const cfg = await api("/api/config");
  const opts = cfg.feeds.map(f => `<option value="${f}">${f === "replay" ? "Fictional matches (JSON replay)" : "StatsBomb Open Data (real)"}</option>`).join("");
  $("#feed").innerHTML = opts; $("#lfeed").innerHTML = opts;
  $("#meter").textContent = `${cfg.models.main} · strict JSON schema · fact guard on`;
  $("#feed").onchange = () => loadMatches($("#feed"), $("#match")); $("#lfeed").onchange = () => loadMatches($("#lfeed"), $("#lmatch"));
  loadMatches($("#feed"), $("#match")); loadMatches($("#lfeed"), $("#lmatch"));
})();
