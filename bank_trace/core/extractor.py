"""Extraction helpers for statement metadata, dates, amounts, and matches."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bank_trace.core.models import MatchResult

AMOUNT_PATTERN = re.compile(
    r"(?<!\d)([+-]?\d{1,3}(?:\.\d{3})*,\d{2}|[+-]?\d+,\d{2})(?!\d)"
)

DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b"),
    re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{2})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
)

STATEMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Kontoauszug\s*Nr\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"Auszug\s*Nr\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"Statement\s*No\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
)


def normalize_contract_token(value: str) -> str:
    """Normalize a contract token for resilient text matching.

    Formatting characters and separator variants are removed so contracts can
    still be matched against imperfect PDF or OCR text.

    :param value: Raw contract number text.
    :returns: Uppercase alphanumeric search token.
    """

    uppercase = value.upper().strip()
    uppercase = (
        uppercase
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("_", "-")
    )
    return re.sub(r"[^A-Z0-9]", "", uppercase)


def normalize_text_for_search(value: str) -> str:
    """Normalize page text into a contract-searchable token stream.

    :param value: Raw text extracted from a PDF line.
    :returns: Uppercase alphanumeric text without formatting characters.
    """

    uppercase = value.upper()
    uppercase = (
        uppercase
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("_", "-")
    )
    return re.sub(r"[^A-Z0-9]", "", uppercase)


def extract_statement_label(text: str, fallback: str) -> str:
    """Extract a statement identifier from page text.

    :param text: Text content of the statement page.
    :param fallback: Value returned when no known label pattern matches.
    :returns: Extracted statement label or the fallback value.
    """

    for pattern in STATEMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return fallback


def find_amounts_in_text(text: str) -> list[str]:
    """Return all amount-like values found in a text fragment.

    :param text: Text that may contain localized currency values.
    :returns: Matched amounts in discovery order.
    """

    return AMOUNT_PATTERN.findall(text)


def parse_date_string(value: str) -> datetime | None:
    """Parse a supported date string into a :class:`datetime` object.

    :param value: Candidate date string.
    :returns: Parsed date or ``None`` when no supported format matches.
    """

    formats = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d")

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def find_best_date_in_context(lines: list[str], hit_index: int) -> tuple[str, str]:
    """Find the nearest valid booking date around a matched contract line.

    :param lines: All text lines from the current PDF page.
    :param hit_index: Index of the line containing the contract match.
    :returns: Tuple of formatted booking date and booking month.
    """

    candidate_indices = [
        hit_index,
        hit_index + 1,
        hit_index + 2,
        hit_index - 1,
        hit_index - 2,
    ]

    for index in candidate_indices:
        if index < 0 or index >= len(lines):
            continue

        line = lines[index]

        for pattern in DATE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue

            raw_date = match.group(1)
            parsed_date = parse_date_string(raw_date)
            if parsed_date is None:
                continue

            return (
                parsed_date.strftime("%d.%m.%Y"),
                parsed_date.strftime("%Y-%m"),
            )

    return ("", "")


def find_best_amount_in_context(lines: list[str], hit_index: int) -> str | None:
    """Find the nearest amount around a matched contract line.

    :param lines: All text lines from the current PDF page.
    :param hit_index: Index of the line containing the contract match.
    :returns: Best matching amount or ``None`` when no amount is found nearby.
    """

    candidate_indices = [
        hit_index,
        hit_index + 1,
        hit_index + 2,
        hit_index - 1,
        hit_index - 2,
    ]

    for index in candidate_indices:
        if index < 0 or index >= len(lines):
            continue

        amounts = find_amounts_in_text(lines[index])
        if amounts:
            return amounts[-1]

    return None


def build_context_line(lines: list[str], hit_index: int) -> str:
    """Build a compact multi-line context string around a page hit.

    :param lines: All text lines from the current PDF page.
    :param hit_index: Index of the matching line.
    :returns: Joined context string for reporting output.
    """

    start = max(0, hit_index - 1)
    end = min(len(lines), hit_index + 2)
    context = " | ".join(line.strip() for line in lines[start:end] if line.strip())
    return context.strip()


def find_matches_in_page(
    page_text: str,
    contract_numbers: Iterable[str],
    statement_file: str,
    statement_label: str,
    page_number: int,
) -> list[MatchResult]:
    """Collect deduplicated contract matches for a single PDF page.

    The surrounding context is used to infer the booking amount and booking
    date near the matched contract token.

    :param page_text: Full text extracted from one PDF page.
    :param contract_numbers: Contract numbers to search for.
    :param statement_file: Name of the source PDF file.
    :param statement_label: Human-readable statement identifier.
    :param page_number: One-based page number in the PDF.
    :returns: All unique matches found on the page.
    """

    results: list[MatchResult] = []
    lines = page_text.splitlines()

    normalized_contracts = {
        contract_number: normalize_contract_token(contract_number)
        for contract_number in contract_numbers
        if contract_number.strip()
    }

    seen_keys: set[tuple[str, int, str]] = set()

    for line_index, line in enumerate(lines):
        normalized_line = normalize_text_for_search(line)

        for contract_number, normalized_contract in normalized_contracts.items():
            if not normalized_contract:
                continue

            if normalized_contract not in normalized_line:
                continue

            amount = find_best_amount_in_context(lines, line_index)
            if amount is None:
                continue

            booking_date, booking_month = find_best_date_in_context(lines, line_index)
            context_line = build_context_line(lines, line_index)
            unique_key = (contract_number, page_number, context_line)

            if unique_key in seen_keys:
                continue

            seen_keys.add(unique_key)

            results.append(
                MatchResult(
                    contract_number=contract_number,
                    amount=amount,
                    statement_file=statement_file,
                    statement_label=statement_label,
                    page_number=page_number,
                    booking_date=booking_date,
                    booking_month=booking_month,
                    line_text=context_line,
                )
            )

    return results
