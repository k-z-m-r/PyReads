#!/bin/sh
uv sync --dev
uv build
uv run twine check dist/*
