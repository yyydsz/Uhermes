"""Uhermes 便携包启动引导（Windows / Linux 共用）。

职责很小，但要解决 4 件事：
1. 把便携包内的源码树加入 sys.path —— 不用 venv、不用 editable 安装，
   因为 venv 的 `pyvenv.cfg`/exe trampoline 会把绝对解释器路径写死，
   换盘符或换机器就失效；而 editable 安装的 `.pth` 同样是绝对路径。
   源码树入 sys.path 后，上游 `PROJECT_ROOT = Path(__file__).parent.parent`
   依然解析到 hermes-agent/，skills/、web/、ui-tui/ 等非打包目录都能找到。
2. 首次运行时补齐配置骨架（与官方安装器行为一致）。
3. 屏蔽 `hermes update` —— 便携包的依赖装在自带 Python 里，
   源码树一旦被就地替换就会与依赖版本脱节。更新请下载新的便携包。
   高级用户可设 UHERMES_ALLOW_SELF_UPDATE=1 自行承担风险。
4. 把中文提示输出成正确的 UTF-8（.bat/.sh 本体保持 ASCII，避免代码页问题）。
"""

from __future__ import annotations

import os
import shutil
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
    if os.environ.get("UHERMES_ALLOW_SELF_UPDATE", "").strip() in {"1", "true", "yes"}:
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

    from hermes_cli.main import main as hermes_main

    sys.argv = ["hermes", *argv]
    code = hermes_main()
    return int(code) if isinstance(code, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
