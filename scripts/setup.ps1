$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$apiRoot = Join-Path $workspaceRoot "services\api"
$webRoot = Join-Path $workspaceRoot "apps\web"
$apiPython = Join-Path $apiRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $apiPython)) {
    python -m venv (Join-Path $apiRoot ".venv")
}

& $apiPython -m pip install --upgrade pip
& $apiPython -m pip install -e "$apiRoot[dev]"

Push-Location $webRoot
try {
    npm install
}
finally {
    Pop-Location
}

Write-Host "Dependencies installed. Run scripts\quality.ps1 to verify the repository."
