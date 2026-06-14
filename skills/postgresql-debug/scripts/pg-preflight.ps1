[CmdletBinding()]
param(
    [string]$Container,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DockerCandidates {
    param(
        [string]$PreferredContainer
    )

    if ($PreferredContainer) {
        return @($PreferredContainer)
    }

    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        return @()
    }

    try {
        $lines = & $docker.Source ps --format "{{.Names}}|{{.Image}}" 2>$null
        if ($LASTEXITCODE -ne 0) {
            return @()
        }
    } catch {
        return @()
    }

    $matches = @()
    foreach ($line in $lines) {
        if (-not $line) {
            continue
        }

        $parts = $line -split "\|", 2
        $name = $parts[0]
        $image = if ($parts.Count -gt 1) { $parts[1] } else { "" }

        if ($name -match "postgres|postgis|timescale" -or $image -match "postgres|postgis|timescale") {
            $matches += $name
        }
    }

    return $matches | Select-Object -Unique
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
$docker = Get-Command docker -ErrorAction SilentlyContinue
$node = Get-Command node -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
$databaseUrl = if ($env:DATABASE_URL) { $env:DATABASE_URL } elseif ($env:POSTGRES_URL) { $env:POSTGRES_URL } else { $null }
$hasPgEnv = [bool]($env:PGHOST -or $env:PGDATABASE -or $env:PGUSER)
$candidateContainers = @(Get-DockerCandidates -PreferredContainer $Container)

$recommendedRoute = "manual"
if ($psql -and $databaseUrl) {
    $recommendedRoute = "local-psql-database-url"
} elseif ($psql -and $hasPgEnv) {
    $recommendedRoute = "local-psql-pg-env"
} elseif ($psql) {
    $recommendedRoute = "local-psql-manual"
} elseif ($candidateContainers.Count -gt 0) {
    $recommendedRoute = "docker-exec-psql"
} elseif ($node -and $npm) {
    $recommendedRoute = "node-pg-fallback"
}

$result = [pscustomobject]@{
    psql_available = [bool]$psql
    psql_path = if ($psql) { $psql.Source } else { $null }
    docker_available = [bool]$docker
    docker_path = if ($docker) { $docker.Source } else { $null }
    node_available = [bool]$node
    node_path = if ($node) { $node.Source } else { $null }
    npm_available = [bool]$npm
    npm_path = if ($npm) { $npm.Source } else { $null }
    candidate_containers = $candidateContainers
    has_database_url = [bool]$databaseUrl
    database_url_source = if ($env:DATABASE_URL) { "DATABASE_URL" } elseif ($env:POSTGRES_URL) { "POSTGRES_URL" } else { $null }
    has_pg_env = $hasPgEnv
    pg_env = [pscustomobject]@{
        PGHOST = [bool]$env:PGHOST
        PGPORT = [bool]$env:PGPORT
        PGDATABASE = [bool]$env:PGDATABASE
        PGUSER = [bool]$env:PGUSER
        PGPASSWORD = [bool]$env:PGPASSWORD
    }
    recommended_route = $recommendedRoute
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
    exit 0
}

Write-Output "PostgreSQL preflight"
Write-Output "recommended_route: $($result.recommended_route)"
Write-Output "psql_available: $($result.psql_available)"
if ($result.psql_path) {
    Write-Output "psql_path: $($result.psql_path)"
}
Write-Output "docker_available: $($result.docker_available)"
if ($result.docker_path) {
    Write-Output "docker_path: $($result.docker_path)"
}
Write-Output "node_available: $($result.node_available)"
if ($result.node_path) {
    Write-Output "node_path: $($result.node_path)"
}
Write-Output "npm_available: $($result.npm_available)"
if ($result.npm_path) {
    Write-Output "npm_path: $($result.npm_path)"
}
Write-Output "has_database_url: $($result.has_database_url)"
if ($result.database_url_source) {
    Write-Output "database_url_source: $($result.database_url_source)"
}
Write-Output "has_pg_env: $($result.has_pg_env)"
Write-Output "pg_env_present: PGHOST=$($result.pg_env.PGHOST) PGPORT=$($result.pg_env.PGPORT) PGDATABASE=$($result.pg_env.PGDATABASE) PGUSER=$($result.pg_env.PGUSER) PGPASSWORD=$($result.pg_env.PGPASSWORD)"

if ($candidateContainers.Count -gt 0) {
    Write-Output "candidate_containers: $($candidateContainers -join ', ')"
}

switch ($recommendedRoute) {
    "local-psql-database-url" {
        Write-Output "next: use invoke-psql.ps1 with DATABASE_URL or POSTGRES_URL"
    }
    "local-psql-pg-env" {
        Write-Output "next: use invoke-psql.ps1 with the current PG* environment variables"
    }
    "local-psql-manual" {
        Write-Output "next: provide -DbHost/-Database/-User or a -DatabaseUrl to invoke-psql.ps1"
    }
    "docker-exec-psql" {
        Write-Output "next: run invoke-psql.ps1 -Container <name> ..."
    }
    "node-pg-fallback" {
        Write-Output "next: run invoke-psql.ps1 and let it fall back to a temporary Node pg client"
    }
    default {
        Write-Output "next: install psql, provide a PostgreSQL container name that already includes psql, or install Node.js and npm for the fallback route"
    }
}
