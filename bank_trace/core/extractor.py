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
    """Normalize a contract token for resilient text matching."""

    uppercase = value.upper().strip()
    uppercase = (
        uppercase.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("_", "-")
    )
    return re.sub(r"[^A-Z0-9]", "", uppercase)


def normalize_text_for_search(value: str) -> str:
    """Normalize extracted PDF text for tolerant matching."""

    uppercase = value.upper()
    uppercase = (
        uppercase.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("_", "-")
    )
    return re.sub(r"[^A-Z0-9]", "", uppercase)


def extract_statement_label(text: str, fallback: str) -> str:
    """Extract a statement label from page text."""

    for pattern in STATEMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return fallback


def find_amounts_in_text(text: str) -> list[str]:
    """Return all amount-like values found in text."""

    return AMOUNT_PATTERN.findall(text)


def parse_date_string(value: str) -> datetime | None:
    """Parse a supported date string."""

    formats = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d")

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def find_best_date_in_text(text: str) -> tuple[str, str]:
    """Find the first valid date in a text fragment."""

    for pattern in DATE_PATTERNS:
        matches = pattern.findall(text)
        for raw_date in matches:
            parsed_date = parse_date_string(raw_date)
            if parsed_date is None:
                continue

            return (
                parsed_date.strftime("%d.%m.%Y"),
                parsed_date.strftime("%Y-%m"),
            )

    return "", ""


def find_best_amount_in_text(text: str) -> str | None:
    """Find the most likely amount in a text fragment."""

    amounts = find_amounts_in_text(text)
    if not amounts:
        return None
    return amounts[-1]


def build_context_text(lines: list[str], start_index: int, end_index: int) -> str:
    """Build a compact context string from a line window."""

    return " | ".join(
        line.strip() for line in lines[start_index:end_index] if line.strip()
    ).strip()


def find_contract_windows(
    lines: list[str],
    normalized_contract: str,
    min_window_size: int = 1,
    max_window_size: int = 8,
) -> list[tuple[int, int]]:
    """Find windows of consecutive lines containing a contract token."""

    windows: list[tuple[int, int]] = []
    line_count = len(lines)

    for window_size in range(min_window_size, max_window_size + 1):
        for start_index in range(line_count):
            end_index = start_index + window_size
            if end_index > line_count:
                break

            window_text = " ".join(lines[start_index:end_index])
            normalized_window = normalize_text_for_search(window_text)

            if normalized_contract in normalized_window:
                windows.append((start_index, end_index))

    return windows


def choose_best_window(
    lines: list[str],
    windows: list[tuple[int, int]],
) -> tuple[int, int] | None:
    """Choose the most useful match window."""

    if not windows:
        return None

    ranked_windows: list[tuple[int, int, int, int]] = []

    for start_index, end_index in windows:
        window_text = " ".join(lines[start_index:end_index])
        has_amount = 1 if find_best_amount_in_text(window_text) is not None else 0
        has_date = 1 if find_best_date_in_text(window_text)[0] else 0
        window_length = end_index - start_index
        ranked_windows.append((has_amount, has_date, -window_length, start_index))

    ranked_windows.sort(reverse=True)

    _, _, _, best_start = ranked_windows[0]

    for start_index, end_index in windows:
        if start_index == best_start:
            return start_index, end_index

    return windows[0]


def find_best_date_in_lines(
    lines: list[str],
    start_index: int,
    end_index: int,
    max_padding: int = 6,
) -> tuple[str, str]:
    """Find the nearest valid date around a match window.

    The search starts inside the match window and then expands outward.
    """

    for padding in range(0, max_padding + 1):
        expanded_start = max(0, start_index - padding)
        expanded_end = min(len(lines), end_index + padding)
        text = " ".join(lines[expanded_start:expanded_end])

        booking_date, booking_month = find_best_date_in_text(text)
        if booking_date:
            return booking_date, booking_month

    return "", ""


def find_best_amount_in_lines(
    lines: list[str],
    start_index: int,
    end_index: int,
    max_padding: int = 4,
) -> tuple[str | None, tuple[int, int]]:
    """Find the nearest valid amount around a match window."""

    for padding in range(0, max_padding + 1):
        expanded_start = max(0, start_index - padding)
        expanded_end = min(len(lines), end_index + padding)
        text = " ".join(lines[expanded_start:expanded_end])

        amount = find_best_amount_in_text(text)
        if amount is not None:
            return amount, (expanded_start, expanded_end)

    return None, (start_index, end_index)


def find_matches_in_page(
    page_text: str,
    contract_numbers: Iterable[str],
    statement_file: str,
    statement_label: str,
    page_number: int,
) -> list[MatchResult]:
    """Collect deduplicated contract matches for a single page."""

    results: list[MatchResult] = []
    lines = page_text.splitlines()
    normalized_page = normalize_text_for_search(page_text)

    normalized_contracts = {
        contract_number: normalize_contract_token(contract_number)
        for contract_number in contract_numbers
        if contract_number.strip()
    }

    seen_keys: set[tuple[str, int, str]] = set()

    for contract_number, normalized_contract in normalized_contracts.items():
        if not normalized_contract:
            continue

        if normalized_contract not in normalized_page:
            continue

        windows = find_contract_windows(lines, normalized_contract)
        best_window = choose_best_window(lines, windows)

        if best_window is None:
            continue

        start_index, end_index = best_window

        amount, context_window = find_best_amount_in_lines(lines, start_index, end_index)
        if amount is None:
            continue

        context_start, context_end = context_window
        booking_date, booking_month = find_best_date_in_lines(
            lines,
            context_start,
            context_end,
        )
        context_text = build_context_text(lines, context_start, context_end)

        unique_key = (contract_number, page_number, context_text)
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
                line_text=context_text,
            )
        )

    return results
