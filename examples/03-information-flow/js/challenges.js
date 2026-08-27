// The challenge set. Three modes, eight programs.
//
// Every `expect` block is checked by verify.mjs against the actual interpreter,
// checker, and leakage computation — so if you edit a program, run
// `node verify.mjs` and fix the expectations rather than trusting the prose.

export const CHALLENGES = [
  // ------------------------------------------------------------ batch mode
  {
    id: 'a1',
    mode: 'batch',
    title: 'Laundering through arithmetic',
    threat: 'A payroll job reads salary data and writes one public number. The observer runs the job and reads what it printed, once, at the end.',
    labels: { salary: 'H', bonus: 'H', t: 'H', avg: 'L' },
    high: { salary: [60000, 90000, 120000, 150000] },
    fixed: { bonus: 5000 },
    observer: 'batch',
    source: `// salary, bonus, t : H        avg : L        out : the public channel
t   = salary + bonus;
avg = t - bonus;
out(avg);`,
    question: {
      prompt: '<code>salary</code> is uniform over four values, so it carries 2 bits. How much does the batch observer learn?',
      options: [
        '0 bits — <code>salary</code> is never assigned to a public variable',
        '1 bit',
        '2 bits — all of it',
        'Undecidable without knowing the bonus',
      ],
      answer: 2,
    },
    expect: { accepted: false, violations: 1, batchBits: 2, streamBits: 2, timingBits: 2 },
    discussion: `
      <p>The label of a computed value is the <em>join</em> of the labels of everything
      that fed it, so <code>t</code> is <code>H</code>, and subtracting a secret back
      out does not lower it. Algebra does not launder labels: the checker is a type
      system, and <code>H ≤ L</code> is simply false.</p>
      <p>The interesting part is that here the type system and the semantics agree
      exactly — 1 violated constraint, 2 bits actually gone. That agreement is the
      exception, not the rule; the next two programs break it in both directions.</p>`,
  },

  {
    id: 'a2',
    mode: 'batch',
    title: 'A leak with no assignment',
    threat: 'Same batch observer. This time no secret is ever copied into a public variable — every value written to <code>public</code> is a literal constant.',
    labels: { salary: 'H', public: 'L' },
    high: { salary: [60000, 90000, 120000, 150000] },
    fixed: {},
    observer: 'batch',
    source: `// salary : H        public : L
public = 0;
if (salary > 100000) {
  public = 1;
}
out(public);`,
    question: {
      prompt: 'A dataflow analysis that tracks <em>copies</em> sees nothing wrong. How much does the batch observer learn?',
      options: [
        '0 bits — only the constants 0 and 1 are ever written',
        '1 bit',
        '2 bits — all of it',
        'It depends on the salary distribution',
      ],
      answer: 1,
    },
    expect: { accepted: false, violations: 1, batchBits: 1, streamBits: 1, timingBits: 1 },
    discussion: `
      <p>The flow is through <strong>control</strong>, not data. Denning's fix is the
      program-counter label: entering a branch guarded by an <code>H</code> expression
      raises <code>pc</code> to <code>H</code>, and every assignment inside is charged
      against it, so <code>public = 1</code> requires <code>L ⊔ H = H ≤ L</code> and
      fails. Look at the checker tab: the violated constraint is on the assignment,
      not on the <code>out</code>.</p>
      <p>Note the <em>quantity</em>. The secret has 2 bits; the observer gets exactly 1,
      the answer to "is the salary above 100000?". A one-bit predicate is all a
      one-bit channel can carry — which is the whole content of the branch.</p>
      <p class="teach">Tie-back: this is the same failure as every control/data confusion
      in the course. The channel was never meant to carry information; it carries it anyway.</p>`,
  },

  {
    id: 'a3',
    mode: 'batch',
    title: 'The checker rejects it. So how bad is it?',
    threat: 'Same batch observer. The checker will reject this program — four times over. Your job is to say what actually escapes.',
    labels: { h: 'H', x: 'L', y: 'L' },
    high: { h: [0, 1, 2, 3] },
    fixed: {},
    observer: 'batch',
    source: `// h : H, uniform on {0,1,2,3}        x, y : L
x = 0;
y = 0;
if (h >= 2) {
  x = 1;
  y = 0;
} else {
  x = 0;
  y = 1;
}
out(x + y);
out(x - y);`,
    question: {
      prompt: '<code>h</code> carries 2 bits. How many does the batch observer get?',
      options: [
        '0 bits — the assignments cancel out',
        '1 bit',
        '2 bits — the checker rejected it, so everything leaks',
        'It cannot be determined without running the program',
      ],
      answer: 1,
    },
    expect: { accepted: false, violations: 4, batchBits: 1, streamBits: 1, timingBits: 1 },
    perOutputNote: true,
    discussion: `
      <p>Open the <strong>Runs</strong> tab and look at the two emissions separately.
      <code>x + y</code> is <code>1</code> on every path — that output alone carries
      <strong>0 bits</strong>, and the checker rejects it anyway. That is exactly the
      sound-but-incomplete example from lecture: the analysis reasons about the shape
      of the program, never about the function it computes, and deciding the latter is
      undecidable.</p>
      <p><code>x - y</code> is <code>+1</code> or <code>-1</code>, so it carries
      <strong>1 bit</strong> — the predicate <code>h ≥ 2</code>. Together: 1 bit, not 2.
      The other bit of <code>h</code> (which of 0 and 1, or which of 2 and 3) never
      reaches the observer at all.</p>
      <p>So four rejected constraints correspond to one leaked bit and one perfectly
      safe output. <strong>A label is a yes/no verdict; leakage is a number.</strong>
      The type system cannot tell you which of those four rejections mattered, and it
      is not designed to. When you need the quantity — how many guesses does this save
      an attacker? — you need a quantitative theory, not a lattice.</p>`,
  },

  // ----------------------------------------------------------- stream mode
  {
    id: 'b1',
    mode: 'stream',
    title: 'The stream that stops',
    threat: 'The program streams progress to a public log. The observer is watching the log live — so they see each line as it lands, and they see when the lines stop coming.',
    labels: { h: 'H', i: 'L' },
    high: { h: [0, 1, 2, 3] },
    fixed: {},
    observer: 'stream',
    source: `// h : H on {0,1,2,3}        i : L
i = 0;
while (i < 4) {
  out(i);
  if (i == h) {
    while (1) { skip; }     // wedge
  }
  i = i + 1;
}`,
    question: {
      prompt: 'The Denning checker <strong>accepts</strong> this program — every constraint is satisfied. Which observers learn something about <code>h</code>?',
      options: [
        'None — the checker accepted it, and the checker is sound',
        'All three: batch, stream, and timing',
        'Stream and timing only; the batch observer learns 0 bits',
        'Timing only',
      ],
      answer: 2,
    },
    expect: { accepted: true, violations: 0, batchBits: 0, streamBits: 2, timingBits: 2 },
    curve: true,
    discussion: `
      <p>Nothing is mislabelled. <code>out(i)</code> emits a public counter at
      <code>pc = L</code>; the wedge assigns nothing, so the raised <code>pc</code>
      inside the branch is never charged for anything. The checker is right, on its own
      terms — and the observer still recovers <code>h</code> exactly.</p>
      <p>The batch observer learns <strong>0 bits</strong>: no run terminates, so every
      run looks the same (<code>⊥</code>) to someone who only reads finished output.
      The stream observer learns <strong>2 bits</strong> — all of <code>h</code> — from
      where the stream stops. Same program, same labels, different threat model,
      different answer.</p>
      <p>This is the precise sense in which the pc-discipline is only
      <em>termination-insensitive</em> sound. Progress-sensitive noninterference is a
      strictly stronger property, and enforcing it means rejecting essentially every
      loop whose trip count depends on a secret — which is why most practical IFC
      systems do not even try, and document the residual channel instead.</p>
      <p class="teach">Ask the room: what is the <em>bandwidth</em> of this channel? One
      run of this program yields 2 bits. If the wedge were a 200 ms sleep instead of a
      hang, it would yield 2 bits per run, repeatedly.</p>`,
  },

  {
    id: 'b2',
    mode: 'stream',
    title: 'Gradual release, one bit at a time',
    threat: 'A service answers range queries about a secret salary bucket and streams each answer as it is computed. Each individual answer looks like a harmless comparison.',
    labels: { secret: 'H', lo: 'L', hi: 'L', mid: 'L' },
    high: { secret: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] },
    fixed: {},
    observer: 'stream',
    source: `// secret : H, uniform on {0,...,15}        lo, hi, mid : L
lo = 0;
hi = 16;
while (hi - lo > 1) {
  mid = (lo + hi) / 2;
  if (secret < mid) {
    out(0);
    hi = mid;
  } else {
    out(1);
    lo = mid;
  }
}`,
    question: {
      prompt: 'The secret carries 4 bits. After the observer has seen exactly <strong>two</strong> emissions, how much do they know?',
      options: ['0 bits', '1 bit', '2 bits', '4 bits — the loop is deterministic, so seeing any of it gives all of it'],
      answer: 2,
    },
    expect: { accepted: false, violations: 4, batchBits: 4, streamBits: 4, timingBits: 4 },
    curve: true,
    discussion: `
      <p>Each emission is one bit of a binary search, and the observer's knowledge climbs
      a staircase: 0, 1, 2, 3, 4 bits. By the last emission the secret is fully
      determined. Look at the knowledge curve — that staircase <em>is</em>
      Sabelfeld–Sands <strong>gradual release</strong> drawn as a graph: the attacker's
      knowledge is flat between release events and steps up by exactly the released
      quantity at each one.</p>
      <p>The lesson for design: every individual answer here is defensible in isolation
      ("it is only a comparison against a public constant"). The policy question is
      never about one release, it is about the <em>sequence</em>. Ask the four axes —
      <strong>what</strong> may be released, <strong>who</strong> may trigger it,
      <strong>where</strong> in the code, and <strong>when</strong> — and note that this
      program answers the first three fine and fails the fourth catastrophically,
      because nothing bounds how many times you may ask.</p>
      <p class="teach">This is the shape of most real-world "aggregate-only" APIs, and the
      reason differential privacy budgets exist: the bound has to be on the whole
      sequence of queries, not on any single one.</p>`,
  },

  {
    id: 'b3',
    mode: 'stream',
    title: 'Same values, different order',
    threat: 'Two records are published to a public feed. Both runs publish the same two records — nothing is added, nothing is withheld.',
    labels: { h: 'H' },
    high: { h: [0, 1] },
    fixed: {},
    observer: 'stream',
    source: `// h : H on {0,1}
if (h == 1) {
  out(7);
  out(9);
} else {
  out(9);
  out(7);
}`,
    question: {
      prompt: 'The <em>multiset</em> of emitted values, {7, 9}, is identical in both runs. How much does the stream observer learn?',
      options: ['0 bits — the multiset is identical', '1 bit', '2 bits', 'Only under a timing observer'],
      answer: 1,
    },
    expect: { accepted: false, violations: 4, batchBits: 1, streamBits: 1, timingBits: 1 },
    discussion: `
      <p>An observer who sees a <em>set</em> or a <em>count</em> learns nothing. An
      observer who sees a <em>sequence</em> learns the whole secret. Nothing about the
      program changed between those two sentences — only the observation function.</p>
      <p>That is the point worth carrying out of stream mode: <strong>the observer is
      part of the threat model, and it is the part people forget to write down.</strong>
      "We only expose aggregates" is not a policy until you say what the client can
      observe — order, arrival time, size, retry behaviour, which shard answered.
      Ordering channels are real: they show up in log interleaving, in packet ordering,
      and in which of two async requests resolves first.</p>
      <p>Notice too that batch and stream agree here (both 1 bit). Not every streaming
      program separates the observers — <code>b1</code> separates them because it
      exploits <em>progress</em>, which is exactly the dimension batch observation
      throws away.</p>`,
  },

  // ----------------------------------------------------------- timing mode
  {
    id: 'c1',
    mode: 'timing',
    title: 'Label-clean, clock-dirty',
    threat: 'The observer sees the public channel and owns a stopwatch. Every variable in this program is labelled correctly, and the checker accepts it.',
    labels: { h: 'H', i: 'H' },
    high: { h: [0, 1, 2, 3] },
    fixed: {},
    observer: 'timing',
    source: `// h : H on {0,1,2,3}        i : H        out : the public channel
i = 0;
while (i < h) {
  i = i + 1;
}
out(0);`,
    question: {
      prompt: 'The checker accepts. The batch and stream observers each learn 0 bits — every run emits the single value <code>0</code> and halts. What does the timing observer learn?',
      options: ['0 bits — the output is a constant', '1 bit', '2 bits — all of <code>h</code>', 'Nothing you can rely on; timing is noise'],
      answer: 2,
    },
    expect: { accepted: true, violations: 0, batchBits: 0, streamBits: 0, timingBits: 2 },
    fix: {
      title: 'The defensive mirror: pad the loop to a public bound',
      labels: { h: 'H', i: 'L', j: 'H' },
      source: `// i : L — a PUBLIC trip count        j : H — the secret-dependent work
i = 0;
j = 0;
while (i < 4) {
  if (i < h) {
    j = j + 1;
  } else {
    j = j + 0;     // same cost on both sides of the branch
  }
  i = i + 1;
}
out(0);`,
      note: 'Loop on a public bound; make both arms of the secret branch cost the same. The timing classes collapse to one — 0 bits under every observer — and the checker still accepts. You pay worst-case time on every run. That is the price, and it is usually worth it.',
      expect: { accepted: true, timingBits: 0 },
    },
    discussion: `
      <p>Every constraint holds: <code>i</code> is <code>H</code>, so writing it under an
      <code>H</code> program counter is fine, and <code>out(0)</code> emits a constant
      after the <code>pc</code> has dropped back to <code>L</code>. Denning's rules
      govern flows through <em>program variables</em>; the clock is not a program
      variable, so the model never sees it. The run takes <code>2h + 3</code> ticks, and
      the observer just reads <code>h</code> off the stopwatch.</p>
      <p>This is Lampson's confinement problem, and it is why noninterference is stated
      over <em>all</em> observable behaviour rather than over the store. The right
      question about a covert channel is never "can it leak" but
      <strong>"what is its bandwidth"</strong> — a one-bit-per-hour channel and a
      one-megabit-per-second channel call for entirely different responses.</p>
      <p class="teach">Recall from lecture: seL4's functional-correctness proof, and even
      the 2013 noninterference proof layered on top of it, explicitly exclude timing
      channels. Verification does not make this go away; it makes the exclusion
      <em>explicit</em>, which is the honest version.</p>`,
  },

  {
    id: 'c2',
    mode: 'timing',
    title: 'An early-exit PIN check',
    threat: 'A 3-digit PIN, each digit in {0,1,2,3} — 64 possibilities, 6 bits. The intended policy is a <strong>declassification of exactly one bit</strong>: the attacker may learn whether their guess is right. They submit guesses and time the response.',
    labels: { secret: 'H', guess: 'L', i: 'H', eq: 'H' },
    high: { secret: (() => { const d = []; for (let a = 0; a < 4; a++) for (let b = 0; b < 4; b++) for (let c = 0; c < 4; c++) d.push(a * 100 + b * 10 + c); return d; })() },
    fixed: { guess: 0 },
    lowControl: {
      name: 'guess',
      label: 'attacker&rsquo;s guess',
      options: [
        { value: 0, text: '000' },
        { value: 1, text: '001' },
        { value: 10, text: '010' },
        { value: 100, text: '100' },
        { value: 123, text: '123' },
        { value: 333, text: '333' },
      ],
    },
    observer: 'timing',
    source: `// secret : H — a 3-digit PIN, digits drawn from {0,1,2,3}
// guess  : L — the attacker's guess          i, eq : H
// digit(x, 0) is the ones place; the loop walks upward from there.
i  = 0;
eq = 1;
while (i < 3 && eq == 1) {
  if (digit(secret, i) == digit(guess, i)) {
    i = i + 1;
  } else {
    eq = 0;               // bail out early
  }
}
out(eq);`,
    question: {
      prompt: 'With <code>guess = 000</code>, the value channel releases the authorised 1 bit (min-entropy). How much does the timing observer get?',
      options: ['1 bit — the same authorised bit', '2 bits', '6 bits — the whole PIN, in one query', '0 bits — the loop always runs three times'],
      answer: 1,
    },
    expect: { accepted: false, violations: 1, batchBits: 1, streamBits: 1, timingBits: 2 },
    fix: {
      title: 'The defensive mirror: constant-time comparison',
      labels: { secret: 'H', guess: 'L', i: 'L', eq: 'H' },
      source: `// i : L — the trip count no longer depends on the secret
i  = 0;
eq = 1;
while (i < 3) {
  if (digit(secret, i) == digit(guess, i)) {
    eq = eq + 0;          // both arms: one assignment, one tick
  } else {
    eq = 0;
  }
  i = i + 1;
}
out(eq);`,
      note: 'No early exit, both arms equal cost. Timing leakage drops from 2 bits to 1 — exactly the bit the declassification policy authorised, and not one bit more. The checker still flags out(eq): that flag is the declassifier, and it is the single point you audit.',
      expect: { accepted: false, timingBits: 1 },
    },
    discussion: `
      <p>The one violated constraint — <code>out(eq)</code> needs <code>H ≤ L</code> — is
      not a bug. It is the <strong>declassifier</strong>, the deliberate downgrade every
      password checker must contain, and the checker's job here is to make sure there is
      exactly one of them and that you can point at it. That is the whole design
      discipline: no flow by default, a leak only through a named, audited release point.</p>
      <p>The problem is that the clock releases more than the policy did. The running time
      is <code>3k + 7</code>, where <code>k</code> is the number of matching low-order
      digits — so a single query returns not "wrong" but "wrong, and the first
      <code>k</code> digits were right". In Sabelfeld–Sands terms, the
      <strong>what</strong> axis has been violated by a channel the policy never named.</p>
      <p><strong>Now do the attack arithmetic, because the bit count understates it.</strong>
      Blind search over 64 PINs costs 32 guesses on average. With the clock, you fix the
      ones digit in at most 4 guesses, then the tens digit in at most 4 more, then the
      hundreds: <strong>12 queries, worst case</strong>, and the search is linear in the
      PIN length instead of exponential. Scale it up to a real 16-byte MAC comparison and
      the same argument turns <code>2^128</code> into <code>16 × 256 = 4096</code>.
      That is why <code>hmac.compare_digest</code> and friends exist, and why "we compare
      the tokens with <code>==</code>" is a finding.</p>
      <p>Change the guess in the control above and watch the partition move: the timing
      classes are always "how far did you get", never "what is the secret" — which is why
      the attack has to be <em>adaptive</em>. One query is worth ~2 bits; the sequence is
      worth the key.</p>`,
  },
];

export const MODES = [
  {
    id: 'batch',
    name: 'Batch',
    tagline: 'input → output, observed once at the end',
    blurb: 'The program runs to completion and the observer reads what it printed. This is the model Denning\'s type system is sound for — and the three programs here show it agreeing with reality, catching a leak no dataflow analysis would, and then telling you far less than you wanted to know.',
  },
  {
    id: 'stream',
    name: 'Streams',
    tagline: 'the observer is watching the pipe',
    blurb: 'Now the observer sees each value as it is emitted, and sees the silence after the last one. Two runs can print the same values and still be distinguishable — by order, by prefix, or by stopping. Batch-mode soundness does not survive the move.',
  },
  {
    id: 'timing',
    name: 'Timing',
    tagline: 'the observer owns a stopwatch',
    blurb: 'Same values, same order, same termination — different durations. Nothing in the lattice model mentions a clock, so a program can satisfy every constraint the checker knows how to state and still hand over the secret.',
  },
];
