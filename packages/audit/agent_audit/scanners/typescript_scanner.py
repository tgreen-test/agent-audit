"""
TypeScript/JavaScript Security Scanner for AI Agent Code.

Detects dangerous patterns in TypeScript and JavaScript agent code:
- Code execution (eval, new Function, vm.runIn*)
- Shell execution (child_process.exec, execSync, spawn, execa)
- SQL injection via template strings
- Prompt injection via template strings
- SSRF via fetch/axios with dynamic URLs
- Unsafe deserialization (serialize-javascript, node-serialize)

Uses TreeSitterParser for AST analysis where available,
falls back to regex-based detection.

Maps findings to existing OWASP Agentic rule IDs:
- AGENT-034: Code/shell execution without input validation
- AGENT-041: SQL injection
- AGENT-010: Prompt injection
- AGENT-026: SSRF
- AGENT-049: Unsafe deserialization
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Sequence, Tuple

if TYPE_CHECKING:
    from agent_audit.parsers.treesitter_parser import FunctionCall, StringLiteral

from agent_audit.models.finding import (
    Finding,
    Remediation,
    confidence_to_tier,
)
from agent_audit.models.risk import Severity, Category, Location
from agent_audit.scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


# ============================================================================
# Dangerous call patterns for TypeScript/JavaScript
# Format: call_name -> (rule_id, pattern_type, base_confidence)
# ============================================================================

TS_DANGEROUS_CALLS: Dict[str, Tuple[str, str, float]] = {
    # Code execution
    "eval": ("AGENT-034", "ts_eval_exec", 0.95),
    "Function": ("AGENT-034", "ts_eval_exec", 0.90),
    "window.eval": ("AGENT-034", "ts_eval_exec", 0.95),
    "globalThis.eval": ("AGENT-034", "ts_eval_exec", 0.95),
    "global.eval": ("AGENT-034", "ts_eval_exec", 0.95),
    "self.eval": ("AGENT-034", "ts_eval_exec", 0.95),
    "vm.runInContext": ("AGENT-034", "ts_eval_exec", 0.90),
    "vm.runInNewContext": ("AGENT-034", "ts_eval_exec", 0.90),
    "vm.runInThisContext": ("AGENT-034", "ts_eval_exec", 0.90),
    # Shell execution
    "child_process.exec": ("AGENT-034", "ts_child_process_exec", 0.90),
    "child_process.execSync": ("AGENT-034", "ts_child_process_exec", 0.90),
    "child_process.spawn": ("AGENT-034", "ts_child_process_exec", 0.85),
    "child_process.spawnSync": ("AGENT-034", "ts_child_process_exec", 0.85),
    "execa": ("AGENT-034", "ts_child_process_exec", 0.85),
    "execaSync": ("AGENT-034", "ts_child_process_exec", 0.85),
    # SQL (only when template string used - checked separately)
    "query": ("AGENT-041", "ts_sql_template_injection", 0.75),
    "execute": ("AGENT-041", "ts_sql_template_injection", 0.75),
    "knex.raw": ("AGENT-041", "ts_sql_template_injection", 0.85),
    "prisma.$queryRaw": ("AGENT-041", "ts_sql_template_injection", 0.85),
    "prisma.$executeRaw": ("AGENT-041", "ts_sql_template_injection", 0.85),
    # Network requests (SSRF)
    "fetch": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "axios.get": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "axios.post": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "axios.put": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "axios.delete": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "axios.patch": ("AGENT-026", "ts_ssrf_fetch", 0.70),
    "http.request": ("AGENT-026", "ts_ssrf_fetch", 0.75),
    "https.request": ("AGENT-026", "ts_ssrf_fetch", 0.75),
}

# Dangerous-call names that must NOT match as member-expression suffixes.
# Rationale: `eval` and `Function` are JS global identifiers; when seen as
# `obj.eval(...)` or `obj.Function(...)` they're almost always unrelated
# member methods (e.g., Redis EVAL Lua via redisClient.eval). Real global
# eval through window/globalThis/global/self is enumerated explicitly in
# TS_DANGEROUS_CALLS above.
GLOBAL_ONLY_TS_CALLS: Set[str] = {"eval", "Function"}

# Receivers that plausibly denote the child_process module, for resolving
# `X.exec(...)` / `X.spawn(...)`.
#
# `exec` and `spawn` are the mirror image of the `eval` case above. `eval` is a
# global, so a member call is the suspicious form. exec/spawn are NOT globals —
# they only exist as members of child_process, or as bare names destructured
# out of it — so the member call is the *normal* form and the receiver is what
# distinguishes shell execution from an unrelated method that happens to share
# the name. `RegExp.prototype.exec` and the `.exec()` on virtually every SQL
# driver are the two that matter in practice; both are extremely common, and
# neither has anything to do with a shell.
#
# Matching is by receiver name rather than by import resolution because the
# regex path has no module graph. That is a deliberate under-approximation:
# an unusual alias (`import * as childProc`) is missed. Missing a true positive
# on an unusual alias is the safer error, and the alias list is cheap to extend.
CHILD_PROCESS_RECEIVERS: Set[str] = {
    "child_process",
    "childProcess",
    "child_proc",
    "childProc",
    "cp",
    "proc",
    "node:child_process",
}

_CP_RECEIVER_RE = "(?:" + "|".join(
    sorted((re.escape(r) for r in CHILD_PROCESS_RECEIVERS), key=len, reverse=True)
) + ")"
_CP_EXEC_NAMES = "(?:execSync|execFileSync|execFile|exec)"
_CP_SPAWN_NAMES = "(?:spawnSync|spawn)"


# A line that is only a comment. `//` and `*` (continuation of a block comment)
# were already skipped; `/*` and `/**` were not, so the opening line of every
# JSDoc block was scanned as code. On the audit target that reported prose —
# "the executable to spawn", "wrap `argv` so it executes confined" — as shell
# execution.
_TS_COMMENT_LINE_RE = re.compile(r"^\s*(?://|/\*|\*)")

# A TypeScript method or function *declaration*, as opposed to a call.
#
# `ts_decl_signature_re` already existed for this, scoped to `eval|Function`
# and to the return-type form alone. Widening it to every detected call name
# needs the shape to be pinned down properly, because `execFileSync('git',
# ['init'], { env })` is a call that superficially matches "identifier, parens,
# end of line".
#
# A declaration is recognised only when ALL of these hold:
#   * parentheses balance on the line — a call continued on the next line, e.g.
#     `spawn(process.execPath, [` , never balances, and neither does
#     `expect(execFileSync('git', [`
#   * nothing before the name that implies a value position: no `=` (so
#     `const child = spawn(...)` is out) and no `(` (so the name is the first
#     call-shaped token on the line)
#   * and one positive declaration marker: a return-type annotation after the
#     closing paren, a body-opening `{` at end of line, or a leading modifier
#     (`function`, `async`, `abstract`, `override`, `static`, `readonly`,
#     `declare`, `export`, or an access modifier).
_TS_DECL_MODIFIER_RE = re.compile(
    r"^(?:export\s+|declare\s+|abstract\s+|override\s+|async\s+|static\s+"
    r"|readonly\s+|private\s+|public\s+|protected\s+|function\s+)+"
)
_TS_DECL_RETURN_TYPE_RE = re.compile(r"\)\s*:\s*[^={]+$")


def _is_ts_declaration(line: str, match_start: int) -> bool:
    """Whether `line` is a declaration rather than a call at `match_start`."""
    stripped = line.strip()
    if stripped.count("(") != stripped.count(")"):
        return False

    before = line[:match_start]
    if "=" in before or "(" in before:
        return False

    if _TS_DECL_MODIFIER_RE.match(stripped):
        return True
    if _TS_DECL_RETURN_TYPE_RE.search(stripped):
        return True
    return stripped.endswith("{")


def _index_inside_string_literal(line: str, index: int) -> bool:
    """Whether `index` falls inside a *closed* string literal on this line.

    The audit target carries generated API-surface files whose entries are
    quoted source text — `signature: 'async spawn(owner: Agent, ...)'`,
    `declaration: 'export interface PtyBackend { spawn(spec) }'` — and test
    files that build a child script as a string before writing it out. The
    callee name appears inside a quotation there; the call it describes happens
    somewhere else, and reporting it at the quotation is reporting it twice or
    in the wrong file.

    Only *closed* spans count. An unterminated quote (a template literal
    continued on the next line) leaves the rest of the line unmarked, so the
    uncertain case stays a finding.
    """
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch in "\"'`":
            quote = ch
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == quote:
                    break
                j += 1
            if j >= n:
                return False  # unterminated: treat the remainder as code
            if i < index < j:
                return True
            i = j + 1
            continue
        i += 1
    return False


# The child_process entry points that do NOT go through a shell. `exec` and
# `execSync` are deliberately absent: they pass their argument to /bin/sh (or
# cmd.exe), which is the thing AGENT-034 is named after.
_NO_SHELL_CALL_RE = re.compile(
    r"(?<![\w.$])(?:execFileSync|execFile|spawnSync|spawn|execaSync|execa)\s*\("
)

# A first argument that fixes the executable: a string literal with no
# interpolation, or `process.execPath`, which is the path of the running Node
# binary and is not attacker-selectable.
_CONST_PROGRAM_RE = re.compile(
    r"""\(\s*(?:'([^']*)'|"([^"]*)"|`([^`${]*)`|process\.execPath)\s*,"""
)

# ...unless the fixed executable is itself a shell. `spawn('sh', ['-c', cmd])`
# has a constant program and is still shell command execution.
_SHELL_PROGRAMS = {
    "sh", "bash", "zsh", "ksh", "dash", "fish", "csh", "tcsh",
    "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "/bin/sh", "/bin/bash", "/bin/zsh", "/usr/bin/sh", "/usr/bin/bash",
    "/usr/bin/env",
}

_SHELL_OPTION_RE = re.compile(r"\bshell\s*:\s*(?:true|1)\b")


def _fixed_non_shell_program(line: str, open_paren: int) -> bool:
    """Whether this call runs a fixed, non-shell executable.

    AGENT-034 is "Shell Command Execution". The execFile/spawn family does not
    involve a shell at all, and when the program argument is a literal the
    executable cannot be chosen by an attacker either. What remains is argument
    injection against a known binary — a real but materially weaker class that
    this rule does not claim to detect and does not describe in its output.

    `_call_args_are_constant` already suppressed the case where *every*
    argument is a literal. That is far stricter than it needs to be: a spread,
    a `cwd` variable or a computed argv defeats it, so on the audit target it
    caught almost none of this shape. This predicate asks only about the
    program.

    Three things keep it from over-reaching:
      * `exec`/`execSync` are excluded — they do go through a shell
      * `shell: true` anywhere on the line keeps the finding
      * a program literal that names a shell keeps the finding, so
        `spawn('sh', ['-c', userCommand])` is untouched
    """
    if not _NO_SHELL_CALL_RE.match(line, 0) and not _NO_SHELL_CALL_RE.search(
        line, max(0, open_paren - 24), open_paren + 1
    ):
        return False
    if _SHELL_OPTION_RE.search(line):
        return False

    match = _CONST_PROGRAM_RE.match(line, open_paren)
    if match is None:
        return False

    program = next((g for g in match.groups() if g is not None), None)
    if program is None:
        return True  # process.execPath
    if program.strip().lower() in _SHELL_PROGRAMS:
        return False
    return bool(program.strip())


# js-yaml renamed `safeLoad` to `load` in v4 (2021): from v4 onward `load` uses
# DEFAULT_SCHEMA, which does not construct arbitrary JavaScript objects, and the
# unsafe entry point is `unsafeLoad` or an explicit full schema. In v3 `load`
# genuinely was the unsafe loader, which is why the pattern exists.
#
# So the finding depends on the declared dependency, not on the call alone. This
# resolves the nearest package.json above the file and suppresses the bare
# `yaml.load` finding only when a v4-or-later range is declared. No declaration,
# an unparseable range, or a range that admits v3 leaves the finding in place.
_JS_YAML_SAFE_MAJOR = 4
_YAML_LOAD_RE = re.compile(r"\byaml\.load\s*\(", re.IGNORECASE)
_YAML_UNSAFE_MARKERS_RE = re.compile(
    r"\bunsafeLoad\b|DEFAULT_FULL_SCHEMA|FULL_SCHEMA|JS_YAML_SCHEMA", re.IGNORECASE
)
_SEMVER_MAJOR_RE = re.compile(r"^\D*(\d+)")


def _declared_js_yaml_major(start: Path, _cache: Dict[str, Optional[int]] = {}) -> Optional[int]:
    """Lowest js-yaml major admitted by the nearest package.json above `start`.

    Returns None when nothing is declared or the range cannot be read, which
    means "keep reporting".
    """
    directory = start.parent if start.is_file() else start
    key = str(directory)
    if key in _cache:
        return _cache[key]

    result: Optional[int] = None
    for candidate in [directory, *directory.parents]:
        manifest = candidate / "package.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - unreadable manifest means "report"
            break
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            spec = (data.get(section) or {}).get("js-yaml")
            if not isinstance(spec, str):
                continue
            match = _SEMVER_MAJOR_RE.match(spec.strip())
            if match:
                result = int(match.group(1))
                break
        if result is not None:
            break
    _cache[key] = result
    return result


def _call_args_are_constant(line: str, open_paren: int) -> bool:
    """Whether the argument list starting at `open_paren` is entirely literal.

    A child_process call whose every argument is a literal has no injection
    surface: `execFileSync('git', ['rev-parse', '--show-toplevel'])` cannot be
    influenced by an attacker regardless of what happens to its output. On the
    audit target this shape — tooling shelling out to `git` with a fixed argv —
    accounted for the bulk of the surviving AGENT-034 findings.

    Conservative by construction. It answers False whenever it is unsure:
    an unterminated argument list (the call is wrapped across lines), a
    template literal containing `${...}`, string concatenation, a spread, or
    any bare identifier. Only string literals, numbers, booleans, null, plain
    array literals of those, and a trailing options object of those are
    accepted. Answering False means "report it", so every uncertain case stays
    a finding.

    Args:
        line: the source line
        open_paren: index of the call's opening parenthesis

    Returns:
        True only if the whole argument list was parsed and is constant.
    """
    if open_paren < 0 or open_paren >= len(line) or line[open_paren] != "(":
        return False

    # Walk to the matching close paren, tracking string state so that a paren
    # inside a literal does not end the scan.
    depth = 0
    quote = ""
    i = open_paren
    end = -1
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                end = i
                break
        i += 1

    if end < 0:
        return False  # unbalanced on this line — call spans lines, so report

    args = line[open_paren + 1:end]
    if not args.strip():
        return False  # no arguments at all is not this predicate's business

    # Any interpolation, concatenation or spread means non-constant.
    if "${" in args or "+" in args or "..." in args:
        return False

    # Strip complete string literals, then options-object keys (`encoding:` in
    # `{ encoding: 'utf8' }` is a key, not a variable reference), then literal
    # keywords. Anything still looking like an identifier is a variable, and the
    # call is not constant.
    residue = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`${]*`", "", args)
    residue = re.sub(r"[A-Za-z_$][\w$]*\s*:", "", residue)
    residue = re.sub(r"\b(?:true|false|null|undefined)\b", "", residue)
    if re.search(r"[A-Za-z_$]", residue):
        return False

    return True


# SQL keywords used to identify SQL template strings
SQL_KEYWORDS: Set[str] = {
    "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "TRUNCATE", "MERGE", "REPLACE", "GRANT", "REVOKE",
}

# A SQL statement, not merely a word that is also a SQL keyword.
#
# Presence of a keyword is far too weak on its own: `insert`, `create`,
# `delete`, `update` and `replace` are ordinary English verbs and ordinary UI
# vocabulary. On the audit target the keyword test reported error messages
# (`cannot create ${target}`), aria-labels (`${t('delete')}: ${name}`), test
# assertions and prompt text as SQL injection.
#
# Every keyword here is paired with the companion clause SQL requires, so the
# test is for statement syntax rather than for a word:
#   SELECT ... FROM      INSERT INTO      UPDATE ... SET      DELETE FROM
#   CREATE/DROP/ALTER/TRUNCATE <object>   GRANT/REVOKE ... ON
# `cannot create ${target}` has no object keyword after CREATE, and
# `insert ${path}` has no INTO, so neither survives — while a real
# `INSERT INTO users (name) VALUES ('${name}')` does.
SQL_STATEMENT_RE = re.compile(
    r"""
    \bSELECT\b (?:.|\n){0,400}? \bFROM\b
  | \bINSERT\s+INTO\b
  | \bUPDATE\b (?:.|\n){0,200}? \bSET\b
  | \bDELETE\s+FROM\b
  | \b(?:CREATE|DROP|ALTER|TRUNCATE)\s+
        (?:TEMP(?:ORARY)?\s+|UNIQUE\s+|MATERIALIZED\s+|OR\s+REPLACE\s+)*
        (?:TABLE|INDEX|VIEW|DATABASE|SCHEMA|SEQUENCE|TRIGGER|FUNCTION|PROCEDURE)\b
  | \b(?:GRANT|REVOKE)\b (?:.|\n){0,200}? \bON\b
  | \bREPLACE\s+INTO\b
  | \bMERGE\s+INTO\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def looks_like_sql_statement(text: str) -> bool:
    """Whether `text` contains SQL statement syntax, not just a SQL keyword.

    Used by every code path that can emit AGENT-041, so the predicate cannot be
    satisfied on one path and bypassed on another.
    """
    return bool(SQL_STATEMENT_RE.search(text or ""))

# Prompt-related variable/function names
PROMPT_CONTEXT_NAMES: Set[str] = {
    "prompt", "system_prompt", "systemPrompt", "system_message",
    "systemMessage", "user_prompt", "userPrompt", "instruction",
    "instructions", "message", "messages", "template",
    "system", "role",
}

# Names in PROMPT_CONTEXT_NAMES that are ordinary programming vocabulary rather
# than evidence of an LLM prompt. `message` is the most common name in
# TypeScript for an error or log string; on the audit target every AGENT-010
# finding but one was `let message = \`... error (HTTP ${status})\``.
#
# Same shape as the SQL narrowing in 5f00398: a keyword alone is too weak, so
# the weak names have to be paired with the companion evidence their claim
# requires. The strong names — prompt, systemPrompt, userPrompt, instructions —
# are unambiguous and keep firing on their own.
WEAK_PROMPT_CONTEXT_NAMES: Set[str] = {
    "message", "messages", "template", "system", "role",
}

# Evidence that the surrounding code is talking to a model.
_LLM_CONTEXT_RE = re.compile(
    r"\bopenai\b|\banthropic\b|\bclaude\b|\bgemini\b|\bollama\b|\bbedrock\b"
    r"|\bllm\b|\blangchain\b|\bchat\.completions\b|\bcreateChatCompletion\b"
    r"|\bcompletions?\s*\.\s*create\b|\bsystem(?:_p|P)rompt\b|\bprompt\b"
    r"|\brole\s*:\s*['\"](?:system|user|assistant)['\"]"
    r"|\bmessages\s*:\s*\[",
    re.IGNORECASE,
)

# How many lines either side of the assignment count as "surrounding".
_PROMPT_CONTEXT_WINDOW = 3

# Unsafe deserialization patterns for JS/TS
UNSAFE_DESER_PATTERNS: List[Tuple[re.Pattern, str, float]] = [
    (
        re.compile(r'\bnode-serialize\b|\brequire\s*\(\s*["\']node-serialize["\']\s*\)'),
        "node-serialize (known RCE vulnerability)",
        0.95,
    ),
    (
        re.compile(r'\bunserialize\s*\('),
        "unserialize() call (potential RCE)",
        0.85,
    ),
    (
        re.compile(r'\bserialize-javascript\b.*\bdeserialize\b'),
        "serialize-javascript deserialize",
        0.80,
    ),
    (
        re.compile(r'\byaml\.load\s*\((?!.*safe)', re.IGNORECASE),
        "yaml.load without safe option",
        0.80,
    ),
]

# File extensions supported by this scanner
TS_EXTENSIONS: Set[str] = {".ts", ".tsx", ".js", ".jsx", ".mjs"}

# Directories to skip during scanning
SKIP_DIRS: Set[str] = {
    ".git", "venv", ".venv", "__pycache__", "dist",
    "build", "node_modules", ".tox", ".pytest_cache",
    ".next", ".nuxt", "coverage", ".nyc_output",
}

# OWASP ID mapping for rule IDs
RULE_OWASP_MAP: Dict[str, str] = {
    "AGENT-034": "ASI-02",
    "AGENT-041": "ASI-02",
    "AGENT-010": "ASI-01",
    "AGENT-026": "ASI-02",
    "AGENT-049": "ASI-04",
}

# CWE ID mapping for rule IDs
RULE_CWE_MAP: Dict[str, str] = {
    "AGENT-034": "CWE-20",
    "AGENT-041": "CWE-89",
    "AGENT-010": "CWE-74",
    "AGENT-026": "CWE-918",
    "AGENT-049": "CWE-502",
}

# Category mapping for rule IDs
RULE_CATEGORY_MAP: Dict[str, Category] = {
    "AGENT-034": Category.TOOL_MISUSE,
    "AGENT-041": Category.COMMAND_INJECTION,
    "AGENT-010": Category.PROMPT_INJECTION,
    "AGENT-026": Category.SUPPLY_CHAIN_AGENTIC,
    "AGENT-049": Category.SUPPLY_CHAIN_AGENTIC,
}

# Severity mapping for pattern types
PATTERN_SEVERITY_MAP: Dict[str, Severity] = {
    "ts_eval_exec": Severity.CRITICAL,
    "ts_child_process_exec": Severity.CRITICAL,
    "ts_sql_template_injection": Severity.HIGH,
    "ts_template_prompt_injection": Severity.HIGH,
    "ts_ssrf_fetch": Severity.MEDIUM,
    "ts_unsafe_deserialization": Severity.HIGH,
}


@dataclass
class TSFinding:
    """Internal finding from TypeScript scanner before conversion."""

    rule_id: str
    pattern_type: str
    title: str
    description: str
    severity: Severity
    category: Category
    owasp_id: str
    cwe_id: str
    line: int
    snippet: str
    confidence: float
    file_path: str
    remediation: str


@dataclass
class TSScanResult(ScanResult):
    """Result of TypeScript scanning."""

    findings: List[TSFinding] = field(default_factory=list)


class TypeScriptScanner(BaseScanner):
    """
    Scanner for TypeScript/JavaScript security issues in AI agent code.

    Detects dangerous function calls, template string injections,
    SSRF patterns, and unsafe deserialization using tree-sitter AST
    analysis with regex fallback.
    """

    name = "TypeScript Scanner"

    def __init__(self, exclude_patterns: Optional[List[str]] = None):
        """Initialize the TypeScript scanner.

        Args:
            exclude_patterns: List of glob patterns to exclude from scanning
        """
        self.exclude_patterns = exclude_patterns or []

    def scan(self, path: Path) -> Sequence[TSScanResult]:
        """
        Scan path for TypeScript/JavaScript security issues.

        Args:
            path: File or directory to scan

        Returns:
            List of scan results with TypeScript findings
        """
        results: List[TSScanResult] = []
        files_to_scan = self._find_files(path)

        for file_path in files_to_scan:
            try:
                result = self._scan_file(file_path)
                if result and result.findings:
                    results.append(result)
            except Exception as e:
                logger.warning("Error scanning %s: %s", file_path, e)

        return results

    def scan_and_convert(self, path: Path) -> List[Finding]:
        """
        Scan and convert results to Finding objects.

        Args:
            path: File or directory to scan

        Returns:
            List of Finding objects
        """
        findings: List[Finding] = []
        scan_results = self.scan(path)

        for result in scan_results:
            for ts_finding in result.findings:
                finding = self._convert_to_finding(ts_finding)
                findings.append(finding)

        return findings

    # ========================================================================
    # File discovery
    # ========================================================================

    def _find_files(self, path: Path) -> List[Path]:
        """Find TypeScript/JavaScript files to scan."""
        if path.is_file():
            if path.suffix in TS_EXTENSIONS:
                return [path]
            return []

        files: List[Path] = []
        for ext in TS_EXTENSIONS:
            for file_path in path.rglob(f"*{ext}"):
                if any(part in SKIP_DIRS for part in file_path.parts):
                    continue
                if self._is_excluded(file_path):
                    continue
                files.append(file_path)

        return files

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if file matches any exclude pattern."""
        file_str = str(file_path)
        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return True
        return False

    # ========================================================================
    # File scanning
    # ========================================================================

    def _scan_file(self, file_path: Path) -> Optional[TSScanResult]:
        """Scan a single TypeScript/JavaScript file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning("Cannot read %s: %s", file_path, e)
            return None

        if not content.strip():
            return None

        file_str = str(file_path)
        findings: List[TSFinding] = []
        lines = content.splitlines()

        # Attempt tree-sitter-based analysis first
        ts_findings = self._scan_with_treesitter(file_path, content, file_str)
        if ts_findings is not None:
            findings.extend(ts_findings)
        else:
            # Fallback to regex-based analysis
            findings.extend(self._scan_dangerous_calls_regex(lines, file_str))
            findings.extend(self._scan_template_sql_regex(lines, file_str))
            findings.extend(self._scan_template_prompt_regex(lines, file_str))
            findings.extend(self._scan_ssrf_regex(lines, file_str))

        # Unsafe deserialization detection (always regex-based, patterns are simple)
        findings.extend(self._scan_unsafe_deserialization(lines, file_str))

        if findings:
            return TSScanResult(source_file=file_str, findings=findings)
        return None

    # ========================================================================
    # Tree-sitter-based analysis
    # ========================================================================

    def _scan_with_treesitter(
        self, file_path: Path, content: str, file_str: str
    ) -> Optional[List[TSFinding]]:
        """
        Attempt tree-sitter-based scanning.

        Returns None if tree-sitter is not available, otherwise returns
        a list of findings (possibly empty).
        """
        try:
            from agent_audit.parsers.treesitter_parser import TreeSitterParser
        except ImportError:
            return None

        parser = TreeSitterParser(
            source=content,
            file_path=str(file_path),
        )

        if not parser.is_tree_sitter_available:
            return None

        findings: List[TSFinding] = []

        # Analyze function calls from tree-sitter
        function_calls = parser.find_function_calls()
        for call in function_calls:
            call_findings = self._analyze_ts_call(call, content, file_str)
            findings.extend(call_findings)

        # Analyze string literals for SQL/prompt injection
        string_literals = parser.find_string_literals()
        for literal in string_literals:
            literal_findings = self._analyze_ts_literal(
                literal, content, file_str
            )
            findings.extend(literal_findings)

        return findings

    def _analyze_ts_call(
        self, call: "FunctionCall", content: str, file_str: str    ) -> List[TSFinding]:
        """Analyze a function call from tree-sitter for dangerous patterns."""
        findings: List[TSFinding] = []
        call_name = call.name

        # Direct match in dangerous calls table
        match_entry = TS_DANGEROUS_CALLS.get(call_name)

        # Try qualified name matching (e.g., child_process.exec).
        # Skip names in GLOBAL_ONLY_TS_CALLS so that, e.g.,
        # `redisClient.eval(luaScript)` (Redis EVAL) does not get
        # misidentified as the JS global `eval(...)` RCE sink.
        if match_entry is None:
            for dangerous_name, entry in TS_DANGEROUS_CALLS.items():
                if dangerous_name in GLOBAL_ONLY_TS_CALLS:
                    continue
                if call_name.endswith(dangerous_name):
                    # Require the boundary to be a dot, so that
                    # `redisClient.evalsha` doesn't endswith-match `eval`-like
                    # entries (it wouldn't here anyway, but the dot-boundary
                    # rule is more robust). Allow exact match for
                    # multi-token entries like `child_process.exec`.
                    if call_name == dangerous_name:
                        match_entry = entry
                        break
                    suffix_start = len(call_name) - len(dangerous_name)
                    if suffix_start > 0 and call_name[suffix_start - 1] == ".":
                        match_entry = entry
                        break

        if match_entry is None:
            return findings

        rule_id, pattern_type, base_confidence = match_entry

        # For SQL-related calls, only flag if template string is used as argument
        if pattern_type == "ts_sql_template_injection":
            if not self._has_template_arg_with_sql(call.args, call.raw_text):
                return findings

        # For SSRF calls, adjust confidence based on argument type
        if pattern_type == "ts_ssrf_fetch":
            confidence = self._compute_ssrf_confidence(
                call.args, base_confidence
            )
            if confidence < 0.30:
                return findings
            base_confidence = confidence

        # For new Function() - check for "new" keyword in raw text
        if call_name == "Function" and "new" not in call.raw_text:
            return findings

        findings.append(
            TSFinding(
                rule_id=rule_id,
                pattern_type=pattern_type,
                title=self._get_title(pattern_type),
                description=self._get_description(pattern_type, call_name),
                severity=PATTERN_SEVERITY_MAP.get(
                    pattern_type, Severity.MEDIUM
                ),
                category=RULE_CATEGORY_MAP.get(
                    rule_id, Category.TOOL_MISUSE
                ),
                owasp_id=RULE_OWASP_MAP.get(rule_id, "ASI-02"),
                cwe_id=RULE_CWE_MAP.get(rule_id, "CWE-20"),
                line=call.line,
                snippet=call.raw_text[:200],
                confidence=base_confidence,
                file_path=file_str,
                remediation=self._get_remediation(pattern_type),
            )
        )

        return findings

    def _analyze_ts_literal(
        self, literal: "StringLiteral", content: str, file_str: str    ) -> List[TSFinding]:
        """Analyze a string literal for SQL/prompt injection patterns."""
        findings: List[TSFinding] = []

        # Only interested in template strings with interpolation
        if not literal.is_fstring:
            return findings

        value_upper = literal.value.upper()

        # Require SQL statement syntax, not merely a word that is also a SQL
        # keyword. See looks_like_sql_statement().
        has_sql = looks_like_sql_statement(value_upper)
        if has_sql and "${" in literal.raw_value:
            findings.append(
                TSFinding(
                    rule_id="AGENT-041",
                    pattern_type="ts_sql_template_injection",
                    title="SQL Injection via Template String",
                    description=(
                        "SQL query constructed using template string interpolation. "
                        "User input may be injected into the query without sanitization."
                    ),
                    severity=Severity.HIGH,
                    category=Category.COMMAND_INJECTION,
                    owasp_id="ASI-02",
                    cwe_id="CWE-89",
                    line=literal.line,
                    snippet=literal.raw_value[:200],
                    confidence=0.85,
                    file_path=file_str,
                    remediation=(
                        "Use parameterized queries instead of template string "
                        "interpolation for SQL queries."
                    ),
                )
            )

        # Check for prompt injection in template strings
        if self._is_prompt_context(literal, content):
            findings.append(
                TSFinding(
                    rule_id="AGENT-010",
                    pattern_type="ts_template_prompt_injection",
                    title="Prompt Injection via Template String",
                    description=(
                        "System/user prompt constructed using template string "
                        "interpolation. Untrusted input may manipulate agent behavior."
                    ),
                    severity=Severity.HIGH,
                    category=Category.PROMPT_INJECTION,
                    owasp_id="ASI-01",
                    cwe_id="CWE-74",
                    line=literal.line,
                    snippet=literal.raw_value[:200],
                    confidence=0.75,
                    file_path=file_str,
                    remediation=(
                        "Sanitize user input before including in prompts. "
                        "Use structured prompt templates with explicit boundaries."
                    ),
                )
            )

        return findings

    # ========================================================================
    # Regex-based fallback analysis
    # ========================================================================

    def _scan_dangerous_calls_regex(
        self, lines: List[str], file_str: str
    ) -> List[TSFinding]:
        """Scan for dangerous function calls using regex."""
        findings: List[TSFinding] = []

        # Patterns: (regex, rule_id, pattern_type, confidence, display_name)
        # The eval pattern uses a negative lookbehind to exclude member-form
        # calls like `redisClient.eval(...)` (Redis EVAL Lua), keeping only
        # the bare global `eval(...)` form. Explicit global aliases
        # (window/globalThis/global/self.eval) are matched separately below.
        patterns: List[Tuple[re.Pattern, str, str, float, str]] = [
            # Bare global eval()
            (
                re.compile(r"(?<![\w.$])eval\s*\("),
                "AGENT-034",
                "ts_eval_exec",
                0.95,
                "eval",
            ),
            # Explicit global-scope eval aliases
            (
                re.compile(
                    r"\b(?:window|globalThis|global|self)\.eval\s*\("
                ),
                "AGENT-034",
                "ts_eval_exec",
                0.95,
                "globalThis.eval",
            ),
            # new Function()
            (
                re.compile(r"\bnew\s+Function\s*\("),
                "AGENT-034",
                "ts_eval_exec",
                0.90,
                "new Function",
            ),
            # vm.runIn*
            (
                re.compile(r"\bvm\.runIn(?:Context|NewContext|ThisContext)\s*\("),
                "AGENT-034",
                "ts_eval_exec",
                0.90,
                "vm.runInContext",
            ),
            # child_process exec/execSync — bare (destructured import) form only.
            #
            # The previous pattern was r"\b(?:child_process\.)?(?:exec|execSync)\("
            # and the optional group did nothing: \b also matches immediately
            # after a dot, so EVERY member call matched. `regex.exec(s)`,
            # `db.exec('COMMIT')` and `stmt.exec()` were all reported as shell
            # execution. Unlike `eval`, exec/spawn are not JS globals — they come
            # from child_process — so the receiver has to be resolved rather than
            # ignored. See CHILD_PROCESS_RECEIVERS and TestExecSpawnReceiver.
            (
                re.compile(
                    rf"(?<![\w.$]){_CP_EXEC_NAMES}\s*\("
                ),
                "AGENT-034",
                "ts_child_process_exec",
                0.90,
                "exec",
            ),
            # child_process exec/execSync — qualified form, receiver resolved.
            (
                re.compile(
                    rf"(?<![\w.$]){_CP_RECEIVER_RE}\.{_CP_EXEC_NAMES}\s*\("
                ),
                "AGENT-034",
                "ts_child_process_exec",
                0.90,
                "exec",
            ),
            # child_process spawn/spawnSync — bare (destructured import) form.
            (
                re.compile(
                    rf"(?<![\w.$]){_CP_SPAWN_NAMES}\s*\("
                ),
                "AGENT-034",
                "ts_child_process_exec",
                0.85,
                "spawn",
            ),
            # child_process spawn/spawnSync — qualified form, receiver resolved.
            (
                re.compile(
                    rf"(?<![\w.$]){_CP_RECEIVER_RE}\.{_CP_SPAWN_NAMES}\s*\("
                ),
                "AGENT-034",
                "ts_child_process_exec",
                0.85,
                "spawn",
            ),
            # execa
            (
                re.compile(r"\bexeca(?:Sync)?\s*\("),
                "AGENT-034",
                "ts_child_process_exec",
                0.85,
                "execa",
            ),
        ]

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip comment-only lines, including the `/*` and `/**` openers the
            # previous `//`-and-`*` test let through.
            if _TS_COMMENT_LINE_RE.match(line):
                continue

            for pattern, rule_id, pattern_type, confidence, call_name in patterns:
                match = pattern.search(line)
                if not match:
                    continue
                # A declaration names the operation; it does not perform it.
                # This replaces ts_decl_signature_re, which covered only
                # `eval|Function` and only the return-type form.
                if _is_ts_declaration(line, match.start()):
                    continue
                # Source text quoted inside a string is not a call site here.
                if _index_inside_string_literal(line, match.start()):
                    continue
                if pattern_type == "ts_child_process_exec":
                    # No injection surface when every argument is a literal:
                    # execFileSync('git', ['rev-parse', '--show-toplevel'])
                    # cannot be influenced by an attacker no matter what the
                    # process does with the result.
                    if _call_args_are_constant(line, match.end() - 1):
                        continue
                    # A fixed, non-shell executable is not shell execution.
                    if _fixed_non_shell_program(line, match.end() - 1):
                        continue
                if match:
                    findings.append(
                        TSFinding(
                            rule_id=rule_id,
                            pattern_type=pattern_type,
                            title=self._get_title(pattern_type),
                            description=self._get_description(
                                pattern_type, call_name
                            ),
                            severity=PATTERN_SEVERITY_MAP.get(
                                pattern_type, Severity.MEDIUM
                            ),
                            category=RULE_CATEGORY_MAP.get(
                                rule_id, Category.TOOL_MISUSE
                            ),
                            owasp_id=RULE_OWASP_MAP.get(rule_id, "ASI-02"),
                            cwe_id=RULE_CWE_MAP.get(rule_id, "CWE-20"),
                            line=line_num,
                            snippet=stripped[:200],
                            confidence=confidence,
                            file_path=file_str,
                            remediation=self._get_remediation(pattern_type),
                        )
                    )

        return findings

    def _scan_template_sql_regex(
        self, lines: List[str], file_str: str
    ) -> List[TSFinding]:
        """Scan for SQL injection via template strings using regex."""
        findings: List[TSFinding] = []

        # Match template strings containing SQL keywords and interpolation
        # Template string containing an interpolation. Whether it is SQL is
        # decided by looks_like_sql_statement() below rather than by the
        # presence of a keyword: `cannot create ${target}` is an error message,
        # not a query.
        template_sql_pattern = re.compile(r"`[^`]*\$\{[^}]+\}[^`]*`")

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            template_match = template_sql_pattern.search(line)
            if template_match and looks_like_sql_statement(template_match.group(0)):
                findings.append(
                    TSFinding(
                        rule_id="AGENT-041",
                        pattern_type="ts_sql_template_injection",
                        title="SQL Injection via Template String",
                        description=(
                            "SQL query constructed using template string "
                            "interpolation. User input may be injected "
                            "into the query without sanitization."
                        ),
                        severity=Severity.HIGH,
                        category=Category.COMMAND_INJECTION,
                        owasp_id="ASI-02",
                        cwe_id="CWE-89",
                        line=line_num,
                        snippet=stripped[:200],
                        confidence=0.85,
                        file_path=file_str,
                        remediation=(
                            "Use parameterized queries instead of "
                            "template string interpolation for SQL queries."
                        ),
                    )
                )

        return findings

    def _scan_template_prompt_regex(
        self, lines: List[str], file_str: str
    ) -> List[TSFinding]:
        """Scan for prompt injection via template strings using regex."""
        findings: List[TSFinding] = []

        # Pattern: variable assignment to a prompt-related name with template string
        prompt_template_pattern = re.compile(
            r"(?:const|let|var)\s+("
            + "|".join(re.escape(n) for n in PROMPT_CONTEXT_NAMES)
            + r")\s*=\s*`[^`]*\$\{[^}]+\}[^`]*`",
            re.IGNORECASE,
        )

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            match = prompt_template_pattern.search(line)
            if match and match.group(1).lower() in {
                n.lower() for n in WEAK_PROMPT_CONTEXT_NAMES
            }:
                # A weak name needs the companion evidence its claim requires.
                window = "\n".join(
                    lines[
                        max(0, line_num - 1 - _PROMPT_CONTEXT_WINDOW):
                        line_num + _PROMPT_CONTEXT_WINDOW
                    ]
                )
                if not _LLM_CONTEXT_RE.search(window):
                    match = None
            if match:
                findings.append(
                    TSFinding(
                        rule_id="AGENT-010",
                        pattern_type="ts_template_prompt_injection",
                        title="Prompt Injection via Template String",
                        description=(
                            f"Prompt variable '{match.group(1)}' constructed "
                            "using template string interpolation. Untrusted "
                            "input may manipulate agent behavior."
                        ),
                        severity=Severity.HIGH,
                        category=Category.PROMPT_INJECTION,
                        owasp_id="ASI-01",
                        cwe_id="CWE-74",
                        line=line_num,
                        snippet=stripped[:200],
                        confidence=0.75,
                        file_path=file_str,
                        remediation=(
                            "Sanitize user input before including in prompts. "
                            "Use structured prompt templates with explicit boundaries."
                        ),
                    )
                )

        return findings

    def _scan_ssrf_regex(
        self, lines: List[str], file_str: str
    ) -> List[TSFinding]:
        """Scan for SSRF patterns using regex."""
        findings: List[TSFinding] = []

        # Pattern: fetch/axios with variable argument (not hardcoded string)
        # Negative lookahead excludes calls where the first arg is a string literal
        _quote_lookahead = r"""(?!['"\x60])"""
        ssrf_patterns: List[Tuple[re.Pattern, str, float]] = [
            # `fetch` is a WHATWG global, so — exactly as with `eval` in
            # _scan_dangerous_calls_regex — the *member* form is the one that
            # is almost never the thing this rule is about. The previous
            # pattern was r"\bfetch\s*\(", and \b also matches immediately
            # after a dot, so `handler.fetch(request)`, `provider().fetch(...)`
            # and `route.fetch()` were all reported as outbound SSRF. A
            # server-side request handler named `fetch` (the Request -> Response
            # convention used by Workers, Bun, Hono and Remix) is the opposite
            # of an outbound request: it receives one.
            #
            # Same fix shape as CHILD_PROCESS_RECEIVERS in a37bfba, applied to
            # the global-identifier side of the problem.
            (
                re.compile(r"(?<![\w.$])fetch\s*\(\s*" + _quote_lookahead),
                "fetch",
                0.70,
            ),
            # Explicit global-scope fetch aliases, which the lookbehind above
            # would otherwise exclude along with the member calls.
            (
                re.compile(
                    r"\b(?:window|globalThis|global|self)\.fetch\s*\(\s*"
                    + _quote_lookahead
                ),
                "fetch",
                0.70,
            ),
            (
                re.compile(
                    r"\baxios\.(?:get|post|put|delete|patch)\s*\(\s*" + _quote_lookahead
                ),
                "axios",
                0.70,
            ),
            (
                re.compile(
                    r"\bhttps?\.request\s*\(\s*" + _quote_lookahead
                ),
                "http.request",
                0.75,
            ),
        ]

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if _TS_COMMENT_LINE_RE.match(line):
                continue

            for pattern, call_name, confidence in ssrf_patterns:
                match = pattern.search(line)
                if match and not _is_ts_declaration(line, match.start()) \
                        and not _index_inside_string_literal(line, match.start()):
                    findings.append(
                        TSFinding(
                            rule_id="AGENT-026",
                            pattern_type="ts_ssrf_fetch",
                            title="Server-Side Request Forgery (SSRF)",
                            description=(
                                f"Network request via {call_name}() with "
                                "dynamic URL. User-controlled input may be "
                                "used to access internal services."
                            ),
                            severity=Severity.MEDIUM,
                            category=Category.SUPPLY_CHAIN_AGENTIC,
                            owasp_id="ASI-02",
                            cwe_id="CWE-918",
                            line=line_num,
                            snippet=stripped[:200],
                            confidence=confidence,
                            file_path=file_str,
                            remediation=(
                                "Validate and allowlist URLs before making "
                                "network requests. Use URL parsing to verify "
                                "the hostname against an allowlist."
                            ),
                        )
                    )

        return findings

    def _scan_unsafe_deserialization(
        self, lines: List[str], file_str: str
    ) -> List[TSFinding]:
        """Scan for unsafe deserialization patterns."""
        findings: List[TSFinding] = []

        js_yaml_major = _declared_js_yaml_major(Path(file_str))
        yaml_load_is_safe = (
            js_yaml_major is not None and js_yaml_major >= _JS_YAML_SAFE_MAJOR
        )

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if _TS_COMMENT_LINE_RE.match(line):
                continue

            # js-yaml >= 4 renamed safeLoad to load; the bare call is the safe
            # loader there. An explicit unsafe entry point still fires.
            if (
                yaml_load_is_safe
                and _YAML_LOAD_RE.search(line)
                and not _YAML_UNSAFE_MARKERS_RE.search(line)
            ):
                continue

            for pattern, description, confidence in UNSAFE_DESER_PATTERNS:
                match = pattern.search(line)
                if match and not _is_ts_declaration(line, match.start()) \
                        and not _index_inside_string_literal(line, match.start()):
                    findings.append(
                        TSFinding(
                            rule_id="AGENT-049",
                            pattern_type="ts_unsafe_deserialization",
                            title="Unsafe Deserialization",
                            description=(
                                f"Unsafe deserialization detected: {description}. "
                                "Deserializing untrusted data can lead to "
                                "remote code execution."
                            ),
                            severity=Severity.HIGH,
                            category=Category.SUPPLY_CHAIN_AGENTIC,
                            owasp_id="ASI-04",
                            cwe_id="CWE-502",
                            line=line_num,
                            snippet=stripped[:200],
                            confidence=confidence,
                            file_path=file_str,
                            remediation=(
                                "Avoid deserializing untrusted data. "
                                "Use safe alternatives like JSON.parse() for "
                                "data interchange."
                            ),
                        )
                    )

        return findings

    # ========================================================================
    # Helper methods
    # ========================================================================

    def _has_template_arg_with_sql(
        self, args: List[str], raw_text: str
    ) -> bool:
        """Check if any argument is a template string containing SQL keywords."""
        combined = " ".join(args) + " " + raw_text
        combined_upper = combined.upper()
        has_sql = looks_like_sql_statement(combined_upper)
        has_interpolation = "${" in combined
        return has_sql and has_interpolation

    def _compute_ssrf_confidence(
        self, args: List[str], base_confidence: float
    ) -> float:
        """
        Compute confidence for SSRF finding based on argument analysis.

        Hardcoded string URLs get low confidence; dynamic URLs get high.
        """
        if not args:
            return base_confidence

        first_arg = args[0].strip()

        # Hardcoded string literal - low confidence
        if (
            first_arg.startswith(("'", '"', "`"))
            and "${" not in first_arg
        ):
            return 0.25

        # Template string with interpolation - high confidence
        if "`" in first_arg and "${" in first_arg:
            return base_confidence * 1.1

        # Variable reference - standard confidence
        return base_confidence

    def _is_prompt_context(
        self, literal: "StringLiteral", content: str    ) -> bool:
        """Check if a template string is used in a prompt context."""
        # Check if template string has interpolation
        if "${" not in literal.raw_value:
            return False

        # Get the surrounding lines for context
        content_lines = content.splitlines()
        start = max(0, literal.line - 3)
        end = min(len(content_lines), literal.line + 2)
        context_window = "\n".join(content_lines[start:end]).lower()

        # Check if any prompt-related names appear nearby
        return any(
            name.lower() in context_window
            for name in PROMPT_CONTEXT_NAMES
        )

    def _get_title(self, pattern_type: str) -> str:
        """Get human-readable title for a pattern type."""
        titles: Dict[str, str] = {
            "ts_eval_exec": "Dangerous Code Execution",
            "ts_child_process_exec": "Shell Command Execution",
            "ts_sql_template_injection": "SQL Injection via Template String",
            "ts_template_prompt_injection": "Prompt Injection via Template String",
            "ts_ssrf_fetch": "Server-Side Request Forgery (SSRF)",
            "ts_unsafe_deserialization": "Unsafe Deserialization",
        }
        return titles.get(pattern_type, "Security Issue")

    def _get_description(self, pattern_type: str, call_name: str) -> str:
        """Get human-readable description for a pattern type."""
        descriptions: Dict[str, str] = {
            "ts_eval_exec": (
                f"Dangerous code execution via {call_name}(). "
                "Executing untrusted code can lead to remote code execution."
            ),
            "ts_child_process_exec": (
                f"Shell command execution via {call_name}(). "
                "Command injection is possible if user input is included "
                "in the command string."
            ),
            "ts_sql_template_injection": (
                f"SQL query via {call_name}() uses template string interpolation. "
                "User input may be injected without sanitization."
            ),
            "ts_template_prompt_injection": (
                "Prompt constructed using template string interpolation. "
                "Untrusted input may manipulate agent behavior."
            ),
            "ts_ssrf_fetch": (
                f"Network request via {call_name}() with potentially "
                "user-controlled URL. May allow access to internal services."
            ),
            "ts_unsafe_deserialization": (
                f"Unsafe deserialization via {call_name}(). "
                "Deserializing untrusted data can lead to remote code execution."
            ),
        }
        return descriptions.get(pattern_type, f"Security issue in {call_name}()")

    def _get_remediation(self, pattern_type: str) -> str:
        """Get remediation guidance for a pattern type."""
        remediations: Dict[str, str] = {
            "ts_eval_exec": (
                "Avoid eval() and new Function(). Use safe alternatives "
                "like JSON.parse() for data or a sandboxed VM for code execution."
            ),
            "ts_child_process_exec": (
                "Use execFile() or spawn() with an argument array instead of "
                "exec() with a command string. Never include user input in "
                "shell commands."
            ),
            "ts_sql_template_injection": (
                "Use parameterized queries instead of template string "
                "interpolation for SQL queries."
            ),
            "ts_template_prompt_injection": (
                "Sanitize user input before including in prompts. "
                "Use structured prompt templates with explicit boundaries."
            ),
            "ts_ssrf_fetch": (
                "Validate and allowlist URLs before making network requests. "
                "Use URL parsing to verify the hostname against an allowlist."
            ),
            "ts_unsafe_deserialization": (
                "Avoid deserializing untrusted data. Use safe alternatives "
                "like JSON.parse() for data interchange."
            ),
        }
        return remediations.get(pattern_type, "Review and secure this code pattern.")

    def _convert_to_finding(self, ts_finding: TSFinding) -> Finding:
        """Convert TSFinding to Finding model."""
        confidence = ts_finding.confidence
        tier = confidence_to_tier(confidence)

        return Finding(
            rule_id=ts_finding.rule_id,
            title=ts_finding.title,
            description=ts_finding.description,
            severity=ts_finding.severity,
            category=ts_finding.category,
            location=Location(
                file_path=ts_finding.file_path,
                start_line=ts_finding.line,
                end_line=ts_finding.line,
                snippet=ts_finding.snippet,
            ),
            cwe_id=ts_finding.cwe_id,
            owasp_id=ts_finding.owasp_id,
            confidence=confidence,
            tier=tier,
            remediation=Remediation(description=ts_finding.remediation),
        )
