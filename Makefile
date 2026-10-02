.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# build/main.build is kept and LTO is off so rebuilds only recompile what changed.
# Pygments lexers/styles are only used to colour code; keep just their _mapping index.
NUITKA_FLAGS := \
	--mode=standalone \
	--assume-yes-for-downloads \
	--windows-console-mode=attach \
	--lto=no \
	--nofollow-import-to='pygments.lexers.[!_]*' \
	--nofollow-import-to='pygments.styles.[!_]*' \
	--output-dir=build \
	--output-filename=wallnext

build: ## Compile wallnext into a standalone .exe with Nuitka
	uv run nuitka $(NUITKA_FLAGS) src/wallnext/main.py

clean: ## Remove build artifacts
	rm -rf build

.PHONY: help build clean
