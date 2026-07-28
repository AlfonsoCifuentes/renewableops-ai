$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$outputDirectory = Join-Path $projectRoot "artifacts\demo"
$videoPath = Join-Path $outputDirectory "renewableops-guided-demo.webm"
$baseUrl = "http://127.0.0.1:3000"
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

function Invoke-AgentBrowser {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & npx agent-browser @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "agent-browser failed: $($Arguments -join ' ')"
    }
}

function Show-Scene {
    param([string]$Path, [int]$Seconds)
    Invoke-AgentBrowser open "$baseUrl$Path"
    Invoke-AgentBrowser wait ($Seconds * 1000)
}

Invoke-AgentBrowser set viewport 1440 1000
Invoke-AgentBrowser record start $videoPath "$baseUrl/"
try {
    Invoke-AgentBrowser wait 12000
    Show-Scene "/fleet" 8
    Invoke-AgentBrowser scroll down 650
    Invoke-AgentBrowser wait 4000
    Invoke-AgentBrowser scroll up 650
    Show-Scene "/forecast-solar" 14
    Show-Scene "/forecast-wind" 12
    Show-Scene "/asset-health" 14
    Show-Scene "/market" 12
    Show-Scene "/inspections" 14
    Show-Scene "/data-explorer" 12
    Show-Scene "/data-quality" 12
    Show-Scene "/mlops" 15
    Show-Scene "/observability" 14
    Show-Scene "/governance" 14
    Show-Scene "/scenario-lab" 8
    Invoke-AgentBrowser find role button click --name "Ejecutar en sandbox"
    Invoke-AgentBrowser wait 15000
    Show-Scene "/" 15
}
finally {
    Invoke-AgentBrowser record stop
}

Write-Host "Demo recorded: $videoPath"
