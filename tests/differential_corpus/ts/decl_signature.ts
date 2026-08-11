// NEGATIVE CONTROL. Declaration signatures, not calls. A type declaration named
// `eval` executes nothing.
export interface Evaluator {
  eval(args: string): string;
  exec(args: string): string;
}

export declare function eval(args: string): string;

export type EvalFn = (args: string) => string;

export abstract class BaseEvaluator {
  abstract eval(args: string): string;
}
