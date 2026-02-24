<#
ترحيل البيانات من SQLite إلى PostgreSQL باستخدام dumpdata/loaddata.
الافتراض: لديك .env حالياً يستخدم SQLite، وسيتم إنشاء DATABASE_URL مؤقتاً لمرحلة PostgreSQL.
الاستخدام:
  .\deploy_windows\migrate_sqlite_to_postgres.ps1 -DbName tonyerp -DbUser erp_user -DbPassword StrongPass123!
#>
[CmdletBinding()]
param(
  [string]$DbName='tonyerp',
  [string]$DbUser='erp_user',
  [string]$DbPassword='StrongPass123!',
  [string]$Host='127.0.0.1',
  [int]$Port=5432,
  [string]$BackupDir='D:\الشامل\migration_backups'
)

$ErrorActionPreference='Stop'

if (-not (Test-Path .venv)) { throw "يجب تشغيل setup_server.ps1 أولاً" }
. .\.venv\Scripts\Activate.ps1

if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

Write-Host "(1) نسخة احتياطية من SQLite" -ForegroundColor Cyan
if (Test-Path db.sqlite3) { Copy-Item db.sqlite3 (Join-Path $BackupDir "db_$timestamp.sqlite3") }

Write-Host "(2) تفريغ البيانات JSON" -ForegroundColor Cyan
python manage.py dumpdata --natural-foreign --natural-primary --exclude auth.permission --exclude contenttypes --indent 2 > (Join-Path $BackupDir "data_$timestamp.json")

Write-Host "(3) إنشاء مستخدم وقاعدة PostgreSQL (يتجاهل الأخطاء لو موجودة)" -ForegroundColor Cyan
$env:PGPASSWORD=''
psql -U postgres -h $Host -p $Port -c "CREATE USER $DbUser WITH PASSWORD '$DbPassword';" 2>$null | Out-Null
psql -U postgres -h $Host -p $Port -c "CREATE DATABASE $DbName OWNER $DbUser;" 2>$null | Out-Null

Write-Host "(4) تحديث .env بـ DATABASE_URL الجديدة (مع الاحتفاظ بالقديمة كتعليق)" -ForegroundColor Cyan
$envFile = Get-Content .env
if (-not ($envFile -match '^DATABASE_URL=')) {
  Add-Content .env "DATABASE_URL=postgres://$DbUser:$DbPassword@$Host:$Port/$DbName"
} else {
  $envFile = $envFile -replace '^DATABASE_URL=.*',"DATABASE_URL=postgres://$DbUser:$DbPassword@$Host:$Port/$DbName"
  Set-Content .env $envFile -Encoding UTF8
}

Write-Host "(5) تشغيل المايجريشن على PostgreSQL" -ForegroundColor Cyan
python manage.py migrate --noinput

Write-Host "(6) تحميل البيانات" -ForegroundColor Cyan
python manage.py loaddata (Join-Path $BackupDir "data_$timestamp.json")

Write-Host "تمت الترقية — اختبر الآن. إن فشل أي شيء يمكنك الرجوع لملف SQLite الاحتياطي." -ForegroundColor Green
