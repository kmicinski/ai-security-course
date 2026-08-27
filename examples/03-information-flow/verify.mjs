#!/usr/bin/env node
// Checks every challenge's stated expectations against the real interpreter,
// the real Denning checker, and the real leakage computation. Run it after
// editing any program or any `expect` block:
//
//     node verify.mjs
//
// Exits non-zero on any mismatch, so it is safe to wire into CI.

import { parse, run } from './js/lang.js';
import { check } from './js/checker.js';
import { runAll, leakageByObserver, fmtBits, knowledgeCurve, OBSERVER_ORDER } from './js/analysis.js';
import { CHALLENGES } from './js/challenges.js';

let failures = 0;
let checks = 0;

const eq = (label, got, want) => {
  checks++;
  const ok = Math.abs(got - want) < 1e-9 || got === want;
  if (!ok) {
    failures++;
    console.log(`    FAIL  ${label}: got ${got}, expected ${want}`);
  }
  return ok;
};

function analyse(source, labels, high, fixed) {
  const ast = parse(source);
  const chk = check(ast, labels);
  const runs = runAll(ast, high, fixed);
  return { ast, chk, runs, leak: leakageByObserver(runs) };
}

for (const c of CHALLENGES) {
  console.log(`\n[${c.mode}] ${c.id} — ${c.title}`);
  let a;
  try {
    a = analyse(c.source, c.labels, c.high, c.fixed);
  } catch (err) {
    failures++;
    console.log(`    FAIL  did not parse/run: ${err.message}`);
    continue;
  }

  const errs = a.runs.filter((r) => r.result.error);
  if (errs.length) {
    failures++;
    console.log(`    FAIL  runtime error on ${errs.length} run(s): ${errs[0].result.error}`);
  }

  eq('checker accepted', a.chk.accepted, c.expect.accepted);
  eq('violations', a.chk.violations.length, c.expect.violations);
  eq('batch bits (min-entropy)', a.leak.batch.minEntropy, c.expect.batchBits);
  eq('stream bits (min-entropy)', a.leak.stream.minEntropy, c.expect.streamBits);
  eq('timing bits (min-entropy)', a.leak.timing.minEntropy, c.expect.timingBits);

  // the observer hierarchy must be monotone: batch ⊑ stream ⊑ timing
  checks++;
  const [b, s, t] = OBSERVER_ORDER.map((o) => a.leak[o].minEntropy);
  if (!(b <= s + 1e-9 && s <= t + 1e-9)) {
    failures++;
    console.log(`    FAIL  observer hierarchy not monotone: ${b} / ${s} / ${t}`);
  }

  // the checker must be sound for the BATCH observer: accept ⇒ 0 batch bits
  checks++;
  if (a.chk.accepted && a.leak.batch.minEntropy > 1e-9) {
    failures++;
    console.log('    FAIL  checker accepted a program that leaks to the batch observer');
  }

  const shan = OBSERVER_ORDER.map((o) => `${fmtBits(a.leak[o].shannon)}`).join(' / ');
  console.log(`    checker: ${a.chk.accepted ? 'ACCEPT' : `REJECT (${a.chk.violations.length})`}`
    + `   runs: ${a.runs.length}   min-entropy bits (b/s/t): ${b} / ${s} / ${t}`
    + `   shannon: ${shan}   prior: ${fmtBits(a.leak.batch.prior)}`);

  if (c.curve) {
    const cv = knowledgeCurve(a.runs);
    console.log(`    knowledge curve (min-entropy bits by emissions seen): `
      + cv.points.map((p) => `${p.k}:${fmtBits(p.minEntropy)}`).join('  '));
  }

  if (c.fix) {
    let f;
    try {
      f = analyse(c.fix.source, c.fix.labels, c.high, c.fixed);
    } catch (err) {
      failures++;
      console.log(`    FAIL  fix did not parse/run: ${err.message}`);
      continue;
    }
    console.log(`    fix — checker: ${f.chk.accepted ? 'ACCEPT' : `REJECT (${f.chk.violations.length})`}`
      + `   bits (b/s/t): ${OBSERVER_ORDER.map((o) => f.leak[o].minEntropy).join(' / ')}`);
    eq('fix: checker accepted', f.chk.accepted, c.fix.expect.accepted);
    eq('fix: timing bits', f.leak.timing.minEntropy, c.fix.expect.timingBits);

    // the fix must not be constant-time by accident of an unreachable path
    checks++;
    const times = new Set(f.runs.map((r) => r.result.time));
    if (c.fix.expect.timingBits === 0 && times.size !== 1) {
      failures++;
      console.log(`    FAIL  fix claims 0 timing bits but has ${times.size} distinct running times`);
    }
  }
}

// ---- language-level sanity checks, independent of the challenge set --------

console.log('\n[lang] sanity');
const t1 = run(parse('x = 3; y = x * 2 + 1; out(y);'), {});
eq('arithmetic', t1.outputs[0]?.value, 7);
eq('halts', t1.halted, true);
eq('cost model: three statements', t1.time, 3);

const t2 = run(parse('while (1) { skip; }'), {}, { maxSteps: 50 });
eq('divergence detected', t2.halted, false);
eq('divergence has no clock', t2.time, null);

const t3 = run(parse('out(digit(4821, 0)); out(digit(4821, 2));'), {});
eq('digit(4821,0)', t3.outputs[0]?.value, 1);
eq('digit(4821,2)', t3.outputs[1]?.value, 8);

const t4 = run(parse('out(7 / 2); out(0 - 7 / 2);'), {});
eq('integer division truncates toward zero', t4.outputs[0]?.value, 3);
eq('negative division truncates toward zero', t4.outputs[1]?.value, -3);

const t5 = run(parse('x = 0; if (x) { out(1); } else { out(2); } if (!x) { out(3); }'), {});
eq('0 is false', t5.outputs[0]?.value, 2);
eq('! of 0 is true', t5.outputs[1]?.value, 3);

console.log(`\n${failures === 0 ? 'OK' : 'FAILED'} — ${checks - failures}/${checks} checks passed`);
process.exit(failures === 0 ? 0 : 1);
