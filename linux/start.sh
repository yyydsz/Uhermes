#!/bin/bash
# ============================================================================
#  Uhermes - USB Hermes Portable Launcher (Linux x86_64)
#
#  No venv, no editable install: the portable interpreter derives its prefix
#  from its own location, and the source tree is simply put on PYTHONPATH.
#  That is what keeps the bundle relocatable (USB stick, any mount point).
# ============================================================================
set -euo pipefail

# Resolve the bundle root from this script's real location (follow symlinks).
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    case "$SOURCE" in
        /*) ;;
        *) SOURCE="$DIR/$SOURCE" ;;
    esac
done
DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

# --- Portable layout --------------------------------------------------------
#   DIR/python       portable CPython (relocatable)
#   DIR/hermes-agent upstream source tree, pinned in versions.env
#   DIR/hermes_home  all user data: .env, config.yaml, sessions, skills, state.db
#   DIR/bin          optional bundled tools (uv), prepended to PATH
export HERMES_HOME="$DIR/hermes_home"
export PYTHONPATH="$DIR/hermes-agent"
export PYTHONNOUSERSITE=1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export HERMES_LAZY_INSTALL_TARGET="$HERMES_HOME/lazy-deps"
export UV_CACHE_DIR="$HERMES_HOME/cache/uv"
export UV_PYTHON_INSTALL_DIR="$HERMES_HOME/runtime"
if [ -d "$DIR/bin" ]; then
    export PATH="$DIR/bin:$PATH"
fi

mkdir -p "$HERMES_HOME"

PY="$DIR/python/bin/python3.11"
if [ ! -x "$PY" ]; then
    echo ""
    echo "  [Uhermes] Portable Python not found: $PY"
    echo "  [Uhermes] The package looks incomplete. Re-extract the archive."
    echo "  [Uhermes] If permissions were lost (FAT/exFAT stick), run:"
    echo "            chmod +x \"$DIR/python/bin/\"*"
    echo ""
    exit 1
fi

exec "$PY" "$DIR/hermes_boot.py" "$@"
