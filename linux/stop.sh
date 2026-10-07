#!/bin/bash
# ============================================================================
#  Uhermes - stop the Hermes gateway and remove host autostart, so the drive
#  can be unmounted safely.
#
#  Use this when the filesystem is busy and refuses to unmount, or before
#  unplugging the stick after having used the messaging gateway.
# ============================================================================
set -uo pipefail

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

export HERMES_HOME="$DIR/hermes_home"
export PYTHONPATH="$DIR/hermes-agent"
export PYTHONNOUSERSITE=1
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
if [ -d "$DIR/bin" ]; then
    export PATH="$DIR/bin:$PATH"
fi

PY="$DIR/python/bin/python3.11"
if [ ! -x "$PY" ]; then
    echo "[Uhermes] Portable Python not found: $PY" >&2
    exit 1
fi

echo
echo "  Stopping Hermes gateway ..."
"$PY" "$DIR/hermes_boot.py" gateway stop
echo
echo "  Removing host autostart entries ..."
"$PY" "$DIR/hermes_boot.py" gateway uninstall
echo
echo "  ------------------------------------------------------------------"
echo "  Done. No gateway process should hold this drive any more."
echo "  You can now unmount / unplug the drive safely."
echo "  ------------------------------------------------------------------"
echo
