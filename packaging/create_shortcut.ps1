param(
  [Parameter(Mandatory=$true)][string]$TargetPath,
  [Parameter(Mandatory=$true)][string]$ShortcutName,
  [string]$IconPath = "$env:SystemRoot\System32\shell32.dll",
  [int]$IconIndex = 0
)
$WScriptShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop ($ShortcutName + '.lnk')
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = Split-Path $TargetPath
$Shortcut.IconLocation = "$IconPath,$IconIndex"
$Shortcut.Save()
