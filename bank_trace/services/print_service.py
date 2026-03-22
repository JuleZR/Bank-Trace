"""Platform-aware helpers for sending generated reports to a printer."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


class PrintService:
    """Send PDF reports to the operating system print command."""

    def print_pdf(self, pdf_path: Path) -> None:
        """Send a PDF file to the default printer.

        :param pdf_path: Path to the report that should be printed.
        :raises FileNotFoundError: If the report file does not exist.
        :raises OSError: If the platform print command cannot be executed.
        :raises subprocess.CalledProcessError: If the print command fails.
        """

        if not pdf_path.exists():
            raise FileNotFoundError(f"Report file not found: {pdf_path}")

        system_name = platform.system()

        if system_name == "Windows":
            os.startfile(str(pdf_path), "print")  # type: ignore[attr-defined]
            return

        if system_name == "Darwin":
            subprocess.run(["lp", str(pdf_path)], check=True)
            return

        subprocess.run(["lp", str(pdf_path)], check=True)
