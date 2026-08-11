// Differential input: the ts_eval_exec family, bare (no tool entry point).
import * as vm from "vm";

export function runExpression(expr: string): unknown {
  return eval(expr);
}

export function runViaConstructor(body: string): unknown {
  const fn = new Function("ctx", body);
  return fn({});
}

export function runInSandbox(code: string): unknown {
  return vm.runInNewContext(code, {});
}

export function runInContext(code: string, ctx: object): unknown {
  return vm.runInContext(code, ctx);
}

export function runInThis(code: string): unknown {
  return vm.runInThisContext(code);
}

export function runViaWindow(expr: string): unknown {
  return window.eval(expr);
}

export function runViaGlobalThis(expr: string): unknown {
  return globalThis.eval(expr);
}

export function runViaGlobal(expr: string): unknown {
  return global.eval(expr);
}

export function runViaSelf(expr: string): unknown {
  return self.eval(expr);
}
