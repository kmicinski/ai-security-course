// CIS400 prompt-injection demo — front end.
// Talks to the FastAPI backend, renders the streamed episode live.

const $ = (s) => document.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
const esc = (s) => (s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

let STATE = { scenarios: [], defenses: [], scn: null, defense: null, running: false };

// ---- boot ----
async function boot() {
  const cfg = await fetch("/api/config").then((r) => r.json()).catch(() => null);
  renderModelBadge(cfg);
  const cat = await fetch("/api/scenarios").then((r) => r.json());
  STATE.scenarios = cat.scenarios;
  STATE.defenses = cat.defenses;
  renderScenarioTabs();
  renderDefenses();
  selectScenario(STATE.scenarios[0].id);
}

function renderModelBadge(cfg) {
  const badge = $("#modelBadge"), txt = $("#mbText");
  if (!cfg) { badge.classList.add("err"); txt.textContent = "backend offline"; return; }
  const { profile, model } = cfg.llm;
  const ok = cfg.health && cfg.health.ok;
  badge.classList.toggle("ok", !!ok);
  badge.classList.toggle("err", !ok);
  txt.textContent = ok ? `${profile} · ${model}` : `${profile}: ${(cfg.health && cfg.health.error || "unreachable").slice(0, 40)}`;
  badge.title = ok ? `Connected to ${cfg.llm.base_url} (model ${model})`
    : `Cannot reach ${cfg.llm.base_url}. Start Ollama or set LLM_PROFILE.`;
}

function renderScenarioTabs() {
  const box = $("#scenarioTabs"); box.innerHTML = "";
  STATE.scenarios.forEach((s) => {
    const kind = s.kind === "direct" ? "Direct injection" : "Indirect injection";
    const b = el("button", "seg", `${esc(s.title)}<small>${kind}</small>`);
    b.dataset.id = s.id;
    b.onclick = () => selectScenario(s.id);
    box.appendChild(b);
  });
}

function renderDefenses() {
  const box = $("#defenseList"); box.innerHTML = "";
  const none = defenseRow({ id: "", label: "None (undefended)", blurb: "Run the attack against the bare model.", outside_model: false }, true);
  box.appendChild(none);
  STATE.defenses.forEach((d) => box.appendChild(defenseRow(d, false)));
}
function defenseRow(d, checked) {
  const row = el("label", "def" + (checked ? " active" : ""));
  const outside = d.outside_model ? `<span class="outside">outside the model</span>` : "";
  row.innerHTML = `<input type="radio" name="def" value="${d.id}" ${checked ? "checked" : ""}>
    <div><div class="d-label">${esc(d.label)}${outside}</div><div class="d-blurb">${esc(d.blurb)}</div></div>`;
  row.querySelector("input").onchange = () => {
    STATE.defense = d.id || null;
    document.querySelectorAll(".def").forEach((x) => x.classList.remove("active"));
    row.classList.add("active");
  };
  return row;
}

function selectScenario(id) {
  const s = STATE.scenarios.find((x) => x.id === id);
  STATE.scn = s;
  document.querySelectorAll(".seg").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  $("#scenarioBlurb").textContent = s.blurb;
  $("#kindChip").textContent = s.kind === "direct" ? "DIRECT" : "INDIRECT";
  $("#siteChip").textContent = "site: " + s.injection_site;
  $("#goalText").textContent = s.attacker_goal;
  $("#sysPrompt").textContent = s.system_prompt;
  $("#userTurn").textContent = s.kind === "direct" ? "(the payload below is the user's message)" : s.user_prompt;

  const sel = $("#payloadSelect"); sel.innerHTML = "";
  s.payloads.forEach((p, i) => { const o = el("option"); o.value = i; o.textContent = p.name; sel.appendChild(o); });
  sel.onchange = () => fillPayload(s, +sel.value);
  fillPayload(s, 0);
}
function fillPayload(s, i) {
  const p = s.payloads[i];
  $("#payloadText").value = p.text;
  $("#payloadNote").textContent = p.note || "";
}

// ---- run ----
$("#temp").oninput = (e) => ($("#tempVal").textContent = (+e.target.value).toFixed(1));
$("#runBtn").onclick = run;

let activeMsg = null; // the streaming assistant/reasoning bubble

function clearStage() {
  $("#transcript").innerHTML = "";
  $("#verdict").hidden = true;
  activeMsg = null;
}
function stepSep(n) { const t = $("#transcript"); t.appendChild(el("div", "step-sep", `model turn ${n}`)); scroll(); }
function scroll() { const t = $("#transcript"); t.scrollTop = t.scrollHeight; }

function ensureBubble(kind) {
  if (activeMsg && activeMsg.dataset.kind === kind) return activeMsg;
  const m = el("div", "msg " + kind);
  m.dataset.kind = kind;
  const who = kind === "reasoning" ? "reasoning" : "assistant";
  m.innerHTML = `<span class="who">${who}</span><div class="content cursor"></div>`;
  $("#transcript").appendChild(m);
  activeMsg = m;
  return m;
}
function endBubble() { if (activeMsg) activeMsg.querySelector(".content")?.classList.remove("cursor"); activeMsg = null; }

async function run() {
  if (STATE.running) return;
  STATE.running = true;
  $("#runBtn").disabled = true;
  $("#runSub").textContent = "streaming…";
  clearStage();

  const body = {
    scenario: STATE.scn.id,
    payload_text: $("#payloadText").value,
    defense: STATE.defense || null,
    temperature: +$("#temp").value,
  };

  let resp;
  try {
    resp = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (e) { fail("network error: " + e.message); return; }
  if (!resp.ok || !resp.body) { fail("server error " + resp.status); return; }

  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const frames = buf.split("\n\n");
    buf = frames.pop();
    for (const f of frames) handleFrame(f);
  }
  STATE.running = false;
  $("#runBtn").disabled = false;
  $("#runSub").textContent = "";
}

function fail(msg) {
  const t = $("#transcript");
  t.appendChild(el("div", "defense-event flagged", `<span class="de-ic">✖</span><div>${esc(msg)}</div>`));
  STATE.running = false; $("#runBtn").disabled = false; $("#runSub").textContent = "";
}

function handleFrame(frame) {
  let event = "message", data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;
  let d; try { d = JSON.parse(data); } catch { return; }
  dispatch(event, d);
}

function dispatch(event, d) {
  const t = $("#transcript");
  switch (event) {
    case "start": break;
    case "step": endBubble(); if (d.n > 1) stepSep(d.n); break;
    case "reasoning": ensureBubble("reasoning").querySelector(".content").textContent += d.text; scroll(); break;
    case "token": ensureBubble("assistant").querySelector(".content").textContent += d.text; scroll(); break;
    case "tool_call": {
      endBubble();
      const card = el("div", "toolcard");
      card.dataset.fn = d.name;
      card.innerHTML = `<div class="tc-head"><span class="fn">${esc(d.name)}()</span><span class="arrow">tool call</span></div>
        <div class="tc-args">${esc(JSON.stringify(d.arguments, null, 2))}</div>`;
      t.appendChild(card); scroll();
      break;
    }
    case "tool_result": {
      const cards = t.querySelectorAll(`.toolcard[data-fn="${cssEsc(d.name)}"]`);
      const card = cards[cards.length - 1];
      if (card) {
        if (d.blocked) card.classList.add("blocked");
        const r = el("div", "tc-result", esc(d.result));
        card.appendChild(r);
      }
      scroll(); break;
    }
    case "defense": {
      endBubble();
      const flagged = d.flagged ? " flagged" : "";
      const ic = d.kind === "tool_policy" ? "⛔" : (d.flagged ? "⚑" : "🛡");
      t.appendChild(el("div", "defense-event" + flagged,
        `<span class="de-ic">${ic}</span><div><span class="de-kind">${esc(d.kind)}</span><br>${esc(d.note)}</div>`));
      const lastTool = t.querySelector(".toolcard:last-of-type");
      if (d.kind !== "tool_policy") markLastUntrusted();
      scroll(); break;
    }
    case "verdict": showVerdict(d); break;
    case "end": endBubble(); break;
    case "error": fail(d.message); break;
  }
}
function cssEsc(s){ return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/"/g,'\\"'); }
function markLastUntrusted() {
  const cards = $("#transcript").querySelectorAll(".toolcard");
  if (cards.length) cards[cards.length - 1].classList.add("untrusted");
}

function showVerdict(d) {
  const v = $("#verdict"); v.hidden = false;
  const win = d.attacker_won;
  $("#vBadge").className = "v-badge " + (win ? "win" : "safe");
  $("#vBadge").innerHTML = win ? "ATTACKER<br>WON" : "ATTACK<br>BLOCKED";
  $("#vTitle").textContent = win ? "Injection succeeded" : "Injection did not succeed";
  $("#vReason").textContent = d.reason;
  const e = d.env_summary || {};
  const parts = [];
  if (e.outbox && e.outbox.length) parts.push("outbox: " + e.outbox.map((m) => `→ ${m.to}`).join(", "));
  if (e.deleted && e.deleted.length) parts.push("deleted: " + e.deleted.join(", "));
  if (e.fetched && e.fetched.length) parts.push("fetched: " + e.fetched.map((u) => u.slice(0, 50)).join(" | "));
  if (e.exfil_hits && e.exfil_hits.length) parts.push("EXFIL HITS: " + e.exfil_hits.map((u) => u.slice(0, 60)).join(" | "));
  $("#vEnv").textContent = parts.join("\n");
  $("#verdict").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

boot();
