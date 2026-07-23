[CmdletBinding()]
param(
    [ValidateSet("catalog", "inventory", "backlog")]
    [string]$Scenario = "catalog",
    [string]$ApiUrl = "http://localhost:8081"
)

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $projectRoot ".env"

if (-not $env:AEGIS_ORCHESTRATOR_TOKEN -and (Test-Path $envFile)) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*AEGIS_ORCHESTRATOR_TOKEN=(.+)$') {
            $env:AEGIS_ORCHESTRATOR_TOKEN = $Matches[1].Trim()
        }
    }
}

if (-not $env:AEGIS_ORCHESTRATOR_TOKEN) {
    throw "AEGIS_ORCHESTRATOR_TOKEN is missing. Set it in .env or the current PowerShell session."
}

$scenarioConfig = @{
    catalog = @{ category = "catalog_search"; target = @{ type = "mongodb_collection"; database = "mydatabase"; collection = "products"; field = "search_text" } }
    inventory = @{ category = "inventory_dependency"; target = @{ type = "inventory_dependency"; service = "inventory" } }
    backlog = @{ category = "order_backlog"; target = @{ type = "order_worker"; service = "worker" } }
}[$Scenario]

$body = @{
    source = "manual-demo"
    fingerprint = "manual-$Scenario-$([guid]::NewGuid())"
    category = $scenarioConfig.category
    target = $scenarioConfig.target
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiUrl/api/v1/orchestration/alerts" `
    -Headers @{ Authorization = "Bearer $env:AEGIS_ORCHESTRATOR_TOKEN" } `
    -ContentType "application/json" `
    -Body $body

Write-Host "Created $Scenario incident: $($response.incident_id)"
Write-Host "Open: http://localhost:3000/ops/incidents/$($response.incident_id)"
