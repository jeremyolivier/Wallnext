# Windows-only project: recipes run in PowerShell.
set windows-shell := ["pwsh", "-NoProfile", "-Command"]

version := `uv version --short`

# build/main.build is kept and LTO is off so rebuilds only recompile what changed.
# Pygments lexers/styles are only used to colour code; keep just their _mapping index.
nuitka_flags := "--mode=standalone --assume-yes-for-downloads --windows-console-mode=attach --enable-plugin=pyside6 --lto=no '--nofollow-import-to=pygments.lexers.[!_]*' '--nofollow-import-to=pygments.styles.[!_]*' --output-dir=build --output-filename=wallnext"

# Shown in the exe's Properties > Details, and read by the About page.
version_info := "--product-name=Wallnext --file-description=Wallnext --product-version=" + version + " --file-version=" + version + " '--company-name=Jérémy Olivier' '--copyright=Copyright (c) 2026 Jérémy Olivier'"

# List the recipes
default:
    @just --list

# Compile wallnext into a standalone .exe with Nuitka, with its licenses
build:
    uv run nuitka {{ nuitka_flags }} {{ version_info }} src/wallnext/main.py
    Copy-Item LICENSE build/main.dist/LICENSE.txt
    uv run python -m wallnext.notices build/main.dist/THIRD-PARTY-NOTICES.txt

# Zip the build with its Scoop manifest into build/dist (base_url: where the zip will be downloaded from)
package base_url:
    ./scripts/package.ps1 -BaseUrl '{{ base_url }}'

# Build the Windows installer into build/dist (needs WiX: scoop install wixtoolset)
msi:
    wix build installer/wallnext.wxs -arch x64 -d Version={{ version }} -b 'dist={{ justfile_directory() }}/build/main.dist' -o build/dist/Wallnext-{{ version }}.msi -pdbtype none -acceptEula wix7

# Build the exe and launch it, without installing it
run-build: build
    ./build/main.dist/wallnext.exe

# Remove the scheduled task and the published Scoop install
scoop-uninstall:
    -wallnext schedule uninstall
    scoop uninstall wallnext

# The tag is annotated: `git push --follow-tags` leaves lightweight tags behind.

# Bump the version (major, minor or patch), commit and tag it; then git push --follow-tags
[arg("kind", pattern="major|minor|patch")]
bump kind:
    if (git status --porcelain) { throw 'Commit or stash your changes first.' }
    if ((git branch --show-current) -ne 'main') { throw 'Release from main.' }
    uv version --bump {{ kind }}
    git add pyproject.toml uv.lock
    git commit -m "🔖 Release v$(uv version --short)"
    git tag -a "v$(uv version --short)" -m "Release v$(uv version --short)"

# Remove build artifacts
clean:
    if (Test-Path build) { Remove-Item -Recurse -Force build }
