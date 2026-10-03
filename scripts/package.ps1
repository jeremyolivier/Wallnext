# Zip build/main.dist and write its Scoop manifest, both into build/dist.
# -BaseUrl is where the zip will be downloaded from; empty means this machine.
param([string]$BaseUrl = '')
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$build = Join-Path $root 'build'
$dist = New-Item -ItemType Directory -Force (Join-Path $build 'dist')
$version = uv version --short --project $root
$name = "wallnext-$version-win64.zip"
$zip = Join-Path $dist $name

Compress-Archive -Path (Join-Path $build 'main.dist') -DestinationPath $zip -Force

$manifest = Get-Content (Join-Path $root 'scoop\wallnext.json') -Raw | ConvertFrom-Json
$manifest.version = $version
$manifest.architecture.'64bit'.url = if ($BaseUrl) { "$BaseUrl/$name" } else { $zip }
$manifest.architecture.'64bit'.hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
# Scoop names the app after the manifest file.
$manifest | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $dist 'wallnext.json')
