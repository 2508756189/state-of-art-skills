---
name: ai-read-fix
description: "Use when Codex or shell tools cannot reliably read or write local files, paths, or command output, especially on Windows: `rg` blocked by WindowsApps, PowerShell mojibake, UTF-8/BOM issues, Chinese path/value handling, PDF text extraction fallbacks, and cases where output is empty, garbled, or access-denied."
---

# AI Read Fix

Use this skill when the problem is not the business logic itself, but the agent's ability to read files or tool output correctly.

Typical triggers:

- `rg` exists but running it returns `Access is denied`
- PowerShell output is garbled for Chinese comments, paths, or logs
- `Get-Content` reads a file but displayed text looks like mojibake
- generated command files, JSON, Postman artifacts, or SQL snippets contain garbled Chinese or UTF-8 BOM side effects
- the file definitely exists, yet search output is empty or obviously wrong
- Windows paths with spaces, Chinese names, or `WindowsApps` shims behave strangely
- PDF text extraction fails or yields poor text and a fallback path is needed

## Core workflow

1. Confirm the failure boundary.
   - Command cannot execute
   - Command executes but output is wrong
   - File content is correct but terminal decoding is wrong
   - The format itself needs another extractor, such as PDF or DOCX
2. Check what executable is really being called.
   - `Get-Command <tool> -All`
   - `where.exe <tool>`
   - compare PATH order before changing anything
3. Prefer user-space fixes over system-wide policy changes.
   - If `rg.exe` under `WindowsApps` is blocked, copy a working binary to a user-writable path and prepend that path
   - avoid changing Defender, AppLocker, or machine-wide execution policy unless the user explicitly asks
4. Separate bytes from display.
   - A file may be fine while PowerShell renders it badly
   - verify by reopening with a different reader, decoding with the expected charset, or checking raw bytes
5. Separate read bugs from write bugs.
   - read bug: source bytes are correct but displayed output is garbled
   - write bug: Codex/shell generated wrong bytes, `?`, mojibake, or a BOM that breaks remote shell execution
   - fix write bugs before retrying business logic; do not work around by changing Chinese values to ASCII
6. For structured files, switch tools instead of forcing plain-text reads.
   - PDF: use `pypdf` or `pdfplumber`; visually inspect when layout matters
   - DOCX: use `python-docx`
   - Images or screenshots: use OCR or image-aware tools only if needed

## Fast fixes

### `rg` on Windows returns `Access is denied`

1. Identify the blocked binary:
   - `Get-Command rg -All`
   - `where.exe rg`
2. If it resolves to a packaged app path under `WindowsApps`, prefer a local copy:
   - create a user bin directory such as `C:\Users\<user>\AppData\Local\Programs\rg\bin`
   - copy `rg.exe` there
   - prepend that directory to the user PATH and current session PATH
3. Re-verify with:
   - `rg --version`
   - a real search against a known file

### PowerShell output is garbled

1. Do not assume the file is broken.
2. Try another reader or decoding path first:
   - reopen with Python and explicit encoding if known
   - for GBK/GB2312 text, decode with `gbk`
   - for unknown encodings, inspect with multiple candidates rather than editing blindly
3. If the terminal only affects display, state that clearly and avoid describing the source file as corrupted.

### Writing UTF-8 files on Windows

1. Prefer deterministic writers over ambiguous PowerShell defaults.
2. For command files consumed by Linux shells or JumpServer helpers, write UTF-8 without BOM:
   ```powershell
   [System.IO.File]::WriteAllLines($path, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
   ```
3. Do not put required Chinese literals directly inside a fragile PowerShell command string. If this shell path converts them to `?`, build them with code points, JSON files, or another UTF-8-safe writer.
4. If using `Set-Content`, verify the current PowerShell supports the requested encoding. Windows PowerShell 5 often lacks `utf8NoBOM`.
5. After writing Chinese values, verify code points or JSON parse result, not only terminal display.
6. For command files, strip or avoid BOM; a leading BOM can be prepended to the first command token, such as `cd` or `whoami`, and make the remote shell report "command not found".

### Chinese paths or spaces break commands

- Prefer `-LiteralPath`
- Quote full paths
- Avoid composing shell fragments that rely on implicit globbing
- When searching recursively, prefer explicit roots over current-directory assumptions

### Chinese business values

- Do not replace required Chinese values such as license plates with ASCII just because output is garbled.
- Preserve the original value in UTF-8 files, JSON files, Unicode escapes, or explicit code points such as `[char]0x95fd` for `闽`.
- Verify the stored value by parsing it back or checking code points.

### PDF content reads badly

- Use `pypdf` or `pdfplumber` for text extraction
- If text quality is poor but layout matters, use a PDF skill and render pages for visual review
- Treat extracted text as a hint, not the final ground truth, for table-heavy or image-based PDFs

## Skill coordination

- Use `pdf` when the underlying issue is PDF extraction or rendering quality.
- Use `doc` when the file is a DOCX and formatting fidelity matters.
- Use `production-ops` or `cpw-production-ops` only after the local read environment is trustworthy.
- For vendor protocol debugging on Windows repos with Chinese paths, use this skill first if file reads are unreliable.

## References

Load [references/windows-read-triage.md](references/windows-read-triage.md) when you need the concrete command sequence for `rg`, PATH, PowerShell decoding, and PDF fallback checks.

## Verification checklist

- The actual executable path is identified, not guessed.
- A user-space or session-scoped fix is preferred over a machine-wide policy change.
- At least one real file search or file read succeeds after the fix.
- Any remaining mojibake is identified as display-only or source-content, not conflated.
