"""GUI application for Bank Trace."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

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
from bank_trace.services.pdf_service import (
    get_pdf_page_count,
    render_pdf_page_to_image,
)
from bank_trace.services.report_service import ReportService
from bank_trace.services.storage_service import StorageService


class BankTraceApp(ctk.CTk):
    """Main desktop application for scanning bank statement PDFs."""

    def __init__(self) -> None:
        """Initialize the main window, services, and preview state."""

        super().__init__()

        ctk.set_appearance_mode(DEFAULT_APPEARANCE_MODE)
        ctk.set_default_color_theme(DEFAULT_COLOR_THEME)

        self.title(APP_NAME)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(1180, 760)

        self.storage_service = StorageService()
        self.scanner = StatementScanner()
        self.report_service = ReportService()

        self.results: list[MatchResult] = []
        self.report_path = Path(DEFAULT_REPORT_FILE)

        self.preview_image: Image.PhotoImage | None = None
        self.preview_page_index = 0
        self.preview_page_count = 0

        self.left_frame: ctk.CTkFrame | None = None
        self.right_frame: ctk.CTkFrame | None = None

        self.folder_entry: ctk.CTkEntry | None = None
        self.contracts_textbox: ctk.CTkTextbox | None = None
        self.output_entry: ctk.CTkEntry | None = None

        self.preview_label: ctk.CTkLabel | None = None
        self.status_label: ctk.CTkLabel | None = None
        self.page_label: ctk.CTkLabel | None = None
        self.prev_button: ctk.CTkButton | None = None
        self.next_button: ctk.CTkButton | None = None

        self._build_layout()
        self._load_saved_config()
        self._update_preview_navigation()

    def _build_layout(self) -> None:
        """Create the two-column layout of the main application window."""

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
        """Build the input and action controls shown on the left side."""

        left_frame = self._require_widget(self.left_frame)

        title_label = ctk.CTkLabel(
            left_frame,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=16, pady=(16, 10), sticky="w")

        folder_label = ctk.CTkLabel(left_frame, text="PDF folder")
        folder_label.grid(row=1, column=0, padx=16, pady=(10, 4), sticky="w")

        folder_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
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

        contracts_label = ctk.CTkLabel(left_frame, text="Contract numbers")
        contracts_label.grid(row=3, column=0, padx=16, pady=(10, 4), sticky="w")

        self.contracts_textbox = ctk.CTkTextbox(left_frame, height=240)
        self.contracts_textbox.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")

        output_label = ctk.CTkLabel(left_frame, text="Output PDF")
        output_label.grid(row=5, column=0, padx=16, pady=(10, 4), sticky="w")

        output_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
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

        button_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        button_frame.grid(row=7, column=0, padx=16, pady=(10, 10), sticky="ew")
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

        open_button = ctk.CTkButton(
            left_frame,
            text="Open PDF",
            command=self._open_report,
        )
        open_button.grid(row=8, column=0, padx=16, pady=(0, 16), sticky="ew")

    def _build_right_panel(self) -> None:
        """Build the preview, pagination, and status area."""

        right_frame = self._require_widget(self.right_frame)

        header = ctk.CTkLabel(
            right_frame,
            text="Preview",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.preview_label = ctk.CTkLabel(
            right_frame,
            text="No preview available.",
            anchor="center",
        )
        self.preview_label.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")

        nav_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        nav_frame.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")
        nav_frame.grid_columnconfigure(1, weight=1)

        self.prev_button = ctk.CTkButton(
            nav_frame,
            text="Previous",
            width=110,
            command=self._show_previous_preview_page,
        )
        self.prev_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.page_label = ctk.CTkLabel(
            nav_frame,
            text="Page 0 / 0",
            anchor="center",
        )
        self.page_label.grid(row=0, column=1, sticky="ew")

        self.next_button = ctk.CTkButton(
            nav_frame,
            text="Next",
            width=110,
            command=self._show_next_preview_page,
        )
        self.next_button.grid(row=0, column=2, padx=(8, 0), sticky="e")

        self.status_label = ctk.CTkLabel(
            right_frame,
            text="Ready.",
            anchor="w",
        )
        self.status_label.grid(row=3, column=0, padx=16, pady=(8, 16), sticky="ew")

    def _load_saved_config(self) -> None:
        """Populate the form with the last saved configuration."""

        folder_entry = self._require_widget(self.folder_entry)
        contracts_textbox = self._require_widget(self.contracts_textbox)
        output_entry = self._require_widget(self.output_entry)

        config = self.storage_service.load_config()

        folder = str(config.get("folder", ""))
        contract_numbers = config.get("contract_numbers", [])
        output_file = str(config.get("output_file", "")) or str(self.report_path)

        folder_entry.delete(0, "end")
        folder_entry.insert(0, folder)

        contracts_textbox.delete("1.0", "end")
        contracts_textbox.insert("1.0", "\n".join(contract_numbers))

        output_entry.delete(0, "end")
        output_entry.insert(0, output_file)

    def _save_config(self) -> None:
        """Persist the current form values and notify the user."""

        status_label = self._require_widget(self.status_label)

        folder = self._require_widget(self.folder_entry).get().strip()
        contract_numbers = self._get_contract_numbers()
        output_file = self._require_widget(self.output_entry).get().strip()

        self.storage_service.save_config(
            folder=folder,
            contract_numbers=contract_numbers,
            output_file=output_file,
        )

        status_label.configure(text="Settings saved.")
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
        """Open a save dialog and update the output PDF field."""

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
        """Return cleaned contract numbers from the multiline input box.

        :returns: Non-empty, stripped contract numbers in input order.
        """

        contracts_textbox = self._require_widget(self.contracts_textbox)
        raw_text = contracts_textbox.get("1.0", "end").strip()
        lines = [line.strip() for line in raw_text.splitlines()]
        return [line for line in lines if line]

    def _run_scan(self) -> None:
        """Scan the selected PDFs, generate the report, and refresh preview."""

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
            self.preview_page_index = 0
            self.preview_page_count = get_pdf_page_count(self.report_path)

            self._update_preview()
            self._update_preview_navigation()

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
        """Render the currently selected report page into the preview pane."""

        preview_label = self._require_widget(self.preview_label)

        if not self.report_path.exists():
            preview_label.configure(text="No preview available.", image=None)
            self.preview_image = None
            return

        image = render_pdf_page_to_image(
            pdf_path=self.report_path,
            page_number=self.preview_page_index,
            zoom=PREVIEW_ZOOM,
        )

        image.thumbnail((760, 760))

        self.preview_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size,
        )
        preview_label.configure(text="", image=self.preview_image)

    def _update_preview_navigation(self) -> None:
        """Refresh preview page labels and navigation button states."""

        page_label = self._require_widget(self.page_label)
        prev_button = self._require_widget(self.prev_button)
        next_button = self._require_widget(self.next_button)

        if self.preview_page_count <= 0:
            page_label.configure(text="Page 0 / 0")
            prev_button.configure(state="disabled")
            next_button.configure(state="disabled")
            return

        page_label.configure(
            text=f"Page {self.preview_page_index + 1} / {self.preview_page_count}"
        )

        prev_button.configure(
            state="normal" if self.preview_page_index > 0 else "disabled"
        )
        next_button.configure(
            state="normal"
            if self.preview_page_index < self.preview_page_count - 1
            else "disabled"
        )

    def _show_previous_preview_page(self) -> None:
        """Move the preview to the previous report page when available."""

        if self.preview_page_index <= 0:
            return

        self.preview_page_index -= 1
        self._update_preview()
        self._update_preview_navigation()

    def _show_next_preview_page(self) -> None:
        """Move the preview to the next report page when available."""

        if self.preview_page_index >= self.preview_page_count - 1:
            return

        self.preview_page_index += 1
        self._update_preview()
        self._update_preview_navigation()

    def _open_report(self) -> None:
        """Open the generated report with the operating system default viewer."""

        if not self.report_path.exists():
            messagebox.showwarning(APP_NAME, "No report file exists yet.")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.report_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self.report_path)], check=True)
            else:
                subprocess.run(["xdg-open", str(self.report_path)], check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror(APP_NAME, f"Could not open PDF:\n{exc}")

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
