// NEGATIVE CONTROL. None of these is a code-execution sink. `.eval` on a client
// object is the Redis / DB scripting API, and v0.19.2 fixed a false positive here.
// A parsing path that flags any of these is worse than the one it replaces.
import Redis from "ioredis";

const redisClient = new Redis();

export async function runLua(luaScript: string, key: string) {
  return redisClient.eval(luaScript, 1, key);
}

export async function runLuaSha(sha: string, key: string) {
  return redisClient.evalsha(sha, 1, key);
}

export function templateEval(engine: { eval: (s: string) => string }, tpl: string) {
  return engine.eval(tpl);
}

export function deepMemberEval(a: { b: { eval: (s: string) => string } }, s: string) {
  return a.b.eval(s);
}

export function notAFunctionConstructor(registry: { Function: (s: string) => unknown }, s: string) {
  return registry.Function(s);
}
