// The .js half. tree_sitter_javascript exposes language(), which the parser
// already recognises, so this half of the AST path activates today with the extra.
const vm = require("vm");

function runExpression(expr) {
  return eval(expr);
}

function runViaConstructor(body) {
  const fn = new Function("ctx", body);
  return fn({});
}

function runInSandbox(code) {
  return vm.runInNewContext(code, {});
}

function runViaGlobalThis(expr) {
  return globalThis.eval(expr);
}

// NEGATIVE CONTROL — member call on a client, not a code-execution sink.
function runLua(redisClient, luaScript, key) {
  return redisClient.eval(luaScript, 1, key);
}

module.exports = { runExpression, runViaConstructor, runInSandbox, runViaGlobalThis, runLua };
