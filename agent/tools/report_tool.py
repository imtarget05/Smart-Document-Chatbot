"""
PDF Report Builder – Phase 4.
Uses ReportLab to generate professional PDF reports from markdown-like text.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class PdfReportBuilder:
    """Converts a text/markdown string into a styled PDF file."""

    def build(self, title: str, content: str, output_path: str) -> None:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
            )

            doc    = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
                leftMargin=2.5 * cm,
                rightMargin=2.5 * cm,
            )
            styles = getSampleStyleSheet()
            story: List = []

            # Title
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=18,
                spaceAfter=12,
                textColor=colors.HexColor("#1a1a2e"),
            )
            story.append(Paragraph(title, title_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#4a90d9")))
            story.append(Spacer(1, 0.4 * cm))

            # Parse content lines
            h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceAfter=6, spaceBefore=12)
            h3_style = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11, spaceAfter=4, spaceBefore=8)
            body_style = styles["BodyText"]
            body_style.leading = 16

            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    story.append(Spacer(1, 0.2 * cm))
                elif stripped.startswith("## "):
                    story.append(Paragraph(stripped[3:], h2_style))
                elif stripped.startswith("# "):
                    story.append(Paragraph(stripped[2:], h2_style))
                elif stripped.startswith("**") and stripped.endswith("**"):
                    story.append(Paragraph(f"<b>{stripped[2:-2]}</b>", body_style))
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    story.append(Paragraph(f"&bull;&nbsp;{stripped[2:]}", body_style))
                else:
                    # Inline bold (**text**)
                    html_line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
                    story.append(Paragraph(html_line, body_style))

            doc.build(story)
            logger.info("PDF built: %s", output_path)
        except ImportError:
            # Fallback: plain text file if ReportLab not available
            txt_path = output_path.replace(".pdf", ".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"{title}\n{'='*len(title)}\n\n{content}")
            logger.warning("ReportLab not available – wrote plain text to %s", txt_path)
