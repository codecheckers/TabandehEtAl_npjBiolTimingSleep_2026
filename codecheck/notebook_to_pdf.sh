#!/bin/bash
set -e  # exit on error

# Notebook name (without extension)
NOTEBOOK="codecheck"
MARKDOWN_FILE="${NOTEBOOK}.md"

# Delete old Markdown to ensure we wait for the new one
if [ -f "$MARKDOWN_FILE" ]; then
    echo "[CODECHECK - Py] Deleting old $MARKDOWN_FILE..."
    rm "$MARKDOWN_FILE"
fi

# Convert notebook to Markdown
echo "[CODECHECK - Py] Converting $NOTEBOOK.ipynb to Markdown..."
jupyter nbconvert --to markdown --no-input --no-prompt --execute --LatexExporter.template_file nbconvert_template.tex.j2 "$NOTEBOOK.ipynb"

# Wait until Markdown is created
echo "[CODECHECK - Py] Waiting for $MARKDOWN_FILE to be created..."
while [ ! -f "$MARKDOWN_FILE" ]; do
    sleep 0.5
done

echo "[CODECHECK - Py] $MARKDOWN_FILE found."

# Start Typst compile
echo "[CODECHECK - Py] Compiling $NOTEBOOK.typ to PDF..."
typst compile "${NOTEBOOK}.typ"
echo "[CODECHECK - Py] Done compiling!"