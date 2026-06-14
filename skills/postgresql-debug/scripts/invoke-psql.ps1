[CmdletBinding(DefaultParameterSetName = "InlineSql")]
param(
    [Parameter(Mandatory = $true, ParameterSetName = "InlineSql")]
    [string]$Sql,

    [Parameter(Mandatory = $true, ParameterSetName = "SqlFile")]
    [string]$SqlFile,

    [string]$Container,
    [string]$DatabaseUrl,
    [string]$DbHost,
    [int]$Port,
    [string]$Database,
    [string]$User,
    [string]$Password,
    [int]$StatementTimeoutMs = 30000,
    [switch]$AllowWrite,
    [switch]$Expanded,
    [switch]$TuplesOnly,
    [switch]$NoAlign
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
    chcp 65001 > $null
} catch {
    # Best effort only. Continue even if the host shell does not allow changing code pages.
}

function Ensure-NodePgRuntime {
    $node = Get-Command node -ErrorAction SilentlyContinue
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $node -or -not $npm) {
        throw "psql is not available, and Node.js/npm are also unavailable for the fallback route."
    }

    $runtimeRoot = Join-Path $env:TEMP "codex-pg-runtime"
    $moduleDir = Join-Path $runtimeRoot "node_modules\pg"

    if (-not (Test-Path -LiteralPath $moduleDir)) {
        New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
        if (-not (Test-Path -LiteralPath (Join-Path $runtimeRoot "package.json"))) {
            Push-Location $runtimeRoot
            try {
                & $npm.Source init -y | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "npm init failed with code $LASTEXITCODE."
                }
            } finally {
                Pop-Location
            }
        }

        Push-Location $runtimeRoot
        try {
            & $npm.Source install --silent --no-save pg
            if ($LASTEXITCODE -ne 0) {
                throw "npm install pg failed with code $LASTEXITCODE."
            }
        } finally {
            Pop-Location
        }
    }

    return [pscustomobject]@{
        NodePath = $node.Source
        RuntimeRoot = $runtimeRoot
    }
}

function Invoke-NodePgFallback {
    param(
        [string]$RuntimeRoot,
        [string]$NodePath,
        [string]$ResolvedDatabaseUrl,
        [string]$ResolvedHost,
        [int]$ResolvedPort,
        [string]$ResolvedDatabase,
        [string]$ResolvedUser,
        [string]$ResolvedPassword,
        [string]$ResolvedSqlToRun,
        [int]$ResolvedStatementTimeoutMs,
        [switch]$ResolvedAllowWrite,
        [switch]$UseExpanded,
        [switch]$UseTuplesOnly,
        [switch]$UseNoAlign
    )

    $runnerPath = Join-Path $PSScriptRoot "run-pg-query.js"
    if (-not (Test-Path -LiteralPath $runnerPath)) {
        throw "Node fallback script not found: $runnerPath"
    }

    $connection = if ($ResolvedDatabaseUrl) {
        @{ connectionString = $ResolvedDatabaseUrl }
    } else {
        @{
            host = $ResolvedHost
            port = if ($ResolvedPort -gt 0) { $ResolvedPort } else { 5432 }
            database = $ResolvedDatabase
            user = $ResolvedUser
            password = $ResolvedPassword
        }
    }

    $previousConnectionJson = $env:CODEX_PG_CONNECTION_JSON
    $previousSql = $env:CODEX_PG_SQL
    $previousTimeout = $env:CODEX_PG_TIMEOUT_MS
    $previousAllowWrite = $env:CODEX_PG_ALLOW_WRITE
    $previousExpanded = $env:CODEX_PG_EXPANDED
    $previousTuplesOnly = $env:CODEX_PG_TUPLES_ONLY
    $previousNoAlign = $env:CODEX_PG_NO_ALIGN
    $previousNodePath = $env:NODE_PATH

    try {
        $env:CODEX_PG_CONNECTION_JSON = $connection | ConvertTo-Json -Compress -Depth 5
        $env:CODEX_PG_SQL = $ResolvedSqlToRun
        $env:CODEX_PG_TIMEOUT_MS = [string]$ResolvedStatementTimeoutMs
        $env:CODEX_PG_ALLOW_WRITE = if ($ResolvedAllowWrite) { "true" } else { "false" }
        $env:CODEX_PG_EXPANDED = if ($UseExpanded) { "true" } else { "false" }
        $env:CODEX_PG_TUPLES_ONLY = if ($UseTuplesOnly) { "true" } else { "false" }
        $env:CODEX_PG_NO_ALIGN = if ($UseNoAlign) { "true" } else { "false" }
        $env:NODE_PATH = Join-Path $RuntimeRoot "node_modules"

        Push-Location $RuntimeRoot
        try {
            & $NodePath $runnerPath
            if ($LASTEXITCODE -ne 0) {
                throw "Node pg fallback exited with code $LASTEXITCODE."
            }
        } finally {
            Pop-Location
        }
    } finally {
        $env:CODEX_PG_CONNECTION_JSON = $previousConnectionJson
        $env:CODEX_PG_SQL = $previousSql
        $env:CODEX_PG_TIMEOUT_MS = $previousTimeout
        $env:CODEX_PG_ALLOW_WRITE = $previousAllowWrite
        $env:CODEX_PG_EXPANDED = $previousExpanded
        $env:CODEX_PG_TUPLES_ONLY = $previousTuplesOnly
        $env:CODEX_PG_NO_ALIGN = $previousNoAlign
        $env:NODE_PATH = $previousNodePath
    }
}

function Resolve-SqlText {
    param(
        [string]$InlineSql,
        [string]$FilePath
    )

    if ($InlineSql) {
        return $InlineSql
    }

    if (-not (Test-Path -LiteralPath $FilePath)) {
        throw "SQL file not found: $FilePath"
    }

    try {
        return Get-Content -Raw -LiteralPath $FilePath -Encoding utf8
    } catch {
        return Get-Content -Raw -LiteralPath $FilePath
    }
}

function Normalize-Sql {
    param(
        [string]$Text
    )

    $trimmed = $Text.Trim()
    if (-not $trimmed.EndsWith(";")) {
        $trimmed = "$trimmed`n;"
    }
    return $trimmed
}

function Wrap-Sql {
    param(
        [string]$Text,
        [int]$TimeoutMs,
        [bool]$AllowWrites
    )

    $body = Normalize-Sql -Text $Text
    if ($AllowWrites) {
        if ($TimeoutMs -gt 0) {
            return "set statement_timeout = '$($TimeoutMs)ms';`n$body"
        }
        return $body
    }

    $lines = @(
        "begin;",
        "set transaction read only;"
    )

    if ($TimeoutMs -gt 0) {
        $lines += "set local statement_timeout = '$($TimeoutMs)ms';"
    }

    $lines += $body
    $lines += "rollback;"

    return ($lines -join "`n")
}

function Build-PsqlArgs {
    param(
        [string]$ResolvedDatabaseUrl,
        [string]$ResolvedHost,
        [int]$ResolvedPort,
        [string]$ResolvedDatabase,
        [string]$ResolvedUser,
        [switch]$UseExpanded,
        [switch]$UseTuplesOnly,
        [switch]$UseNoAlign
    )

    $args = @("-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off")

    if ($UseExpanded) {
        $args += "-x"
    }
    if ($UseTuplesOnly) {
        $args += "-t"
    }
    if ($UseNoAlign) {
        $args += "-A"
    }

    if ($ResolvedDatabaseUrl) {
        $args += $ResolvedDatabaseUrl
        return $args
    }

    if ($ResolvedHost) {
        $args += @("-h", $ResolvedHost)
    }
    if ($ResolvedPort -gt 0) {
        $args += @("-p", $ResolvedPort.ToString())
    }
    if ($ResolvedDatabase) {
        $args += @("-d", $ResolvedDatabase)
    }
    if ($ResolvedUser) {
        $args += @("-U", $ResolvedUser)
    }

    return $args
}

$resolvedSql = Resolve-SqlText -InlineSql $Sql -FilePath $SqlFile
$sqlToRun = Wrap-Sql -Text $resolvedSql -TimeoutMs $StatementTimeoutMs -AllowWrites:$AllowWrite

$resolvedDatabaseUrl = if ($DatabaseUrl) { $DatabaseUrl } elseif ($env:DATABASE_URL) { $env:DATABASE_URL } elseif ($env:POSTGRES_URL) { $env:POSTGRES_URL } else { $null }
$resolvedHost = if ($DbHost) { $DbHost } elseif ($env:PGHOST) { $env:PGHOST } else { $null }
$resolvedPort = if ($Port) { $Port } elseif ($env:PGPORT) { [int]$env:PGPORT } else { 0 }
$resolvedDatabase = if ($Database) { $Database } elseif ($env:PGDATABASE) { $env:PGDATABASE } else { $null }
$resolvedUser = if ($User) { $User } elseif ($env:PGUSER) { $env:PGUSER } else { $null }
$resolvedPassword = if ($Password) { $Password } elseif ($env:PGPASSWORD) { $env:PGPASSWORD } else { $null }

$psqlArgs = Build-PsqlArgs `
    -ResolvedDatabaseUrl $resolvedDatabaseUrl `
    -ResolvedHost $resolvedHost `
    -ResolvedPort $resolvedPort `
    -ResolvedDatabase $resolvedDatabase `
    -ResolvedUser $resolvedUser `
    -UseExpanded:$Expanded `
    -UseTuplesOnly:$TuplesOnly `
    -UseNoAlign:$NoAlign

$originalPgPassword = $env:PGPASSWORD
try {
    if ($resolvedPassword) {
        $env:PGPASSWORD = $resolvedPassword
    }

    if ($Container) {
        $docker = Get-Command docker -ErrorAction SilentlyContinue
        if (-not $docker) {
            throw "docker is not available. Remove -Container or install Docker."
        }

        $commandArgs = @("exec", "-i", $Container, "psql") + $psqlArgs
        $sqlToRun | & $docker.Source @commandArgs
    } else {
        $psql = Get-Command psql -ErrorAction SilentlyContinue
        if (-not $psql) {
            $runtime = Ensure-NodePgRuntime
            Invoke-NodePgFallback `
                -RuntimeRoot $runtime.RuntimeRoot `
                -NodePath $runtime.NodePath `
                -ResolvedDatabaseUrl $resolvedDatabaseUrl `
                -ResolvedHost $resolvedHost `
                -ResolvedPort $resolvedPort `
                -ResolvedDatabase $resolvedDatabase `
                -ResolvedUser $resolvedUser `
                -ResolvedPassword $resolvedPassword `
                -ResolvedSqlToRun $resolvedSql `
                -ResolvedStatementTimeoutMs $StatementTimeoutMs `
                -ResolvedAllowWrite:$AllowWrite `
                -UseExpanded:$Expanded `
                -UseTuplesOnly:$TuplesOnly `
                -UseNoAlign:$NoAlign
            return
        }

        $sqlToRun | & $psql.Source @psqlArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "psql exited with code $LASTEXITCODE."
    }
} finally {
    $env:PGPASSWORD = $originalPgPassword
}
