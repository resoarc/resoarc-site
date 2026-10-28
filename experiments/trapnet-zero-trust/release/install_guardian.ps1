# User-home Guardian TEST deployment, not a signed public release.
[CmdletBinding()]
param(
 [Parameter(Mandatory)][ValidateSet('Install','Remove')][string]$Action,
 [Parameter(Mandatory)][string]$Prefix,
 [string]$Binary,
 [string]$Sha256
)
$ErrorActionPreference='Stop'
$homeFull=[IO.Path]::GetFullPath($HOME).TrimEnd('\','/')
$dest=[IO.Path]::GetFullPath($Prefix).TrimEnd('\','/')
if(-not $dest.StartsWith($homeFull+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
 throw 'Refused: destination must be beneath current user home'
}
$relative=$dest.Substring($homeFull.Length).TrimStart('\','/')
$current=$homeFull
foreach($part in ($relative -split '[\\/]')){
 if(!$part){continue};$current=Join-Path $current $part
 if(Test-Path -LiteralPath $current){
  $item=Get-Item -LiteralPath $current -Force
  if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Refused: reparse point in install path'}
 }
}
$installed=Join-Path $dest 'guardian.exe'
$receipt=Join-Path $dest 'guardian.install.sha256'
if($Action -eq 'Install'){
 if(-not $Binary -or $Sha256 -notmatch '^[0-9a-fA-F]{64}$'){throw 'Binary and verified SHA-256 required'}
 $source=Get-Item -LiteralPath $Binary -ErrorAction Stop
 if($source.PSIsContainer -or ($source.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Source must be normal file'}
 $expected=$Sha256.ToLowerInvariant()
 if((Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Source digest mismatch'}
 if((Test-Path -LiteralPath $installed) -or (Test-Path -LiteralPath $receipt)){throw 'Refused: install exists'}
 New-Item -ItemType Directory -Path $dest -Force | Out-Null
 $tmp=Join-Path $dest ('.guardian-'+[guid]::NewGuid().ToString('N')+'.tmp')
 try{
  [IO.File]::Copy($source.FullName,$tmp,$false)
  if((Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Copy digest mismatch'}
  [IO.File]::Move($tmp,$installed)
  $bytes=[Text.Encoding]::ASCII.GetBytes($expected+[Environment]::NewLine)
  $stream=[IO.File]::Open($receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
  Write-Output 'Guardian test installation complete (SHA-256 is NOT authenticity)'
 }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
}else{
 if(!(Test-Path -LiteralPath $installed) -or !(Test-Path -LiteralPath $receipt)){throw 'Incomplete install; manual review'}
 foreach($file in @($installed,$receipt)){
  $item=Get-Item -LiteralPath $file -Force
  if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Refused: modified install'}
 }
 $stored=(Get-Content -LiteralPath $receipt -Raw).Trim()
 if($stored -notmatch '^[0-9a-f]{64}$' -or (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash.ToLowerInvariant() -ne $stored){
  throw 'Installed binary modified; manual review required'
 }
 Remove-Item -LiteralPath $installed,$receipt -Force
 Write-Output 'Guardian binary removed. Trust/anti-rollback state retained.'
}
