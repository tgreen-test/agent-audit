"""Tests for MCP config scanner routing (KNOWN-003 fix)."""

import json
import pytest
from pathlib import Path

from agent_audit.scanners.mcp_config_scanner import MCPConfigScanner


class TestMCPConfigRouting:
    """Test that MCP configs are discovered regardless of filename."""

    @pytest.fixture
    def scanner(self):
        return MCPConfigScanner()

    def test_finds_standard_filename(self, scanner, tmp_path):
        """Test scanner finds standard mcp.json filename."""
        config = {
            "mcpServers": {
                "test": {"command": "npx", "args": ["-y", "test-server"]}
            }
        }
        (tmp_path / "mcp.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert len(results[0].servers) == 1
        assert results[0].servers[0].name == "test"

    def test_finds_nonstandard_filename_with_mcpservers(self, scanner, tmp_path):
        """KNOWN-003: Test scanner finds JSON with mcpServers key regardless of filename."""
        config = {
            "mcpServers": {
                "my-server": {"command": "node", "args": ["server.js"]}
            }
        }
        # Non-standard filename
        (tmp_path / "my-custom-config.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert len(results[0].servers) == 1
        assert results[0].servers[0].name == "my-server"

    def test_finds_nonstandard_yaml_with_mcpservers(self, scanner, tmp_path):
        """KNOWN-003: Test scanner finds YAML with mcpServers key regardless of filename."""
        yaml_content = """
mcpServers:
  yaml-server:
    command: python
    args:
      - server.py
"""
        (tmp_path / "agent-config.yaml").write_text(yaml_content)

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert len(results[0].servers) == 1
        assert results[0].servers[0].name == "yaml-server"

    def test_finds_config_with_servers_key(self, scanner, tmp_path):
        """Test scanner finds config with 'servers' key (standard MCP format)."""
        config = {
            "servers": {
                "standard-server": {"command": "uvx", "args": ["mcp-server"]}
            }
        }
        (tmp_path / "random-name.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert len(results[0].servers) == 1
        assert results[0].servers[0].name == "standard-server"

    def test_finds_config_with_gateway_key(self, scanner, tmp_path):
        """Test scanner finds config with 'gateway' key (Docker MCP format)."""
        config = {
            "gateway": {
                "servers": [
                    {"name": "docker-server", "image": "mcp/server"}
                ]
            }
        }
        (tmp_path / "docker-setup.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert len(results[0].servers) == 1
        assert results[0].servers[0].name == "docker-server"

    def test_ignores_non_mcp_json(self, scanner, tmp_path):
        """Test scanner ignores JSON files without MCP indicators."""
        non_mcp = {"name": "package", "version": "1.0.0"}
        (tmp_path / "package.json").write_text(json.dumps(non_mcp))

        results = scanner.scan(tmp_path)

        assert len(results) == 0

    def test_scans_cursor_directory(self, scanner, tmp_path):
        """Test scanner checks .cursor directory for MCP configs."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        config = {
            "mcpServers": {
                "cursor-server": {"command": "npx", "args": ["server"]}
            }
        }
        (cursor_dir / "mcp.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert results[0].servers[0].name == "cursor-server"

    def test_scans_claude_directory(self, scanner, tmp_path):
        """Test scanner checks .claude directory for MCP configs."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        config = {
            "mcpServers": {
                "claude-server": {"command": "npx", "args": ["server"]}
            }
        }
        (claude_dir / "config.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert results[0].servers[0].name == "claude-server"

    def test_no_duplicate_findings_for_known_filenames(self, scanner, tmp_path):
        """Test that known filenames aren't scanned twice."""
        config = {
            "mcpServers": {
                "server": {"command": "npx", "args": ["server"]}
            }
        }
        # Use a known filename
        (tmp_path / "mcp.json").write_text(json.dumps(config))

        results = scanner.scan(tmp_path)

        # Should only appear once, not duplicated
        assert len(results) == 1

    def test_direct_file_scan_nonstandard_name(self, scanner, tmp_path):
        """Test scanning a specific file with non-standard name."""
        config = {
            "mcpServers": {
                "direct-server": {"command": "node", "args": ["server.js"]}
            }
        }
        config_file = tmp_path / "weird-name.json"
        config_file.write_text(json.dumps(config))

        # Scan the file directly
        results = scanner.scan(config_file)

        assert len(results) == 1
        assert results[0].servers[0].name == "direct-server"

    def test_handles_invalid_json_gracefully(self, scanner, tmp_path):
        """Test scanner handles invalid JSON without crashing."""
        (tmp_path / "broken.json").write_text("{ invalid json }")

        results = scanner.scan(tmp_path)

        # Should not crash, just skip invalid files
        assert isinstance(results, list)

    def test_handles_empty_json(self, scanner, tmp_path):
        """Test scanner handles empty JSON object."""
        (tmp_path / "empty.json").write_text("{}")

        results = scanner.scan(tmp_path)

        # Empty object doesn't have mcpServers, should be ignored
        assert len(results) == 0

    def test_multiple_configs_in_directory(self, scanner, tmp_path):
        """Test scanner finds multiple MCP configs in same directory."""
        config1 = {
            "mcpServers": {
                "server1": {"command": "npx", "args": ["server1"]}
            }
        }
        config2 = {
            "mcpServers": {
                "server2": {"command": "node", "args": ["server2.js"]}
            }
        }

        (tmp_path / "mcp.json").write_text(json.dumps(config1))
        (tmp_path / "custom-mcp.json").write_text(json.dumps(config2))

        results = scanner.scan(tmp_path)

        # Should find both configs
        assert len(results) == 2
        server_names = {s.name for r in results for s in r.servers}
        assert "server1" in server_names
        assert "server2" in server_names


class TestMCPConfigRecursiveDiscovery:
    """Regression: MCP configs below the scan root were never discovered.

    `_find_config_files` walked the scan root with `path.iterdir()`, which does
    not recurse, while every other scanner in the package uses `rglob`. A config
    one directory below the scan root was therefore invisible, so AGENT-029/030/
    032 could not fire during an ordinary directory scan — which is how the tool
    is normally invoked, and how the Layer 1 benchmark scans its fixture tree.

    Originating scan: the Layer 1 ASI-04 row read 0.0%; two of its seven labels
    were detections that existed but were unreachable by directory walk.
    """

    @pytest.fixture
    def scanner(self):
        return MCPConfigScanner()

    @staticmethod
    def _write_config(target: Path, server_name: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "mcpServers": {
                server_name: {"command": "npx", "args": ["-y", "some-server"]}
            }
        }))

    @pytest.mark.parametrize("depth", [1, 2, 3])
    def test_finds_config_below_scan_root(self, scanner, tmp_path, depth):
        """A config nested `depth` levels down is found by a scan of the root."""
        nested = tmp_path.joinpath(*[f"level{i}" for i in range(depth)]) / "mcp.json"
        self._write_config(nested, "nested-server")

        results = scanner.scan(tmp_path)

        assert len(results) == 1, f"config at depth {depth} was not discovered"
        assert results[0].servers[0].name == "nested-server"

    def test_nonstandard_filename_below_scan_root(self, scanner, tmp_path):
        """Recursion applies to the content-sniffed path, not just known names."""
        self._write_config(tmp_path / "sub" / "whatever.json", "sniffed-server")

        results = scanner.scan(tmp_path)

        assert len(results) == 1
        assert results[0].servers[0].name == "sniffed-server"

    def test_directory_scan_matches_file_scan(self, scanner, tmp_path):
        """The invariant the bug broke: same file, same servers, either way in."""
        config = tmp_path / "pkg" / "conf" / "mcp.json"
        self._write_config(config, "parity-server")

        via_file = scanner.scan(config)
        via_dir = scanner.scan(tmp_path)

        assert {s.name for r in via_file for s in r.servers} == \
               {s.name for r in via_dir for s in r.servers}

    def test_skips_dependency_and_vcs_directories(self, scanner, tmp_path):
        """Recursion must not walk into node_modules/.git/.venv and friends.

        Without this the fix would read every JSON file in every vendored
        dependency of every scanned repository.
        """
        for noisy in ("node_modules", ".git", "__pycache__", ".venv", "venv"):
            self._write_config(tmp_path / noisy / "mcp.json", f"{noisy}-server")
        self._write_config(tmp_path / "src" / "mcp.json", "real-server")

        results = scanner.scan(tmp_path)

        assert {s.name for r in results for s in r.servers} == {"real-server"}

    def test_each_config_reported_once(self, scanner, tmp_path):
        """A config matching both a known filename and the sniffer is not doubled."""
        self._write_config(tmp_path / "a" / "mcp.json", "known-name")
        self._write_config(tmp_path / "b" / "custom.json", "sniffed-name")

        results = scanner.scan(tmp_path)

        paths = [r.source_file for r in results]
        assert len(paths) == len(set(paths)), f"duplicate config results: {paths}"
        assert len(results) == 2
