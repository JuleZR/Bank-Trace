"""PDF report generation utilities for scan results."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bank_trace.core.models import MatchResult


class ReportService:
    """Create PDF reports summarizing detected statement matches."""

    def create_report(
        self,
        output_path: Path,
        results: list[MatchResult],
    ) -> None:
        """Generate a report PDF for the provided match results.

        :param output_path: Destination path of the generated report.
        :param results: Matches that should appear in the report.
        """

        output_path.parent.mkdir(parents=True, exist_ok=True)

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        normal_style = styles["BodyText"]
        small_style = ParagraphStyle(
            "SmallText",
            parent=styles["BodyText"],
            fontSize=7,
            leading=9,
        )

        content = [
            Paragraph("Bank Trace Report", title_style),
            Spacer(1, 6 * mm),
        ]

        if not results:
            content.append(Paragraph("No matching entries found.", normal_style))
            document.build(content)
            return

        table_data = [
            [
                "Contract Number",
                "Amount",
                "Date",
                "Month",
                "Statement",
                "File",
                "Page",
                "Source Line",
            ]
        ]

        for result in results:
            table_data.append(
                [
                    Paragraph(self._escape(result.contract_number), small_style),
                    Paragraph(self._escape(result.amount), small_style),
                    Paragraph(self._escape(result.booking_date), small_style),
                    Paragraph(self._escape(result.booking_month), small_style),
                    Paragraph(self._escape(result.statement_label), small_style),
                    Paragraph(self._escape(result.statement_file), small_style),
                    Paragraph(str(result.page_number), small_style),
                    Paragraph(self._escape(result.line_text), small_style),
                ]
            )

        table = Table(
            table_data,
            colWidths=[
                30 * mm,
                20 * mm,
                22 * mm,
                22 * mm,
                24 * mm,
                35 * mm,
                10 * mm,
                90 * mm,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        content.append(table)
        document.build(content)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape XML-sensitive characters for ReportLab paragraphs.

        :param text: Raw text content.
        :returns: Escaped text safe for paragraph rendering.
        """

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
