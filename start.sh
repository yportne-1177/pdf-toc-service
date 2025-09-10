cat > start.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PORT="${PORT:-5000}"

# Detect the app file
if [[ -f "function_app.py" ]]; then
  APP_FILE="function_app.py"
elif [[ -f "app.py" ]]; then
  APP_FILE="app.py"
else
  echo "❌ No function_app.py or app.py found in $(pwd)."
  exit 1
fi

# venv + deps
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# Helpful URLs (Codespaces)
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  BASE="https://${CODESPACE_NAME}-${PORT}.app.github.dev"
  echo
  echo "🌐 Public endpoints (set port $PORT to Public in the Ports tab):"
  echo "  GET  $BASE/"
  echo "  GET  $BASE/health"
  echo "  GET  $BASE/add-pdf-toc  (readiness)"
  echo "  POST $BASE/add-pdf-toc  (TOC creation)"
  echo
fi

echo "🚀 Starting Flask app: $APP_FILE on 0.0.0.0:$PORT ..."
python "$APP_FILE"
SH

chmod +x start.sh
