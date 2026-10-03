.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# build/main.build is kept and LTO is off so rebuilds only recompile what changed.
# Pygments lexers/styles are only used to colour code; keep just their _mapping index.
NUITKA_FLAGS := \
	--mode=standalone \
	--assume-yes-for-downloads \
	--windows-console-mode=attach \
	--enable-plugin=pyside6 \
	--lto=no \
	--nofollow-import-to='pygments.lexers.[!_]*' \
	--nofollow-import-to='pygments.styles.[!_]*' \
	--output-dir=build \
	--output-filename=wallnext

build: ## Compile wallnext into a standalone .exe with Nuitka
	uv run nuitka $(NUITKA_FLAGS) src/wallnext/main.py

scoop-install: build ## Build and install it with Scoop
	pwsh -NoProfile -File scripts/scoop-local.ps1

scoop-uninstall: ## Remove the scheduled task and the Scoop install
	-wallnext schedule uninstall
	pwsh -NoProfile -Command "scoop uninstall wallnext"

clean: ## Remove build artifacts
	rm -rf build

.PHONY: help build scoop-install scoop-uninstall clean
