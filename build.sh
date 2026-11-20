#!/usr/bin/env bash
# TriageIQ - end-to-end build (macOS / Linux). Safe to re-run.
set -e
cd "$(dirname "$0")"
echo "== TriageIQ end-to-end build =="
if [ ! -x ".venv/bin/python" ]; then
  echo "[1/5] Creating virtual environment .venv ..."
  python3 -m venv .venv
else
  echo "[1/5] Virtual environment .venv already exists - reusing it."
fi
PY=.venv/bin/python
echo "[2/5] Installing dependencies (requirements.txt) ..."
$PY -m pip install --upgrade pip >/dev/null
$PY -m pip install -r requirements.txt
echo "[3/5] Configuration smoke test (test.py) ..."
$PY test.py
echo "[4/5] Building the knowledge base (data_ingestion.py) ..."
$PY data_ingestion.py
echo "[5/5] Running the test suite (pytest) ..."
$PY -m pytest -q
echo
echo "BUILD OK - TriageIQ is ready."
echo "Run it with:  .venv/bin/python app.py"
echo "Then open:    http://127.0.0.1:8080"
