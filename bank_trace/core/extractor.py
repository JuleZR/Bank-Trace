from __future__ import annotations

import re
from typing import Iterable

from bank_trace.core.models import MatchResult

AMOUNT_PATTERN = re.compile(
    r"(?<!\d)([+-]?\d{1,3}(?:\.\d{3})*,\d{2}|[+-]?\d+,\d{2})(?!\d)"
)

STATEMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Kontoauszug\s*Nr\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"Auszug\s*Nr\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"Statement\s*No\.?\s*([A-Za-z0-9\-/]+)", re.IGNORECASE),
)


def normalize_contract_token(value: str) -> str:
    """
    Normalize contract numbers aggressively:
    keep only letters and digits, remove spaces, hyphens and similar separators.
    """
    uppercase = value.upper().strip()

    # Vereinheitliche verschiedene Bindestriche / Gedankenstriche
    uppercase = (
        uppercase
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("_", "-")
    )

    # Für die Suche: alles außer A-Z und 0-9 raus
    return re.sub(r"[^A-Z0-9]", "", uppercase)


def normalize_text_for_search(value: str) -> str:
    """
    Normalize extracted PDF text for tolerant contract matching.
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
    for pattern in STATEMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return fallback


def find_amounts_in_text(text: str) -> list[str]:
    return AMOUNT_PATTERN.findall(text)


def find_best_amount_in_context(lines: list[str], hit_index: int) -> str | None:
    """
    Search for an amount in the hit line and nearby lines.
    Preference:
    1. same line
    2. next lines
    3. previous lines
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
                    line_text=context_line,
                )
            )

    return results
