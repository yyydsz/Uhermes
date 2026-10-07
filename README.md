<div align="center">

# Uhermes

<p align="center">
  <img src="assets/umes-hero.gif" alt="Uhermes Hero Animation" />
</p>

> *「插上U盘，走到哪，Agent跟到哪」*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-v0.21.5-green.svg)](https://github.com/NousResearch/hermes-agent)
[![Python 3.11](https://img.shields.io/badge/Python-3.11.17-blue.svg)](https://www.python.org/)

**U盘里的 AI Agent。解压即用，不装 Python，不配环境。**

[这是什么](#这是什么) · [快速开始](#快速开始) · [目录结构](#目录结构) · [配置](#配置) · [常见问题](#常见问题) · [构建](#构建) · [技术说明](#技术说明)

</div>

---

## 这是什么

Uhermes（**U**SB + **Hermes**）是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的便携打包版：把便携 Python、Hermes 本体、以及全部依赖装进一个目录，解压后双击就能跑，全部数据（配置、会话、技能、记忆）都留在这个目录里，跟着 U 盘走。

**当前钉定的上游版本：[Hermes Agent v0.21.5](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.9.24)（tag `v2026.9.24`，commit `f97608f`，2026-09-24 发布）。**

> 上一版 Umes 钉的是 v0.9.0，本次已跨 12 个 minor 升级并重做打包方式 —— 因为 v0.21.x 的 Hermes 已经不是当年那个 `pip install` 就能打 PEX 的项目了，详见[技术说明](#技术说明)。

**适用场景：**
- U 盘随身携带，插到任何 Windows / Linux x86_64 电脑上就能用
- 不想在公司/学校机器上装 Python 或污染系统环境
- 临时借用别人的电脑
- 需要一套「完全自包含、可整体拷走」的 Agent 环境

---

## 快速开始

### 1. 解压

把 `Uhermes-windows.zip`（或 `Uhermes-linux.zip`）解压到任意位置 —— U 盘、桌面、D 盘都行。

> **别放在压缩包里直接运行**，必须先解压。含空格与中文的路径实测可用（启动器全程加引号，`PYTHONUTF8=1`），但个别第三方工具仍可能对非 ASCII 路径不友好。

### 2. 启动

```bash
# Linux
chmod +x start.sh python/bin/*        # 从 FAT/exFAT U盘解压时执行权限会丢
./start.sh

# Windows
双击 start.bat
```

首次启动会自动在 `hermes_home/` 里生成 `.env` 与 `config.yaml` 骨架，并打印一段中文引导。

### 3. 配置模型（至少一种方式）

**方式 A —— 什么都不填**：Hermes 内置免费额度与登录流程。启动后在对话里输入 `/login` 按提示走。

**方式 B —— 交互式向导（推荐）**：

```bash
./start.sh setup          # Windows: start.bat setup
```

**方式 C —— 手工填一个密钥**：编辑 `hermes_home/.env`，取消下面任意一行的注释并填入密钥：

```env
OPENROUTER_API_KEY=sk-or-xxx     # 一个密钥用遍各家模型，最省事
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GLM_API_KEY=xxx                  # 智谱，国内可直连
KIMI_API_KEY=xxx                 # 月之暗面
```

> `.env` 里**只放密钥**。模型、界面、终端等一切设置都写在 `config.yaml`（这是上游 Hermes 的硬规则）。

### 4. 开始用

```bash
./start.sh                       # 交互式对话
./start.sh "帮我写个备份脚本"      # 单次提问
./start.sh --help                # 全部命令（v0.21.5 有 70+ 个子命令）
./start.sh setup                 # 配置向导
./start.sh model                 # 切换模型
./start.sh skills                # 管理技能
./start.sh gateway               # 接入 Telegram / Discord / Slack
./start.sh cron                  # 定时任务
./start.sh logs                  # 看日志（agent.log / errors.log）
./start.sh doctor                # 体检：环境、依赖、配置
```

---

## 目录结构

```
Uhermes-windows/  (或 Uhermes-linux/)
├── start.bat / start.sh   启动器：设置全部环境变量后调用 hermes_boot.py
├── hermes_boot.py         启动引导：装配置骨架、拦自更新、进入 Hermes CLI
├── VERSION.txt            本包钉定的版本与构建信息
├── python/                便携 CPython 3.11.17（可搬迁：前缀由自身位置推导）
│   └── Lib/site-packages/ 所有第三方依赖装在这里
├── hermes-agent/          上游 Hermes 源码树（已裁剪，v0.21.5）
├── hermes_home/           你的全部数据都在这里，备份/迁移只需拷这个目录
│   ├── .env               密钥（首次启动自动生成）
│   ├── config.yaml        设置（首次启动自动生成）
│   ├── .env.example       密钥模板（带中文注释）
│   ├── config.yaml.example 设置模板（带中文注释，全部为注释状态）
│   ├── reference/         上游完整配置参考，离线可查
│   │   ├── env.full.example      上游 .env.example 原文（137 个键）
│   │   └── config.full.example   上游 config 示例全文（约 2300 行 / 80 个配置段）
│   ├── skills/            技能（内置技能在 hermes-agent/skills/，这里放你自己装的）
│   ├── sessions/          会话记录
│   ├── memories/          长期记忆
│   ├── logs/              agent.log / errors.log
│   ├── cron/              定时任务
│   ├── lazy-deps/         按需安装的可选依赖（跟着 U 盘走）
│   └── state.db           会话数据库（SQLite）
└── bin/                   可选：随包的 uv（用 --with-uv 构建时才有）
```

**备份或换机**：只拷 `hermes_home/` 就够了（前提是新包的 Hermes 版本不低于旧包）。

---

## 配置

### 三个入口，按需选

| 方式 | 命令 | 说明 |
|---|---|---|
| 交互向导 | `./start.sh setup` | 首次使用推荐，自动写 `.env` + `config.yaml` |
| 命令行改单项 | `./start.sh config set display.skin ares` | 会保留配置文件里的注释与键序 |
| 直接编辑 | 打开 `hermes_home/config.yaml` | 有中文注释模板可选，改完下次启动生效 |

### 便携场景值得改的几项

```yaml
# U盘是 exFAT/FAT32、或放在网络盘上时：WAL 模式需要可靠的文件锁，
# 建议改成 delete，否则 SQLite 可能报 WAL 不兼容。
database:
  journal_mode: "delete"

# 限制日志体积，减少 U盘写入
logging:
  max_size_mb: 5
  backup_count: 3

# 旧会话自动清理，避免 U盘被慢慢占满
sessions:
  auto_prune: true
  retention_days: 90

# 便携包不能就地自更新，关掉更新检查可避免每次启动联网
updates:
  check: false

# 界面语言与主题
display:
  skin: "default"        # default / ares / mono / slate
  language: "zh"
```

完整键表见 `hermes_home/reference/config.full.example`（离线，无需联网）。

---

## 常见问题

### Q: 怎么更新到新版本？

下载新版 Uhermes 便携包，解压后把你旧的 `hermes_home/` 整个复制过去即可（配置、会话、技能、记忆都在里面）。

**`hermes update` 在便携包里被有意禁用**。原因是便携包的依赖装在自带的 `python/` 里，而上游的 `hermes update` 会就地替换源码树 —— 换完之后依赖版本与新代码不匹配，会出现难以排查的故障。启动器会拦住这个命令并提示正确做法。确实想冒险可以设 `UHERMES_ALLOW_SELF_UPDATE=1`。

### Q: 体积为什么比上一版大这么多？

因为上游 Hermes 从 v0.9.0 长到 v0.21.5 已经是另一个量级的项目：Desktop 插件 SDK、Web dashboard、TUI、约 20 个消息平台适配器、插件目录、几十个 provider。而且它不再发布 wheel，只能带着源码树跑。构建时已裁掉 `tests/`、`website/`、`apps/`（Electron 桌面端）、`evals/` 等约 113 MB 非运行时内容。

实测（Windows x86_64，`--extras all`）：

| 部分 | 解压后 | 说明 |
|---|---|---|
| `python/` | 317 MB | 便携解释器 + 318 个依赖包 |
| `hermes-agent/` | 64 MB | 上游源码树（已从 178 MB 裁剪到 64 MB） |
| `hermes_home/` | < 1 MB | 初始只有模板，用起来才增长 |
| **合计** | **400 MB** | zip 压缩后 **125 MB** |

想要更小：构建时用 `--extras core`（核心依赖从 318 个包降到 173 个，消息平台/语音等改为首次使用时按需下载）。

### Q: `hermes doctor` 报 "Not in virtual environment" / "python-telegram-bot (optional, not installed)"，要紧吗？

都不要紧，这是便携包的设计结果：

- **Not in virtual environment**：便携包刻意不用 venv（原因见[技术说明](#为什么不用-venv)），依赖直接装在自带解释器里。doctor 只是提示「这不是标准 venv 布局」。
- **python-telegram-bot / discord.py 未安装**：上游 `[all]` 这个 extra 有意不含消息平台依赖，它们在首次使用对应平台时按需安装（见下一条）。core 与 all 两种构建都是这个行为。
- **`hermes --version` 显示 `Install method: unknown`**：也是预期的 —— 便携包没有 `.git`，不冒充官方安装形态。

### Q: 哪些功能需要额外装 Node.js？

Python 运行时**不需要** Node。以下功能需要系统里已有 Node.js（包内不带）：

| 功能 | 说明 |
|---|---|
| `hermes --tui` | Ink 终端界面，需要 `ui-tui/` 构建产物 |
| `hermes dashboard` | Web 面板 |
| 浏览器自动化工具 | 走 `npx agent-browser` |
| WhatsApp 桥接 | 需要 `node_modules` |

基础对话、工具调用、技能、cron、Telegram/Discord/Slack 网关都不需要 Node。

### Q: 首次用到某些功能时提示要下载依赖？

那是 Hermes 的「懒加载依赖」机制：消息平台、语音、云记忆等可选后端不在默认依赖里，首次使用时按需安装。便携包已把它指向 `hermes_home/lazy-deps/`，装的东西跟着 U 盘走，不会污染宿主机。

- 需要联网 + `uv`。用 `--with-uv` 构建的包自带 uv，否则 Hermes 会尝试下载一个。
- 完全离线或只读介质：在 `config.yaml` 里设 `security.allow_lazy_installs: false` 关掉。

### Q: Windows 提示「Windows 已保护你的电脑」？

点「更多信息」→「仍要运行」。便携 Python 来自 [python-build-standalone](https://github.com/astral-sh/python-build-standalone)（astral-sh 官方构建），Hermes 来自 Nous Research 官方仓库，构建过程只下载预编译 wheel、不编译任何东西。

### Q: 从 U 盘直接跑有什么注意事项？

- **文件系统**：exFAT/FAT32 没有 POSIX 权限与可靠文件锁 —— Linux 下先 `chmod +x start.sh python/bin/*`，并把 `database.journal_mode` 设为 `delete`。追求稳定建议把包放 U 盘、数据目录放本地盘（改 `HERMES_HOME` 环境变量指向本地目录即可）。
- **运行中别拔盘**：SQLite 与正在写的日志会受损。
- **NTFS U 盘**在 Windows 上表现最好；Linux 上需要 `ntfs-3g`。

### Q: 能装第三方技能吗？

能。`./start.sh skills` 走官方技能管理，技能落在 `hermes_home/skills/`，跟着便携包走。也可以用 `skills.external_dirs` 指向 U 盘上的共享技能目录，多个便携包复用同一份技能。

### Q: 和直接装 Hermes 有什么区别？

功能一致（同一个上游版本），差别在于：

| | 官方安装 | Uhermes 便携包 |
|---|---|---|
| 位置 | `~/.hermes` + `%LOCALAPPDATA%` | 全在解压出来的目录里 |
| 依赖管理 | git checkout + venv + uv sync | 自带 Python + 预装依赖，无 venv |
| 自更新 | `hermes update` | 不支持，换新包 + 拷 `hermes_home` |
| 写注册表/环境变量 | Windows 安装器会写 | 完全不写 |
| 换机 | 重新安装 | 拷目录 |

---

## 构建

### 依赖

- Python 3.9+（只用来跑构建脚本）
- [uv](https://docs.astral.sh/uv/)（解析并安装依赖）
- 能访问 `github.com` 与 `pypi.org`
- **不需要 git**，**不需要目标平台的工具链**（全部使用预编译 wheel，不编译任何东西）

### 命令

```bash
# Windows 便携包
pwsh -File build/build-windows.ps1

# Linux 便携包（在 Linux 上）
./build/build-linux.sh

# 在 Windows 上交叉构建 Linux 包（无法在本机验证，见下）
pwsh -File build/build-windows.ps1 -Platform all -Cross

# 直接调用构建器
python build/build.py --platform windows --extras all
python build/build.py --platform linux   --extras core --with-uv
python build/build.py --check            # 查上游有没有新版本
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--platform windows\|linux\|all` | 目标平台 |
| `--extras all\|core\|a,b` | `all`=全部可选依赖（默认）；`core`=仅核心；也可写具体 extra 名 |
| `--cross` | 允许产出非当前主机的包（依赖 wheel 解析，本机跑不起来） |
| `--with-uv` | 把 uv 二进制也打进包，让懒加载依赖开箱可用 |
| `--out` / `--cache` | 产物目录（默认 `dist/`）/ 缓存目录（默认 `build/_cache/`） |
| `--no-zip` | 只出目录，不压 zip |
| `--check` | 只检查上游版本，不构建 |

产物：`dist/Uhermes-windows/`、`dist/Uhermes-linux/`，以及同名 `.zip`。

### 自检

构建完（或拿到别人给的包）之后跑一次结构自检。本机平台与包目标平台一致时，它还会真正启动解释器并运行 `hermes --version`：

```bash
python build/verify.py dist/Uhermes-windows
python build/verify.py dist/Uhermes-linux
```

检查内容：启动器（含 CRLF 检查，避免 Linux 上 `bad interpreter`）、便携解释器、site-packages 里原生扩展是否属于目标平台（Windows 应见 `.pyd`、Linux 应见 `.so`，出现错平台扩展直接判失败）、源码树关键文件、配置模板与离线参考、以及 Linux zip 内 `start.sh` 与 `python/bin/*` 的可执行位。

### 升级到新的上游版本

只改一个文件 —— `versions.env`：

```env
HERMES_VERSION=0.21.5
HERMES_TAG=v2026.9.24
HERMES_COMMIT=f97608f178d1ffeca59860195ab7da295f7c8e5f
PYTHON_VERSION=3.11.17          # 需满足上游 requires-python >=3.11,<3.14
PBS_RELEASE=20261003
```

然后重新构建。构建器按版本号自动使用全新的 stage 目录，不会复用旧源码树。

### 交叉构建的边界

`--cross` 在 Windows 上构建 Linux 包时，走的是 `uv pip install --python-platform x86_64-unknown-linux-gnu --target ...` —— 只解析并铺开 Linux wheel，**无法在本机运行验证**。如果某个依赖在目标平台没有 wheel，构建会在安装阶段直接报错（而不是产出一个坏包）。要在发布前确认，请在真实 Linux 机器上跑一次 `./build/build-linux.sh`。

---

## 技术说明

### 为什么不用 PEX / zipapp 了

v0.9.0 时代的做法是 `pex . -e hermes_cli.main:main`（Linux）与 `python -m zipapp`（Windows）。到 v0.21.5 这条路已经走不通：

1. **上游不再发布可安装的包**：`setup.py` 主动拦截 `bdist_wheel`/`sdist`（只有 `HERMES_NIX_BUILD=1` 放行）；官方安装器是「git clone → 建 venv → `uv sync`」。也就是说 `pip install hermes-agent` 拿不到东西。
2. **大量非包内资源**：`skills/`、`optional-skills/`、`plugin-catalog/`、`web/`、`ui-tui/` 都不在 `packages.find` 里，代码按「源码树相对路径」或环境变量去找它们。打成 wheel/zipapp 后这些目录会丢，技能与面板随之失效。
3. **原生依赖变多**：`pydantic-core`、`Pillow`、`pillow-heif`、`cryptography`、`websockets`、`httptools`、`watchfiles`、`psutil`，Windows 上还有 `pywinpty`/`pywin32`/`tzdata`。PEX 打包这些既脆弱又难验证。

所以便携包改成「**自带解释器 + 上游源码树 + 依赖装进自带解释器**」的形态，和官方安装的语义一致，只是把「检查点 + venv」换成了「内置目录 + PYTHONPATH」。

### 为什么不用 venv

因为 venv 与「可搬迁」天然冲突：

- `pyvenv.cfg` 里的 `home` 是**绝对路径**，解析的是创建时的那个解释器位置；
- Windows 上 `Scripts\python.exe` 是 exe trampoline，内嵌绝对解释器路径（上游自己的安装器也踩过这个坑，所以它在 `relocatable=true` 时才改用 `.cmd` 委托器）；
- editable 安装生成的 `.pth` 同样是绝对路径。

U 盘换台机器就可能变成 `E:` → `F:`，这些路径全部失效。本方案改成：

- 便携解释器用 [python-build-standalone](https://github.com/astral-sh/python-build-standalone) 的 `install_only` 构建，**前缀由自身位置推导**，整体搬走不会坏；
- 依赖直接装进 `python/Lib/site-packages`（Windows）或 `python/lib/python3.11/site-packages`（Linux），路径同样是相对的；
- 源码树由启动器在运行时加入 `PYTHONPATH`，不生成任何写死路径的 `.pth`、不使用 console script shim。

### 启动器设置了什么

| 变量 | 值 | 为什么 |
|---|---|---|
| `HERMES_HOME` | `<包>/hermes_home` | 所有数据留在包内，不碰 `~/.hermes` 或 `%LOCALAPPDATA%` |
| `PYTHONPATH` | `<包>/hermes-agent` | 让源码树可导入，替代 venv/editable 安装 |
| `HERMES_LAZY_INSTALL_TARGET` | `<包>/hermes_home/lazy-deps` | 按需安装的可选依赖也留在包内 |
| `UV_CACHE_DIR` / `UV_PYTHON_INSTALL_DIR` | 包内 | Hermes 调 uv 时不要把缓存写到用户目录 |
| `PYTHONNOUSERSITE=1` | 1 | 不加载宿主机的用户级 site-packages，保证行为可复现 |
| `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` | utf-8 | Windows 中文路径与中文输出 |
| `PATH` 前缀 | `<包>/bin` | 用 `--with-uv` 构建时让包内 uv 优先 |

### 被裁掉的部分

`build/prune.txt` 里逐条列出，均为 Python 运行时不需要的内容：`.git`、`.github`、`tests/`、`tests-js/`、`evals/`、`website/`、`contributors/`、`docker/`、`nix/`、`native/`、`apps/`（Electron 桌面端源码，39 MB）。裁掉 `apps/` 后 `hermes desktop` 类命令不可用；CLI、TUI 后端、gateway、dashboard、技能都不受影响。

### 版本钉定一览

| 组件 | 版本 | 来源 |
|---|---|---|
| Hermes Agent | 0.21.5（`v2026.9.24` / `f97608f`） | NousResearch/hermes-agent |
| Python | 3.11.17 `install_only_stripped` | astral-sh/python-build-standalone `20261003` |
| 依赖 | 由上游 `uv.lock` 精确导出 | 与上游发布时锁定的版本一致 |

上游要求 `requires-python = ">=3.11,<3.14"`，其 `.python-version` 指向 3.11 —— 便携包跟随官方选择。

---

## 许可证

MIT —— 随便用，随便改。

Hermes Agent 由 [Nous Research](https://github.com/NousResearch) 开发，同样以 MIT 发布；便携包内 `hermes-agent/LICENSE` 为其原始许可证。
