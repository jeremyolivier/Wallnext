# Install the local build (see `just package`) with Scoop.
$ErrorActionPreference = 'Stop'

$manifestPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'build\dist\wallnext.json'

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
