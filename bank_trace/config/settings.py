"""Central application settings for the Bank Trace package."""

from pathlib import Path

APP_NAME = "Bank Trace"
APP_WIDTH = 1360
APP_HEIGHT = 860

BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / ".bank_trace"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.json"
DEFAULT_REPORT_FILE = DATA_DIR / "bank_trace_report.pdf"

PDF_EXTENSION = ".pdf"
PREVIEW_ZOOM = 1.5
DEFAULT_APPEARANCE_MODE = "System"
DEFAULT_COLOR_THEME = "blue"
