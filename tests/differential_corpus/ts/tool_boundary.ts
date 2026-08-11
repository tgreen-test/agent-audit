// The same sinks inside an MCP tool entry point, where AGENT-034's boundary gate
// admits them. `server.tool(name, schema, handler)` is the highest-confidence
// boundary `detect_ts_tool_boundaries` recognises.
import { z } from "zod";
import * as child_process from "child_process";

server.tool("run_expression", { input: z.string() }, async ({ input }) => {
  const result = eval(input);
  return { content: [{ type: "text", text: String(result) }] };
});

server.tool("run_command", { cmd: z.string() }, async ({ cmd }) => {
  const out = child_process.execSync(cmd);
  return { content: [{ type: "text", text: out.toString() }] };
});

server.tool("run_sandboxed", { code: z.string() }, async ({ code }) => {
  const vm = await import("vm");
  return { content: [{ type: "text", text: String(vm.runInNewContext(code, {})) }] };
});
