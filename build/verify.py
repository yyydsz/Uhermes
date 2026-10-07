#!/usr/bin/env python3
"""Uhermes 便携包结构自检。

构建完（或拿到别人的包）之后跑一次，确认它不是"看起来有文件、实际跑不起来"的残缺包。
本机平台与包目标平台一致时，还会真正启动解释器与 hermes CLI 做冒烟测试。

用法：
    python build/verify.py dist/Uhermes-windows
    python build/verify.py dist/Uhermes-linux --run     # 强制尝试运行
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

# Windows 控制台默认是 GBK（cp936），直接打印 "✓/✗" 会 UnicodeEncodeError。
# 强制 UTF-8 输出，任何终端下都能正常显示。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

OK = "  ✓"
BAD = "  ✗"
WARN = "  ⚠"


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"{OK} {msg}")

    def bad(self, msg: str) -> None:
        print(f"{BAD} {msg}")
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        print(f"{WARN} {msg}")
        self.warnings.append(msg)

    def check(self, cond: bool, msg: str, *, warn_only: bool = False) -> bool:
        if cond:
            self.ok(msg)
        elif warn_only:
            self.warn(msg)
        else:
            self.bad(msg)
        return cond


def detect_target(bundle: Path) -> str:
    exe = bundle / "python" / "python.exe"
    return "windows" if exe.exists() else "linux"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", help="便携包目录")
    ap.add_argument("--run", action="store_true", help="即使平台不匹配也尝试运行")
    args = ap.parse_args()

    bundle = Path(args.bundle).resolve()
    rep = Report()
    print(f"检查 {bundle}\n")

    if not bundle.is_dir():
        print(f"{BAD} 目录不存在")
        return 2

    target = detect_target(bundle)
    print(f"[目标平台] {target}\n")

    # --- 1. 顶层文件 ---
    print("[顶层结构]")
    rep.check((bundle / "VERSION.txt").is_file(), "VERSION.txt")
    rep.check((bundle / "hermes_boot.py").is_file(), "hermes_boot.py")
    launcher = bundle / ("start.bat" if target == "windows" else "start.sh")
    rep.check(launcher.is_file(), launcher.name)
    if target == "linux":
        data = launcher.read_bytes()
        rep.check(b"\r\n" not in data, "start.sh 无 CRLF（否则 Linux 上 bad interpreter）")
        rep.check(data.startswith(b"#!"), "start.sh 有 shebang")

    # --- 2. 便携解释器 ---
    print("\n[便携解释器]")
    py = bundle / ("python/python.exe" if target == "windows" else "python/bin/python3.11")
    rep.check(py.is_file(), str(py.relative_to(bundle)))
    site = bundle / ("python/Lib/site-packages" if target == "windows"
                     else "python/lib/python3.11/site-packages")
    rep.check(site.is_dir(), str(site.relative_to(bundle)))
    if site.is_dir():
        pkgs = [p for p in site.iterdir() if p.is_dir()]
        rep.check(len(pkgs) > 100, f"site-packages 含 {len(pkgs)} 个包目录")
        native = list(site.rglob("*.pyd" if target == "windows" else "*.so"))
        wrong = list(site.rglob("*.so" if target == "windows" else "*.pyd"))
        rep.check(len(native) > 0, f"原生扩展 {len(native)} 个（.{'pyd' if target == 'windows' else 'so'}）")
        rep.check(not wrong, f"没有错平台的扩展（找到 {len(wrong)} 个）")
    if target == "linux":
        # bin/python3 在 PBS 归档里是符号链接/硬链接，Windows 上构建时需要补齐
        rep.check((bundle / "python/bin/python3").exists(),
                  "python/bin/python3 存在（链接条目已补齐）", warn_only=True)

    # --- 3. 源码树 ---
    print("\n[上游源码树]")
    tree = bundle / "hermes-agent"
    rep.check((tree / "hermes_cli" / "main.py").is_file(), "hermes_cli/main.py")
    rep.check((tree / "pyproject.toml").is_file(), "pyproject.toml")
    rep.check((tree / "skills").is_dir(), "skills/（内置技能）")
    rep.check((tree / ".env.example").is_file(), ".env.example（参考用）")
    rep.check(not (tree / ".git").exists(), "没有 .git（便携包不携带版本库）")
    for pruned in ("tests", "website", "apps", "evals", ".github"):
        rep.check(not (tree / pruned).exists(), f"已裁掉 {pruned}/", warn_only=True)

    # --- 4. 数据目录与模板 ---
    print("\n[hermes_home]")
    home = bundle / "hermes_home"
    rep.check(home.is_dir(), "hermes_home/")
    rep.check((home / ".env.example").is_file(), ".env.example")
    rep.check((home / "config.yaml.example").is_file(), "config.yaml.example")
    ref = home / "reference"
    rep.check((ref / "env.full.example").is_file(), "reference/env.full.example")
    rep.check((ref / "config.full.example").is_file(), "reference/config.full.example")
    for name in ("skills", "sessions", "logs"):
        rep.check((home / name).is_dir(), f"hermes_home/{name}/", warn_only=True)

    # --- 5. 版本一致性 ---
    print("\n[版本]")
    version_txt = bundle / "VERSION.txt"
    if version_txt.is_file():
        for line in version_txt.read_text(encoding="utf-8").splitlines():
            if ":" in line and not line.startswith(" "):
                print(f"      {line}")

    # --- 6. 冒烟运行 ---
    host = "windows" if os.name == "nt" else "linux"
    print("\n[冒烟测试]")
    if host != target and not args.run:
        rep.warn(f"本机是 {host}，无法运行 {target} 包的解释器（仅做了结构检查）")
    elif py.is_file():
        try:
            out = subprocess.run([str(py), "--version"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=120)
            rep.check(out.returncode == 0, f"解释器可运行：{(out.stdout or out.stderr).strip()}")
        except Exception as exc:
            rep.bad(f"解释器启动失败：{exc}")
        boot = bundle / "hermes_boot.py"
        if boot.is_file():
            env = {**os.environ,
                   "HERMES_HOME": str(home),
                   "PYTHONPATH": str(tree),
                   "PYTHONNOUSERSITE": "1",
                   "PYTHONUTF8": "1"}
            try:
                out = subprocess.run([str(py), str(boot), "--version"],
                                     capture_output=True, text=True,
                                     encoding="utf-8", errors="replace",
                                     timeout=300, env=env)
                text = (out.stdout or "") + (out.stderr or "")
                first = next((l for l in text.splitlines() if "Hermes Agent" in l), "").strip()
                rep.check(out.returncode == 0 and bool(first),
                          f"hermes CLI 可运行：{first or text.strip()[:160]}")
            except Exception as exc:
                rep.bad(f"hermes CLI 启动失败：{exc}")

    # --- 7. zip 权限位（仅 Linux 包） ---
    if target == "linux":
        zpath = bundle.with_suffix(".zip")
        if zpath.is_file():
            print("\n[zip 权限位]")
            with zipfile.ZipFile(zpath) as zf:
                want = [f"{bundle.name}/start.sh", f"{bundle.name}/python/bin/python3.11"]
                for name in want:
                    try:
                        mode = (zf.getinfo(name).external_attr >> 16) & 0o777
                    except KeyError:
                        rep.warn(f"zip 内缺少 {name}")
                        continue
                    rep.check(mode & 0o111 != 0, f"{name} 在 zip 内可执行（{oct(mode)}）")

    print("\n" + "=" * 58)
    if rep.failures:
        print(f"结果：{len(rep.failures)} 项失败，{len(rep.warnings)} 项警告")
        for f in rep.failures:
            print(f"  ✗ {f}")
        return 1
    print(f"结果：全部通过（{len(rep.warnings)} 项警告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
