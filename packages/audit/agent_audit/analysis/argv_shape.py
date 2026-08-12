"""Does a subprocess call name its own program?

Issue #8, problem 4: `subprocess.run(cmd, capture_output=True)` where two lines above

    cmd = ["docker", "run", "--rm", "-v", f"{workdir}:/work", image]

was reported as a command-execution risk, with a taint flow claiming `cmd` reached a
`shell_execution` sink from `user_input`. Nothing a caller supplies can change *which*
binary runs there. Only its arguments can move, and argument injection is a different and
lesser thing than command injection.

The distinction is structural and therefore checkable:

  * the argv is a list or tuple literal, so the elements are visible in the source;
  * its first element is a string constant, so the program is named here;
  * that program is not itself an interpreter that re-reads its argument as a command;
  * and `shell=True` is absent, which would hand the whole thing to a shell anyway.

**What this does not decide.** `["pip", "install", package]` satisfies every clause above
and is a genuine supply-chain finding; `["docker", "run", ..., image]` satisfies them too
and is the reporter's false positive. They are structurally identical and differ only in
what the named program does with its argument — which is semantics this analyser does not
have. So callers use this to *reduce* confidence, never to decide truth, and the residual
is recorded in CAPABILITY_BOUNDARIES.md rather than hidden behind a list of program names
someone would have to keep current.

Lives in one module because two call sites need it — `taint_tracker.SinkReachabilityChecker`
and `python_scanner._check_subprocess_expanded` — and two copies of one predicate is the
defect this repository keeps rediscovering.
"""

from __future__ import annotations

import ast
from typing import List, Optional

# Programs that re-interpret an argument as a command, so naming them fixes nothing.
SHELL_INTERPRETERS = frozenset({
    'sh', 'bash', 'zsh', 'ksh', 'dash', 'csh', 'tcsh', 'fish',
    'cmd', 'cmd.exe', 'powershell', 'powershell.exe', 'pwsh', 'pwsh.exe',
    'python', 'python2', 'python3', 'node', 'deno', 'bun', 'perl', 'ruby', 'php',
    'env', 'eval', 'xargs', 'ssh', 'sudo', 'nohup', 'timeout', 'nice', 'setsid',
})

SUBPROCESS_FUNCTIONS = frozenset({'run', 'Popen', 'call', 'check_output', 'check_call'})


def _literal_sequence(expr: ast.expr, scope: Optional[ast.AST]) -> Optional[List[ast.expr]]:
    """The elements of a list/tuple literal, following at most one assignment in `scope`.

    One level only, and deliberately: chasing further would need the reaching-definition
    analysis this scanner does not have, and a wrong answer here suppresses a finding.
    """
    if isinstance(expr, (ast.List, ast.Tuple)):
        return list(expr.elts)
    if isinstance(expr, ast.Name) and scope is not None:
        assigned: Optional[List[ast.expr]] = None
        for stmt in ast.walk(scope):
            if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, (ast.List, ast.Tuple)):
                continue
            if any(isinstance(t, ast.Name) and t.id == expr.id for t in stmt.targets):
                if assigned is not None:
                    # Reassigned more than once: which literal reaches the call is a
                    # question this pass cannot answer, so it declines to.
                    return None
                assigned = list(stmt.value.elts)
        return assigned
    return None


def has_shell_true(node: ast.Call) -> bool:
    return any(
        kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True
        for kw in node.keywords
    )


def is_fixed_program_argv(
    node: ast.Call,
    func_name: str,
    scope: Optional[ast.AST] = None,
) -> bool:
    """True when this subprocess call names its own, non-interpreter program.

    `scope` is the function body to search for the argv assignment; pass None to accept
    only a literal written at the call site.
    """
    simple = func_name.split('.')[-1]
    if simple not in SUBPROCESS_FUNCTIONS:
        return False

    if has_shell_true(node):
        return False

    if not node.args:
        return False

    argv = _literal_sequence(node.args[0], scope)
    if not argv:
        return False

    program = argv[0]
    if not (isinstance(program, ast.Constant) and isinstance(program.value, str)):
        return False

    basename = program.value.strip().replace('\\', '/').split('/')[-1].lower()
    return basename not in SHELL_INTERPRETERS
