"""Data models shared across Bank Trace scanning workflows."""

from dataclasses import dataclass


@dataclass(slots=True)
class MatchResult:
    """Represent a single contract match found within a statement line.

    :param contract_number: Contract number that was matched.
    :param amount: Amount extracted from the matching line.
    :param statement_file: Source PDF file name.
    :param statement_label: Human-readable statement identifier.
    :param page_number: One-based page number inside the PDF.
    :param line_text: Original line text that produced the match.
    """

    contract_number: str
    amount: str
    statement_file: str
    statement_label: str
    page_number: int
    line_text: str
