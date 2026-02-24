<#
نسخ احتياطي يومي بسيط (SQLite + media) مع تدوير آخر 7 أيام.
أضفه إلى Task Scheduler يومياً.
#>
[CmdletBinding()]
param(
  [string]$BackupRoot = 'D:\الشامل\backups',
  [int]$KeepDays = 7
)

$stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$dest = Join-Path $BackupRoot $stamp
New-Item -ItemType Directory -Path $dest -Force | Out-Null

# قاعدة البيانات (SQLite)
if (Test-Path 'D:\الشامل\db.sqlite3') {
  Copy-Item 'D:\الشامل\db.sqlite3' (Join-Path $dest 'db.sqlite3')
}

# مجلد media
if (Test-Path 'D:\الشامل\media') {
  robocopy 'D:\الشامل\media' (Join-Path $dest 'media') /E /NFL /NDL /NJH /NJS /NP | Out-Null
}

Write-Host "تم النسخ الاحتياطي إلى $dest" -ForegroundColor Green

# تدوير
Get-ChildItem $BackupRoot -Directory | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } | ForEach-Object {
  Write-Host "حذف قديم: $($_.FullName)" -ForegroundColor Yellow
  Remove-Item $_.FullName -Recurse -Force
}
