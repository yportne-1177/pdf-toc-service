cat > start.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root (this script's folder)
cd "$(dirname "${BASH_SOURCE[0]}")"

# ---- Settings ----
PORT="${PORT:-5000}"

# Pick the app file automatically
if [[ -f "function_app.py" ]]; then
  APP_FILE="function_app.py"
elif [[ -f "app.py" ]]; then
  APP_FILE="app.py"
else
  echo "❌ Could not find function_app.py or app.py in $(pwd). Edit start.sh to set APP_FILE."
  exit 1
fi

# ---- Python / venv ----
if [[ ! -d ".venv" ]]; then
  echo "📦 Creating virtual environment (.venv)…"
  python3 -m venv .venv
fi

echo "🔧 Activating .venv…"
# shellcheck disable=SC1091
source .venv/bin/activate

# Keep pip fresh
python -m pip install --upgrade pip >/dev/null

# If Flask or PyMuPDF (fitz) are missing, install from requirements.txt
python - <<'PY' >/dev/null 2>&1 || pip install -r requirements.txt
try:
    import flask, fitz  # PyMuPDF
except Exception:
    raise SystemExit(1)
PY

# ---- Helpful info for Codespaces ----
echo
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  PUBLIC_BASE="https://${CODESPACE_NAME}-${PORT}.app.github.dev"
  echo "🌐 If Port $PORT is Public (Ports tab), your endpoints are:"
  echo "  GET  $PUBLIC_BASE/"
  echo "  GET  $PUBLIC_BASE/health"
  echo "  POST $PUBLIC_BASE/add-pdf-toc"
  echo
  echo "⚠️  In the Ports tab, set port $PORT to Visibility: Public."
else
  echo "🌐 Not in Codespaces. Access locally at: http://localhost:${PORT}/"
fi
echo

export PORT
echo "🚀 Starting Flask app: ${APP_FILE} on 0.0.0.0:${PORT} (Ctrl+C to stop)"
echo
python "$APP_FILE"
SH

chmod +x start.sh
