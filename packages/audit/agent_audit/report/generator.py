"""PDF audit report generator for agent-audit scan results."""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent_audit.report.styles import (
    Colors,
    SEVERITY_COLORS,
    TIER_COLORS,
    OWASP_ASI_CATEGORIES,
    CATEGORY_TO_ASI,
    PAGE_MARGIN_LEFT,
    PAGE_MARGIN_RIGHT,
    PAGE_MARGIN_TOP,
    PAGE_MARGIN_BOTTOM,
)

try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        NextPageTemplate,
        PageBreak,
        PageTemplate,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.graphics.shapes import Drawing, Rect, String
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _check_deps() -> None:
    if not HAS_REPORTLAB:
        raise ImportError(
            "reportlab is required for PDF report generation. "
            "Install with: pip install agent-audit[report]"
        )


def _rl_color(rgb: Tuple[float, float, float]) -> Any:
    """Convert RGB tuple to reportlab Color."""
    return rl_colors.Color(rgb[0], rgb[1], rgb[2])


def _severity_label(sev: str) -> str:
    return sev.upper()


class ReportGenerator:
    """
    Generate professional PDF compliance reports from agent-audit scan JSON.

    Usage:
        gen = ReportGenerator()
        gen.generate("/path/to/scan.json", "/path/to/report.pdf")

    Or from dict:
        gen = ReportGenerator()
        gen.generate_from_data(scan_data, "/path/to/report.pdf")
    """

    def __init__(
        self,
        *,
        title: str = "AI Agent Security Audit Report",
        organization: str = "",
        logo_path: Optional[str] = None,
        include_suppressed: bool = False,
    ):
        _check_deps()
        self.title = title
        self.organization = organization
        self.logo_path = logo_path
        self.include_suppressed = include_suppressed
        self._styles = self._create_styles()

    def generate(self, input_path: str, output_path: str) -> str:
        """
        Generate PDF report from scan JSON file.

        Args:
            input_path: Path to scan result JSON file
            output_path: Path for output PDF file

        Returns:
            Absolute path to generated PDF
        """
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        return self.generate_from_data(data, output_path)

    def generate_from_data(self, data: Dict[str, Any], output_path: str) -> str:
        """
        Generate PDF report from scan data dict.

        Args:
            data: Parsed scan JSON data
            output_path: Path for output PDF file

        Returns:
            Absolute path to generated PDF
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(out),
            pagesize=A4,
            leftMargin=PAGE_MARGIN_LEFT,
            rightMargin=PAGE_MARGIN_RIGHT,
            topMargin=PAGE_MARGIN_TOP,
            bottomMargin=PAGE_MARGIN_BOTTOM,
            title=self.title,
            author="agent-audit",
        )

        story = []
        story.extend(self._build_cover_page(data))
        story.append(PageBreak())
        story.extend(self._build_executive_summary(data))
        story.append(PageBreak())
        story.extend(self._build_charts_section(data))
        story.append(PageBreak())
        story.extend(self._build_owasp_coverage(data))
        story.append(PageBreak())
        story.extend(self._build_findings_detail(data))
        story.append(PageBreak())
        story.extend(self._build_remediation_roadmap(data))
        story.append(PageBreak())
        story.extend(self._build_methodology(data))

        doc.build(story, onFirstPage=self._page_footer, onLaterPages=self._page_footer)
        return str(out.resolve())

    # ---------------------------------------------------------------
    # Styles
    # ---------------------------------------------------------------

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "cover_title": ParagraphStyle(
                "cover_title",
                parent=base["Title"],
                fontSize=28,
                leading=34,
                textColor=_rl_color(Colors.WHITE),
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            "cover_subtitle": ParagraphStyle(
                "cover_subtitle",
                parent=base["Normal"],
                fontSize=14,
                leading=18,
                textColor=_rl_color(Colors.WHITE),
                alignment=TA_CENTER,
                spaceAfter=6,
            ),
            "cover_meta": ParagraphStyle(
                "cover_meta",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                textColor=rl_colors.Color(0.85, 0.85, 0.88),
                alignment=TA_CENTER,
            ),
            "h1": ParagraphStyle(
                "h1",
                parent=base["Heading1"],
                fontSize=18,
                leading=22,
                textColor=_rl_color(Colors.PRIMARY),
                spaceBefore=20,
                spaceAfter=14,
            ),
            "h2": ParagraphStyle(
                "h2",
                parent=base["Heading2"],
                fontSize=14,
                leading=18,
                textColor=_rl_color(Colors.PRIMARY),
                spaceBefore=16,
                spaceAfter=10,
            ),
            "h3": ParagraphStyle(
                "h3",
                parent=base["Heading3"],
                fontSize=11,
                leading=14,
                textColor=_rl_color(Colors.ACCENT),
                spaceBefore=8,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "body",
                parent=base["Normal"],
                fontSize=9,
                leading=13,
                textColor=_rl_color(Colors.BLACK),
                spaceAfter=6,
                alignment=TA_JUSTIFY,
            ),
            "body_small": ParagraphStyle(
                "body_small",
                parent=base["Normal"],
                fontSize=8,
                leading=11,
                textColor=_rl_color(Colors.DARK_GRAY),
                spaceAfter=4,
            ),
            "code": ParagraphStyle(
                "code",
                parent=base["Code"],
                fontSize=7.5,
                leading=10,
                textColor=_rl_color(Colors.PRIMARY),
                backColor=_rl_color(Colors.LIGHT_GRAY),
                borderPadding=4,
                spaceAfter=6,
            ),
            "table_header": ParagraphStyle(
                "table_header",
                parent=base["Normal"],
                fontSize=8,
                leading=10,
                textColor=_rl_color(Colors.WHITE),
                fontName="Helvetica-Bold",
            ),
            "table_cell": ParagraphStyle(
                "table_cell",
                parent=base["Normal"],
                fontSize=8,
                leading=10,
                textColor=_rl_color(Colors.BLACK),
            ),
            "metric_value": ParagraphStyle(
                "metric_value",
                parent=base["Normal"],
                fontSize=22,
                leading=26,
                textColor=_rl_color(Colors.PRIMARY),
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            "metric_label": ParagraphStyle(
                "metric_label",
                parent=base["Normal"],
                fontSize=8,
                leading=10,
                textColor=_rl_color(Colors.DARK_GRAY),
                alignment=TA_CENTER,
            ),
        }

    # ---------------------------------------------------------------
    # Cover Page
    # ---------------------------------------------------------------

    def _build_cover_page(self, data: Dict[str, Any]) -> List:
        story = []
        summary = data.get("summary", {})
        risk_score = summary.get("risk_score", 0.0)
        risk_label = summary.get("risk_label", "N/A")
        version = data.get("version", "")
        scan_ts = data.get("scan_timestamp", "")
        scan_path = data.get("scan_path", "")

        # Background block (simulated with a colored table)
        cover_data = [[""]]
        cover_inner = []

        # Logo
        if self.logo_path and Path(self.logo_path).exists():
            cover_inner.append(Spacer(1, 30))
            cover_inner.append(Image(self.logo_path, width=80, height=80))
            cover_inner.append(Spacer(1, 20))
        else:
            cover_inner.append(Spacer(1, 80))

        cover_inner.append(Paragraph(self.title, self._styles["cover_title"]))
        cover_inner.append(Spacer(1, 8))

        if self.organization:
            cover_inner.append(
                Paragraph(self.organization, self._styles["cover_subtitle"])
            )
            cover_inner.append(Spacer(1, 12))

        # Risk score badge
        risk_color = Colors.RISK_LOW
        if risk_score >= 8.0:
            risk_color = Colors.RISK_HIGH
        elif risk_score >= 4.0:
            risk_color = Colors.RISK_MEDIUM

        risk_text = f'Risk Score: <font color="#{int(risk_color[0]*255):02x}{int(risk_color[1]*255):02x}{int(risk_color[2]*255):02x}"><b>{risk_score:.1f}</b></font> ({risk_label})'
        cover_inner.append(Paragraph(risk_text, self._styles["cover_subtitle"]))
        cover_inner.append(Spacer(1, 16))

        # Compliance status badge
        by_tier = summary.get("by_tier", {})
        block_count = by_tier.get("BLOCK", 0)
        warn_count = by_tier.get("WARN", 0)
        compliance = self._compute_compliance(block_count, warn_count)

        badge_bg = {
            "FAIL": (0.86, 0.15, 0.15),
            "CONDITIONAL PASS": (0.95, 0.75, 0.10),
            "PASS": (0.20, 0.65, 0.33),
        }[compliance["status"]]
        badge_fg = "ffffff" if compliance["status"] != "CONDITIONAL PASS" else "000000"

        badge_data = [[
            Paragraph(
                f'<font color="#{badge_fg}"><b>COMPLIANCE STATUS: {compliance["status"]}</b></font>',
                ParagraphStyle(
                    "badge_title", fontSize=18, leading=24,
                    alignment=TA_CENTER, fontName="Helvetica-Bold",
                    textColor=rl_colors.HexColor(f"#{badge_fg}"),
                ),
            ),
        ], [
            Paragraph(
                f'<font color="#{badge_fg}">{compliance["message"]}</font>',
                ParagraphStyle(
                    "badge_msg", fontSize=10, leading=14,
                    alignment=TA_CENTER,
                    textColor=rl_colors.HexColor(f"#{badge_fg}"),
                ),
            ),
        ]]
        badge_table = Table(badge_data, colWidths=[400], rowHeights=[40, 28])
        badge_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _rl_color(badge_bg)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 24),
            ("RIGHTPADDING", (0, 0), (-1, -1), 24),
            ("TOPPADDING", (0, 0), (0, 0), 10),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ("ROUNDEDCORNERS", (0, 0), (-1, -1), [10, 10, 10, 10]),
        ]))
        cover_inner.append(badge_table)
        cover_inner.append(Spacer(1, 20))

        # Metadata
        if scan_ts:
            try:
                dt = datetime.fromisoformat(scan_ts)
                formatted_ts = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, TypeError):
                formatted_ts = scan_ts
            cover_inner.append(
                Paragraph(f"Scan Date: {formatted_ts}", self._styles["cover_meta"])
            )

        if scan_path:
            display_path = Path(scan_path).name or scan_path
            cover_inner.append(
                Paragraph(f"Target: {display_path}", self._styles["cover_meta"])
            )

        cover_inner.append(
            Paragraph(
                f"Scanner Version: agent-audit {version}",
                self._styles["cover_meta"],
            )
        )
        cover_inner.append(
            Paragraph(
                f"Report Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                self._styles["cover_meta"],
            )
        )

        cover_inner.append(Spacer(1, 40))
        cover_inner.append(
            Paragraph(
                "Based on OWASP Agentic Security Initiative (ASI) Top 10 — 2026",
                self._styles["cover_meta"],
            )
        )

        # Wrap in a colored table for background
        cover_data = [[cover_inner]]
        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        cover_table = Table(cover_data, colWidths=[page_w], rowHeights=[580])
        cover_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _rl_color(Colors.PRIMARY)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 30),
                ("RIGHTPADDING", (0, 0), (-1, -1), 30),
                ("TOPPADDING", (0, 0), (-1, -1), 20),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
                ("ROUNDEDCORNERS", (0, 0), (-1, -1), [8, 8, 8, 8]),
            ])
        )
        story.append(cover_table)
        return story

    # ---------------------------------------------------------------
    # Executive Summary
    # ---------------------------------------------------------------

    def _build_executive_summary(self, data: Dict[str, Any]) -> List:
        story = []
        summary = data.get("summary", {})
        findings = data.get("findings", [])

        story.append(Paragraph("1. Executive Summary", self._styles["h1"]))

        # Key metrics cards
        total = summary.get("total", 0)
        actionable = summary.get("actionable", 0)
        risk_score = summary.get("risk_score", 0.0)
        risk_label = summary.get("risk_label", "N/A")
        scanned = data.get("scanned_files", 0)
        by_tier = summary.get("by_tier", {})

        metrics = [
            (str(total), "Total Findings"),
            (str(actionable), "Actionable"),
            (str(by_tier.get("BLOCK", 0)), "BLOCK Tier"),
            (str(by_tier.get("WARN", 0)), "WARN Tier"),
            (f"{risk_score:.1f}", f"Risk ({risk_label})"),
            (str(scanned), "Files Scanned"),
        ]

        metric_cells = []
        for val, label in metrics:
            cell_content = [
                Paragraph(val, self._styles["metric_value"]),
                Paragraph(label, self._styles["metric_label"]),
            ]
            metric_cells.append(cell_content)

        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        col_w = page_w / 6
        metric_table = Table([metric_cells], colWidths=[col_w] * 6, rowHeights=[65])
        metric_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, _rl_color(Colors.MEDIUM_GRAY)),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, _rl_color(Colors.LIGHT_GRAY)),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(metric_table)
        story.append(Spacer(1, 16))

        # Summary paragraph
        by_severity = summary.get("by_severity", {})
        critical_count = by_severity.get("critical", 0)
        high_count = by_severity.get("high", 0)

        summary_text = (
            f"The scan analyzed <b>{scanned}</b> files and identified "
            f"<b>{total}</b> potential security findings, of which "
            f"<b>{actionable}</b> are actionable (confidence tier BLOCK, WARN, or INFO). "
        )
        if critical_count > 0:
            summary_text += (
                f"<b>{critical_count}</b> findings are rated <font color='#db2626'><b>CRITICAL</b></font> severity. "
            )
        if high_count > 0:
            summary_text += (
                f"<b>{high_count}</b> findings are rated <font color='#ed7d21'><b>HIGH</b></font> severity. "
            )
        summary_text += (
            f"The overall risk score is <b>{risk_score:.1f}</b> ({risk_label})."
        )
        story.append(Paragraph(summary_text, self._styles["body"]))
        story.append(Spacer(1, 8))

        # Compliance Verdict
        by_tier = summary.get("by_tier", {})
        block_count = by_tier.get("BLOCK", 0)
        warn_count = by_tier.get("WARN", 0)
        compliance = self._compute_compliance(block_count, warn_count)
        verdict_text = self._build_compliance_verdict(
            compliance, block_count, warn_count, findings, summary
        )
        story.append(Paragraph("Compliance Verdict", self._styles["h2"]))
        story.append(Paragraph(verdict_text, self._styles["body"]))
        story.append(Spacer(1, 8))

        # Top Risk Rules table
        top_rules = self._compute_top_risk_rules(findings, top_n=3)
        if top_rules:
            story.append(Paragraph("Top Risk Rules", self._styles["h2"]))
            tr_header = [
                Paragraph("Rule ID", self._styles["table_header"]),
                Paragraph("Severity", self._styles["table_header"]),
                Paragraph("Count", self._styles["table_header"]),
                Paragraph("Impact Summary", self._styles["table_header"]),
            ]
            tr_rows = [tr_header]
            for rule_id, sev, count, desc_short in top_rules:
                sev_color = SEVERITY_COLORS.get(sev, Colors.MEDIUM_GRAY)
                sev_hex = f"#{int(sev_color[0]*255):02x}{int(sev_color[1]*255):02x}{int(sev_color[2]*255):02x}"
                tr_rows.append([
                    Paragraph(f"<b>{rule_id}</b>", self._styles["table_cell"]),
                    Paragraph(
                        f'<font color="{sev_hex}"><b>{sev.upper()}</b></font>',
                        self._styles["table_cell"],
                    ),
                    Paragraph(str(count), self._styles["table_cell"]),
                    Paragraph(desc_short, self._styles["table_cell"]),
                ])
            tr_table = Table(
                tr_rows,
                colWidths=[page_w * 0.15, page_w * 0.13, page_w * 0.10, page_w * 0.62],
            )
            tr_table.setStyle(self._table_style(len(tr_rows)))
            story.append(tr_table)
            story.append(Spacer(1, 8))

        # Severity breakdown table
        story.append(Paragraph("Severity Breakdown", self._styles["h2"]))
        sev_header = [
            Paragraph("Severity", self._styles["table_header"]),
            Paragraph("Count", self._styles["table_header"]),
            Paragraph("Percentage", self._styles["table_header"]),
        ]
        sev_rows = [sev_header]

        severity_order = ["critical", "high", "medium", "low", "info"]
        for sev in severity_order:
            count = by_severity.get(sev, 0)
            if count > 0:
                pct = f"{count / max(total, 1) * 100:.1f}%"
                sev_rows.append([
                    Paragraph(f"<b>{sev.upper()}</b>", self._styles["table_cell"]),
                    Paragraph(str(count), self._styles["table_cell"]),
                    Paragraph(pct, self._styles["table_cell"]),
                ])

        sev_table = Table(sev_rows, colWidths=[page_w * 0.4, page_w * 0.3, page_w * 0.3])
        sev_table.setStyle(self._table_style(len(sev_rows)))
        story.append(sev_table)

        return story

    # ---------------------------------------------------------------
    # Charts Section
    # ---------------------------------------------------------------

    def _build_charts_section(self, data: Dict[str, Any]) -> List:
        story = []
        summary = data.get("summary", {})

        story.append(Paragraph("2. Visual Analysis", self._styles["h1"]))

        try:
            from agent_audit.report.charts import (
                create_severity_bar_chart,
                create_tier_donut_chart,
                create_category_chart,
            )
        except ImportError:
            story.append(Paragraph(
                "<i>Charts unavailable — install matplotlib: pip install agent-audit[report]</i>",
                self._styles["body"],
            ))
            return story

        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        chart_w = page_w * 0.80

        def _chart_image(png_bytes: bytes, target_w: float) -> Image:
            """Create Image scaled to target_w, preserving actual PNG aspect ratio."""
            from PIL import Image as PILImage
            buf = io.BytesIO(png_bytes)
            with PILImage.open(buf) as img:
                px_w, px_h = img.size
            ratio = px_h / px_w
            buf2 = io.BytesIO(png_bytes)
            return Image(buf2, width=target_w, height=target_w * ratio)

        # Severity bar chart
        by_severity = summary.get("by_severity", {})
        sev_bytes = create_severity_bar_chart(by_severity)
        story.append(_chart_image(sev_bytes, chart_w))
        story.append(Spacer(1, 16))

        # Tier donut chart
        by_tier = summary.get("by_tier", {})
        tier_bytes = create_tier_donut_chart(by_tier)
        story.append(_chart_image(tier_bytes, chart_w * 0.70))

        # Category chart on next page
        by_category = summary.get("by_category", {})
        if by_category:
            story.append(PageBreak())
            story.append(Paragraph("2b. Category Breakdown", self._styles["h1"]))
            story.append(Spacer(1, 8))
            cat_bytes = create_category_chart(by_category)
            story.append(_chart_image(cat_bytes, page_w * 0.88))

        return story

    # ---------------------------------------------------------------
    # OWASP Coverage
    # ---------------------------------------------------------------

    def _build_owasp_coverage(self, data: Dict[str, Any]) -> List:
        story = []
        findings = data.get("findings", [])
        summary = data.get("summary", {})
        by_category = summary.get("by_category", {})

        story.append(Paragraph("3. OWASP Agentic Top 10 Coverage", self._styles["h1"]))

        # Build ASI counts from findings
        findings_by_asi: Dict[str, int] = {}
        for f in findings:
            asi_cats = f.get("asi_categories", [])
            owasp_id = f.get("owasp_id", "")
            category = f.get("category", "")

            # Use asi_categories first, fall back to owasp_id, then category mapping
            asi_ids = set()
            if asi_cats:
                asi_ids.update(asi_cats)
            elif owasp_id:
                asi_ids.add(owasp_id)
            elif category:
                mapped = CATEGORY_TO_ASI.get(category, "")
                if mapped:
                    asi_ids.add(mapped)

            for asi in asi_ids:
                findings_by_asi[asi] = findings_by_asi.get(asi, 0) + 1

        # Chart
        try:
            from agent_audit.report.charts import create_owasp_coverage_chart
            page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
            chart_bytes = create_owasp_coverage_chart(findings_by_asi)
            chart_img = Image(io.BytesIO(chart_bytes), width=page_w * 0.9, height=180)
            story.append(chart_img)
            story.append(Spacer(1, 12))
        except ImportError:
            pass

        # Coverage table
        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        header = [
            Paragraph("ASI ID", self._styles["table_header"]),
            Paragraph("Category", self._styles["table_header"]),
            Paragraph("Findings", self._styles["table_header"]),
            Paragraph("Status", self._styles["table_header"]),
        ]
        rows = [header]

        for asi_id in [f"ASI-{i:02d}" for i in range(1, 11)]:
            info = OWASP_ASI_CATEGORIES.get(asi_id, {})
            count = findings_by_asi.get(asi_id, 0)
            status = "COVERED" if count > 0 else "No findings"
            rows.append([
                Paragraph(f"<b>{asi_id}</b>", self._styles["table_cell"]),
                Paragraph(info.get("title", ""), self._styles["table_cell"]),
                Paragraph(str(count), self._styles["table_cell"]),
                Paragraph(
                    f'<font color="#33a654"><b>{status}</b></font>' if count > 0
                    else f'<font color="#b3b3ba">{status}</font>',
                    self._styles["table_cell"],
                ),
            ])

        covered = sum(1 for aid in [f"ASI-{i:02d}" for i in range(1, 11)] if findings_by_asi.get(aid, 0) > 0)
        rows.append([
            Paragraph("<b>Total</b>", self._styles["table_cell"]),
            Paragraph("", self._styles["table_cell"]),
            Paragraph(f"<b>{sum(findings_by_asi.values())}</b>", self._styles["table_cell"]),
            Paragraph(f"<b>{covered}/10 covered</b>", self._styles["table_cell"]),
        ])

        cov_table = Table(
            rows,
            colWidths=[page_w * 0.12, page_w * 0.45, page_w * 0.15, page_w * 0.28],
        )
        cov_table.setStyle(self._table_style(len(rows)))
        story.append(cov_table)

        return story

    # ---------------------------------------------------------------
    # Detailed Findings
    # ---------------------------------------------------------------

    def _build_findings_detail(self, data: Dict[str, Any]) -> List:
        story = []
        all_findings = data.get("findings", [])

        story.append(Paragraph("4. Detailed Findings", self._styles["h1"]))

        # Separate suppressed from actionable
        suppressed = [f for f in all_findings if f.get("suppressed", False)]
        actionable = [f for f in all_findings if not f.get("suppressed", False)]

        if not actionable and not suppressed:
            story.append(Paragraph("No findings detected.", self._styles["body"]))
            return story

        if not actionable:
            story.append(Paragraph("No actionable findings detected.", self._styles["body"]))
        else:
            # Group actionable findings by rule_id
            rule_groups: Dict[str, List[Dict]] = {}
            for f in actionable:
                rid = f.get("rule_id", "UNKNOWN")
                rule_groups.setdefault(rid, []).append(f)

            # Sort rule groups: by max severity weight desc, then count desc
            severity_sort = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            sorted_rules = sorted(
                rule_groups.items(),
                key=lambda x: (
                    min(severity_sort.get(f.get("severity", "info"), 4) for f in x[1]),
                    -len(x[1]),
                ),
            )

            page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT

            for rule_id, rule_findings in sorted_rules:
                story.extend(
                    self._build_rule_group(rule_id, rule_findings, page_w)
                )

        # Suppressed summary (single line, no individual cards)
        if suppressed:
            story.append(Spacer(1, 12))
            story.append(
                Paragraph(
                    f'<font color="#b3b3ba"><b>SUPPRESSED</b></font> — '
                    f'{len(suppressed)} findings suppressed (confidence &lt; 0.30). '
                    f'Available in full JSON output.',
                    self._styles["body"],
                )
            )

        return story

    def _build_rule_group(
        self, rule_id: str, findings: List[Dict], page_w: float
    ) -> List:
        """Build a grouped section for all findings of one rule_id."""
        elements = []
        representative = findings[0]
        title = representative.get("title", "")
        sev = representative.get("severity", "medium")
        sev_color = SEVERITY_COLORS.get(sev, Colors.MEDIUM_GRAY)
        sev_hex = f"#{int(sev_color[0]*255):02x}{int(sev_color[1]*255):02x}{int(sev_color[2]*255):02x}"
        tier = representative.get("tier", "WARN")
        tier_color = TIER_COLORS.get(tier, Colors.MEDIUM_GRAY)
        tier_hex = f"#{int(tier_color[0]*255):02x}{int(tier_color[1]*255):02x}{int(tier_color[2]*255):02x}"

        # Rule header
        elements.append(
            Paragraph(
                f'<b>{rule_id}</b> — {title} '
                f'<font color="{sev_hex}">[{sev.upper()}]</font> '
                f'<font color="{tier_hex}">({len(findings)} occurrences)</font>',
                self._styles["h3"],
            )
        )

        # Description (once)
        desc = representative.get("description", "")
        if desc:
            elements.append(Paragraph(desc, self._styles["body_small"]))

        # CWE / OWASP metadata (once)
        cwe = representative.get("cwe_id", "")
        owasp = representative.get("owasp_id", "")
        meta_parts = []
        if cwe:
            meta_parts.append(f"<b>CWE:</b> {cwe}")
        if owasp:
            meta_parts.append(f"<b>OWASP:</b> {owasp}")
        if meta_parts:
            elements.append(
                Paragraph(" &nbsp;|&nbsp; ".join(meta_parts), self._styles["body_small"])
            )

        # Remediation (once)
        remediation = representative.get("remediation", {})
        rem_desc = remediation.get("description", "")
        if rem_desc:
            elements.append(
                Paragraph(f"<b>Remediation:</b> {rem_desc}", self._styles["body_small"])
            )
        rem_code = remediation.get("code_example", "")
        if rem_code:
            safe_code = (
                rem_code.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br/>")
            )
            elements.append(
                Paragraph(f"<font face='Courier'>{safe_code}</font>", self._styles["code"])
            )

        # Compact locations table
        loc_header = [
            Paragraph("#", self._styles["table_header"]),
            Paragraph("File", self._styles["table_header"]),
            Paragraph("Line", self._styles["table_header"]),
            Paragraph("Confidence", self._styles["table_header"]),
        ]
        loc_rows = [loc_header]
        for i, f in enumerate(findings, 1):
            loc = f.get("location", {})
            fp = loc.get("file_path", "")
            if len(fp) > 55:
                fp = "..." + fp[-52:]
            loc_rows.append([
                Paragraph(str(i), self._styles["table_cell"]),
                Paragraph(fp, self._styles["table_cell"]),
                Paragraph(str(loc.get("start_line", "")), self._styles["table_cell"]),
                Paragraph(f"{f.get('confidence', 0):.2f}", self._styles["table_cell"]),
            ])

        loc_table = Table(
            loc_rows,
            colWidths=[page_w * 0.06, page_w * 0.64, page_w * 0.10, page_w * 0.14],
            repeatRows=1,
        )
        loc_table.setStyle(self._table_style(len(loc_rows)))
        elements.append(loc_table)
        elements.append(Spacer(1, 10))

        return elements


    # ---------------------------------------------------------------
    # Remediation Roadmap
    # ---------------------------------------------------------------

    def _build_remediation_roadmap(self, data: Dict[str, Any]) -> List:
        story = []
        findings = data.get("findings", [])
        actionable = [f for f in findings if not f.get("suppressed", False)]

        story.append(Paragraph("5. Remediation Roadmap", self._styles["h1"]))
        story.append(Paragraph(
            "Prioritized remediation plan based on severity and occurrence count.",
            self._styles["body"],
        ))

        if not actionable:
            story.append(Paragraph("No actionable findings to remediate.", self._styles["body"]))
            return story

        # Group by rule
        rule_info: Dict[str, Dict[str, Any]] = {}
        for f in actionable:
            rid = f.get("rule_id", "UNKNOWN")
            if rid not in rule_info:
                rule_info[rid] = {
                    "title": f.get("title", ""),
                    "severity": f.get("severity", "medium"),
                    "count": 0,
                }
            rule_info[rid]["count"] += 1

        # Estimate effort
        def estimate_effort(severity: str, count: int) -> Tuple[int, str]:
            if severity == "critical" and count >= 5:
                return (1, "High (Architecture Change)")
            if severity == "critical":
                return (2, "Medium (Code Refactor)")
            if severity == "high" and count >= 10:
                return (3, "Medium (Systematic Fix)")
            if severity == "high":
                return (4, "Low (Targeted Fix)")
            return (5, "Low (Targeted Fix)")

        roadmap_rows_data = []
        for rid, info in rule_info.items():
            priority, effort = estimate_effort(info["severity"], info["count"])
            roadmap_rows_data.append((priority, rid, info["title"], info["severity"], info["count"], effort))

        roadmap_rows_data.sort(key=lambda x: x[0])

        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        header = [
            Paragraph("Priority", self._styles["table_header"]),
            Paragraph("Rule ID", self._styles["table_header"]),
            Paragraph("Title", self._styles["table_header"]),
            Paragraph("Severity", self._styles["table_header"]),
            Paragraph("Count", self._styles["table_header"]),
            Paragraph("Est. Effort", self._styles["table_header"]),
        ]
        rows = [header]

        for i, (_, rid, title, sev, count, effort) in enumerate(roadmap_rows_data, 1):
            sev_color = SEVERITY_COLORS.get(sev, Colors.MEDIUM_GRAY)
            sev_hex = f"#{int(sev_color[0]*255):02x}{int(sev_color[1]*255):02x}{int(sev_color[2]*255):02x}"
            short_title = title[:40] + ("..." if len(title) > 40 else "")
            rows.append([
                Paragraph(f"<b>P{i}</b>", self._styles["table_cell"]),
                Paragraph(f"<b>{rid}</b>", self._styles["table_cell"]),
                Paragraph(short_title, self._styles["table_cell"]),
                Paragraph(
                    f'<font color="{sev_hex}"><b>{sev.upper()}</b></font>',
                    self._styles["table_cell"],
                ),
                Paragraph(str(count), self._styles["table_cell"]),
                Paragraph(effort, self._styles["table_cell"]),
            ])

        roadmap_table = Table(
            rows,
            colWidths=[
                page_w * 0.08, page_w * 0.12, page_w * 0.28,
                page_w * 0.12, page_w * 0.08, page_w * 0.27,
            ],
            repeatRows=1,
        )
        roadmap_table.setStyle(self._table_style(len(rows)))
        story.append(roadmap_table)

        return story

    # ---------------------------------------------------------------
    # Methodology
    # ---------------------------------------------------------------

    def _build_methodology(self, data: Dict[str, Any]) -> List:
        story = []
        version = data.get("version", "")

        story.append(Paragraph("6. Methodology", self._styles["h1"]))

        story.append(Paragraph(
            f"This report was generated by <b>agent-audit v{version}</b>, "
            "a static security analyzer for AI agent code, MCP configurations, "
            "and agentic workflows.",
            self._styles["body"],
        ))

        story.append(Paragraph("Analysis Techniques", self._styles["h2"]))

        techniques = [
            "<b>AST-based taint analysis</b> — Tracks data flow from user inputs "
            "through tool functions to dangerous sinks (subprocess, eval, SQL).",
            "<b>Credential detection</b> — Three-stage pipeline: regex matching, "
            "value entropy analysis, and contextual confidence scoring.",
            "<b>MCP configuration audit</b> — Validates Model Context Protocol server "
            "configs for SSRF, credential exposure, and scope issues.",
            "<b>Framework-aware analysis</b> — Reduces false positives by recognizing "
            "Pydantic schemas, LangChain/CrewAI internals, and test fixtures.",
        ]
        for t in techniques:
            story.append(Paragraph(f"&bull; {t}", self._styles["body"]))

        story.append(Paragraph("Confidence Scoring", self._styles["h2"]))
        story.append(Paragraph(
            "Each finding receives a confidence score (0.0 — 1.0) computed from "
            "pattern specificity, context multipliers (test/infra dampening), and "
            "taint flow analysis. Scores map to actionability tiers:",
            self._styles["body"],
        ))

        page_w = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT
        tier_header = [
            Paragraph("Tier", self._styles["table_header"]),
            Paragraph("Threshold", self._styles["table_header"]),
            Paragraph("Meaning", self._styles["table_header"]),
        ]
        tier_rows = [
            tier_header,
            [
                Paragraph("<b>BLOCK</b>", self._styles["table_cell"]),
                Paragraph(">= 0.92", self._styles["table_cell"]),
                Paragraph("High confidence — should fail CI", self._styles["table_cell"]),
            ],
            [
                Paragraph("<b>WARN</b>", self._styles["table_cell"]),
                Paragraph(">= 0.60", self._styles["table_cell"]),
                Paragraph("Medium confidence — review recommended", self._styles["table_cell"]),
            ],
            [
                Paragraph("<b>INFO</b>", self._styles["table_cell"]),
                Paragraph(">= 0.30", self._styles["table_cell"]),
                Paragraph("Low confidence — informational", self._styles["table_cell"]),
            ],
            [
                Paragraph("<b>SUPPRESSED</b>", self._styles["table_cell"]),
                Paragraph("< 0.30", self._styles["table_cell"]),
                Paragraph("Very low — hidden by default", self._styles["table_cell"]),
            ],
        ]
        tier_table = Table(
            tier_rows,
            colWidths=[page_w * 0.2, page_w * 0.2, page_w * 0.6],
        )
        tier_table.setStyle(self._table_style(len(tier_rows)))
        story.append(tier_table)

        story.append(Spacer(1, 12))

        story.append(Paragraph("Standards Alignment", self._styles["h2"]))
        story.append(Paragraph(
            "All rules are mapped to OWASP Agentic Security Initiative (ASI) Top 10 "
            "categories and MITRE CWE identifiers. The scanner provides 10/10 coverage "
            "of the OWASP ASI Top 10.",
            self._styles["body"],
        ))

        story.append(Paragraph("Limitations", self._styles["h2"]))
        story.append(Paragraph(
            "This is a <b>static analysis</b> report. It does not execute agent code "
            "or test runtime behavior. Some findings may be false positives due to "
            "static analysis limitations. Manual review is recommended for all BLOCK-tier "
            "findings before taking remediation action.",
            self._styles["body"],
        ))

        return story

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    @staticmethod
    def _build_compliance_verdict(
        compliance: Dict[str, str],
        block_count: int,
        warn_count: int,
        findings: List[Dict],
        summary: Dict[str, Any],
    ) -> str:
        """Generate 2-3 sentence compliance narrative."""
        by_category = summary.get("by_category", {})
        categories_affected = len([c for c, n in by_category.items() if n > 0])
        top_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:3]
        top_cat_names = ", ".join(c.replace("_", " ").title() for c, _ in top_cats)

        status = compliance["status"]
        if status == "FAIL":
            return (
                f"This codebase <b>does not meet</b> agent security compliance requirements. "
                f"<b>{block_count}</b> critical findings across <b>{categories_affected}</b> "
                f"OWASP categories require remediation before production deployment. "
                f"Priority areas: <b>{top_cat_names}</b>."
            )
        if status == "CONDITIONAL PASS":
            return (
                f"This codebase meets baseline requirements <b>with conditions</b>. "
                f"<b>{warn_count}</b> findings across <b>{categories_affected}</b> "
                f"OWASP categories require review before production deployment. "
                f"Key areas: <b>{top_cat_names}</b>."
            )
        return (
            "This codebase <b>meets</b> agent security compliance requirements. "
            "No BLOCK-tier findings were detected and WARN-tier findings are within "
            "acceptable thresholds. Continued monitoring is recommended."
        )

    @staticmethod
    def _compute_top_risk_rules(
        findings: List[Dict], top_n: int = 3
    ) -> List[Tuple[str, str, int, str]]:
        """Return top N rules by (severity_weight * count), descending."""
        severity_weights = {
            "critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0.5
        }
        rule_data: Dict[str, Dict[str, Any]] = {}
        for f in findings:
            if f.get("suppressed", False):
                continue
            rid = f.get("rule_id", "")
            if not rid:
                continue
            if rid not in rule_data:
                rule_data[rid] = {
                    "severity": f.get("severity", "medium"),
                    "count": 0,
                    "description": f.get("description", ""),
                }
            rule_data[rid]["count"] += 1

        scored = []
        for rid, info in rule_data.items():
            weight = severity_weights.get(info["severity"], 1)
            score = weight * info["count"]
            desc_short = info["description"][:80]
            if len(info["description"]) > 80:
                desc_short += "..."
            scored.append((score, rid, info["severity"], info["count"], desc_short))

        scored.sort(reverse=True)
        return [(rid, sev, cnt, desc) for _, rid, sev, cnt, desc in scored[:top_n]]

    @staticmethod
    def _compute_compliance(block_count: int, warn_count: int) -> Dict[str, str]:
        """Compute compliance status from tier counts."""
        if block_count > 0:
            return {
                "status": "FAIL",
                "message": f"{block_count} BLOCK-tier findings require remediation before deployment",
            }
        if warn_count > 3:
            return {
                "status": "CONDITIONAL PASS",
                "message": f"{warn_count} WARN-tier findings should be reviewed before production",
            }
        return {
            "status": "PASS",
            "message": "No critical findings — codebase meets agent security requirements",
        }

    def _table_style(self, num_rows: int) -> TableStyle:
        """Create standard table style with alternating row colors."""
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), _rl_color(Colors.PRIMARY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), _rl_color(Colors.WHITE)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, _rl_color(Colors.MEDIUM_GRAY)),
            ("LINEBELOW", (0, 0), (-1, 0), 1, _rl_color(Colors.ACCENT)),
        ]
        # Alternating row colors
        for i in range(1, num_rows):
            if i % 2 == 0:
                style_commands.append(
                    ("BACKGROUND", (0, i), (-1, i), _rl_color(Colors.LIGHT_GRAY))
                )
        return TableStyle(style_commands)

    def _page_footer(self, canvas, doc) -> None:
        """Draw footer on each page."""
        canvas.saveState()
        page_w, page_h = A4

        # Footer line
        canvas.setStrokeColor(_rl_color(Colors.MEDIUM_GRAY))
        canvas.setLineWidth(0.5)
        canvas.line(
            PAGE_MARGIN_LEFT, PAGE_MARGIN_BOTTOM - 15,
            page_w - PAGE_MARGIN_RIGHT, PAGE_MARGIN_BOTTOM - 15,
        )

        # Footer text
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_rl_color(Colors.DARK_GRAY))
        canvas.drawString(
            PAGE_MARGIN_LEFT, PAGE_MARGIN_BOTTOM - 28,
            f"agent-audit — AI Agent Security Audit Report",
        )
        canvas.drawRightString(
            page_w - PAGE_MARGIN_RIGHT, PAGE_MARGIN_BOTTOM - 28,
            f"Page {doc.page}",
        )
        canvas.drawCentredString(
            page_w / 2, PAGE_MARGIN_BOTTOM - 28,
            "CONFIDENTIAL",
        )

        canvas.restoreState()
