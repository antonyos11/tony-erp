<#
تسجيل خدمات Celery (worker + beat + Flower) باستخدام NSSM.
الاستخدام:
  .\deploy_windows\register_celery_services.ps1 -NssmPath C:\nssm\nssm.exe -ProjectDir D:\الشامل -ServicePrefix TonyERP
#>
[CmdletBinding()]
param(
  [string]$NssmPath='C:\nssm\nssm.exe',
  [string]$ProjectDir=$(Get-Location).Path,
  [string]$ServicePrefix='TonyERP',
  [string]$AppModule='accountant_pro',
  [string]$LogDir='logs'
)

if (-not (Test-Path $NssmPath)) { throw "لم يتم العثور على NSSM" }
Push-Location $ProjectDir
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$python = Join-Path $ProjectDir '.venv\Scripts\python.exe'

$services = @(
  @{Name="${ServicePrefix}_CeleryWorker"; Args="-m celery -A $AppModule worker -l info"},
  @{Name="${ServicePrefix}_CeleryBeat"; Args="-m celery -A $AppModule beat -l info"},
  @{Name="${ServicePrefix}_Flower"; Args="-m flower -A $AppModule --port=5555"}
)

foreach ($svc in $services) {
  Write-Host "تسجيل الخدمة $($svc.Name)" -ForegroundColor Cyan
  & $NssmPath install $svc.Name $python $svc.Args | Out-Null
  & $NssmPath set $svc.Name AppDirectory $ProjectDir | Out-Null
  & $NssmPath set $svc.Name AppStdout "$ProjectDir\$LogDir\$($svc.Name).out.log" | Out-Null
  & $NssmPath set $svc.Name AppStderr "$ProjectDir\$LogDir\$($svc.Name).err.log" | Out-Null
  & $NssmPath set $svc.Name Start SERVICE_AUTO_START | Out-Null
  Start-Service $svc.Name
}

Pop-Location
Write-Host "تم تسجيل وتشغيل خدمات Celery و Flower" -ForegroundColor Green
