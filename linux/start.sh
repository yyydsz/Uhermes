#!/bin/bash
# Umes - USB Hermes Portable Launcher
# 插上U盘，运行此脚本即可启动 Hermes Agent

DIR="$(cd "$(dirname "$0")" && pwd)"
export HERMES_HOME="$DIR/hermes_home"

# 确保配置目录存在
mkdir -p "$HERMES_HOME/skills" "$HERMES_HOME/sessions"

# 检查是否已配置
if [ ! -f "$HERMES_HOME/.env" ]; then
    echo ""
    echo "  =========================================="
    echo "  |        Umes - USB Hermes Agent         |"
    echo "  =========================================="
    echo ""
    echo "  首次使用，请先配置 API 密钥："
    echo ""
    echo "  1. 复制配置模板："
    echo "     cp hermes_home/.env.example hermes_home/.env"
    echo ""
    echo "  2. 编辑 .env 文件，填入 API 密钥"
    echo ""
    echo "  3. 复制配置文件："
    echo "     cp hermes_home/config.yaml.example hermes_home/config.yaml"
    echo ""
    echo "  详细说明请查看 README.md"
    echo ""
    exit 1
fi

exec "$DIR/python/bin/python3.11" "$DIR/hermes.pex" "$@"
