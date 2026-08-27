<!-- title: CIS400 — Foundations of Security -->
<!--
  ============================================================================
  HOW TO EDIT THIS DECK   (Week 1 — Foundations of Security)
  FOLDER: slides/02-security-foundations
  ============================================================================
  Rebuild after any edit:  node slides-infra/build.mjs slides/02-security-foundations
  Slide syntax:  a lone "---" line = new horizontal slide, "--" = vertical
  sub-slide, "Note:" begins speaker notes (press "s" in the deck).

  Reusable CSS (slides-infra/css/theme.css):
    .slide classes: title-slide, section-divider, big-point
    <p class="source">Source: ...</p>   on-slide citation line (required on
                                          every figure / named result / theorem)
    .callout threat | defense | note | good
    .two-col with .col-left / .col-right
    .stat / .stat-label   big-figure block

  MATH: LaTeX between $ ... $ (inline) or $$ ... $$ (display); KaTeX renders it
  and skips code and pre elements, so $ inside code fences is safe. Use letter macros
  (\frac \sqrt \sum \sqcup \sqcap \le \mathrm \forall). Two rendering hazards,
  both avoided throughout this deck: (1) do NOT use a backslash-space spacing
  macro — write \quad, not the comma/semicolon spacing macros; (2) multi-row
  display math with a double-backslash row break is fragile through the
  markdown pass, so multi-line derivations are written as separate $$ blocks.
  Never put a literal pipe inside $...$ inside a markdown table.

  SOURCING RULE: every quantitative claim and every named theorem/model carries
  an on-slide <p class="source"> line, verified against the primary source. The
  seL4 figures in 08 are the SOSP 2009 numbers (8,700 LoC C, 600 LoC asm,
  ~200k lines Isabelle, ~20 person-years). A slide marked "EDIT: verify" flags
  a nuance to confirm before lecturing (e.g. the exact complexity class of the
  mono-operational HRU safety problem).

  GUARDRAIL: this deck teaches models, math, and mechanisms only. No working
  exploits. INSTRUCTOR TODO markers point demos to the authorized sandbox.

  HTML-COMMENT RULE: a comment cannot contain another comment-open or
  comment-close inside it. This header contains none; keep it that way.
  ============================================================================
-->
<!-- .slide: class="title-slide" -->
<span class="course-tag">CIS 400 / 600 &bull; Syracuse University &bull; Fall 2026</span>

# Foundations of Security

Prof. Kristopher Micinski

<div class="footer">cis400 &bull; week 1 &bull; foundations</div>

Note:
This foundations lecture is deliberately not AI-specific. That is
intentional. The attacks we will study this semester — prompt injection, jailbreaks,
agent escapes — reuse failures that systems security has had names for
for decades. Today we build the machinery: a formal reading of CIA,
the access-control matrix and the HRU safety result, lattice information flow,
Bell-LaPadula and Biba, noninterference, the reference monitor, Saltzer--Schroeder,
threat modeling, and what a proof like seL4 does and does not buy.

The through-line, which we return to in week 11: many vulnerabilities are
failures to keep attacker-controlled data out of the system's control channel.
Buffer overflow, SQL injection, prompt injection — same pattern, different nouns.

Housekeeping: the reading for today is Anderson, Security Engineering, Chapter 1.
Thursday is a discussion day. Collect the "AI-security news story you are
skeptical of" items from the intro homework and park them on the board; tell
the class we will come back to them once we have the vocabulary to analyze them.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 1</span>

# What security means

## How do we define security rigorously?

---

## Correctness and security are different quantifiers

Fix a system as a function `f` from inputs to behaviors, and a specification `φ`.

**Correctness** — for the inputs you *expect*:
<span class="ktx" data-d="1" data-tex="IFxmb3JhbGwgeCBcaW4gRF97XG1hdGhybXt0ZXN0fX0uIFxxdWFkIFx2YXJwaGkoeCwgZih4KSkg"></span>

**Security** — for the inputs an *adversary chooses*:
<span class="ktx" data-d="1" data-tex="IFxmb3JhbGwgeCBcaW4gRF97XG1hdGhybXthbGx9fS4gXHF1YWQgXHZhcnBoaSh4LCBmKHgpKSwgXHFxdWFkIERfe1xtYXRocm17dGVzdH19IFxzdWJzZXRuZXEgRF97XG1hdGhybXthbGx9fSA="></span>

The adversary's power is exactly the gap <span class="ktx" data-tex="RF97XG1hdGhybXthbGx9fSBcc2V0bWludXMgRF97XG1hdGhybXt0ZXN0fX0="></span>: inputs no honest user would ever produce.

Note:
State this as a change in the quantifier domain. Correctness quantifies over a test distribution;
security quantifies over everything, chosen adversarially. Every attack this
term lives in that set difference. We will reuse the same distinction for ML systems: training fixes one
distribution, while deployment gives an adversary room to induce another. Keep the phrase "the attacker moves second"; Thursday's discussion paper is
built on it.

---

## CIA, said precisely

*Confidentiality, Integrity, Availability.*

Split every input and output into **high** (secret / privileged) and **low**
(public / attacker-visible).

- **Confidentiality** — what the attacker sees does not depend on the secrets.
  Vary a high input, and the low output is unchanged.
- **Integrity** — the dual: untrusted (low) input must not determine trusted
  (high) state.
- **Availability** — a *liveness* property: every request is answered within a
  bound. Different in kind from C and I, which are "nothing bad happens."

<p class="source">Framing after Goguen &amp; Meseguer, IEEE S&amp;P, 1982; Anderson, Security Engineering, Ch. 1, 3rd ed., 2020.</p>

Note:
CIA is usually taught as a mnemonic. Here I want it to be a set of predicates you can check against a model. Confidentiality is the
statement that varying the secret does not vary what the attacker sees — that is
noninterference, which we make fully formal in Part 5. Integrity is its dual:
untrusted input must not determine trusted state. Availability is different in
kind — it is a liveness property, "something good eventually happens," whereas
C and I are about "nothing bad happens." That distinction matters: liveness and
safety need different proof techniques, and DoS defenses look nothing like
confidentiality defenses for exactly this reason.

---

## Policy versus mechanism

**Policy** — *what* is allowed. Example: "no execution lets a student read
`grades.db`."

**Mechanism** — *how* it is enforced: file permissions, a cipher, a type system.

A mechanism is **sound** if it allows only what the policy permits (the security
direction), and **permissive enough** if it doesn't block legitimate use (the
usability direction). Most failures are not broken mechanisms. They are
correct mechanisms enforcing the wrong policy.

Anderson's frame: a secure system is the product of four things.

1. **Policy** — what you are trying to achieve.
2. **Mechanism** — ciphers, access controls, hardware, filters.
3. **Assurance** — how much you can *rely* on each mechanism (Part 8).
4. **Incentives** — who bears the loss when it fails.

<p class="source">Source: Anderson, Security Engineering, Ch. 1, 3rd ed., 2020.</p>

Note:
Separate policy from mechanism; do not let the examples blur them together. Soundness
is the security direction (allow only what the policy permits); permissiveness is
the usability direction, and over-tight mechanisms get turned off by frustrated
users (Part 6, psychological acceptability). The important failure mode: most failures
are a mechanism soundly enforcing the wrong policy — a proof shows the mechanism
matches the spec, never that the spec was the policy you wanted. Then use Anderson's
four-part frame and emphasize the incentives question: who eats the loss when a
system fails? The Chapter 1 ATM cases were mostly not broken crypto — banks
assumed the mechanism was perfect, so customers ate the losses, so banks had no
incentive to fix real flaws. Apply the same analysis to AI vendors: who eats the loss
when an agent is injected, and what does that predict about how fast real
defenses ship? That structures our policy discussions in week 13.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 2</span>

# Access control

## Subjects, objects, rights

---

## The access-control matrix

Authorization is built from three finite sets:

- **subjects** <span class="ktx" data-tex="Uw=="></span> — the actors (users, processes)
- **objects** <span class="ktx" data-tex="Tw=="></span> — the things acted on (files, devices)
- **rights** <span class="ktx" data-tex="Ug=="></span> — what an actor may do (`read`, `write`, `own`, `execute`)

The **access control matrix** <span class="ktx" data-tex="TSA6IFMgXHRpbWVzIE8gXHRvIDJee1J9"></span> has cell <span class="ktx" data-tex="TVtzLG9d"></span> = the rights subject <span class="ktx" data-tex="cw=="></span> has on object <span class="ktx" data-tex="bw=="></span>:

| | `grades.db` | `payroll.db` | `ta_acct` |
|---|---|---|---|
| **prof** | read, write, own | — | — |
| **ta** | read | — | own |
| **student** | — | — | — |

<p class="source">Source: Lampson, "Protection," 1971; Graham &amp; Denning, 1972.</p>

Note:
Lampson's matrix gives us a crisp, checkable model of authorization: discrete subjects, discrete objects, an explicit relation. Keep that crispness in mind — an LLM context window has no subjects and objects inside
it at all, just one undifferentiated string, and much of the week-11 defensive
research is people trying to bolt this matrix back on from the outside. Point out the diagonal-ish cell: `prof` owns `grades.db`, and `own` is the meta-right that lets
a subject change the matrix itself. That matters for what follows — a protection system is a matrix plus rules that rewrite the matrix.

---

## Two ways to store the matrix: ACLs and capabilities

The matrix is sparse. Store it **by column** or **by row**.

<div class="two-col">
<div class="col-left">

**ACL** (column, per object)
`grades.db → {prof: rw, ta: r}`
- Object answers "who can access me?"
- Easy to review per object, revoke per object
- Examples: Unix mode bits, Windows ACLs, S3 policies

</div>
<div class="col-right">

**Capability** (row, per subject)
`ta → {grades.db: r, ta_acct: own}`
- Subject holds unforgeable tokens
- Easy to delegate; access = *possession*
- Examples: fds, OAuth tokens, object-capability systems

</div>
</div>

<div class="callout threat"><strong>The confused deputy.</strong> A capability is
authority detached from identity. A privileged program invoked by an attacker
uses <em>its own</em> authority on the attacker's behalf — the deputy is confused
about <em>whose</em> request it is serving. An LLM agent holding your API tokens is a clean confused-deputy example.</div>

<p class="source">Source: Hardy, The Confused Deputy, ACM SIGOPS OSR 22(4), 1988.</p>

Note:
The ACL-vs-capability choice looks like an implementation detail, but it is a
real design choice. ACLs bind rights to identity checked at the moment of access;
capabilities bind rights to possession of a token; delegation becomes easy and
revocation becomes harder. Introduce Hardy's confused-deputy paper here: a
compiler with a capability to write anywhere, asked by a user to write output to
a billing file it happens to have access to, does it — using its authority, not
the user's. Replace "compiler" with "agent," "billing file" with "your inbox,"
and "user" with "a web page the agent read," and you have indirect prompt
injection. We will reuse this slide in week 11.

---

## Some policies are too expressive to analyze

The matrix isn't static: real systems have rules that rewrite it (`chmod`,
transferring ownership, spawning a process). So the useful question is not "is the
current matrix okay?" — that's easy to check — it's the **safety problem**:

> starting from here, can any sequence of allowed operations ever hand right
> `r` to someone who shouldn't have it?

**HRU (1976): in general, this is undecidable.** Because those rewrite rules are
expressive enough to simulate an arbitrary computation, deciding whether a right
can ever leak is as hard as deciding whether a program halts — which is undecidable.

<div class="callout note">Access control is not broken; the policy language can simply become too
expressive to analyze. That is the recurring tradeoff: expressiveness
is paid for in analyzability. A system prompt written in English sits at the far
end of it — able to express any policy, and giving you almost no proof obligations you can actually discharge.</div>

<p class="source">Source: Harrison, Ruzzo &amp; Ullman, CACM 19(8), 1976.</p>

Note:
State the safety problem carefully: not "is the current matrix fine" (trivial) but "over the
tree of reachable future states the rewrite rules generate, can this right ever escape into
a cell it shouldn't reach." HRU's result is one of the central impossibility results in security: the rewrite rules are Turing-complete, so asking whether a
right ever appears is the halting problem in disguise. I am not going to walk through the Turing-machine reduction at the board — the takeaway matters more than the encoding. The takeaway: analyzability usually costs expressiveness, and LLM "policies" written in English are the
maximally expressive, minimally analyzable end of that trade.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 2a</span>

# Lattices

## Partial orders, joins, and meets

Note:
This is a short math interlude. The next three parts — information flow,
the Bell-LaPadula and Biba models, and every taint or type-label system later in
the course — all sit on one algebraic object: the lattice. Ten minutes here will pay off repeatedly, so define it cleanly now instead of hand-waving when Denning requires a lattice on the next slide.

---

## Partial orders

A **partial order** <span class="ktx" data-tex="XGxl"></span> on a set <span class="ktx" data-tex="TA=="></span> is a relation that is

- **reflexive:** <span class="ktx" data-tex="YSBcbGUgYQ=="></span>;
- **antisymmetric:** <span class="ktx" data-tex="YSBcbGUgYg=="></span> and <span class="ktx" data-tex="YiBcbGUgYQ=="></span> imply <span class="ktx" data-tex="YSA9IGI="></span>;
- **transitive:** <span class="ktx" data-tex="YSBcbGUgYg=="></span> and <span class="ktx" data-tex="YiBcbGUgYw=="></span> imply <span class="ktx" data-tex="YSBcbGUgYw=="></span>.

The pair <span class="ktx" data-tex="KEwsIFxsZSk="></span> is a **poset**. "Partial" is the key word: two elements can be
**incomparable** — neither <span class="ktx" data-tex="YSBcbGUgYg=="></span> nor <span class="ktx" data-tex="YiBcbGUgYQ=="></span>.

- A **chain** is a subset in which every pair is comparable (a total order).
- An **antichain** is a set of pairwise-incomparable elements.
- The running example is the **powerset** <span class="ktx" data-tex="KDJee1h9LCBcc3Vic2V0ZXEp"></span>: subsets ordered by
  inclusion. <span class="ktx" data-tex="XHthXH0="></span> and <span class="ktx" data-tex="XHtiXH0="></span> are incomparable — the reason security needs more
  than a single ranking.

<!-- FIGURE: Hasse diagram of the powerset of {a,b,c} — the cube, bottom = {}, top = {a,b,c}, with {a},{b},{c} as an antichain on the lower level. -->

Note:
Reflexive, antisymmetric, transitive — the same three properties as "less than or
equal to" on numbers, minus totality. Dropping totality is the key move:
numbers are a chain, but security clearances are not, because two SECRET items in
different compartments are genuinely incomparable. Draw a Hasse diagram on the board: nodes are
elements, an upward edge joins each element to those that cover it (the immediate
successors), and transitivity is read off by following edges up. No arrowheads, no
transitive edges drawn — that economy is what makes Hasse diagrams useful.

---

## Joins, meets, and lattices

For elements <span class="ktx" data-tex="YSwgYg=="></span>: an **upper bound** is any <span class="ktx" data-tex="dQ=="></span> with <span class="ktx" data-tex="YSBcbGUgdQ=="></span> and <span class="ktx" data-tex="YiBcbGUgdQ=="></span>.

- The **join** <span class="ktx" data-tex="YSBcc3FjdXAgYg=="></span> is the *least* upper bound, when a unique one exists.
- The **meet** <span class="ktx" data-tex="YSBcc3FjYXAgYg=="></span> is the *greatest* lower bound, dually.

A **lattice** is a poset in which **every pair** has both a join and a meet.

- **Bounded:** there is a top <span class="ktx" data-tex="XHRvcA=="></span> (above all) and bottom <span class="ktx" data-tex="XGJvdA=="></span> (below all).
- **Complete:** *every* subset <span class="ktx" data-tex="UyBcc3Vic2V0ZXEgTA=="></span> — not just pairs — has a join
  <span class="ktx" data-tex="XGJpZ3NxY3VwIFM="></span> and meet. Every finite bounded lattice is complete.

<span class="ktx" data-d="1" data-tex="KDJee1h9LCBcc3Vic2V0ZXEpOiBccXVhZCBBIFxzcWN1cCBCID0gQSBcY3VwIEIsIFxxdWFkIEEgXHNxY2FwIEIgPSBBIFxjYXAgQiwKXHF1YWQgXHRvcCA9IFgsIFxxdWFkIFxib3QgPSBcdmFybm90aGluZy4="></span>

<div class="callout note">Not every poset is a lattice. If a poset contains
<span class="ktx" data-tex="XHthXH0="></span> and <span class="ktx" data-tex="XHtiXH0="></span> but omits <span class="ktx" data-tex="XHthLGJcfQ=="></span>, the two have upper bounds but no
<em>least</em> one — the join is undefined. The lattice axiom is exactly the
guarantee that a unique least combination <strong>always exists</strong>.</div>

Note:
Join is least-upper-bound, meet is greatest-lower-bound. The powerset makes both
concrete: the least set containing both <span class="ktx" data-tex="QQ=="></span> and <span class="ktx" data-tex="Qg=="></span> is their union; the greatest
set inside both is their intersection; the top is the full ground set and the
bottom is empty. Emphasize the failure case in the callout — a poset with a gap where
the least upper bound should be is not a lattice — because it is what the lattice requirement rules out, and it is why Denning insists on it on the next
slide. Complete versus merely-lattice matters only for infinite label sets; for
the finite label sets we use, bounded already gives complete.

---

## Hasse diagrams: how to draw an order

A Hasse diagram draws only the **covering** relation: an edge from <span class="ktx" data-tex="YQ=="></span> up to <span class="ktx" data-tex="Yg=="></span>
when <span class="ktx" data-tex="YSA8IGI="></span> with nothing strictly in between. Everything else you read off by
walking upward.

No arrowheads — up *is* the direction. No self-loops for <span class="ktx" data-tex="YSBcbGUgYQ=="></span>, and no edge
for anything transitivity already gives you. That economy is the point:
what is drawn is exactly the information you cannot derive.

The smallest security lattice has two elements.

<svg viewBox="0 0 300 248" width="100%" style="max-width:380px;height:auto;display:block;margin:0.4em auto" role="img" aria-label="Hasse diagram of the two-element lattice with Public below Secret">
  <line x1="110" y1="60" x2="110" y2="190" stroke="#b8c0cc" stroke-width="2.5"/>
  <circle cx="110" cy="60" r="9" fill="#26346b"/>
  <circle cx="110" cy="190" r="9" fill="#26346b"/>
  <text x="136" y="68" font-size="25" fill="#26346b" font-weight="600">Secret</text>
  <text x="136" y="198" font-size="25" fill="#26346b" font-weight="600">Public</text>
  <text x="86" y="68" font-size="21" fill="#9aa3b3" text-anchor="end">&#8868;</text>
  <text x="86" y="198" font-size="21" fill="#9aa3b3" text-anchor="end">&#8869;</text>
  <text x="150" y="236" font-size="15" fill="#9aa3b3" text-anchor="middle">one edge: Public may flow to Secret</text>
</svg>

There is no edge downward, and that missing edge is the confidentiality policy.

Note:
Define covering carefully — students who have seen posets still draw transitive
edges. The two-element lattice is worth putting up even though it is trivial,
because it is the label set of every taint-tracking system in the course:
untrusted/trusted, tainted/clean, low/high. Point at the missing downward edge
and say that is the policy; everything else today is elaboration.

---

## Two compartments: the diamond

Take the powerset of <span class="ktx" data-tex="XHtcbWF0aHJte0hSfSwgXG1hdGhybXtMRUdBTH1cfQ=="></span> ordered by <span class="ktx" data-tex="XHN1YnNldGVx"></span>.

<svg viewBox="0 0 560 344" width="100%" style="max-width:470px;height:auto;display:block;margin:0.1em auto" role="img" aria-label="Hasse diagram of the diamond lattice on subsets of HR and LEGAL">
  <line x1="270" y1="278" x2="120" y2="168" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="270" y1="278" x2="420" y2="168" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="120" y1="168" x2="270" y2="58" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="420" y1="168" x2="270" y2="58" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="146" y1="168" x2="394" y2="168" stroke="#ccd3dd" stroke-width="1.5" stroke-dasharray="5 7"/>
  <circle cx="270" cy="58" r="9" fill="#F76900"/>
  <circle cx="120" cy="168" r="9" fill="#26346b"/>
  <circle cx="420" cy="168" r="9" fill="#26346b"/>
  <circle cx="270" cy="278" r="9" fill="#F76900"/>
  <text x="270" y="36" font-size="23" fill="#26346b" font-weight="600" text-anchor="middle">{HR, LEGAL}</text>
  <text x="98" y="176" font-size="23" fill="#26346b" font-weight="600" text-anchor="end">{HR}</text>
  <text x="442" y="176" font-size="23" fill="#26346b" font-weight="600" text-anchor="start">{LEGAL}</text>
  <text x="270" y="310" font-size="23" fill="#26346b" font-weight="600" text-anchor="middle">&#8709;</text>
  <text x="270" y="15" font-size="15" fill="#c25200" text-anchor="middle">join &#8852;</text>
  <text x="270" y="334" font-size="15" fill="#c25200" text-anchor="middle">meet &#8851;</text>
  <text x="270" y="158" font-size="14" fill="#9aa3b3" text-anchor="middle">not an edge &#8212; no path either way</text>
</svg>

<span class="ktx" data-tex="XHtcbWF0aHJte0hSfVx9"></span> and <span class="ktx" data-tex="XHtcbWF0aHJte0xFR0FMfVx9"></span> are **incomparable** — clearance for
one says nothing about the other:
<span class="ktx" data-d="1" data-tex="XHtcbWF0aHJte0hSfVx9IFxzcWN1cCBce1xtYXRocm17TEVHQUx9XH0gPSBce1xtYXRocm17SFJ9LFxtYXRocm17TEVHQUx9XH0sClxxcXVhZCBce1xtYXRocm17SFJ9XH0gXHNxY2FwIFx7XG1hdGhybXtMRUdBTH1cfSA9IFx2YXJub3RoaW5n"></span>

Delete the top node and it stops being a lattice: the singletons lose their upper
bound, so combined HR+LEGAL data could not be labelled at all.

Note:
This is the smallest diagram that shows why security needs more than a ranking.
Ask the class directly: is {HR} more or less secret than {LEGAL}? Neither — the
question is malformed, and that is the content of "partial". The dashed line is
not an edge; it is there to be pointed at and called *not* an edge. The deletion
argument at the bottom is the one to dwell on, because it is exactly the
condition Denning needs on the next part: combined data must always have a
label, which forces the join to exist.

---

## Levels &times; compartments: the product

Cross the two-level chain <span class="ktx" data-tex="XG1hdGhybXtVfSBcbGUgXG1hdGhybXtTfQ=="></span> with the compartment
diamond. Each node is a pair <span class="ktx" data-tex="KGMsIEsp"></span> — a **level** <span class="ktx" data-tex="Yw=="></span> and a **set** <span class="ktx" data-tex="Sw=="></span> of
compartments drawn from <span class="ktx" data-tex="XHtcbWF0aHJte0hSfSwgXG1hdGhybXtMRUdBTH1cfQ=="></span>.

<svg viewBox="0 0 680 500" width="100%" style="max-width:640px;height:auto;display:block;margin:0.2em auto" role="img" aria-label="Hasse diagram of the cube: the two-level chain U below S crossed with the diamond of compartment sets over HR and LEGAL">
  <line x1="340" y1="440" x2="150" y2="320" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="340" y1="440" x2="530" y2="320" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="150" y1="320" x2="340" y2="180" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="530" y1="320" x2="340" y2="180" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="340" y1="320" x2="150" y2="180" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="340" y1="320" x2="530" y2="180" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="150" y1="180" x2="340" y2="60" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="530" y1="180" x2="340" y2="60" stroke="#b8c0cc" stroke-width="2.5"/>
  <line x1="340" y1="440" x2="340" y2="320" stroke="#F76900" stroke-width="2.5"/>
  <line x1="150" y1="320" x2="150" y2="180" stroke="#F76900" stroke-width="2.5"/>
  <line x1="530" y1="320" x2="530" y2="180" stroke="#F76900" stroke-width="2.5"/>
  <line x1="340" y1="180" x2="340" y2="60" stroke="#F76900" stroke-width="2.5"/>
  <circle cx="340" cy="440" r="8.5" fill="#F76900"/>
  <circle cx="150" cy="320" r="8.5" fill="#26346b"/>
  <circle cx="340" cy="320" r="8.5" fill="#26346b"/>
  <circle cx="530" cy="320" r="8.5" fill="#26346b"/>
  <circle cx="150" cy="180" r="8.5" fill="#26346b"/>
  <circle cx="340" cy="180" r="8.5" fill="#26346b"/>
  <circle cx="530" cy="180" r="8.5" fill="#26346b"/>
  <circle cx="340" cy="60" r="8.5" fill="#F76900"/>
  <text x="340" y="470" font-size="20" fill="#26346b" text-anchor="middle">(U, &#8709;)</text>
  <text x="138" y="326" font-size="20" fill="#26346b" text-anchor="end">(U, {H})</text>
  <text x="356" y="332" font-size="20" fill="#26346b" text-anchor="start">(S, &#8709;)</text>
  <text x="542" y="326" font-size="20" fill="#26346b" text-anchor="start">(U, {L})</text>
  <text x="138" y="186" font-size="20" fill="#26346b" text-anchor="end">(S, {H})</text>
  <text x="356" y="176" font-size="20" fill="#26346b" text-anchor="start">(U, {H,L})</text>
  <text x="542" y="186" font-size="20" fill="#26346b" text-anchor="start">(S, {L})</text>
  <text x="340" y="46" font-size="20" fill="#26346b" font-weight="700" text-anchor="middle">(S, {H,L})</text>
  <text x="24" y="430" font-size="14" fill="#9aa3b3" text-anchor="start">gray: add a compartment</text>
  <text x="24" y="452" font-size="14" fill="#c25200" text-anchor="start">orange: raise the level (U &#8594; S)</text>
  <text x="24" y="474" font-size="14" fill="#6b7280" text-anchor="start">H = HR&nbsp;&nbsp;&nbsp;L = LEGAL</text>
</svg>

Join and meet are **componentwise** — the compartment part is a *set*, joined by
union — which is why the product of two lattices is again a lattice:
<span class="ktx" data-d="1" data-tex="KGNfMSxLXzEpIFxzcWN1cCAoY18yLEtfMikgPSAoXG1heChjXzEsY18yKSxcIEtfMSBcY3VwIEtfMik="></span>

<span class="ktx" data-tex="KFxtYXRocm17U30sXHtcbWF0aHJte0hSfVx9KQ=="></span> and <span class="ktx" data-tex="KFxtYXRocm17U30sXHtcbWF0aHJte0xFR0FMfVx9KQ=="></span> sit at the
same height and are still **incomparable**: drawn height is not the order.

Note:
Eight nodes, twelve edges: the cube. Color-coding the two kinds of edge is why the picture is useful — every gray edge adds a compartment, every orange edge
raises the level, and a legal read walks only upward. Do the worked question out
loud: can someone cleared (S, {H}) read an object at (U, {H,L})? Level says yes,
compartments say no — dominance needs both, so no. That is need-to-know beating
clearance level, and it is the case students often get wrong. Call back to this
cube in Part 4 when Bell-LaPadula turns it into two rules.

---

## Why security is built on lattices

Read the order as a flow rule: security labels live in a lattice <span class="ktx" data-tex="KFNDLCBcbGUp"></span>, and
<span class="ktx" data-tex="YSBcbGUgYg=="></span> means **class <span class="ktx" data-tex="YQ=="></span> may flow to class <span class="ktx" data-tex="Yg=="></span>** — information at class <span class="ktx" data-tex="YQ=="></span> is
allowed to reach a container cleared for <span class="ktx" data-tex="Yg=="></span>.

Combine data of classes <span class="ktx" data-tex="cA=="></span> and <span class="ktx" data-tex="cQ=="></span> and the result must get **one** label — the
**join** <span class="ktx" data-tex="cCBcc3FjdXAgcQ=="></span>, the least class that dominates both. A computation
<span class="ktx" data-tex="dCA9IGYoYV8xLCBcZG90cywgYV9uKQ=="></span> is legal exactly when

<span class="ktx" data-d="1" data-tex="XHVuZGVybGluZXthXzF9IFxzcWN1cCBcY2RvdHMgXHNxY3VwIFx1bmRlcmxpbmV7YV9ufSBcIFxsZVwgXHVuZGVybGluZXt0fS4="></span>

Worked: <span class="ktx" data-tex="XCBcbWF0aHJte1NFQ1JFVH0gXHNxY3VwIFxtYXRocm17Q09ORklERU5USUFMfSA9IFxtYXRocm17U0VDUkVUfQ=="></span>, and in
the compartment lattice <span class="ktx" data-tex="XCBce1x0ZXh0e0hSfVx9IFxzcWN1cCBce1x0ZXh0e0xFR0FMfVx9ID0gXHtcdGV4dHtIUn0sIFx0ZXh0e0xFR0FMfVx9"></span>.

<p class="source">Sources: Birkhoff, <em>Lattice Theory</em>, AMS, 1940; Denning, A Lattice Model of Secure Information Flow, CACM 19(5), 1976.</p>

Note:
This slide answers "why lattices?", and the answer is the join. Whenever a
program mixes two inputs, the output has to be assigned a single class, and it
must be the *least* class at least as high as both — anything lower would leak,
anything higher over-classifies and breaks usability. For "least upper bound" to
exist and be unique for every pair, the label set must be a lattice; that is not notation for its own sake, it is forced by the requirement that combined data always has a
well-defined class. Once students see that the join is doing the work, the information-flow section, and later taint tracking in the agent-security weeks,
reads as the same idea applied in different settings.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 3</span>

# Information flow

## Labels that move with the data

---

## Denning's lattice model

Access control guards *containers*. Information flow guards the *information* as
it moves. A flow model is
<span class="ktx" data-d="1" data-tex="IEZNID0gXGxhbmdsZSBOLFwgUCxcIFNDLFwgXHNxY3VwLFwgXHJpZ2h0YXJyb3cgXHJhbmdsZSA="></span>

- <span class="ktx" data-tex="Tg=="></span> — **objects**: the passive containers that *hold* information — variables,
  files, buffers, table columns. Each object <span class="ktx" data-tex="YQ=="></span> carries a class
  <span class="ktx" data-tex="XHVuZGVybGluZXthfSBcaW4gU0M="></span>.
- <span class="ktx" data-tex="UA=="></span> — **processes**: the active agents that *run* and move information between
  objects — a running program, a thread, a database query.
- <span class="ktx" data-tex="U0M="></span> — the **security classes** (the labels themselves); <span class="ktx" data-tex="XHNxY3Vw"></span> combines two
  classes; <span class="ktx" data-tex="XHJpZ2h0YXJyb3c="></span> is the "can-flow-to" relation on them.

A **flow** happens when a process reads some objects and writes a result: the
information moves from the source objects into the target, so the target's class
must dominate every source's.

**Central requirement:** <span class="ktx" data-tex="KFNDLCBccmlnaHRhcnJvdywgXHNxY3VwKQ=="></span> must form a **lattice**
(Part 2a): every pair of classes has a join <span class="ktx" data-tex="XHNxY3Vw"></span> and a meet <span class="ktx" data-tex="XHNxY2Fw"></span>, with a
bottom <span class="ktx" data-tex="XGJvdA=="></span> (public) and top <span class="ktx" data-tex="XHRvcA=="></span> (most secret). The <span class="ktx" data-tex="XHJpZ2h0YXJyb3c="></span> relation is
the lattice order, and <span class="ktx" data-tex="XHNxY3Vw"></span> is what a computation assigns when it combines two
classes.

<p class="source">Source: Denning, A Lattice Model of Secure Information Flow, CACM 19(5), 1976.</p>

Note:
Denning's 1976 paper is the pivot of the deck. Bell-LaPadula
labels files; Denning labels the information itself and tracks it through
computation. The lattice requirement is not cosmetic. You need a join
because when a computation combines two inputs of classes P and Q, the result
must get a single well-defined class — the least class that dominates both — and
for "least such class" to exist and be unique for every pair, the order must be a
lattice. This is the same shape as joins in type systems. Once you see it here,
you will recognize it in taint-tracking and IFC systems in the course.

---

## Denning's model on a small program

Two objects feed a process; the class of each **write** must satisfy
<span class="ktx" data-tex="XHJpZ2h0YXJyb3c="></span>. A computation <span class="ktx" data-tex="dCA9IGYoYV8xLFxkb3RzLGFfbik="></span> is legal exactly when

<span class="ktx" data-d="1" data-tex="IFx1bmRlcmxpbmV7YV8xfSBcc3FjdXAgXGNkb3RzIFxzcWN1cCBcdW5kZXJsaW5le2Ffbn0gXCBcbGVcIFx1bmRlcmxpbmV7dH0uIA=="></span>

<svg viewBox="0 0 660 320" width="100%" style="max-width:660px;height:auto;display:block;margin:0.2em auto" role="img" aria-label="A process p reads two SECRET objects; the write to a SECRET object is legal, the write to a PUBLIC object is an illegal downward flow">
  <defs>
    <marker id="ah-gray" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#9aa3b3"/></marker>
    <marker id="ah-green" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#1a7f37"/></marker>
    <marker id="ah-red" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#c0392b"/></marker>
  </defs>
  <rect x="18" y="48" width="150" height="52" rx="6" fill="#f4f6fa" stroke="#26346b" stroke-width="2"/>
  <text x="93" y="70" font-size="17" fill="#26346b" font-weight="700" text-anchor="middle">salary</text>
  <text x="93" y="90" font-size="14" fill="#26346b" text-anchor="middle">SECRET</text>
  <rect x="18" y="168" width="150" height="52" rx="6" fill="#f4f6fa" stroke="#26346b" stroke-width="2"/>
  <text x="93" y="190" font-size="17" fill="#26346b" font-weight="700" text-anchor="middle">bonus</text>
  <text x="93" y="210" font-size="14" fill="#26346b" text-anchor="middle">SECRET</text>
  <circle cx="338" cy="134" r="36" fill="#26346b"/>
  <text x="338" y="142" font-size="24" fill="#ffffff" font-weight="700" text-anchor="middle">p</text>
  <text x="338" y="192" font-size="13" fill="#6b7280" text-anchor="middle">process</text>
  <rect x="486" y="40" width="156" height="52" rx="6" fill="#eef7f0" stroke="#1a7f37" stroke-width="2.5"/>
  <text x="564" y="62" font-size="17" fill="#14532d" font-weight="700" text-anchor="middle">report</text>
  <text x="564" y="82" font-size="14" fill="#14532d" text-anchor="middle">SECRET</text>
  <rect x="486" y="212" width="156" height="52" rx="6" fill="#fbeded" stroke="#c0392b" stroke-width="2.5"/>
  <text x="564" y="234" font-size="17" fill="#7f1d1d" font-weight="700" text-anchor="middle">avg</text>
  <text x="564" y="254" font-size="14" fill="#7f1d1d" text-anchor="middle">PUBLIC</text>
  <line x1="168" y1="74" x2="300" y2="124" stroke="#9aa3b3" stroke-width="2.5" marker-end="url(#ah-gray)"/>
  <line x1="168" y1="194" x2="300" y2="146" stroke="#9aa3b3" stroke-width="2.5" marker-end="url(#ah-gray)"/>
  <line x1="372" y1="116" x2="486" y2="72" stroke="#1a7f37" stroke-width="2.5" marker-end="url(#ah-green)"/>
  <line x1="372" y1="154" x2="486" y2="228" stroke="#c0392b" stroke-width="2.5" marker-end="url(#ah-red)"/>
  <text x="564" y="108" font-size="12.5" fill="#1a7f37" text-anchor="middle">SECRET &#8804; SECRET &#10003;</text>
  <text x="564" y="280" font-size="12.5" fill="#c0392b" text-anchor="middle">SECRET &#8816; PUBLIC &#10007; (leak)</text>
</svg>

```python
report = salary + bonus   # SECRET ⊔ SECRET = SECRET,  SECRET ⊑ SECRET  → OK
avg    = salary           # would need SECRET ⊑ PUBLIC → fails: a leak
```

The write to `report` climbs the lattice; the write to `avg` runs *down* it —
what the code intends is irrelevant, only where the classes sit decides.

Note:
The smallest honest instance of the model. Both writes come from the same process
p reading the same SECRET data; what differs is the class of the target. Every
assignment emits a constraint join(sources) &le; target, and you type-check the
program against the lattice exactly as with ordinary types. Intent is irrelevant:
avg = salary is rejected whether or not the programmer meant to leak — the whole
point of an information-flow type system, and the same mechanism we later see
enforced dynamically as taint tracking.

---

## The model is too strict: sound, not complete

Here is a program the checker **rejects** as a leak. Is it *actually* a leak?

```python
leak = False                 # PUBLIC
if salary > 100000:          # branch on SECRET
    leak = True
else:
    leak = True
# checker: a PUBLIC variable is assigned under a SECRET branch
#          → requires  SECRET ⊑ PUBLIC  →  REJECTED
```

<p><button onclick="var d=document.getElementById('cw-ans');d.style.display=(d.style.display==='none'||!d.style.display)?'block':'none';" style="cursor:pointer;border:1px solid #bbb;border-radius:5px;background:#f6f5f0;padding:0.18em 0.7em;font-size:0.92em;">Reveal: is any secret actually leaking?</button></p>

<div id="cw-ans" style="display:none;">

<div class="callout good"><code>leak</code> is <code>True</code> on <em>every</em>
path — its value never depends on <code>salary</code>. A Low observer sees
<code>True</code> whether the salary is high or low, so <strong>no information
crosses</strong>. The program is safe; the checker rejected it anyway.</div>

<div class="callout note">Static information flow is <strong>sound but not
complete</strong>: to guarantee it never accepts a real leak, it must reject some
safe programs. It tracks <em>syntactic dependence</em>, not the information that
actually flows — and deciding the latter exactly is undecidable, so every
practical checker over-approximates. False positives are the price of soundness.</div>

</div>

<div class="callout note"><strong>Try it:</strong> the <a href="../../examples/03-information-flow/">Information Flow Challenge</a> &mdash; eight programs, three observers. Decide what a public observer learns, then watch each program run over its whole secret input space and check yourself against Denning's type checker.</div>

Note:
The counterpart to the previous slide: there we saw a program the checker
correctly rejects; here is one it rejects wrongly. Both branches write the same
constant, so the PUBLIC output is independent of the secret and nothing leaks —
yet the rule "no PUBLIC write under a SECRET branch" fires anyway, because the
analysis reasons about the *shape* of the program, not its semantics. Make the
soundness/completeness point explicit: an information-flow type system is designed
to never miss a real leak (sound), and it buys that guarantee by rejecting some
harmless programs (incomplete). You cannot have both and stay decidable, because
"does any information actually flow?" is undecidable in general. This is the same
sound-but-conservative trade-off students will meet again in taint tracking and in
every static analyzer.

---

## US classification: levels and compartments

This is not only a teaching model; this is close to US classification policy.

A class is a pair <span class="ktx" data-tex="KGMsIEsp"></span>: a **level** <span class="ktx" data-tex="Yw=="></span> from a chain of three,
<span class="ktx" data-d="1" data-tex="IFxtYXRocm17Q09ORklERU5USUFMfSA8IFxtYXRocm17U0VDUkVUfSA8IFxtYXRocm17VE9QXCBTRUNSRVR9IA=="></span>
and a set <span class="ktx" data-tex="Sw=="></span> of **compartments** — control systems dividing material into
need-to-know groups (TALENT KEYHOLE, HUMINT Control System, Special Intelligence).

You may read an object only if its class is **dominated** by your clearance:
<span class="ktx" data-d="1" data-tex="IChjXzEsIEtfMSkgXGxlIChjXzIsIEtfMikgXGlmZiBjXzEgXGxlIGNfMiBcIFx0ZXh0eyBhbmQgfVwgS18xIFxzdWJzZXRlcSBLXzIg"></span>

Both conditions. Top Secret clearance does not admit you to a compartment you
were never read into — need-to-know *is* set inclusion.

<p class="source">Executive Order 13526 &sect;1.2 and &sect;4.1(a) (2009); compartmented access, ICD 703.</p>

Note:
Unclassified is the bottom of this lattice, not a fourth level — worth saying.
This is the cube from Part 2a with real names on the nodes; say so explicitly.
Make the incomparability concrete because it is where the powerset lattice earns
its keep. Two SECRET items in different compartments are not ordered — you cannot
read one on the strength of clearance for the other. That is need-to-know, and it
is exactly the sub-lattice structure of set inclusion. The join of those two is
SECRET with both categories; the meet is SECRET with neither. Call back to the
product lattice drawn in Part 2a rather than redrawing it: the diamond, not the
chain, is what makes this a lattice rather than a total order. Compartments are
why real systems are lattices and not just stacked levels. Say plainly that the levels and compartment systems named here are real policy terms.

---

## The flow rules: explicit flows

A statement causes information to flow from its inputs to its target. It is
**secure** iff the class of every source flows-to the class of the target.

```python
# each assignment induces a flow constraint on the classes:
y = x                 # requires   x_  <=  y_
z = x + w             # requires   x_ ⊔ w_  <=  z_
out.write(z)          # requires   z_  <=  out_
```

The rule generalizes: for `t = f(a1, ..., an)`, secure iff
<span class="ktx" data-d="1" data-tex="IFx1bmRlcmxpbmV7YV8xfSBcc3FjdXAgXHVuZGVybGluZXthXzJ9IFxzcWN1cCBcY2RvdHMgXHNxY3VwIFx1bmRlcmxpbmV7YV9ufSBcIFxsZVwgXHVuZGVybGluZXt0fSA="></span>

These are **explicit** flows — data is literally copied. A compiler or type
system can check them statically by propagating labels and verifying each
inequality.

Note:
Explicit flow is the easy half and the join operator does all the work: the label
of a computed value is the join of the labels of everything that fed it, and the
assignment is legal only if the target is cleared at least that high. This is a
type system — Denning-style labels are types, the join is the least-upper-bound of
types, and the check is subtyping. If explicit flow were the whole story, IFC
would be a solved compiler problem. It is not, because of the next slide: you can
leak a secret without ever copying it.

---

## The flow rules: implicit flows

No secret is ever assigned to a public variable — and it leaks completely:

```python
def leak(secret_bit):        # secret_bit_ = HIGH
    public = 0               # public_ = LOW
    if secret_bit == 1:      # branch on a HIGH value
        public = 1           # assign a LOW variable...
    return public            # ...public now equals secret_bit
```

The value `1` is a public constant; `secret_bit` is never copied. Yet after the
call, `public == secret_bit`. The flow is through **control**, not data.

**The rule.** Every statement executed under a guard of class
<span class="ktx" data-tex="XHVuZGVybGluZXtlfQ=="></span> incurs an implicit flow: for each variable <span class="ktx" data-tex="dg=="></span> assigned in a
branch,
<span class="ktx" data-d="1" data-tex="IFx1bmRlcmxpbmV7ZX0gXCBcbGVcIFx1bmRlcmxpbmV7dn0g"></span>
The whole branch runs in a **program-counter label** raised to <span class="ktx" data-tex="XHVuZGVybGluZXtlfQ=="></span>.

<div class="callout threat">Tracking <em>copies</em> is easy. Tracking
<em>influence</em> is the hard part — and influence is all an LLM does: every
token in the context conditions every token it emits.</div>

Note:
This slide is where students usually see why IFC is not just ordinary dataflow. The variable
public is assigned only public constants, so a data-flow analysis sees nothing
wrong — and yet the observer learns the secret exactly. The leak is carried by
which branch executed, i.e. by control flow. Denning's fix is the pc-label: on
entering a branch guarded by a secret, raise a program-counter label to the
guard's class, and charge every assignment in the branch against it, so writing a
public variable under a secret guard is rejected. Flag two consequences.
First, this is why IFC is hard: you must reason about paths not taken. Second,
push it further — termination and timing are themselves implicit channels; a loop
that runs longer on secret=1 leaks through the clock even if no variable is
mislabeled. That crack is the covert channel, next slide, and it is one reason noninterference is stronger than any label-checker.

---

## Covert (side) channels

Denning's rules stop flows through *program variables*. Real machines have state
the model never named:

- **Timing** — a branch that runs longer on `secret == 1` signals through the clock.
- **Termination** — `while secret: pass` leaks one bit by halting or not.
- **Resource** — cache occupancy, lock contention, disk fullness, an exception raised or not.
- **Power / EM** — the hardware itself modulated by the secret.

A channel is **covert** when it uses a mechanism *not intended for communication*.
Its danger is a **bandwidth**: bits per second the sender can push.

<p class="source">Sources: Denning, CACM, 1976; Lampson, A Note on the Confinement Problem, CACM 16(10), 1973.</p>

Note:
Lampson's 1973 confinement note named this problem before Denning formalized the
positive side, and the pairing is the lesson: you can enforce every flow rule your
model contains and still leak, because the machine has channels your model did not
mention. Timing and termination are the ones students underrate — a program that
is perfectly label-clean at the variable level still leaks through how long it
runs. Bandwidth is the right way to argue about covert channels: not "can it
leak" but "how many bits per second," because a one-bit-per-hour channel and a
one-megabit channel demand different responses. Bookmark this. In Part 5 we meet
noninterference, which is defined precisely to close this gap by quantifying over
all observable behavior, timing included — and in Part 8 we see even seL4's proof
explicitly does not cover timing channels.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 4</span>

# Mandatory access control

## Bell-LaPadula and Biba: two rules, and a dual

---

## Bell-LaPadula: no read up, no write down

Bell and LaPadula (1973) turned a military classification policy into two rules
over a lattice of clearances. A subject has a clearance; every object has a class.

- **No read up.** You may read an object only if your clearance is at least its
  class — secrets don't reach the uncleared.
- **No write down.** You may write to an object only if its class is at least your
  current level — a cleared process can't copy a secret *downward*, even if it
  wants to.

<div class="callout note">No-write-down is the important one: it assumes the process
that read your secret might be a <strong>Trojan</strong> and forbids it from
writing anything lower — exactly how to think about an LLM that just ingested
untrusted content. And the lattice is <em>mandatory</em>: no discretionary grant
can override it. That's what the "mandatory" in MAC means.</div>

<p class="source">Source: Bell &amp; LaPadula, Secure Computer Systems (MITRE MTR-2547), 1973.</p>

Note:
No-read-up is the obvious rule; no-write-down is the important one, so spend your
time there. The star-property assumes the high subject may be running a Trojan —
it does not trust even a legitimately cleared process not to try to leak — and so
it forbids that process from writing anything to a lower level. That is a
a useful way to view modern agents: assume the thing that read your secret is
compromised, and constrain its outputs. Use it to think about an LLM
that has just ingested untrusted content. Also stress that MAC sits above DAC: the
lattice is mandatory, the matrix is discretionary, and no discretionary grant can
override the mandatory flow rule. That "mandatory on top of discretionary"
layering is the reason it is called mandatory access control.

---

## Biba: integrity is Bell-LaPadula with the order flipped

Confidentiality keeps secrets from flowing **down**. Integrity keeps trusted data
from being polluted by flows **up**. Same lattice, order flipped — now high means
*trustworthy*:

- **No read down.** A high-integrity subject must not read low-integrity data.
- **No write up.** A subject must not write to anything of higher integrity than
  itself.

<div class="callout threat"><strong>Biba, stated for this course.</strong>
An agent that reads a random web page into a trusted computation is a textbook
integrity violation — a high-integrity process reading low-integrity data
(no-read-down), which then steers high-integrity actions (writes). That is the integrity shape behind indirect prompt injection.</div>

<p class="source">Source: Biba, Integrity Considerations for Secure Computer Systems (MITRE MTR-3153), 1977.</p>

Note:
Biba is confidentiality's mathematical dual — flip the order on the lattice and
the two BLP rules become the two integrity rules. The rules read backwards from
intuition at first: no-read-down says a trusted process must not ingest untrusted
input, and no-write-up says untrusted code cannot modify trusted state. Make the callout explicit and reuse it in week 11, because it is the indirect-injection threat model in 1977 language. An agent
is a high-integrity subject — it holds your tokens and can take real actions. When
it pulls a web page or an email into its context, it is reading low-integrity data
into a high-integrity computation, violating simple-integrity, and then it acts on
that data, letting the low input drive high writes. Classical security has a name and a rule for this; many agent designs violate it
by construction.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 5</span>

# Noninterference

## The strongest confidentiality statement, and why access control is not it

---

## Noninterference: secrets you cannot observe

**Noninterference**: whatever the High (secret) side did, a Low (public) observer
**cannot tell** — the Low view is identical whether the secrets were there or not.
Let `h` be High and `l` be Low; run each program from `l = 0` and vary *only* the
secret:

| program | `h = 0` → `l` | `h = 5` → `l` | leaks? |
|---|---|---|---|
| `l := l + 1` | `1` | `1` | **no** — `l` never depends on `h` |
| `l := h` | `0` | `5` | yes — a *direct* flow |
| `if h > 0: l := 1 else: l := 0` | `0` | `1` | yes — an *implicit* flow |

A program **leaks** exactly when two runs that start with the *same* Low input end
with *different* Low output. That "two runs" phrasing is the whole definition.

Note:
Ground the idea in traces before the formalism. Fix the Low input, vary only High,
watch the Low output. Row one is secure — `l` ends at 1 regardless of `h`, so a Low
observer learns nothing. Row two is the textbook direct leak. Row three is the
implicit flow: no Low variable is ever assigned from `h`, yet the control path
depends on `h` and the Low result reveals its sign. Leave them with the punchline:
a leak is a statement about a *pair* of runs that agree on Low-in and disagree on
Low-out — which is exactly what the next slide makes formal.

---

## Noninterference, formally

Label each variable <span class="ktx" data-tex="XEdhbW1hIDogXG1hdGhybXtWYXJ9IFx0byBce0wsIEhcfQ=="></span>. Two states are
**low-equivalent** when they agree on every Low variable:
<span class="ktx" data-d="1" data-tex="IFxzaWdtYSBcYXBwcm94X0wgXHNpZ21hJyBcaWZmIFxmb3JhbGwgeC5cIFxHYW1tYSh4KSA9IEwgXFJpZ2h0YXJyb3cgXHNpZ21hKHgpID0gXHNpZ21hJyh4KS4g"></span>

Command <span class="ktx" data-tex="Yw=="></span> is **noninterfering** iff low-equivalent inputs yield low-equivalent
outputs:
<span class="ktx" data-d="1" data-tex="IFxzaWdtYSBcYXBwcm94X0wgXHNpZ21hJyBcIFx3ZWRnZVwgXGxhbmdsZSBjLFxzaWdtYVxyYW5nbGUgXERvd25hcnJvdyBcdGF1IFwgXHdlZGdlXCBcbGFuZ2xlIGMsXHNpZ21hJ1xyYW5nbGUgXERvd25hcnJvdyBcdGF1JyBcIFxpbXBsaWVzXCBcdGF1IFxhcHByb3hfTCBcdGF1Jy4g"></span>

It quantifies over **pairs** of runs — a *2-safety hyperproperty* — so no single-run
monitor can check it, and no finite test can establish it.

- **Termination-(in)sensitive** — is a run that diverges on High an observation? (`while h > 0: skip` leaks a bit if it is.)
- **Observational determinism** — the concurrency variant: from low-equivalent starts the Low *trace* is identical under *every* schedule.
- **Noninference** — a possibilistic cousin: every observable Low trace is consistent with High having supplied nothing at all.

<p class="source">Sources: Goguen &amp; Meseguer, IEEE S&amp;P, 1982; Sabelfeld &amp; Myers, IEEE JSAC 21(1), 2003.</p>

Note:
This is the definition to get exactly right. Low-equivalence is an equivalence
relation on states that ignores High; noninterference says the program sends
low-equivalent inputs to low-equivalent outputs — i.e. the Low output is a function
of the Low input alone. Stress the hyperproperty point: in Clarkson–Schneider terms
it is a 2-safety property, a property of pairs of executions, which is the deep
reason it is neither testable nor monitorable from one run. Then the variants —
termination sensitivity is whether nontermination is observable; observational
determinism lifts the definition from final states to whole traces and is the
standard concurrency notion; noninference is the possibilistic trace formulation.
Keep these on the board; they return for IFC type systems and the declassification
literature.

---

## Noninterference under concurrency

Sequential noninterference can hold for *each thread* yet **fail for their
composition** — scheduling turns into a channel.

```text
# l is Low, h is High; two threads share l, initially l = 0
Thread A:   if h > 0: sleep(10ms)     # delay depends on the secret
            l := 1
Thread B:   sleep(5ms)
            l := 2
# final l = whichever thread wrote last  →  depends on h through timing
```

- **Internal timing channel** — a High-dependent delay reorders Low writes; each thread is individually clean.
- **The scheduler is attack surface** — a program NI under one scheduler can leak under another, so the definition must quantify over the whole scheduler class.
- **Refinement paradox** — resolving nondeterminism can *break* possibilistic NI; **observational determinism** survives it, because the Low trace is fixed regardless of scheduling.
- **Probabilistic leaks** — with no deterministic channel at all, High can still *bias the distribution* of Low outcomes (probabilistic NI).

<div class="callout threat">Access control sees none of this. The printer-lock
contention leaks one bit with <em>zero</em> access-control violations — a timing
channel the matrix never modeled. NI forbids the influence; access control only
forbids the read.</div>

Note:
Concurrency is where noninterference gets genuinely hard and naive definitions fall
apart. Walk the two-thread example: A and B each only write a Low variable, nothing
reads High into Low, but A's delay depends on the secret, so the secret decides the
order of the writes and hence the final Low value. That is an internal timing
channel, and it is compositional poison — per-thread security does not compose. Two
consequences. First, the scheduler must be modeled as part of the adversary, since a
program secure under one scheduler can leak under another. Second, the standard fix
is observational determinism: require the Low trace to be a deterministic function
of the Low input, independent of scheduling — which is what makes it robust under
refinement, unlike possibilistic noninterference, which the refinement paradox
breaks. Close on the printer-lock example: contention leaked a bit with the matrix
perfectly enforced — the same lesson one layer up.

---

## Declassification and gradual release

Pure noninterference is often **too strong**: real systems must release
*something* derived from secrets — a password check reveals one bit, a query
returns a median. The usable version relaxes "no flow" to "no flow *except*
through explicit, trusted release points."

**Declassification** is that deliberate downgrade — a value's label lowered on
purpose. The design question is *what* may be released and *under what condition*;
the literature (Sabelfeld–Sands) organizes it along four axes:

- **what** — only this aggregate, never a raw record;
- **who** — only an authorized principal may trigger the release;
- **where** — the downgrade happens at one auditable point in the code;
- **when** — *gradual release*: an observer learns nothing until an authorized
  declassification event, and exactly the released quantity at it — never more,
  never earlier.

<div class="callout defense">Every declassifier is your entire confidentiality
attack surface: no flow by default, a leak only through a named, audited release
point. Shrink and watch that point the way you shrink and watch a TCB.</div>

<p class="source">Source: Sabelfeld &amp; Sands, Dimensions and Principles of Declassification, IEEE CSFW, 2005.</p>

Note:
Noninterference taken literally forbids a password checker, which must reveal the
one bit right-or-wrong; so every real system needs a way to release *some* function
of its secrets on purpose. That deliberate downgrade is declassification, and the
research contribution is realizing it has structure — what, who, where, when —
rather than being an ad-hoc escape hatch. Gradual release is the cleanest of the
temporal conditions: the attacker's knowledge is flat until an authorized event
and then steps up by exactly the released quantity, nothing more. The engineering
rule is the same one as the TCB — concentrate every downgrade into a small, audited
set of release points, because that set *is* your confidentiality attack surface.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 6</span>

# The reference monitor and design principles

## Where the policy is enforced, and the rules for building it

---

## The reference monitor

Every enforcement mechanism is measured against one ideal: the **reference
monitor**, an abstract component that mediates all access of subjects to objects.
Three requirements, all mandatory:

1. **Complete mediation** — invoked on *every* access; no path around it.
2. **Tamperproof** — the subjects it governs cannot modify it.
3. **Verifiable** — small and simple enough to be analyzed for correctness.

An **inline reference monitor (IRM)** is one common realization: the checks are
*woven into the program itself* — by a rewriter or compiler — rather than living
in a separate kernel, so mediation travels with the code. It only counts as a
reference monitor if those inlined checks stay unbypassable and tamperproof.

<p class="source">Source: Anderson (James P.), Computer Security Technology Planning Study, ESD-TR-73-51, 1972.</p>

Note:
The reference monitor comes from the 1972 Anderson report and it is the standard reference point for enforcement mechanisms against which every real one is graded. The three properties
are a diagnostic checklist, and the large share of real bypasses are
failures of property one: some path that reaches the object without passing the
check — a second interface, a debug hook, a cache, a TOCTOU race. Property three
is the subtle one, because it is what forces minimality: you can only verify what
is small, so completeness and tamperproofness must be concentrated into as little
code as possible. Foreshadow week 11: ask which of the three an LLM "safety
fine-tune" satisfies. It is not complete mediation — you can phrase around it. It
is not tamperproof against its own input. And it is not verifiable — it is a
tendency in billions of weights, not a checkable predicate. It fails all three.

---

## The trusted computing base

The **TCB** is the totality of hardware, firmware, and software whose correct
operation is *necessary and sufficient* for the security policy to hold.

- Everything in the TCB you must **trust**; everything outside you need not.
- A bug **inside** the TCB can break the policy. A bug **outside** cannot (if the TCB is doing its job).
- Therefore: **minimize the TCB.** Its size is the size of your attack surface for policy violations — and, per property 3, the limit on what you can verify.

<svg viewBox="0 0 640 300" width="100%" style="max-width:600px;height:auto;display:block;margin:0.3em auto" role="img" aria-label="A small trusted computing base nested inside a large untrusted shell">
  <rect x="30" y="28" width="580" height="244" rx="14" fill="#eef1f7" stroke="#26346b" stroke-width="2"/>
  <text x="52" y="55" font-size="16" fill="#26346b" font-weight="600" text-anchor="start">untrusted apps &middot; user code &middot; plugins</text>
  <text x="588" y="55" font-size="13" fill="#6b7280" text-anchor="end">large, buggy &mdash; tolerated</text>
  <rect x="150" y="96" width="340" height="132" rx="10" fill="#26346b" stroke="#0a1642" stroke-width="1.5"/>
  <text x="320" y="140" font-size="26" fill="#ffffff" font-weight="700" text-anchor="middle">TCB</text>
  <text x="320" y="168" font-size="15" fill="#dfe4f2" text-anchor="middle">kernel &middot; monitor &middot; crypto</text>
  <text x="320" y="190" font-size="14" fill="#ffb27a" text-anchor="middle">must be correct</text>
  <text x="320" y="254" font-size="14" fill="#c25200" text-anchor="middle">small &middot; trusted &middot; ideally verified</text>
</svg>

Note:
The TCB is the operational form of the reference-monitor idea: name the exact set
of components that must be correct, trust those, and treat the rest as hostile.
The discipline is minimization — a smaller TCB means fewer places a bug becomes a
policy break, and it is the only way property three of the reference monitor is
achievable, because you cannot verify a large TCB. The diagram is the mental
model I want them carrying all term: a small trusted core inside a large
untrusted shell. Then ask the AI-unit question — where is an agent's
TCB? If correct enforcement of "do not exfiltrate the user's data" depends on the
model, the prompt, every tool, and every document the model reads, then the TCB
is effectively everything, which means nothing is genuinely trusted. Good security
architecture for agents is largely a fight to shrink that TCB back to something
bounded.

---

## Saltzer and Schroeder: the eight principles

An influential 1975 paper; it introduces a framework of eight design principles
that remain canonical:

1. **Economy of mechanism** — small and simple; you can't verify what you can't understand.
2. **Fail-safe defaults** — default **deny**, grant explicitly. A missing rule should lock, not open.
3. **Complete mediation** — check authority on *every* access, not once-and-cache.
4. **Open design** — assume the attacker has the blueprints. Secrecy belongs in keys, not architecture.
5. **Separation of privilege** — require *two independent conditions* (two-person rule, MFA).
6. **Least privilege** — the *minimum* rights for the task, for the *minimum* time. Limits blast radius.
7. **Least common mechanism** — minimize *shared* state; sharing is a channel and a single point of failure.
8. **Psychological acceptability** — it must be *usable*, or users route around it.

<p class="source">Source: Saltzer &amp; Schroeder, The Protection of Information in Computer Systems, Proc. IEEE 63(9), 1975.</p>

Note:
I want all eight named, not four gestured at. A few to dwell on. Fail-safe
defaults is violated most often and most expensively — every "that S3 bucket was
public by default" is a default-allow failure. Complete mediation eliminates the class of check-once-then-cache and TOCTOU bugs. Open design is Kerckhoffs: assume
the enemy has your source, put secrecy in keys — vendor claims about proprietary
safety filters are the modern violation to be skeptical of. Least privilege is
the core one for AI agents: the standing permission set an agent
holds is its most sensitive asset, so shrink it to exactly the task, for exactly the
duration, and a successful injection steals as little authority as possible.
Least common mechanism is the covert-channel principle restated as design advice.
Psychological acceptability is the human one engineers dismiss and attackers
exploit: a control users find intolerable gets disabled, and a disabled control
is no control. Saltzer and Schroeder add two imperfect extras — work factor and
compromise recording — flagging that not every rule is absolute.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 7</span>

# Threat modeling

---

## How to build a threat model: four questions

1. **What are you protecting?** — *assets* (and their value).
2. **From whom?** — *adversaries*, with capabilities and motivations.
3. **Where can they touch you?** — *attack surface* and *trust boundaries*.
4. **What happens if you fail?** — *impact*, and therefore how much defense is worth buying.

Question 4 is really economics: your defense budget is bounded by what you'd lose,
so spend up to roughly (chance of the threat) × (what it costs you), and no more.

Note:
This is the framework we will use all term; every discussion, every project
writeup, every exam question about a defense gets pushed through these four. The
order matters — people jump to mechanism, "we will add a filter," before naming
the asset, the adversary, and the boundary. The expected-loss line is deliberately crude, but it sets the right instinct: defense budget is bounded by expected loss, so
a control that costs more than the asset is worth is a failure regardless of how
well it works. This is where the AI systems make the asset question concrete: model weights are
nine figures of training cost in one file, and an agent's standing authority can
be worth more than any single record it guards. In some systems, misusing the agent's authority for an afternoon is worse than
stealing a single database table.

---

## STRIDE: a checklist that maps onto CIA

For each element and each boundary crossing, ask which of six threats applies.
STRIDE is the dual of the properties from Part 1:

| Threat | Violates | Example |
|---|---|---|
| **S**poofing | Authentication | Forge a sender, impersonate a service |
| **T**ampering | Integrity | Alter data in transit or at rest |
| **R**epudiation | Non-repudiation | Deny an action; no reliable audit trail |
| **I**nformation disclosure | Confidentiality | Read data you should not |
| **D**enial of service | Availability | Exhaust a resource, block legitimate use |
| **E**levation of privilege | Authorization | Run as admin from an unprivileged foothold |

<p class="source">Source: Kohnfelder &amp; Garg, The Threats to Our Products, Microsoft internal, 1999.</p>

Note:
STRIDE is Microsoft's 1999 mnemonic and its whole value is coverage — it is a forcing function so you do not stop after the one threat you already thought of.
Notice it is basically the CIA properties plus authentication, non-repudiation, and
authorization turned into attack verbs, which is why it maps cleanly onto Part 1:
spoofing attacks authentication, tampering attacks integrity, disclosure attacks
confidentiality, DoS attacks availability, elevation attacks authorization,
repudiation attacks auditability. The method is deliberately mechanical:
for every box and every boundary crossing in your DFD, run all six letters. When
we get to agents, the interesting cells are elevation — a confused deputy is
elevation of privilege by another name — and information disclosure through the
model's outputs.

---

## Exercise: threat-model an email assistant

Take an LLM app that reads your inbox and drafts replies. Run it through the four
questions and watch where the analysis breaks:

- **Assets?** — yours (inbox, contacts, the drafts) *and* the vendor's (model, prompt).
- **Adversaries?** — who benefits, at what capability level?
- **Attack surface?** — *who can put text in front of this model?*
- **Worst realistic failure?** — and build the two-level attack tree for it.

<!-- INSTRUCTOR TODO: sandbox demo — a toy email-assistant mockup students poke at in the authorized course sandbox (canned, CTF-style); left for KM to develop -->

Note:
Run this live. Steer them toward is the answer
to question three: anyone on the internet can email you, so anyone on the internet
gets to put input in front of the model that holds your inbox. The attack surface
of "reads your email" is "the entire world," and the trust boundary between
instructions-from-the-user and content-from-a-stranger simply does not exist inside
the context window — which is the noninterference failure from Part 5 made
concrete. Do not rush to name indirect prompt injection if students do not; let the
structure do the work, and let them draw the attack tree with a phishing-style content
injection as the cheapest branch. When we hit the Greshake indirect-injection paper
in week 11, call back to this exact exercise, and to Biba's no-read-down, and to
the trust boundary nobody could draw.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 8</span>

# Provably-Correct Security

## What a proof buys — and the assumptions where attacks live

---

## Anatomy of a security proof

Every "proof of security" has three parts and one hidden fourth:

1. A **model** of the system — simplified, formal.
2. A **policy** — a precise property ("no buffer overflow," "secrets don't leak").
3. A **proof** that the *model* satisfies the *policy*,
4. ...against a **stated adversary**.

So a proof establishes: *this model* meets *this policy* against *this adversary*.
It does **not** establish that the model equals the real system, that the policy
is the one you actually wanted, or that the real attacker respects your adversary
model.

Note:
Be fair to formal methods before criticizing their scope. A security proof is a serious achievement, but it is
always a conditional with three antecedents: the model faithfully represents the
system, the policy captures what you actually care about, and the adversary plays
by the stated rules. The proof establishes the consequent given all three. None of
the three is ever perfectly true, and that is not a reason to skip proofs — it is a reason to read assumptions the way an attacker does, as the likely places
to look. This slide is the frame for both the seL4 case study and Thursday's
discussion paper, where the same argument is made about published LLM defenses.

---

## Testing versus verification

**Testing** checks the property on the inputs you *tried*. **Verification** proves
it for *all* inputs — but only inside the model.

> "Program testing can be used to show the presence of bugs, but never to show
> their absence." — Dijkstra

This is Part 1's correctness-vs-security gap again: testing samples the input
space; the attacker searches all of it. Fuzzing is testing with an adversarial
sampler — it explores millions of inputs and finds real bugs, but "didn't find
one" never becomes "there is none." Only verification reaches *all inputs*, and
its catch is the phrase "in the model."

<p class="source">Source: Dijkstra, Notes on Structured Programming (EWD249), 1970.</p>

Note:
This is the quantifier slide from Part 1 returning as a proof-methodology statement. Testing evaluates the property on the inputs you sampled; verification
proves it for all inputs the model admits. Dijkstra's line is the difference
in one sentence — testing can exhibit a bug, never certify its absence, because no
finite sample is the universal quantifier. Fuzzing is a strong form of testing, an adversarial sampler that explores millions of inputs, and it finds
real bugs, but it is still sampling: it never crosses from "did not find one" to
"there is none." Verification is the only tool that reaches the universal
quantifier, and the catch, which the next two slides are entirely about, is the
phrase "in the model."

---

## seL4: the strongest OS proof we have

A general-purpose microkernel with a machine-checked functional-correctness proof.

<div class="two-col">
<div class="col-left">

**The artifact**
- <span class="stat">8,700</span><span class="stat-label">lines of C (+ ~600 asm)</span>
- <span class="stat">~200k</span><span class="stat-label">lines of Isabelle/HOL proof</span>
- <span class="stat">~20</span><span class="stat-label">person-years total effort</span>

</div>
<div class="col-right">

**The theorem**

Every behavior of the C code is allowed by an abstract specification. So the
kernel has **no** null derefs, buffer overflows, code injection, or unchecked
arithmetic — and every system call **terminates** — for *all* inputs, not a test
suite.

</div>
</div>

<p class="source">Source: Klein et al., seL4: Formal Verification of an OS Kernel, SOSP, 2009.</p>

Note:
seL4 is the landmark example, and the numbers matter: about eighty-seven hundred lines of
C, roughly two hundred thousand lines of Isabelle proof, on the order of twenty
person-years — a proof-to-code ratio north of twenty to one. The theorem is a
refinement: the C implementation refines an abstract specification, meaning every
behavior the C code can exhibit is one the spec allows. That single property is
enormously strong for a systems artifact — it rules out the entire class of C
memory-safety and control-flow bugs, guarantees every kernel call terminates, and
does so for all inputs, not a test suite. This is among the strongest verification results for real software. That is why the next slide — what the proof does not cover —
is the one that teaches the lesson.

---

## What the seL4 proof does not cover

The theorem is conditional on assumptions the proof **explicitly excludes**:

- The **~600 lines of assembly** and the **boot code** — hand-verified at best, not in the refinement.
- The **C compiler and linker** — the proof is about the C, not the emitted machine code.
- The **hardware model** — CPU, MMU, and crucially **cache and TLB** management (done in that assembly).
- **Timing / covert channels** — the functional proof says nothing about them.
- **DMA** from devices bypassing the MMU.
- **The specification itself** — a wrong spec is faithfully implemented wrong (McLean's System Z, Part 4).

<div class="callout defense">Follow-on work shrank two gaps: <strong>Sewell et
al. 2013</strong> validated the compiler output down to the binary;
<strong>Murray et al. 2013</strong> added an information-flow (noninterference)
proof. The <em>2009</em> result assumed both.</div>

<p class="source">Sources: Klein et al., SOSP, 2009; Sewell et al., PLDI, 2013; Murray et al., IEEE S&amp;P, 2013.</p>

Note:
This is the important slide in Part 8. seL4's own authors list the
assumptions, and reading that list is the skill. The proof is about the C
source, so the compiler must be trusted — later closed by Sewell's translation
validation, but assumed in 2009. The hardware model is assumed correct, including
cache and TLB behavior, which lives in the unverified assembly. The functional
proof is silent on timing, so covert timing channels are out of scope entirely —
the same gap we saw in Part 3, now in a formal-methods case study. And the spec
itself is an assumption: seL4 proves the code matches the spec, never that the spec
was the security policy you wanted, which is System Z again. So what did twenty person-years buy? Not the elimination of trust, but the
*relocation and shrinking* of it. Trust in eighty-seven hundred lines of C became trust in a formal spec, a
compiler, and a hardware model. That is a major win, and it is still conditional.

---

## The lesson for AI: verification does not directly scale to models

seL4: about **10,000** lines of code, a **precise spec**, **20 person-years** —
and even then, a proof with a page of assumptions.

An LLM: **hundreds of billions** of learned weights, and **no specification of
correct behavior at all.** A proof needs a precise spec to check the system
against, and "be helpful and harmless" is not one. You cannot prove a system meets a specification you cannot state.

Note:
Here is why this whole deck matters for AI. seL4 shows the price
and the limit of the strongest tool we have: ten thousand lines, a precise
specification, twenty person-years, and still a page of assumptions. Now scale the
object of study to a language model — a hundreds of billions of parameters, weights learned
from data, and, decisively, no specification of correct behavior to prove anything
against. Refinement needs a spec on the right-hand side. "Helpful and harmless" is not
a formal predicate. So proving a model
safe is not merely hard; it is not a well-posed verification problem today. What is
well-posed is verifying the scaffold — the monitor, the sandbox, the policy engine
around the model — which is a small, classical TCB of exactly the kind seL4 shows
we can handle. That is the strategic reason the classical foundations are the
foundations of AI security: the model is unverifiable, so security has to live in
the verifiable ring around it.

---

## Assurance is a spectrum — ask where the evidence sits

From weakest to strongest, roughly:

1. "We wrote it carefully."
2. **Tested** — sampled the input space.
3. **Fuzzed** — sampled adversarially, at scale.
4. **Audited / pentested** — a human adversary, briefly.
5. **Bug bounty** — many adversaries, weak incentives.
6. **Formally verified** — strongest *claims*, about the *model* (inherits Part 8's gap).

Note:
This ladder is a consumer-protection tool the students can use for the rest of the
term and their careers. Most software lives at rungs one and two. Note the
inversion at the top: rung six gives the strongest claims but inherits the
model-versus-system gap from the seL4 slides, so mature systems combine high rungs
with low ones — verify the core, fuzz the edges, bounty the rest. Apply it to AI
honestly: most guardrails are rung two with thin coverage, and "we red-teamed it"
usually means rung four for a few weeks against last month's attacks, which says
almost nothing about an adaptive adversary who studies the defense. When a vendor
says a model cannot do something, translate it: did not, on the distribution we
tried. That translation is the basic check this course keeps applying.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 9</span>

# The bug we keep reintroducing

## Control versus data — the course through-line

---

<!-- .slide: class="big-point" -->

# Control vs. data

**Many serious vulnerabilities share one failure: the attacker's *data* becomes the
system's *control*.**

Note:
State the course thesis plainly. Control is what the machine does; data is what
it does it to. Security requires a hard boundary between them, and mixing them is
usually convenient — one channel, one format, one parser — so every generation
of systems remakes the same trade and every generation of attackers collects the same debt. Say it abstractly here so the four instances on the next slide land
as instances of one thing, not four separate topics. The reason it recurs is partly economic, not just technical: separation costs effort, mixing ships faster, and the bill
comes due later as somebody else's incident.

---

## The same pattern, four decades

| Era | The *data* channel | Becomes *control* when... | Re-separating mechanism |
|---|---|---|---|
| 1988– | bytes into a stack buffer | they overwrite the return address | NX / W^X, ASLR, stack canaries |
| 1998– | a form field in a query string | quotes escape into SQL syntax | parameterized queries |
| 2005– | user content in a web page | it is parsed as `<script>` (XSS) | output encoding, CSP |
| 2023– | any text in a context window | the model treats it as instructions | **no equivalent mechanism** |

The first three fixes share a shape: they don't *detect* bad input, they make the
confusion **impossible by construction** — a W^X page cannot execute, a bound
parameter cannot become syntax. Each leaned on a **syntactic boundary** a parser
or a hardware bit could enforce: code vs. data pages, SQL grammar vs. string
literals, markup vs. text.

<div class="callout threat">The fourth row is open because that boundary is gone.
To an LLM, an instruction and a <em>description</em> of an instruction are both
just text in one stream — no grammar separates them, so there is no structural fix
yet. Today's defenses detect and limit damage; they do not separate.</div>

Note:
Walk each row of the table as data, control, and the
mechanism that re-separated them. Stack overflow: the data is bytes copied into a
buffer, they become control when they land on the saved return address, and the
fix is to make writable memory non-executable so injected bytes cannot run. SQL
injection: the data is a form field, it becomes control when a quote escapes into
query syntax, and the fix is parameterized queries that send code and data on
separate channels so data can never be parsed as SQL. XSS: user content becomes a
script tag, and the fix is output encoding plus a content-security policy. The important point is that all three fixes are constructions, not filters — they do not try
to recognize malicious input, they make the category confusion structurally
impossible. That distinction is why they worked where blocklists
failed, and it is the standard the fourth row does not yet meet.

---

## Recap: the toolkit, and where each piece returns

- **CIA, said precisely** — name the property violated; confidentiality is about pairs of runs, so you cannot test it by watching one. *(Part 1)*
- **Access control + HRU** — subjects/objects/rights; and safety is *undecidable* — a limit on the policy, not the mechanism. *(Part 2)*
- **Information flow** — label the information; implicit flows and covert channels are the hard part; influence, not copying. *(Part 3)*
- **BLP / Biba / noninterference** — no-write-down, no-read-down, and the strongest confidentiality statement — which an LLM violates by construction. *(Parts 4–5)*
- **Reference monitor, TCB, the eight principles** — where enforcement lives, and the rubric for every defense. *(Part 6)*
- **Threat modeling** — four questions, DFDs, STRIDE, attack trees with real propagation. *(Part 7)*
- **Proofs** — read the assumptions; verification relocates trust, it does not remove it; it does not scale to models. *(Part 8)*

<div class="callout good">One invariant underneath all of it: <strong>keep the
attacker's data out of your control channel.</strong> Most AI attacks this term will be violations of the same old invariant.</div>

Note:
Close by connecting each tool to where it returns. CIA gives the vocabulary and the
hyperproperty point. HRU gives the humbling result that you cannot even always
analyze your own policy. Information flow gives influence-versus-copying and the
covert-channel gap. BLP, Biba, and noninterference give the mandatory-flow models
and the exact sense in which an LLM context violates them. The reference monitor,
TCB, and the eight principles give the enforcement architecture and the grading
rubric. Threat modeling gives the four questions and the propagation arithmetic
that exposes misallocated hardening. And the proofs part gives the discipline of reading
assumptions and the strategic conclusion that we verify the scaffold, not the
model. Underneath every one of them is the single invariant — separate control
from data — which is why day one of an AI security course is fifty-year-old
systems security.
