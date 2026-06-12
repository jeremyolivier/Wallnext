.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

build: ## Compile wallnext into a standalone .exe with Nuitka
	uv run nuitka --mode=standalone --assume-yes-for-downloads --output-dir=build --output-filename=wallnext --remove-output src/wallnext/main.py

clean: ## Remove build artifacts
	rm -rf build

.PHONY: help build clean
