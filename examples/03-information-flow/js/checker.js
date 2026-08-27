// Denning's lattice checker, as given in lecture 2.
//
// Labels live in the two-point lattice L < H (bottom = public). Every variable
// carries a fixed declared label; the public channel `out` has label L. Each
// statement emits a constraint:
//
//   x = e          under pc   requires   label(e) ⊔ pc  ≤  label(x)
//   out(e)         under pc   requires   label(e) ⊔ pc  ≤  L
//   if (e) B1 B2              checks B1, B2 under  pc ⊔ label(e)
//   while (e) B               checks B      under  pc ⊔ label(e)
//
// where label(e) is the join of the labels of e's free variables. This is the
// standard flow-insensitive, pc-based discipline. It is sound for a
// TERMINATION-INSENSITIVE (batch) observer and nothing more: it says nothing
// about how long a branch runs or whether it returns, which is exactly the gap
// the timing and stream challenges walk through.

export const L = 'L';
export const H = 'H';

export const join = (a, b) => (a === H || b === H ? H : L);
export const flowsTo = (a, b) => a === L || b === H; // a ≤ b in {L < H}

/** Join of the labels of every variable occurring in an expression. */
export function labelOfExpr(e, gamma, defaultLabel = L) {
  switch (e.kind) {
    case 'num': return L;
    case 'var': return gamma[e.name] ?? defaultLabel;
    case 'un': return labelOfExpr(e.operand, gamma, defaultLabel);
    case 'bin': return join(labelOfExpr(e.left, gamma, defaultLabel), labelOfExpr(e.right, gamma, defaultLabel));
    case 'call': return e.args.reduce((acc, a) => join(acc, labelOfExpr(a, gamma, defaultLabel)), L);
    default: return L;
  }
}

/** Source text of an expression, for printing constraints back to the reader. */
export function exprToString(e) {
  switch (e.kind) {
    case 'num': return String(e.value);
    case 'var': return e.name;
    case 'un': return `${e.op}${exprToString(e.operand)}`;
    case 'bin': return `${exprToString(e.left)} ${e.op} ${exprToString(e.right)}`;
    case 'call': return `${e.name}(${e.args.map(exprToString).join(', ')})`;
    default: return '?';
  }
}

/**
 * Type-check a program against a label environment.
 * @returns {{accepted: boolean, constraints: Array, violations: Array}}
 *   each constraint: {line, stmt, source, pc, target, ok, why}
 */
export function check(prog, gamma, opts = {}) {
  const defaultLabel = opts.defaultLabel ?? L;
  const channel = opts.channelLabel ?? L;
  const constraints = [];

  const walk = (s, pc) => {
    switch (s.kind) {
      case 'seq':
        s.body.forEach((st) => walk(st, pc));
        return;
      case 'skip':
        return;
      case 'assign': {
        const src = labelOfExpr(s.expr, gamma, defaultLabel);
        const eff = join(src, pc);
        const target = gamma[s.name] ?? defaultLabel;
        constraints.push({
          line: s.line,
          stmt: `${s.name} = ${exprToString(s.expr)};`,
          source: src,
          pc,
          target,
          effective: eff,
          ok: flowsTo(eff, target),
          why: `label(${exprToString(s.expr)}) ⊔ pc = ${src} ⊔ ${pc} = ${eff} ≤ label(${s.name}) = ${target}`,
        });
        return;
      }
      case 'out': {
        const src = labelOfExpr(s.expr, gamma, defaultLabel);
        const eff = join(src, pc);
        constraints.push({
          line: s.line,
          stmt: `out(${exprToString(s.expr)});`,
          source: src,
          pc,
          target: channel,
          effective: eff,
          ok: flowsTo(eff, channel),
          why: `label(${exprToString(s.expr)}) ⊔ pc = ${src} ⊔ ${pc} = ${eff} ≤ label(out) = ${channel}`,
        });
        return;
      }
      case 'if': {
        const g = labelOfExpr(s.guard, gamma, defaultLabel);
        const pc2 = join(pc, g);
        constraints.push({
          line: s.line,
          stmt: `if (${exprToString(s.guard)})`,
          source: g,
          pc,
          target: null,
          effective: pc2,
          ok: true,
          raises: pc2 !== pc,
          why: `pc raised to pc ⊔ label(${exprToString(s.guard)}) = ${pc} ⊔ ${g} = ${pc2} inside the branches`,
        });
        walk(s.then, pc2);
        if (s.alt) walk(s.alt, pc2);
        return;
      }
      case 'while': {
        const g = labelOfExpr(s.guard, gamma, defaultLabel);
        const pc2 = join(pc, g);
        constraints.push({
          line: s.line,
          stmt: `while (${exprToString(s.guard)})`,
          source: g,
          pc,
          target: null,
          effective: pc2,
          ok: true,
          raises: pc2 !== pc,
          why: `pc raised to pc ⊔ label(${exprToString(s.guard)}) = ${pc} ⊔ ${g} = ${pc2} inside the body`,
        });
        walk(s.body, pc2);
        return;
      }
      default:
        return;
    }
  };

  walk(prog, L);
  const violations = constraints.filter((c) => !c.ok);
  return { accepted: violations.length === 0, constraints, violations };
}
