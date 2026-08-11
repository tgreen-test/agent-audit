// TestToolBoundaryGate shapes beyond `server.tool(...)`. AGENT-034 is scoped to tool
// entry points, so which constructs open a boundary is part of the detection surface,
// and a parsing change that stops recognising one silently drops every finding inside
// it.
import { z } from "zod";
import { tool } from "ai";
import { DynamicStructuredTool } from "@langchain/core/tools";
import express from "express";
import * as cp from "child_process";

// vercel-ai
export const vercelTool = tool({
  description: "run a task",
  parameters: z.object({ cmd: z.string() }),
  execute: async ({ cmd }) => {
    return cp.execSync(cmd).toString();
  },
});

// langchain-js
export const langchainTool = new DynamicStructuredTool({
  name: "run_task",
  description: "run a task",
  schema: z.object({ cmd: z.string() }),
  func: async ({ cmd }) => {
    return cp.execSync(cmd).toString();
  },
});

// express
const app = express();
app.post("/run", (req, res) => {
  const out = cp.execSync(req.body.cmd);
  res.send(out.toString());
});

// bare — outside any boundary, for contrast
export function bare(cmd: string) {
  return cp.execSync(cmd);
}
