$ErrorActionPreference='Stop'
$script=Join-Path $PSScriptRoot 'install_guardian.ps1'
$root=Join-Path $HOME ('Documents\TrapNetGuardianInstallTrial-'+[guid]::NewGuid().ToString('N'))
$install=Join-Path $root 'per-user'
New-Item -Path $root -ItemType Directory -Force|Out-Null
try{
 $source=Join-Path $root 'synthetic-guardian.exe'
 [IO.File]::WriteAllBytes($source,[Text.Encoding]::UTF8.GetBytes('Synthetic test artifact, not a real release'))
 $digest=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 & $script -Action Install -Prefix $install -Binary $source -Sha256 $digest |Out-Null
 if(!(Test-Path (Join-Path $install 'guardian.exe'))){throw 'Installer did not create binary'}
 $overwritten=$false
 try{& $script -Action Install -Prefix $install -Binary $source -Sha256 $digest|Out-Null}catch{$overwritten=$true}
 if(!$overwritten){throw 'Installer overwrote existing executable'}
 [IO.File]::WriteAllText((Join-Path $install 'guardian-state.json'),'antirollback-state-do-not-delete')
 [IO.File]::AppendAllText((Join-Path $install 'guardian.exe'),'TAMPER')
 $tamperRejected=$false
 try{& $script -Action Remove -Prefix $install|Out-Null}catch{$tamperRejected=$true}
 if(!$tamperRejected){throw 'Installer deleted modified executable'}
 Remove-Item -LiteralPath (Join-Path $install 'guardian.exe'),(Join-Path $install 'guardian.install.sha256') -Force
 & $script -Action Install -Prefix $install -Binary $source -Sha256 $digest |Out-Null
 & $script -Action Remove -Prefix $install |Out-Null
 if(Test-Path (Join-Path $install 'guardian.exe')){throw 'Uninstall left executable'}
 if(!(Test-Path (Join-Path $install 'guardian-state.json'))){throw 'Uninstall deleted rollback state'}
 $outsideRejected=$false
 try{& $script -Action Install -Prefix ([IO.Path]::GetTempPath()) -Binary $source -Sha256 $digest|Out-Null}catch{$outsideRejected=$true}
 if(!$outsideRejected){throw 'Installer permitted path outside HOME'}
 $mismatchRejected=$false
 try{& $script -Action Install -Prefix (Join-Path $root 'incorrect') -Binary $source -Sha256 ('a'*64)|Out-Null}catch{$mismatchRejected=$true}
 if(!$mismatchRejected){throw 'Installer permitted wrong SHA-256'}
 Write-Output 'Windows native user-home install, overwrite, tamper, removal, rollback preservation: PASS'
}finally{
 if(Test-Path -LiteralPath $root){Remove-Item -LiteralPath $root -Recurse -Force}
}
