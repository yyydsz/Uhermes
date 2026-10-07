#!/usr/bin/env bash
# Uhermes 便携包构建（Linux / macOS 上构建 Linux 包）
#
# 用法：
#   ./build/build-linux.sh                    # 构建 Linux 便携包
#   ./build/build-linux.sh --extras core      # 只装核心依赖
#   ./build/build-linux.sh --with-uv          # 把 uv 也打进包
#   ./build/build-linux.sh --check            # 查上游是否有新版本
#
# 网络：需要能访问 github.com 与 pypi.org。走代理时设置：
#   export HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890
#
# 依赖：Python 3.9+ 与 uv。不需要 git。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
    for cand in python3 python; do
        if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
    done
fi
if [ -z "$PY" ]; then
    echo "build-linux.sh: 找不到 python3（需要 Python 3.9+）" >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "build-linux.sh: 警告 —— 未找到 uv，将回退到 pip（无法交叉构建）" >&2
fi

exec "$PY" "$ROOT/build/build.py" --platform linux "$@"
