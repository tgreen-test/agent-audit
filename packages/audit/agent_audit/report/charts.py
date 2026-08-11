"""Chart generation for PDF audit reports using matplotlib."""

from __future__ import annotations

import io
from typing import Dict, List, Tuple

from agent_audit.report.styles import (
    Colors,
    SEVERITY_COLORS,
    TIER_COLORS,
    OWASP_ASI_CATEGORIES,
    CATEGORY_TO_ASI,
)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Convert (0-1) RGB tuple to hex string."""
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
    )


def _check_matplotlib() -> None:
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for chart generation. "
            "Install with: pip install agent-audit[report]"
        )


def create_severity_bar_chart(by_severity: Dict[str, int]) -> bytes:
    """
    Create horizontal bar chart of findings by severity.

    Args:
        by_severity: Dict mapping severity name to count

    Returns:
        PNG image bytes
    """
    _check_matplotlib()

    severity_order = ["critical", "high", "medium", "low", "info"]
    labels = []
    values = []
    colors = []

    for sev in severity_order:
        count = by_severity.get(sev, 0)
        if count > 0:
            labels.append(sev.upper())
            values.append(count)
            colors.append(_rgb_to_hex(SEVERITY_COLORS.get(sev, Colors.MEDIUM_GRAY)))

    if not labels:
        labels, values, colors = ["None"], [0], [_rgb_to_hex(Colors.MEDIUM_GRAY)]

    fig, ax = plt.subplots(figsize=(5.5, max(1.5, len(labels) * 0.55)))
    bars = ax.barh(labels, values, color=colors, height=0.5, edgecolor="white")

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold",
            )

    ax.set_xlabel("Count", fontsize=9)
    ax.set_title("Findings by Severity", fontsize=11, fontweight="bold", pad=10)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(values) * 1.2 + 1)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def create_tier_donut_chart(by_tier: Dict[str, int]) -> bytes:
    """
    Create donut chart of findings by confidence tier.

    Args:
        by_tier: Dict mapping tier name to count

    Returns:
        PNG image bytes
    """
    _check_matplotlib()

    tier_order = ["BLOCK", "WARN", "INFO", "SUPPRESSED"]
    labels = []
    values = []
    colors = []

    for tier in tier_order:
        count = by_tier.get(tier, 0)
        if count > 0:
            labels.append(tier)
            values.append(count)
            colors.append(_rgb_to_hex(TIER_COLORS.get(tier, Colors.MEDIUM_GRAY)))

    if not labels:
        labels, values, colors = ["None"], [1], [_rgb_to_hex(Colors.MEDIUM_GRAY)]

    fig, ax = plt.subplots(figsize=(4.0, 4.0))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct=lambda pct: f"{int(round(pct * sum(values) / 100))}",
        pctdistance=0.78,
        startangle=90,
        wedgeprops={"width": 0.4, "edgecolor": "white", "linewidth": 2},
    )

    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
        at.set_color("white")

    total = sum(values)
    ax.text(0, 0, str(total), ha="center", va="center", fontsize=20, fontweight="bold")
    ax.text(
        0, -0.12, "Total", ha="center", va="center",
        fontsize=9, color=_rgb_to_hex(Colors.DARK_GRAY),
    )

    legend_patches = [
        mpatches.Patch(color=c, label=f"{l} ({v})")
        for l, v, c in zip(labels, values, colors)
    ]
    ax.legend(
        handles=legend_patches, loc="lower center",
        bbox_to_anchor=(0.5, -0.15), ncol=min(4, len(labels)),
        fontsize=8, frameon=False,
    )

    ax.set_title("Findings by Tier", fontsize=11, fontweight="bold", pad=10)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def create_category_chart(by_category: Dict[str, int]) -> bytes:
    """
    Create horizontal bar chart of findings by OWASP category.

    Args:
        by_category: Dict mapping category name to count

    Returns:
        PNG image bytes
    """
    _check_matplotlib()

    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    if not sorted_cats:
        sorted_cats = [("none", 0)]

    labels = []
    values = []
    colors = []

    palette = [_rgb_to_hex(c) for c in Colors.CHART_PALETTE]
    for i, (cat, count) in enumerate(sorted_cats):
        asi = CATEGORY_TO_ASI.get(cat, "")
        display = f"{asi} {cat.replace('_', ' ').title()}" if asi else cat.replace("_", " ").title()
        labels.append(display)
        values.append(count)
        colors.append(palette[i % len(palette)])

    fig, ax = plt.subplots(figsize=(6.0, max(2.0, len(labels) * 0.45)))
    bars = ax.barh(labels, values, color=colors, height=0.5, edgecolor="white")

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, fontweight="bold",
            )

    ax.set_xlabel("Count", fontsize=9)
    ax.set_title("Findings by OWASP Agentic Category", fontsize=11, fontweight="bold", pad=10)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(values) * 1.2 + 1)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def create_risk_gauge(score: float) -> bytes:
    """
    Create a semicircular risk gauge visualization.

    Args:
        score: Risk score 0.0 - 9.8

    Returns:
        PNG image bytes
    """
    _check_matplotlib()

    import numpy as np

    fig, ax = plt.subplots(figsize=(3.5, 2.2), subplot_kw={"projection": "polar"})

    # Gauge spans from pi to 0 (left to right semicircle)
    theta_bg = np.linspace(np.pi, 0, 100)

    # Background arc segments: green → yellow → red
    segments = [
        (np.linspace(np.pi, np.pi * 0.6, 30), _rgb_to_hex(Colors.RISK_LOW)),
        (np.linspace(np.pi * 0.6, np.pi * 0.3, 30), _rgb_to_hex(Colors.RISK_MEDIUM)),
        (np.linspace(np.pi * 0.3, 0, 30), _rgb_to_hex(Colors.RISK_HIGH)),
    ]

    for thetas, color in segments:
        ax.fill_between(thetas, 0.6, 1.0, color=color, alpha=0.3)

    # Needle position
    normalized = min(score / 10.0, 1.0)
    needle_angle = np.pi * (1 - normalized)
    ax.plot([needle_angle, needle_angle], [0, 0.85], color=_rgb_to_hex(Colors.PRIMARY), linewidth=2.5)
    ax.plot(needle_angle, 0.85, "o", color=_rgb_to_hex(Colors.PRIMARY), markersize=5)
    ax.plot(needle_angle, 0, "o", color=_rgb_to_hex(Colors.PRIMARY), markersize=8)

    ax.set_ylim(0, 1.1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.set_rticks([])
    ax.set_thetagrids([])
    ax.spines["polar"].set_visible(False)
    ax.grid(False)

    # Score text below
    fig.text(0.5, 0.08, f"{score:.1f} / 10.0", ha="center", fontsize=16, fontweight="bold")

    if score < 2.0:
        label, color = "LOW", _rgb_to_hex(Colors.RISK_LOW)
    elif score < 4.0:
        label, color = "LOW-MEDIUM", _rgb_to_hex(Colors.RISK_LOW)
    elif score < 6.0:
        label, color = "MEDIUM", _rgb_to_hex(Colors.RISK_MEDIUM)
    elif score < 8.0:
        label, color = "MEDIUM-HIGH", _rgb_to_hex(Colors.RISK_MEDIUM)
    else:
        label, color = "HIGH", _rgb_to_hex(Colors.RISK_HIGH)

    fig.text(0.5, -0.02, label, ha="center", fontsize=10, fontweight="bold", color=color)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def create_owasp_coverage_chart(
    findings_by_asi: Dict[str, int],
) -> bytes:
    """
    Create OWASP ASI Top 10 coverage heatmap.

    Args:
        findings_by_asi: Dict mapping ASI-XX to finding count

    Returns:
        PNG image bytes
    """
    _check_matplotlib()

    asi_ids = [f"ASI-{i:02d}" for i in range(1, 11)]
    labels = [
        f"{aid}\n{OWASP_ASI_CATEGORIES[aid]['title']}"
        for aid in asi_ids
    ]
    values = [findings_by_asi.get(aid, 0) for aid in asi_ids]
    covered = sum(1 for v in values if v > 0)

    fig, ax = plt.subplots(figsize=(7.0, 2.5))

    bar_colors = []
    for v in values:
        if v == 0:
            bar_colors.append(_rgb_to_hex(Colors.LIGHT_GRAY))
        elif v <= 3:
            bar_colors.append(_rgb_to_hex(Colors.RISK_LOW))
        elif v <= 10:
            bar_colors.append(_rgb_to_hex(Colors.RISK_MEDIUM))
        else:
            bar_colors.append(_rgb_to_hex(Colors.RISK_HIGH))

    bars = ax.bar(range(len(asi_ids)), values, color=bar_colors, edgecolor="white", width=0.7)

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", fontsize=8, fontweight="bold",
            )

    ax.set_xticks(range(len(asi_ids)))
    ax.set_xticklabels(
        [f"{aid}" for aid in asi_ids],
        fontsize=7, rotation=45, ha="right",
    )
    ax.set_title(
        f"OWASP Agentic Top 10 Coverage ({covered}/10)",
        fontsize=11, fontweight="bold", pad=10,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("Findings", fontsize=9)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
