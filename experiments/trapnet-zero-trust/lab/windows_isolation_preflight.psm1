# Read-only TrapNet Sensor lateral-movement preflight.
# Never modifies Windows routing, firewall, services or credentials.
Set-StrictMode -Version Latest

function ConvertTo-TrapNetIPv4Integer {
    param([Parameter(Mandatory)][string]$Address)
    $ip=$null
    if (-not [System.Net.IPAddress]::TryParse($Address,[ref]$ip) -or $ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        throw 'An IPv4 literal is required.'
    }
    $b=$ip.GetAddressBytes()
    return ([uint64]$b[0]*[uint64]16777216+[uint64]$b[1]*[uint64]65536+[uint64]$b[2]*[uint64]256+[uint64]$b[3])
}

function Assert-TrapNetPrivateIPv4 {
    param([Parameter(Mandatory)][string]$Address)
    $ip=$null
    if (-not [System.Net.IPAddress]::TryParse($Address,[ref]$ip) -or $ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        throw 'Only explicit private IPv4 literals are accepted.'
    }
    $b=$ip.GetAddressBytes()
    if (-not (($b[0] -eq 10) -or ($b[0] -eq 172 -and $b[1] -ge 16 -and $b[1] -le 31) -or ($b[0] -eq 192 -and $b[1] -eq 168))) {
        throw 'Refusing to probe any public, loopback, multicast or link-local address.'
    }
    return $true
}

function Test-TrapNetSharedPrefix {
    param([Parameter(Mandatory)][string]$Target,[Parameter(Mandatory)][object[]]$LocalPrefixes)
    $null=Assert-TrapNetPrivateIPv4 -Address $Target
    $t=ConvertTo-TrapNetIPv4Integer -Address $Target
    foreach($item in $LocalPrefixes){
        if($null -eq $item -or $null -eq $item.IPAddress -or $null -eq $item.PrefixLength){continue}
        $p=[int]$item.PrefixLength
        if($p -lt 1 -or $p -gt 32){continue}
        $local=ConvertTo-TrapNetIPv4Integer -Address ([string]$item.IPAddress)
        $mask=([uint64]4294967295 -shl (32-$p)) -band [uint64]4294967295
        if(($local -band $mask) -eq ($t -band $mask)){return $true}
    }
    return $false
}

function Test-TrapNetTcpConnect {
    param([Parameter(Mandatory)][string]$Target,[Parameter(Mandatory)][int]$Port,[ValidateRange(100,5000)][int]$TimeoutMs=1200)
    $null=Assert-TrapNetPrivateIPv4 -Address $Target
    if($Port -lt 1 -or $Port -gt 65535){throw 'Invalid TCP port'}
    $client=New-Object System.Net.Sockets.TcpClient
    try {
        $async=$client.BeginConnect($Target,$Port,$null,$null)
        if(-not $async.AsyncWaitHandle.WaitOne($TimeoutMs)){return $false}
        try{$client.EndConnect($async);return $true}catch{return $false}
    }finally{$client.Close()}
}

function New-TrapNetIsolationPreflight {
    param(
        [Parameter(Mandatory)][string]$ProtectedTarget,
        [ValidateRange(1,65535)][int]$Port=3389,
        [ValidateRange(100,5000)][int]$TimeoutMs=1200,
        [object[]]$LocalPrefixes,
        [scriptblock]$Dialer
    )
    $null=Assert-TrapNetPrivateIPv4 -Address $ProtectedTarget
    if($null -eq $LocalPrefixes){
        $LocalPrefixes=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {$_.AddressState -eq 'Preferred' -and $_.PrefixLength -ge 1} |
            Select-Object IPAddress,PrefixLength)
    }
    if($null -eq $Dialer){
        $Dialer={param($target,$port,$timeout) Test-TrapNetTcpConnect -Target $target -Port $port -TimeoutMs $timeout}
    }
    $shared=[bool](Test-TrapNetSharedPrefix -Target $ProtectedTarget -LocalPrefixes $LocalPrefixes)
    $reachable=[bool](& $Dialer $ProtectedTarget $Port $TimeoutMs)
    $verdict=if($reachable){'UNSAFE_DIRECT_REACHABLE'}else{'NOT_PROVEN'}
    $advice=if($reachable){
        'Sensor can directly reach a protected host service. Isolate the future honeypot on a dedicated VLAN/guest network before exposing it.'
    }else{
        'TCP failed but network isolation is NOT proven: target may be stopped, firewalled or routed through other paths.'
    }
    return [pscustomobject][ordered]@{
        schema='trapnet.windows-isolation-preflight.v1'
        verdict=$verdict
        protected_tcp_reachable=$reachable
        shared_ipv4_prefix=$shared
        control_port=$Port
        active_probe_count=1
        credentials_sent=$false
        routes_or_firewall_modified=$false
        isolation_proven=$false
        exposed_raw_addresses_in_report=$false
        advice=$advice
    }
}
Export-ModuleMember -Function Assert-TrapNetPrivateIPv4,ConvertTo-TrapNetIPv4Integer,Test-TrapNetSharedPrefix,Test-TrapNetTcpConnect,New-TrapNetIsolationPreflight
