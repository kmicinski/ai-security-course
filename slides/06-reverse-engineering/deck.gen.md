<!-- title: CIS400 — Reverse Engineering -->
<!-- theme: cis400 -->
<!-- .slide: class="title-slide" -->
<span class="course-tag">CIS 400 &bull; AI + Cybersecurity &bull; Fall 2026</span>

# Reverse Engineering

## Kristopher Micinski

<div class="footer">cis400 &bull; cybersecurity &amp; ai</div>

Note:
About a lecture and a half. Stop before the end of Tuesday for the student presentation and pick up Thursday. Content: what a binary actually contains, how source becomes machine code, what compilation destroys, and what a reverse engineer must rebuild. Next week uses this to reason about binaries automatically: symbolic execution, constraint solving, SMT.

---

## We have binary, but not source code

- Kind of equivalent, kind of not: binaries are hard to reason about directly, so we "lift" or "decompile" them back toward source
- In a *stripped* binary there is no symbol table to say where the functions are. The file header gives one address, the _entry point_ (`_start`), and nothing else.
  - Maybe common compiler idioms tell us where functions start?
  - Maybe not: what even is a "function"? What if the binary came from a language we have never seen?

<div class="figure">
<svg viewBox="0 0 1200 210" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="ep" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#f76900"/></marker></defs>
<text class="fig-small" x="40" y="92" text-anchor="start">.text</text>
<rect class="fig-box ctx" x="110" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="138" y="94" text-anchor="middle">55</text>
<rect class="fig-box ctx" x="168" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="196" y="94" text-anchor="middle">48</text>
<rect class="fig-box ctx" x="226" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="254" y="94" text-anchor="middle">89</text>
<rect class="fig-box ctx" x="284" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="312" y="94" text-anchor="middle">e5</text>
<rect class="fig-box ctx" x="342" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="370" y="94" text-anchor="middle">48</text>
<rect class="fig-box ctx" x="400" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="428" y="94" text-anchor="middle">83</text>
<rect class="fig-box ctx" x="458" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="486" y="94" text-anchor="middle">ec</text>
<rect class="fig-box ctx" x="516" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="544" y="94" text-anchor="middle">20</text>
<rect class="fig-box ctx" x="574" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="602" y="94" text-anchor="middle">8b</text>
<rect class="fig-box ctx" x="632" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="660" y="94" text-anchor="middle">45</text>
<rect class="fig-box ctx" x="690" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="718" y="94" text-anchor="middle">f8</text>
<rect class="fig-box ctx" x="748" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="776" y="94" text-anchor="middle">c9</text>
<rect class="fig-box ctx" x="806" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="834" y="94" text-anchor="middle">c3</text>
<rect class="fig-box ctx" x="864" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="892" y="94" text-anchor="middle">55</text>
<rect class="fig-box ctx" x="922" y="62" width="56" height="50" rx="4"/><text class="fig-mono" x="950" y="94" text-anchor="middle">48</text>
<text class="fig-mono" x="1000" y="94" text-anchor="start">…</text>
<g class="fragment">
<path class="fig-arrow model" marker-end="url(#ep)" d="M138,20 L138,56"/>
<text class="fig-small fig-orange" x="150" y="28" text-anchor="start">entry point: the one address we are given</text>
</g>
<g class="fragment">
<rect x="110" y="122" width="752" height="34" rx="4" fill="none" stroke="#c0392b" stroke-width="2" stroke-dasharray="7 5"/>
<text class="fig-small fig-danger" x="486" y="145" text-anchor="middle">function?</text>
<rect x="864" y="122" width="150" height="34" rx="4" fill="none" stroke="#c0392b" stroke-width="2" stroke-dasharray="7 5"/>
<text class="fig-small fig-danger" x="939" y="145" text-anchor="middle">function?</text>
<text class="fig-small fig-danger" x="486" y="190" text-anchor="middle">where does one end and the next begin? nothing in the bytes says</text>
</g>
<g class="fragment">
<rect class="fig-box ctx" x="1050" y="55" width="130" height="64" rx="6"/>
<text class="fig-small" x="1115" y="82" text-anchor="middle">symbol</text>
<text class="fig-small" x="1115" y="104" text-anchor="middle">table</text>
<path d="M1055,60 L1175,114" stroke="#c0392b" stroke-width="4"/>
<path d="M1175,60 L1055,114" stroke="#c0392b" stroke-width="4"/>
<text class="fig-small fig-danger" x="1115" y="145" text-anchor="middle">stripped</text>
</g>
</svg>
</div>

---

## What can we learn

- What does it do?
- What inputs does it accept?
- Where does it communicate?
- Does it contain vulnerabilities?
- Can we make it do something unintended?

---

## Why reverse engineer

<div class="two-col">
<div class="col-left">

- Lots of applications of RE: vulnerability research, malware analysis, firmware, forensics, compatibility, legacy software

- RE involves lots of iterated hypothesis formation, testing, falsification, and iterating again in a tight loop to build understanding.

- Recently: can AI and LLMs be used to help humans perform RE at an increasingly rapid pace or with higher fidelity?

</div>


<div class="col-right">

<div class="figure">
<svg viewBox="0 0 400 360" xmlns="http://www.w3.org/2000/svg">
<rect class="fig-box ctx" x="30" y="20" width="150" height="70" rx="8"/><text class="fig-small" x="105" y="60" text-anchor="middle">executable</text>
<rect class="fig-box ctx" x="220" y="20" width="150" height="70" rx="8"/><text class="fig-small" x="295" y="60" text-anchor="middle">firmware</text>
<rect class="fig-box ctx" x="30" y="150" width="150" height="70" rx="8"/><text class="fig-small" x="105" y="190" text-anchor="middle">library</text>
<rect class="fig-box world" x="220" y="150" width="150" height="70" rx="8"/><text class="fig-small" x="295" y="190" text-anchor="middle">malware</text>
</svg>
</div>

</div>
</div>

---

## Scenarios

| situation | question |
|---|---|
| unknown binary in `/tmp` on a compromised server | what did it do? |
| email attachment that phones home | where, and what does it send? |
| router firmware, no source | hardcoded credentials? |
| vendor ships a patch on Tuesday | what bug did they fix? |
| a dependency behaves oddly (xz, 2024) | does it do what it claims? |
| factory controller, vendor long gone | make it talk to new hardware |
| undocumented file format or network protocol | write a compatible reader |
| closed-source driver crashes the kernel | where, and is it exploitable? |
| CTF challenge | what input prints the flag? |

Different goals. Same starting point: a binary and no source.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 1</span>

# Compilation: from source code to machine code

---

## Source code

```c
int clamp_square(int x, int limit) {
    int y = x * x;
    if (y > limit)
        return limit;
    return y;
}
```

Programmer-level abstractions: names, types, control structure.

---

## Assembly

```asm
clamp_square:
    imul edi, edi        ; y = x * x
    mov  eax, esi        ; result = limit
    cmp  edi, esi
    jg   .done           ; y > limit ?
    mov  eax, edi        ; result = y
.done:
    ret
```

Text instructions. Architecture specific. One of several ways to compile this function.

---

## Machine code

<div class="two-col">
<div class="col-left">

```asm
imul edi, edi
mov  eax, esi
cmp  edi, esi
jg   .done
mov  eax, edi
ret
```

</div>
<div class="col-right">

```text
0f af ff
89 f0
39 f7
7f 02
89 f8
c3
```

</div>
</div>

The CPU executes encoded instructions. `7f 02` means "jump forward 2 bytes if greater." Exact bytes depend on the instructions chosen.

---

## Compiling a program _throws away_ information

#### RE is the process of _recovering_ it, using a mix of automated / manual methods

<div class="two-col">
<div class="col-left">

```c
int clamp_square(int x, int limit) {
    int y = x * x;
    if (y > limit)
        return limit;
    return y;
}
```

</div>
<div class="col-right">

Gone or transformed:

- names <!-- .element: class="fragment" -->
- types <!-- .element: class="fragment" -->
- comments <!-- .element: class="fragment" -->
- source-level control structure <!-- .element: class="fragment" -->
- abstractions <!-- .element: class="fragment" -->

</div>
</div>

---

## Compilation is a pipeline

<div class="figure">
<svg viewBox="0 0 1200 120" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="pl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="0" y="25" width="200" height="70" rx="10"/>
<text class="fig-title" x="100" y="68" text-anchor="middle">C source</text>
<path class="fig-arrow" marker-end="url(#pl)" d="M205,60 L245,60"/>
<rect class="fig-box ctx" x="250" y="25" width="200" height="70" rx="10"/>
<text class="fig-title" x="350" y="68" text-anchor="middle">front end</text>
<path class="fig-arrow" marker-end="url(#pl)" d="M455,60 L495,60"/>
<rect class="fig-box ctx" x="500" y="25" width="200" height="70" rx="10"/>
<text class="fig-title" x="600" y="68" text-anchor="middle">IR</text>
<path class="fig-arrow" marker-end="url(#pl)" d="M705,60 L745,60"/>
<rect class="fig-box ctx" x="750" y="25" width="200" height="70" rx="10"/>
<text class="fig-title" x="850" y="68" text-anchor="middle">optimizer</text>
<path class="fig-arrow" marker-end="url(#pl)" d="M955,60 L995,60"/>
<rect class="fig-box world" x="1000" y="25" width="200" height="70" rx="10"/>
<text class="fig-title" x="1100" y="68" text-anchor="middle">machine code</text>
<g class="fragment fade-out" data-fragment-index="1"><rect x="-6" y="19" width="212" height="82" rx="14" fill="none" stroke="#f76900" stroke-width="6"/></g>
<g class="fragment current-visible" data-fragment-index="1"><rect x="244" y="19" width="212" height="82" rx="14" fill="none" stroke="#f76900" stroke-width="6"/></g>
<g class="fragment current-visible" data-fragment-index="2"><rect x="494" y="19" width="212" height="82" rx="14" fill="none" stroke="#f76900" stroke-width="6"/></g>
<g class="fragment current-visible" data-fragment-index="3"><rect x="744" y="19" width="212" height="82" rx="14" fill="none" stroke="#f76900" stroke-width="6"/></g>
<g class="fragment" data-fragment-index="4"><rect x="994" y="19" width="212" height="82" rx="14" fill="none" stroke="#f76900" stroke-width="6"/></g>
</svg>
</div>

<div class="r-stack" style="display:grid; justify-items:center; align-items:start; width:100%;">
<div class="fragment fade-out" data-fragment-index="1" style="grid-area:1/1; width:100%;">

```c
int clamp_square(int x, int limit) {
    int y = x * x;
    if (y > limit)
        return limit;
    return y;
}
```

What you wrote.

</div>
<div class="fragment current-visible" data-fragment-index="1" style="grid-area:1/1; width:100%;">

```text
FunctionDecl clamp_square : (int, int) -> int
  ParmVar  x : int
  ParmVar  limit : int
  VarDecl  y : int  =  BinaryOp(*, x, x)
  IfStmt   BinaryOp(>, y, limit)
    Return limit
  Return y
```

Parsed and type-checked. Every name still present.

</div>
<div class="fragment current-visible" data-fragment-index="2" style="grid-area:1/1; width:100%;">

```llvm
  %y = alloca i32
  %0 = mul i32 %x, %x
  store i32 %0, ptr %y
  %1 = load i32, ptr %y
  %c = icmp sgt i32 %1, %limit
  br i1 %c, label %L1, label %L2
L1:
  ret i32 %limit
L2:
  ret i32 %1
```

`y` gets a memory slot. Every use is a load or a store.

</div>
<div class="fragment current-visible" data-fragment-index="3" style="grid-area:1/1; width:100%;">

```llvm
  %y = mul i32 %x, %x
  %c = icmp sgt i32 %y, %limit
  br i1 %c, label %L1, label %L2
L1:
  ret i32 %limit
L2:
  ret i32 %y
```

`y` now lives in a register. The loads and stores are gone.

</div>
<div class="fragment" data-fragment-index="4" style="grid-area:1/1; width:100%;">

```text
0f af ff    imul edi, edi
89 f0       mov  eax, esi
39 f7       cmp  edi, esi
7f 02       jg   +2
89 f8       mov  eax, edi
c3          ret
```

Instructions selected and encoded. No names left.

</div>
</div>

---

## A more realistic pipeline

<div class="figure">
<svg viewBox="340 0 620 540" style="max-width:620px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="p2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="360" y="10" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="39" text-anchor="middle">C source</text>
<path class="fig-arrow" marker-end="url(#p2)" d="M500,58 L500,86"/><text class="fig-small" x="640" y="78" text-anchor="start">cpp</text>
<rect class="fig-box ctx" x="360" y="88" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="117" text-anchor="middle">preprocessor</text>
<path class="fig-arrow" marker-end="url(#p2)" d="M500,136 L500,164"/>
<rect class="fig-box ctx" x="360" y="166" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="195" text-anchor="middle">front end</text>
<path class="fig-arrow fragment" marker-end="url(#p2)" d="M500,214 L500,242"/>
<rect class="fig-box ctx fragment" x="360" y="244" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="273" text-anchor="middle">IR</text>
<path class="fig-arrow fragment" marker-end="url(#p2)" d="M500,292 L500,320"/>
<rect class="fig-box ctx fragment" x="360" y="322" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="351" text-anchor="middle">optimizer</text>
<path class="fig-arrow fragment" marker-end="url(#p2)" d="M500,370 L500,398"/>
<rect class="fig-box ctx fragment" x="360" y="400" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="429" text-anchor="middle">assembly</text>
<path class="fig-arrow fragment" marker-end="url(#p2)" d="M500,448 L500,476"/><text class="fig-small fragment" x="640" y="468" text-anchor="start">as</text>
<rect class="fig-box ctx fragment" x="360" y="478" width="280" height="46" rx="6"/><text class="fig-mono" x="500" y="507" text-anchor="middle">object file</text>
<g class="fragment">
<path class="fig-arrow" marker-end="url(#p2)" d="M640,501 L740,501 L740,320"/><text class="fig-small" x="760" y="410" text-anchor="start">ld</text>
<rect class="fig-box world" x="700" y="272" width="240" height="46" rx="6"/><text class="fig-mono" x="820" y="301" text-anchor="middle">executable</text>
</g>
</svg>
</div>

---

## Front end

<div class="figure">
<svg viewBox="0 0 1100 140" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="fe" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="20" y="40" width="200" height="60" rx="8"/><text class="fig-mono" x="120" y="77" text-anchor="middle">source</text>
<path class="fig-arrow" marker-end="url(#fe)" d="M225,70 L285,70"/>
<rect class="fig-box ctx" x="290" y="40" width="200" height="60" rx="8"/><text class="fig-mono" x="390" y="77" text-anchor="middle">tokens</text>
<path class="fig-arrow" marker-end="url(#fe)" d="M495,70 L555,70"/>
<rect class="fig-box ctx" x="560" y="40" width="200" height="60" rx="8"/><text class="fig-mono" x="660" y="77" text-anchor="middle">syntax tree</text>
<path class="fig-arrow" marker-end="url(#fe)" d="M765,70 L825,70"/>
<rect class="fig-box ctx" x="830" y="40" width="240" height="60" rx="8"/><text class="fig-mono" x="950" y="77" text-anchor="middle">typed program</text>
</svg>
</div>

Parsing, type checking, source-language semantics.

---

## Intermediate representations

Compilers rarely translate source straight to machine code.

<div class="figure">
<svg viewBox="0 0 1100 300" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="ir" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="20" y="30" width="140" height="50" rx="6"/><text class="fig-small" x="90" y="61" text-anchor="middle">C</text>
<rect class="fig-box ctx" x="20" y="110" width="140" height="50" rx="6"/><text class="fig-small" x="90" y="141" text-anchor="middle">C++</text>
<rect class="fig-box ctx" x="20" y="190" width="140" height="50" rx="6"/><text class="fig-small" x="90" y="221" text-anchor="middle">Rust</text>
<rect class="fig-box model" x="450" y="105" width="200" height="70" rx="10"/><text class="fig-title" x="550" y="147" text-anchor="middle">IR</text>
<path class="fig-arrow" marker-end="url(#ir)" d="M165,55 C 320,55 340,130 445,132"/>
<path class="fig-arrow" marker-end="url(#ir)" d="M165,135 L445,138"/>
<path class="fig-arrow" marker-end="url(#ir)" d="M165,215 C 320,215 340,145 445,143"/>
<rect class="fig-box ctx" x="940" y="30" width="140" height="50" rx="6"/><text class="fig-small" x="1010" y="61" text-anchor="middle">x86-64</text>
<rect class="fig-box ctx" x="940" y="110" width="140" height="50" rx="6"/><text class="fig-small" x="1010" y="141" text-anchor="middle">ARM</text>
<rect class="fig-box ctx" x="940" y="190" width="140" height="50" rx="6"/><text class="fig-small" x="1010" y="221" text-anchor="middle">RISC-V</text>
<path class="fig-arrow" marker-end="url(#ir)" d="M655,132 C 780,130 820,55 935,55"/>
<path class="fig-arrow" marker-end="url(#ir)" d="M655,138 L935,138"/>
<path class="fig-arrow" marker-end="url(#ir)" d="M655,143 C 780,145 820,215 935,215"/>
</svg>
</div>

Analysis and optimization, once, over one representation.

---

## Common compiler IRs

<div class="figure">
<svg viewBox="0 0 1200 132" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="cir" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="0" y="50" width="150" height="50" rx="6"/><text class="fig-small" x="75" y="81" text-anchor="middle">source</text>
<path class="fig-arrow" marker-end="url(#cir)" d="M155,75 L1045,75"/>
<rect class="fig-box ctx" x="1050" y="50" width="150" height="50" rx="6"/><text class="fig-small" x="1125" y="81" text-anchor="middle">machine code</text>
<path class="fig-arrow model" d="M240,38 L655,38"/>
<path class="fig-arrow model" d="M240,30 L240,46"/>
<path class="fig-arrow model" d="M655,30 L655,46"/>
<text class="fig-small fig-orange" x="447" y="22" text-anchor="middle">MLIR: a stack of dialects, high to low</text>
<circle class="fig-box model" cx="560" cy="75" r="9"/><text class="fig-small" x="560" y="120" text-anchor="middle">GIMPLE</text>
<circle class="fig-box model" cx="660" cy="75" r="9"/><text class="fig-small" x="660" y="120" text-anchor="middle">LLVM IR</text>
<circle class="fig-box model" cx="900" cy="75" r="9"/><text class="fig-small" x="900" y="120" text-anchor="middle">RTL</text>
</svg>
</div>

<div style="font-size:0.75em">

| IR | Level | Shape | What sets it apart | Used by |
|---|---|---|---|---|
| **LLVM IR** | mid | typed SSA, unlimited virtual registers; `.ll` text or `.bc` bitcode | one IR for the whole middle end; stable enough that many front ends target it | Clang, Rust, Swift, Julia |
| **GIMPLE** | mid | three-address tuples, one op per statement; SSA for most passes | GCC's language-neutral IR, lowered from each front end's GENERIC; where GCC optimizes | gcc, g++, gfortran |
| **RTL** | low | Lisp-like `(set (reg:SI 0) (plus:SI …))` | target-specific: machine modes, real registers, instruction patterns; where GCC selects instructions and allocates registers | GCC back ends |
| **MLIR** | high → mid | ops grouped into *dialects*: `affine`, `linalg`, `llvm`, … | a framework for building IRs, not one IR; lowered dialect by dialect, usually into LLVM IR | TensorFlow, Triton, IREE, Flang |

</div>

---

## LLVM

Compiler infrastructure, not one compiler. Front ends emit LLVM IR. Passes rewrite it. Back ends turn it into machine code.

<div class="figure">
<svg viewBox="0 0 1200 170" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="lv" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="0" y="40" width="150" height="70" rx="10"/><text class="fig-mono" x="75" y="82" text-anchor="middle">clamp.c</text>
<path class="fig-arrow" marker-end="url(#lv)" d="M155,75 L235,75"/><text class="fig-small" x="195" y="60" text-anchor="middle">clang</text>
<rect class="fig-box model" x="240" y="40" width="150" height="70" rx="10"/><text class="fig-mono" x="315" y="82" text-anchor="middle">clamp.ll</text>
<path class="fig-arrow" marker-end="url(#lv)" d="M395,75 L475,75"/><text class="fig-small" x="435" y="60" text-anchor="middle">opt -O2</text>
<rect class="fig-box model" x="480" y="40" width="150" height="70" rx="10"/><text class="fig-mono" x="555" y="82" text-anchor="middle">clamp.ll</text>
<path class="fig-arrow" marker-end="url(#lv)" d="M635,75 L715,75"/><text class="fig-small" x="675" y="60" text-anchor="middle">llc</text>
<rect class="fig-box ctx" x="720" y="40" width="150" height="70" rx="10"/><text class="fig-mono" x="795" y="82" text-anchor="middle">clamp.s</text>
<path class="fig-arrow" marker-end="url(#lv)" d="M875,75 L955,75"/><text class="fig-small" x="915" y="60" text-anchor="middle">as</text>
<rect class="fig-box world" x="960" y="40" width="150" height="70" rx="10"/><text class="fig-mono" x="1035" y="82" text-anchor="middle">clamp.o</text>
<text class="fig-small" x="315" y="145" text-anchor="middle">IR, unoptimized</text>
<text class="fig-small" x="555" y="145" text-anchor="middle">IR, optimized</text>
<text class="fig-small" x="795" y="145" text-anchor="middle">x86-64 assembly</text>
</svg>
</div>

Started 2003 at UIUC. Today the back end for Clang, Rust, Swift, Julia, and most GPU compilers.

---

## LLVM IR in one slide

<div class="two-col">
<div class="col-left">

- **typed**: every value has a type: `i32`, `i1`, `ptr`
- **SSA**: each `%name` is assigned exactly once
- **unlimited registers**: `%y`, `%c`, … are virtual; allocation happens later
- **explicit control flow**: a function is a list of basic blocks; each ends in `br` or `ret`
- no flags, no implicit stack, no hidden side effects

</div>
<div class="col-right">

```llvm
define i32 @f(i32 %x) {
entry:
  %y = mul i32 %x, %x
  %c = icmp sgt i32 %y, 10
  br i1 %c, label %big, label %small
big:
  ret i32 10
small:
  ret i32 %y
}
```

</div>
</div>

Readable by humans, designed for tools.

---

## clamp_square in LLVM IR

<div class="two-col">
<div class="col-left">

```c
int clamp_square(int x, int limit) {
    int y = x * x;
    if (y > limit)
        return limit;
    return y;
}
```

```bash
clang -O0 -S -emit-llvm clamp.c
```

</div>
<div class="col-right">

```llvm
define i32 @clamp_square(i32 %x, i32 %limit) {
entry:
  %y = mul nsw i32 %x, %x
  %c = icmp sgt i32 %y, %limit
  br i1 %c, label %ret_limit, label %ret_y
ret_limit:
  ret i32 %limit
ret_y:
  ret i32 %y
}
```

</div>
</div>

Three basic blocks. The `if` became a `br` on an `i1`. Simplified: `-O0` output also spills `x`, `limit`, and `y` to memory.

---

## The optimizer at work

<div class="two-col">
<div class="col-left">

```bash
opt -O2 -S clamp.ll
```

```llvm
define i32 @clamp_square(i32 %x, i32 %limit) {
  %y = mul nsw i32 %x, %x
  %c = icmp sgt i32 %y, %limit
  %r = select i1 %c, i32 %limit, i32 %y
  ret i32 %r
}
```

</div>
<div class="col-right">

```bash
llc clamp.opt.ll
```

```asm
clamp_square:
    imul   edi, edi
    cmp    edi, esi
    mov    eax, esi
    cmovle eax, edi
    ret
```

</div>
</div>

Three blocks became one. The branch became `select`, then `cmovle`. Same function as slide 8, different shape.

---

## Why LLVM matters for us

<div class="two-col">
<div class="col-left">

**Going down** (compilers)

- Clang, Rust, Swift all produce it
- every analysis and optimization is a pass over it

**Coming back up** (binary analysis)

- lifters turn machine code into LLVM IR: McSema / remill, RetDec
- tools written for LLVM IR then run on binaries: KLEE (symbolic execution), sanitizers, fuzzing instrumentation

</div>
<div class="col-right">

```bash
clang -O0 -S -emit-llvm clamp.c -o clamp.ll
opt   -O2 -S clamp.ll        -o clamp.opt.ll
llc   clamp.opt.ll           -o clamp.s
```

Try it on `clamp.c` before Thursday.

</div>
</div>

One IR, many front ends, many back ends. Binary-analysis tools borrow the idea. Why they rarely borrow the IR itself is a Part 3 question.

---

## Optimization rewrites the program

```c
int f(int x) {
    int y = x * 2;
    return y + 0;
}
```

<div class="two-col">
<div class="col-left">

**`clang -O0`**

```asm
f:
    push rbp
    mov  rbp, rsp
    mov  [rbp-4], edi     ; spill x
    mov  eax, [rbp-4]     ; reload x
    shl  eax, 1           ; y = x * 2
    mov  [rbp-8], eax     ; spill y
    mov  eax, [rbp-8]     ; reload y
    add  eax, 0           ; y + 0
    pop  rbp
    ret
```

</div>
<div class="col-right fragment">

**`clang -O2`**

```asm
f:
    lea eax, [rdi + rdi]   ; x << 1
    ret
```

</div>
</div>

Ten instructions became two. The stack traffic is gone, the `+ 0` is gone, and `x * 2` became an address computation.

---

## Control flow becomes a graph

<div class="two-col" style="align-items:center">
<div class="col-left">
<div style="font-size:1.35em">

```c
if (x > 10)
    y = 1;
else
    y = 2;
```

</div>
</div>
<div class="col-right">

<div class="figure narrow" style="max-width:400px; margin:0 auto">
<svg viewBox="0 0 420 320" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="cf" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="130" y="10" width="160" height="55" rx="8"/><text class="fig-mono" x="210" y="43" text-anchor="middle">cmp x,10</text>
<path class="fig-arrow" marker-end="url(#cf)" d="M180,67 L90,120"/>
<path class="fig-arrow" marker-end="url(#cf)" d="M240,67 L330,120"/>
<rect class="fig-box model" x="10" y="125" width="160" height="55" rx="8"/><text class="fig-mono" x="90" y="158" text-anchor="middle">y = 1</text>
<rect class="fig-box model" x="250" y="125" width="160" height="55" rx="8"/><text class="fig-mono" x="330" y="158" text-anchor="middle">y = 2</text>
<path class="fig-arrow" marker-end="url(#cf)" d="M90,182 L180,245"/>
<path class="fig-arrow" marker-end="url(#cf)" d="M330,182 L240,245"/>
<rect class="fig-box ctx" x="130" y="250" width="160" height="55" rx="8"/><text class="fig-mono" x="210" y="283" text-anchor="middle">merge</text>
</svg>
</div>

</div>
</div>

Nodes and edges: the control-flow graph (CFG). Each node is a **basic block**: straight-line code, one entry, one exit.

---

## Object files

<div class="figure">
<svg viewBox="0 0 1100 260" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="ob" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="60" y="90" width="180" height="70" rx="8"/><text class="fig-mono" x="150" y="132" text-anchor="middle">main.o</text>
<rect class="fig-box ctx" x="60" y="20" width="180" height="55" rx="8"/><text class="fig-mono" x="150" y="53" text-anchor="middle">util.o</text>
<rect class="fig-box world" x="60" y="175" width="180" height="55" rx="8"/><text class="fig-mono" x="150" y="208" text-anchor="middle">libc</text>
<path class="fig-arrow" marker-end="url(#ob)" d="M245,47 L430,110"/>
<path class="fig-arrow" marker-end="url(#ob)" d="M245,125 L430,125"/>
<path class="fig-arrow" marker-end="url(#ob)" d="M245,202 L430,140"/>
<rect class="fig-box model" x="435" y="90" width="180" height="70" rx="8"/><text class="fig-title" x="525" y="132" text-anchor="middle">linker</text>
<path class="fig-arrow" marker-end="url(#ob)" d="M620,125 L800,125"/>
<rect class="fig-box world" x="805" y="90" width="230" height="70" rx="8"/><text class="fig-mono" x="920" y="132" text-anchor="middle">executable</text>
</svg>
</div>

Object files hold machine code with unresolved references. The linker resolves **symbols** and **relocations**.

---

## Static vs dynamic linking

<div class="two-col">
<div class="col-left">

**Static**

```text
program + library code
        → executable
```

Library baked in.

</div>
<div class="col-right">

**Dynamic**

```text
program → shared library
        at load / runtime
```

`.so` on Linux, `.dll` on Windows.

</div>
</div>

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 2</span>

# Binaries on disk

---

## The Linux toolchain

<div class="figure">
<svg viewBox="0 0 500 430" style="max-width:400px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="lt" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="150" y="20" width="200" height="60" rx="8"/><text class="fig-mono" x="250" y="57" text-anchor="middle">foo.c</text>
<path class="fig-arrow" marker-end="url(#lt)" d="M250,82 L250,128"/><text class="fig-small" x="360" y="110" text-anchor="start">gcc / clang</text>
<rect class="fig-box ctx" x="150" y="130" width="200" height="60" rx="8"/><text class="fig-mono" x="250" y="167" text-anchor="middle">foo.s</text>
<path class="fig-arrow" marker-end="url(#lt)" d="M250,192 L250,238"/><text class="fig-small" x="360" y="220" text-anchor="start">as</text>
<rect class="fig-box ctx" x="150" y="240" width="200" height="60" rx="8"/><text class="fig-mono" x="250" y="277" text-anchor="middle">foo.o</text>
<path class="fig-arrow" marker-end="url(#lt)" d="M250,302 L250,348"/><text class="fig-small" x="360" y="330" text-anchor="start">ld / lld</text>
<rect class="fig-box world" x="150" y="350" width="200" height="60" rx="8"/><text class="fig-mono" x="250" y="387" text-anchor="middle">a.out</text>
</svg>
</div>

---

## ELF

Executable and Linkable Format. A structured file, not a raw stream of instructions.

<div class="figure">
<svg viewBox="0 0 520 390" style="max-width:520px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<rect class="fig-box ctx" x="40" y="15" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="42" text-anchor="middle">ELF header</text>
<rect class="fig-box ctx" x="40" y="60" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="87" text-anchor="middle">program headers</text>
<rect class="fig-box model" x="40" y="105" width="440" height="45" rx="6"/><text class="fig-mono" x="260" y="134" text-anchor="middle">.text</text>
<rect class="fig-box ctx" x="40" y="155" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="182" text-anchor="middle">.rodata</text>
<rect class="fig-box ctx" x="40" y="200" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="227" text-anchor="middle">.data / .bss</text>
<rect class="fig-box ctx" x="40" y="245" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="272" text-anchor="middle">symbol table</text>
<rect class="fig-box ctx" x="40" y="290" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="317" text-anchor="middle">relocations</text>
<rect class="fig-box ctx" x="40" y="335" width="440" height="40" rx="6"/><text class="fig-mono" x="260" y="362" text-anchor="middle">section headers</text>
</svg>
</div>

---

## Sections

| section | holds |
|---|---|
| `.text` | executable code |
| `.rodata` | read-only constants |
| `.data` | initialized writable data |
| `.bss` | zero-initialized storage |

A useful simplified model. Not every binary has every section.

---

## Symbols

A symbol table maps names to addresses. The linker and the debugger use it. The CPU never does.

<div class="two-col">
<div class="col-left">

```text
$ nm program
0000000000401230 T authenticate
0000000000404020 D banner
                 U fgets@GLIBC_2.2.5
0000000000401136 T main
                 U printf@GLIBC_2.2.5
                 U puts@GLIBC_2.2.5
```

`T` code in `.text` · `D` data · `U` undefined, imported from a library

</div>
<div class="col-right">

<div class="fragment">

```text
$ strip program
$ nm program
nm: program: no symbols
```

</div>

<div class="fragment">

```text
$ nm -D program
                 U fgets@GLIBC_2.2.5
                 U printf@GLIBC_2.2.5
                 U puts@GLIBC_2.2.5
```

Externally-referenced symbols are left alone, because the loader needs them at runtime.

</div>

</div>
</div>

<div class="fragment">

```text
authenticate  →  FUN_00401230        main  →  FUN_00401136
```

Notice: even though the semantics is unchanged, the names are gone.
</div>

---

## Linux tools

```bash
file program        # what kind of file
readelf -h program  # ELF header
nm program          # symbols
strings program     # printable strings
objdump -d program  # disassembly
```

---

## file and strings

<div class="two-col">
<div class="col-left">

```text
$ file program
program: ELF 64-bit LSB executable,
x86-64, dynamically linked,
stripped
```

</div>
<div class="col-right">

```text
$ strings program
Password:
Access granted
Access denied
```

</div>
</div>

Strings are evidence, not proof.

---

## Cross-references

<div class="figure">
<svg viewBox="0 0 900 260" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="xr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#f76900"/></marker></defs>
<rect class="fig-box ctx" x="300" y="20" width="300" height="55" rx="8"/><text class="fig-mono" x="450" y="53" text-anchor="middle">"Access granted"</text>
<path class="fig-arrow model" marker-end="url(#xr)" d="M450,77 L450,125"/><text class="fig-small" x="470" y="105" text-anchor="start">referenced by</text>
<rect class="fig-box model" x="280" y="130" width="340" height="55" rx="8"/><text class="fig-mono" x="450" y="163" text-anchor="middle">function at 0x401230</text>
</svg>
</div>

A string points back to the code that uses it. These back-pointers are **xrefs**.

---

## Same CPU, different ecosystem

Both run the same x86-64 instructions. Everything around them differs.

| | **Linux** | **Windows** |
|---|---|---|
| compiler | `gcc` / `clang` | MSVC `cl.exe` |
| executable | ELF | PE |
| shared library | `libfoo.so` | `foo.dll` |
| calling convention | System V: `rdi rsi rdx rcx r8 r9` | Microsoft x64: `rcx rdx r8 r9` + shadow space |
| C++ symbol for `foo(int)` | `_Z3fooi` | `?foo@@YAXH@Z` |
| debug info | DWARF, inside the binary | PDB, separate file |
| system calls | through `libc`, numbers stable | through `kernel32` → `ntdll`, numbers change per build |

Reverse engineering includes the file format and toolchain, not only the instruction set. A disassembler has to know which world it is in before it can find the entry point, name the arguments, or resolve a call.

---

## Windows toolchain and PE

<div class="two-col">
<div class="col-left">

<div class="figure">
<svg viewBox="0 0 560 280" style="max-width:460px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="pe-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="20" y="12" width="200" height="50" rx="8"/><text class="fig-mono" x="120" y="44" text-anchor="middle">foo.cpp</text>
<path class="fig-arrow" marker-end="url(#pe-arr)" d="M120,64 L120,106"/><text class="fig-small" x="135" y="90" text-anchor="start">cl.exe</text>
<rect class="fig-box ctx" x="20" y="108" width="200" height="50" rx="8"/><text class="fig-mono" x="120" y="140" text-anchor="middle">foo.obj</text>
<path class="fig-arrow" marker-end="url(#pe-arr)" d="M120,160 L120,202"/><text class="fig-small" x="135" y="178" text-anchor="start">link.exe</text>
<path class="fig-arrow" marker-end="url(#pe-arr)" d="M120,190 L430,190 L430,202"/><text class="fig-small" x="290" y="184" text-anchor="middle">/DEBUG</text>
<rect class="fig-box world" x="20" y="204" width="200" height="50" rx="8"/><text class="fig-mono" x="120" y="236" text-anchor="middle">foo.exe</text>
<rect class="fig-box ctx" x="330" y="204" width="200" height="50" rx="8" stroke-dasharray="6 4"/><text class="fig-mono" x="430" y="236" text-anchor="middle">foo.pdb</text>
<text class="fig-small" x="430" y="274" text-anchor="middle">symbols and types, kept by the vendor</text>
</svg>
</div>

`cl.exe` compiles straight to `.obj`. Symbols and types go to a separate `.pdb`, not into the executable.

</div>
<div class="col-right">

<div class="figure">
<svg viewBox="0 0 620 290" style="max-width:460px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<rect class="fig-box ctx" x="20" y="8" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="29" text-anchor="middle">DOS header (MZ)</text>
<rect class="fig-box ctx" x="20" y="42" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="63" text-anchor="middle">PE + optional header</text><text class="fig-small" x="285" y="62" text-anchor="start">entry point, image base</text>
<rect class="fig-box ctx" x="20" y="76" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="97" text-anchor="middle">section table</text>
<rect class="fig-box model" x="20" y="110" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="131" text-anchor="middle">.text</text><text class="fig-small" x="285" y="130" text-anchor="start">code</text>
<rect class="fig-box ctx" x="20" y="144" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="165" text-anchor="middle">.rdata</text><text class="fig-small" x="285" y="164" text-anchor="start">constants, imports, exports, PDB path</text>
<rect class="fig-box ctx" x="20" y="178" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="199" text-anchor="middle">.data</text><text class="fig-small" x="285" y="198" text-anchor="start">writable globals</text>
<rect class="fig-box ctx" x="20" y="212" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="233" text-anchor="middle">.rsrc</text><text class="fig-small" x="285" y="232" text-anchor="start">icons, dialogs, version info</text>
<rect class="fig-box ctx" x="20" y="246" width="250" height="30" rx="6"/><text class="fig-mono" x="145" y="267" text-anchor="middle">.reloc</text><text class="fig-small" x="285" y="266" text-anchor="start">fixups when not at image base</text>
</svg>
</div>

Same shape as ELF: headers, then sections. `.rdata` is `.rodata`; `.rsrc` has no ELF counterpart.

</div>
</div>

- **No symbol table.** A shipped `.exe` names only its imports and exports; the rest is `FUN_140001230` until you find the `.pdb`.
- **PDBs rarely ship.** Microsoft publishes them for Windows itself; third parties do not, but the debug directory still leaks the `.pdb` path.
- **Resources are data.** `.rsrc` holds icons and version info, and in malware often the payload itself.

---

## Imports: which APIs a program can call

<div class="two-col">
<div class="col-left">

```text
$ dumpbin /imports program.exe
  KERNEL32.dll
    CreateFileW
    ReadFile
    VirtualAlloc
    VirtualProtect
  WS2_32.dll
    connect
    send
```

</div>
<div class="col-right">

Reads a file, allocates memory and marks it executable, opens a socket.

Loader that decrypts a payload? Downloader? Auto-updater?

</div>
</div>

An import only says the code *can* call it. Follow the **xrefs** to see where it does, and with what arguments.

A binary that resolves functions at run time with `GetProcAddress` shows almost nothing here.

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 3</span>

# Disassembly and decompilation

---

## Disassembly

<div class="two-col">
<div class="col-left">

```text
401130: 55
401131: 48 89 e5
401134: 48 83 ec 28
401138: 48 8b 45 f8
        ...
401166: c9
401167: c3
```

</div>
<div class="col-right">

```asm
push rbp
mov  rbp, rsp
sub  rsp, 0x28
mov  rax, [rbp-8]
...
leave
ret
```

</div>
</div>

Machine code back to assembly instructions.

- a **disassembler** decodes bytes into instructions using the ISA's encoding tables
- the output is a listing: address, bytes, mnemonic, operands
- `objdump -d`, Ghidra, IDA, and radare2 all produce one
- each instruction decodes exactly, _if_ you start on the right byte

---

## Why disassembly is hard

- where do instructions begin?
- code or data?
- indirect jumps and calls
- architecture-specific encoding
- stripped metadata

x86 instructions vary in length, so a wrong start decodes into garbage.

---

## Functions are reconstructed

A stripped binary has no list of functions. The tool has to infer them.

<div class="two-col">
<div class="col-left">

**Evidence it uses**

```asm
call 0x401130       ; a call target...

0x401130:
push rbp            ; ...with a prologue
mov  rbp, rsp
...
ret                 ; ...ending in ret
```

- also: the entry point, `.eh_frame`, symbols if any survived

</div>
<div class="col-right">

**Where it goes wrong**

- reached only through a function pointer: never found
- `call exit` never returns: the next function gets merged in
- tail call `jmp f`: boundary lands in the wrong place
- hot/cold splitting: one function in two pieces

</div>
</div>

`FUN_00401130` just means "starts at 0x401130": the name, the arguments, and the return type are all guesses.

---

## Decompilation

<div class="two-col">
<div class="col-left">

```asm
imul   edi, edi
mov    eax, esi
cmp    edi, esi
cmovle eax, edi
ret
```

</div>
<div class="col-right">

```c
int FUN_00401130(int param_1, int param_2)
{
  int iVar1 = param_1 * param_1;
  if (param_2 < iVar1) {
    iVar1 = param_2;
  }
  return iVar1;
}
```

</div>
</div>

Assembly back to something that reads like source.

- a **decompiler** takes the disassembly and rebuilds expressions, variables, and control flow
- the output is pseudo-C: meant to be read, not recompiled
- Ghidra, IDA (Hex-Rays), Binary Ninja, and angr all ship one
- this is `clamp_square` from the compilation section: the names and types are gone, so the tool invents `param_1` and `iVar1`

---

## Disassembly is not decompilation

<div class="two-col">
<div class="col-left">

**Disassembly**

```text
bytes → instructions
```

- decoding: a table lookup on the ISA's encoding
- exact, if you start on the right byte
- one line per instruction, as long as the code
- says what the CPU does, not why
- `objdump -d` is enough

</div>
<div class="col-right">

**Decompilation**

```text
instructions → structure
```

- analysis: dataflow, type inference, control-flow structuring
- recovers variables, expressions, conditions, loops, parameters, types
- one line can stand in for twenty instructions
- says what the program _means_, as the tool understands it
- needs a real engine: Ghidra, Hex-Rays, Binary Ninja

</div>
</div>

Read the pseudo-C for the shape of the program. Drop to the disassembly when the shape looks wrong.

---

## Decompiler output is a hypothesis

<div class="two-col">
<div class="col-left">

**What was written**

```c
bool ok = authenticate(input);
if (!ok)
    reject();
```

</div>
<div class="col-right">

**What the tool recovered**

```c
iVar1 = FUN_00401230(param_1);
if (iVar1 == 0)
    FUN_00401180();
```

</div>
</div>

<div class="callout good">Same behavior, none of the meaning. Names, types, and control-flow are essentially the heuristic's "best guess." Sometimes the decompiler will get them wrong and they will need to be fixed by the user.</div>

Note:
The decompiler reconstructs a plausible program with the same behavior. It does not recover the source. Names, types, and structure are guesses. This is the conceptual center of the lecture.

---

## Binary-analysis IRs

<div class="two-col">
<div class="col-left">

**What it has to do**

- one representation for x86-64, ARM, MIPS, …
- spell out implicit effects: flags, `push` moving `rsp`
- keep machine semantics: bit widths, wraparound, flat memory
- keep addresses: every op maps back to an instruction
- assume nothing the lifter does not know

</div>
<div class="col-right">

**Examples**

- Ghidra P-code
- angr VEX (from Valgrind)
- Binary Ninja LLIL / MLIL / HLIL
- IDA microcode

Verbose by design: one `cmp` becomes five P-code ops.

</div>
</div>

Analysis is easier over one normalized IR than over every machine ISA. The question is what that IR may assume.

---

## Why not just LLVM IR?

McSema and RetDec lift into it, and every LLVM tool comes for free. So why doesn't every tool?

<div class="two-col">
<div class="col-left">

**LLVM IR records what the front end knew**

- every value has a type: `i32`, `i1`, `ptr`
- SSA over unlimited virtual registers
- functions with a declared signature
- locals are `alloca`s; there is no stack pointer
- no flags, no hidden side effects

</div>
<div class="col-right">

**The lifter knows none of it**

- `rax` holds 64 bits: integer, pointer, or two `int`s packed?
- 16 registers reused constantly: which write reaches this read?
- function boundaries and argument counts are reconstructed
- the stack is arithmetic on `rsp`
- flags *are* the control flow: `cmp`, then `jg`

</div>
</div>

Every property that makes LLVM IR nice to analyze is a fact the compiler had and the lifter has to guess. Lifting to LLVM means guessing first and analyzing second.

---

## Compiler IR vs. binary IR

| | LLVM IR | VEX, P-code, LLIL |
|---|---|---|
| built for | source → machine | machine → analysis |
| types, variables | given by the front end | recovered later, or never |
| functions | declared signature | reconstructed boundary, inferred calling convention |
| flags, side effects | abstracted away | every one written down |
| semantics | C's: overflow and bad pointers are *undefined* | the CPU's: everything is defined |
| addresses | gone | kept on every op |
| reuse | KLEE, sanitizers, every `opt` pass | that tool's own analyses |


---

## When lifting to LLVM pays off

<div class="two-col">
<div class="col-left">

**You gain the ecosystem**

- KLEE: symbolic execution of the binary
- sanitizers and fuzzing instrumentation on code you never had source for
- `llc` again: recompile for another CPU, or with hardening added

McSema / remill, RetDec and rev.ng do exactly this.

</div>
<div class="col-right">

**You pay in guesses**

- types, variables, stack frames and function signatures are fixed *before* analysis starts
- a wrong guess is now a wrong program, and nothing downstream will notice
- LLVM's optimizer follows C's rules, not the CPU's: the lifter has to fence off any pass that could rewrite the bug it is hunting

</div>
</div>

Machine-level IRs go the other way: commit to nothing, then climb. Binary Ninja's LLIL → MLIL → HLIL and Ghidra's raw → high P-code are that climb, one hypothesis at a time.

---

## Lifting

<div class="figure">
<svg viewBox="0 0 500 360" style="max-width:400px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="lf" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box world" x="110" y="20" width="280" height="60" rx="8"/><text class="fig-mono" x="250" y="57" text-anchor="middle">machine instructions</text>
<path class="fig-arrow" marker-end="url(#lf)" d="M250,82 L250,138"/>
<rect class="fig-box model" x="110" y="140" width="280" height="60" rx="8"/><text class="fig-title" x="250" y="177" text-anchor="middle">IR</text>
<path class="fig-arrow" marker-end="url(#lf)" d="M250,202 L250,258"/>
<rect class="fig-box ctx" x="110" y="260" width="280" height="60" rx="8"/><text class="fig-mono" x="250" y="297" text-anchor="middle">program analysis</text>
</svg>
</div>

Translate machine instructions into an analysis-friendly IR. This is what angr does before reasoning.

---

## Ghidra

<div class="two-col">
<div class="col-left">

- NSA's reverse-engineering framework. Open source since 2019. Java; runs anywhere.
- loads ELF, PE, Mach-O, raw firmware images
- processors via SLEIGH specs: x86, ARM, MIPS, PowerPC, RISC-V, AVR, 6502, …
- scripting in Java or Python; headless mode for batch runs

</div>
<div class="col-right">

<div class="figure">
<svg viewBox="0 0 560 300" xmlns="http://www.w3.org/2000/svg">
<rect class="fig-box ctx" x="10" y="10" width="130" height="280" rx="6"/><text class="fig-small" x="75" y="150" text-anchor="middle">symbol tree</text>
<rect class="fig-box ctx" x="150" y="10" width="200" height="280" rx="6"/><text class="fig-small" x="250" y="140" text-anchor="middle">listing</text><text class="fig-small" x="250" y="165" text-anchor="middle">(disassembly)</text>
<rect class="fig-box model" x="360" y="10" width="190" height="280" rx="6"/><text class="fig-small" x="455" y="140" text-anchor="middle">decompiler</text><text class="fig-small" x="455" y="165" text-anchor="middle">(pseudo-C)</text>
</svg>
</div>

Plus: function graph, strings, xrefs, data types.

</div>
</div>

---

## P-code

Ghidra's IR. Each machine instruction becomes a few P-code operations. Operands are **varnodes**: an address space, an offset, a size.

<div class="two-col">
<div class="col-left">

```text
cmp edi, esi
  CF = INT_LESS    edi, esi
  OF = INT_SBORROW edi, esi
  u1 = INT_SUB     edi, esi
  SF = INT_SLESS   u1, 0
  ZF = INT_EQUAL   u1, 0
```

</div>
<div class="col-right">

```text
jg .done
  u2 = INT_EQUAL ZF, 0
  u3 = INT_EQUAL SF, OF
  u4 = BOOL_AND  u2, u3
  CBRANCH .done, u4
```

</div>
</div>

Every side effect is written down. The SLEIGH spec for the processor says how.

---

## From P-code to pseudo-C

<div class="figure">
<svg viewBox="0 0 1200 190" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="pc" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box world" x="0" y="40" width="170" height="70" rx="10"/><text class="fig-title" x="85" y="83" text-anchor="middle">bytes</text>
<path class="fig-arrow" marker-end="url(#pc)" d="M175,75 L235,75"/><text class="fig-small" x="205" y="60" text-anchor="middle">SLEIGH</text>
<rect class="fig-box ctx" x="240" y="40" width="190" height="70" rx="10"/><text class="fig-title" x="335" y="83" text-anchor="middle">raw P-code</text>
<path class="fig-arrow" marker-end="url(#pc)" d="M435,75 L495,75"/>
<rect class="fig-box ctx" x="500" y="40" width="190" height="70" rx="10"/><text class="fig-title" x="595" y="83" text-anchor="middle">high P-code</text>
<path class="fig-arrow" marker-end="url(#pc)" d="M695,75 L755,75"/>
<rect class="fig-box ctx" x="760" y="40" width="190" height="70" rx="10"/><text class="fig-title" x="855" y="83" text-anchor="middle">structured</text>
<path class="fig-arrow" marker-end="url(#pc)" d="M955,75 L1015,75"/>
<rect class="fig-box model" x="1020" y="40" width="180" height="70" rx="10"/><text class="fig-title" x="1110" y="83" text-anchor="middle">pseudo-C</text>
<text class="fig-small" x="335" y="145" text-anchor="middle">one op per side effect</text>
<text class="fig-small" x="595" y="145" text-anchor="middle">SSA, dead flags removed,</text>
<text class="fig-small" x="595" y="168" text-anchor="middle">variables and types inferred</text>
<text class="fig-small" x="855" y="145" text-anchor="middle">if / while / switch</text>
<text class="fig-small" x="855" y="168" text-anchor="middle">recovered from the CFG</text>
<text class="fig-small" x="1110" y="145" text-anchor="middle">what you read</text>
</svg>
</div>

The decompiler is written once, against P-code. Add a processor spec and it decompiles that processor too.

---

## Ghidra and angr
- Both perform lifting before any analysis / transformation occurs.
  
| | Ghidra | angr |
|---|---|---|
| IR | P-code | VEX (from Valgrind) |
| built for | reading: decompile to C | reasoning: execute symbolically |
| written in | Java, C++ decompiler | Python |
| you drive it | GUI, or headless scripts | Python API |
| this course | this lecture, your first look at a binary | next week, with a solver |

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 4</span>

# Reverse engineering in practice

---

## First pass

<div class="two-col">
<div class="col-left">

- file type
- architecture
- strings
- imports
- symbols
- sections

</div>
<div class="col-right">

```bash
file program
readelf -h program
strings program
nm -D program
objdump -d program
```

</div>
</div>

Collect evidence before reading code.

---

## Follow the evidence

<div class="figure">
<svg viewBox="0 0 520 460" style="max-width:480px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="ev" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="130" y="10" width="260" height="55" rx="8"/><text class="fig-mono" x="260" y="43" text-anchor="middle">"Access granted"</text>
<path class="fig-arrow fragment" marker-end="url(#ev)" d="M260,67 L260,103"/>
<rect class="fig-box ctx fragment" x="130" y="105" width="260" height="55" rx="8"/><text class="fig-mono" x="260" y="138" text-anchor="middle">cross-reference</text>
<path class="fig-arrow fragment" marker-end="url(#ev)" d="M260,162 L260,198"/>
<rect class="fig-box model fragment" x="130" y="200" width="260" height="55" rx="8"/><text class="fig-mono" x="260" y="233" text-anchor="middle">function</text>
<path class="fig-arrow fragment" marker-end="url(#ev)" d="M260,257 L260,293"/>
<rect class="fig-box ctx fragment" x="130" y="295" width="260" height="55" rx="8"/><text class="fig-mono" x="260" y="328" text-anchor="middle">callers</text>
<path class="fig-arrow fragment" marker-end="url(#ev)" d="M260,352 L260,388"/>
<rect class="fig-box ctx fragment" x="130" y="390" width="260" height="55" rx="8"/><text class="fig-mono" x="260" y="423" text-anchor="middle">input validation</text>
</svg>
</div>

---

## Build hypotheses

1. Program prints `"Access granted"`.
2. Find code referencing that string.
3. Identify the preceding branch.
4. Determine what controls the branch.
5. Trace the input backward.

Reverse engineering is iterative hypothesis formation.

---

## Ghidra workflow

<div class="figure">
<svg viewBox="0 0 1100 220" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="gh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="15" y="85" width="130" height="55" rx="6"/><text class="fig-small" x="80" y="118" text-anchor="middle">binary</text>
<path class="fig-arrow" marker-end="url(#gh)" d="M148,112 L178,112"/>
<rect class="fig-box ctx" x="180" y="85" width="140" height="55" rx="6"/><text class="fig-small" x="250" y="118" text-anchor="middle">auto-analysis</text>
<path class="fig-arrow" marker-end="url(#gh)" d="M323,112 L353,112"/>
<rect class="fig-box ctx" x="355" y="85" width="140" height="55" rx="6"/><text class="fig-small" x="425" y="118" text-anchor="middle">functions</text>
<path class="fig-arrow" marker-end="url(#gh)" d="M498,112 L528,112"/>
<rect class="fig-box ctx" x="530" y="85" width="150" height="55" rx="6"/><text class="fig-small" x="605" y="118" text-anchor="middle">strings / xrefs</text>
<path class="fig-arrow" marker-end="url(#gh)" d="M683,112 L713,112"/>
<rect class="fig-box ctx" x="715" y="85" width="150" height="55" rx="6"/><text class="fig-small" x="790" y="118" text-anchor="middle">decompiler</text>
<path class="fig-arrow" marker-end="url(#gh)" d="M868,112 L898,112"/>
<rect class="fig-box model" x="900" y="85" width="180" height="55" rx="6"/><text class="fig-small" x="990" y="118" text-anchor="middle">rename / annotate</text>
</svg>
</div>

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 5</span>

# How to find vulnerabilities

---



## A memory-safety bug

```c
void copy(char *input) {
    char buf[16];
    strcpy(buf, input);   // input length unchecked
}
```

`strcpy` writes until a zero byte. `buf` holds 16.

---

## Bug is not exploit

<div class="figure">
<svg viewBox="0 0 1100 130" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="be" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box ctx" x="10" y="40" width="180" height="55" rx="8"/><text class="fig-small" x="100" y="73" text-anchor="middle">bug</text>
<path class="fig-arrow" marker-end="url(#be)" d="M193,67 L233,67"/>
<rect class="fig-box ctx" x="235" y="40" width="200" height="55" rx="8"/><text class="fig-small" x="335" y="73" text-anchor="middle">vulnerability</text>
<path class="fig-arrow" marker-end="url(#be)" d="M438,67 L478,67"/>
<rect class="fig-box ctx" x="480" y="40" width="260" height="55" rx="8"/><text class="fig-small" x="610" y="73" text-anchor="middle">exploitable vuln</text>
<path class="fig-arrow" marker-end="url(#be)" d="M743,67 L783,67"/>
<rect class="fig-box world" x="785" y="40" width="240" height="55" rx="8"/><text class="fig-small" x="905" y="73" text-anchor="middle">working exploit</text>
</svg>
</div>

- First we find a bug. Next we need to ask: is it a vulnerability?
  - Q: When is it a vulnerability? A: we could use the bug to do something bad
- Next: is it an **exploitable** vulnerability? 
  - Some vulnerabilities may be in parts of the code we can't possibly influence / control
  - Need to be able to **effect** the bug in practice
- Last, we need a _proof of concept_ (**POC**) that demonstrates the exploit is viable
  - Often POC is not very "real," but just demonstrates the _potential_ for the exploit
- AI now great at _all_ of these stages

---

## Can we automate this

<div class="figure">
<svg viewBox="0 0 560 465" style="max-width:520px;width:100%;height:auto;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="au" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#0f2a4a"/></marker></defs>
<rect class="fig-box world" x="150" y="15" width="260" height="55" rx="8"/><text class="fig-mono" x="280" y="48" text-anchor="middle">binary</text>
<path class="fig-arrow" marker-end="url(#au)" d="M280,72 L280,108"/>
<rect class="fig-box ctx" x="110" y="110" width="340" height="55" rx="8"/><text class="fig-small" x="280" y="143" text-anchor="middle">recover program structure</text>
<path class="fig-arrow" marker-end="url(#au)" d="M280,167 L280,203"/>
<rect class="fig-box ctx" x="110" y="205" width="340" height="55" rx="8"/><text class="fig-small" x="280" y="238" text-anchor="middle">reason about execution</text>
<path class="fig-arrow" marker-end="url(#au)" d="M280,262 L280,298"/>
<rect class="fig-box ctx" x="110" y="300" width="340" height="55" rx="8"/><text class="fig-small" x="280" y="333" text-anchor="middle">find dangerous behavior</text>
<path class="fig-arrow" marker-end="url(#au)" d="M280,357 L280,393"/>
<rect class="fig-box model" x="110" y="395" width="340" height="55" rx="8"/><text class="fig-small" x="280" y="428" text-anchor="middle">find an input that reaches it</text>
</svg>
</div>

---

<!-- .slide: class="section-divider" -->
<span class="chapter-num">Part 6</span>

# Where AI comes in
## The reverse-engineering problems this course will study

---

## Problems we will study

<div class="two-col">
<div class="col-left">

**Recovering what the compiler erased**

- **neural decompilation**: source that reads well and compiles again, a promise Ghidra's pseudo-C never made
- **identifier naming**: `iVar1` → `bytes_read`, `FUN_00401230` → `authenticate`
- **type recovery**: `undefined8` → `struct packet *`
- **function boundaries and disassembly** on stripped, optimized code

</div>
<div class="col-right">

**Matching and hunting**

- **binary similarity**: is this function the same as that one, across compilers, flags, and architectures?
- **library and version identification**: which OpenSSL is statically linked in here?
- **malware classification**: family, lineage, and behavior
- **vulnerability discovery**: models and agents that read binaries and find bugs
- **agents driving Ghidra and angr**: today's tools, operated by a model

</div>
</div>

Each one is a guess about what the compiler was given.

---


## What makes it hard

- **No single right answer.** Is `n_bytes` wrong when the source said `len`? Recompilable is not the same as correct.
- **Distribution shift.** Trained on `gcc -O0`, tested on `clang -O3`, another architecture, or an obfuscated binary.
- **Fluency is not faithfulness.** A model will write clean, confident pseudo-C for code that does something else.
- **Evaluation is unsettled.** Exact match, recompilation, re-execution, human study: each measures something different.
- **Adversaries adapt.** Malware authors obfuscate to defeat similarity, and a model can be fooled on purpose.
- **Binaries do not fit in a window.** Thousands of functions, and the model reads one at a time.

---

## Next: reasoning about binaries

- symbolic execution
- path constraints
- SMT
- automatic exploit generation
- MAYHEM, angr
- return-oriented programming

<div class="callout note">Can a machine solve for an input that reaches a bug?</div>

<div class="footer">cis400 &bull; cybersecurity &amp; ai</div>