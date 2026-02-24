<#
تسجيل خدمة Windows عبر NSSM لتشغيل Tony ERP.
الاستخدام:
  .\deploy_windows\register_service_nssm.ps1 -ServiceName TonyERP -NssmPath C:\nssm\nssm.exe -Mode waitress
Mode:
  runserver  => يستخدم manage.py runserver (للتجربة)
  waitress   => يستخدم start_waitress.bat (موصى به داخلياً)
#>
[CmdletBinding()]
param(
  [string]$ServiceName='TonyERP',
  [string]$NssmPath='C:\nssm\\nssm.exe',
  [ValidateSet('runserver','waitress','daphne')] [string]$Mode='waitress',
  [int]$Port=8000,
  [string]$CertPath='',
  [string]$KeyPath=''
)

if (-not (Test-Path $NssmPath)) { throw "لم يتم العثور على NSSM في: $NssmPath" }

switch ($Mode) {
  'runserver' {
    $app = "${PWD}\.venv\Scripts\python.exe"
    $args = "${PWD}\manage.py runserver 0.0.0.0:$Port"
  }
  'waitress' {
    $app = "${PWD}\start_waitress.bat"
    $args = ''
  }
  'daphne' {
    $daphneExe = "${PWD}\.venv\Scripts\daphne.exe"
    if (-not (Test-Path $daphneExe)) { $daphneExe = "${PWD}\.venv\Scripts\python.exe"; $args = "-m daphne -b 0.0.0.0 -p $Port" }
    else { $app = $daphneExe; $args = "-b 0.0.0.0 -p $Port" }
    if ($CertPath -and $KeyPath) { $args += " --ssl-certfile `"$CertPath`" --ssl-keyfile `"$KeyPath`"" }
    if (-not $app) { $app = $daphneExe }
    $args += ' accountant_pro.asgi:application'
  }
}

Write-Host "تثبيت الخدمة $ServiceName" -ForegroundColor Cyan
& $NssmPath install $ServiceName $app $args | Out-Null
& $NssmPath set $ServiceName Start SERVICE_AUTO_START | Out-Null
& $NssmPath set $ServiceName AppDirectory "${PWD}" | Out-Null
& $NssmPath set $ServiceName AppStdout "${PWD}\logs\$ServiceName.out.log" | Out-Null
& $NssmPath set $ServiceName AppStderr "${PWD}\logs\$ServiceName.err.log" | Out-Null

if (-not (Test-Path .\logs)) { New-Item -ItemType Directory -Path .\logs | Out-Null }

Write-Host "تشغيل الخدمة" -ForegroundColor Cyan
Start-Service $ServiceName

Write-Host "تم التسجيل والتشغيل" -ForegroundColor Green
