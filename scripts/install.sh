#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ClawShell 2.0 — Local Installer (Linux / macOS / WSL)
# ═══════════════════════════════════════════════════════════
set -e

CLR="\033[0m"; RED="\033[31m"; GRN="\033[32m"; YLW="\033[33m"; BLU="\033[34m"
info()  { echo -e "${BLU}[INFO]${CLR} $1"; }
ok()    { echo -e "${GRN}[OK]${CLR}   $1"; }
warn()  { echo -e "${YLW}[WARN]${CLR} $1"; }
err()   { echo -e "${RED}[ERR]${CLR} $1"; }

echo "============================================"
echo "  ClawShell 2.0 — Local Installer"
echo "============================================"
echo ""

# ── Prerequisites ─────────────────────────────────────
info "Checking prerequisites..."

PYTHON=""
for py in python3 python; do
    if command -v $py &>/dev/null; then
        PYTHON=$py
        break
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python 3 not found. Please install Python 3.10+ first."
    exit 1
fi

PY_VER=$($PYTHON --version 2>&1 | cut -d' ' -f2)
ok "Python $PY_VER"

# ── Detect Environment ────────────────────────────────
info "Detecting environment..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWSHELL_SRC=""

# Try to find ClawShell source
for d in "$HOME/.ClawShell" "/mnt/c/Users/$USER/.ClawShell" "$SCRIPT_DIR/.."; do
    if [ -f "$d/scripts/env_detector.py" ]; then
        CLAWSHELL_SRC="$d"
        break
    fi
done

if [ -n "$CLAWSHELL_SRC" ]; then
    ok "ClawShell source: $CLAWSHELL_SRC"
    $PYTHON "$CLAWSHELL_SRC/scripts/env_detector.py"
else
    warn "ClawShell source not found — using standalone mode"
fi

# ── Install Dependencies ──────────────────────────────
info "Installing core dependencies..."

REQUIRED_PKGS="websockets psutil"
$PYTHON -m pip install --quiet $REQUIRED_PKGS 2>/dev/null || {
    warn "pip install failed — trying with --user"
    $PYTHON -m pip install --quiet --user $REQUIRED_PKGS
}
ok "Core packages installed"

# ── Ecosystem Selection ───────────────────────────────
if [ -f "$CLAWSHELL_SRC/scripts/ecosystem_installer.py" ]; then
    echo ""
    info "Starting ecosystem component selector..."
    $PYTHON "$CLAWSHELL_SRC/scripts/ecosystem_installer.py"
else
    info "Ecosystem installer not found — installing defaults"
    $PYTHON -m pip install --quiet chromadb watchdog onnxruntime
fi

# ── Configuration ─────────────────────────────────────
echo ""
info "Running configuration wizard..."
if [ -f "$CLAWSHELL_SRC/scripts/config_wizard.py" ]; then
    $PYTHON "$CLAWSHELL_SRC/scripts/config_wizard.py"
else
    warn "Config wizard not found — please configure manually"
    echo "  Edit: ~/.clawshell_edge/config.yaml"
fi

# ── Done ──────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "    clawshell-edge start    — Start edge client"
echo "    clawshell-edge status   — Check connection"
echo "    clawshell-edge stop     — Stop edge client"
echo ""
