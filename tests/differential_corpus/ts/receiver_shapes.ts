// Shapes drawn from the TypeScript scanner's own unit tests, because the first
// version of this corpus was not sensitive enough: the differential came back empty
// while `pytest tests/test_typescript_scanner.py` reported 40 failures on the same
// build. A differential that cannot see a regression is worse than none, so every
// class that moved is represented here.
//
// Mixed on purpose: some of these MUST be flagged and some MUST NOT, so a change of
// parsing path shows up in both directions of the symmetric difference.
import * as cp from "child_process";
import { exec, spawn, execSync } from "child_process";

// --- must be flagged: receiver aliases and bare destructured forms -------------
export function cpAlias(cmd: string) {
  return cp.exec(cmd);
}

export function bareDestructuredExec(cmd: string) {
  return exec(cmd);
}

export function bareSpawn(cmd: string, args: string[]) {
  return spawn(cmd, args);
}

export function bareExecSync(cmd: string) {
  return execSync(cmd);
}

// --- must be flagged: a variable program, however it is assembled --------------
export function templateInterpolation(userInput: string) {
  return cp.execSync(`ls -la ${userInput}`);
}

export function concatenation(userInput: string) {
  return cp.execSync("ls -la " + userInput);
}

export function spreadIntoVariableProgram(program: string, args: string[]) {
  return cp.spawn(program, [...args]);
}

export function bareIdentifierCommand(command: string) {
  return cp.exec(command);
}

export function shellTrueWithVariable(command: string) {
  return cp.spawn(command, { shell: true });
}

export function multilineCallWithVariableProgram(
  program: string,
  args: string[],
) {
  return cp.spawn(
    program,
    args,
  );
}

// --- must NOT be flagged: a fixed non-shell program has no injection surface ---
export function execaLiteralProgram(args: string[]) {
  return cp.spawn("git", args);
}

// --- must NOT be flagged: `.fetch` on a receiver is not the global fetch -------
export async function requestHandlerFetch(handler: { fetch: (u: string) => Promise<Response> }, url: string) {
  return handler.fetch(url);
}

export async function providerCallResultFetch(provider: { get: () => { fetch: (u: string) => Promise<Response> } }, url: string) {
  return provider.get().fetch(url);
}

export async function propertyChainFetch(a: { b: { fetch: (u: string) => Promise<Response> } }, url: string) {
  return a.b.fetch(url);
}

// --- must be flagged: the global fetch with a variable URL --------------------
export async function globalFetch(url: string) {
  return fetch(url);
}
