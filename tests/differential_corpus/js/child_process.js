const child_process = require("child_process");
const { exec, execSync, spawn } = require("child_process");

function viaNamespace(cmd) {
  return child_process.exec(cmd);
}

function viaDestructured(cmd) {
  return execSync(cmd);
}

function viaSpawn(cmd, args) {
  return spawn(cmd, args);
}

function literalOnly() {
  return exec("git rev-parse HEAD");
}

module.exports = { viaNamespace, viaDestructured, viaSpawn, literalOnly };
