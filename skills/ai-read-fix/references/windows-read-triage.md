# Windows Read/Write Triage

Use this reference only when the core skill has already triggered and you need concrete commands.

## 1. Identify the real executable

```powershell
Get-Command rg -All
where.exe rg
```

If the path points to `WindowsApps` and execution is blocked, prefer a local user copy.

## 2. Install a user-space `rg`

```powershell
$src = 'C:\Program Files\WindowsApps\<package>\app\resources\rg.exe'
$dstDir = 'C:\Users\<user>\AppData\Local\Programs\rg\bin'
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
Copy-Item -LiteralPath $src -Destination (Join-Path $dstDir 'rg.exe') -Force

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = if ($userPath) { $userPath -split ';' | Where-Object { $_ } } else { @() }
if (-not ($parts -contains $dstDir)) {
  [Environment]::SetEnvironmentVariable('Path', ($dstDir + ';' + ($parts -join ';')).TrimEnd(';'), 'User')
}
$env:PATH = $dstDir + ';' + $env:PATH
```

Verify:

```powershell
rg --version
rg -n "needle" "C:\path\to\file.js"
```

## 3. Distinguish display encoding from file corruption

If comments or Chinese text look garbled in PowerShell:

- reopen with another tool before editing
- verify the bytes with Python if needed
- if it is a known legacy charset, decode explicitly

Example:

```powershell
@'
from pathlib import Path
path = Path(r"C:\path\to\file.txt")
data = path.read_bytes()
for enc in ("utf-8", "gbk", "gb18030"):
    try:
        print(f"--- {enc} ---")
        print(data.decode(enc)[:500])
    except Exception as exc:
        print(enc, exc)
'@ | python -
```

## 4. Prefer format-native readers

- PDF text extraction: `pypdf`, `pdfplumber`
- DOCX content extraction: `python-docx`
- Avoid forcing `Get-Content` on binary or zipped office formats

## 5. Write UTF-8 without BOM

Use this for command files, JSON, Postman artifacts, SQL snippets, or any file
that must preserve Chinese values and avoid a leading BOM:

```powershell
$path = "C:\path\to\file.txt"
$plate = ([char]0x95fd) + "A88888"
$lines = [string[]]@(
  "cd /data/projects/parking_platform_service",
  "echo $plate"
)
[System.IO.File]::WriteAllLines($path, $lines, [System.Text.UTF8Encoding]::new($false))
```

Verify the bytes and code points after writing:

```powershell
@'
from pathlib import Path
path = Path(r"C:\path\to\file.txt")
data = path.read_bytes()
print("has_bom=", data.startswith(b"\xef\xbb\xbf"))
text = data.decode("utf-8")
print(text)
plate = "\u95fdA88888"
print("contains_plate=", plate in text)
print([hex(ord(ch)) for ch in plate])
'@ | python -
```

If Windows PowerShell rejects `-Encoding utf8NoBOM`, do not keep retrying
`Set-Content`; use the .NET `WriteAllLines` form above.

If a Chinese literal typed into a PowerShell command becomes `?`, treat the
command input path as unsafe. Use explicit code points, Unicode escapes, or an
already UTF-8 encoded file instead.

## 6. Command hygiene

- Prefer `-LiteralPath` for paths with brackets, spaces, or Chinese characters
- Quote full absolute paths
- Use explicit working directories
- When a search tool fails unexpectedly, validate on a known file before assuming the repo is the issue
