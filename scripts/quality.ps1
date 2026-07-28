$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$apiRoot = Join-Path $workspaceRoot "services\api"
$webRoot = Join-Path $workspaceRoot "apps\web"
$apiPython = Join-Path $apiRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $apiPython)) {
    throw "Chưa có API virtual environment. Chạy scripts\setup.ps1 trước."
}

Push-Location $apiRoot
try {
    & $apiPython -m pytest
}
finally {
    Pop-Location
}

Push-Location $webRoot
try {
    npm run lint
    npm run format:check
    npm run typecheck
    npm test
    npm run build
}
finally {
    Pop-Location
}
