<#
  Moves everything into .\app except this script and the launcher, keeping top level clean.
  Usage: powershell -ExecutionPolicy Bypass -File .\repack_to_app.ps1
#>

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSCommandPath
Set-Location $Root

$App = Join-Path $Root 'app'
if (!(Test-Path $App)) { New-Item -ItemType Directory -Path $App | Out-Null }

$keep = @('تشغيل النظام.bat','repack_to_app.ps1','README_تشغيل.txt')

Get-ChildItem -Force -LiteralPath $Root | ForEach-Object {
  if ($_.Name -in $keep) { return }
  if ($_.Name -eq 'app') { return }
  Move-Item -LiteralPath $_.FullName -Destination $App -Force -ErrorAction SilentlyContinue
}

# Done
Write-Host '[OK] Moved files into app/. Keep only launcher at root.'
