<div align="center">

# Umes

<p align="center">
  <img src="assets/umes-hero.gif" alt="Umes Hero Animation" />
  <br/>
  <sub>动画由 <a href="https://github.com/alchaincyf/huashu-design">huashu-design</a> skill 制作</sub>
</p>

> *「插上U盘，走到哪，Agent跟到哪」*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Hermes Agent](https://img.shields.io/badge/Powered%20by-Hermes%20Agent-green.svg)](https://github.com/NousResearch/hermes-agent)

<br>

**U盘里的 AI Agent。解压即用，无需安装 Python，无需配置环境。**

<br>

[快速开始](#快速开始) · [Linux 使用](#linux-使用) · [Windows 使用](#windows-使用) · [配置说明](#配置说明) · [常见问题](#常见问题) · [构建说明](#构建说明)

</div>

---

## 这是什么

Umes (USB + Hermes) 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的便携打包版。

把整个 Python 解释器 + Hermes + 所有依赖打成一个压缩包，解压后双击就能跑。

**适用场景：**
- U盘随身携带，走到哪用到哪
- 不想在公司/学校电脑上装 Python 环境
- 临时用一下别人的电脑
- 快速部署到多台机器

---

## 快速开始

### 下载

从 [Releases](https://github.com/BBGGX/Umes/releases) 页面下载对应版本：

| 平台 | 文件 | 大小 |
|------|------|------|
| Linux x86_64 | `umes-linux.zip` | ~73MB |
| Windows x86_64 | `umes-windows.zip` | ~34MB |

### 配置 API 密钥

解压后，进入 `hermes_home` 目录：

```bash
# Linux / macOS
cp hermes_home/.env.example hermes_home/.env
cp hermes_home/config.yaml.example hermes_home/config.yaml

# Windows
copy hermes_home\.env.example hermes_home\.env
copy hermes_home\config.yaml.example hermes_home\config.yaml
```

编辑 `.env` 文件，填入至少一个 LLM Provider 的 API 密钥：

```env
# Anthropic (推荐 Claude)
ANTHROPIC_API_KEY=sk-ant-xxx

# OpenAI
OPENAI_API_KEY=sk-xxx

# OpenRouter (支持多种模型)
OPENROUTER_API_KEY=sk-or-xxx
```

编辑 `config.yaml` 设置默认模型：

```yaml
model:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
```

### 启动

```bash
# Linux
chmod +x start.sh
./start.sh

# Windows
双击 start.bat
```

就这么简单。

---

## Linux 使用

### 目录结构

```
umes-linux/
├── start.sh              # 启动脚本
├── hermes.pex            # Hermes Agent (PEX 格式，含所有依赖)
├── python/               # 便携版 Python 3.11 (不污染系统)
│   ├── bin/
│   │   └── python3.11    # Python 解释器
│   └── lib/
│       └── python3.11/   # 标准库
└── hermes_home/          # 配置和数据目录
    ├── .env.example      # API 密钥模板
    ├── config.yaml.example
    ├── skills/           # 技能目录 (自动创建)
    ├── sessions/         # 会话记录 (自动创建)
    └── ...
```

### 基本使用

```bash
# 进入目录
cd umes-linux

# 首次使用：配置 API 密钥
cp hermes_home/.env.example hermes_home/.env
nano hermes_home/.env  # 或用任何编辑器

# 启动交互式聊天
./start.sh

# 直接发消息 (非交互模式)
./start.sh chat "帮我写一个 Python 脚本"

# 查看帮助
./start.sh --help

# 管理模型
./start.sh model

# 管理技能
./start.sh skills
```

### 高级用法

```bash
# 使用特定技能
./start.sh --skills coding "帮我重构这段代码"

# 进入 gateway 模式 (连接 Telegram/Discord 等)
./start.sh gateway

# 查看状态
./start.sh status

# 管理定时任务
./start.sh cron
```

### 系统要求

- **操作系统**: Linux x86_64 (glibc 2.17+，即 CentOS 7+ / Ubuntu 16.04+)
- **磁盘空间**: 解压后约 118MB
- **内存**: 建议 512MB+
- **网络**: 需要网络连接 (调用 LLM API)

---

## Windows 使用

### 目录结构

```
umes-windows/
├── start.bat             # 启动脚本 (双击即可)
├── hermes-win.pyz        # Hermes Agent (Python zipapp 格式)
├── python/               # 便携版 Python 3.11 (不污染系统)
│   ├── python.exe        # Python 解释器
│   ├── python311.dll     # Python 运行时
│   └── Lib/
│       └── python3.11/   # 标准库
└── hermes_home/          # 配置和数据目录
    ├── .env.example
    ├── config.yaml.example
    ├── skills/
    ├── sessions/
    └── ...
```

### 基本使用

1. **解压** `umes-windows.zip` 到任意位置 (U盘、桌面、D盘都行)

2. **配置 API 密钥**:
   - 复制 `hermes_home\.env.example` 为 `hermes_home\.env`
   - 复制 `hermes_home\config.yaml.example` 为 `hermes_home\config.yaml`
   - 用记事本编辑 `.env`，填入 API 密钥

3. **双击 `start.bat`** 启动

### Windows 特别说明

- **杀毒软件**: 首次运行可能被 Windows Defender 拦截，点击"仍要运行"即可。便携版 Python 是官方构建，完全安全。
- **中文路径**: 支持中文目录名，但建议用英文路径避免兼容性问题。
- **U盘**: 直接解压到U盘根目录，插到任何 Windows 电脑上双击就能用。
- **PowerShell**: 也可以在 PowerShell 中运行 `.\start.bat`。

### 系统要求

- **操作系统**: Windows 10+ x86_64
- **磁盘空间**: 解压后约 113MB
- **内存**: 建议 512MB+
- **网络**: 需要网络连接 (调用 LLM API)

---

## 配置说明

### .env 文件

```env
# ===== LLM Provider (至少配一个) =====
ANTHROPIC_API_KEY=sk-ant-xxx      # Anthropic Claude (推荐)
OPENAI_API_KEY=sk-xxx             # OpenAI GPT
OPENROUTER_API_KEY=sk-or-xxx      # OpenRouter (多模型)
GOOGLE_API_KEY=xxx                # Google Gemini

# ===== 可选工具 =====
FIRECRAWL_API_KEY=fc-xxx          # 网页抓取
EXA_API_KEY=xxx                   # 搜索引擎
FAL_KEY=xxx                       # 图片生成

# ===== 可选集成 =====
TELEGRAM_BOT_TOKEN=xxx            # Telegram Bot
DISCORD_TOKEN=xxx                 # Discord Bot
```

### config.yaml 文件

```yaml
# 默认模型
model:
  provider: "anthropic"           # anthropic, openai, openrouter, etc.
  model: "claude-sonnet-4-20250514"  # 模型名称

# 显示设置
display:
  skin: default                   # 主题: default, ares, mono, slate

# 工具设置
tools:
  web_search: parallel            # 搜索引擎: parallel, exa
  browser: false                  # 浏览器自动化
```

### 配置文件位置

| 平台 | 路径 |
|------|------|
| Linux | `umes-linux/hermes_home/` |
| Windows | `umes-windows\hermes_home\` |

所有配置、技能、会话记录都在 `hermes_home` 目录中，完全自包含。

---

## 支持的功能

Umes 包含完整的 Hermes Agent 功能：

| 功能 | 说明 |
|------|------|
| 💬 交互式聊天 | 终端里的 AI 对话 |
| 🔧 工具调用 | 终端命令、文件操作、网页搜索 |
| 🎯 技能系统 | 安装/创建/使用技能 |
| ⏰ 定时任务 | Cron 调度 |
| 🌐 Gateway | 连接 Telegram/Discord/Slack |
| 🖥️ 代码执行 | 安全沙箱执行 Python 代码 |
| 🌍 网页浏览 | 自动化浏览器操作 |
| 📝 文件操作 | 读写、搜索、编辑文件 |
| 🎨 图片生成 | AI 图片生成 |
| 🔊 TTS | 文字转语音 |

---

## 常见问题

### Q: 和直接装 Hermes 有什么区别？

功能完全一样。区别在于：
- **不需要装 Python** — 解压就能跑
- **不污染系统** — Python 和依赖都在包内
- **便携** — U盘带走，插哪用哪

### Q: 能装第三方技能吗？

能。技能装在 `hermes_home/skills/` 目录，跟着便携包走。

```bash
./start.sh skills install some-skill
```

### Q: 能连接 Telegram Bot 吗？

能。在 `.env` 里配置 `TELEGRAM_BOT_TOKEN`，然后运行：

```bash
./start.sh gateway
```

### Q: 更新怎么办？

下载新版本的 zip，解压后把旧的 `hermes_home` 目录复制过去即可。配置和数据都在这个目录里。

### Q: Linux 版能在 macOS 上跑吗？

目前只支持 Linux x86_64。macOS 版后续可能支持。

### Q: Windows 版提示"Windows 已保护你的电脑"？

点击"更多信息" → "仍要运行"。便携版 Python 来自 [python-build-standalone](https://github.com/astral-sh/python-build-standalone)，完全安全。

### Q: 磁盘空间不够怎么办？

可以删除不需要的文件减小体积：
- `python/lib/python3.11/test/` — 测试文件 (可删)
- `python/lib/python3.11/idlelib/` — IDLE (可删)
- `python/lib/python3.11/lib2to3/` — 2to3 工具 (可删)

---

## 构建说明

想自己打包？以下是构建流程。

### Linux 版 (PEX)

```bash
# 1. 安装 PEX
pip install pex

# 2. 下载便携 Python
curl -L -o python.tar.gz \
  "https://github.com/astral-sh/python-build-standalone/releases/latest/download/cpython-3.11-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
tar xzf python.tar.gz

# 3. 克隆 Hermes
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent

# 4. 构建 PEX
pex . -e hermes_cli.main:main -o ../hermes.pex --python ../python/bin/python3.11

# 5. 组装
mkdir -p portable/{hermes_home/skills,hermes_home/sessions}
mv python portable/
mv hermes.pex portable/
# 复制 start.sh, .env.example, config.yaml.example 到 portable/
```

### Windows 版 (Zipapp)

```bash
# 1. 下载便携 Python (Windows)
curl -L -o python-win.tar.gz \
  "https://github.com/astral-sh/python-build-standalone/releases/latest/download/cpython-3.11-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
tar xzf python-win.tar.gz -C python-windows --strip-components=1

# 2. 下载 Windows wheels
cd hermes-agent
pip download --platform win_amd64 --python-version 3.11 --only-binary=:all: -d ../win-wheels .
pip wheel --no-deps -w ../win-wheels .

# 3. 解压所有 wheel 并打包
cd ../win-wheels
for whl in *.whl; do python3 -m zipfile -e "$whl" ../win-app; done

# 4. 创建入口点
echo 'from hermes_cli.main import main; main()' > ../win-app/__main__.py

# 5. 打包为 zipapp
python3 -m zipapp ../win-app -o ../hermes-win.pyz -p "/usr/bin/env python3"

# 6. 组装
mkdir -p portable-win/{hermes_home/skills,hermes_home/sessions}
mv python-windows/* portable-win/python/
mv hermes-win.pyz portable-win/
# 复制 start.bat, .env.example, config.yaml.example 到 portable-win/
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| AI Agent | [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.9.0 |
| Python | [python-build-standalone](https://github.com/astral-sh/python-build-standalone) 3.11.15 |
| Linux 打包 | [PEX](https://github.com/pex-tools/pex) (Python EXecutable) |
| Windows 打包 | Python zipapp (.pyz) |
| LLM | Anthropic Claude / OpenAI GPT / OpenRouter |

---

## 许可证

MIT — 随便用，随便改。

Hermes Agent 由 [Nous Research](https://github.com/NousResearch) 开发。
