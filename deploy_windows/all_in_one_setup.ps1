<#
سكربت موحد لتنفيذ جميع خطوات إعداد النظام داخلياً على ويندوز.
يشمل (اختياري):
  - تهيئة البيئة والتثبيت الأولي
  - إعداد PostgreSQL (إن تم طلبه)
  - إنشاء شهادة HTTPS ذاتية (إن طلبت)
  - تسجيل خدمة التطبيق (waitress أو daphne)
  - تسجيل خدمات Celery (worker + beat + Flower)
  - جدولة نسخ احتياطي يومي + نسخ احتياطي مضغوط فوري
  - (اختياري) ترحيل SQLite إلى PostgreSQL

الاستخدام النموذجي (PowerShell كمسؤول أو بصلاحيات مناسبة):
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\deploy_windows\all_in_one_setup.ps1 -ServerIP 192.168.1.50 -UsePostgres -PgPassword StrongPass123! -UseDaphne -CreateCert -RegisterCelery -ScheduleBackup -MigrateIfPostgres

يمكن عرض المساعدة:
  Get-Help .\deploy_windows\all_in_one_setup.ps1 -Detailed
#>
[CmdletBinding()]
param(
  [string]$ServerIP = '192.168.1.50',
  [switch]$UsePostgres,
  [string]$PgDb='tonyerp',
  [string]$PgUser='erp_user',
  [string]$PgPassword='StrongPass123!',
  [switch]$MigrateIfPostgres,
  [switch]$UseDaphne,
  [int]$Port=8000,
  [switch]$CreateCert,
  [string]$CertDns='erp.local',
  [switch]$RegisterCelery,
  [switch]$ScheduleBackup,
  [switch]$FullZipBackup,
  [switch]$SkipInitialSetup,
  [switch]$Force,
  [string]$ServiceName='TonyERP',
  [string]$NssmPath='C:\nssm\nssm.exe'
)

$ErrorActionPreference='Stop'
$root = (Get-Item (Join-Path $PSScriptRoot '..')).FullName
Push-Location $root
Write-Host "جذر المشروع: $root" -ForegroundColor Cyan

function Section($t){ Write-Host "==== $t ====" -ForegroundColor Magenta }

# 1) التهيئة الأساسية
if (-not $SkipInitialSetup) {
  Section 'تهيئة البيئة'
  & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\setup_server.ps1" -ServerIP $ServerIP -UsePostgres:$UsePostgres | Write-Host
} else { Write-Host 'تخطي التهيئة الأولية بناءً على المعامل' -ForegroundColor Yellow }

# تحميل البيئة
if (Test-Path '.venv/Scripts/Activate.ps1') { . .\.venv\Scripts\Activate.ps1 } else { throw 'البيئة الافتراضية غير موجودة' }

# 2) إعداد PostgreSQL إن طُلب
if ($UsePostgres) {
  Section 'إعداد PostgreSQL'
  if ($MigrateIfPostgres) {
    & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\migrate_sqlite_to_postgres.ps1" -DbName $PgDb -DbUser $PgUser -DbPassword $PgPassword | Write-Host
  } else {
    & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\setup_postgres.ps1" -DbName $PgDb -DbUser $PgUser -DbPassword $PgPassword | Write-Host
  }
}

# 3) شهادة HTTPS ذاتية
$certPem=''; $keyPem=''
if ($CreateCert) {
  Section 'إنشاء شهادة HTTPS'
  & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\make_self_signed_cert.ps1" -DnsName $CertDns -OutDir "$root\certs" | Write-Host
  $certPem = Join-Path "$root\certs" "$CertDns.crt.pem"
  $keyPem = Join-Path "$root\certs" "$CertDns.key.pem"
  if (-not (Test-Path $certPem) -or -not (Test-Path $keyPem)) { Write-Host 'ملفات PEM غير متوفرة (قد لا يكون openssl مثبت) سيتم تشغيل الخدمة بدون SSL' -ForegroundColor Yellow }
}

# 4) تسجيل خدمة التطبيق
Section 'تسجيل خدمة التطبيق'
$mode = if ($UseDaphne) { 'daphne' } else { 'waitress' }
$serviceExists = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($serviceExists -and -not $Force) {
  Write-Host "الخدمة $ServiceName موجودة — استخدم -Force لإعادة إنشائها" -ForegroundColor Yellow
} else {
  if ($serviceExists -and $Force) { Write-Host 'إزالة قديم' -ForegroundColor Yellow; sc.exe delete $ServiceName | Out-Null; Start-Sleep 2 }
  $certArg = @()
  if ($mode -eq 'daphne' -and (Test-Path $certPem) -and (Test-Path $keyPem)) { $certArg = @('-CertPath', $certPem, '-KeyPath', $keyPem) }
  & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\register_service_nssm.ps1" -ServiceName $ServiceName -Mode $mode -Port $Port -NssmPath $NssmPath @certArg | Write-Host
}

# 5) تسجيل خدمات Celery
if ($RegisterCelery) {
  Section 'خدمات Celery'
  & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\register_celery_services.ps1" -NssmPath $NssmPath -ServicePrefix $ServiceName | Write-Host
}

# 6) جدولة النسخ الاحتياطي
if ($ScheduleBackup) {
  Section 'جدولة النسخ الاحتياطي اليومي'
  $taskName = 'TonyERP_DailyBackup'
  $exists = schtasks /Query /TN $taskName 2>$null
  if ($LASTEXITCODE -eq 0 -and -not $Force) {
    Write-Host 'مهمة النسخ الاحتياطي موجودة — تخطي (استخدم -Force لإعادة الإنشاء)' -ForegroundColor Yellow
  } else {
    if ($LASTEXITCODE -eq 0 -and $Force) { schtasks /Delete /TN $taskName /F | Out-Null }
    schtasks /Create /TN $taskName /XML "$PSScriptRoot\backup_daily_task.xml" | Out-Null
    Write-Host 'تم إنشاء مهمة النسخ الاحتياطي' -ForegroundColor Green
  }
}

# 7) نسخ احتياطي مضغوط فوري
if ($FullZipBackup) {
  Section 'نسخ احتياطي ZIP فوري'
  if ($UsePostgres) {
    & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\backup_full_zip.ps1" -PgDb $PgDb -PgUser $PgUser -PgPassword $PgPassword | Write-Host
  } else {
    & powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\backup_full_zip.ps1" | Write-Host
  }
}

Section 'انتهى — تحقق من الخدمات:'
Write-Host "  net start | findstr $ServiceName" -ForegroundColor Cyan
if ($RegisterCelery) { Write-Host "  net start | findstr ${ServiceName}_Celery" -ForegroundColor Cyan }
Write-Host "الوصول: http://$ServerIP:$Port/" -ForegroundColor Green
if ($UseDaphne -and (Test-Path $certPem)) { Write-Host "الوصول الآمن (قد تحتاج تثبيت الشهادة): https://$CertDns:$Port/" -ForegroundColor Green }

Pop-Location
