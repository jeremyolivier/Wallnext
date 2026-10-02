# Install build/main.dist with Scoop, zipped like a release.
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$build = Join-Path $root 'build'
$zip = Join-Path $build 'wallnext-local.zip'

Compress-Archive -Path (Join-Path $build 'main.dist') -DestinationPath $zip -Force

$manifest = Get-Content (Join-Path $root 'scoop\wallnext.json') -Raw | ConvertFrom-Json
$manifest.architecture.'64bit'.url = $zip
$manifest.architecture.'64bit'.hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
$manifest.PSObject.Properties.Remove('checkver')
$manifest.PSObject.Properties.Remove('autoupdate')

# Scoop names the app after the manifest file.
$manifestDir = New-Item -ItemType Directory -Force (Join-Path $build 'scoop')
$manifestPath = Join-Path $manifestDir 'wallnext.json'
$manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath

$scoopRoot = if ($env:SCOOP) { $env:SCOOP } else { Join-Path $HOME 'scoop' }
if (Test-Path (Join-Path $scoopRoot 'apps\wallnext')) {
    scoop uninstall wallnext
}

# aria2 can't download a local path: disable it for this install only.
$aria2 = (Get-Content (Join-Path $HOME '.config\scoop\config.json') -Raw | ConvertFrom-Json).'aria2-enabled'
scoop config aria2-enabled false | Out-Null
try {
    # Same version and path on every build: a cached zip would be stale.
    scoop install $manifestPath --no-cache
} finally {
    if ($null -eq $aria2) {
        scoop config rm aria2-enabled | Out-Null
    } else {
        scoop config aria2-enabled $aria2 | Out-Null
    }
}
