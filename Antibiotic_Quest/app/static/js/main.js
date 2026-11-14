// Antibiotic Quest - game flow: welcome → consent → pre-test → levels 1-5 → post-test → results.
import { api, ApiError } from "./api.js";
import { initAudio, speak, stop as stopAudio, hasVoice } from "./audio.js";
import { BoardView } from "./board.js";
import { t } from "./i18n.js";

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const STORE = "aq_state_v1";
const LADDER = 3, SNAKE = 3;

let CFG = null;        // /api/config
let board = null;      // BoardView (created the first time the board is shown)
let G = null;          // current level runtime
let Q = null;          // open question

const S = Object.assign({
  stage: "welcome", lang: "en", audio: false, pid: null, sid: null, testRun: false, level: 1, points: 0,
  order: { pre: null, post: null }, answers: { pre: {}, post: {} }, consent: { checked: false, demo: {} },
  levelStats: {}, scores: null,
}, JSON.parse(sessionStorage.getItem(STORE) || "{}"));
const save = () => sessionStorage.setItem(STORE, JSON.stringify(S));
const L = (key, ...a) => t(S.lang, key, ...a);

// ------------------------------------------------------------------ boot
init();

async function init() {
  wireTopbar();
  try {
    CFG = await api.config();
  } catch (e) {
    $("#screen").innerHTML = `<p class="error">${esc(L("errNetwork"))}</p>`;
    return;
  }
  initAudio(CFG.audio_files);
  if (S.stage === "game") S.stage = "intro";           // after a page refresh, resume at the level intro
  applyLang();
  render();
}

function wireTopbar() {
  document.querySelectorAll(".seg [data-lang]").forEach((b) =>
    b.addEventListener("click", () => { S.lang = b.dataset.lang; save(); applyLang(); rerenderAfterLang(); }));
  $("#soundBtn").addEventListener("click", () => {
    S.audio = !S.audio; save(); applyLang();
    if (!S.audio) stopAudio();
    else if (!hasVoice(S.lang)) showTip("noVoice");
  });
  $("#rollBtn").addEventListener("click", roll);
  $("#endBtn").addEventListener("click", endGameEarly);
  $("#hintBtn").addEventListener("click", showHint);
  $("#listenBtn").addEventListener("click", () => speakQuestion(true));
  $("#qnext").addEventListener("click", afterAnswer);
}

function applyLang() {
  document.documentElement.lang = S.lang;
  document.querySelectorAll(".seg [data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === S.lang)));
  $("#brand").textContent = L("title");
  $("#soundBtn").textContent = S.audio ? L("soundOn") : L("soundOff");
  $("#soundBtn").setAttribute("aria-pressed", String(S.audio));
  $("#rollBtn").textContent = L("roll");
  $("#pointsLabel").textContent = L("score");
  $("#bugsLabel").textContent = L("bugsCleared");
  $("#endBtn").textContent = L("endGame");
  $("#hintBtn").textContent = `${L("hint")} ${L("hintCost")}`;
  $("#listenBtn").textContent = L("listen");
  $("#qnext").textContent = L("next");
  updateLevelLabel();
}

function rerenderAfterLang() {
  if (S.stage === "game") {
    updatePanel();
    if (G && G.tip) showTip(G.tip.key, ...G.tip.args);
    if (Q) renderQuestion();
  } else {
    render();
  }
}

function updateLevelLabel() {
  const el = $("#levelLabel");
  const show = ["intro", "game", "levelEnd"].includes(S.stage) && CFG;
  el.hidden = !show;
  if (show) el.textContent = `${L("levelOf", S.level, CFG.levels.length)}: ${CFG.levels[S.level - 1].name[S.lang]}`;
}

function go(stage) { S.stage = stage; save(); render(); }

function render() {
  stopAudio();
  updateLevelLabel();
  const gameOn = S.stage === "game";
  $("#game").hidden = !gameOn;
  $("#screen").hidden = gameOn;
  if (gameOn) return;
  ({ welcome: renderWelcome, consent: renderConsent, pre: () => renderTest("pre"), intro: renderLevelIntro,
     levelEnd: renderLevelEnd, post: () => renderTest("post"), results: renderResults }[S.stage] || renderWelcome)();
  window.scrollTo(0, 0);
  $("#screen").focus({ preventScroll: true });
}

function showError(where, err) {
  const msg = err instanceof ApiError && err.status === 0 ? L("errNetwork") : err.message;
  let box = where.querySelector(".error");
  if (!box) { box = document.createElement("p"); box.className = "error"; box.setAttribute("role", "alert"); where.appendChild(box); }
  box.textContent = msg;
}

// ------------------------------------------------------------------ welcome
function dishSVG() {
  const bug = (x, y, r) => {
    let spikes = "";
    for (let k = 0; k < 10; k++) {
      const a = (Math.PI * 2 * k) / 10;
      spikes += `<circle cx="${x + Math.cos(a) * (r + 3)}" cy="${y + Math.sin(a) * (r + 3)}" r="${r * 0.28}"/>`;
    }
    return `<g fill="#d6457a">${spikes}<circle cx="${x}" cy="${y}" r="${r}"/></g>
      <circle cx="${x - r * 0.35}" cy="${y - r * 0.15}" r="${r * 0.25}" fill="#fff"/><circle cx="${x + r * 0.35}" cy="${y - r * 0.15}" r="${r * 0.25}" fill="#fff"/>
      <circle cx="${x - r * 0.3}" cy="${y - r * 0.08}" r="${r * 0.12}" fill="#241640"/><circle cx="${x + r * 0.4}" cy="${y - r * 0.08}" r="${r * 0.12}" fill="#241640"/>`;
  };
  const cocci = (x, y) => [0, 1, 2, 3].map((i) => `<circle cx="${x + (i % 2) * 11}" cy="${y + Math.floor(i / 2) * 11}" r="5.5" fill="#4a2c7a"/>`).join("");
  return `<svg class="dish" viewBox="0 0 400 400" role="img" aria-label="A culture dish with superbug colonies and an immune cell">
    <circle cx="200" cy="200" r="188" fill="#fff" stroke="#4a2c7a" stroke-width="6"/>
    <circle cx="200" cy="200" r="168" fill="#efeaf7"/>
    <circle cx="200" cy="200" r="168" fill="none" stroke="#ddd6ea" stroke-width="2" stroke-dasharray="4 10"/>
    ${bug(130, 140, 30)}${bug(270, 120, 20)}${bug(285, 255, 34)}${bug(140, 285, 16)}
    ${cocci(205, 180)}${cocci(110, 215)}${cocci(240, 315)}${cocci(300, 180)}
    <g transform="translate(205 250)"><circle r="34" fill="#4a2c7a"/><circle r="26" fill="#fff"/>
      <circle cx="-7" cy="-4" r="10" fill="#b9a6dc"/><circle cx="7" cy="5" r="10" fill="#b9a6dc"/></g>
    <g stroke="#e2a12b" stroke-width="6" stroke-linecap="round"><line x1="250" y1="225" x2="262" y2="213"/><line x1="241" y1="214" x2="253" y2="202"/></g>
  </svg>`;
}

function renderWelcome() {
  const scr = $("#screen");
  scr.className = "";
  scr.innerHTML = `
    <div class="welcome">
      <div>
        <h1>${esc(L("title"))}</h1>
        <p class="lead">${esc(L("tagline"))}</p>
        <div class="choices">
          <div>
            <p class="muted" id="langq">${esc(L("chooseLang"))}</p>
            <div class="lang-pick" role="group" aria-labelledby="langq">
              <button type="button" data-l="en" aria-pressed="${S.lang === "en"}">English</button>
              <button type="button" data-l="hi" aria-pressed="${S.lang === "hi"}" lang="hi">हिंदी</button>
            </div>
          </div>
          <label class="check"><input type="checkbox" id="wAudio" ${S.audio ? "checked" : ""}> <span>${esc(L("sound"))}</span></label>
        </div>
        <button type="button" class="btn" id="wStart">${esc(L("start"))}</button>
        <p class="muted" style="margin-top:14px">${esc(L("howItWorks"))}</p>
      </div>
      ${dishSVG()}
    </div>`;
  scr.querySelectorAll("[data-l]").forEach((b) => b.addEventListener("click", () => {
    S.lang = b.dataset.l; save(); applyLang(); renderWelcome();
  }));
  $("#wAudio").addEventListener("change", (e) => { S.audio = e.target.checked; save(); applyLang(); });
  $("#wStart").addEventListener("click", () => go(S.pid ? "pre" : "consent"));
}

// ------------------------------------------------------------------ consent
function renderConsent() {
  const scr = $("#screen");
  scr.className = "screen";
  const demo = CFG.instrument.demographics.filter((d) => d.id !== "D05");
  scr.innerHTML = `
    <h2>${esc(L("consentTitle"))}</h2>
    <div class="consent-text">${L("consentBody").map((p) => `<p>${esc(p)}</p>`).join("")}</div>
    <h3 style="margin-top:28px">${esc(L("aboutYou"))}</h3>
    <div class="demo-grid">
      ${demo.map((d) => `<label>${esc(d.text[S.lang])}
        <select data-demo="${d.id}"><option value="">–</option>
          ${d.options.map((o) => `<option value="${esc(o.value)}" ${S.consent.demo[d.id] === o.value ? "selected" : ""}>${esc(o.label[S.lang])}</option>`).join("")}
        </select></label>`).join("")}
    </div>
    <label class="check"><input type="checkbox" id="cAgree" ${S.consent.checked ? "checked" : ""}> <span><b>${esc(L("consentCheck"))}</b></span></label>
    <label class="check" style="margin-top:10px"><input type="checkbox" id="cTest" ${S.testRun ? "checked" : ""}> <span class="muted">${esc(L("testRun"))}</span></label>
    <div class="form-actions"><button type="button" class="btn" id="cGo" ${S.consent.checked ? "" : "disabled"}>${esc(L("continue"))}</button></div>`;
  scr.querySelectorAll("[data-demo]").forEach((s) => s.addEventListener("change", () => { S.consent.demo[s.dataset.demo] = s.value; save(); }));
  $("#cAgree").addEventListener("change", (e) => { S.consent.checked = e.target.checked; $("#cGo").disabled = !e.target.checked; save(); });
  $("#cTest").addEventListener("change", (e) => { S.testRun = e.target.checked; save(); });
  $("#cGo").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      const r = await api.createParticipant({ consent: true, language: S.lang, audio: S.audio,
        demographics: S.consent.demo, test_run: S.testRun });
      S.pid = r.participant_id; S.sid = r.session_id;
      go("pre");
    } catch (err) { e.target.disabled = false; showError(scr, err); }
  });
}

// ------------------------------------------------------------------ pre / post test
function shuffled(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function itemHTML(it, num, phase) {
  const ans = S.answers[phase][it.id] ?? "";
  const name = `${phase}_${it.id}`;
  let body;
  if (it.free_text) {
    body = `<textarea data-item="${it.id}" aria-label="${esc(it.text[S.lang])}">${esc(ans)}</textarea>`;
  } else {
    const isScale = it.options.length === 5 && it.options[0].value === "1";
    body = `<div class="${isScale ? "scale" : "pills"}">${it.options.map((o) => `
      <label class="pill"><input type="radio" name="${name}" value="${esc(o.value)}" data-item="${it.id}" ${ans === o.value ? "checked" : ""}>
      <span>${esc(o.label[S.lang])}</span></label>`).join("")}</div>`;
  }
  return `<fieldset class="item" id="it_${it.id}"><legend><span class="num">${num}</span>${esc(it.text[S.lang])}</legend>${body}</fieldset>`;
}

function renderTest(phase) {
  const scr = $("#screen");
  scr.className = "screen";
  const inst = CFG.instrument;
  if (!S.order[phase]) { S.order[phase] = shuffled(inst.knowledge.map((k) => k.id)); save(); }
  const byId = Object.fromEntries(inst.knowledge.map((k) => [k.id, k]));
  const know = S.order[phase].map((id) => byId[id]);
  let n = 0;
  scr.innerHTML = `
    <h2>${esc(L(phase === "pre" ? "preTitle" : "postTitle"))}</h2>
    <p class="lead">${esc(L(phase === "pre" ? "preIntro" : "postIntro"))}</p>
    <form id="testForm" novalidate>
      <div class="test-section"><h3>${esc(L("sectionKnowledge"))}</h3>${know.map((it) => itemHTML(it, ++n, phase)).join("")}</div>
      <div class="test-section"><h3>${esc(L("sectionAttitude"))}</h3>${inst.attitude.map((it) => itemHTML(it, ++n, phase)).join("")}</div>
      ${phase === "post" ? `<div class="test-section"><h3>${esc(L("sectionFeedback"))}</h3>${inst.feedback.map((it) => itemHTML(it, ++n, phase)).join("")}</div>` : ""}
      <div class="form-actions"><button type="submit" class="btn" id="tGo">${esc(L(phase === "pre" ? "submitPre" : "submitPost"))}</button></div>
    </form>`;
  const form = $("#testForm");
  form.addEventListener("change", (e) => {
    const id = e.target.dataset.item;
    if (!id) return;
    S.answers[phase][id] = e.target.value; save();
    $(`#it_${id}`).classList.remove("missing");
  });
  form.addEventListener("input", (e) => {
    if (e.target.tagName === "TEXTAREA") { S.answers[phase][e.target.dataset.item] = e.target.value; save(); }
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const required = [...inst.knowledge, ...inst.attitude];
    const missing = required.filter((it) => !S.answers[phase][it.id]);
    form.querySelectorAll(".item").forEach((f) => f.classList.remove("missing"));
    if (missing.length) {
      missing.forEach((it) => $(`#it_${it.id}`).classList.add("missing"));
      showError(form, new Error(`${L("answerAll")} ${missing.length}`));
      $(`#it_${missing[0].id}`).scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    const btn = $("#tGo");
    btn.disabled = true; btn.textContent = L("saving");
    try {
      const r = await api.saveTest(phase, { participant_id: S.pid, responses: S.answers[phase] });
      if (phase === "pre") { S.level = 1; go("intro"); }
      else {
        S.scores = r;
        api.endSession({ session_id: S.sid, participant_id: S.pid }).catch(() => {});
        go("results");
      }
    } catch (err) {
      btn.disabled = false; btn.textContent = L(phase === "pre" ? "submitPre" : "submitPost");
      showError(form, err);
    }
  });
}

// ------------------------------------------------------------------ level intro / end
function renderLevelIntro() {
  const scr = $("#screen");
  scr.className = "screen level-intro";
  const lv = CFG.levels[S.level - 1];
  scr.innerHTML = `
    <div class="big-num" aria-hidden="true">${S.level}</div>
    <h2>${esc(lv.name[S.lang])}</h2>
    <p class="muted">${esc(L("learn"))}</p>
    <p class="lead">${esc(lv.learn[S.lang])}</p>
    <div class="form-actions"><button type="button" class="btn" id="lGo">${esc(L("startLevel"))}</button></div>`;
  $("#lGo").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { await startLevel(); }
    catch (err) { e.target.disabled = false; S.stage = "intro"; save(); render(); showError($("#screen"), err); }
  });
}

function renderLevelEnd() {
  const scr = $("#screen");
  scr.className = "screen";
  const st = S.levelStats[S.level] || { correct: 0, n: 0, points: 0 };
  const last = S.level >= CFG.levels.length;
  scr.innerHTML = `
    <h2>${esc(L("levelDone"))}</h2>
    <p class="lead">${esc(L("levelSummary", st.correct, st.n, st.points))}</p>
    <div class="form-actions"><button type="button" class="btn" id="eGo">${esc(L(last ? "toPostTest" : "nextLevel"))}</button></div>`;
  $("#eGo").addEventListener("click", () => {
    if (last) go("post");
    else { S.level += 1; go("intro"); }
  });
}

// ------------------------------------------------------------------ game
function computeGates(n, cells) {
  return Array.from({ length: n }, (_, k) => Math.floor(((k + 1) * cells) / (n + 1)));
}
const nextGate = () => G.state.findIndex((s) => s === null);

async function startLevel() {
  const res = await api.startLevel(S.level, { session_id: S.sid, participant_id: S.pid });
  const n = res.questions.length;
  G = { questions: res.questions, cells: res.board_cells, gates: computeGates(n, res.board_cells),
        state: Array(n).fill(null), pos: 1, points: 0, correct: 0, tip: null };
  res.questions.forEach((q, i) => {
    const a = res.answered[q.id];
    if (a) {
      G.state[i] = a.is_correct ? "cleared" : "escaped";
      G.points += a.points_awarded; G.correct += a.is_correct;
      G.pos = G.gates[i];
    }
  });
  S.stage = "game"; save(); render();
  if (!board) board = new BoardView("board");
  await board.setLevel({ cells: G.cells, gates: G.gates, startLabel: L("boardStart"), exitLabel: L("boardExit") });
  for (let i = 0; i < n; i++) if (G.state[i]) await board.setGate(G.gates[i], G.state[i]);
  await board.place(G.pos);
  updatePanel();
  showTip("tipStart");
  $("#die").textContent = "–";
  $("#rollBtn").disabled = false;
  $("#rollBtn").focus();
}

function updatePanel() {
  if (!G) return;
  $("#points").textContent = S.points;
  const cleared = G.state.filter((s) => s === "cleared").length;
  $("#bugCount").textContent = `${cleared} / ${G.state.length}`;
  $("#bugRow").innerHTML = G.state.map((s) => `<span class="bug-dot ${s || ""}" aria-hidden="true"></span>`).join("");
}

function showTip(key, ...args) {
  if (G) G.tip = { key, args };
  $("#tip").textContent = L(key, ...args);
}

async function animateDie(d) {
  const die = $("#die");
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    die.classList.add("spin");
    for (let i = 0; i < 7; i++) { die.textContent = 1 + Math.floor(Math.random() * 6); await new Promise((r) => setTimeout(r, 60)); }
    die.classList.remove("spin");
  }
  die.textContent = d;
}

async function roll() {
  const btn = $("#rollBtn");
  if (btn.disabled || !G) return;
  btn.disabled = true;
  stopAudio();
  const d = 1 + Math.floor(Math.random() * 6);
  await animateDie(d);
  const ni = nextGate();
  const limit = ni === -1 ? G.cells : G.gates[ni];
  const stopAt = Math.min(G.pos + d, limit);
  const path = [];
  for (let c = G.pos + 1; c <= stopAt; c++) path.push(c);
  await board.walk(path);
  G.pos = stopAt;
  if (ni !== -1 && G.pos === G.gates[ni]) { showTip("tipGate"); openQuestion(ni); return; }
  if (G.pos >= G.cells) { finishLevel(); return; }
  btn.disabled = false;
  btn.focus();
}

// ------------------------------------------------------------------ question overlay
function openQuestion(i) {
  Q = { i, q: G.questions[i], hint: false, audioPlayed: false, t0: performance.now(), result: null, busy: false };
  renderQuestion();
  $("#quiz").hidden = false;
  $("#qtext").focus();
  if (S.audio) speakQuestion(false);
}

function renderQuestion() {
  const q = Q.q, c = q[S.lang] || q.en;
  $("#qcount").textContent = `${L("question")} ${Q.i + 1} / ${G.questions.length}`;
  $("#qtext").textContent = c.question;
  const box = $("#qoptions");
  box.innerHTML = q.options.map((letter, k) => `
    <button type="button" class="opt" data-opt="${letter}">
      <span class="letter">${letter}</span><span>${esc(c.options[k])}</span></button>`).join("");
  box.querySelectorAll(".opt").forEach((b) => b.addEventListener("click", () => choose(b.dataset.opt)));
  $("#hintText").textContent = c.hint || "";
  $("#hintText").hidden = !Q.hint;
  $("#hintBtn").hidden = Q.hint || Boolean(Q.result) || !c.hint;
  $("#listenBtn").textContent = L("listen");
  const fb = $("#feedback"), card = document.querySelector(".qcard");
  if (Q.result) {
    const r = Q.result;
    box.querySelectorAll(".opt").forEach((b) => {
      b.disabled = true;
      if (b.dataset.opt === r.correct_option) b.classList.add("is-correct");
      else if (b.dataset.opt === r.selected_option) b.classList.add("is-wrong");
    });
    const ci = q.options.indexOf(r.correct_option);
    fb.className = `feedback ${r.is_correct ? "good" : "bad"}`;
    fb.innerHTML = `<h3>${esc(L(r.is_correct ? "correct" : "wrong"))}${r.points ? `<span class="pts">${esc(L("points", r.points))}</span>` : ""}</h3>
      ${r.is_correct ? "" : `<p><b>${esc(L("correctAnswerIs"))}</b> ${esc(r.correct_option)}. ${esc(c.options[ci])}</p>`}
      <p style="margin:0">${esc(r.explanation[S.lang] || r.explanation.en)}</p>`;
    fb.hidden = false;
    card.classList.toggle("solved", r.is_correct);
    $("#qnext").hidden = false;
  } else {
    fb.hidden = true;
    card.classList.remove("solved");
    $("#qnext").hidden = true;
  }
}

function showHint() {
  if (!Q || Q.result) return;
  Q.hint = true;
  renderQuestion();
}

function speakQuestion(byUser) {
  if (!Q) return;
  const c = Q.q[S.lang] || Q.q.en;
  const text = `${c.question} ${Q.q.options.map((l, k) => `${l}. ${c.options[k]}.`).join(" ")}`;
  speak(text, S.lang, `${Q.q.id}_q`).then((ok) => {
    if (ok) Q && (Q.audioPlayed = true);
    else if (byUser) showTip("noVoice");
  });
}

async function choose(letter) {
  if (!Q || Q.result || Q.busy) return;
  Q.busy = true;
  document.querySelectorAll("#qoptions .opt").forEach((b) => { b.disabled = true; });
  try {
    const r = await api.answer({
      session_id: S.sid, participant_id: S.pid, level: S.level, question_id: Q.q.id, selected_option: letter,
      hint_used: Q.hint, audio_played: Q.audioPlayed, response_time_ms: Math.round(performance.now() - Q.t0),
      language: S.lang,
    });
    Q.result = r;
    G.state[Q.i] = r.is_correct ? "cleared" : "escaped";
    G.points += r.points; G.correct += r.is_correct ? 1 : 0;
    S.points += r.points; save();
    renderQuestion();
    $("#qnext").focus();
    if (S.audio) speak(r.explanation[S.lang] || r.explanation.en, S.lang, `${Q.q.id}_e`);
  } catch (err) {
    Q.busy = false;
    document.querySelectorAll("#qoptions .opt").forEach((b) => { b.disabled = false; });
    showError(document.querySelector(".qcard"), err);
  }
}

async function afterAnswer() {
  if (!Q || !Q.result) return;
  const ok = Q.result.is_correct, gateCell = G.gates[Q.i];
  stopAudio();
  $("#quiz").hidden = true;
  document.querySelector(".qcard .error")?.remove();
  Q = null;
  updatePanel();
  await board.setGate(gateCell, ok ? "cleared" : "escaped");
  if (ok) {
    const ni = nextGate();
    const limit = ni === -1 ? G.cells : G.gates[ni] - 1;
    const up = Math.min(G.pos + LADDER, limit);
    if (up > G.pos) { await board.ladder(G.pos, up); showTip("tipLadder", up - G.pos); G.pos = up; }
  } else {
    const down = Math.max(1, G.pos - SNAKE);
    if (down < G.pos) { await board.snake(G.pos, down); showTip("tipSnake", G.pos - down); G.pos = down; }
  }
  if (G.pos >= G.cells) { finishLevel(); return; }
  $("#rollBtn").disabled = false;
  $("#rollBtn").focus();
}

async function finishLevel() {
  showTip("tipFinish");
  try { await api.endLevel(S.level, { session_id: S.sid, participant_id: S.pid, completed: true }); } catch (e) { /* logged server-side on next call */ }
  S.levelStats[S.level] = { correct: G.correct, n: G.questions.length, points: G.points };
  await new Promise((r) => setTimeout(r, 600));
  G = null;
  go("levelEnd");
}

async function endGameEarly() {
  if (!window.confirm(L("confirmEnd"))) return;
  try { await api.endLevel(S.level, { session_id: S.sid, participant_id: S.pid, completed: false }); } catch (e) { /* ignore */ }
  G = null; Q = null;
  $("#quiz").hidden = true;
  go("post");
}

// ------------------------------------------------------------------ results
async function renderResults() {
  const scr = $("#screen");
  scr.className = "screen";
  let r = S.scores;
  try { r = await api.results(S.pid); } catch (e) { /* use saved */ }
  const max = r?.max || 16, pre = r?.pre_score ?? 0, post = r?.post_score ?? 0;
  const h = (v) => Math.max(8, Math.round((v / max) * 180));
  scr.innerHTML = `
    <h2>${esc(L("thanksTitle"))}</h2>
    <h3>${esc(L("yourScores"))}</h3>
    <div class="score-pair">
      <div class="col"><div class="bar before" style="height:${h(pre)}px"></div><div class="n">${pre}</div><div class="muted">${esc(L("before"))}, ${esc(L("outOf", max))}</div></div>
      <div class="col"><div class="bar after" style="height:${h(post)}px"></div><div class="n">${post}</div><div class="muted">${esc(L("after"))}, ${esc(L("outOf", max))}</div></div>
    </div>
    <h3>${esc(L("remember"))}</h3>
    <ul class="takeaways">${L("takeaways").map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <p class="muted" style="margin-top:28px">${esc(L("yourId"))}: <span class="pid">${esc(S.pid)}</span></p>
    <div class="form-actions"><button type="button" class="btn secondary" id="again">${esc(L("playAgain"))}</button></div>`;
  $("#again").addEventListener("click", () => { sessionStorage.removeItem(STORE); location.reload(); });
}
