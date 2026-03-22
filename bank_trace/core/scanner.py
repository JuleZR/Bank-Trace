"""Directory-level scanning workflow for bank statement PDFs."""

from __future__ import annotations

from pathlib import Path

from bank_trace.config.settings import PDF_EXTENSION
from bank_trace.core.extractor import extract_statement_label, find_matches_in_page
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

        The scanner walks the selected directory recursively, reads every PDF,
        and aggregates all matches found across all pages.

        :param folder_path: Directory containing statement PDFs.
        :param contract_numbers: Contract numbers that should be matched.
        :returns: Combined matches from all scanned PDF pages.
        :raises FileNotFoundError: If ``folder_path`` does not exist or is not a directory.
        """

        results: list[MatchResult] = []

        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        pdf_files = sorted(
            file_path
            for file_path in folder_path.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() == PDF_EXTENSION
        )

        print(f"[Bank Trace] Found {len(pdf_files)} PDF file(s) in {folder_path}")
        for pdf_file in pdf_files:
            print(f"[Bank Trace] -> {pdf_file}")

        for pdf_file in pdf_files:
            try:
                print(f"[Bank Trace] Reading: {pdf_file.name}")
                page_texts = extract_text_per_page(pdf_file)

                if not page_texts:
                    print(
                        f"[Bank Trace] Skipped {pdf_file.name}: "
                        "no readable text extracted"
                    )
                    continue

                first_page_text = page_texts[0]
                statement_label = extract_statement_label(first_page_text, pdf_file.name)

                file_match_count = 0

                for page_index, page_text in enumerate(page_texts, start=1):
                    page_results = find_matches_in_page(
                        page_text=page_text,
                        contract_numbers=contract_numbers,
                        statement_file=pdf_file.name,
                        statement_label=statement_label,
                        page_number=page_index,
                    )
                    results.extend(page_results)
                    file_match_count += len(page_results)

                print(
                    f"[Bank Trace] Finished {pdf_file.name}: "
                    f"{len(page_texts)} page(s), {file_match_count} match(es)"
                )

            except (OSError, ValueError, RuntimeError) as exc:
                print(f"[Bank Trace] Error reading {pdf_file}: {exc}")
                continue

        print(f"[Bank Trace] Total matches: {len(results)}")
        return results
