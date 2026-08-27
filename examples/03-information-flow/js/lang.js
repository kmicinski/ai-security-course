// WHILE-with-output: the tiny imperative language the challenges are written in.
//
//   stmt  := ident '=' expr ';'
//          | 'if' '(' expr ')' block ('else' block)?
//          | 'while' '(' expr ')' block
//          | 'out' '(' expr ')' ';'
//          | 'skip' ';'
//   block := '{' stmt* '}'
//
// Values are integers; 0 is false, everything else true. The only builtin is
// digit(x, i) = the i-th base-10 digit of x, counting from the least
// significant. Comments run from '//' to end of line.
//
// The interpreter records a TRACE: the sequence of emitted values, each stamped
// with the abstract time at which it was emitted, plus whether the run halted.
// That trace is the only thing the observers in analysis.js get to look at.

export class ParseError extends Error {
  constructor(msg, line) {
    super(`line ${line}: ${msg}`);
    this.line = line;
  }
}

export class RuntimeError extends Error {
  constructor(msg, line) {
    super(`line ${line}: ${msg}`);
    this.line = line;
  }
}

// ---------------------------------------------------------------- tokenizer

const KEYWORDS = new Set(['if', 'else', 'while', 'out', 'skip']);
const PUNCT = [
  '&&', '||', '==', '!=', '<=', '>=',
  '=', '<', '>', '+', '-', '*', '/', '%', '!',
  '(', ')', '{', '}', ';', ',',
];

function tokenize(src) {
  const toks = [];
  let i = 0;
  let line = 1;
  while (i < src.length) {
    const c = src[i];
    if (c === '\n') { line++; i++; continue; }
    if (/\s/.test(c)) { i++; continue; }
    if (c === '/' && src[i + 1] === '/') {
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }
    if (/[0-9]/.test(c)) {
      let j = i;
      while (j < src.length && /[0-9]/.test(src[j])) j++;
      toks.push({ type: 'num', value: Number(src.slice(i, j)), line });
      i = j;
      continue;
    }
    if (/[A-Za-z_]/.test(c)) {
      let j = i;
      while (j < src.length && /[A-Za-z0-9_]/.test(src[j])) j++;
      const word = src.slice(i, j);
      toks.push({ type: KEYWORDS.has(word) ? word : 'ident', value: word, line });
      i = j;
      continue;
    }
    const p = PUNCT.find((op) => src.startsWith(op, i));
    if (!p) throw new ParseError(`unexpected character ${JSON.stringify(c)}`, line);
    toks.push({ type: p, value: p, line });
    i += p.length;
  }
  toks.push({ type: 'eof', value: null, line });
  return toks;
}

// ------------------------------------------------------------------- parser

class Parser {
  constructor(toks) {
    this.toks = toks;
    this.pos = 0;
  }

  peek(k = 0) { return this.toks[this.pos + k]; }
  next() { return this.toks[this.pos++]; }

  expect(type) {
    const t = this.peek();
    if (t.type !== type) {
      throw new ParseError(`expected '${type}' but found '${t.value ?? 'end of input'}'`, t.line);
    }
    return this.next();
  }

  parseProgram() {
    const body = [];
    while (this.peek().type !== 'eof') body.push(this.parseStmt());
    return { kind: 'seq', body, line: 1 };
  }

  parseBlock() {
    const open = this.expect('{');
    const body = [];
    while (this.peek().type !== '}') {
      if (this.peek().type === 'eof') throw new ParseError('unclosed block', open.line);
      body.push(this.parseStmt());
    }
    this.expect('}');
    return { kind: 'seq', body, line: open.line };
  }

  parseStmt() {
    const t = this.peek();
    switch (t.type) {
      case 'skip':
        this.next();
        this.expect(';');
        return { kind: 'skip', line: t.line };
      case 'out': {
        this.next();
        this.expect('(');
        const expr = this.parseExpr();
        this.expect(')');
        this.expect(';');
        return { kind: 'out', expr, line: t.line };
      }
      case 'if': {
        this.next();
        this.expect('(');
        const guard = this.parseExpr();
        this.expect(')');
        const then = this.parseBlock();
        let alt = null;
        if (this.peek().type === 'else') {
          this.next();
          alt = this.peek().type === 'if'
            ? { kind: 'seq', body: [this.parseStmt()], line: this.peek().line }
            : this.parseBlock();
        }
        return { kind: 'if', guard, then, alt, line: t.line };
      }
      case 'while': {
        this.next();
        this.expect('(');
        const guard = this.parseExpr();
        this.expect(')');
        const body = this.parseBlock();
        return { kind: 'while', guard, body, line: t.line };
      }
      case 'ident': {
        this.next();
        this.expect('=');
        const expr = this.parseExpr();
        this.expect(';');
        return { kind: 'assign', name: t.value, expr, line: t.line };
      }
      default:
        throw new ParseError(`unexpected '${t.value ?? 'end of input'}' at the start of a statement`, t.line);
    }
  }

  // precedence climbing, loosest first
  parseExpr() { return this.parseBinary(0); }

  parseBinary(level) {
    const LEVELS = [
      ['||'],
      ['&&'],
      ['==', '!='],
      ['<', '<=', '>', '>='],
      ['+', '-'],
      ['*', '/', '%'],
    ];
    if (level >= LEVELS.length) return this.parseUnary();
    let left = this.parseBinary(level + 1);
    while (LEVELS[level].includes(this.peek().type)) {
      const op = this.next();
      const right = this.parseBinary(level + 1);
      left = { kind: 'bin', op: op.type, left, right, line: op.line };
    }
    return left;
  }

  parseUnary() {
    const t = this.peek();
    if (t.type === '-' || t.type === '!') {
      this.next();
      return { kind: 'un', op: t.type, operand: this.parseUnary(), line: t.line };
    }
    return this.parsePrimary();
  }

  parsePrimary() {
    const t = this.next();
    if (t.type === 'num') return { kind: 'num', value: t.value, line: t.line };
    if (t.type === '(') {
      const e = this.parseExpr();
      this.expect(')');
      return e;
    }
    if (t.type === 'ident') {
      if (this.peek().type === '(') {
        this.next();
        const args = [];
        if (this.peek().type !== ')') {
          args.push(this.parseExpr());
          while (this.peek().type === ',') { this.next(); args.push(this.parseExpr()); }
        }
        this.expect(')');
        return { kind: 'call', name: t.value, args, line: t.line };
      }
      return { kind: 'var', name: t.value, line: t.line };
    }
    throw new ParseError(`unexpected '${t.value ?? 'end of input'}' in an expression`, t.line);
  }
}

export function parse(src) {
  return new Parser(tokenize(src)).parseProgram();
}

/** Every variable the program mentions, in source order of first mention. */
export function variablesOf(node, acc = []) {
  const add = (n) => { if (!acc.includes(n)) acc.push(n); };
  const walkE = (e) => {
    if (!e) return;
    if (e.kind === 'var') add(e.name);
    else if (e.kind === 'bin') { walkE(e.left); walkE(e.right); }
    else if (e.kind === 'un') walkE(e.operand);
    else if (e.kind === 'call') e.args.forEach(walkE);
  };
  const walkS = (s) => {
    if (!s) return;
    switch (s.kind) {
      case 'seq': s.body.forEach(walkS); break;
      case 'assign': add(s.name); walkE(s.expr); break;
      case 'out': walkE(s.expr); break;
      case 'if': walkE(s.guard); walkS(s.then); walkS(s.alt); break;
      case 'while': walkE(s.guard); walkS(s.body); break;
      default: break;
    }
  };
  walkS(node);
  return acc;
}

// -------------------------------------------------------------- interpreter

/**
 * The abstract cost model, stated once and used everywhere. Expression
 * evaluation is free; each *statement step* costs one tick:
 *
 *   assignment            1
 *   out                   1
 *   skip                  1
 *   if      (guard test)  1
 *   while   (each test)   1   -- including the final test that fails
 *
 * It is deliberately microarchitecture-free: no caches, no branch predictor, no
 * memory hierarchy. A real clock leaks strictly more than this one does.
 */
export const COST = { assign: 1, out: 1, skip: 1, ifTest: 1, whileTest: 1 };

class BudgetExceeded extends Error {}

/**
 * Run `prog` with the given initial store.
 * @returns {{outputs: {value:number,time:number}[], halted: boolean,
 *            time: number|null, store: Object, error: string|null}}
 *   `time` is the total tick count, or null if the run did not halt.
 */
export function run(prog, initial = {}, opts = {}) {
  const budget = opts.maxSteps ?? 20000;
  const store = new Map(Object.entries(initial));
  const outputs = [];
  let time = 0;
  let halted = true;
  let error = null;

  const tick = (n) => {
    time += n;
    if (time > budget) throw new BudgetExceeded();
  };

  const evalE = (e) => {
    switch (e.kind) {
      case 'num': return e.value;
      case 'var': {
        if (!store.has(e.name)) throw new RuntimeError(`variable '${e.name}' read before assignment`, e.line);
        return store.get(e.name);
      }
      case 'un': {
        const v = evalE(e.operand);
        return e.op === '-' ? -v : (v === 0 ? 1 : 0);
      }
      case 'bin': {
        if (e.op === '&&') return evalE(e.left) !== 0 && evalE(e.right) !== 0 ? 1 : 0;
        if (e.op === '||') return evalE(e.left) !== 0 || evalE(e.right) !== 0 ? 1 : 0;
        const a = evalE(e.left);
        const b = evalE(e.right);
        switch (e.op) {
          case '+': return a + b;
          case '-': return a - b;
          case '*': return a * b;
          case '/':
            if (b === 0) throw new RuntimeError('division by zero', e.line);
            return Math.trunc(a / b);
          case '%':
            if (b === 0) throw new RuntimeError('division by zero', e.line);
            return a % b;
          case '==': return a === b ? 1 : 0;
          case '!=': return a !== b ? 1 : 0;
          case '<': return a < b ? 1 : 0;
          case '<=': return a <= b ? 1 : 0;
          case '>': return a > b ? 1 : 0;
          case '>=': return a >= b ? 1 : 0;
          default: throw new RuntimeError(`unknown operator ${e.op}`, e.line);
        }
      }
      case 'call': {
        if (e.name !== 'digit') throw new RuntimeError(`unknown function '${e.name}'`, e.line);
        if (e.args.length !== 2) throw new RuntimeError('digit(x, i) takes two arguments', e.line);
        const x = Math.abs(evalE(e.args[0]));
        const i = evalE(e.args[1]);
        if (i < 0) throw new RuntimeError('digit index must be non-negative', e.line);
        return Math.floor(x / 10 ** i) % 10;
      }
      default:
        throw new RuntimeError(`unknown expression node ${e.kind}`, e.line);
    }
  };

  const exec = (s) => {
    switch (s.kind) {
      case 'seq':
        s.body.forEach(exec);
        return;
      case 'skip':
        tick(COST.skip);
        return;
      case 'assign': {
        const v = evalE(s.expr);
        tick(COST.assign);
        store.set(s.name, v);
        return;
      }
      case 'out': {
        const v = evalE(s.expr);
        tick(COST.out);
        outputs.push({ value: v, time });
        return;
      }
      case 'if': {
        const c = evalE(s.guard);
        tick(COST.ifTest);
        if (c !== 0) exec(s.then);
        else if (s.alt) exec(s.alt);
        return;
      }
      case 'while': {
        for (;;) {
          const c = evalE(s.guard);
          tick(COST.whileTest);
          if (c === 0) return;
          exec(s.body);
        }
      }
      default:
        throw new RuntimeError(`unknown statement node ${s.kind}`, s.line ?? 0);
    }
  };

  try {
    exec(prog);
  } catch (err) {
    if (err instanceof BudgetExceeded) {
      halted = false;
      time = null;
    } else if (err instanceof RuntimeError) {
      halted = false;
      time = null;
      error = err.message;
    } else {
      throw err;
    }
  }

  return { outputs, halted, time, store: Object.fromEntries(store), error };
}
