"""PDF report generation for Bank Trace scan results."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bank_trace.core.models import MatchResult


class ReportService:
    """Create structured PDF reports from extracted statement matches."""

    def create_report(
        self,
        output_path: Path,
        results: list[MatchResult],
    ) -> None:
        """Create a PDF report grouped by contract number.

        Each contract number gets exactly one continuous table. Entries are
        sorted chronologically by booking month and booking date.

        :param output_path: Destination path of the generated PDF report.
        :param results: Extracted matches to include in the report.
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
        heading_1_style = styles["Heading1"]
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

        grouped_results = self._group_results(results)

        first_contract = True

        for contract_number in sorted(grouped_results):
            if not first_contract:
                content.append(PageBreak())
            first_contract = False

            content.append(
                Paragraph(
                    f"Contract Number: {self._escape(contract_number)}",
                    heading_1_style,
                )
            )
            content.append(Spacer(1, 4 * mm))

            entries = sorted(
                grouped_results[contract_number],
                key=self._sort_key_for_result,
            )

            table = self._build_contract_table(entries, small_style)
            content.append(table)
            content.append(Spacer(1, 6 * mm))

        document.build(content)

    def _group_results(
        self,
        results: list[MatchResult],
    ) -> dict[str, list[MatchResult]]:
        """Group results by contract number."""

        grouped: dict[str, list[MatchResult]] = defaultdict(list)

        for result in results:
            grouped[result.contract_number].append(result)

        return dict(grouped)

    def _build_contract_table(
        self,
        entries: list[MatchResult],
        small_style: ParagraphStyle,
    ) -> Table:
        """Create one continuous table for a contract number."""

        table_data = [
            [
                "Month",
                "Date",
                "Amount",
                "Statement",
                "File",
                "Page",
                "Source Line",
            ]
        ]

        for entry in entries:
            table_data.append(
                [
                    Paragraph(self._escape(entry.booking_month), small_style),
                    Paragraph(self._escape(entry.booking_date), small_style),
                    Paragraph(self._escape(entry.amount), small_style),
                    Paragraph(self._escape(entry.statement_label), small_style),
                    Paragraph(self._escape(entry.statement_file), small_style),
                    Paragraph(str(entry.page_number), small_style),
                    Paragraph(self._escape(entry.line_text), small_style),
                ]
            )

        table = Table(
            table_data,
            colWidths=[
                20 * mm,
                22 * mm,
                20 * mm,
                24 * mm,
                42 * mm,
                10 * mm,
                150 * mm,
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

        return table

    def _sort_key_for_result(self, result: MatchResult) -> tuple[str, str, str, str]:
        """Create a stable chronological sort key."""

        iso_date = self._to_iso_date(result.booking_date)

        return (
            result.booking_month or "9999-99",
            iso_date,
            result.statement_label or "",
            result.statement_file or "",
        )

    @staticmethod
    def _to_iso_date(value: str) -> str:
        """Convert dd.mm.yyyy to yyyy-mm-dd for proper sorting."""

        if not value:
            return "9999-99-99"

        try:
            parsed = datetime.strptime(value, "%d.%m.%Y")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            return "9999-99-99"

    @staticmethod
    def _escape(text: str) -> str:
        """Escape XML-sensitive characters for ReportLab paragraphs."""

        return (
            (text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
