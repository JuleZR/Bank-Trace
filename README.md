# Bank Trace

Bank Trace is a desktop application for scanning bank statement PDFs and extracting entries related to specific contract numbers. It is designed for operational workflows where users need to review multiple statements quickly, identify matching lines, and generate a clean PDF report for follow-up, documentation, or printing.

The application provides a graphical interface built with `customtkinter`, processes PDF files with `PyMuPDF`, and creates structured reports with `ReportLab`.

## Features

- Scan an entire folder of PDF bank statements
- Search for one or more contract numbers in extracted page text
- Detect related amount values from matching lines
- Identify statement labels such as statement numbers when available
- Generate a consolidated PDF report with all matches
- Preview the generated report directly in the UI
- Save the selected folder, contract numbers, and output path locally
- Send the generated report to the default printer

## How It Works

1. Select a folder that contains bank statement PDFs.
2. Enter one contract number per line.
3. Choose the destination for the generated report.
4. Start the scan.
5. Review the generated PDF preview and optionally print the report.

For each PDF file, Bank Trace extracts text page by page, searches for the provided contract numbers, reads the amount from the same matching line, and writes all findings into a structured PDF report.

## Requirements

- Python 3.11 or newer recommended
- A desktop environment capable of running `tkinter`
- PDF documents with text content available for extraction

## Installation

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

## Dependencies

The project currently depends on:

- `customtkinter`
- `PyMuPDF`
- `Pillow`
- `reportlab`

## Running the Application

Start the desktop application with:

```bash
python main.py
```

## Output and Local Data

Bank Trace creates a local application data directory at:

```text
.bank_trace/
```

This directory is used for:

- `config.json` - saved UI settings such as folder, contract numbers, and output file
- `bank_trace_report.pdf` - default generated report location

## Report Contents

The generated report includes the following columns:

- Contract Number
- Amount
- Statement
- File
- Page
- Source Line

If no matches are found, the report is still created and clearly states that no matching entries were detected.

## Project Structure

```text
bank_trace/
|-- config/
|   `-- settings.py
|-- core/
|   |-- extractor.py
|   |-- models.py
|   `-- scanner.py
|-- services/
|   |-- pdf_service.py
|   |-- print_service.py
|   |-- report_service.py
|   `-- storage_service.py
`-- ui/
    `-- app.py
main.py
requirements.txt
```

## Architecture Overview

- `ui`: desktop interface and user interaction flow
- `core`: scanning logic, pattern matching, and result models
- `services`: PDF handling, report creation, persistence, and printing
- `config`: application-wide settings and default paths

## Notes and Limitations

- The scan quality depends on whether text can be extracted from the PDFs. Image-only scans without OCR may not produce usable results.
- Amount extraction is based on values found in the same line as a contract number.
- Statement label detection supports common German and English statement formats, but may need adjustment for other document templates.

## License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
