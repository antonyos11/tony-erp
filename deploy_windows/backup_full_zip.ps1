<#
نسخ احتياطي كامل (SQLite أو PostgreSQL + media + ملفات env) في ملف ZIP مع تدوير.
الاستخدام:
  .\deploy_windows\backup_full_zip.ps1 -Keep 10
#>
[CmdletBinding()]
param(
  [string]$OutDir='D:\الشامل\backups_zip',
  [int]$Keep=10,
  [string]$PgDb='',
  [string]$PgUser='',
  [string]$PgHost='127.0.0.1',
  [int]$PgPort=5432,
  [string]$PgPassword=''  # يمكن تمريره وقت التنفيذ
)

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$temp = Join-Path $OutDir "tmp_$stamp"
New-Item -ItemType Directory -Path $temp | Out-Null

# db
if (Test-Path 'D:\الشامل\db.sqlite3') {
  Copy-Item 'D:\الشامل\db.sqlite3' (Join-Path $temp 'db.sqlite3')
} elseif ($PgDb) {
  if ($PgPassword) { $env:PGPASSWORD=$PgPassword }
  pg_dump -h $PgHost -p $PgPort -U $PgUser -F c -d $PgDb -f (Join-Path $temp 'db.dump') 2>$null
}

# media
if (Test-Path 'D:\الشامل\media') {
  robocopy 'D:\الشامل\media' (Join-Path $temp 'media') /E /NFL /NDL /NJH /NJS /NP | Out-Null
}

# env/config
foreach ($f in @('.env','.env.example','requirements.txt')) { if (Test-Path $f) { Copy-Item $f (Join-Path $temp $f.TrimStart('.')) } }

$zipPath = Join-Path $OutDir "backup_$stamp.zip"
Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $zipPath -Force
Remove-Item $temp -Recurse -Force
Write-Host "تم إنشاء: $zipPath" -ForegroundColor Green

# تدوير
Get-ChildItem $OutDir -Filter 'backup_*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | ForEach-Object { Remove-Item $_.FullName -Force }
