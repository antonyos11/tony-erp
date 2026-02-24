<#
تهيئة PostgreSQL محلي (يلزم وجود psql في PATH). ينشئ مستخدم وقاعدة ويحدث .env.
الاستخدام:
  .\deploy_windows\setup_postgres.ps1 -DbName tonyerp -DbUser erp_user -DbPassword StrongPass123!
#>
[CmdletBinding()]
param(
  [string]$DbName='tonyerp',
  [string]$DbUser='erp_user',
  [string]$DbPassword='StrongPass123!',
  [string]$Host='127.0.0.1',
  [int]$Port=5432
)

function Exec-Sql($sql){
  $env:PGPASSWORD = ''
  psql -U postgres -h $Host -p $Port -c $sql 2>$null | Out-Null
}

Write-Host "إنشاء المستخدم (يتجاهل الخطأ لو موجود)" -ForegroundColor Cyan
Exec-Sql "CREATE USER $DbUser WITH PASSWORD '$DbPassword';"

Write-Host "إنشاء قاعدة البيانات (يتجاهل الخطأ لو موجودة)" -ForegroundColor Cyan
Exec-Sql "CREATE DATABASE $DbName OWNER $DbUser;"

Write-Host "تعديل .env لإضافة DATABASE_URL" -ForegroundColor Cyan
if (Test-Path .env) {
  $lines = Get-Content .env
  if (-not ($lines -match '^DATABASE_URL=')) {
    Add-Content .env "DATABASE_URL=postgres://$DbUser:$DbPassword@$Host:$Port/$DbName"
  } else {
    $lines = $lines -replace '^DATABASE_URL=.*',"DATABASE_URL=postgres://$DbUser:$DbPassword@$Host:$Port/$DbName"
    Set-Content .env $lines -Encoding UTF8
  }
  Write-Host "تم تحديث .env" -ForegroundColor Green
} else { Write-Host "ملف .env غير موجود — شغّل setup_server.ps1 أولاً" -ForegroundColor Yellow }

Write-Host "تشغيل مهاجرات Django" -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1
python manage.py migrate
