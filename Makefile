# Makefile for version bumping with optional flags

.PHONY: bump

major:
	uv run bump pyreads/__init__.py --major

minor:
	uv run bump pyreads/__init__.py- -minor

patch:
	uv run bump pyreads/__init__.py --patch

# Usage:
#   make major
#   make minor
#   make patch
