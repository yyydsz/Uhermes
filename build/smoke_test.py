#!/usr/bin/env python3
"""Uhermes 便携包「行为冒烟测试」—— 直接操作启动器，验证用户真实会遇到的路径。

与 build/verify.py 的分工：
  verify.py    ：结构自检（文件是否齐全、依赖是否属于目标平台、zip 权限位…）
  smoke_test.py：行为自检（真的去跑 start.bat/start.sh，检查首启、幂等、拦截、无外泄）

用法：
    python build/smoke_test.py dist/Uhermes-windows
    python build/smoke_test.py dist/Uhermes-windows.zip      # 先解压再测（用户真实路径）
    python build/smoke_test.py <某个解压出来的目录>

注意：只在本机平台与包目标平台一致时才会执行启动器；否则只报告并跳过。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

OK = "  ✓"
BAD = "  ✗"
SKIP = "  ⚠"


class Runner:
    def __init__(self, bundle: Path) -> None:
        self.bundle = bundle
        self.target = "windows" if (bundle / "python" / "python.exe").exists() else "linux"
        self.host = "windows" if os.name == "nt" else "linux"
        self.launcher = bundle / ("start.bat" if self.target == "windows" else "start.sh")
        self.stop_script = bundle / ("stop.bat" if self.target == "windows" else "stop.sh")
        self.home = bundle / "hermes_home"
        self.failures: list[str] = []
        self.checks = 0

    # -- helpers -----------------------------------------------------------
    def run(self, *args: str, timeout: int = 420) -> tuple[int, str]:
        """调用启动器。

        实测（见下）四种写法里只有"直接传 [bat 路径, 参数]"是稳的：
          ["cmd","/c",'"bat" "arg"']            ✗ cmd 首尾引号剥离规则，路径被当命令名
          ["cmd","/c",'""bat" "arg""']          ✗ subprocess 又把引号转义成 \\"
          f'cmd /c ""bat" "arg""' 字符串        ✓
          ["bat", "arg"] 直接传                 ✓  ← 采用这个，已验证含空格+中文路径可用
        包可能被解压到带空格甚至中文的目录（这是便携包的常见场景），所以引号不能省。
        """
        cmd = [str(self.launcher), *args]
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        env.pop("HERMES_HOME", None)  # 必须由包自己的启动器决定 HOME
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, env=env, cwd=str(self.bundle))
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            return 124, "(超时)"

    def check(self, cond: bool, label: str, detail: str = "") -> None:
        self.checks += 1
        if cond:
            print(f"{OK} {label}")
        else:
            print(f"{BAD} {label}" + (f"  [{detail}]" if detail else ""))
            self.failures.append(label)

    # -- checks ------------------------------------------------------------
    def _stash_configs(self) -> None:
        """备份并移走现有配置：首启测试需要"没有配置"的状态，但绝不能弄丢用户配置。"""
        self._stash: dict[str, bytes] = {}
        for name in (".env", "config.yaml"):
            p = self.home / name
            if p.is_file():
                self._stash[name] = p.read_bytes()
                try:
                    p.unlink()
                except OSError:
                    pass

    def _restore_configs(self) -> None:
        for name, data in getattr(self, "_stash", {}).items():
            try:
                (self.home / name).write_bytes(data)
            except OSError:
                pass
        if getattr(self, "_stash", None):
            print(f"  （已还原原有 {', '.join(self._stash)}）")

    def check_first_run(self) -> None:
        print("\n[首次运行]")
        rc, out = self.run("--version")
        self.check(rc == 0, f"启动器可运行（exit {rc}）", out.strip()[:120])
        self.check("Uhermes" in out and ".env" in out, "打印了中文首启引导")
        self.check((self.home / ".env").is_file(), "自动生成 hermes_home/.env")
        self.check((self.home / "config.yaml").is_file(), "自动生成 hermes_home/config.yaml")
        self.check("Hermes Agent v" in out, "输出真正的版本行",
                   next((l for l in out.splitlines() if "Hermes Agent v" in l), "")[:80])

    def check_idempotent(self) -> None:
        print("\n[重复运行（幂等）]")
        rc, out = self.run("--version")
        self.check(rc == 0, f"第二次运行正常（exit {rc}）")
        self.check("已为你生成配置文件骨架" not in out, "不再重复打印首启引导")

    def check_config(self) -> None:
        print("\n[配置读写]")
        rc, out = self.run("config", "get", "display.skin")
        self.check(rc == 0 and "default" in out, f"config get display.skin → {out.strip()[:40]}")

    def check_doctor(self) -> None:
        print("\n[体检]")
        rc, out = self.run("doctor")
        self.check("Python Environment" in out or "Hermes Doctor" in out, "doctor 可运行",
                   out.strip()[:120])

    def check_guards(self) -> None:
        print("\n[便携包护栏]")
        rc, out = self.run("update")
        self.check(rc == 2, f"`update` 被拦截（exit {rc}，期望 2）", out.strip()[:80])
        rc, out = self.run("gateway", "start")
        self.check(rc == 2, f"`gateway start` 被拦截（exit {rc}，期望 2）", out.strip()[:80])
        rc, out = self.run("gateway", "status")
        self.check(rc != 124, f"`gateway status` 放行（exit {rc}）", out.strip()[:80])

    def check_no_host_leak(self) -> None:
        print("\n[不污染宿主机]")
        created = [p for p in self._leak_paths if not self._leak_before.get(p, False) and p.exists()]
        self.check(not created, "本次运行未创建 ~/.hermes 或 %LOCALAPPDATA%\\hermes",
                   ", ".join(str(p) for p in created))

    def check_stop_script(self) -> None:
        print("\n[清理脚本]")
        if not self.stop_script.is_file():
            self.check(False, f"{self.stop_script.name} 存在")
            return
        self.check(True, f"{self.stop_script.name} 存在")
        try:
            # input="\n" 用于回答脚本结尾的 pause（Windows 与 Linux 都适用）
            p = subprocess.run([str(self.stop_script)], input="\n", capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=420, cwd=str(self.bundle))
            self.check(p.returncode == 0, f"清理脚本可运行（exit {p.returncode}）",
                       ((p.stdout or "") + (p.stderr or "")).strip()[:120])
        except subprocess.TimeoutExpired:
            self.check(False, "清理脚本可运行", "超时")

    # -- entry -------------------------------------------------------------
    def run_all(self) -> int:
        print(f"冒烟测试 {self.bundle}")
        print(f"  目标平台={self.target}  本机平台={self.host}")
        if self.target != self.host:
            print(f"{SKIP} 本机无法运行 {self.target} 包的启动器，跳过全部行为检查")
            print("     （请在对应平台上重跑，或仅用 build/verify.py 做结构检查）")
            return 0
        if not self.launcher.is_file():
            print(f"{BAD} 找不到启动器 {self.launcher}")
            return 2

        # 记录测试前宿主机是否已存在这些目录：只报"本次新建的"，不误伤既有安装
        self._leak_paths = [Path.home() / ".hermes"]
        appdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            self._leak_paths.append(Path(appdata) / "hermes")
        self._leak_before = {p: p.exists() for p in self._leak_paths}

        # 首启测试需要"无配置"状态：先备份用户配置，结束时还原
        self._stash_configs()
        try:
            self.check_first_run()
            self.check_idempotent()
            self.check_config()
            self.check_doctor()
            self.check_guards()
            self.check_no_host_leak()
            self.check_stop_script()
        finally:
            self._restore_configs()

        print("\n" + "=" * 58)
        if self.failures:
            print(f"结果：{len(self.failures)}/{self.checks} 项失败")
            for f in self.failures:
                print(f"  ✗ {f}")
            return 1
        print(f"结果：全部通过（{self.checks} 项检查）")
        return 0


def materialize(target: Path, workdir: Path) -> Path:
    """支持直接传 zip：解压到工作区临时目录后返回包目录（模拟用户真实路径）。"""
    if target.is_dir():
        return target
    if target.suffix == ".zip" and target.is_file():
        dest = workdir / "smoke-extract"
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
        print(f"解压 {target.name} → {dest}（这一步比较慢，U 盘上尤其明显）")
        with zipfile.ZipFile(target) as zf:
            zf.extractall(dest)
        inner = [p for p in dest.iterdir() if p.is_dir()]
        return inner[0] if len(inner) == 1 else dest
    raise SystemExit(f"路径不存在或不是目录/zip：{target}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Uhermes 便携包行为冒烟测试")
    ap.add_argument("target", help="便携包目录，或 dist/Uhermes-windows.zip")
    ap.add_argument("--keep", action="store_true", help="保留解压出来的临时副本（默认删除）")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    workdir = repo / "build" / "_cache" / "smoke"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        bundle = materialize(Path(args.target).resolve(), workdir)
        rc = Runner(bundle).run_all()
    finally:
        if not args.keep:
            shutil.rmtree(workdir / "smoke-extract", ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
