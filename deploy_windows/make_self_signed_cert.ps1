<#
إنشاء شهادة HTTPS ذاتية التوقيع لاستخدام داخلي مع daphne أو nginx.
الاستخدام:
  .\deploy_windows\make_self_signed_cert.ps1 -DnsName erp.local -OutDir D:\الشامل\certs
#>
[CmdletBinding()]
param(
  [string]$DnsName='erp.local',
  [string]$OutDir='D:\الشامل\certs',
  [int]$Years=3
)

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$cert = New-SelfSignedCertificate -DnsName $DnsName -CertStoreLocation Cert:\LocalMachine\My -NotAfter (Get-Date).AddYears($Years)
$pwdPlain = [Guid]::NewGuid().ToString('N')
$pwd = ConvertTo-SecureString -String $pwdPlain -Force -AsPlainText
$pfxPath = Join-Path $OutDir "$DnsName.pfx"
$cerPath = Join-Path $OutDir "$DnsName.cer"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwd | Out-Null
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null
Write-Host "PFX: $pfxPath" -ForegroundColor Green
Write-Host "CER: $cerPath (وزعه على الأجهزة لاستيراده في Trusted Root أو Current User)" -ForegroundColor Green
Write-Host "Password: $pwdPlain" -ForegroundColor Yellow

# استخراج مفتاح خاص وشهادة بصيغة PEM (يتطلب openssl مثبت)
if (Get-Command openssl -ErrorAction SilentlyContinue) {
  $pemKey = Join-Path $OutDir "$DnsName.key.pem"
  $pemCrt = Join-Path $OutDir "$DnsName.crt.pem"
  & openssl pkcs12 -in $pfxPath -nocerts -nodes -password pass:$pwdPlain -out $pemKey | Out-Null
  & openssl pkcs12 -in $pfxPath -clcerts -nokeys -password pass:$pwdPlain -out $pemCrt | Out-Null
  Write-Host "PEM Key: $pemKey" -ForegroundColor Green
  Write-Host "PEM Cert: $pemCrt" -ForegroundColor Green
} else {
  Write-Host "openssl غير متوفر - تخطى استخراج PEM" -ForegroundColor Yellow
}
