"""PDF utility helpers for text extraction and preview rendering."""

from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image


def extract_text_per_page(pdf_path: Path) -> list[str]:
    """Extract plain text for every page in a PDF document.

    :param pdf_path: Path to the PDF file.
    :returns: Extracted page texts in document order.
    """

    texts: list[str] = []

    with fitz.open(pdf_path) as document:
        for page in document:
            texts.append(page.get_text("text"))

    return texts


def render_pdf_page_to_image(
    pdf_path: Path,
    page_number: int = 0,
    zoom: float = 1.5,
) -> Image.Image:
    """Render a PDF page to a Pillow image for UI preview purposes.

    :param pdf_path: Path to the PDF file.
    :param page_number: Zero-based page index to render.
    :param zoom: Scaling factor applied during rendering.
    :returns: Rendered page image.
    :raises IndexError: If ``page_number`` is outside the document range.
    """

    with fitz.open(pdf_path) as document:
        if page_number < 0 or page_number >= len(document):
            raise IndexError("Page number is out of range.")

        page = document[page_number]
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        image = Image.frombytes(
            "RGB",
            (pixmap.width, pixmap.height),
            pixmap.samples,
        )
        return image
