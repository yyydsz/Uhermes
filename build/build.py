#!/usr/bin/env python3
"""Uhermes 便携包构建器（Windows / Linux x86_64）。

设计原则
--------
* **只依赖 Python 3.9+ 与 uv**（uv 用于解析/安装依赖）。不需要 git、不需要 pip、
  不需要目标平台上的工具链 —— 因为不编译任何东西，全部使用预编译 wheel。
* **可复现**：上游 Hermes 按 tag 钉定（versions.env），Python 运行时按
  python-build-standalone 的 release 钉定，依赖从上游 uv.lock 精确导出。
* **可搬迁**：产物里没有 venv、没有 editable 的 .pth、没有写死的绝对路径。
  便携解释器靠自身位置推导 prefix，源码树靠启动器动态加入 PYTHONPATH。
  因此整个目录可以放 U 盘、换盘符、换机器。
* **不改上游代码**：裁剪只删文件，不 patch 任何 .py。

用法
----
    python build/build.py --platform windows
    python build/build.py --platform linux            # 在 Linux 上构建
    python build/build.py --platform linux --cross    # 在 Windows 上交叉构建
    python build/build.py --platform all
    python build/build.py --check                     # 查上游是否有新版本

产物
----
    dist/Uhermes-windows/   （或 Uhermes-linux/）
      start.bat | start.sh
      hermes_boot.py
      VERSION.txt
      python/               便携 CPython
      hermes-agent/         上游源码树（已裁剪）
      hermes_home/          .env.example / config.yaml.example / reference/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GH = "https://github.com"
PBS = f"{GH}/astral-sh/python-build-standalone/releases/download"
UV_RELEASES = f"{GH}/astral-sh/uv/releases/download"

PLATFORMS = {
    "windows": {
        "label": "windows",
        "triple_key": "TRIPLE_WINDOWS",
        "python_exe": "python.exe",
        "site_packages": "Lib/site-packages",
        "launcher": "windows/start.bat",
        "uv_asset": "uv-{v}-x86_64-pc-windows-msvc.zip",
    },
    "linux": {
        "label": "linux",
        "triple_key": "TRIPLE_LINUX",
        "python_exe": "bin/python3.11",
        "site_packages": "lib/python3.11/site-packages",
        "launcher": "linux/start.sh",
        "uv_asset": "uv-{v}-x86_64-unknown-linux-gnu.tar.gz",
    },
}


# --------------------------------------------------------------------------- #
# 基础设施
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def read_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (REPO / "versions.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def http_get(url: str, dest: Path, *, expect_bytes: bool = True, attempts: int = 3) -> Path:
    """下载到 dest（已存在且非空则跳过）。带完整性校验与重试 —— 慢速/不稳的网络下
    urllib 可能"正常结束"却只下到一半，必须比对 Content-Length。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"缓存命中 {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        return dest

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        tmp = dest.with_name(dest.name + ".part")
        tmp.unlink(missing_ok=True)
        log(f"下载 {url}" + (f"（第 {attempt}/{attempts} 次）" if attempt > 1 else ""))
        req = urllib.request.Request(url, headers={"User-Agent": "uhermes-build"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        print(f"\r        {pct:3d}%  {done / 1e6:7.1f}/{total / 1e6:.1f} MB",
                              end="", flush=True)
            if total:
                print()
            size = tmp.stat().st_size
            if expect_bytes and size == 0:
                raise RuntimeError("下载为空")
            if total and size != total:
                raise RuntimeError(f"下载不完整：期望 {total} 字节，实际 {size} 字节")
        except Exception as exc:  # 网络中断 / 截断 / 超时
            last_error = exc
            tmp.unlink(missing_ok=True)
            log(f"失败：{exc}")
            if attempt < attempts:
                time.sleep(2 * attempt)
            continue
        log(f"完成 {size / 1e6:.1f} MB / {time.time() - t0:.0f}s")
        tmp.replace(dest)
        return dest

    raise RuntimeError(f"下载失败（已重试 {attempts} 次）：{url}\n  最后错误：{last_error}")


EXTRACT_MARKER = ".uhermes-extract-ok"


def extract_marker_ok(dest: Path, token: str) -> bool:
    """判据必须是「上次解包完整跑完」，而不是「某个文件恰好存在」。

    否则一次中途失败的解包（断网、归档截断）会留下部分文件，让下一次构建误以为
    已完成而跳过下载与解包，产出一个残缺却看不出问题的包。
    """
    try:
        return (dest / EXTRACT_MARKER).read_text(encoding="utf-8").strip() == token
    except OSError:
        return False


def write_extract_marker(dest: Path, token: str) -> None:
    try:
        (dest / EXTRACT_MARKER).write_text(token, encoding="utf-8")
    except OSError:
        pass


def extract_tar(archive: Path, dest: Path, *, strip_first: bool = False) -> None:
    """显式解包。

    不用 tarfile.extractall：它对目录条目调用 os.mkdir(path, mode)，在受限 ACL
    的环境里会得到不可写目录（CRT _wmkdir 用进程默认 DACL，而不是继承父目录）。
    这里目录一律走 os.makedirs，文件自己写，任何环境都安全。

    链接条目：python-build-standalone 的 Linux 归档里 bin/python3 之类是符号链接，
    而 Windows 上创建符号链接需要开发者模式或管理员权限；少数归档还用硬链接。
    两种都在主循环里记下来，等全部文件落地后再补齐（复制或建硬链接），
    这样既不会因权限失败，也不会因为目标还没解出来而漏掉。
    """
    dest.mkdir(parents=True, exist_ok=True)
    n_dir = n_file = n_sym = n_copy = n_lnk = 0
    deferred: list[tuple[Path, str, str]] = []  # (target, linkname, kind)
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf:
            parts = list(Path(m.name).parts)
            if strip_first and parts:
                parts = parts[1:]
            if not parts or parts[0] in (".", ".."):
                continue
            target = dest.joinpath(*parts)
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                n_dir += 1
            elif m.issym():
                os.makedirs(target.parent, exist_ok=True)
                try:
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    os.symlink(m.linkname, target)
                    n_sym += 1
                except OSError:
                    deferred.append((target, m.linkname, "sym"))
            elif m.islnk():
                os.makedirs(target.parent, exist_ok=True)
                link_parts = list(Path(m.linkname).parts)
                if strip_first and link_parts:
                    link_parts = link_parts[1:]
                deferred.append((target, str(Path(*link_parts)), "lnk"))
            elif m.isfile():
                os.makedirs(target.parent, exist_ok=True)
                src = tf.extractfile(m)
                if src is None:
                    continue
                with src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
                if os.name != "nt" and (m.mode & stat.S_IXUSR):
                    os.chmod(target, m.mode | 0o111)
                n_file += 1

    for target, linkname, kind in deferred:
        # 符号链接的 linkname 相对于本条目所在目录；硬链接的相对于归档根
        source = (target.parent / linkname) if kind == "sym" else (dest / linkname)
        try:
            resolved = source.resolve(strict=True)
        except OSError:
            log(f"警告：链接目标不存在，跳过 {target.name} -> {linkname}")
            continue
        try:
            if target.exists():
                target.unlink()
            if kind == "lnk":
                try:
                    os.link(resolved, target)
                    n_lnk += 1
                    continue
                except OSError:
                    pass  # 跨卷等情况退化为复制
            if resolved.is_dir():
                shutil.copytree(resolved, target, symlinks=False, dirs_exist_ok=True)
            else:
                shutil.copy2(resolved, target)
                if os.name != "nt":
                    os.chmod(target, os.stat(resolved).st_mode | 0o111)
            n_copy += 1
        except OSError as exc:
            log(f"警告：无法补齐 {target.name} -> {linkname}（{exc}）")

    log(f"解包 {archive.name}: dirs={n_dir} files={n_file} "
        f"symlinks={n_sym} hardlinks={n_lnk} copied_links={n_copy}")


def extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = dest / info.filename
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(target.parent, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    log("$ " + " ".join(cmd))
    merged = {**os.environ, **(env or {})}
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=merged)
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败（exit {proc.returncode}）: {' '.join(cmd)}")


def which(name: str) -> str | None:
    return shutil.which(name)


# --------------------------------------------------------------------------- #
# 构建步骤
# --------------------------------------------------------------------------- #
def fetch_runtime(
    versions: dict[str, str], triple: str, cache: Path, dest: Path, python_exe: str
) -> None:
    name = (
        f"cpython-{versions['PYTHON_VERSION']}+{versions['PBS_RELEASE']}"
        f"-{triple}-{versions['PBS_VARIANT']}.tar.gz"
    )
    token = f"{name}"
    # 只有「上次解包完整跑完」才跳过。单看 python_exe 是否存在会被中途失败的解包骗过。
    if (dest / python_exe).exists() and extract_marker_ok(dest, token):
        log(f"运行时已存在且完整，跳过：{dest}")
        return
    if dest.exists():
        log(f"运行时目录不完整或来源不符，重新解包：{dest}")
        shutil.rmtree(dest, ignore_errors=True)
    archive = http_get(f"{PBS}/{versions['PBS_RELEASE']}/{name}", cache / name)
    # PBS 归档顶层固定是 python/，剥掉它，让 dest 直接就是运行时根目录
    extract_tar(archive, dest, strip_first=True)
    write_extract_marker(dest, token)


def fetch_source(versions: dict[str, str], cache: Path, dest: Path) -> None:
    tag = versions["HERMES_TAG"]
    token = f"hermes-agent-{tag}"
    if (dest / "pyproject.toml").exists() and extract_marker_ok(dest, token):
        log(f"源码树已存在且完整，跳过：{dest}")
        return
    if dest.exists():
        log(f"源码树目录不完整或来源不符，重新解包：{dest}")
        shutil.rmtree(dest, ignore_errors=True)
    archive = http_get(f"{GH}/NousResearch/hermes-agent/archive/refs/tags/{tag}.tar.gz",
                       cache / f"hermes-agent-{tag}.tar.gz")
    extract_tar(archive, dest, strip_first=True)
    write_extract_marker(dest, token)


def prune_tree(tree: Path) -> None:
    spec = REPO / "build" / "prune.txt"
    removed = kept = 0
    for raw in spec.read_text(encoding="utf-8").splitlines():
        entry = raw.split("#", 1)[0].strip()
        if not entry:
            continue
        target = tree / entry
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            removed += 1
        elif target.exists():
            target.unlink(missing_ok=True)
            removed += 1
        else:
            kept += 1
    # __pycache__ 一律清掉（构建机上可能残留，且可执行文件指纹会变）
    for pc in tree.rglob("__pycache__"):
        shutil.rmtree(pc, ignore_errors=True)
    log(f"裁剪完成：命中 {removed} 项，未命中 {kept} 项")


def export_requirements(tree: Path, extras: list[str], cache: Path, out: Path) -> Path:
    uv = which("uv")
    if not uv:
        raise RuntimeError("需要 uv 来解析依赖（安装：https://docs.astral.sh/uv/）")
    cmd = [
        uv, "export",
        "--frozen",              # 严格按 uv.lock，不重新解析
        "--no-hashes",
        "--no-emit-project",     # 不包含 hermes-agent 自身（它不发行 wheel）
        "--format", "requirements-txt",
        "-o", str(out),
    ]
    for extra in extras:
        cmd += ["--extra", extra]
    run(cmd, cwd=tree, env={"UV_CACHE_DIR": str(cache / "uv")})
    n = sum(1 for line in out.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
    log(f"依赖清单：{n} 个包 -> {out.name}")
    return out


def install_deps(
    platform: str,
    cfg: dict[str, str],
    triple: str,
    runtime: Path,
    reqs: Path,
    cache: Path,
    cross: bool,
) -> None:
    uv = which("uv")
    env = {"UV_CACHE_DIR": str(cache / "uv"), "UV_PYTHON_INSTALL_DIR": str(cache / "uv-python")}
    py_exe = runtime / cfg["python_exe"]
    site = runtime / cfg["site_packages"]

    if uv:
        if cross:
            # 交叉构建：无法执行目标平台的解释器，改为按目标三元组解析 wheel 并铺到 site-packages
            cmd = [
                uv, "pip", "install",
                "--python-platform", triple,
                "--python-version", "3.11",
                "--target", str(site),
                "--link-mode", "copy",
                "-r", str(reqs),
            ]
        else:
            cmd = [
                uv, "pip", "install",
                "--python", str(py_exe),
                "--system",
                "--link-mode", "copy",
                "-r", str(reqs),
            ]
        run(cmd, env=env)
        return

    if cross:
        raise RuntimeError("交叉构建必须有 uv（pip 无法为其他平台安装）")
    log("未找到 uv，回退到便携解释器自带的 pip（速度慢很多）")
    site.mkdir(parents=True, exist_ok=True)
    run([str(py_exe), "-m", "pip", "install", "--no-warn-script-location", "-r", str(reqs)],
        env={"PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1"})


def fetch_uv(versions: dict[str, str], cfg: dict[str, str], cache: Path, bin_dir: Path) -> None:
    """把 uv 二进制打进便携包 —— 让 Hermes 的"按需安装依赖"能力在离线介质上也可用。"""
    uv_version = versions.get("UV_VERSION", "0.12.6")
    asset = cfg["uv_asset"].format(v=uv_version)
    url = f"{UV_RELEASES}/{uv_version}/{asset}"
    archive = http_get(url, cache / asset)
    bin_dir.mkdir(parents=True, exist_ok=True)
    if asset.endswith(".zip"):
        extract_zip(archive, bin_dir)
    else:
        extract_tar(archive, bin_dir)
    for candidate in bin_dir.rglob("uv*"):
        if candidate.is_file() and candidate.suffix in ("", ".exe"):
            target = bin_dir / ("uv.exe" if os.name == "nt" else "uv")
            if candidate.resolve() != target.resolve():
                shutil.copy2(candidate, target)
    log(f"uv 已放入 {bin_dir}")


def assemble(
    platform: str,
    cfg: dict[str, str],
    stage: Path,
    out_dir: Path,
    versions: dict[str, str],
    extras: list[str],
) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 用复制而不是移动：保留 stage，重复构建时不必重新解包 4000+ 个文件
    # 1) 便携解释器
    shutil.copytree(stage / "python", out_dir / "python", symlinks=True)
    # 2) 上游源码树
    shutil.copytree(stage / "hermes-agent", out_dir / "hermes-agent", symlinks=True)
    # 3) 启动器
    launcher_src = REPO / cfg["launcher"]
    launcher_dst = out_dir / launcher_src.name
    shutil.copy2(launcher_src, launcher_dst)
    if platform == "linux":
        # 防御性归一：Windows 工作区可能是 CRLF，而 CRLF 的 shell 脚本在 Linux 上
        # 会以 "bad interpreter: /bin/bash^M" 直接失败（.gitattributes 已锁 LF，
        # 但用户可能从别处拷来文件或改过配置）。
        data = launcher_dst.read_bytes().replace(b"\r\n", b"\n")
        launcher_dst.write_bytes(data)
        os.chmod(launcher_dst, 0o755)
    # 4) 启动引导
    shutil.copy2(REPO / "shared" / "hermes_boot.py", out_dir / "hermes_boot.py")

    # 5) hermes_home 骨架 + 模板
    home = out_dir / "hermes_home"
    home.mkdir(parents=True, exist_ok=True)
    for name in (".env.example", "config.yaml.example"):
        shutil.copy2(REPO / "shared" / "hermes_home" / name, home / name)
    for name in ("skills", "sessions", "logs", "cron", "memories", "pairing", "hooks"):
        (home / name).mkdir(exist_ok=True)

    # 6) 上游完整参考（离线可查，避免用户为了查一个键去联网）
    ref = home / "reference"
    ref.mkdir(exist_ok=True)
    tree = out_dir / "hermes-agent"
    for src_name, dst_name in ((".env.example", "env.full.example"),
                               ("cli-config.yaml.example", "config.full.example")):
        src = tree / src_name
        if src.exists():
            shutil.copy2(src, ref / dst_name)

    # 7) 版本与来源
    (out_dir / "VERSION.txt").write_text(
        "\n".join([
            "Uhermes - portable Hermes Agent",
            "",
            f"hermes-version : {versions['HERMES_VERSION']}",
            f"hermes-tag     : {versions['HERMES_TAG']}",
            f"hermes-commit  : {versions['HERMES_COMMIT']}",
            f"hermes-released: {versions['HERMES_RELEASED']}",
            f"python         : {versions['PYTHON_VERSION']} (python-build-standalone {versions['PBS_RELEASE']})",
            f"target         : {platform} / {versions[cfg['triple_key']]}",
            f"extras         : {','.join(extras) if extras else '(core only)'}",
            f"built-at       : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "hermes-agent is MIT licensed, (c) Nous Research -",
            "https://github.com/NousResearch/hermes-agent",
            "",
        ]),
        encoding="utf-8",
    )

    # 8) 清掉构建期用的内部标记，别让它们出现在用户看到的包里
    for stray in out_dir.rglob(EXTRACT_MARKER):
        try:
            stray.unlink()
        except OSError:
            pass
    log(f"组装完成：{out_dir}")


def make_zip(out_dir: Path, platform: str) -> Path:
    archive = out_dir.with_suffix(".zip")
    if archive.exists():
        archive.unlink()
    log(f"打包 {archive.name} …")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(out_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(out_dir)
            arc = str(Path(out_dir.name) / rel)
            if platform != "linux":
                zf.write(path, arcname=arc)
                continue
            # Linux 包常常在 Windows 上构建，而 Windows 文件没有 Unix 权限位 ——
            # 显式写入模式，否则用户在 Linux 解压后 python/bin/* 与 start.sh 不可执行。
            zi = zipfile.ZipInfo(arc, date_time=time.localtime(path.stat().st_mtime)[:6])
            zi.compress_type = zipfile.ZIP_DEFLATED
            executable = (
                rel.parts[:2] == ("python", "bin")
                or rel.parts[:2] == ("bin",)
                or path.name.endswith(".sh")
            )
            mode = 0o755 if executable else 0o644
            zi.external_attr = (stat.S_IFREG | mode) << 16
            with zf.open(zi, "w") as dst, open(path, "rb") as src:
                shutil.copyfileobj(src, dst, 1 << 20)
    log(f"{archive.name}: {archive.stat().st_size / 1e6:.1f} MB")
    return archive


def dir_size(path: Path) -> tuple[float, int]:
    total = 0
    files = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            files += 1
    return total / 1e6, files


# --------------------------------------------------------------------------- #
# 上游版本检查
# --------------------------------------------------------------------------- #
def check_upstream(versions: dict[str, str]) -> int:
    url = f"https://api.github.com/repos/NousResearch/hermes-agent/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "uhermes-build", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        log(f"GitHub API 返回 {e.code}（匿名调用有速率限制，稍后再试或直接看 Releases 页面）")
        return 1
    tag = data.get("tag_name", "")
    name = data.get("name", "")
    pinned = versions["HERMES_TAG"]
    log(f"上游最新：{tag}  ({name})")
    log(f"当前钉定：{pinned}  ({versions['HERMES_VERSION']})")
    if tag == pinned:
        log("已是最新。")
        return 0
    log("发现新版本 —— 更新 versions.env 中的 HERMES_VERSION / HERMES_TAG / HERMES_COMMIT 后重新构建。")
    return 10


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def build_platform(
    platform: str,
    versions: dict[str, str],
    extras: list[str],
    out_root: Path,
    cache: Path,
    *,
    cross: bool,
    with_uv: bool,
    zip_it: bool,
) -> Path:
    cfg = PLATFORMS[platform]
    triple = versions[cfg["triple_key"]]
    # 版本作用域的工作目录：升级 versions.env 后自动使用全新的 stage，避免复用旧树
    stage = cache / f"stage-{platform}-{versions['HERMES_VERSION']}-py{versions['PYTHON_VERSION']}"
    log(f"===== 构建 {platform} ({triple}) =====")
    log(f"stage: {stage}")

    runtime = stage / "python"
    tree = stage / "hermes-agent"
    fetch_runtime(versions, triple, cache, runtime, cfg["python_exe"])
    fetch_source(versions, cache, tree)
    prune_tree(tree)

    reqs = cache / f"requirements-{platform}.txt"
    export_requirements(tree, extras, cache, reqs)
    install_deps(platform, cfg, triple, runtime, reqs, cache, cross)

    out_dir = out_root / f"Uhermes-{platform}"
    assemble(platform, cfg, stage, out_dir, versions, extras)
    if with_uv:
        fetch_uv(versions, cfg, cache, out_dir / "bin")

    mb, files = dir_size(out_dir)
    log(f"产物：{out_dir}  {mb:.1f} MB / {files} 个文件")
    if zip_it:
        make_zip(out_dir, platform)
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="Uhermes 便携包构建器")
    ap.add_argument("--platform", choices=["windows", "linux", "all"], default=None)
    ap.add_argument("--extras", default="all",
                    help="all | core | 逗号分隔的 extra 列表（默认 all）")
    ap.add_argument("--out", default=None, help="产物根目录（默认 <repo>/dist）")
    ap.add_argument("--cache", default=None, help="下载与中间产物目录（默认 <repo>/build/_cache）")
    ap.add_argument("--cross", action="store_true",
                    help="交叉构建：在 Windows 上产出 Linux 包（依赖 wheel 解析，无法实机验证）")
    ap.add_argument("--with-uv", action="store_true", help="把 uv 二进制也打进便携包")
    ap.add_argument("--zip", dest="zip_it", action="store_true", default=True, help="同时产出 zip（默认）")
    ap.add_argument("--no-zip", dest="zip_it", action="store_false")
    ap.add_argument("--check", action="store_true", help="只检查上游是否有新版本")
    args = ap.parse_args()

    versions = read_versions()
    if args.check:
        return check_upstream(versions)

    if not args.platform:
        ap.error("需要 --platform（或 --check）")

    out_root = Path(args.out) if args.out else REPO / "dist"
    cache = Path(args.cache) if args.cache else REPO / "build" / "_cache"
    out_root.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    extras = [] if args.extras == "core" else [e.strip() for e in args.extras.split(",") if e.strip()]
    host = "windows" if os.name == "nt" else "linux"
    targets = ["windows", "linux"] if args.platform == "all" else [args.platform]

    results: list[Path] = []
    for platform in targets:
        cross = platform != host
        if cross and not args.cross:
            log(f"跳过 {platform}：当前主机是 {host}，需要 --cross 才做交叉构建")
            continue
        if cross:
            log(f"注意：{platform} 为交叉构建产物，本机无法运行验证；"
                f"若某些依赖缺少目标平台 wheel，会在安装阶段报错而不是产出坏包。")
        results.append(
            build_platform(platform, versions, extras, out_root, cache,
                           cross=cross, with_uv=args.with_uv, zip_it=args.zip_it)
        )

    log("===== 完成 =====")
    for path in results:
        mb, files = dir_size(path)
        log(f"  {path.name}: {mb:.1f} MB / {files} 文件")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"\n[build] 失败：{exc}", file=sys.stderr)
        sys.exit(1)
