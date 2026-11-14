// Admin page: review, AI drafts, exports, analysis.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const STATUS_LABEL = { pending_review: "Pending review", approved: "Approved", needs_edit: "Needs edit", rejected: "Rejected" };
let TOKEN = sessionStorage.getItem("aq_admin_token") || "";

async function call(method, url, data) {
  const res = await fetch(url, {
    method, headers: { "X-Admin-Token": TOKEN, ...(data ? { "Content-Type": "application/json" } : {}) },
    body: data ? JSON.stringify(data) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error(json.error || `Request failed (${res.status})`); e.status = res.status; e.body = json; throw e; }
  return json;
}

// ---------------------------------------------------------------- login
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  TOKEN = $("#token").value;
  await tryOpen();
});

async function tryOpen() {
  try {
    await loadStats();
    sessionStorage.setItem("aq_admin_token", TOKEN);
    $("#login").hidden = true;
    $("#app").hidden = false;
  } catch (err) {
    $("#loginErr").hidden = !TOKEN;
    $("#loginErr").textContent = err.message;
  }
}
if (TOKEN) tryOpen();

// ---------------------------------------------------------------- tabs
document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-tab]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== b.dataset.tab; });
  if (b.dataset.tab === "overview" || b.dataset.tab === "drafts") loadStats();
  if (b.dataset.tab === "review") loadQuestions();
}));

// ---------------------------------------------------------------- overview
async function loadStats() {
  const s = await call("GET", "/api/admin/stats");
  const q = s.questions, total = Object.values(q).reduce((a, b) => a + b, 0);
  const llmTotal = Object.values(s.llm_questions).reduce((a, b) => a + b, 0);
  const cards = [
    ["Participants", s.participants], ["Finished the pre-test", s.pre_done], ["Finished the post-test", s.post_done],
    ["In-game answers", s.answers], ["Questions approved", `${q.approved || 0} / ${total}`],
    ["AI-drafted questions approved", `${s.llm_questions.approved || 0} / ${llmTotal}`], ["Team test runs", s.test_runs],
  ];
  $("#stats").innerHTML = cards.map(([k, v]) => `<div><b>${esc(v)}</b>${esc(k)}</div>`).join("") +
    (s.demo_approved ? `<p class="error" style="grid-column:1/-1">${s.demo_approved} question(s) were auto-approved with --approve-all-demo and have not been reviewed. Review them before the pilot (filter the Review tab by Approved).</p>` : "");
  const need = { 1: 5, 2: 5, 3: 5, 4: 5, 5: 4 };
  $("#levelTable").innerHTML = `<tr><th>Level</th><th>Approved</th><th>Needed</th><th>Status</th></tr>` +
    [1, 2, 3, 4, 5].map((l) => {
      const a = s.approved_by_level[l] || 0;
      return `<tr><td>${l}</td><td>${a}</td><td>${need[l]}</td><td>${a >= need[l] ? "Ready" : "Not playable yet"}</td></tr>`;
    }).join("");
  $("#geminiStatus").textContent = s.gemini_configured
    ? `Gemini is configured (model: ${s.gemini_model}).`
    : "Gemini is not configured: add GEMINI_API_KEY to the .env file and restart run.py.";
  $("#runTable").innerHTML = `<tr><th>When</th><th>Level</th><th>Difficulty</th><th>Asked</th><th>Returned</th><th>Failed checks</th><th>Added</th><th>Error</th></tr>` +
    s.llm_runs.map((r) => `<tr><td>${esc(r.created_at)}</td><td>${r.level}</td><td>${esc(r.difficulty)}</td><td>${r.n_requested}</td>
      <td>${r.n_returned}</td><td>${r.n_failed_checks}</td><td>${r.n_inserted}</td><td>${esc(r.error || "")}</td></tr>`).join("");
  return s;
}

// ---------------------------------------------------------------- review
$("#reviewer").value = localStorage.getItem("aq_reviewer") || "";
$("#reviewer").addEventListener("change", (e) => localStorage.setItem("aq_reviewer", e.target.value));
$("#fStatus").addEventListener("change", loadQuestions);
$("#fLevel").addEventListener("change", loadQuestions);

async function loadQuestions() {
  const p = new URLSearchParams();
  if ($("#fStatus").value) p.set("status", $("#fStatus").value);
  if ($("#fLevel").value) p.set("level", $("#fLevel").value);
  const qs = await call("GET", "/api/admin/questions?" + p);
  $("#qCount").textContent = `${qs.length} question(s)`;
  $("#qList").innerHTML = qs.length ? qs.map(qHTML).join("") : `<p class="muted">No questions match this filter.</p>`;
  $("#qList").querySelectorAll("[data-review]").forEach((b) => b.addEventListener("click", () => review(b)));
}

function opts(q, lang) {
  const letters = q.question_type === "tf" ? "AB" : "ABCD";
  return `<ol type="A">${[...letters].map((l) =>
    `<li class="${l === q.correct_answer ? "right" : ""}">${esc(q[`option_${l.toLowerCase()}_${lang}`])}</li>`).join("")}</ol>`;
}

function qHTML(q) {
  return `<article class="q" id="q_${q.question_id}">
    <div class="meta"><b>${esc(q.question_id)}</b><span>Level ${q.level}</span><span>${esc(q.difficulty)}</span>
      <span>${esc(q.question_type)}</span><span class="chip ${q.review_status}">${STATUS_LABEL[q.review_status]}</span>
      <span>Drafted by ${esc(q.drafted_by || "")}</span>${q.reviewer ? `<span>Reviewed by ${esc(q.reviewer)}${q.review_date ? ` on ${esc(q.review_date)}` : ""}</span>` : ""}</div>
    <div><p class="qt">${esc(q.question_en)}</p>${opts(q, "en")}<p class="expl">${esc(q.explanation_en)}</p></div>
    <div lang="hi"><p class="qt">${esc(q.question_hi)}</p>${opts(q, "hi")}<p class="expl">${esc(q.explanation_hi)}</p></div>
    <div class="facts">${q.facts.map((f) => `<div><b>${esc(f.fact_id)}</b> ${esc(f.statement)} <a href="${esc(f.source_url.split("; ")[0])}" target="_blank" rel="noopener">${esc(f.source_org.split("; ")[0])}</a></div>`).join("")}</div>
    <div class="actions">
      <input placeholder="Notes (what to fix, why rejected)" value="${esc(q.review_notes || "")}" data-notes="${q.question_id}">
      <button class="small-btn ok" data-review="approved" data-q="${q.question_id}">Approve</button>
      <button class="small-btn edit" data-review="needs_edit" data-q="${q.question_id}">Needs edit</button>
      <button class="small-btn no" data-review="rejected" data-q="${q.question_id}">Reject</button>
    </div>
  </article>`;
}

async function review(btn) {
  const qid = btn.dataset.q, reviewer = $("#reviewer").value.trim();
  if (!reviewer) { alert("Enter the reviewer's name at the top first."); $("#reviewer").focus(); return; }
  const notes = document.querySelector(`[data-notes="${qid}"]`).value;
  try {
    await call("POST", `/api/admin/questions/${qid}/review`, { status: btn.dataset.review, reviewer, notes });
    const card = $(`#q_${qid}`);
    const chip = card.querySelector(".chip");
    chip.className = `chip ${btn.dataset.review}`;
    chip.textContent = STATUS_LABEL[btn.dataset.review];
    if ($("#fStatus").value === "pending_review") card.remove();
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------- AI drafts
$("#draftForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#dGo"), out = $("#draftResult");
  btn.disabled = true; btn.textContent = "Drafting…"; out.innerHTML = "";
  try {
    const r = await call("POST", "/api/admin/drafts", { level: +$("#dLevel").value, difficulty: $("#dDiff").value, n: +$("#dN").value });
    out.innerHTML = draftSummary(r);
  } catch (err) {
    out.innerHTML = `<p class="error">${esc(err.message)}</p>` + (err.body && err.body.n_requested ? draftSummary(err.body) : "");
  } finally {
    btn.disabled = false; btn.textContent = "Draft questions";
    loadStats();
  }
});

function draftSummary(r) {
  return `<p>Returned ${r.n_returned}, failed checks ${r.n_failed_checks}, added ${r.n_inserted} as pending review
    ${r.inserted_ids && r.inserted_ids.length ? `(${r.inserted_ids.map(esc).join(", ")}). Review them in the Review tab.` : "."}</p>
    ${r.error ? `<p class="error">${esc(r.error)}</p>` : ""}
    ${r.rejected && r.rejected.length ? `<p class="muted">Rejected by checks:</p><ul>${r.rejected.map((x) => `<li>${esc(x.question_en)}: ${esc(x.errors.join(", "))}</li>`).join("")}</ul>` : ""}`;
}

// ---------------------------------------------------------------- data + analysis
document.querySelectorAll("[data-export]").forEach((b) => b.addEventListener("click", async () => {
  const inc = $("#incTest").checked ? "1" : "0";
  const res = await fetch(`/api/admin/export/${b.dataset.export}?include_test=${inc}`, { headers: { "X-Admin-Token": TOKEN } });
  if (!res.ok) { alert("Export failed"); return; }
  const blob = await res.blob();
  const name = (res.headers.get("Content-Disposition") || "").split("filename=")[1] || "export.csv";
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: name });
  document.body.appendChild(a); a.click(); a.remove();
}));

$("#runAnalysis").addEventListener("click", async (e) => {
  const btn = e.target, out = $("#analysisOut");
  btn.disabled = true; btn.textContent = "Running…"; out.innerHTML = "";
  try {
    const r = await call("POST", "/api/admin/analysis", { include_test: $("#incTest").checked });
    out.innerHTML = `<p class="muted">Saved in <code>${esc(r.folder)}</code></p>
      <div class="charts">${r.charts.map((c) => `<img alt="${esc(c)}" src="/api/admin/analysis/${r.run_id}/charts/${encodeURIComponent(c)}?token=${encodeURIComponent(TOKEN)}">`).join("")}</div>
      <h3>Summary</h3><div class="summary">${esc(r.summary)}</div>`;
  } catch (err) {
    out.innerHTML = `<p class="error">${esc(err.message)}</p>${err.body && err.body.log ? `<pre class="summary">${esc(err.body.log)}</pre>` : ""}`;
  } finally {
    btn.disabled = false; btn.textContent = "Run analysis";
  }
});
