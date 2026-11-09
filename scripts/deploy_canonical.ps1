# ResoArc Cloudflare Pages production deployment (Direct Upload project).
# Use only from the official resoarc/resoarc-site repository checkout.
param(
  [string]$WranglerPath = "wrangler"
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$site = Join-Path $root "site"
Push-Location $root
try {
  $head = (git rev-parse HEAD).Trim()
  if ($LASTEXITCODE -ne 0) { throw "Not a Git checkout" }
  $origin = (git remote get-url origin).Trim()
  if ($origin -notmatch "resoarc/resoarc-site(?:\.git)?$") {
    throw "Unexpected Git remote. Refusing production deployment."
  }
  $remoteLine = (git ls-remote https://github.com/resoarc/resoarc-site.git refs/heads/main)
  if ($LASTEXITCODE -ne 0) { throw "Cannot verify official remote HEAD" }
  $remote = ($remoteLine -split "\s+")[0]
  if ($head -ne $remote) { throw "Local HEAD is not the latest official main commit. Fetch and fast-forward first." }
  $dirty = @(git status --porcelain -- site site-manifest.sha256 scripts/verify_site.py)
  if ($dirty.Count -gt 0) { throw ("Canonical site has uncommitted changes: " + ($dirty -join "; ")) }
  # Verify and hydrate only immutable GitHub Release binaries; never silently replace a mismatch.
  & python -X utf8 (Join-Path $root "scripts/verify_external_archive_mirror.py") --hydrate
  if ($LASTEXITCODE -ne 0) { throw "Pinned GitHub Release assets unavailable or mismatched" }
  & python -X utf8 (Join-Path $root "scripts/hydrate_current_distribution.py")
  if ($LASTEXITCODE -ne 0) { throw "Current distribution assets unavailable or mismatched" }
  & python -X utf8 (Join-Path $root "scripts/verify_suite16_readiness.py")
  if ($LASTEXITCODE -ne 0) { throw "Signed QA source integrity failed" }
  & python -X utf8 (Join-Path $root "scripts/check_signed_qa_reconciliation.py")
  if ($LASTEXITCODE -ne 0) { throw "Signed QA public catalog integrity failed" }
  & python -X utf8 (Join-Path $root "scripts/verify_web8_v1.py")
  if ($LASTEXITCODE -ne 0) { throw "Frozen Web8 release integrity failed" }
  $osPage = Join-Path $site "os/index.html"
  $source = Join-Path $site "downloads/resoarcos-pc-v0.1.0-dev-source.zip"
  if (!(Test-Path $osPage) -or !(Test-Path $source)) { throw "ResoArcOS release files missing. Deployment blocked." }
  $expected = "72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20"
  if ((Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw "OS source archive digest mismatch"
  }
  & python -X utf8 (Join-Path $root "scripts/verify_site.py")
  if ($LASTEXITCODE -ne 0) { throw "Site verification failed" }
  # Fail closed if currently published Pages routes are missing from the candidate.
  # A GitHub merge alone is not evidence that the public Direct Upload site is synchronized.
  & python -X utf8 (Join-Path $root "scripts/verify_live_route_preservation.py")
  if ($LASTEXITCODE -ne 0) { throw "Live route preservation failed; refusing full-site overwrite" }
  & python -X utf8 (Join-Path $root "scripts/verify_live_data_preservation.py")
  if ($LASTEXITCODE -ne 0) { throw "Live SWWW snapshot mismatch; refusing full-site overwrite" }
  # Main PC uses an authenticated local npx Wrangler installation.
  # Never install or update a CLI as a side effect of a production deploy.
  $wranglerArgs = @()
  if (!(Get-Command $WranglerPath -ErrorAction SilentlyContinue)) {
    if ($WranglerPath -ne "wrangler") { throw "Specified Wrangler executable is unavailable" }
    if (!(Get-Command npx -ErrorAction SilentlyContinue)) { throw "Neither wrangler nor npx is available" }
    $WranglerPath = "npx"
    $wranglerArgs = @("--no-install", "wrangler")
    Write-Output "Wrangler CLI unavailable, falling back to preinstalled npx"
  }
  Write-Output ("Deploying verified Git commit " + $head)
  & $WranglerPath @wranglerArgs pages deploy $site --project-name resoarc --branch main --commit-hash $head --commit-dirty=true
  if ($LASTEXITCODE -ne 0) { throw "Cloudflare Pages deployment failed" }
  $stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  foreach ($hostName in @("resoarc.com", "www.resoarc.com", "resoarc.pages.dev")) {
    foreach ($route in @("/", "/os/", "/products/")) {
      $url = 'https://' + $hostName + $route + '?deploycheck=' + $stamp
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
      if ($response.StatusCode -ne 200 -or !$response.Content.Contains('href="/os/"')) {
        throw ("Live site failed OS navigation check: " + $url)
      }
      Write-Output ("LIVE_OK " + $url)
    }
    $zipUrl = 'https://' + $hostName + '/downloads/resoarcos-pc-v0.1.0-dev-source.zip?deploycheck=' + $stamp
    $tempZip = Join-Path ([IO.Path]::GetTempPath()) ("resoarc-verify-" + [guid]::NewGuid().ToString("N") + ".zip")
    try {
      Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -TimeoutSec 45
      if ((Get-FileHash $tempZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw ("Live source ZIP checksum mismatch: " + $zipUrl)
      }
      Write-Output ("SOURCE_OK " + $zipUrl)
    } finally {
      Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
    }
  }
  Write-Output "PRODUCTION_SITE_VERIFIED"
} finally {
  Pop-Location
}
