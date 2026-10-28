# Read-only single-target probe. Exit 2: unsafe; 3: not proven; 1: error.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ProtectedTarget,
    [ValidateRange(1,65535)][int]$Port=3389,
    [ValidateRange(100,5000)][int]$TimeoutMs=1200,
    [string]$OutputJson
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'windows_isolation_preflight.psm1') -Force
try {
    $result=New-TrapNetIsolationPreflight -ProtectedTarget $ProtectedTarget -Port $Port -TimeoutMs $TimeoutMs
    $data=$result|ConvertTo-Json -Depth 4
    Write-Output $data
    if($OutputJson){
        $parent=Split-Path -Parent $OutputJson
        if($parent -and -not(Test-Path -LiteralPath $parent)){throw 'Output parent folder must already exist.'}
        # Output has no host IP, computer/user name, access key or credentials.
        [System.IO.File]::WriteAllText($OutputJson,$data+[Environment]::NewLine,[System.Text.UTF8Encoding]::new($false))
    }
    if($result.protected_tcp_reachable){exit 2}
    # A closed port can never automatically pass isolation.
    exit 3
}catch {
    Write-Error ('Preflight refused or failed: '+$_.Exception.Message)
    exit 1
}
