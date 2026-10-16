# Local-only Cloudflare workerd integration check. Uses disabled Clock sample, no secrets.
$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir=Join-Path $here '.wrangler\clock-local-test'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$out=Join-Path $logDir 'stdout.log'
$err=Join-Path $logDir 'stderr.log'
$port=8793
$npx='C:\Program Files\nodejs\npx.cmd'
if(!(Test-Path $npx)){throw 'npx.cmd not found'}
$proc=Start-Process -FilePath $npx -ArgumentList @('wrangler','dev','--local','--test-scheduled','--config','center-wrangler.example.jsonc','--port',$port,'--show-interactive-dev-session=false') -PassThru -WorkingDirectory $here -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
try {
    $response=$null
    for($i=0;$i -lt 70;$i++){
        Start-Sleep -Milliseconds 300
        try{$response=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/cdn-cgi/local/scheduled?cron=*+*+*+*+*" -TimeoutSec 2;break}catch{}
    }
    if(!$response){throw 'workerd did not respond to scheduled route'}
    if($response.StatusCode -ne 200){throw "unexpected Cron HTTP $($response.StatusCode)"}
    $webResp=$null
    try{$webResp=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/run" -TimeoutSec 3}catch{ $webResp=$_.Exception.Response }
    if($webResp -and [int]$webResp.StatusCode -ne 404){throw 'public endpoint was not 404'}
    $logs=@()
    if(Test-Path $out){$logs+=Get-Content $out -ErrorAction SilentlyContinue}
    if(Test-Path $err){$logs+=Get-Content $err -ErrorAction SilentlyContinue}
    if(($logs -join ' ') -notmatch 'Clock is disabled'){throw 'Cron handler did not run disabled Clock'}
    Write-Output 'LOCAL_WORKER_CRON_OK: HTTP 200, disabled without kintone, public endpoint 404'
} finally {
    if($proc){
        cmd.exe /c "taskkill /PID $($proc.Id) /T /F" 2>$null | Out-Null
    }
}
