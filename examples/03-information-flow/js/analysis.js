// Observers, noninterference, and quantitative leakage.
//
// A run of a program produces a trace. WHAT AN ATTACKER LEARNS depends entirely
// on which function of that trace they get to see — the observer *is* the threat
// model. We define three, in increasing distinguishing power:
//
//   O_batch (r)  =  ⊥                       if r diverges      (all ⊥ identified)
//                =  the output sequence     if r halts
//   O_stream(r)  =  the output sequence, plus whether it halted
//   O_time  (r)  =  the output sequence with a timestamp on every emission,
//                   plus the total running time
//
// O_batch ⊑ O_stream ⊑ O_time: each is a function of the next, so leakage is
// monotone along the chain. O_batch is termination-INsensitive (the classic
// batch-job model: you only ever see the finished output). O_stream is
// progress-sensitive: the observer is watching the pipe, so a prefix followed by
// unbounded silence is itself an observation.
//
// Noninterference w.r.t. O: for all high inputs h, h' agreeing on the low
// inputs,   O(⟦P⟧(h)) = O(⟦P⟧(h')).   We decide this by ENUMERATING the declared
// finite high domain. That is a decision procedure for these challenges only;
// noninterference is undecidable in general.
//
// Leakage, with a uniform prior on a high domain of size N and a deterministic
// program (so the observation partitions the domain into classes C_1..C_k):
//
//   Shannon:      I(H;O) = H(H) - H(H|O) = log2 N - Σ_i (|C_i|/N) log2 |C_i|
//   min-entropy:  L(H;O) = H_∞(H) - H_∞(H|O) = log2 k
//
// The min-entropy measure (Smith, FoSSaCS 2009) is the one that bounds an
// attacker's single-guess success probability, and it is usually the honest
// number to quote for a key-recovery threat model.

import { run } from './lang.js';

// ------------------------------------------------------------------ helpers

/** Cartesian product of {name: [values...]} into an array of stores. */
export function product(domains) {
  const names = Object.keys(domains);
  let rows = [{}];
  for (const n of names) {
    const next = [];
    for (const row of rows) for (const v of domains[n]) next.push({ ...row, [n]: v });
    rows = next;
  }
  return rows;
}

const seq = (r) => r.outputs.map((o) => o.value);

// ---------------------------------------------------------------- observers

export const OBSERVERS = {
  batch: {
    id: 'batch',
    name: 'Batch',
    blurb: 'sees the finished output sequence, and only if the program terminates',
    formal: 'O_batch(r) = ⊥ if r diverges, else the output sequence',
    key: (r) => (r.halted ? `v:${JSON.stringify(seq(r))}` : 'bottom'),
    render: (r) => (r.halted ? `[${seq(r).join(', ')}]` : '⊥ (no output ever arrives)'),
  },
  stream: {
    id: 'stream',
    name: 'Stream',
    blurb: 'watches the pipe: sees each value as it is emitted, and sees the silence after the last one',
    formal: 'O_stream(r) = (output sequence, halted?)',
    key: (r) => `v:${JSON.stringify(seq(r))}|${r.halted ? 'halt' : 'silent'}`,
    render: (r) => `[${seq(r).join(', ')}]${r.halted ? '' : ' then silence…'}`,
  },
  timing: {
    id: 'timing',
    name: 'Timing',
    blurb: 'the stream observer, plus a clock on every emission and on termination',
    formal: 'O_time(r) = ((v_i, τ_i)_i, total time)',
    key: (r) => `t:${JSON.stringify(r.outputs.map((o) => [o.value, o.time]))}|${r.halted ? r.time : 'silent'}`,
    render: (r) => {
      const body = r.outputs.map((o) => `${o.value}@${o.time}`).join(', ');
      return `[${body}]${r.halted ? ` total ${r.time}` : ' then silence…'}`;
    },
  },
};

export const OBSERVER_ORDER = ['batch', 'stream', 'timing'];

// ------------------------------------------------------------------ leakage

export function log2(x) { return Math.log(x) / Math.LN2; }

/**
 * Partition runs by an observation key and compute both leakage measures.
 * @param {Array} runs   [{inputs, result}]
 * @param {(r)=>string} keyOf
 */
export function leakage(runs, keyOf) {
  const N = runs.length;
  const classes = new Map();
  for (const r of runs) {
    const k = keyOf(r.result);
    if (!classes.has(k)) classes.set(k, []);
    classes.get(k).push(r);
  }
  const sizes = [...classes.values()].map((c) => c.length);
  const shannon = log2(N) - sizes.reduce((acc, n) => acc + (n / N) * log2(n), 0);
  return {
    total: N,
    classes,
    numClasses: classes.size,
    prior: log2(N),
    shannon: Math.max(0, shannon),
    minEntropy: log2(classes.size),
    interferenceFree: classes.size === 1,
  };
}

/** Run a challenge program over its whole declared input space. */
export function runAll(ast, highDomains, lowInputs = {}, opts = {}) {
  return product(highDomains).map((high) => ({
    inputs: { ...high, ...lowInputs },
    high,
    result: run(ast, { ...high, ...lowInputs }, opts),
  }));
}

/** Leakage under every observer, for the standard side-by-side comparison. */
export function leakageByObserver(runs) {
  const out = {};
  for (const id of OBSERVER_ORDER) out[id] = leakage(runs, OBSERVERS[id].key);
  return out;
}

/**
 * Knowledge as a function of how much of the stream the observer has seen.
 * At step k the observer has seen the first k emissions; a run that has not
 * produced a k-th emission yet is distinguishable from one that has (that is
 * precisely the progress channel). Returns min-entropy and Shannon leakage per k.
 */
export function knowledgeCurve(runs, { withTime = false } = {}) {
  const maxOut = Math.max(0, ...runs.map((r) => r.result.outputs.length));
  const pts = [];
  for (let k = 0; k <= maxOut; k++) {
    const keyOf = (r) => {
      const seen = r.outputs.slice(0, k);
      const body = withTime ? seen.map((o) => [o.value, o.time]) : seen.map((o) => o.value);
      // fewer than k emissions => the observer is still waiting, which they can tell
      const stalled = r.outputs.length < k ? (r.halted ? '|halted' : '|silent') : '';
      return JSON.stringify(body) + stalled;
    };
    const l = leakage(runs, keyOf);
    pts.push({ k, minEntropy: l.minEntropy, shannon: l.shannon, numClasses: l.numClasses });
  }
  return { points: pts, prior: log2(runs.length) };
}

/** Per-output-position leakage: what does emission #i alone reveal? */
export function perOutputLeakage(runs) {
  const maxOut = Math.max(0, ...runs.map((r) => r.result.outputs.length));
  const rows = [];
  for (let i = 0; i < maxOut; i++) {
    const l = leakage(runs, (r) => JSON.stringify(r.outputs[i]?.value ?? null));
    rows.push({ index: i, minEntropy: l.minEntropy, numClasses: l.numClasses });
  }
  return rows;
}

export const fmtBits = (b) => (Math.abs(b - Math.round(b)) < 1e-9 ? String(Math.round(b)) : b.toFixed(3));
