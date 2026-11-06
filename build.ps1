$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python -m PyInstaller --noconfirm --clean --onefile --noconsole --name UsageDesk --icon assets\app.ico --add-data 'web;web' --add-data 'prices.json;.' --add-data 'THIRD_PARTY_NOTICES.md;.' --add-data 'licenses;licenses' app.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
    Write-Host "EXE: $PSScriptRoot\dist\UsageDesk.exe"
} finally { Pop-Location }
