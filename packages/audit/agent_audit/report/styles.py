"""PDF styling constants for agent-audit reports."""

from __future__ import annotations


# --- Color Palette ---

class Colors:
    """Report color palette (RGB tuples, 0-1 range for reportlab)."""

    # Brand
    PRIMARY = (0.13, 0.15, 0.23)       # Dark navy
    ACCENT = (0.20, 0.47, 0.96)        # Blue accent
    WHITE = (1.0, 1.0, 1.0)
    LIGHT_GRAY = (0.95, 0.95, 0.97)
    MEDIUM_GRAY = (0.70, 0.70, 0.73)
    DARK_GRAY = (0.40, 0.40, 0.43)
    BLACK = (0.0, 0.0, 0.0)

    # Severity
    CRITICAL = (0.86, 0.15, 0.15)      # Red
    HIGH = (0.93, 0.49, 0.13)          # Orange
    MEDIUM = (0.95, 0.75, 0.10)        # Yellow-amber
    LOW = (0.20, 0.65, 0.33)           # Green
    INFO = (0.55, 0.55, 0.58)          # Gray

    # Risk gauge
    RISK_LOW = (0.20, 0.72, 0.40)
    RISK_MEDIUM = (0.95, 0.75, 0.10)
    RISK_HIGH = (0.86, 0.15, 0.15)

    # Tier badges
    TIER_BLOCK = (0.86, 0.15, 0.15)
    TIER_WARN = (0.93, 0.49, 0.13)
    TIER_INFO = (0.20, 0.47, 0.96)
    TIER_SUPPRESSED = (0.70, 0.70, 0.73)

    # Chart palette (for category breakdown)
    CHART_PALETTE = [
        (0.23, 0.47, 0.84),   # Blue
        (0.86, 0.15, 0.15),   # Red
        (0.93, 0.49, 0.13),   # Orange
        (0.20, 0.65, 0.33),   # Green
        (0.55, 0.27, 0.68),   # Purple
        (0.95, 0.75, 0.10),   # Yellow
        (0.17, 0.63, 0.73),   # Teal
        (0.80, 0.33, 0.38),   # Rose
        (0.40, 0.55, 0.25),   # Olive
        (0.33, 0.33, 0.55),   # Slate
        (0.73, 0.50, 0.25),   # Brown
        (0.60, 0.60, 0.60),   # Gray
        (0.45, 0.70, 0.85),   # Light blue
    ]


SEVERITY_COLORS = {
    "critical": Colors.CRITICAL,
    "high": Colors.HIGH,
    "medium": Colors.MEDIUM,
    "low": Colors.LOW,
    "info": Colors.INFO,
}

TIER_COLORS = {
    "BLOCK": Colors.TIER_BLOCK,
    "WARN": Colors.TIER_WARN,
    "INFO": Colors.TIER_INFO,
    "SUPPRESSED": Colors.TIER_SUPPRESSED,
}


# --- Page Layout ---

PAGE_MARGIN_LEFT = 50
PAGE_MARGIN_RIGHT = 50
PAGE_MARGIN_TOP = 60
PAGE_MARGIN_BOTTOM = 60


# --- OWASP ASI Mapping ---

OWASP_ASI_CATEGORIES = {
    "ASI-01": {
        "title": "Prompt Injection / Goal Hijack",
        "description": "Adversarial prompts that redirect agent behavior",
    },
    "ASI-02": {
        "title": "Tool Misuse",
        "description": "Unsafe tool invocation allowing command injection or data exfiltration",
    },
    "ASI-03": {
        "title": "Identity & Privilege Abuse",
        "description": "Agents operating with excessive permissions or impersonating users",
    },
    "ASI-04": {
        "title": "Supply Chain (Agentic)",
        "description": "Compromised plugins, tools, or dependencies in agent pipelines",
    },
    "ASI-05": {
        "title": "Unexpected Code Execution",
        "description": "Uncontrolled eval/exec of LLM-generated or user-supplied code",
    },
    "ASI-06": {
        "title": "Memory Poisoning",
        "description": "Tampering with agent memory or conversation history",
    },
    "ASI-07": {
        "title": "Insecure Inter-Agent Communication",
        "description": "Unvalidated messages between agents in multi-agent systems",
    },
    "ASI-08": {
        "title": "Cascading Failures",
        "description": "Error propagation and uncontrolled retry loops in agent chains",
    },
    "ASI-09": {
        "title": "Trust Exploitation",
        "description": "Agents trusting unverified external data or tool outputs",
    },
    "ASI-10": {
        "title": "Rogue Agent",
        "description": "Agents acting outside their defined scope or without guardrails",
    },
}

# Map category enum values to ASI IDs
CATEGORY_TO_ASI = {
    "goal_hijack": "ASI-01",
    "tool_misuse": "ASI-02",
    "command_injection": "ASI-02",
    "identity_privilege_abuse": "ASI-03",
    "excessive_permission": "ASI-03",
    "supply_chain_agentic": "ASI-04",
    "unexpected_code_execution": "ASI-05",
    "memory_poisoning": "ASI-06",
    "insecure_inter_agent_comm": "ASI-07",
    "cascading_failures": "ASI-08",
    "trust_exploitation": "ASI-09",
    "rogue_agent": "ASI-10",
    "credential_exposure": "ASI-04",
}
