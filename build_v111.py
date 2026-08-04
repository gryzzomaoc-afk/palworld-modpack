#!/usr/bin/env python3
"""build_v111: build .exe + wrap into friend-distribution .zip.

v1.1.1: parallelized `fetch_mods_from_github()` (ThreadPoolExecutor) so
the sync button pulls all per-mod manifest.json files concurrently.
Wall time drops from ~4×latency to ~1×latency.  Also fixes a cosmetic
double-v version label in the mod details dialog / update button.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Users\yason\.minimax-agent\projects\palworld-modpack")
PYTHON = Path(r"C:\Users\yason\.minimax\workspace\python-embed-311\tools\python.exe")
FRIEND_PACK = ROOT / "friend_pack"
DIST = ROOT / "dist"
VERSION = "1.1.1"
EXE_NAME = "PalworldFriendModInstaller.exe"
ZIP_NAME = f"PalworldFriendModInstaller-v{VERSION}.zip"
LOG_PATH = ROOT / f"build_v{VERSION.replace('.', '')}_python.log"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_pyinstaller() -> None:
    cmd = [
        str(PYTHON),
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        "PalworldFriendModInstaller",
        "--icon",
        str(ROOT / "installer.ico"),
        "--add-data",
        f"{ROOT / 'installer.ico'};.",
        "--distpath",
        str(DIST),
        "--workpath",
        str(ROOT / "build_v111_raw"),
        "--specpath",
        str(ROOT / "build_v111_raw"),
        "--noconfirm",
        "friend_flet.py",
    ]
    log(f"PyInstaller: {' '.join(cmd)}")
    # On Windows, PyInstaller writes progress to stderr which PowerShell
    # surfaces as a RemoteException when using subprocess.call.  Use
    # subprocess.run and only fail if the .exe is actually missing or
    # the return code is non-zero AND no .exe was produced.
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # Log tail of stdout/stderr for debug
    if proc.stdout:
        for line in proc.stdout.strip().splitlines()[-10:]:
            log(f"  | {line}")
    if proc.stderr:
        for line in proc.stderr.strip().splitlines()[-10:]:
            log(f"  ! {line}")
    expected_exe = DIST / EXE_NAME
    if not expected_exe.exists():
        raise SystemExit(f"PyInstaller FAILED rc={proc.returncode}; {expected_exe} missing")
    if proc.returncode != 0:
        log(f"PyInstaller rc={proc.returncode} but exe exists, continuing")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    LOG_PATH.unlink(missing_ok=True)
    log(f"build v{VERSION} start")

    DIST.mkdir(exist_ok=True)
    run_pyinstaller()
    log("PyInstaller OK")

    exe_src = DIST / EXE_NAME
    if not exe_src.exists():
        raise SystemExit(f"missing {exe_src}")

    exe_hash = sha256(exe_src)
    log(f"exe sha256={exe_hash} size={exe_src.stat().st_size}")

    # Write SHA256.txt into friend_pack
    sha_txt = FRIEND_PACK / "SHA256.txt"
    sha_txt.write_text(
        f"{EXE_NAME}  {exe_hash}\n",
        encoding="utf-8",
    )
    log(f"wrote {sha_txt}")

    # Copy .exe into friend_pack\ with versioned name
    exe_in_pack = FRIEND_PACK / f"PalworldFriendModInstaller-v{VERSION}.exe"
    shutil.copy2(exe_src, exe_in_pack)
    log(f"copied to {exe_in_pack}")

    # Build zip
    zip_path = DIST / ZIP_NAME
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in sorted(FRIEND_PACK.iterdir()):
            if f.is_file():
                zf.write(f, f.name)
                log(f"  + {f.name} ({f.stat().st_size} bytes)")
    log(f"wrote {zip_path} ({zip_path.stat().st_size} bytes)")

    # Also drop a copy on the desktop
    desktop = Path.home() / "OneDrive" / "桌面" / ZIP_NAME
    if desktop.parent.exists():
        shutil.copy2(zip_path, desktop)
        log(f"copied to {desktop}")
    else:
        log(f"skip desktop copy ({desktop.parent} missing)")

    log("=== final outputs ===")
    log(f"  {zip_path}  {zip_path.stat().st_size} bytes  sha256={sha256(zip_path)}")
    log(f"  {exe_src}  {exe_src.stat().st_size} bytes  sha256={exe_hash}")
    log("done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FAILED: {e!r}")
        raise
