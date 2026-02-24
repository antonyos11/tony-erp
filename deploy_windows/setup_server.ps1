<#
تهيئة أولية لسيرفر Tony ERP على ويندوز (تشغيل داخلي)
الاستخدام (PowerShell كمسؤول أو مستخدم بصلاحيات كتابة):
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\deploy_windows\setup_server.ps1 -ServerIP 192.168.1.50 -UsePostgres:$false
#>
[CmdletBinding()]
param(
    [string]$PythonPath = "python",
    [string]$ServerIP = "192.168.1.50",
    [switch]$UsePostgres,
    [string]$DbName = "tonyerp",
    [string]$DbUser = "erp_user",
    [string]$DbPassword = "StrongPass123!",
    [int]$Port = 8000
)

Write-Host "=== (1) إنشاء بيئة افتراضية ===" -ForegroundColor Cyan
if (-not (Test-Path .venv)) { & $PythonPath -m venv .venv } else { Write-Host "موجودة" }

Write-Host "تحديث pip والحزم" -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip > $null
pip install -r requirements.txt > $null
pip install waitress > $null
if ($UsePostgres) { pip install psycopg[binary] > $null }

Write-Host "=== (2) إنشاء ملف .env إن لم يوجد ===" -ForegroundColor Cyan
$envFile = ".env"
if (-not (Test-Path $envFile)) {
    $secret = (& $PythonPath - <<'PY'
import secrets, string
alphabet = string.ascii_letters+string.digits+string.punctuation.replace('"','').replace("'",'')
print(''.join(secrets.choice(alphabet) for _ in range(64)))
PY
    ).Trim()
    $content = @()
    $content += "DJANGO_SETTINGS_MODULE=accountant_pro.settings"
    $content += "DEBUG=False"
    $content += "SECRET_KEY=$secret"
    $content += "ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0,$ServerIP,erp.local"
    $content += "TIME_ZONE=Africa/Cairo"
    if ($UsePostgres) { $content += "DATABASE_URL=postgres://$DbUser:$DbPassword@127.0.0.1:5432/$DbName" }
    Set-Content -Path $envFile -Value ($content -join "`n") -Encoding UTF8
    Write-Host "تم إنشاء .env" -ForegroundColor Green
} else { Write-Host ".env موجود - لن يتم استبداله" -ForegroundColor Yellow }

Write-Host "=== (3) تنفيذ المايجريشن والملفات الثابتة ===" -ForegroundColor Cyan
python manage.py migrate
python manage.py collectstatic --noinput

Write-Host "=== (4) إنشاء مستخدم إداري (لو لم يوجد) ===" -ForegroundColor Cyan
$createsuper = @"
from django.contrib.auth import get_user_model
U=get_user_model()
if not U.objects.filter(username='superadmin').exists():
    U.objects.create_superuser('superadmin','admin@example.com','Admin123!')
    print('تم إنشاء superadmin / Admin123! (غيّرها فوراً)')
else:
    print('superadmin موجود بالفعل')
"@
python manage.py shell -c "$createsuper"

Write-Host "=== (5) إنشاء سكربت التشغيل waitress إذا لم يوجد ===" -ForegroundColor Cyan
$bat = "start_waitress.bat"
if (-not (Test-Path $bat)) {
@"
@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
waitress-serve --listen=0.0.0.0:$Port accountant_pro.wsgi:application
"@ | Set-Content $bat -Encoding ASCII
}

Write-Host "=== (6) فتح المنفذ في الجدار (إن لم توجد قاعدة) ===" -ForegroundColor Cyan
$ruleName = "TonyERP $Port"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "تم فتح المنفذ $Port" -ForegroundColor Green
} else { Write-Host "القاعدة موجودة" }

Write-Host "=== تم — شغل النظام بـ  start_waitress.bat  أو أنشئ خدمة NSSM ===" -ForegroundColor Green
