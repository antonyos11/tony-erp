# Run Django locally on 127.0.0.1:8001 from the app folder
$ErrorActionPreference = 'Stop'
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $AppRoot
$python = Join-Path $AppRoot ".venv/\Scripts/\python.exe"
$manage = Join-Path $AppRoot "manage.py"
& $python $manage check
& $python $manage migrate --noinput
& $python $manage collectstatic --noinput
$port = 8001
Write-Host "Starting server on 127.0.0.1:$port"
& $python $manage runserver "127.0.0.1:$port"
