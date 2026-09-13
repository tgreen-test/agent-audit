"""The Python side of the differential.

`semantic_analyzer` builds a `TreeSitterParser` per file, and `tree_sitter_python`
exposes the `LANGUAGE` attribute the parser already recognises. Installing the
`tree-sitter` extra therefore switches the Python credential path over with **no code
change at all** — which is why a differential that only looked at `.ts` files would
answer the wrong question.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field

# A literal that looks like a credential.
OPENAI_API_KEY = "sk-proj-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# A read from the environment — not a credential.
RUNTIME_KEY = os.environ["SERVICE_API_KEY"]
FALLBACK_KEY = os.getenv("SERVICE_API_KEY", "")

# A function call — not a credential.
ROTATED_KEY = os.popen("cat /dev/null").read()

# A UUID, which the value analyser is meant to reject.
CORRELATION_TOKEN = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"

# A placeholder, which the placeholder detector is meant to reject.
PLACEHOLDER_SECRET = "your-api-key-here"


class ServiceConfig(BaseModel):
    """A schema definition, not a credential."""

    api_key: Optional[str] = Field(default=None, description="API key")
    password: Optional[str] = None
    token: str = Field(...)


def build_client(api_key: str):
    """A parameter named like a credential is not a credential."""
    return {"api_key": api_key}
