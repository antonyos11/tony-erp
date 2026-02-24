# Start Django server in background and log output
$ErrorActionPreference = 'SilentlyContinue'
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $AppRoot
$python = Join-Path $AppRoot ".venv/\Scripts/\python.exe"
$manage = Join-Path $AppRoot "manage.py"
$newPort = 8002
$logDir = Join-Path $AppRoot "logs"
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$outLog = Join-Path $logDir ("runserver_${newPort}.log")
$errLog = Join-Path $logDir ("runserver_${newPort}.err")
Start-Process -FilePath $python -ArgumentList @($manage,'runserver',"127.0.0.1:${newPort}",'--noreload') -WorkingDirectory $AppRoot -RedirectStandardOutput $outLog -RedirectStandardError $errLog -WindowStyle Hidden
Write-Host "Started runserver on 127.0.0.1:${newPort}. Logs: $outLog | $errLog"
