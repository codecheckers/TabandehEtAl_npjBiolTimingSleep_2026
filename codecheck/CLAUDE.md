# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based template repository for creating [CODECHECK](https://codecheck.org.uk) certificates. CODECHECK is a process where an independent party (the codechecker) verifies that computational results can be reproduced from the provided code and data.

**Key concept**: This is NOT a standalone project - it's a template meant to be copied into a `codecheck/` subdirectory within a forked repository that is being checked. The codechecker fills out the Jupyter notebook to generate a certificate PDF.

## Architecture

### Core Components

1. **`codecheck.py`**: Python helper module with a `Codecheck` class that generates Markdown/LaTeX output for Jupyter notebooks. It reads configuration from `codecheck.yml` and provides methods to generate:
   - Title and metadata tables
   - File manifests with sizes
   - CSV file summaries using pandas `describe()`
   - LaTeX figure inclusions
   - Citation boilerplate

2. **`codecheck.ipynb`**: Template Jupyter notebook that uses the `Codecheck` class to generate a standardized certificate. Codecheckers fill in the TODO sections with notes and recommendations.

3. **`nbconvert_template.tex.j2`**: Custom nbconvert template that overrides default PDF generation settings (reduces font size, enables line breaks in verbatim output).

### Expected Directory Structure

The template assumes this structure when deployed:
```
repository-root/
├── codecheck.yml          # Configuration file (required)
└── codecheck/             # This template's files go here
    ├── codecheck.py
    ├── codecheck.ipynb
    ├── nbconvert_template.tex.j2
    ├── codecheck_logo.png
    └── outputs/           # Reproduced outputs from manifest
        └── (files matching structure in codecheck.yml manifest)
```

### Configuration File (`codecheck.yml`)

The `Codecheck` class expects a YAML file at `../codecheck.yml` (relative to the notebook) following the [CODECHECK configuration specification](https://codecheck.org.uk/spec/config/1.0/). Key fields:
- `certificate`: Certificate number
- `report`: DOI/URL of the report
- `paper`: Title, authors (with ORCID), reference
- `repository`: URL of code repository
- `codechecker`: Name and ORCID
- `check_time`: ISO format timestamp
- `summary`: Check summary text
- `manifest`: List of files with `file` path, optional `comment`, and optional `size`

## Development Commands

### Environment Setup

Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate codecheck-env
```

The environment includes:
- Jupyter notebook 6 and nbconvert 6
- pandas 1.2.4 for CSV analysis
- matplotlib 3.4 for potential plotting
- tabulate 0.8 for table formatting
- pandoc 2.10 for document conversion

### Generating the Certificate PDF

From within the `codecheck/` directory with the environment activated:
```bash
jupyter nbconvert --to pdf --no-input --no-prompt --execute \
  --LatexExporter.template_file nbconvert_template.tex.j2 codecheck.ipynb
```

This command:
- Executes all notebook cells
- Hides code cells (`--no-input`) and prompts (`--no-prompt`)
- Uses the custom LaTeX template
- Outputs `codecheck.pdf`

### Testing During Development

To test the `Codecheck` class methods interactively:
```bash
jupyter notebook codecheck.ipynb
```

Or use a Python REPL:
```python
from codecheck import Codecheck
check = Codecheck("path/to/codecheck.yml")
check.summary_table()  # Test individual methods
```

## Key Implementation Details

### Path Handling
- The `Codecheck` class defaults to reading `../codecheck.yml` (one directory up)
- Output files are expected in `outputs/` subdirectory with structure matching manifest paths
- When displaying files, directory names are stripped by default via `remove_dirname=True`

### Markdown/LaTeX Output
- Methods return `IPython.display.Markdown` or `Latex` objects for notebook rendering
- The `latex_figures()` method only handles `.pdf` and `.eps` by default (other formats need Markdown cells)
- Special characters in LaTeX output (underscores, etc.) are properly escaped

### CSV Handling
- `csv_files()` uses pandas to read and summarize all `.csv` files in the manifest
- Accepts `**kwds` that are passed to `pd.read_csv()` (e.g., `index_col=False`)
- Outputs descriptive statistics in grid format with controlled float precision

### ORCID Integration
- Authors and codecheckers include ORCID identifiers
- The `name_orcid()` helper formats as: "Name (ORCID: [0000-0000-0000-0000](https://orcid.org/0000-0000-0000-0000))"
