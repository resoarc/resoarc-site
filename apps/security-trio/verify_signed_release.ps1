# Read-only, fail-closed public release signature gate.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Dist,
 [Parameter(Mandatory=$true)][string]$ExpectedPublisher,
 [Parameter(Mandatory=$true)][string]$ExpectedCertificateThumbprint,
 [string]$ManifestPath = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$names=@('ResoArcSecretScout.exe','ResoArcLogLantern.exe','ResoArcFileInspector.exe')
$expectedThumb=($ExpectedCertificateThumbprint -replace '[^0-9A-Fa-f]','').ToUpperInvariant()
if($expectedThumb.Length -ne 40){throw 'BLOCK: actual approved signer certificate fingerprint required (40 hex).'}
if($ExpectedPublisher.Trim().Length -lt 5){throw 'BLOCK: publisher required.'}
if(!(Test-Path -LiteralPath $Dist -PathType Container)){throw 'BLOCK: missing dist.'}
$actual=@(Get-ChildItem -LiteralPath $Dist -Filter '*.exe' -File | ForEach-Object Name | Sort-Object)
if(($actual -join '|') -ne (@($names | Sort-Object) -join '|')){throw 'BLOCK: unexpected or missing EXE.'}
$manifest=@()
foreach($name in $names){
 $file=Join-Path $Dist $name
 $sig=Get-AuthenticodeSignature -LiteralPath $file
 if($sig.Status -ne 'Valid' -or $null -eq $sig.SignerCertificate){throw "BLOCK: $name signature: $($sig.Status)"}
 $cert=$sig.SignerCertificate
 if($cert.Subject -notlike ('*'+$ExpectedPublisher+'*')){throw "BLOCK: wrong publisher: $name"}
 if($cert.Thumbprint.ToUpperInvariant() -ne $expectedThumb){throw "BLOCK: unknown signer certificate: $name"}
 $eku=@($cert.EnhancedKeyUsageList | ForEach-Object {$_.ObjectId.Value})
 if($eku -notcontains '1.3.6.1.5.5.7.3.3'){throw "BLOCK: code signing EKU missing: $name"}
 if($null -eq $sig.TimeStamperCertificate){throw "BLOCK: no timestamp: $name"}
 $hash=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
 $manifest+=("$hash  $name")
 Write-Output "PASS: $name $hash"
}
if($ManifestPath){
 if(Test-Path -LiteralPath $ManifestPath){throw 'BLOCK: refusing to overwrite existing manifest.'}
 [System.IO.File]::WriteAllLines($ManifestPath,$manifest,[System.Text.UTF8Encoding]::new($false))
}
Write-Output 'PASS: approved trusted signer, 3 EXEs, timestamp and hashes.'
