#!/usr/bin/env node
// Headless UI smoke test: renders every challenge, in every reveal tab, under
// every observer, against a minimal DOM stub. Catches the render-time errors a
// browser would otherwise find during lecture.

class El {
  constructor(id = '') { this.id = id; this._html = ''; this.dataset = {}; this.value = ''; }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  matches() { return false; }
  setAttribute() {}
  addEventListener() {}
}

const els = new Map();
const getEl = (id) => { if (!els.has(id)) els.set(id, new El(id)); return els.get(id); };

globalThis.document = {
  getElementById: getEl,
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener: () => {},
};
globalThis.localStorage = {
  _d: {},
  getItem(k) { return this._d[k] ?? null; },
  setItem(k, v) { this._d[k] = v; },
};

const { __test } = await import('./js/app.js');
const { CHALLENGES } = await import('./js/challenges.js');
const { OBSERVER_ORDER } = await import('./js/analysis.js');
const { state, render, benchResult } = __test;

let failures = 0;
let renders = 0;
const app = getEl('app');

const must = (cond, msg) => { if (!cond) { failures++; console.log(`  FAIL  ${msg}`); } };

for (const c of CHALLENGES) {
  state.mode = c.mode;
  state.current[c.mode] = c.id;

  // unanswered: question visible, reveal hidden
  delete state.answers[c.id];
  render(); renders++;
  must(app.innerHTML.includes('Question'), `${c.id}: unanswered view has no question`);
  must(!app.innerHTML.includes('Runs &amp; classes'), `${c.id}: reveal leaked before answering`);
  must(app.innerHTML.includes(c.title.replace(/&/g, '&amp;')), `${c.id}: title missing`);

  // answered: every tab, every observer
  state.answers[c.id] = { picked: c.question.answer, correct: true };
  for (const tab of ['runs', 'leak', 'checker', 'disc', 'bench']) {
    state.tab[c.id] = tab;
    for (const obs of OBSERVER_ORDER) {
      state.observer[c.id] = obs;
      render(); renders++;
      must(app.innerHTML.length > 800, `${c.id}/${tab}/${obs}: suspiciously short render`);
      must(!app.innerHTML.includes('undefined'), `${c.id}/${tab}/${obs}: 'undefined' in output`);
      must(!app.innerHTML.includes('NaN'), `${c.id}/${tab}/${obs}: 'NaN' in output`);
    }
    delete state.observer[c.id];
  }

  // the bench, on the original program and on the fix
  const b1 = benchResult(c, c.source, c.labels);
  must(b1.includes('checker'), `${c.id}: bench produced no verdict`);
  must(!b1.includes('class="err"'), `${c.id}: bench errored on its own program`);
  if (c.fix) {
    const b2 = benchResult(c, c.fix.source, c.fix.labels);
    must(!b2.includes('class="err"'), `${c.id}: bench errored on the fix`);
  }
  // the bench must report a parse error rather than throwing
  const bad = benchResult(c, 'x = ;', c.labels);
  must(bad.includes('class="err"'), `${c.id}: bench swallowed a parse error`);

  // the public-input control, if any
  if (c.lowControl) {
    for (const opt of c.lowControl.options) {
      state.low[c.id] = { [c.lowControl.name]: opt.value };
      state.tab[c.id] = 'leak';
      render(); renders++;
      must(!app.innerHTML.includes('NaN'), `${c.id}: guess=${opt.text} produced NaN`);
    }
    delete state.low[c.id];
  }
  console.log(`  ok  ${c.id}`);
}

console.log(`\n${failures === 0 ? 'OK' : 'FAILED'} — ${renders} renders, ${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
