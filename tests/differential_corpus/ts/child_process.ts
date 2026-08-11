// Differential input: the ts_child_process_exec family, both import shapes.
import * as child_process from "child_process";
import { exec, execSync, spawn, spawnSync } from "node:child_process";
import { execa, execaSync } from "execa";

export function viaNamespace(cmd: string) {
  return child_process.exec(cmd);
}

export function viaNamespaceSync(cmd: string) {
  return child_process.execSync(cmd);
}

export function viaNamespaceSpawn(cmd: string, args: string[]) {
  return child_process.spawn(cmd, args);
}

export function viaNamespaceSpawnSync(cmd: string, args: string[]) {
  return child_process.spawnSync(cmd, args);
}

export function viaDestructured(cmd: string) {
  return exec(cmd);
}

export function viaDestructuredSync(cmd: string) {
  return execSync(cmd);
}

export function viaDestructuredSpawn(cmd: string, args: string[]) {
  return spawn(cmd, args);
}

export function viaDestructuredSpawnSync(cmd: string, args: string[]) {
  return spawnSync(cmd, args);
}

export function viaExeca(cmd: string) {
  return execa(cmd);
}

export function viaExecaSync(cmd: string) {
  return execaSync(cmd);
}

export function literalOnly() {
  // Every argument is a literal — no injection surface.
  return child_process.execSync("git rev-parse HEAD");
}
