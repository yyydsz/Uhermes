"""Uhermes 便携包启动引导（Windows / Linux 共用）。

职责：
1. 把便携包内的源码树加入 sys.path —— 不用 venv、不用 editable 安装，
   因为 venv 的 `pyvenv.cfg`/exe trampoline 会把绝对解释器路径写死，
   换盘符或换机器就失效；而 editable 安装的 `.pth` 同样是绝对路径。
   源码树入 sys.path 后，上游 `PROJECT_ROOT = Path(__file__).parent.parent`
   依然解析到 hermes-agent/，skills/、web/、ui-tui/ 等非打包目录都能找到。
2. 首次运行时补齐配置骨架（与官方安装器行为一致）。
3. 屏蔽 `hermes update` —— 便携包的依赖装在自带 Python 里，
   源码树一旦被就地替换就会与依赖版本脱节。更新请下载新的便携包。
   高级用户可设 UHERMES_ALLOW_SELF_UPDATE=1 自行承担风险。
4. **gateway 策略**：便携包默认不在宿主机上留下任何开机自启。
   实测（v0.21.5）：`gateway run` 是真正的前台运行，关掉窗口即随之退出，且不会
   安装自启；而 `gateway start/install/restart/setup` 会在宿主机注册计划任务
   （Windows，失败时退化为启动文件夹里的 VBS）、systemd user unit（Linux）或
   LaunchAgent（macOS），其路径指向 U 盘 —— 只要盘插着、用户又登录，gateway
   就会自己起来把盘占住，导致「关了窗口也拔不掉 U 盘」。
   因此这里默认拦下这四个子命令，并在退出时清理已存在的自启残留；
   确实需要常驻的人可以显式设置 UHERMES_ALLOW_GATEWAY_SERVICE=1 放行。
5. 把中文提示输出成正确的 UTF-8（.bat/.sh 本体保持 ASCII，避免代码页问题）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = HERE / "hermes-agent"
HOME = Path(os.environ.get("HERMES_HOME") or (HERE / "hermes_home"))

SKELETON = (
    "skills",
    "sessions",
    "logs",
    "cron",
    "memories",
    "pairing",
    "hooks",
    "image_cache",
    "audio_cache",
    "cache",
)

# 这些 gateway 子命令会在宿主机上安装/启用后台自启，便携包默认拒绝
GATEWAY_SERVICE_ACTIONS = {"start", "install", "restart", "setup"}
# 这些是前台运行或清理/诊断，任何时候都放行
GATEWAY_ALLOWED_ACTIONS = {"", "run", "stop", "uninstall", "status", "list"}


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_skeleton() -> None:
    for name in SKELETON:
        try:
            (HOME / name).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


def _seed(name: str, target: str) -> bool:
    """缺失时用模板补齐；返回是否新建。"""
    dst = HOME / target
    src = HOME / name
    if dst.exists() or not src.exists():
        return False
    try:
        shutil.copyfile(src, dst)
        return True
    except OSError:
        return False


def _first_run_banner(seeded_env: bool) -> None:
    if not seeded_env:
        return
    line = "=" * 58
    print(
        f"""
{line}
  Uhermes —— U盘里的 Hermes Agent（便携版）
{line}

  已为你生成配置文件骨架：

    {HOME / '.env'}
    {HOME / 'config.yaml'}

  `.env` 只放 API 密钥（密钥以外的设置都在 config.yaml）。
  下一步任选其一：

    1) 用向导配置：            hermes setup
    2) 只填一个密钥就能跑：    编辑 .env，填 OPENROUTER_API_KEY 或
                              ANTHROPIC_API_KEY 或 OPENAI_API_KEY
    3) 不填密钥也能启动：      hermes 支持免费额度 / 登录（/login）

  完整配置参考（离线可查）：
    hermes_home/reference/env.full.example
    hermes_home/reference/config.full.example

{line}
""",
        flush=True,
    )


def _block_self_update(argv: list[str]) -> None:
    if _truthy("UHERMES_ALLOW_SELF_UPDATE"):
        return
    if not argv or argv[0] not in {"update", "upgrade"}:
        return
    print(
        "\n".join(
            [
                "",
                "  ✗ 便携包不支持 `hermes update`。",
                "",
                "    原因：便携包的依赖装在自带的 Python 里，源码树被就地替换后",
                "    会与已安装的依赖版本脱节，产生难以排查的故障。",
                "",
                "    更新方式：下载新版 Uhermes 便携包，解压后把她的 hermes_home/",
                "    目录整个复制过去（配置、会话、技能都在那里）。",
                "",
                "    临时绕过（自行承担风险）：设置 UHERMES_ALLOW_SELF_UPDATE=1",
                "",
            ]
        ),
        flush=True,
    )
    raise SystemExit(2)


def _host_autostart_entries() -> list[Path]:
    """宿主机上指向 hermes gateway 的开机自启项（各平台落点由上游代码决定）。"""
    found: list[Path] = []
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        startup = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup.is_dir():
            found += sorted(startup.glob("Hermes_Gateway*.vbs"))
            found += sorted(startup.glob("Hermes_Gateway*.cmd"))
    try:
        user_systemd = Path.home() / ".config" / "systemd" / "user"
        if user_systemd.is_dir():
            found += sorted(user_systemd.glob("hermes-gateway*.service"))
        launch_agents = Path.home() / "Library" / "LaunchAgents"
        if launch_agents.is_dir():
            found += sorted(launch_agents.glob("ai.hermes.gateway*.plist"))
    except OSError:
        pass
    # 便携包内的服务脚本目录。注意必须按内容判断：上游在 stop/uninstall 之后
    # 会留下一个空的 gateway-service/ 目录，把"目录存在"当残留会造成每次都误报。
    service_dir = HOME / "gateway-service"
    try:
        if service_dir.is_dir() and any(service_dir.glob("Hermes_Gateway*")):
            found.append(service_dir)
    except OSError:
        pass
    return found


def _run_self(*args: str) -> int:
    """以子进程再入本脚本执行一个 hermes 子命令（避免在同进程里二次进入 CLI）。

    子进程带 UHERMES_GATEWAY_CLEANUP=1：清理本身调用的 stop/uninstall 退出时
    不得再触发一轮清理，否则会无限递归。
    """
    cmd = [sys.executable, str(Path(__file__).resolve()), *args]
    env = {**os.environ, "UHERMES_GATEWAY_CLEANUP": "1"}
    try:
        return subprocess.run(cmd, env=env, timeout=180).returncode
    except Exception:
        return 1


def _enforce_gateway_policy(argv: list[str]) -> None:
    """默认拦下会安装宿主机后台自启的 gateway 子命令。"""
    action = _gateway_action(argv)
    if action not in GATEWAY_SERVICE_ACTIONS or _truthy("UHERMES_ALLOW_GATEWAY_SERVICE"):
        return
    print(
        "\n".join(
            [
                "",
                f"  ✗ 便携包默认不执行 `hermes gateway {action}`。",
                "",
                "    原因：该命令会在**这台电脑**上注册开机自启（Windows 计划任务/启动",
                "    文件夹、Linux systemd user unit、macOS LaunchAgent），而路径指向你",
                "    的 U 盘。只要盘插着、你又登录系统，gateway 就会自己起来把盘占住，",
                "    于是「关掉窗口也拔不掉 U 盘」。",
                "",
                "    想在前台跑（关掉窗口即退出，不留任何自启）：",
                "        start.bat gateway run      # Windows",
                "        ./start.sh gateway run     # Linux",
                "",
                "    想清理已经留下的自启残留：",
                "        stop.bat                   # Windows",
                "        ./stop.sh                  # Linux",
                "",
                "    确实需要常驻后台服务（例如长期挂消息平台）：显式放行",
                "        set UHERMES_ALLOW_GATEWAY_SERVICE=1   # Windows",
                "        export UHERMES_ALLOW_GATEWAY_SERVICE=1  # Linux",
                "",
            ]
        ),
        flush=True,
    )
    raise SystemExit(2)


def _cleanup_gateway_leftovers() -> None:
    """退出时清理宿主机上的 gateway 自启残留（未显式放行时）。

    覆盖不了「直接叉掉窗口」的情况 —— 那时本进程被杀，收尾代码没有机会运行；
    那种情况请用 stop.bat / stop.sh。
    """
    if _truthy("UHERMES_ALLOW_GATEWAY_SERVICE") or _truthy("UHERMES_GATEWAY_CLEANUP"):
        return
    entries = _host_autostart_entries()
    if not entries:
        return
    print(
        f"\n  提示：检测到宿主机上仍有 {len(entries)} 项 gateway 自启残留，正在清理 …",
        flush=True,
    )
    _run_self("gateway", "stop")
    _run_self("gateway", "uninstall")
    left = _host_autostart_entries()
    if left:
        print("  ⚠ 仍有残留，请手动运行 stop.bat / stop.sh 查看细节。", flush=True)
    else:
        print("  ✓ 已清理，可以安全弹出 U 盘。", flush=True)


def _gateway_action(argv: list[str]) -> str:
    if not argv or argv[0] != "gateway":
        return ""
    if len(argv) > 1 and not argv[1].startswith("-"):
        return argv[1]
    return ""


def main() -> int:
    # 便携包的写入应当收敛在包内：关掉用户级 site-packages 干扰。
    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    # Windows 控制台 + 中文路径：让 Python 侧始终按 UTF-8 处理文本。
    os.environ.setdefault("PYTHONUTF8", "1")
    # 懒加载依赖（首次用到某能力时按需安装）落到便携包内，而不是系统目录。
    os.environ.setdefault("HERMES_LAZY_INSTALL_TARGET", str(HOME / "lazy-deps"))
    os.environ.setdefault("UV_CACHE_DIR", str(HOME / "cache" / "uv"))
    os.environ.setdefault("UV_PYTHON_INSTALL_DIR", str(HOME / "runtime"))
    os.environ["HERMES_HOME"] = str(HOME)

    sys.path.insert(0, str(TREE))

    _ensure_skeleton()
    seeded = _seed(".env.example", ".env")
    _seed("config.yaml.example", "config.yaml")
    _first_run_banner(seeded)

    argv = sys.argv[1:]
    _block_self_update(argv)
    _enforce_gateway_policy(argv)

    from hermes_cli.main import main as hermes_main

    sys.argv = ["hermes", *argv]
    try:
        code = hermes_main()
    finally:
        # gateway 前台运行结束后同样走这里；没有残留时是零成本的一次 glob。
        if _gateway_action(argv) in GATEWAY_ALLOWED_ACTIONS:
            _cleanup_gateway_leftovers()
    return int(code) if isinstance(code, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
