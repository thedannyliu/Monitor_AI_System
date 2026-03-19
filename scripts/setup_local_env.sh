#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
VENV_DIR="${VENV_DIR:-.venv}"

"$PYTHON_BIN" --version
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -e .

echo "Created virtual environment at $VENV_DIR"
