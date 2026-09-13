"""Regression guard: a bare 40-hex string is a digest, not an AWS secret key.

The AWS secret-key pattern in secret_scanner.py is a bare 40-character run over
the base64 alphabet:

    (?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])

Every SHA-1 satisfies it. On a repository that pins content by checksum — git
object ids, `sha1sum` output, lockfiles, translation manifests — this produced
462 "Potential AWS Secret Key" findings, the single largest noise family in the
scan that motivated this fix.

An AWS secret access key is 40 characters of base64 and is essentially never
all-hex. A 40-character all-hex string is essentially always a digest. That is a
shape fact about the value, so it is tested as one.

Every credential literal below is synthetic and was written for this file.

Regression source: the audit-target evaluation recorded in NIGHT_RUN_LEDGER.md
§ W14, pattern 1.
"""

from __future__ import annotations

import pytest

from agent_audit.analysis.value_analyzer import detect_hex_digest_format
from agent_audit.analysis.semantic_analyzer import get_analyzer


class TestHexDigestShape:
    """The shape predicate in isolation."""

    @pytest.mark.parametrize("value", [
        "356a192b7913b04c54574d18c28d46e6395428ab",   # sha1("1")
        "da4b9237bacccdf19c0760cab7aec4a8359010b0",   # sha1("2")
        "77de68daecd823babbb58edb1c8e14d7106e83bb",   # sha1("3")
        "356A192B7913B04C54574D18C28D46E6395428AB",   # uppercase
        "  356a192b7913b04c54574d18c28d46e6395428ab  ",  # surrounding space
    ])
    def test_forty_hex_is_a_digest(self, value):
        assert detect_hex_digest_format(value).is_digest is True

    @pytest.mark.parametrize("value", [
        # A real-shaped AWS secret: 40 chars, base64 alphabet, not all hex.
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/==",
        # Wrong length — 39 and 41 hex.
        "356a192b7913b04c54574d18c28d46e6395428a",
        "356a192b7913b04c54574d18c28d46e6395428abc",
        # 64 hex is deliberately NOT suppressed: it is SHA-256, but it is also a
        # secp256k1 private key with the 0x stripped, which is a real credential.
        "0" * 64,
        "",
    ])
    def test_non_digest_shapes_are_not_suppressed(self, value):
        assert detect_hex_digest_format(value).is_digest is False

    def test_sixty_four_hex_stays_detectable_as_a_private_key(self):
        """Explicit control for the shape we chose not to add.

        Suppressing 64-hex by length would trade this false positive for a
        missed private key. If this test ever fails, someone added SHA-256 to
        HEX_DIGEST_PATTERNS without accounting for that.
        """
        assert detect_hex_digest_format("a" * 64).is_digest is False


class TestSemanticAnalyzerIntegration:
    """The predicate as the scanner actually reaches it."""

    @pytest.fixture(scope="class")
    def analyzer(self):
        return get_analyzer()

    def _verdict(self, analyzer, line, identifier, value):
        """Run one candidate through the three-stage pipeline."""
        return analyzer.analyze_single_match(
            identifier=identifier,
            value=value,
            line=1,
            column=0,
            end_column=len(line),
            raw_line=line,
            file_path="manifest.yaml",
            pattern_name="Potential AWS Secret Key",
        )

    # --- false positives that must now be suppressed ---

    def test_checksum_manifest_entry_suppressed(self, analyzer):
        """The exact shape that produced 462 findings: name mapped to a SHA-1."""
        sha = "356a192b7913b04c54574d18c28d46e6395428ab"
        result = self._verdict(analyzer, f"README.md: {sha}", "README.md", sha)
        assert result.should_report is False

    def test_credential_named_identifier_does_not_rescue_a_digest(self, analyzer):
        """`api_key` holding a SHA-1 is a content hash under a bad name."""
        sha = "da4b9237bacccdf19c0760cab7aec4a8359010b0"
        result = self._verdict(analyzer, f"api_key: {sha}", "api_key", sha)
        assert result.should_report is False

    # --- TRUE-POSITIVE CONTROLS: these must still fire ---

    def test_real_aws_secret_shape_still_fires(self, analyzer):
        """The control that makes this fix acceptable.

        A genuine AWS secret is 40 base64 characters and is not all hex, so the
        digest predicate must not touch it.
        """
        # Synthetic. Deliberately NOT AWS's published example key
        # (wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY) — the scanner suppresses
        # that one as a known vendor example, correctly, and using it here would
        # have made this control pass for the wrong reason.
        secret = "kR7pQz2mXf9TnB4vLc8dW1sYgH3jA6eU0oI5rZtN"
        result = self._verdict(
            analyzer, f'aws_secret_access_key = "{secret}"', "aws_secret_access_key", secret
        )
        assert result.should_report is True

    def test_private_key_hex_still_fires(self, analyzer):
        """64 hex under a credential name must survive — see the shape control."""
        key = "4c0883a69102937d6231471b5dbb6204fe512961708279e6f6b1f0b1d1b1a1c1"
        result = self._verdict(analyzer, f'private_key = "{key}"', "private_key", key)
        assert result.should_report is True
