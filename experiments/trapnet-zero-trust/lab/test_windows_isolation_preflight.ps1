# No-network deterministic regression tests; run under Windows PowerShell 5.1 or PowerShell 7.
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'windows_isolation_preflight.psm1') -Force
$assertions=0
function Check([bool]$ok,[string]$name) {
    if(-not $ok){throw ('FAIL '+$name)}
    $script:assertions+=1
    Write-Output ('PASS '+$name)
}
foreach($address in @('10.0.0.1','172.16.0.1','172.31.255.254','192.168.1.1')){
    Check ([bool](Assert-TrapNetPrivateIPv4 -Address $address)) 'RFC1918-accepted'
}
foreach($address in @('127.0.0.1','169.254.2.4','172.32.0.1','8.8.8.8','224.0.0.1','not-a-host')){
    $rejected=$false
    try{$null=Assert-TrapNetPrivateIPv4 -Address $address}catch{$rejected=$true}
    Check $rejected ('non-private-rejected-'+$address)
}
$pfx=@([pscustomobject]@{IPAddress='192.168.1.170';PrefixLength=24})
Check (Test-TrapNetSharedPrefix -Target '192.168.1.101' -LocalPrefixes $pfx) 'same-prefix'
Check (-not(Test-TrapNetSharedPrefix -Target '192.168.2.101' -LocalPrefixes $pfx)) 'other-prefix'
Check (-not(Test-TrapNetSharedPrefix -Target '10.0.0.1' -LocalPrefixes $pfx)) 'other-private-range'
$r=New-TrapNetIsolationPreflight -ProtectedTarget '192.168.1.101' -LocalPrefixes $pfx -Dialer {param($h,$p,$t) return $true}
Check ($r.verdict -eq 'UNSAFE_DIRECT_REACHABLE' -and -not $r.isolation_proven) 'reachable-is-unsafe'
Check ($r.shared_ipv4_prefix -eq $true) 'shared-prefix-reported'
Check ($r.active_probe_count -eq 1 -and -not $r.credentials_sent -and -not $r.routes_or_firewall_modified) 'strictly-read-only'
$r=New-TrapNetIsolationPreflight -ProtectedTarget '192.168.1.101' -LocalPrefixes $pfx -Dialer {param($h,$p,$t) return $false}
Check ($r.verdict -eq 'NOT_PROVEN' -and -not $r.isolation_proven) 'failed-connect-is-not-proof'
$j=$r|ConvertTo-Json
Check (-not($j -match '192\.168\.1\.')) 'report-excludes-addresses'
Write-Output ('ALL TESTS PASSED: '+$assertions)
