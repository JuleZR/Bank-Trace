"""Directory-level scanning workflow for bank statement PDFs."""

from __future__ import annotations

from pathlib import Path

from bank_trace.config.settings import PDF_EXTENSION
from bank_trace.core.extractor import (
    extract_statement_label,
    find_matches_in_page,
)
from bank_trace.core.models import MatchResult
from bank_trace.services.pdf_service import extract_text_per_page


class StatementScanner:
    """Scan statement directories and aggregate contract matches."""

    def scan_directory(
        self,
        folder_path: Path,
        contract_numbers: list[str],
    ) -> list[MatchResult]:
        """Scan all PDF statements in a folder for contract matches.

        :param folder_path: Directory containing statement PDFs.
        :param contract_numbers: Contract numbers that should be matched.
        :returns: Combined matches from all scanned PDF pages.
        :raises FileNotFoundError: If ``folder_path`` does not exist or is not a directory.
        """

        results: list[MatchResult] = []

        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        pdf_files = sorted(
            path for path in folder_path.iterdir()
            if path.suffix.lower() == PDF_EXTENSION
        )

        for pdf_file in pdf_files:
            page_texts = extract_text_per_page(pdf_file)
            if not page_texts:
                continue

            first_page_text = page_texts[0]
            statement_label = extract_statement_label(
                first_page_text, pdf_file.name
            )

            for page_index, page_text in enumerate(page_texts, start=1):
                page_results = find_matches_in_page(
                    page_text=page_text,
                    contract_numbers=contract_numbers,
                    statement_file=pdf_file.name,
                    statement_label=statement_label,
                    page_number=page_index,
                )
                results.extend(page_results)

        return results
