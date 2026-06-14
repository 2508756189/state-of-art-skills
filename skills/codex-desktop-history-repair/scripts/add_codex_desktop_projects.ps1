param(
  [string[]]$Roots = @(),

  [string]$RootsFile,

  [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex"),

  [switch]$DoNotActivate
)

$ErrorActionPreference = "Stop"

$statePath = Join-Path $CodexHome ".codex-global-state.json"
if (-not (Test-Path -LiteralPath $statePath)) {
  throw "State file not found: $statePath"
}

$running = Get-Process -ErrorAction SilentlyContinue |
  Where-Object { $_.ProcessName -in @("Codex", "codex") }
if ($running) {
  Write-Warning "Codex/Codex CLI processes are running. Codex Desktop can overwrite this file while open."
  Write-Warning "For durable sidebar changes, close Codex Desktop and rerun this script."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = "$statePath.before-add-projects-$stamp.bak"
Copy-Item -LiteralPath $statePath -Destination $backupPath -Force

$json = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json

$normalizedRoots = @()
if ($RootsFile) {
  if (-not (Test-Path -LiteralPath $RootsFile)) {
    throw "Roots file not found: $RootsFile"
  }
  $rootsText = Get-Content -LiteralPath $RootsFile -Raw -Encoding UTF8
  $parsedRoots = $null
  try {
    $parsedRoots = $rootsText | ConvertFrom-Json
  } catch {
    $parsedRoots = $rootsText -split "`r?`n"
  }
  foreach ($root in @($parsedRoots)) {
    if ($null -ne $root -and "$root".Trim().Length -gt 0) {
      $normalizedRoots += "$root".Trim()
    }
  }
}
foreach ($root in $Roots) {
  if ($null -eq $root) {
    continue
  }
  foreach ($part in ($root -split ",")) {
    $trimmed = $part.Trim()
    if ($trimmed.Length -gt 0) {
      $normalizedRoots += $trimmed
    }
  }
}

if ($normalizedRoots.Count -eq 0) {
  throw "No project roots supplied. Use -Roots or -RootsFile."
}

function Ensure-ArrayProperty($Object, [string]$Name) {
  if (-not ($Object.PSObject.Properties.Name -contains $Name) -or $null -eq $Object.$Name) {
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue @() -Force
  }
  if ($Object.$Name -isnot [System.Array]) {
    $Object.$Name = @($Object.$Name)
  }
}

Ensure-ArrayProperty $json "electron-saved-workspace-roots"
Ensure-ArrayProperty $json "project-order"
Ensure-ArrayProperty $json "active-workspace-roots"

foreach ($root in $normalizedRoots) {
  if (-not (Test-Path -LiteralPath $root)) {
    New-Item -ItemType Directory -Force -Path $root | Out-Null
  }
  if ($json."electron-saved-workspace-roots" -notcontains $root) {
    $json."electron-saved-workspace-roots" += $root
  }
  if ($json."project-order" -notcontains $root) {
    $json."project-order" += $root
  }
  if (-not $DoNotActivate -and $json."active-workspace-roots" -notcontains $root) {
    $json."active-workspace-roots" += $root
  }
}

$out = $json | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText(
  $statePath,
  $out + [Environment]::NewLine,
  [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Updated Codex Desktop project roots."
Write-Host "Backup: $backupPath"
foreach ($root in $normalizedRoots) {
  Write-Host " - $root"
}
