param(
  [Parameter(Mandatory=$true)][string]$User,
  [string]$JumpHost = $(if ($env:JUMP_HOST) { $env:JUMP_HOST } else { "192.168.1.100" }),
  [int]$Port = 12222,
  [Parameter(Mandatory=$true)][string]$KeyPath,
  [string]$HostKey = "*",
  [Parameter(Mandatory=$true)][string[]]$Command,
  [string]$WinScpPath = "C:\Program Files (x86)\WinSCP\WinSCP.com",
  [switch]$ContinueOnError
)

$ErrorActionPreference = "Stop"

try {
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [Console]::OutputEncoding
  chcp 65001 > $null
} catch {
  # Best effort only.
}

if (-not (Test-Path -LiteralPath $WinScpPath)) {
  throw "WinSCP.com not found: $WinScpPath"
}
if (-not (Test-Path -LiteralPath $KeyPath)) {
  throw "Private key not found: $KeyPath"
}

$batch = if ($ContinueOnError) { "continue" } else { "abort" }
$open = "open sftp://$User@$JumpHost`:$Port/ -privatekey=`"$KeyPath`" -hostkey=`"$HostKey`""
$args = @(
  "/ini=nul",
  "/command",
  "option batch $batch",
  "option confirm off",
  $open
) + $Command + @("exit")

& $WinScpPath @args
exit $LASTEXITCODE
