// UI. All the interesting logic lives in lang.js / checker.js / analysis.js;
// this file only decides what to draw.

import { parse, run, ParseError } from './lang.js';
import { check } from './checker.js';
import {
  runAll, leakage, leakageByObserver, knowledgeCurve, perOutputLeakage,
  OBSERVERS, OBSERVER_ORDER, fmtBits, log2,
} from './analysis.js';
import { CHALLENGES, MODES } from './challenges.js';

const STORE_KEY = 'cis400-ifc-v1';

const state = {
  mode: 'batch',
  current: Object.fromEntries(MODES.map((m) => [m.id, CHALLENGES.find((c) => c.mode === m.id).id])),
  answers: {},          // id -> {picked, correct}
  picked: {},           // id -> tentative selection before submit
  observer: {},         // id -> observer id
  low: {},              // id -> {var: value}
  tab: {},              // id -> reveal tab
  bench: {},            // id -> {source, labels}
};

try {
  const saved = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
  if (saved && typeof saved === 'object') Object.assign(state.answers, saved.answers || {});
} catch { /* private window, blocked storage — run without persistence */ }

function persist() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify({ answers: state.answers })); } catch { /* ignore */ }
}

// ------------------------------------------------------------------ helpers

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const CLASS_COLORS = [
  '#0aa6b7', '#f76900', '#7d3c98', '#4b8b3b', '#b7410e',
  '#1a277a', '#a8890a', '#c2185b', '#00838f', '#6d4c41',
];
const classColor = (i) => CLASS_COLORS[i % CLASS_COLORS.length];

function highlight(src, marks = {}) {
  return src.split('\n').map((line, i) => {
    const n = i + 1;
    const cut = line.indexOf('//');
    const code = cut >= 0 ? line.slice(0, cut) : line;
    const comment = cut >= 0 ? line.slice(cut) : '';
    const body = esc(code)
      .replace(/\b(if|else|while|out|skip)\b/g, '<span class="kw">$1</span>')
      .replace(/\b(digit)\b/g, '<span class="fn">$1</span>')
      .replace(/\b(\d+)\b/g, '<span class="num">$1</span>')
      + (comment ? `<span class="cm">${esc(comment)}</span>` : '');
    const m = marks[n];
    const cls = m ? ` ${m.cls}` : '';
    const gut = m ? m.glyph : '';
    return `<div class="ln${cls}"><span class="n">${n}</span><span class="gut">${gut}</span><span>${body || ' '}</span></div>`;
  }).join('');
}

function renderInputs(inputs) {
  return Object.entries(inputs).map(([k, v]) => `${k}=${v}`).join(', ');
}

// ---------------------------------------------------------------- analysis

/** Everything the UI needs about a (program, labels, inputs) triple. */
function analyse(chal, source = chal.source, labels = chal.labels) {
  const fixed = { ...chal.fixed, ...(state.low[chal.id] || {}) };
  const ast = parse(source);
  const chk = check(ast, labels);
  const runs = runAll(ast, chal.high, fixed);
  return { ast, chk, runs, fixed, byObserver: leakageByObserver(runs) };
}

const observerOf = (chal) => state.observer[chal.id] || chal.observer;

// ------------------------------------------------------------------ render

function render() {
  renderHeader();
  const root = document.getElementById('app');
  const mode = MODES.find((m) => m.id === state.mode);
  const inMode = CHALLENGES.filter((c) => c.mode === state.mode);
  const chal = CHALLENGES.find((c) => c.id === state.current[state.mode]) || inMode[0];

  let a, err = null;
  try { a = analyse(chal); } catch (e) { err = e; }

  root.innerHTML = `
    <section class="mode-intro">
      <h2>${esc(mode.name)} <span class="tagline">— ${esc(mode.tagline)}</span></h2>
      <p>${mode.blurb}</p>
      <p class="obsdef" style="margin-top:.5rem">
        <b>Default observer for this mode:</b>
        <span class="mono">${esc(OBSERVERS[mode.id].formal)}</span> — ${esc(OBSERVERS[mode.id].blurb)}.
      </p>
    </section>
    <div class="chal-nav">${inMode.map((c) => {
      const ans = state.answers[c.id];
      const mark = ans ? `<span class="mark ${ans.correct ? 'right' : 'wrong'}">${ans.correct ? '✓' : '✗'}</span>` : '';
      return `<button data-goto="${c.id}" aria-current="${c.id === chal.id}">${esc(c.title)}${mark}</button>`;
    }).join('')}</div>
    <div class="grid">
      <div>${err ? `<div class="card"><div class="bench"><div class="err">${esc(err.message)}</div></div></div>` : programCard(chal, a)}</div>
      <div id="rightcol">${questionCard(chal)}${state.answers[chal.id] ? revealCard(chal, a) : ''}</div>
    </div>
    <p class="kbdhint">
      <kbd>1</kbd>–<kbd>4</kbd> pick · <kbd>Enter</kbd> submit · <kbd>←</kbd> <kbd>→</kbd> previous / next program
    </p>`;

  wire(chal, a);
}

function renderHeader() {
  const answered = Object.keys(state.answers).length;
  const correct = Object.values(state.answers).filter((x) => x.correct).length;
  document.getElementById('score').innerHTML = `<strong>${correct} / ${answered}</strong>of ${CHALLENGES.length} programs`;
  document.querySelectorAll('nav.modes button').forEach((b) => {
    b.setAttribute('aria-selected', String(b.dataset.mode === state.mode));
  });
}

function programCard(chal, a) {
  const marks = {};
  if (state.tab[chal.id] === 'checker') {
    for (const c of a.chk.constraints) {
      if (!c.ok) marks[c.line] = { cls: 'bad', glyph: '✗' };
      else if (c.raises && !marks[c.line]) marks[c.line] = { cls: 'pcraise', glyph: '↑' };
    }
  }
  const labels = Object.entries(chal.labels)
    .map(([v, l]) => `<span class="lab ${l}">${esc(v)}<span class="l"> : ${l}</span></span>`).join('');

  const domain = Object.entries(chal.high)
    .map(([k, vs]) => `<code>${esc(k)}</code> ranges over ${vs.length} value${vs.length === 1 ? '' : 's'}`)
    .join('; ');
  const priorBits = fmtBits(log2(a.runs.length));

  const ctl = chal.lowControl ? `
    <div class="lowctl">
      <label>Public input — ${chal.lowControl.label}:
        <select id="lowctl">${chal.lowControl.options.map((o) =>
          `<option value="${o.value}" ${a.fixed[chal.lowControl.name] === o.value ? 'selected' : ''}>${esc(o.text)}</option>`).join('')}
        </select>
      </label>
      <div style="margin-top:.3rem;color:var(--muted);font-size:.8rem">
        The attacker chooses this. Change it and the partition moves — that is what makes the attack adaptive.
      </div>
    </div>` : '';

  return `
    <div class="card">
      <h3><span class="idtag">${esc(chal.id)}</span>${esc(chal.title)}</h3>
      <div class="threat"><b>Threat model.</b> ${chal.threat}</div>
      <div class="labels">${labels}<span class="lab L">out<span class="l"> : L (public channel)</span></span></div>
      <pre class="code">${highlight(chal.source, marks)}</pre>
      ${ctl}
      <p class="costnote">
        ${domain} — a uniform prior of <b>${priorBits} bits</b> over ${a.runs.length} runs, all enumerated.
        Cost model: one tick per statement step (assignment, <code>out</code>, <code>skip</code>, and each
        <code>if</code>/<code>while</code> guard test); expression evaluation is free. No caches, no branch
        predictor — a real clock leaks strictly more than this one.
      </p>
    </div>`;
}

function questionCard(chal) {
  const ans = state.answers[chal.id];
  const picked = ans ? ans.picked : state.picked[chal.id];
  const opts = chal.question.options.map((o, i) => {
    let cls = 'opt';
    if (ans) {
      if (i === chal.question.answer) cls += ' correct';
      else if (i === picked) cls += ' wrong';
    }
    return `<button class="${cls}" data-opt="${i}" aria-pressed="${picked === i}" ${ans ? 'disabled' : ''}>
        <span class="key">${i + 1}</span><span>${o}</span></button>`;
  }).join('');

  const verdict = ans ? `<div class="verdict ${ans.correct ? 'right' : 'wrong'}">
      ${ans.correct ? '✓ Correct.' : '✗ Not quite.'} The answer is
      <em>${chal.question.options[chal.question.answer].replace(/<[^>]+>/g, '')}</em>.
      Everything below is computed by running the program over its entire input space.
    </div>` : '';

  return `
    <div class="card">
      <h3>Question</h3>
      <p class="qprompt">${chal.question.prompt}</p>
      <div class="opts">${opts}</div>
      ${ans ? verdict : `<div class="qactions">
        <button class="primary" id="submit" ${picked === undefined ? 'disabled' : ''}>Submit</button>
        <button class="ghost" id="skip">Skip to the analysis</button>
      </div>`}
    </div>`;
}

const TABS = [
  ['runs', 'Runs &amp; classes'],
  ['leak', 'Leakage'],
  ['checker', 'The checker'],
  ['disc', 'Discussion'],
  ['bench', 'Bench'],
];

function revealCard(chal, a) {
  const tab = state.tab[chal.id] || 'runs';
  let body = '';
  if (tab === 'runs') body = runsTab(chal, a);
  else if (tab === 'leak') body = leakTab(chal, a);
  else if (tab === 'checker') body = checkerTab(chal, a);
  else if (tab === 'disc') body = discTab(chal);
  else body = benchTab(chal);

  return `
    <div class="card">
      <div class="tabs">${TABS.map(([id, name]) =>
        `<button data-tab="${id}" aria-selected="${tab === id}">${name}</button>`).join('')}</div>
      ${body}
    </div>`;
}

function observerBar(chal) {
  const sel = observerOf(chal);
  return `
    <div class="obsbar">
      <span style="font-weight:600">Observer:</span>
      <span class="seg">${OBSERVER_ORDER.map((o) =>
        `<button data-obs="${o}" aria-pressed="${o === sel}">${OBSERVERS[o].name}</button>`).join('')}</span>
      <span class="obsdef"><span class="mono">${esc(OBSERVERS[sel].formal)}</span></span>
    </div>`;
}

function runsTab(chal, a) {
  const obs = OBSERVERS[observerOf(chal)];
  const l = leakage(a.runs, obs.key);
  const classes = [...l.classes.values()];
  const highVars = Object.keys(chal.high);

  const rows = classes.map((members, i) => {
    const color = classColor(i);
    const shown = members.slice(0, 6).map((m) => renderInputs(m.high)).join('; ');
    const more = members.length > 6 ? ` … +${members.length - 6}` : '';
    return `<tr class="cls">
      <td><span class="cbadge" style="background:${color}">C${i + 1}</span></td>
      <td class="mono">${esc(obs.render(members[0].result))}</td>
      <td>${members.length}</td>
      <td class="mono" style="color:var(--muted)">${esc(shown)}${more}</td>
    </tr>`;
  }).join('');

  const full = a.runs.map((r) => {
    const key = obs.key(r.result);
    const idx = [...l.classes.keys()].indexOf(key);
    return `<tr>
      <td class="mono">${esc(renderInputs(r.high))}</td>
      <td class="mono">${esc(r.result.outputs.map((o) => o.value).join(', ') || '—')}</td>
      <td>${r.result.halted ? '✓' : '✗ diverges'}</td>
      <td class="mono">${r.result.time === null ? '∞' : r.result.time}</td>
      <td><span class="cbadge" style="background:${classColor(idx)}">C${idx + 1}</span></td>
    </tr>`;
  }).join('');

  return `${observerBar(chal)}
    <div class="summary">
      ${a.runs.length} runs collapse to <b>${l.numClasses}</b> distinguishable observation${l.numClasses === 1 ? '' : 's'}.
      ${l.interferenceFree
        ? '<b>Noninterference holds</b> for this observer: every high input looks identical.'
        : `<b>Noninterference fails</b>: the observation partitions the ${a.runs.length} secrets into ${l.numClasses} classes,
           so the observer can rule out everything outside the class they see.`}
    </div>
    <table class="runs">
      <thead><tr><th></th><th>what the observer sees</th><th>secrets</th><th>which ones</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <details class="more">
      <summary>Show all ${a.runs.length} runs</summary>
      <table class="runs" style="margin-top:.5rem">
        <thead><tr><th>${esc(highVars.join(', '))}</th><th>emitted</th><th>halts</th><th>ticks</th><th>class</th></tr></thead>
        <tbody>${full}</tbody>
      </table>
    </details>
    <p class="footnote">
      Divergence is detected by exhausting a step budget, not by deciding halting. What a real stream observer
      sees is “no further output for as long as I have waited”, which is what the ⊥ / silence rows stand for here.
    </p>`;
}

function bar(name, bits, prior) {
  const pct = prior > 0 ? Math.min(100, (bits / prior) * 100) : 0;
  return `<div class="bar">
    <span class="nm">${name}</span>
    <span class="track"><span class="fill" style="width:${pct}%"></span></span>
    <span class="amt">${fmtBits(bits)} bits</span>
  </div>`;
}

function leakTab(chal, a) {
  const sel = observerOf(chal);
  const obs = OBSERVERS[sel];
  const l = leakage(a.runs, obs.key);
  const sizes = [...l.classes.values()].map((c) => c.length).sort((x, y) => y - x);
  const N = a.runs.length;

  const curve = chal.curve ? curveChart(a.runs, sel === 'timing') : '';
  const perOut = chal.perOutputNote ? perOutputTable(a.runs) : '';

  return `${observerBar(chal)}
    <div class="stats">
      <div class="stat"><div class="v">${fmtBits(l.prior)}</div><div class="k">prior H∞(H)</div></div>
      <div class="stat"><div class="v ${l.minEntropy > 0 ? 'hot' : 'cool'}">${fmtBits(l.minEntropy)}</div><div class="k">leaked (min-entropy)</div></div>
      <div class="stat"><div class="v">${fmtBits(l.shannon)}</div><div class="k">leaked (Shannon)</div></div>
      <div class="stat"><div class="v">${fmtBits(l.prior - l.minEntropy)}</div><div class="k">uncertainty left</div></div>
    </div>
    <h4 style="margin:.2rem 0 .3rem;font-size:.9rem;color:var(--navy)">The observer hierarchy, on this program</h4>
    <div class="bars">
      ${OBSERVER_ORDER.map((o) => bar(OBSERVERS[o].name, a.byObserver[o].minEntropy, l.prior)).join('')}
    </div>
    <p style="font-size:.85rem;margin:.2rem 0 .6rem">
      Min-entropy leakage is monotone along <span class="mono">O_batch ⊑ O_stream ⊑ O_time</span>, because each
      observation is a function of the next one. A gap between two bars is a channel the weaker observer cannot see.
    </p>
    <div class="formula">N  = ${N} secrets, uniform          H∞(H)     = log₂ ${N}  = ${fmtBits(l.prior)} bits
k  = ${l.numClasses} observation classes${' '.repeat(Math.max(0, 8 - String(l.numClasses).length))}   L(H;O)    = log₂ ${l.numClasses}  = ${fmtBits(l.minEntropy)} bits
class sizes: ${sizes.join(', ')}
Shannon:  I(H;O) = log₂ N − Σᵢ (|Cᵢ|/N)·log₂|Cᵢ| = ${fmtBits(l.shannon)} bits</div>
    <p style="font-size:.85rem">
      The two numbers answer different questions. <b>Min-entropy</b> (Smith 2009) bounds the attacker's
      probability of guessing the secret in <em>one</em> try, and is the number to quote for key recovery.
      <b>Shannon</b> is an average code length, and can look reassuringly small even when a single
      high-value class has been isolated — compare them on <span class="mono">c2</span>.
    </p>
    ${perOut}
    ${curve}`;
}

function perOutputTable(runs) {
  const rows = perOutputLeakage(runs);
  if (!rows.length) return '';
  return `
    <h4 style="margin:.9rem 0 .3rem;font-size:.9rem;color:var(--navy)">What each emission carries, on its own</h4>
    <table class="runs">
      <thead><tr><th>emission</th><th>distinct values</th><th>min-entropy bits</th></tr></thead>
      <tbody>${rows.map((r) => `<tr>
        <td class="mono">#${r.index + 1}</td><td>${r.numClasses}</td>
        <td class="mono">${fmtBits(r.minEntropy)}</td></tr>`).join('')}</tbody>
    </table>
    <p class="footnote">An output carrying 0 bits is one the checker may still reject — soundness is not precision.</p>`;
}

function curveChart(runs, withTime) {
  const { points, prior } = knowledgeCurve(runs, { withTime });
  const W = 520, H = 230, L = 46, R = 14, T = 16, B = 34;
  const maxK = Math.max(1, points.length - 1);
  const maxY = Math.max(prior, 1);
  const x = (k) => L + (k / maxK) * (W - L - R);
  const y = (b) => T + (1 - b / maxY) * (H - T - B);

  // staircase: knowledge is constant between emissions and steps at each one
  let d = `M ${x(0)} ${y(points[0].minEntropy)}`;
  for (let i = 1; i < points.length; i++) {
    d += ` L ${x(i)} ${y(points[i - 1].minEntropy)} L ${x(i)} ${y(points[i].minEntropy)}`;
  }
  const dots = points.map((p) => `<circle cx="${x(p.k)}" cy="${y(p.minEntropy)}" r="3.5" fill="#f76900"/>`).join('');
  const xticks = points.map((p) =>
    `<text x="${x(p.k)}" y="${H - B + 16}" font-size="11" fill="#6b7a99" text-anchor="middle">${p.k}</text>`).join('');
  const yticks = Array.from({ length: Math.round(maxY) + 1 }, (_, i) =>
    `<line x1="${L}" y1="${y(i)}" x2="${W - R}" y2="${y(i)}" stroke="#ece7da" stroke-width="1"/>
     <text x="${L - 8}" y="${y(i) + 4}" font-size="11" fill="#6b7a99" text-anchor="end">${i}</text>`).join('');

  return `
    <h4 style="margin:1rem 0 .2rem;font-size:.9rem;color:var(--navy)">Knowledge as the stream arrives</h4>
    <svg class="curve" viewBox="0 0 ${W} ${H}" role="img"
         aria-label="Min-entropy leakage in bits as a function of how many emissions the observer has seen">
      ${yticks}
      <line x1="${L}" y1="${y(prior)}" x2="${W - R}" y2="${y(prior)}" stroke="#b7410e" stroke-width="1.5" stroke-dasharray="5 4"/>
      <text x="${W - R}" y="${y(prior) - 6}" font-size="11" fill="#b7410e" text-anchor="end">the whole secret (${fmtBits(prior)} bits)</text>
      <path d="${d}" fill="none" stroke="#0aa6b7" stroke-width="2.5"/>
      ${dots}
      <line x1="${L}" y1="${T}" x2="${L}" y2="${H - B}" stroke="#26304a" stroke-width="1.5"/>
      <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="#26304a" stroke-width="1.5"/>
      ${xticks}
      <text x="${(L + W - R) / 2}" y="${H - 4}" font-size="11.5" fill="#26304a" text-anchor="middle">emissions observed</text>
      <text x="12" y="${(T + H - B) / 2}" font-size="11.5" fill="#26304a" text-anchor="middle"
            transform="rotate(-90 12 ${(T + H - B) / 2})">bits known</text>
    </svg>
    <p class="footnote">
      Each step is a release event. Between events the attacker's knowledge is flat; at an event it rises by exactly
      the quantity released — Sabelfeld &amp; Sands' <em>gradual release</em>, drawn.
    </p>`;
}

function checkerTab(chal, a) {
  const { chk } = a;
  const list = chk.constraints.map((c) => {
    const cls = !c.ok ? 'bad' : (c.raises ? 'pc' : 'ok');
    const mark = !c.ok ? '✗' : (c.raises ? '↑' : '✓');
    return `<div class="c ${cls}">
      <span class="mark">${mark}</span>
      <span><span class="lno">${c.line}:</span> <span class="stmt">${esc(c.stmt)}</span>
        <div class="why">${esc(c.why)}</div></span>
    </div>`;
  }).join('');

  const bits = a.byObserver;
  const unsound = chk.accepted && (bits.stream.minEntropy > 0 || bits.timing.minEntropy > 0);
  const imprecise = !chk.accepted && bits.batch.minEntropy === 0;

  let gap = '';
  if (unsound) {
    gap = `<div class="summary" style="border-left:3px solid var(--danger)">
      <b>Accepted, and still leaking.</b> The checker is sound only for the batch observer. Here the stream
      observer gets ${fmtBits(bits.stream.minEntropy)} bits and the timing observer
      ${fmtBits(bits.timing.minEntropy)} — through channels no constraint above even mentions.</div>`;
  } else if (imprecise) {
    gap = `<div class="summary" style="border-left:3px solid var(--orange)">
      <b>Rejected, and nothing leaks.</b> The batch observer learns 0 bits. This is the price of soundness:
      the analysis tracks syntactic dependence, and deciding real dependence is undecidable.</div>`;
  }

  return `
    <div class="banner ${chk.accepted ? 'accept' : 'reject'}">
      ${chk.accepted
        ? '✓ ACCEPTED — every flow constraint is satisfied'
        : `✗ REJECTED — ${chk.violations.length} violated constraint${chk.violations.length === 1 ? '' : 's'}`}
    </div>
    ${gap}
    <div class="checklist">${list}</div>
    <p class="footnote">
      Two-point lattice L &lt; H; ↑ marks a statement that raises the program-counter label over its body.
      Each row is the constraint <span class="mono">label(e) ⊔ pc ≤ label(target)</span>. Violated rows are
      highlighted in the program listing on the left.
    </p>`;
}

function discTab(chal) {
  const fix = chal.fix ? `
    <div class="fixbox">
      <h4>${esc(chal.fix.title)}</h4>
      <p style="margin:.2rem 0 .5rem">${esc(chal.fix.note)}</p>
      <button class="ghost" id="loadfix">Load it into the bench and analyse it →</button>
    </div>` : '';
  return `<div class="disc">${chal.discussion}${fix}</div>`;
}

function benchTab(chal) {
  const b = state.bench[chal.id] || { source: chal.source, labels: chal.labels };
  const labelStr = Object.entries(b.labels).map(([k, v]) => `${k}:${v}`).join(', ');
  return `
    <div class="bench">
      <p style="font-size:.87rem;margin:0 0 .5rem">
        Edit the program, or the labels, and re-run the whole analysis over the same input space
        (<span class="mono">${esc(Object.entries(chal.high).map(([k, v]) => `${k} ∈ ${v.length} values`).join(', '))}</span>).
        Patch the leak, break it again, or paste in a student's proposal.
      </p>
      <textarea id="bsrc" spellcheck="false">${esc(b.source)}</textarea>
      <div class="row">
        <label for="blabels">Labels:</label>
        <input type="text" id="blabels" value="${esc(labelStr)}" spellcheck="false">
        <button class="primary" id="brun">Run</button>
        <button class="ghost" id="breset">Reset</button>
      </div>
      <div id="bout"></div>
    </div>`;
}

function benchResult(chal, source, labels) {
  let a;
  try {
    a = analyse(chal, source, labels);
  } catch (e) {
    return `<div class="err">${esc(e instanceof ParseError ? `parse error, ${e.message}` : e.message)}</div>`;
  }
  const errRun = a.runs.find((r) => r.result.error);
  const obs = OBSERVERS[observerOf(chal)];
  const l = leakage(a.runs, obs.key);
  const classes = [...l.classes.values()].map((members, i) =>
    `<tr><td><span class="cbadge" style="background:${classColor(i)}">C${i + 1}</span></td>
      <td class="mono">${esc(obs.render(members[0].result))}</td><td>${members.length}</td></tr>`).join('');

  return `
    ${errRun ? `<div class="err" style="margin-bottom:.6rem">runtime error: ${esc(errRun.result.error)}</div>` : ''}
    <div class="banner ${a.chk.accepted ? 'accept' : 'reject'}" style="margin-top:.6rem">
      ${a.chk.accepted ? '✓ checker ACCEPTS' : `✗ checker REJECTS — ${a.chk.violations.map((v) => `line ${v.line}`).join(', ')}`}
    </div>
    <div class="bars">${OBSERVER_ORDER.map((o) =>
      bar(OBSERVERS[o].name, a.byObserver[o].minEntropy, log2(a.runs.length))).join('')}</div>
    <table class="runs">
      <thead><tr><th></th><th>${esc(obs.name)} observation</th><th>secrets</th></tr></thead>
      <tbody>${classes}</tbody>
    </table>`;
}

// -------------------------------------------------------------------- wiring

function wire(chal, a) {
  const root = document.getElementById('app');

  root.querySelectorAll('[data-goto]').forEach((b) => b.onclick = () => {
    state.current[state.mode] = b.dataset.goto;
    render();
  });

  root.querySelectorAll('[data-opt]').forEach((b) => b.onclick = () => {
    if (state.answers[chal.id]) return;
    state.picked[chal.id] = Number(b.dataset.opt);
    render();
  });

  const submit = root.querySelector('#submit');
  if (submit) submit.onclick = () => answer(chal, state.picked[chal.id]);

  const skip = root.querySelector('#skip');
  if (skip) skip.onclick = () => answer(chal, -1);

  root.querySelectorAll('[data-tab]').forEach((b) => b.onclick = () => {
    state.tab[chal.id] = b.dataset.tab;
    render();
  });

  root.querySelectorAll('[data-obs]').forEach((b) => b.onclick = () => {
    state.observer[chal.id] = b.dataset.obs;
    render();
  });

  const low = root.querySelector('#lowctl');
  if (low) low.onchange = () => {
    state.low[chal.id] = { ...(state.low[chal.id] || {}), [chal.lowControl.name]: Number(low.value) };
    render();
  };

  const loadfix = root.querySelector('#loadfix');
  if (loadfix) loadfix.onclick = () => {
    state.bench[chal.id] = { source: chal.fix.source, labels: chal.fix.labels };
    state.tab[chal.id] = 'bench';
    render();
    document.getElementById('brun')?.click();
  };

  const brun = root.querySelector('#brun');
  if (brun) brun.onclick = () => {
    const source = document.getElementById('bsrc').value;
    const labels = {};
    for (const part of document.getElementById('blabels').value.split(',')) {
      const [k, v] = part.split(':').map((s) => s.trim());
      if (k) labels[k] = v === 'H' ? 'H' : 'L';
    }
    state.bench[chal.id] = { source, labels };
    document.getElementById('bout').innerHTML = benchResult(chal, source, labels);
  };

  const breset = root.querySelector('#breset');
  if (breset) breset.onclick = () => {
    delete state.bench[chal.id];
    render();
  };
}

function answer(chal, picked) {
  state.answers[chal.id] = { picked, correct: picked === chal.question.answer };
  state.tab[chal.id] = state.tab[chal.id] || 'runs';
  persist();
  render();
}

function step(delta) {
  const inMode = CHALLENGES.filter((c) => c.mode === state.mode);
  const i = inMode.findIndex((c) => c.id === state.current[state.mode]);
  const next = inMode[i + delta];
  if (next) { state.current[state.mode] = next.id; render(); return; }
  const mi = MODES.findIndex((m) => m.id === state.mode);
  const nm = MODES[mi + delta];
  if (!nm) return;
  state.mode = nm.id;
  const list = CHALLENGES.filter((c) => c.mode === nm.id);
  state.current[nm.id] = delta > 0 ? list[0].id : list[list.length - 1].id;
  render();
}

document.addEventListener('keydown', (e) => {
  if (e.target.matches('textarea, input, select')) return;
  const chal = CHALLENGES.find((c) => c.id === state.current[state.mode]);
  if (e.key >= '1' && e.key <= '4') {
    const i = Number(e.key) - 1;
    if (!state.answers[chal.id] && i < chal.question.options.length) {
      state.picked[chal.id] = i;
      render();
    }
  } else if (e.key === 'Enter') {
    if (!state.answers[chal.id] && state.picked[chal.id] !== undefined) answer(chal, state.picked[chal.id]);
  } else if (e.key === 'ArrowRight') { step(1); }
  else if (e.key === 'ArrowLeft') { step(-1); }
});

document.querySelectorAll('nav.modes button').forEach((b) => b.onclick = () => {
  state.mode = b.dataset.mode;
  render();
});

document.getElementById('reset').onclick = () => {
  state.answers = {};
  state.picked = {};
  state.tab = {};
  state.bench = {};
  persist();
  render();
};

render();

// Exposed for smoke.mjs, which renders every challenge/tab/observer headlessly.
export const __test = { state, render, benchResult, analyse };
