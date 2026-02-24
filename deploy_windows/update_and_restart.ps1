<#
تحديث الحزم (اختياري)، تطبيق migrations، جمع static، وإعادة تشغيل خدمة NSSM إن وجدت.
الاستخدام:
    .\deploy_windows\update_and_restart.ps1 -ServiceName TonyERP [-Upgrade]
#>
[CmdletBinding()]
param(
  [string]$ServiceName = 'TonyERP',
  [switch]$Upgrade
)

Write-Host "تنشيط البيئة" -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1

if ($Upgrade) {
  Write-Host "ترقية pip والحزم" -ForegroundColor Cyan
  pip install --upgrade pip
  pip install -r requirements.txt --upgrade
}

Write-Host "تطبيق migrations" -ForegroundColor Cyan
python manage.py migrate --noinput

Write-Host "جمع static" -ForegroundColor Cyan
python manage.py collectstatic --noinput

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
  Write-Host "إعادة تشغيل الخدمة $ServiceName" -ForegroundColor Cyan
  Stop-Service $ServiceName -Force
  Start-Sleep -Seconds 2
  Start-Service $ServiceName
  Write-Host "تمت إعادة التشغيل" -ForegroundColor Green
} else {
  Write-Host "الخدمة غير موجودة — شغل start_waitress.bat يدوياً" -ForegroundColor Yellow
}
