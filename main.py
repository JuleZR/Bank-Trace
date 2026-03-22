"""Application entry point for the Bank Trace desktop client."""

from bank_trace.ui.app import BankTraceApp


def main() -> None:
    """Start the desktop application event loop."""

    app = BankTraceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
