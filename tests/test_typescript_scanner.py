"""Tests for TypeScript/JavaScript security scanner."""

import tempfile
import textwrap
from pathlib import Path

import pytest

from agent_audit.scanners.typescript_scanner import TypeScriptScanner


@pytest.fixture
def scanner():
    """Create a TypeScriptScanner instance."""
    return TypeScriptScanner()


def _write_ts_file(content: str, suffix: str = ".ts") -> Path:
    """Write content to a temporary TypeScript file and return the path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    tmp.write(textwrap.dedent(content))
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


class TestEvalDetection:
    """Test detection of eval() calls."""

    def test_eval_detection(self, scanner):
        """eval(userInput) should produce AGENT-034 finding."""
        path = _write_ts_file("""
            function processInput(userInput: string) {
                const result = eval(userInput);
                return result;
            }
        """)
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1
        eval_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(eval_findings) >= 1
        assert eval_findings[0].confidence >= 0.90

    def test_eval_in_js_file(self, scanner):
        """eval() detection should work in .js files too."""
        path = _write_ts_file(
            """
            const x = eval(data);
        """,
            suffix=".js",
        )
        findings = scanner.scan_and_convert(path)
        eval_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(eval_findings) >= 1


class TestNewFunctionDetection:
    """Test detection of new Function() calls."""

    def test_new_function_detection(self, scanner):
        """new Function(code) should produce AGENT-034 finding."""
        path = _write_ts_file("""
            function createDynamic(code: string) {
                const fn = new Function(code);
                return fn();
            }
        """)
        findings = scanner.scan_and_convert(path)
        func_findings = [
            f
            for f in findings
            if f.rule_id == "AGENT-034"
            and ("Function" in f.description or "Function" in f.location.snippet)
        ]
        assert len(func_findings) >= 1


class TestChildProcessExec:
    """Test detection of child_process.exec calls."""

    def test_child_process_exec(self, scanner):
        """child_process.exec(cmd) should produce AGENT-034 finding."""
        path = _write_ts_file("""
            import { exec } from 'child_process';

            function runCommand(cmd: string) {
                exec(cmd, (error, stdout, stderr) => {
                    console.log(stdout);
                });
            }
        """)
        findings = scanner.scan_and_convert(path)
        exec_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(exec_findings) >= 1

    def test_child_process_spawn(self, scanner):
        """child_process.spawn should produce AGENT-034 finding."""
        path = _write_ts_file("""
            import { spawn } from 'child_process';

            function runProcess(cmd: string) {
                const proc = spawn(cmd, []);
                return proc;
            }
        """)
        findings = scanner.scan_and_convert(path)
        spawn_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(spawn_findings) >= 1

    def test_execa_detection(self, scanner):
        """execa() should produce AGENT-034 finding."""
        path = _write_ts_file("""
            import { execa } from 'execa';

            async function run(cmd: string) {
                const result = await execa(cmd);
                return result.stdout;
            }
        """)
        findings = scanner.scan_and_convert(path)
        execa_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(execa_findings) >= 1


class TestTemplateSQLInjection:
    """Test detection of SQL injection via template strings."""

    def test_template_sql_injection(self, scanner):
        """Template string with SQL keywords should produce AGENT-041."""
        path = _write_ts_file("""
            async function getUser(name: string) {
                const query = `SELECT * FROM users WHERE name = '${name}'`;
                return db.query(query);
            }
        """)
        findings = scanner.scan_and_convert(path)
        sql_findings = [f for f in findings if f.rule_id == "AGENT-041"]
        assert len(sql_findings) >= 1

    def test_template_insert_injection(self, scanner):
        """INSERT with template interpolation should produce AGENT-041."""
        path = _write_ts_file("""
            async function addUser(name: string, email: string) {
                const query = `INSERT INTO users (name, email) VALUES ('${name}', '${email}')`;
                return db.execute(query);
            }
        """)
        findings = scanner.scan_and_convert(path)
        sql_findings = [f for f in findings if f.rule_id == "AGENT-041"]
        assert len(sql_findings) >= 1

    def test_safe_parameterized_query_not_flagged(self, scanner):
        """Parameterized queries (no template interpolation) should not flag."""
        path = _write_ts_file("""
            async function getUser(name: string) {
                const query = 'SELECT * FROM users WHERE name = ?';
                return db.query(query, [name]);
            }
        """)
        findings = scanner.scan_and_convert(path)
        sql_findings = [f for f in findings if f.rule_id == "AGENT-041"]
        assert len(sql_findings) == 0


class TestTemplatePromptInjection:
    """Test detection of prompt injection via template strings."""

    def test_template_prompt_injection(self, scanner):
        """Template string in prompt context should produce AGENT-010."""
        path = _write_ts_file("""
            function buildPrompt(role: string) {
                const prompt = `You are ${role}. Follow instructions carefully.`;
                return prompt;
            }
        """)
        findings = scanner.scan_and_convert(path)
        prompt_findings = [f for f in findings if f.rule_id == "AGENT-010"]
        assert len(prompt_findings) >= 1

    def test_system_message_injection(self, scanner):
        """Template string assigned to systemMessage should produce AGENT-010."""
        path = _write_ts_file("""
            function buildSystem(userInput: string) {
                const systemMessage = `You are a helpful assistant. ${userInput}`;
                return systemMessage;
            }
        """)
        findings = scanner.scan_and_convert(path)
        prompt_findings = [f for f in findings if f.rule_id == "AGENT-010"]
        assert len(prompt_findings) >= 1


class TestFetchSSRF:
    """Test detection of SSRF via fetch/axios."""

    def test_fetch_ssrf(self, scanner):
        """fetch(userUrl) should produce AGENT-026 finding."""
        path = _write_ts_file("""
            async function getData(userUrl: string) {
                const response = await fetch(userUrl);
                return response.json();
            }
        """)
        findings = scanner.scan_and_convert(path)
        ssrf_findings = [f for f in findings if f.rule_id == "AGENT-026"]
        assert len(ssrf_findings) >= 1

    def test_hardcoded_fetch_low_confidence(self, scanner):
        """fetch with hardcoded URL should not produce a finding or have low confidence."""
        path = _write_ts_file("""
            async function getWeather() {
                const response = await fetch("https://api.example.com/weather");
                return response.json();
            }
        """)
        findings = scanner.scan_and_convert(path)
        ssrf_findings = [f for f in findings if f.rule_id == "AGENT-026"]
        # Should either have no findings or very low confidence
        for f in ssrf_findings:
            assert f.confidence < 0.50

    def test_axios_ssrf(self, scanner):
        """axios.get(url) with dynamic URL should produce AGENT-026."""
        path = _write_ts_file("""
            import axios from 'axios';

            async function fetchData(url: string) {
                const response = await axios.get(url);
                return response.data;
            }
        """)
        findings = scanner.scan_and_convert(path)
        ssrf_findings = [f for f in findings if f.rule_id == "AGENT-026"]
        assert len(ssrf_findings) >= 1


class TestSafePatterns:
    """Test that safe patterns are not falsely flagged."""

    def test_safe_json_parse_not_flagged(self, scanner):
        """JSON.parse(str) should NOT produce any finding."""
        path = _write_ts_file("""
            function parseConfig(data: string) {
                const config = JSON.parse(data);
                return config;
            }
        """)
        findings = scanner.scan_and_convert(path)
        # JSON.parse is safe - should not trigger any code execution finding
        exec_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(exec_findings) == 0

    def test_safe_template_no_interpolation(self, scanner):
        """Template string without interpolation should not flag SQL injection."""
        path = _write_ts_file("""
            const query = `SELECT * FROM users`;
            db.query(query);
        """)
        findings = scanner.scan_and_convert(path)
        sql_findings = [f for f in findings if f.rule_id == "AGENT-041"]
        assert len(sql_findings) == 0

    def test_comment_not_flagged(self, scanner):
        """Comments containing dangerous patterns should not be flagged."""
        path = _write_ts_file("""
            // eval(something) - this is just a comment
            // child_process.exec(cmd)
            const x = 42;
        """)
        findings = scanner.scan_and_convert(path)
        assert len(findings) == 0


class TestUnsafeDeserialization:
    """Test detection of unsafe deserialization patterns."""

    def test_node_serialize_detection(self, scanner):
        """require('node-serialize') should produce AGENT-049."""
        path = _write_ts_file("""
            const serialize = require('node-serialize');
            const obj = serialize.unserialize(data);
        """)
        findings = scanner.scan_and_convert(path)
        deser_findings = [f for f in findings if f.rule_id == "AGENT-049"]
        assert len(deser_findings) >= 1

    def test_unserialize_detection(self, scanner):
        """Direct unserialize() call should produce AGENT-049."""
        path = _write_ts_file("""
            const result = unserialize(userInput);
        """)
        findings = scanner.scan_and_convert(path)
        deser_findings = [f for f in findings if f.rule_id == "AGENT-049"]
        assert len(deser_findings) >= 1


class TestVmExecution:
    """Test detection of vm.runIn* calls."""

    def test_vm_run_in_context(self, scanner):
        """vm.runInContext should produce AGENT-034."""
        path = _write_ts_file("""
            import * as vm from 'vm';

            function executeCode(code: string) {
                const context = vm.createContext({});
                vm.runInContext(code, context);
            }
        """)
        findings = scanner.scan_and_convert(path)
        vm_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(vm_findings) >= 1

    def test_vm_run_in_new_context(self, scanner):
        """vm.runInNewContext should produce AGENT-034."""
        path = _write_ts_file("""
            import vm from 'vm';
            vm.runInNewContext(userCode, {});
        """)
        findings = scanner.scan_and_convert(path)
        vm_findings = [f for f in findings if f.rule_id == "AGENT-034"]
        assert len(vm_findings) >= 1


class TestFileExtensions:
    """Test that various file extensions are supported."""

    def test_tsx_file(self, scanner):
        """TSX files should be scanned."""
        path = _write_ts_file(
            """
            const result = eval(input);
        """,
            suffix=".tsx",
        )
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1

    def test_jsx_file(self, scanner):
        """JSX files should be scanned."""
        path = _write_ts_file(
            """
            const result = eval(input);
        """,
            suffix=".jsx",
        )
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1

    def test_mjs_file(self, scanner):
        """MJS files should be scanned."""
        path = _write_ts_file(
            """
            const result = eval(input);
        """,
            suffix=".mjs",
        )
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1

    def test_py_file_ignored(self, scanner):
        """Python files should NOT be scanned."""
        path = _write_ts_file(
            """
            eval(something)
        """,
            suffix=".py",
        )
        findings = scanner.scan_and_convert(path)
        assert len(findings) == 0


class TestScanAndConvert:
    """Test the scan_and_convert integration."""

    def test_finding_has_correct_location(self, scanner):
        """Findings should have correct file path and line numbers."""
        path = _write_ts_file("""
            const x = 1;
            const y = 2;
            const z = eval(something);
        """)
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1
        finding = findings[0]
        assert finding.location.file_path == str(path)
        assert finding.location.start_line >= 1
        assert finding.location.snippet is not None

    def test_finding_has_correct_metadata(self, scanner):
        """Findings should have correct CWE and OWASP IDs."""
        path = _write_ts_file("""
            eval(userInput);
        """)
        findings = scanner.scan_and_convert(path)
        assert len(findings) >= 1
        finding = findings[0]
        assert finding.rule_id == "AGENT-034"
        assert finding.cwe_id == "CWE-20"
        assert finding.owasp_id == "ASI-02"
        assert finding.tier in ("BLOCK", "WARN", "INFO", "SUPPRESSED")

    def test_empty_file_no_findings(self, scanner):
        """Empty files should produce no findings."""
        path = _write_ts_file("")
        findings = scanner.scan_and_convert(path)
        assert len(findings) == 0

    def test_directory_scanning(self, scanner, tmp_path):
        """Directory scanning should find files recursively."""
        sub_dir = tmp_path / "src"
        sub_dir.mkdir()

        ts_file = sub_dir / "app.ts"
        ts_file.write_text("const x = eval(input);", encoding="utf-8")

        safe_file = sub_dir / "safe.ts"
        safe_file.write_text("const x = 42;", encoding="utf-8")

        findings = scanner.scan_and_convert(tmp_path)
        assert len(findings) >= 1
        assert any("eval" in f.description for f in findings)


class TestEvalMemberCallDistinction:
    """
    AGENT-034 must distinguish the JS global ``eval(...)`` RCE sink from
    unrelated member-method calls like Redis ``client.eval(luaScript, ...)``
    (Redis EVAL Lua). Regression for FPs seen in x402-foundation/x402 scans.
    """

    def _has_eval_finding(self, scanner, path):
        """Return AGENT-034 findings whose pattern is eval-exec (not exec/spawn)."""
        return [
            f
            for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034"
            and "code execution" in f.description.lower()
        ]

    # --- Must NOT trigger AGENT-034 (false-positive regressions) ----------

    def test_redis_member_eval_not_flagged(self, scanner):
        """`redisClient.eval(luaScript, ...)` is Redis EVAL Lua, not RCE."""
        path = _write_ts_file("""
            async function updateChannel(key: string) {
                return await this.client.eval(UPDATE_CHANNEL_SCRIPT, {
                    keys: [key],
                });
            }
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_redis_evalsha_not_flagged(self, scanner):
        """`redis.evalsha(sha, ...)` is Redis EVALSHA Lua, not RCE."""
        path = _write_ts_file("""
            async function run(sha: string) {
                return await redis.evalsha(sha, 0);
            }
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_ioredis_member_eval_not_flagged(self, scanner):
        """`ioredis.eval(...)` member call is Redis EVAL, not RCE."""
        path = _write_ts_file("""
            const ioredis = makeIoredis();
            async function run(s: string) {
                return await ioredis.eval(s, 0);
            }
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_arbitrary_member_eval_not_flagged(self, scanner):
        """Any `someObj.eval(...)` member call is not the JS eval sink."""
        path = _write_ts_file("""
            function go(x: string) {
                return someObj.eval(x);
            }
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_ts_interface_method_signature_not_flagged(self, scanner):
        """TS interface method signatures `eval(args): Type;` aren't calls."""
        path = _write_ts_file("""
            export type RedisChannelStorageClient = {
                get(key: string): Promise<string | null>;
                eval(script: string, options: RedisEvalOptions): Promise<unknown>;
            };
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_class_method_eval_declaration_not_flagged(self, scanner):
        """Class method declarations `async eval(args): Type {}` aren't calls."""
        path = _write_ts_file("""
            class MockRedis {
                async eval(script: string, options: RedisEvalOptions): Promise<unknown> {
                    return null;
                }
            }
        """)
        assert self._has_eval_finding(scanner, path) == []

    def test_object_property_named_eval_not_flagged(self, scanner):
        """Object property keys named ``eval:`` are not call expressions."""
        path = _write_ts_file("""
            const client = {
                eval: (script: string, options: RedisEvalOptions) =>
                    ensureClient().then(c => c.eval(script, options)),
            };
        """)
        assert self._has_eval_finding(scanner, path) == []

    # --- Must STILL trigger AGENT-034 (real RCE, no regressions) ----------

    def test_bare_eval_with_user_input_still_flagged(self, scanner):
        """Bare global `eval(userInput)` is a real RCE sink."""
        path = _write_ts_file("""
            function go(userInput: string) {
                return eval(userInput);
            }
        """)
        assert self._has_eval_finding(scanner, path) != []

    def test_bare_eval_with_literal_still_flagged(self, scanner):
        """Bare global `eval("some code")` is still flagged."""
        path = _write_ts_file("""
            function go() {
                return eval("some code");
            }
        """)
        assert self._has_eval_finding(scanner, path) != []

    def test_window_eval_still_flagged(self, scanner):
        """`window.eval(x)` is a real global RCE sink (browser)."""
        path = _write_ts_file("""
            function go(x: string) {
                return window.eval(x);
            }
        """)
        assert self._has_eval_finding(scanner, path) != []

    def test_globalthis_eval_still_flagged(self, scanner):
        """`globalThis.eval(x)` is a real global RCE sink."""
        path = _write_ts_file("""
            function go(x: string) {
                return globalThis.eval(x);
            }
        """)
        assert self._has_eval_finding(scanner, path) != []

    def test_new_function_still_flagged(self, scanner):
        """`new Function(userInput)()` is a real RCE sink."""
        path = _write_ts_file("""
            function go(userInput: string) {
                return new Function(userInput)();
            }
        """)
        eval_like = [
            f
            for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034"
        ]
        assert eval_like != []


class TestExecSpawnReceiver:
    """
    AGENT-034 must distinguish child_process ``exec``/``spawn`` from unrelated
    member methods that share the name — ``RegExp.prototype.exec`` and the
    ``.exec()`` on essentially every SQL driver being the two that matter.

    This is the mirror image of TestEvalMemberCallDistinction above. ``eval`` is
    a JS global, so the *member* form is the suspicious one. ``exec``/``spawn``
    are not globals — they exist only on child_process or destructured out of
    it — so the member form is the normal one and the receiver is what carries
    the signal. The old pattern was
    ``r"\\b(?:child_process\\.)?(?:exec|execSync)\\s*\\("``, whose optional group
    did nothing: ``\\b`` also matches immediately after a dot, so every member
    call matched.

    Regression source: the audit-target evaluation recorded in
    NIGHT_RUN_LEDGER.md § W14, pattern 2. 455 of its findings were this.
    """

    def _shell_findings(self, scanner, path):
        """AGENT-034 findings from the child_process patterns, not eval."""
        return [
            f
            for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034"
            and "shell" in f.description.lower()
        ]

    # --- Must NOT trigger: receivers that are not child_process -------------

    def test_regex_exec_not_flagged(self, scanner):
        """`re.exec(s)` is RegExp.prototype.exec — the brief's named control."""
        path = _write_ts_file("""
            const re = /^(\\w+)=(\\w+)$/;
            function parse(line: string) {
                const m = re.exec(line);
                return m ? m[1] : null;
            }
        """)
        assert self._shell_findings(scanner, path) == []

    def test_regex_literal_exec_not_flagged(self, scanner):
        path = _write_ts_file("""
            const m = /a(b)c/.exec(input);
        """)
        assert self._shell_findings(scanner, path) == []

    def test_sqlite_db_exec_not_flagged(self, scanner):
        """`db.exec('COMMIT')` is a SQL driver, not a shell."""
        path = _write_ts_file("""
            function commit(db: Database) {
                db.exec('COMMIT');
            }
        """)
        assert self._shell_findings(scanner, path) == []

    def test_this_qualified_db_exec_not_flagged(self, scanner):
        path = _write_ts_file("""
            class Store {
                flush() { this.db.exec('PRAGMA wal_checkpoint'); }
            }
        """)
        assert self._shell_findings(scanner, path) == []

    def test_minified_single_letter_receiver_not_flagged(self, scanner):
        """Bundled output routinely produces `i.exec(...)` / `u.exec(...)`."""
        path = _write_ts_file("""
            const r = i.exec(s), q = u.exec(s);
        """)
        assert self._shell_findings(scanner, path) == []

    def test_unrelated_spawn_receivers_not_flagged(self, scanner):
        """A pty, a sandbox or a service having .spawn() is not child_process."""
        path = _write_ts_file("""
            const a = ctx.pty.spawn(cmd);
            const b = ctx.subprocess.spawn(cmd);
            const c = sandbox.spawn(cmd);
            const d = backend.spawn(cmd);
        """)
        assert self._shell_findings(scanner, path) == []

    # --- TRUE-POSITIVE CONTROLS: these must still fire ----------------------

    def test_child_process_exec_still_flagged(self, scanner):
        """The brief's named control: `child_process.exec(userInput)` fires."""
        path = _write_ts_file("""
            import child_process from 'child_process';
            function run(userInput: string) {
                return child_process.exec(userInput);
            }
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_bare_destructured_exec_still_flagged(self, scanner):
        """`const { exec } = require('child_process')` then bare `exec(...)`."""
        path = _write_ts_file("""
            const { exec } = require('child_process');
            function run(userInput: string) {
                return exec(userInput);
            }
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_bare_spawn_still_flagged(self, scanner):
        path = _write_ts_file("""
            import { spawn } from 'child_process';
            const child = spawn(userCommand, userArgs);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_execsync_still_flagged(self, scanner):
        path = _write_ts_file("""
            import { execSync } from 'child_process';
            const out = execSync(`git log ${userRef}`);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_cp_alias_still_flagged(self, scanner):
        """`import * as cp from 'child_process'` is a common alias."""
        path = _write_ts_file("""
            import * as cp from 'child_process';
            cp.spawnSync(userCommand);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_execa_still_flagged(self, scanner):
        """execa is a child_process wrapper and is matched by name."""
        path = _write_ts_file("""
            import execa from 'execa';
            await execa(userCommand);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_mixed_file_keeps_only_the_real_one(self, scanner):
        """The discrimination itself, in one file: 1 of 4 calls is a shell."""
        path = _write_ts_file("""
            import child_process from 'child_process';
            const m = re.exec(line);
            db.exec('COMMIT');
            ctx.pty.spawn(shellCmd);
            child_process.exec(userInput);
        """)
        assert len(self._shell_findings(scanner, path)) == 1


class TestConstantArgumentSuppression:
    """
    A child_process call whose every argument is a literal has no injection
    surface. ``execFileSync('git', ['rev-parse', '--show-toplevel'])`` cannot be
    influenced by an attacker regardless of what happens to its output.

    The predicate is conservative by construction: it answers "not constant",
    and therefore reports, whenever it is unsure — an argument list that runs
    past the end of the line, a template interpolation, a concatenation, a
    spread, or any bare identifier. Every uncertain case stays a finding.

    Regression source: the audit-target evaluation recorded in
    NIGHT_RUN_LEDGER.md § W14, pattern 3.
    """

    def _shell_findings(self, scanner, path):
        return [
            f
            for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034" and "shell" in f.description.lower()
        ]

    # --- Must NOT trigger: nothing an attacker can reach --------------------

    def test_fixed_argv_not_flagged(self, scanner):
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            const root = execFileSync('git', ['rev-parse', '--show-toplevel']);
        """)
        assert self._shell_findings(scanner, path) == []

    def test_fixed_argv_with_options_object_not_flagged(self, scanner):
        """An options object's keys are keys, not variable references."""
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            const out = execFileSync('git', ['status'], { encoding: 'utf8' });
        """)
        assert self._shell_findings(scanner, path) == []

    def test_constant_string_command_not_flagged(self, scanner):
        path = _write_ts_file("""
            import { exec } from 'child_process';
            exec('copy');
        """)
        assert self._shell_findings(scanner, path) == []

    # --- TRUE-POSITIVE CONTROLS: anything variable must still fire ----------

    def test_variable_argument_to_fixed_program_superseded(self, scanner):
        """SUPERSEDED by TestFixedNonShellProgram — behaviour change, recorded.

        W14 pattern 3 asserted that a variable *argument* keeps the finding even
        when the program is fixed: `execFileSync('git', ['-C', cwd, 'log'])`.
        W17 pattern 3 narrows AGENT-034 to what its title claims — shell
        execution — and execFile with a literal program is neither a shell nor
        an attacker-chosen executable. What this gives up is argument injection
        against a known binary (`git --upload-pack=...` is the real one), which
        AGENT-034 never described and does not remediate.

        Kept as a test rather than deleted so the change of contract is visible
        rather than silent. See DECISIONS.md item 24.
        """
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            execFileSync('git', ['-C', cwd, 'log']);
        """)
        assert self._shell_findings(scanner, path) == []

    def test_template_interpolation_still_flagged(self, scanner):
        path = _write_ts_file("""
            import { execSync } from 'child_process';
            execSync(`git log ${userRef}`);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_concatenation_still_flagged(self, scanner):
        path = _write_ts_file("""
            import { exec } from 'child_process';
            exec('git log ' + userRef);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_spread_into_fixed_program_superseded(self, scanner):
        """SUPERSEDED by TestFixedNonShellProgram, same reason as above.

        The spread is the strongest form of the argument-injection case and it
        is the one this change gives up. Recorded here, not deleted.
        """
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            execFileSync('git', ['-C', cwd, ...args]);
        """)
        assert self._shell_findings(scanner, path) == []

    def test_spread_into_variable_program_still_flagged(self, scanner):
        """The spread still fires when the program itself is not fixed."""
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            execFileSync(binary, ['-C', cwd, ...args]);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_bare_identifier_command_still_flagged(self, scanner):
        path = _write_ts_file("""
            import { exec } from 'child_process';
            exec(userCommand);
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_shell_true_with_variable_still_flagged(self, scanner):
        """`shell: true` plus a variable is the dangerous combination."""
        path = _write_ts_file("""
            import { spawn } from 'child_process';
            spawn(userCommand, { shell: true });
        """)
        assert len(self._shell_findings(scanner, path)) >= 1

    def test_multiline_call_with_fixed_program_superseded(self, scanner):
        """SUPERSEDED by TestFixedNonShellProgram, same reason as the two above.

        W14 could not see past the end of the line, so `const files =
        execFileSync(` was treated as unknown and reported. W17 joins a short
        window and finds the literal `'git'` on the next line, which puts this
        in exactly the same bucket as the single-line form. Kept and inverted so
        the change is visible. See DECISIONS.md item 24.
        """
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            const files = execFileSync(
                'git',
                ['ls-files', userPath],
            );
        """)
        assert self._shell_findings(scanner, path) == []

    def test_multiline_call_with_variable_program_still_flagged(self, scanner):
        """The line-joining must not turn an unknown program into a safe one."""
        path = _write_ts_file("""
            import { execFileSync } from 'child_process';
            const files = execFileSync(
                resolvedBinary,
                ['ls-files', userPath],
            );
        """)
        assert len(self._shell_findings(scanner, path)) >= 1


class TestSqlStatementRequirement:
    """
    AGENT-041 must require SQL statement syntax, not merely a word that is also
    a SQL keyword. ``insert``, ``create``, ``delete``, ``update`` and
    ``replace`` are ordinary English verbs and ordinary UI vocabulary.

    The old test was ``any(kw in value_upper for kw in SQL_KEYWORDS)``, a bare
    substring check, so ``cannot create ${target}`` matched on CREATE. On the
    audit target this reported error messages, aria-labels, test assertions and
    prompt text as SQL injection.

    Regression source: the audit-target evaluation recorded in
    NIGHT_RUN_LEDGER.md § W14, pattern 4.
    """

    def _sql_findings(self, scanner, path):
        return [f for f in scanner.scan_and_convert(path) if f.rule_id == "AGENT-041"]

    # --- Must NOT trigger: English prose that contains a SQL keyword --------

    def test_error_message_with_create_not_flagged(self, scanner):
        path = _write_ts_file("""
            throw new Error(`cannot create ${target}: not a directory`);
        """)
        assert self._sql_findings(scanner, path) == []

    def test_aria_label_with_delete_not_flagged(self, scanner):
        path = _write_ts_file("""
            const label = `${t('delete')}: ${text.name}`;
        """)
        assert self._sql_findings(scanner, path) == []

    def test_prompt_text_with_create_not_flagged(self, scanner):
        path = _write_ts_file("""
            const p = `Create ${path} containing exactly ${content} using bash.`;
        """)
        assert self._sql_findings(scanner, path) == []

    def test_path_label_with_insert_not_flagged(self, scanner):
        path = _write_ts_file("""
            validateEntry(value.insert[index], file, `${path}.insert[${index}]`);
        """)
        assert self._sql_findings(scanner, path) == []

    def test_update_without_set_not_flagged(self, scanner):
        path = _write_ts_file("""
            out.push(`# Translation update briefing: ${input.sourcePath}`);
        """)
        assert self._sql_findings(scanner, path) == []

    # --- TRUE-POSITIVE CONTROLS: real SQL must still fire -------------------

    def test_select_from_still_flagged(self, scanner):
        path = _write_ts_file("""
            const rows = await db.query(`SELECT * FROM users WHERE id = ${userId}`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_insert_into_still_flagged(self, scanner):
        path = _write_ts_file("""
            await db.query(`INSERT INTO users (name) VALUES ('${name}')`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_delete_from_still_flagged(self, scanner):
        path = _write_ts_file("""
            await db.query(`DELETE FROM sessions WHERE token = '${token}'`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_update_set_still_flagged(self, scanner):
        path = _write_ts_file("""
            await db.query(`UPDATE users SET email = '${email}' WHERE id = ${id}`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_create_table_still_flagged(self, scanner):
        path = _write_ts_file("""
            await db.query(`CREATE TABLE ${tableName} (id INTEGER PRIMARY KEY)`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_drop_table_still_flagged(self, scanner):
        path = _write_ts_file("""
            await db.query(`DROP TABLE ${tableName}`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_lowercase_sql_still_flagged(self, scanner):
        """SQL written in lower case is still SQL."""
        path = _write_ts_file("""
            await db.query(`select * from audit_log where actor = '${actor}'`);
        """)
        assert len(self._sql_findings(scanner, path)) >= 1

    def test_mixed_file_keeps_only_the_query(self, scanner):
        """The discrimination itself: 1 of 3 interpolated templates is SQL."""
        path = _write_ts_file("""
            const msg = `cannot create ${target}`;
            const label = `${t('delete')}: ${name}`;
            const rows = await db.query(`SELECT id FROM users WHERE n = '${n}'`);
        """)
        assert len(self._sql_findings(scanner, path)) == 1


class TestFetchReceiver:
    """
    AGENT-026 must distinguish the global ``fetch`` from a member method that
    happens to be called ``fetch``.

    Same shape as TestExecSpawnReceiver, on the other side of the problem.
    ``exec``/``spawn`` are not globals, so there the *receiver* carries the
    signal. ``fetch`` **is** a WHATWG global, so — as with ``eval`` in
    TestEvalMemberCallDistinction — the member form is the one that is almost
    never an outbound request. The old pattern was ``r"\\bfetch\\s*\\("`` and
    ``\\b`` matches immediately after a dot, so every ``x.fetch(...)`` matched.

    The case that matters in practice is the ``fetch(Request) -> Response``
    server-handler convention (Workers, Bun, Hono, Remix). A handler named
    ``fetch`` *receives* a request; reporting it as server-side request forgery
    inverts the direction of the finding.

    Regression source: the audit-target evaluation recorded in
    NIGHT_RUN_LEDGER.md § W17, pattern 1. 67 of its 84 AGENT-026 findings were
    member-form calls.
    """

    def _ssrf(self, scanner, path):
        return [
            f for f in scanner.scan_and_convert(path) if f.rule_id == "AGENT-026"
        ]

    # --- Must NOT trigger: receivers that are not the global ---------------

    def test_request_handler_fetch_not_flagged(self, scanner):
        """`handler.fetch(new Request(...))` receives a request, not sends one."""
        path = _write_ts_file("""
            async function call(handler) {
                const response = await handler.fetch(new Request(target));
                return response.status;
            }
        """)
        assert self._ssrf(scanner, path) == []

    def test_provider_call_result_fetch_not_flagged(self, scanner):
        path = _write_ts_file("""
            const result = await provider().fetch({ url: base });
        """)
        assert self._ssrf(scanner, path) == []

    def test_property_chain_fetch_not_flagged(self, scanner):
        path = _write_ts_file("""
            const page = await ctx.web.fetch({ url: endpoint });
        """)
        assert self._ssrf(scanner, path) == []

    def test_route_fetch_not_flagged(self, scanner):
        path = _write_ts_file("""
            const response = await route.fetch();
        """)
        assert self._ssrf(scanner, path) == []

    # --- Must STILL trigger: the global ------------------------------------

    def test_bare_global_fetch_flagged(self, scanner):
        path = _write_ts_file("""
            export async function load(url: string) {
                return await fetch(url, { redirect: "follow" });
            }
        """)
        assert len(self._ssrf(scanner, path)) >= 1

    def test_globalthis_fetch_flagged(self, scanner):
        path = _write_ts_file("""
            const response = await globalThis.fetch(endpoint, { method: "GET" });
        """)
        assert len(self._ssrf(scanner, path)) >= 1

    def test_window_fetch_flagged(self, scanner):
        path = _write_ts_file("""
            const response = await window.fetch(target);
        """)
        assert len(self._ssrf(scanner, path)) >= 1

    def test_axios_still_flagged(self, scanner):
        """The axios patterns are receiver-qualified already and unaffected."""
        path = _write_ts_file("""
            const response = await axios.get(userSuppliedUrl);
        """)
        assert len(self._ssrf(scanner, path)) >= 1

    def test_hardcoded_url_still_excluded(self, scanner):
        """The pre-existing string-literal exclusion is preserved."""
        path = _write_ts_file("""
            const response = await fetch("https://api.example.com/health");
        """)
        assert self._ssrf(scanner, path) == []

    def test_mixed_file_keeps_only_the_global(self, scanner):
        """The discrimination itself: 1 of 3 fetch calls is outbound."""
        path = _write_ts_file("""
            const a = await handler.fetch(new Request(input));
            const b = await provider().fetch({ url: base });
            const c = await fetch(userSuppliedUrl, { method: "GET" });
        """)
        assert len(self._ssrf(scanner, path)) == 1


class TestDeclarationsAndQuotedSource:
    """
    A declaration names an operation; it does not perform one. Neither does a
    comment, nor source text quoted inside a string.

    `ts_decl_signature_re` already covered part of this — scoped to
    ``eval|Function`` and to the return-type form alone. On the audit target the
    uncovered shapes were the bulk of what remained: interface and class method
    declarations named ``spawn``/``exec``/``fetch``, JSDoc opener lines (`/**`
    was never skipped, only `//` and `*`), and generated API-surface entries
    whose values are quoted source — ``signature: 'async spawn(owner: Agent)'``.

    The discrimination that has to hold is `execFileSync('git', ['init'])`:
    identifier, parens, end of line, and still a call. Balanced parentheses plus
    "no `=` or `(` before the name" plus one positive declaration marker is what
    separates them.

    Regression source: the audit-target measurement recorded in
    NIGHT_RUN_LEDGER.md § W17, pattern 2.
    """

    def _shell(self, scanner, path):
        return [
            f for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034" and "shell" in f.description.lower()
        ]

    def _ssrf(self, scanner, path):
        return [
            f for f in scanner.scan_and_convert(path) if f.rule_id == "AGENT-026"
        ]

    # --- Must NOT trigger: declarations ------------------------------------

    def test_interface_method_declaration_not_flagged(self, scanner):
        path = _write_ts_file("""
            export interface PtyBackend {
                spawn(spec: PtyBackendSpawnSpec): Promise<PtyBackendSession>
            }
        """)
        assert self._shell(scanner, path) == []

    def test_abstract_method_declaration_not_flagged(self, scanner):
        path = _write_ts_file("""
            abstract class Base {
                abstract spawn(spec: SubprocessSpawnSpec): SubprocessHandle
            }
        """)
        assert self._shell(scanner, path) == []

    def test_async_method_body_opener_not_flagged(self, scanner):
        path = _write_ts_file("""
            class Local {
                async spawn() {
                    return this.backend;
                }
            }
        """)
        assert self._shell(scanner, path) == []

    def test_override_method_declaration_not_flagged(self, scanner):
        path = _write_ts_file("""
            class Fake extends Base {
                override spawn(spec: SubprocessSpawnSpec): SubprocessHandle {
                    throw new Error("unused");
                }
            }
        """)
        assert self._shell(scanner, path) == []

    def test_local_function_named_exec_not_flagged(self, scanner):
        path = _write_ts_file("""
            function exec(name: string, args: unknown): ToolExecutionInput {
                return { name, args };
            }
        """)
        assert self._shell(scanner, path) == []

    def test_fetch_method_declaration_not_flagged(self, scanner):
        path = _write_ts_file("""
            export interface WebFetchProvider {
                fetch(request: WebFetchRequest, signal?: AbortSignal): Promise<WebFetchResult>
            }
        """)
        assert self._ssrf(scanner, path) == []

    # --- Must NOT trigger: comments and quoted source ----------------------

    def test_jsdoc_opener_not_flagged(self, scanner):
        """`/**` was never skipped — only `//` and a continuation `*`."""
        path = _write_ts_file("""
            /** Executable to spawn (absolute, or resolved on PATH at load). */
            const program = resolved;
        """)
        assert self._shell(scanner, path) == []

    def test_block_comment_opener_not_flagged(self, scanner):
        path = _write_ts_file("""
            /* wrap argv so the caller spawn()s it confined */
            const argv = confine(input);
        """)
        assert self._shell(scanner, path) == []

    def test_api_surface_signature_string_not_flagged(self, scanner):
        path = _write_ts_file("""
            const entry = {
                signature: 'async spawn(owner: Agent, request: PtySpawnRequest): Promise<R>',
            };
        """)
        assert self._shell(scanner, path) == []

    def test_child_script_built_as_string_not_flagged(self, scanner):
        path = _write_ts_file("""
            const helper = 'const child = spawnSync(process.argv[1], [], {});';
            writeFileSync(target, helper);
        """)
        assert self._shell(scanner, path) == []

    # --- Must STILL trigger: real calls ------------------------------------

    def test_call_that_looks_like_a_declaration_still_flagged(self, scanner):
        """The discriminator: identifier, parens, end of line — still a call."""
        path = _write_ts_file("""
            execFileSync(gitBinary, ['init', '--quiet', root], { env })
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_multiline_call_opener_still_flagged(self, scanner):
        """An unbalanced paren is a continued call, not a declaration body."""
        path = _write_ts_file("""
            const child = spawn(program, [
                "--flag",
            ]);
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_bare_call_with_variable_still_flagged(self, scanner):
        path = _write_ts_file("""
            const out = execSync(userCommand);
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_global_fetch_call_still_flagged(self, scanner):
        path = _write_ts_file("""
            const response = await fetch(target, { method: "GET" });
        """)
        assert len(self._ssrf(scanner, path)) >= 1

    def test_trailing_brace_call_still_flagged(self, scanner):
        """Ends with `{`, but the parens do not balance — an options object."""
        path = _write_ts_file("""
            spawn(program, args, {
                stdio: "inherit",
            });
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_deserialization_declaration_excluded_but_call_kept(self, scanner):
        """The deserialization scanner gets the same treatment."""
        decl = _write_ts_file("""
            interface Loader {
                load(source: string): unknown
            }
        """)
        assert [f for f in scanner.scan_and_convert(decl)
                if f.rule_id == "AGENT-049"] == []
        call = _write_ts_file("""
            const parsed = yaml.load(untrustedDocument);
        """)
        assert [f for f in scanner.scan_and_convert(call)
                if f.rule_id == "AGENT-049"] != []


class TestFixedNonShellProgram:
    """
    AGENT-034 is "Shell Command Execution". The execFile/spawn family does not
    go through a shell, and a literal first argument fixes the executable, so
    neither half of the rule's own definition is present.

    `_call_args_are_constant` (W14 pattern 3) already covered the case where
    *every* argument is a literal. That is much stricter than the rule needs: a
    spread, a `cwd` variable or a computed argv defeats it, which is why 84
    findings of this shape survived it on the audit target.

    The three guards that keep this from over-reaching are each tested below:
    `exec`/`execSync` still fire because they do use a shell; `shell: true`
    still fires; and a program literal naming a shell still fires, so
    `spawn('sh', ['-c', userCommand])` is untouched.

    Regression source: the audit-target measurement recorded in
    NIGHT_RUN_LEDGER.md section W17, pattern 3.
    """

    def _shell(self, scanner, path):
        return [
            f for f in scanner.scan_and_convert(path)
            if f.rule_id == "AGENT-034" and "shell" in f.description.lower()
        ]

    # --- Must NOT trigger: fixed program, no shell -------------------------

    def test_execfilesync_literal_program_not_flagged(self, scanner):
        path = _write_ts_file("""
            const out = execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8' });
        """)
        assert self._shell(scanner, path) == []

    def test_spawnsync_literal_program_not_flagged(self, scanner):
        path = _write_ts_file("""
            const probe = spawnSync('bwrap', [...profileArgs(mode), '--'], { timeout });
        """)
        assert self._shell(scanner, path) == []

    def test_execa_literal_program_not_flagged(self, scanner):
        path = _write_ts_file("""
            const result = await execa('pnpm', ['pack', '--pack-destination', dest]);
        """)
        assert self._shell(scanner, path) == []

    def test_process_execpath_not_flagged(self, scanner):
        """process.execPath is the running Node binary, not an attacker choice."""
        path = _write_ts_file("""
            const child = spawn(process.execPath, ['--import', loader, entry], { env });
        """)
        assert self._shell(scanner, path) == []

    # --- Must STILL trigger: the three guards ------------------------------

    def test_variable_program_still_flagged(self, scanner):
        """The executable is chosen at runtime — the whole point of the rule."""
        path = _write_ts_file("""
            const child = spawn(command, args, { cwd, env });
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_shell_true_still_flagged(self, scanner):
        path = _write_ts_file("""
            const result = spawnSync('lefthook', args, { cwd: root, shell: true });
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_literal_shell_program_still_flagged(self, scanner):
        """spawn('sh', ['-c', cmd]) has a constant program and is still a shell."""
        path = _write_ts_file("""
            const child = spawn('sh', ['-c', userCommand], { stdio: 'inherit' });
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_literal_bash_program_still_flagged(self, scanner):
        path = _write_ts_file("""
            const child = spawnSync('/bin/bash', ['-c', script]);
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_exec_with_literal_first_arg_still_flagged(self, scanner):
        """exec/execSync pass their argument to a shell whatever it looks like."""
        path = _write_ts_file("""
            const out = execSync('git status --porcelain ' + userPath);
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_template_program_with_interpolation_still_flagged(self, scanner):
        path = _write_ts_file("""
            const child = spawnSync(`${binaryDir}/tool`, args, { encoding: 'utf8' });
        """)
        assert len(self._shell(scanner, path)) >= 1

    def test_mixed_file_keeps_only_the_variable_program(self, scanner):
        """The discrimination itself: 1 of 3 spawns has a runtime executable."""
        path = _write_ts_file("""
            const a = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd });
            const b = spawnSync(process.execPath, ['-e', code], { env });
            const c = spawnSync(resolvedBinary, args, { encoding: 'utf8' });
        """)
        assert len(self._shell(scanner, path)) == 1


class TestWeakPromptNames:
    """
    AGENT-010 fired on any interpolated template assigned to a name in
    PROMPT_CONTEXT_NAMES, and that set contains ordinary programming vocabulary:
    `message`, `messages`, `template`, `system`, `role`. `message` is the most
    common name in TypeScript for an error or log string, so on the audit target
    all but one AGENT-010 finding was an HTTP error message.

    Same shape as the SQL narrowing in 5f00398: a keyword alone is too weak, so
    the weak names are paired with the companion evidence their claim requires —
    something in the surrounding three lines that shows the code is talking to a
    model. The strong names (prompt, systemPrompt, userPrompt, instructions)
    keep firing on their own.

    Regression source: the audit-target measurement recorded in
    NIGHT_RUN_LEDGER.md section W17, pattern 5.
    """

    def _prompts(self, scanner, path):
        return [
            f for f in scanner.scan_and_convert(path) if f.rule_id == "AGENT-010"
        ]

    # --- Must NOT trigger: weak name, no model in sight --------------------

    def test_http_error_message_not_flagged(self, scanner):
        path = _write_ts_file("""
            function describe(response: Response) {
                let message = `Upstream API error (HTTP ${response.status})`;
                return message;
            }
        """)
        assert self._prompts(scanner, path) == []

    def test_timeout_message_not_flagged(self, scanner):
        path = _write_ts_file("""
            const message = `tool call timed out after ${timeoutMs}ms`;
        """)
        assert self._prompts(scanner, path) == []

    def test_ui_template_not_flagged(self, scanner):
        path = _write_ts_file("""
            const template = `<li data-id="${item.id}">${item.label}</li>`;
        """)
        assert self._prompts(scanner, path) == []

    # --- Must STILL trigger --------------------------------------------------

    def test_strong_name_flagged_without_context(self, scanner):
        """`prompt` is unambiguous and needs no corroboration."""
        path = _write_ts_file("""
            const prompt = `Summarise the following: ${document}`;
        """)
        assert len(self._prompts(scanner, path)) >= 1

    def test_system_prompt_flagged_without_context(self, scanner):
        path = _write_ts_file("""
            const systemPrompt = `You are ${persona}. Be brief.`;
        """)
        assert len(self._prompts(scanner, path)) >= 1

    def test_weak_name_flagged_with_model_context(self, scanner):
        """`message` beside a chat call is the case the rule is for."""
        path = _write_ts_file("""
            const message = `Answer as ${persona}: ${userText}`;
            const reply = await openai.chat.completions.create({
                model: "gpt-4o",
                messages: [{ role: "user", content: message }],
            });
        """)
        assert len(self._prompts(scanner, path)) >= 1

    def test_weak_name_flagged_with_role_literal_nearby(self, scanner):
        path = _write_ts_file("""
            const role = `${persona} assistant`;
            const payload = { role: "system", content: role };
        """)
        assert len(self._prompts(scanner, path)) >= 1

    def test_mixed_file_keeps_only_the_prompt(self, scanner):
        """The discrimination itself: 1 of 3 interpolated templates is a prompt.

        The weak names are placed outside the three-line window of the strong
        one on purpose. Proximity IS the corroboration this predicate uses, so a
        `message` two lines from a `prompt` is deliberately kept — that is the
        granularity, and pretending otherwise in a test would hide it.
        """
        path = _write_ts_file("""
            const message = `request failed (HTTP ${status})`;
            const template = `<b>${label}</b>`;

            function unrelated(a, b) {
                return a + b;
            }

            const prompt = `Rewrite this: ${userText}`;
        """)
        assert len(self._prompts(scanner, path)) == 1


class TestJsYamlVersionAwareLoad:
    """
    js-yaml renamed `safeLoad` to `load` in v4 (2021). From v4 onward `load`
    uses DEFAULT_SCHEMA, which does not construct arbitrary JavaScript objects;
    the unsafe entry points are `unsafeLoad` and an explicit full schema. In v3
    `load` genuinely was the unsafe loader, which is why the pattern exists.

    So whether `yaml.load(x)` is a finding depends on the declared dependency,
    not on the call alone. The nearest package.json above the file decides it,
    and only a range that clearly admits v4 or later suppresses. No declaration,
    an unreadable manifest, or a range admitting v3 leaves the finding in place —
    which is the direction that keeps a v3 project reported.

    Regression source: the audit-target measurement recorded in
    NIGHT_RUN_LEDGER.md section W17, pattern 8.
    """

    def _deser(self, tmp_path, manifest, source):
        pkg = tmp_path / "pkg"
        (pkg / "src").mkdir(parents=True)
        if manifest is not None:
            (pkg / "package.json").write_text(manifest, encoding="utf-8")
        target = pkg / "src" / "load.ts"
        target.write_text(source, encoding="utf-8")
        scanner = TypeScriptScanner()
        return [
            f for f in scanner.scan_and_convert(target) if f.rule_id == "AGENT-049"
        ]

    CALL = "const parsed = yaml.load(readFileSync(path, 'utf8'));\n"

    # --- Must NOT trigger: v4 and later ------------------------------------

    def test_caret_v4_not_flagged(self, tmp_path):
        manifest = '{"name":"p","dependencies":{"js-yaml":"^4.1.0"}}'
        assert self._deser(tmp_path, manifest, self.CALL) == []

    def test_exact_v4_not_flagged(self, tmp_path):
        manifest = '{"name":"p","devDependencies":{"js-yaml":"4.2.0"}}'
        assert self._deser(tmp_path, manifest, self.CALL) == []

    def test_v5_not_flagged(self, tmp_path):
        manifest = '{"name":"p","dependencies":{"js-yaml":">=5.0.0"}}'
        assert self._deser(tmp_path, manifest, self.CALL) == []

    # --- Must STILL trigger -------------------------------------------------

    def test_v3_still_flagged(self, tmp_path):
        """v3 load IS the unsafe loader — the case the pattern was written for."""
        manifest = '{"name":"p","dependencies":{"js-yaml":"^3.14.1"}}'
        assert len(self._deser(tmp_path, manifest, self.CALL)) >= 1

    def test_no_manifest_still_flagged(self, tmp_path):
        assert len(self._deser(tmp_path, None, self.CALL)) >= 1

    def test_manifest_without_js_yaml_still_flagged(self, tmp_path):
        manifest = '{"name":"p","dependencies":{"zod":"^3.0.0"}}'
        assert len(self._deser(tmp_path, manifest, self.CALL)) >= 1

    def test_unreadable_manifest_still_flagged(self, tmp_path):
        assert len(self._deser(tmp_path, "{not json", self.CALL)) >= 1

    def test_unsafe_load_still_flagged_on_v4(self, tmp_path):
        manifest = '{"name":"p","dependencies":{"js-yaml":"^4.1.0"}}'
        source = "const parsed = yaml.load(doc, { schema: DEFAULT_FULL_SCHEMA });\n"
        assert len(self._deser(tmp_path, manifest, source)) >= 1

    def test_other_deserialization_patterns_unaffected(self, tmp_path):
        manifest = '{"name":"p","dependencies":{"js-yaml":"^4.1.0"}}'
        source = "const obj = unserialize(payload);\n"
        assert len(self._deser(tmp_path, manifest, source)) >= 1
