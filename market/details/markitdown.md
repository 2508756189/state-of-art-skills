# MarkItDown

Use this skill when the task is to turn mixed source files into useful Markdown for reading, summarization, migration, or downstream analysis.

## Source

Inspired by Microsoft MarkItDown: `https://github.com/microsoft/markitdown` (MIT).

Do not vendor the upstream project into this skill. Install or invoke it as a dependency when needed.

## Workflow

1. Identify input type and whether the user needs faithful extraction, readable Markdown, or evidence-grade conversion.
2. Prefer local conversion. Avoid uploading private files to third-party services unless the user explicitly asks.
3. If `markitdown` is available, use it first.
4. If it is unavailable, use local fallbacks appropriate to the file type, such as `python-docx`, `pypdf`, `pdfplumber`, `openpyxl`, or plain text parsers.
5. Preserve source filenames and page/sheet/section boundaries when they matter.
6. Save converted Markdown beside the requested output path or in a clearly named working folder.
7. Report conversion caveats, especially OCR gaps, scanned PDFs, embedded images, tables, formulas, comments, and tracked changes.

## Commands

Check availability:

```bash
python -m markitdown --help
```

Common conversion shape:

```bash
python -m markitdown input.pdf > output.md
```

If the package is missing and installation is acceptable:

```bash
python -m pip install markitdown
```

## Quality Checks

- Open the generated Markdown and confirm it contains real content, not only metadata.
- For PDFs, sample beginning, middle, and end pages.
- For spreadsheets, confirm sheet names and key columns survived.
- For Office files, flag comments, tracked changes, embedded media, and unsupported layout.
