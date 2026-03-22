"""Data models shared across Bank Trace scanning workflows."""

from dataclasses import dataclass


@dataclass(slots=True)
class MatchResult:
    """Represent a single contract match found in a bank statement.

    :param contract_number: Contract number that was matched.
    :param amount: Amount associated with the match.
    :param statement_file: Source PDF file name.
    :param statement_label: Human-readable statement identifier.
    :param page_number: One-based page number inside the PDF.
    :param booking_date: Extracted booking date near the match.
    :param booking_month: Year-month bucket derived from ``booking_date``.
    :param line_text: Context text shown in the report.
    """

    contract_number: str
    amount: str
    statement_file: str
    statement_label: str
    page_number: int
    booking_date: str
    booking_month: str
    line_text: str
