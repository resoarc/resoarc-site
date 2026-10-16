# ResoArc Mini Plugins: import a verified *unsigned* v1-review source archive.
# This script never uploads to kintone, never signs ZIPs, and never overwrites sources.
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ArchivePath,
  [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$expectedSha256 = '8924b75e36b964fd4985a15f5b3bb423961b2334e8e5fc7035509493def1d103'
$root = Join-Path $env:USERPROFILE 'Documents\GitHub\resoarc-mini-plugins'
$work = Join-Path $env:USERPROFILE 'Documents\AI-Work\MR-kintone-tests\staging'
$staging = Join-Path $work ('mini-v1-review-' + [guid]::NewGuid().ToString('N'))
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) { throw "Archive not found: $ArchivePath" }
$hash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $expectedSha256) { throw "Archive SHA-256 mismatch: expected $expectedSha256, got $hash" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
try {
  if ($zip.Entries.Count -lt 150) { throw "Incomplete source ZIP: $($zip.Entries.Count) members" }
  foreach ($entry in $zip.Entries) {
    $name = $entry.FullName
    if ($name -match '(^/|(^|/)\.\.(/|$)|^[A-Za-z]:|\\)' -or [string]::IsNullOrWhiteSpace($name)) {
      throw "Unsafe ZIP member: $name"
    }
  }
} finally { $zip.Dispose() }

New-Item -ItemType Directory -Force -Path $work | Out-Null
New-Item -ItemType Directory -Force -Path $staging | Out-Null
try {
  [System.IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath,$staging)
  $manifests = @(Get-ChildItem -LiteralPath (Join-Path $staging 'plugins') -Recurse -File -Filter manifest.json)
  if ($manifests.Count -ne 18) { throw "Expected 18 manifests, found $($manifests.Count)" }

  Push-Location $staging
  try {
    & python 'scripts\build_source.py'
    if ($LASTEXITCODE -ne 0) { throw 'Source-only build or manifest validation failed' }
    & node 'tests\smoke.cjs'
    if ($LASTEXITCODE -ne 0) { throw '18-plugin event mocks failed' }
    & node --test 'tests\v1-hardening.cjs'
    if ($LASTEXITCODE -ne 0) { throw 'Security regressions failed' }
    & python 'tests\test_packaging_safety.py'
    if ($LASTEXITCODE -ne 0) { throw 'Signing fail-closed regression failed' }
  } finally { Pop-Location }

  if ($VerifyOnly) {
    Write-Output 'VALIDATED: 18 manifests; source-only build, event and security tests passed.'
    return
  }
  if (Test-Path -LiteralPath $root) {
    $present = @(Get-ChildItem -LiteralPath $root -Force -ErrorAction Stop)
    if ($present.Count -ne 0) { throw "Destination is not empty. Nothing was overwritten: $root" }
  } else {
    New-Item -ItemType Directory -Force -Path $root | Out-Null
  }
  foreach ($file in (Get-ChildItem -LiteralPath $staging -Force)) {
    Move-Item -LiteralPath $file.FullName -Destination $root -ErrorAction Stop
  }
  Write-Output "IMPORTED: 18 beta-derived plugin sources to $root"
  Write-Output 'This is an UNSIGNED v1-review source candidate. Not deployable as a kintone plugin ZIP.'
} finally {
  if (Test-Path -LiteralPath $staging) {
    Remove-Item -LiteralPath $staging -Force -Recurse -ErrorAction SilentlyContinue
  }
}
