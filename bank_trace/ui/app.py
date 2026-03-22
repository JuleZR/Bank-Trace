"""GUI application for Bank Trace."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import ImageTk

from bank_trace.config.settings import (
    APP_HEIGHT,
    APP_NAME,
    APP_WIDTH,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    DEFAULT_REPORT_FILE,
    PREVIEW_ZOOM,
)
from bank_trace.core.models import MatchResult
from bank_trace.core.scanner import StatementScanner
from bank_trace.services.pdf_service import render_pdf_page_to_image
from bank_trace.services.print_service import PrintService
from bank_trace.services.report_service import ReportService
from bank_trace.services.storage_service import StorageService


class BankTraceApp(ctk.CTk):
    """Main desktop application for scanning bank statement PDFs."""

    def __init__(self) -> None:
        """Initialize the main window, services, and widget references."""

        super().__init__()

        ctk.set_appearance_mode(DEFAULT_APPEARANCE_MODE)
        ctk.set_default_color_theme(DEFAULT_COLOR_THEME)

        self.title(APP_NAME)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(1100, 700)

        self.storage_service = StorageService()
        self.scanner = StatementScanner()
        self.report_service = ReportService()
        self.print_service = PrintService()

        self.results: list[MatchResult] = []
        self.preview_image: ImageTk.PhotoImage | None = None
        self.report_path = Path(DEFAULT_REPORT_FILE)

        self.left_frame: ctk.CTkFrame | None = None
        self.right_frame: ctk.CTkFrame | None = None
        self.folder_entry: ctk.CTkEntry | None = None
        self.contracts_textbox: ctk.CTkTextbox | None = None
        self.output_entry: ctk.CTkEntry | None = None
        self.preview_label: ctk.CTkLabel | None = None
        self.status_label: ctk.CTkLabel | None = None

        self._build_layout()
        self._load_saved_config()

    def _build_layout(self) -> None:
        """Create the two-column application layout."""

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkFrame(self, corner_radius=12)
        self.left_frame.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self) -> None:
        """Build the control panel for input, actions, and printing."""

        if self.left_frame is None:
            raise RuntimeError("Left frame has not been initialized.")

        title_label = ctk.CTkLabel(
            self.left_frame,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=16, pady=(16, 10), sticky="w")

        folder_label = ctk.CTkLabel(self.left_frame, text="PDF folder")
        folder_label.grid(row=1, column=0, padx=16, pady=(10, 4), sticky="w")

        folder_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        folder_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        folder_frame.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(folder_frame)
        self.folder_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        folder_button = ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=110,
            command=self._select_folder,
        )
        folder_button.grid(row=0, column=1, sticky="e")

        contracts_label = ctk.CTkLabel(self.left_frame, text="Contract numbers")
        contracts_label.grid(row=3, column=0, padx=16, pady=(10, 4), sticky="w")

        self.contracts_textbox = ctk.CTkTextbox(self.left_frame, height=220)
        self.contracts_textbox.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.contracts_textbox.insert("1.0", "Enter one contract number per line...")

        output_label = ctk.CTkLabel(self.left_frame, text="Output PDF")
        output_label.grid(row=5, column=0, padx=16, pady=(10, 4), sticky="w")

        output_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        output_frame.grid(row=6, column=0, padx=16, pady=(0, 10), sticky="ew")
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(output_frame)
        self.output_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.output_entry.insert(0, str(self.report_path))

        output_button = ctk.CTkButton(
            output_frame,
            text="Save as",
            width=110,
            command=self._select_output_file,
        )
        output_button.grid(row=0, column=1, sticky="e")

        button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        button_frame.grid(row=7, column=0, padx=16, pady=(10, 16), sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        save_button = ctk.CTkButton(
            button_frame,
            text="Save settings",
            command=self._save_config,
        )
        save_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        scan_button = ctk.CTkButton(
            button_frame,
            text="Scan PDFs",
            command=self._run_scan,
        )
        scan_button.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        print_button = ctk.CTkButton(
            self.left_frame,
            text="Print report",
            command=self._print_report,
        )
        print_button.grid(row=8, column=0, padx=16, pady=(0, 16), sticky="ew")

    def _build_right_panel(self) -> None:
        """Build the preview and status area of the application."""

        if self.right_frame is None:
            raise RuntimeError("Right frame has not been initialized.")

        header = ctk.CTkLabel(
            self.right_frame,
            text="Preview",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.preview_label = ctk.CTkLabel(
            self.right_frame,
            text="No preview available.",
            anchor="center",
        )
        self.preview_label.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")

        self.status_label = ctk.CTkLabel(
            self.right_frame,
            text="Ready.",
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")

    def _load_saved_config(self) -> None:
        """Populate the UI with previously persisted settings.

        :raises RuntimeError: If required widgets are not initialized yet.
        """

        if (
            self.folder_entry is None
            or self.contracts_textbox is None
            or self.output_entry is None
        ):
            raise RuntimeError("UI widgets have not been initialized.")

        config = self.storage_service.load_config()

        folder = str(config.get("folder", ""))
        contract_numbers = config.get("contract_numbers", [])
        output_file = str(config.get("output_file", "")) or str(self.report_path)

        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, folder)

        self.contracts_textbox.delete("1.0", "end")
        self.contracts_textbox.insert("1.0", "\n".join(contract_numbers))

        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, output_file)

    def _save_config(self) -> None:
        """Persist the current form state and notify the user."""

        if self.status_label is None:
            raise RuntimeError("Status label has not been initialized.")

        folder = self._require_widget(self.folder_entry).get().strip()
        contract_numbers = self._get_contract_numbers()
        output_file = self._require_widget(self.output_entry).get().strip()

        self.storage_service.save_config(
            folder=folder,
            contract_numbers=contract_numbers,
            output_file=output_file,
        )

        self.status_label.configure(text="Settings saved.")
        messagebox.showinfo(APP_NAME, "Settings have been saved locally.")

    def _select_folder(self) -> None:
        """Open a folder picker and update the folder input field."""

        folder_entry = self._require_widget(self.folder_entry)

        selected_folder = filedialog.askdirectory(title="Select PDF folder")
        if not selected_folder:
            return

        folder_entry.delete(0, "end")
        folder_entry.insert(0, selected_folder)

    def _select_output_file(self) -> None:
        """Open a save dialog and update the output file input field."""

        output_entry = self._require_widget(self.output_entry)

        selected_file = filedialog.asksaveasfilename(
            title="Select output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not selected_file:
            return

        output_entry.delete(0, "end")
        output_entry.insert(0, selected_file)

    def _get_contract_numbers(self) -> list[str]:
        """Return cleaned contract numbers from the multiline textbox.

        :returns: Non-empty, stripped contract numbers in input order.
        """

        contracts_textbox = self._require_widget(self.contracts_textbox)
        raw_text = contracts_textbox.get("1.0", "end").strip()
        lines = [line.strip() for line in raw_text.splitlines()]
        return [line for line in lines if line]

    def _run_scan(self) -> None:
        """Scan the selected PDFs, generate a report, and refresh the preview."""

        status_label = self._require_widget(self.status_label)
        folder_text = self._require_widget(self.folder_entry).get().strip()
        output_text = self._require_widget(self.output_entry).get().strip()
        contract_numbers = self._get_contract_numbers()

        if not folder_text:
            messagebox.showwarning(APP_NAME, "Please select a PDF folder.")
            return

        if not contract_numbers:
            messagebox.showwarning(APP_NAME, "Please enter at least one contract number.")
            return

        folder_path = Path(folder_text)
        output_path = Path(output_text) if output_text else Path(DEFAULT_REPORT_FILE)

        try:
            status_label.configure(text="Scanning PDFs...")
            self.update_idletasks()

            self.results = self.scanner.scan_directory(
                folder_path=folder_path,
                contract_numbers=contract_numbers,
            )

            self.report_service.create_report(
                output_path=output_path,
                results=self.results,
            )

            self.report_path = output_path
            self._update_preview()

            status_label.configure(
                text=f"Done. {len(self.results)} match(es) written to {output_path.name}."
            )
            messagebox.showinfo(
                APP_NAME,
                f"Scan complete.\nFound {len(self.results)} match(es).",
            )
        except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
            status_label.configure(text="Error during scan.")
            messagebox.showerror(APP_NAME, f"An error occurred:\n{exc}")

    def _update_preview(self) -> None:
        """Render the first report page as an image preview."""

        preview_label = self._require_widget(self.preview_label)

        if not self.report_path.exists():
            preview_label.configure(text="No preview available.", image=None)
            self.preview_image = None
            return

        image = render_pdf_page_to_image(
            pdf_path=self.report_path,
            page_number=0,
            zoom=PREVIEW_ZOOM,
        )

        image.thumbnail((700, 700))

        self.preview_image = ImageTk.PhotoImage(image)
        preview_label.configure(text="", image=self.preview_image)

    def _print_report(self) -> None:
        """Send the generated report to the default printer."""

        status_label = self._require_widget(self.status_label)

        try:
            self.print_service.print_pdf(self.report_path)
            status_label.configure(text="Print command sent.")
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            messagebox.showerror(APP_NAME, f"Printing failed:\n{exc}")

    @staticmethod
    def _require_widget(widget: Any) -> Any:
        """Return an initialized widget or raise a clear runtime error.

        :param widget: Widget reference that may still be ``None``.
        :returns: The validated widget reference.
        :raises RuntimeError: If the widget has not been initialized.
        """

        if widget is None:
            raise RuntimeError("Required widget is not initialized.")
        return widget
