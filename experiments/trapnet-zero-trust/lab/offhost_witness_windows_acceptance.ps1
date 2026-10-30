# Disposable cross-machine Witness acceptance; DO NOT point at real logs.
# Run on the Witness-owned Windows PC after receiving ONLY synthetic handoff.
param(
 [Parameter(Mandatory=$true)][string]$Handoff,
 [Parameter(Mandatory=$true)][string]$Output,
 [Parameter(Mandatory=$true)][string]$KeygenExe,
 [Parameter(Mandatory=$true)][string]$WitnessExe,
 [Parameter(Mandatory=$true)][string]$ReceiptAuditExe,
 [Parameter(Mandatory=$true)][string]$SourceCommit
)
$ErrorActionPreference='Continue'
if(Test-Path -LiteralPath $Output){throw 'Output directory must not exist'}
if(!(Test-Path -LiteralPath $Handoff -PathType Container)){throw 'Handoff missing'}
if($SourceCommit -notmatch '^[0-9a-f]{40}$'){throw 'Pinned SHA missing'}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $Handoff 'handoff-manifest.json') | ConvertFrom-Json
if($manifest.source_commit -ne $SourceCommit -or $manifest.accepted_reports -ne 2 -or !$manifest.all_data_synthetic -or $manifest.handoff_contains_private_key){throw 'Unsafe handoff manifest'}
foreach($entry in $manifest.sha256.PSObject.Properties){
 $name=[string]$entry.Name
 if($name -notmatch '^[A-Za-z0-9._/-]+$' -or $name.Contains('..')){throw 'Unsafe manifest relative path'}
 $p=Join-Path $Handoff $name.Replace('/','\')
 if(!(Test-Path $p -PathType Leaf)){throw 'Missing evidence file'}
 $digest=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
 if($digest -ne $entry.Value){throw 'Handoff evidence digest mismatch'}
}
New-Item -ItemType Directory -Path $Output | Out-Null
$signer=Join-Path $Output 'ephemeral-local-signer'
$historyDir=Join-Path $Output 'witness-only'
New-Item -ItemType Directory -Path $historyDir | Out-Null
$hist=Join-Path $historyDir 'history.jsonl'
$private=Join-Path $signer 'private.hex'
$pub=Join-Path $signer 'public.hex'
$validated=$false
try {
 & $KeygenExe -out $signer >$null
 if($LASTEXITCODE -ne 0 -or !(Test-Path $private)){throw 'Witness local keygen failed'}
 $one=(& $WitnessExe -mode attest -ledger (Join-Path $Handoff 'snapshot-1\ledger.jsonl') -history $hist -key $private -bootstrap-history 2>&1) -join ' '
 if($LASTEXITCODE -ne 0 -or $one -notmatch 'tip=([0-9a-f]{64})'){throw 'First checkpoint failed'}
 $tip1=$Matches[1]
 Start-Sleep -Milliseconds 1100
 $two=(& $WitnessExe -mode attest -ledger (Join-Path $Handoff 'snapshot-2\ledger.jsonl') -history $hist -key $private -expected-tip $tip1 2>&1) -join ' '
 if($LASTEXITCODE -ne 0 -or $two -notmatch 'tip=([0-9a-f]{64})'){throw 'Second independent-history checkpoint failed'}
 $tip2=$Matches[1]
 $trust=@('-history',$hist,'-witness-tip',$tip2,'-witness-pub',$pub,
          '-hub-pub',(Join-Path $Handoff 'hub-public.hex'),
          '-sensor-pub',(Join-Path $Handoff 'sensor-public.hex'))
 foreach($n in 1,2){
  $args2=@('-ledger',(Join-Path $Handoff 'snapshot-2\ledger.jsonl'))+$trust+
         @('-report',(Join-Path $Handoff ('signed-report-'+$n+'.json')),
           '-receipt',(Join-Path $Handoff ('signed-hub-receipt-'+$n+'.json')))
  & $ReceiptAuditExe @args2 >$null 2>$null
  if($LASTEXITCODE -ne 0){throw 'Witness could not verify original receipt'}
 }
 $old=@('-ledger',(Join-Path $Handoff 'snapshot-1\ledger.jsonl'))+$trust+
      @('-report',(Join-Path $Handoff 'signed-report-1.json'),
        '-receipt',(Join-Path $Handoff 'signed-hub-receipt-1.json'))
 & $ReceiptAuditExe @old >$null 2>$null
 if($LASTEXITCODE -eq 0){throw 'Rollback was incorrectly accepted'}
 $export=Join-Path $Output 'export-only-public'
 New-Item -ItemType Directory -Path $export | Out-Null
 Copy-Item $hist (Join-Path $export 'history.jsonl')
 Copy-Item $pub (Join-Path $export 'witness-public.hex')
 # ASCII Windows CRLF is intentional: Linux verifier must normalize line endings.
 Set-Content -Encoding ascii (Join-Path $export 'pinned-tip-2.txt') $tip2
 $report=[ordered]@{
  schema='trapnet.cross-host-witness-windows.v051'
  passed=$true
  synthetic_only=$true
  source_commit=$SourceCommit
  signed_history_entries=2
  latest_snapshot_audits_both_reports=$true
  old_snapshot_rejected=$true
  private_key_exported=$false
  public_release_approved=$false
 }
 $report | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 (Join-Path $Output 'windows-acceptance.json')
 $validated=$true
 Write-Output ('WINDOWS_WITNESS_2_CHECKPOINTS_PASS: tip='+$tip2)
}
finally{
 # Ephemeral test private signing key is not retained after attestation.
 if(Test-Path -LiteralPath $signer){Remove-Item -LiteralPath $signer -Recurse -Force}
}
if(!$validated){throw 'Witness acceptance incomplete'}
