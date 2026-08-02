"""Shared backend logic for the friend mod installer.

Used by both friend_gui.py (tkinter) and friend_flet.py (Flet/Flutter).
NO tkinter, flet, or GUI imports here — pure stdlib only.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import ssl

try:
    import certifi
    _HAS_CERTIFI = True
except ImportError:
    _HAS_CERTIFI = False


def _make_ssl_context():
    """SSL context that uses certifi's CA bundle (fixes CERTIFICATE_VERIFY_FAILED on
    Windows machines where Python's default CA store is missing GitHub's intermediate cert).
    Falls back to default context if certifi isn't available.
    """
    if _HAS_CERTIFI:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()
import zipfile
from pathlib import Path

# --- paths & config ---
APP_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = Path.home() / ".palworld_friend_tool.json"


def _default_catalog_path() -> str:
    """Default mod source for the friend installer.

    v1.0.8+ uses GitHub folder-discovery: each mod lives in
    `mods/<name>/manifest.json` and the installer lists the directory via
    the GitHub API.  Returning the `GITHUB_DISCOVERY_SCHEME` sentinel here
    tells the UI to call `fetch_mods_from_github()` instead of
    `fetch_catalog(url)`.

    For custom catalogs (e.g. a fork, a local file), drop a
    `friend-catalog.json` next to the .exe (or in PyInstaller's _MEIPASS)
    and that file:// URL will take precedence — useful for testing before
    pushing a manifest update.
    """
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        # PyInstaller / Flet onefile extract dir (where --add-data files live)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "friend-catalog.json")
        # Next to the .exe (where friend might drop a custom catalog)
        candidates.append(Path(sys.executable).parent / "friend-catalog.json")
    else:
        candidates.append(Path(__file__).parent.resolve() / "friend-catalog.json")
    for c in candidates:
        if c.exists():
            return c.as_uri()  # file:///C:/...
    # No local override -> use the repo-driven discovery pipeline.
    return GITHUB_DISCOVERY_SCHEME


# Sentinel used by `_default_catalog_path()` to indicate "use the GitHub
# folder-discovery pipeline". The UI code treats any URL starting with
# the literal GITHUB_DISCOVERY_SCHEME as a request to call
# `fetch_mods_from_github()` instead of `fetch_catalog(url)`.
GITHUB_DISCOVERY_SCHEME = "github://gryzzomaoc-afk/palworld-modpack/main/mods"


# --- GitHub repo-driven mod discovery (v1.0.8+) ---


DEFAULT_CATALOG_URL = _default_catalog_path()


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"catalog_url": DEFAULT_CATALOG_URL}


def save_config(cfg: dict) -> None:
    try:
        CONFIG_FILE.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"save_config err: {e!r}")


# --- Steam / Palworld auto-detect (Windows registry + common paths) ---
def detect_steam() -> tuple[str | None, str | None]:
    """Return (steam_path, palworld_path) or (None, None) if not found."""
    if sys.platform != "win32":
        return None, None

    steam_root = None
    try:
        import winreg
        for hive, key_path in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
        ]:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    val, _ = winreg.QueryValueEx(key, "InstallPath")
                    if val and Path(val).exists():
                        steam_root = val
                        break
            except FileNotFoundError:
                continue
            except Exception:
                continue
    except ImportError:
        pass

    if not steam_root:
        for d in [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Steam",
            r"D:\Program Files (x86)\Steam",
            r"E:\Steam",
        ]:
            if Path(d).exists() and Path(d, "steamapps").exists():
                steam_root = d
                break

    if not steam_root:
        return None, None

    palworld = Path(steam_root) / "steamapps" / "common" / "Palworld"
    if not palworld.exists():
        lib_vdf = Path(steam_root) / "steamapps" / "libraryfolders.vdf"
        if lib_vdf.exists():
            try:
                import re
                text = lib_vdf.read_text(encoding="utf-8", errors="ignore")
                for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                    p = Path(m.group(1).replace("\\\\", "\\")) / "steamapps" / "common" / "Palworld"
                    if p.exists():
                        palworld = p
                        break
            except Exception:
                pass

    return steam_root, (str(palworld) if palworld.exists() else None)


# --- Palworld running check (prevents file lock issues) ---
def is_palworld_running() -> tuple[bool, list[str]]:
    """Check if Palworld is currently running.

    Returns (running, [process_names]).
    Looks for both shipping exe and common related processes.
    """
    if sys.platform != "win32":
        return False, []
    candidates = ["Palworld-Win64-Shipping", "Palworld", "PalServer"]
    found = []
    try:
        import subprocess  # noqa: F401  (not used directly, kept for future)
        for name in candidates:
            # tasklist filter by image name
            ps_cmd = [
                "powershell", "-NoProfile", "-Command",
                f"Get-Process -Name '{name}' -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty Name"
            ]
            r = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
            for ln in (r.stdout or "").splitlines():
                ln = ln.strip()
                if ln:
                    found.append(ln)
    except Exception:
        pass
    return (len(found) > 0), found


def _backup_dir(src: Path, label: str = "") -> Path | None:
    """Snapshot a directory to <src>.bak-<timestamp> before destructive ops.

    Returns the backup path, or None if src didn't exist.
    """
    if not src or not src.exists() or not src.is_dir():
        return None
    import shutil
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{label}" if label else ""
    backup = src.with_name(src.name + f".bak-{ts}{suffix}")
    if backup.exists():
        # collision: append a counter
        i = 1
        while True:
            cand = src.with_name(src.name + f".bak-{ts}{suffix}-{i}")
            if not cand.exists():
                backup = cand
                break
            i += 1
    try:
        shutil.copytree(src, backup)
        return backup
    except Exception:
        return None


# --- Catalog fetch ---
def fetch_catalog(url: str) -> dict:
    """Fetch and parse the mod catalog JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "PalworldFriendModInstaller/1.0.7"})
    ctx = _make_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}")
    # Use utf-8-sig so we transparently handle a UTF-8 BOM if the catalog
    # was saved with one (common when using Windows tools like PowerShell's
    # Set-Content -Encoding UTF8, which prepends a BOM by default).
    return json.loads(data.decode("utf-8-sig"))


# --- GitHub repo-driven mod discovery (v1.0.8+) ---
# Each mod lives in `mods/<name>/` with a `manifest.json` and one or more
# `*.zip` files referenced by the manifest.  Installer uses the GitHub API
# to list the `mods/` directory, then downloads each manifest, then
# assembles the same dict shape that `fetch_catalog()` returns so the
# rest of the codebase (install / uninstall / UI) doesn't need to change.
GITHUB_REPO = "gryzzomaoc-afk/palworld-modpack"
GITHUB_BRANCH = "main"
GITHUB_MODS_SUBDIR = "mods"


def _github_raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{path.lstrip('/')}"


def _github_api_url(path: str) -> str:
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path.lstrip('/')}"


def _github_get_json(url: str, timeout: int = 15) -> dict | list:
    """GET a JSON document from a GitHub URL. Raises RuntimeError on failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "PalworldFriendModInstaller/1.0.8",
        "Accept": "application/vnd.github+json",
    })
    ctx = _make_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP {e.code}: {e.reason} (url={url})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API URL error: {e.reason} (url={url})")
    return json.loads(data.decode("utf-8-sig"))


def _resolve_component_url(mod_name: str, comp: dict) -> dict:
    """Turn a component's `zip` filename into a full raw.githubusercontent.com URL.

    Mutates and returns the component dict.
    """
    zip_name = (comp.get("zip") or "").strip()
    if not zip_name:
        raise RuntimeError(f"mod {mod_name!r} component has no 'zip' field")
    comp["url"] = _github_raw_url(f"{GITHUB_MODS_SUBDIR}/{mod_name}/{zip_name}")
    return comp


def fetch_mods_from_github() -> dict:
    """Discover mods by listing `mods/` in the GitHub repo.

    Returns a dict in the same shape as the old `friend-catalog.json`:
      {"version": int, "updated": str, "mods": {<name>: <manifest>}}

    Only mods with `"friend_allowed": true` in their manifest are returned.
    """
    listing = _github_get_json(_github_api_url(GITHUB_MODS_SUBDIR))
    if not isinstance(listing, list):
        raise RuntimeError(
            f"GitHub API returned unexpected payload for "
            f"{GITHUB_MODS_SUBDIR!r} (expected directory listing)"
        )

    mods: dict = {}
    skipped: list = []
    for entry in listing:
        if entry.get("type") != "dir":
            continue
        mod_name = entry.get("name") or ""
        if not mod_name or mod_name.startswith("."):
            continue
        manifest_url = _github_raw_url(f"{GITHUB_MODS_SUBDIR}/{mod_name}/manifest.json")
        try:
            req = urllib.request.Request(manifest_url, headers={
                "User-Agent": "PalworldFriendModInstaller/1.0.8",
            })
            ctx = _make_ssl_context()
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                data = r.read()
            manifest = json.loads(data.decode("utf-8-sig"))
        except Exception as e:
            skipped.append({"name": mod_name, "reason": f"manifest fetch failed: {e}"})
            continue
        if not isinstance(manifest, dict):
            skipped.append({"name": mod_name, "reason": "manifest is not a JSON object"})
            continue
        # Confirm name matches the folder; if not, prefer the folder name to
        # keep the on-disk install path stable.
        manifest["name"] = manifest.get("name") or mod_name
        if not manifest.get("friend_allowed", False):
            skipped.append({"name": mod_name, "reason": "friend_allowed=false"})
            continue
        if not manifest.get("components"):
            skipped.append({"name": mod_name, "reason": "no components in manifest"})
            continue
        # Resolve each component's `zip` filename to a full raw.githubusercontent.com URL
        for role, comp in list(manifest.get("components", {}).items()):
            try:
                _resolve_component_url(mod_name, comp)
            except Exception as e:
                skipped.append({"name": mod_name, "reason": f"component {role!r}: {e}"})
                break
        else:
            mods[mod_name] = manifest

    return {
        "version": 3,
        "updated": "auto",
        "source": f"github:{GITHUB_REPO}@{GITHUB_BRANCH}/{GITHUB_MODS_SUBDIR}/",
        "mods": mods,
        "_skipped": skipped,
    }


# --- UE4SS prereq (Okaetsu RE-UE4SS for Palworld) ---
UE4SS_URL = "https://github.com/Okaetsu/RE-UE4SS/releases/download/experimental-palworld/UE4SS-Palworld.zip"


def check_ue4ss(palworld_path: str) -> dict:
    """Check if RE-UE4SS is installed.

    Looks in multiple common locations (Okaetsu default + direct + root):
      1. <pal>/Pal/Binaries/Win64/ue4ss/UE4SS.dll  (Okaetsu RE-UE4SS)
      2. <pal>/Pal/Binaries/Win64/UE4SS.dll         (direct extract)
      3. <pal>/Pal/Binaries/Win64/ue4ss/UE4SS.pak
      4. <pal>/Pal/Binaries/Win64/UE4SS.pak
      5. <pal>/ue4ss/UE4SS.dll                      (root variant)
    """
    out = {
        "installed": False,
        "found_path": None,
        "marker": None,
        "checked": [],
        "error": None,
    }
    if not palworld_path:
        out["error"] = "no palworld path"
        return out

    pp = Path(palworld_path)
    win64 = pp / "Pal" / "Binaries" / "Win64"
    candidates = [
        (win64 / "ue4ss" / "UE4SS.dll", "Pal/Binaries/Win64/ue4ss/UE4SS.dll (Okaetsu)"),
        (win64 / "UE4SS.dll", "Pal/Binaries/Win64/UE4SS.dll"),
        (win64 / "ue4ss" / "UE4SS.pak", "Pal/Binaries/Win64/ue4ss/UE4SS.pak"),
        (win64 / "UE4SS.pak", "Pal/Binaries/Win64/UE4SS.pak"),
        (pp / "ue4ss" / "UE4SS.dll", "ue4ss/UE4SS.dll (root)"),
    ]
    for path, desc in candidates:
        out["checked"].append({"path": str(path), "desc": desc, "exists": path.exists()})
        if path.exists():
            out["installed"] = True
            out["found_path"] = str(path.parent)
            out["marker"] = path.name
            return out
    return out


def check_ue4ss_health(palworld_path: str) -> dict:
    """Comprehensive UE4SS health check (for Okaetsu RE-UE4SS layout).

    Goes beyond check_ue4ss (which only finds UE4SS.dll) and verifies that
    all expected files are in the right places. A "UE4SS.dll is present" result
    from check_ue4ss can still mean UE4SS won't work for mods (e.g. missing
    UEHelpers.lua, missing zip-extracted Mods/, or UE4SS-settings.ini with
    EnableMods=false). Friend installer calls this after install_ue4ss to
    confirm the install actually took.

    Returns:
      {
        "ok": bool,                  # True if all required files present
        "issues": [str],             # human-readable problems found
        "checks": [{name, path, ok, detail}],  # per-file results
        "dll_path": str|None,        # resolved UE4SS.dll location
        "mods_path": str|None,       # resolved Mods/ location
      }
    """
    out = {
        "ok": False,
        "issues": [],
        "checks": [],
        "dll_path": None,
        "mods_path": None,
    }
    if not palworld_path:
        out["issues"].append("no palworld path")
        return out

    base = check_ue4ss(palworld_path)
    if not base.get("installed"):
        out["issues"].append("UE4SS.dll not found in any standard location")
        out["checks"].extend([
            {"name": c["desc"], "path": c["path"], "ok": c["exists"]}
            for c in base.get("checked", [])
        ])
        return out

    # UE4SS.dll is there; check the rest of the layout relative to it.
    # Okaetsu's standard layout: UE4SS.dll sits at <...>/ue4ss/, with Mods/
    # and UE4SS-settings.ini as siblings.
    ue4ss_dir = Path(base["found_path"])
    out["dll_path"] = str(ue4ss_dir / base["marker"])
    out["mods_path"] = str(ue4ss_dir / "Mods")

    expected = [
        (ue4ss_dir / "UE4SS.dll",         "UE4SS.dll",             "required"),
        (ue4ss_dir / "UE4SS-settings.ini", "UE4SS-settings.ini",    "required"),
        (ue4ss_dir / "Mods",               "Mods/",                 "required"),
        (ue4ss_dir / "Mods" / "shared" / "UEHelpers" / "UEHelpers.lua",
         "Mods/shared/UEHelpers/UEHelpers.lua", "required"),
        (ue4ss_dir / "Mods" / "mods.txt",  "Mods/mods.txt",         "optional"),
    ]
    for path, name, severity in expected:
        ok = path.exists()
        out["checks"].append({
            "name": name,
            "path": str(path),
            "ok": ok,
            "severity": severity,
        })
        if not ok and severity == "required":
            out["issues"].append(f"missing required file: {name} ({path})")

    out["ok"] = not any(
        not c["ok"] and c.get("severity") == "required"
        for c in out["checks"]
    )
    return out


def verify_mod_install(mod: dict, palworld_path: str) -> dict:
    """Verify an installed mod matches the catalog expectations.

    For each component (server / client), checks that the files listed in
    catalog `files` exist on disk at the expected location. Does NOT verify
    per-file SHA256 (catalog only has zip-level SHA256, not per-file).

    Returns:
      {
        "ok": bool,
        "components": {role: {ok, files, issues}},
      }
    """
    out = {"ok": True, "components": {}}
    for role, comp in (mod.get("components") or {}).items():
        per_role = {"ok": True, "files": [], "issues": []}
        needs_ue4ss = comp.get("needs_ue4ss", True)
        files = comp.get("files") or []

        # Determine target directory. Use extract_to from manifest, with
        # the same heuristic as verify_all_mods: only UE4SS Lua mods
        # (extract_to ends with ue4ss/Mods) get a <modname>/ subfolder.
        # LogicMods and plain Pak mods drop files directly in extract_to.
        extract_to = comp.get("extract_to", "")
        if extract_to:
            base = Path(palworld_path) / extract_to
            mod_name = mod.get("name", "unknown")
            et_norm = extract_to.replace("\\", "/").rstrip("/")
            if needs_ue4ss and et_norm.endswith("ue4ss/Mods"):
                base = base / mod_name
            target_dir = base
        elif needs_ue4ss:
            # No extract_to specified: fall back to old UE4SS default
            mod_name = mod.get("name", "unknown")
            target_dir = Path(palworld_path) / "Pal" / "Binaries" / "Win64" / "ue4ss" / "Mods" / mod_name
        else:
            target_dir = Path(palworld_path) / "Pal" / "Content" / "Paks" / "~mods"

        for f in files:
            # 'Scripts/main.lua' -> target_dir / Scripts / main.lua
            # 'YetAnotherMinimap.pak' -> target_dir / YetAnotherMinimap.pak (flat)
            parts = f.replace("\\", "/").split("/")
            if not (needs_ue4ss and et_norm.endswith("ue4ss/Mods")):
                # Client / LogicMod: flatten (only top-level filename)
                parts = [parts[-1]]
            fpath = target_dir.joinpath(*parts)
            entry = {
                "file": f,
                "path": str(fpath),
                "exists": fpath.exists(),
            }
            if fpath.exists():
                entry["size"] = fpath.stat().st_size
            else:
                per_role["issues"].append(f"{f} not found at {fpath}")
                per_role["ok"] = False
            per_role["files"].append(entry)

        if not per_role["ok"]:
            out["ok"] = False
        out["components"][role] = per_role
    return out


def _parse_mods_txt(text: str) -> tuple[dict, list]:
    """Parse mods.txt: return ({name: val}, [comments])."""
    entries = {}
    comments = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(";"):
            comments.append(line)
            continue
        if ":" in s:
            name, _, val = s.partition(":")
            entries[name.strip()] = val.strip()
    return entries, comments


def _merge_mods_txt(mods_txt: Path, original_text: str) -> None:
    """Merge original mod entries (user customizations) into zip's built-in mods.txt.

    Logic: union of (zip's current built-in entries) + (original custom entries).
    For the 8 built-in mod names, zip's value wins (zip is authoritative for built-ins).
    """
    zip_entries, zip_comments = _parse_mods_txt(
        mods_txt.read_text(encoding="utf-8", errors="replace")
    )
    orig_entries, orig_comments = _parse_mods_txt(original_text)

    # Start with original (preserves user customizations like WTDScaler, PalToolkit, etc.)
    merged = dict(orig_entries)
    # Overlay zip's built-in 8 (zip is authoritative for built-ins; values typically same anyway)
    for name, val in zip_entries.items():
        merged[name] = val

    # Reconstruct
    lines = list(dict.fromkeys(zip_comments + orig_comments))  # dedupe comments, keep order
    for name, val in merged.items():
        lines.append(f"{name} : {val}")
    mods_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def install_ue4ss(palworld_path: str) -> tuple[bool, str]:
    """Download Okaetsu RE-UE4SS for Palworld and extract to Palworld's Win64/.

    Preserves any user-customized entries in <win64>/ue4ss/Mods/mods.txt
    (e.g. WTDScaler, PalToolkit, WorldTreeDragonSuperEvolution, etc.) by
    snapshotting the file before extraction and merging back the custom
    entries after. This prevents the zip's built-in 8 entries from
    clobbering server-side custom mods.

    Also backs up the existing ue4ss/ folder to ue4ss.bak-<ts>/ before
    extraction so the user can rollback if something goes wrong.
    Aborts with a clear message if Palworld is currently running (would
    lock UE4SS.dll + mods).
    """
    # Refuse if Pal is running (would lock .dll + .pak)
    running, names = is_palworld_running()
    if running:
        return False, (
            f"Palworld 正在執行（{', '.join(names)}），請先完整關閉遊戲再裝 UE4SS。"
            f"沒關的話 .dll 會被 lock、安裝完也無法生效。"
        )

    try:
        req = urllib.request.Request(UE4SS_URL, headers={"User-Agent": "PalworldFriendModInstaller/1.0"})
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
            data = r.read()
    except Exception as e:
        return False, f"download failed: {e}"
    try:
        target_base = Path(palworld_path) / "Pal" / "Binaries" / "Win64"
        ue4ss_dir = target_base / "ue4ss"
        mods_txt = ue4ss_dir / "Mods" / "mods.txt"

        # Backup existing ue4ss/ folder (whole tree) so user can rollback
        backup_path = None
        if ue4ss_dir.exists():
            backup_path = _backup_dir(ue4ss_dir, label="pre-install")
        backup_msg = f"（舊版備份到 {backup_path.name}\\）" if backup_path else ""

        # Snapshot existing mods.txt (if any) so we can preserve user customizations
        original_mods_txt = None
        if mods_txt.exists():
            original_mods_txt = mods_txt.read_text(encoding="utf-8", errors="replace")

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(target_base)

        # Merge built-in (from zip) + custom (from snapshot)
        if original_mods_txt is not None and mods_txt.exists():
            _merge_mods_txt(mods_txt, original_mods_txt)

        # Verify install actually took (catches silent layout breakage — e.g.
        # zip structure changed, UEHelpers.lua missing, etc.)
        health = check_ue4ss_health(palworld_path)
        if not health["ok"]:
            issues = "; ".join(health["issues"])
            # Auto-rollback: restore from backup so user isn't stuck
            rollback_msg = ""
            if backup_path and backup_path.exists():
                import shutil
                if ue4ss_dir.exists():
                    shutil.rmtree(ue4ss_dir, ignore_errors=True)
                shutil.copytree(backup_path, ue4ss_dir)
                rollback_msg = f"（已從備份還原: {backup_path.name}）"
            return False, (
                f"extract 完成但 layout 驗證失敗 ({issues}) {rollback_msg}。"
                f"請回報這個錯誤給工具維護者。"
            )

        msg = f"已安裝至 {target_base}\\ue4ss\\ {backup_msg}"
        return True, msg
    except Exception as e:
        return False, f"extract failed: {e}"


def uninstall_ue4ss(palworld_path: str) -> tuple[bool, str]:
    """Remove UE4SS install: ue4ss/ dir + the zip-root dwmapi.dll in Win64/.

    The Okaetsu RE-UE4SS zip extracts two top-level entries: `dwmapi.dll`
    (sits at Win64/ root) and `ue4ss/...` (subdir). Removing only ue4ss/
    leaves a stale dwmapi.dll that conflicts on reinstall.

    Backs up the existing ue4ss/ folder to ue4ss.bak-<ts>/ first.
    Aborts if Palworld is running.
    """
    if not palworld_path:
        return False, "no palworld path"
    import shutil
    target_base = Path(palworld_path) / "Pal" / "Binaries" / "Win64"
    ue4ss_dir = target_base / "ue4ss"
    if not ue4ss_dir.exists():
        return False, f"not installed at {ue4ss_dir}"

    # Refuse if Pal is running
    running, names = is_palworld_running()
    if running:
        return False, (
            f"Palworld 正在執行（{', '.join(names)}），請先完整關閉遊戲再卸載 UE4SS。"
        )

    # Backup before destroying
    backup = _backup_dir(ue4ss_dir, label="pre-uninstall")
    backup_msg = f"（已備份到 {backup.name}\\）" if backup else ""

    try:
        shutil.rmtree(ue4ss_dir, ignore_errors=True)
        # also remove zip-root dwmapi.dll (lives in Win64/, not under ue4ss/)
        dwmapi = target_base / "dwmapi.dll"
        if dwmapi.exists():
            try:
                dwmapi.unlink()
            except Exception:
                pass
        return True, f"removed {ue4ss_dir} {backup_msg}"
    except Exception as e:
        return False, f"uninstall failed: {e}"


# --- Install / Uninstall mods ---
def _resolve_target_dir(comp: dict, palworld_path: str) -> Path:
    """Where to extract a single component."""
    if comp.get("needs_ue4ss", True):
        return Path(palworld_path) / "Pal" / "Binaries" / "Win64" / "ue4ss" / "Mods"
    return Path(palworld_path) / "Pal" / "Content" / "Paks" / "~mods"


def _install_component(mod: dict, comp: dict, palworld_path: str, role: str) -> tuple[bool, str]:
    """Install ONE component (server or client). Returns (success, message)."""
    url = comp.get("url", "").strip()
    if not url:
        return False, f"{role}: no URL"

    # Refuse if Pal is running (would lock .pak / .dll mid-write)
    running, names = is_palworld_running()
    if running:
        return False, (
            f"{role}: Palworld 正在執行（{', '.join(names)}），"
            f"請先完整關閉遊戲再裝 mod。"
        )

    target_dir = _resolve_target_dir(comp, palworld_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalworldFriendModInstaller/1.0.7"})
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            data = r.read()
    except Exception as e:
        return False, f"{role}: download failed: {e}"

    # SHA256 verification (defends against MITM, file corruption, malicious fork).
    # If the catalog entry has a `sha256` field, we verify the downloaded bytes
    # match before doing any extraction. Mismatch -> abort.
    expected_sha = (comp.get("sha256") or "").strip().lower()
    if expected_sha:
        actual_sha = hashlib.sha256(data).hexdigest().lower()
        if actual_sha != expected_sha:
            return False, (
                f"{role}: SHA256 mismatch (file may be corrupted, MITM'd, "
                f"or catalog is out of date). "
                f"expected={expected_sha[:16]}... actual={actual_sha[:16]}..."
            )

    try:
        backup_msg = ""  # used by both server and client branches below
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if comp.get("needs_ue4ss", True):
                import shutil
                mod_name = mod.get("name", "unknown")
                target_root = target_dir / mod_name
                tmp_root = target_dir / f".{mod_name}_extract_tmp"

                # Backup existing mod folder so user can rollback if they
                # had any custom-patched files (e.g. server-side Lua overrides)
                backup_msg = ""
                if target_root.exists():
                    backup = _backup_dir(target_root, label=f"pre-{role}")
                    if backup:
                        backup_msg = f"（舊版備份到 {backup.name}\\）"

                # Clean any prior tmp + target
                if tmp_root.exists():
                    shutil.rmtree(tmp_root, ignore_errors=True)
                if target_root.exists():
                    shutil.rmtree(target_root, ignore_errors=True)
                tmp_root.mkdir(parents=True, exist_ok=True)
                zf.extractall(tmp_root)

                # Strip wrapper: if zip has a single top-level dir matching mod_name,
                # move its children up to target_root (this is the BREEDING HELPER shape:
                # zip root contains "BreedingHelper/Scripts/main.lua" + "BreedingHelper/enabled.txt")
                top = [p for p in tmp_root.iterdir() if not p.name.startswith(".")]
                if (len(top) == 1
                        and top[0].is_dir()
                        and top[0].name == mod_name):
                    inner = top[0]
                    inner.rename(target_root)
                else:
                    # No wrapper — just rename tmp dir to target
                    tmp_root.rename(target_root)

                # Cleanup leftover tmp (if rename target was already gone)
                if tmp_root.exists() and tmp_root != target_root:
                    shutil.rmtree(tmp_root, ignore_errors=True)

                # Ensure enabled.txt exists
                et = target_root / "enabled.txt"
                if not et.exists():
                    et.write_bytes(b"")

                # UE4SS reads mods.txt at <win64>/ue4ss/Mods/mods.txt (NOT ue4ss/mods.txt)
                mods_txt = target_dir / "mods.txt"
                if mods_txt.exists():
                    txt = mods_txt.read_text(encoding="utf-8", errors="replace")
                    entry = f"{mod_name} : 1"
                    if entry not in txt and f"{mod_name}: 1" not in txt:
                        with open(mods_txt, "a", encoding="utf-8") as f:
                            f.write("\n" + entry + "\n")
            else:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.replace("\\", "/")
                    if name.startswith("../") or "/../" in name:
                        continue
                    fname = name.split("/")[-1]
                    out_path = target_dir / fname
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(out_path, "wb") as dst:
                        dst.write(src.read())
        return True, f"{role}: installed to {target_dir if not comp.get('needs_ue4ss', True) else (target_dir / mod_name)} {backup_msg}".rstrip()
    except Exception as e:
        return False, f"{role}: install failed: {e}"


def _uninstall_component(mod: dict, comp: dict, palworld_path: str, role: str) -> tuple[bool, str]:
    """Uninstall ONE component. Returns (success, message)."""
    if comp.get("needs_ue4ss", True):
        target_dir = Path(palworld_path) / "Pal" / "Binaries" / "Win64" / "ue4ss" / "Mods"
        mod_name = mod.get("name", "unknown")
        mod_root = target_dir / mod_name
        if not mod_root.exists():
            return False, f"{role}: not installed at {mod_root}"
        try:
            import shutil
            shutil.rmtree(mod_root, ignore_errors=True)
            # UE4SS reads mods.txt at <win64>/ue4ss/Mods/mods.txt (NOT ue4ss/mods.txt)
            mods_txt = target_dir / "mods.txt"
            if mods_txt.exists():
                txt = mods_txt.read_text(encoding="utf-8", errors="replace")
                lines = [
                    ln for ln in txt.splitlines()
                    if ln.strip().split(":")[0].strip() != mod_name
                ]
                mods_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True, f"{role}: removed {mod_root}"
        except Exception as e:
            return False, f"{role}: uninstall failed: {e}"
    files = comp.get("files", [])
    removed = 0
    for f in files:
        fname = f.split("/")[-1]
        for d in [
            Path(palworld_path) / "Pal" / "Content" / "Paks" / "~mods",
            Path(palworld_path) / "Pal" / "Content" / "Paks",
        ]:
            p = d / fname
            if p.exists():
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
    if removed:
        return True, f"{role}: removed {removed} files"
    return False, f"{role}: no files found"


def _is_component_installed(comp: dict, palworld_path: str, mod_name: str) -> bool:
    """Check if a single component is installed."""
    if comp.get("needs_ue4ss", True):
        # UE4SS Lua mod: look in ue4ss/Mods/<name>/ folder
        target = Path(palworld_path) / "Pal" / "Binaries" / "Win64" / "ue4ss" / "Mods" / mod_name
        if target.exists():
            return True
        # ALSO check extract_to for UE4SS-using LogicMods (.pak in Paks/LogicMods/)
        extract_to = comp.get("extract_to", "")
        if extract_to:
            base = Path(palworld_path) / extract_to
            for f in comp.get("files", []):
                if (base / f.split("/")[-1]).exists():
                    return True
        return False
    # Plain .pak mod: respect extract_to if present, else fall back to defaults
    candidates = []
    extract_to = comp.get("extract_to", "")
    if extract_to:
        candidates.append(Path(palworld_path) / extract_to)
    candidates += [
        Path(palworld_path) / "Pal" / "Content" / "Paks" / "~mods",
        Path(palworld_path) / "Pal" / "Content" / "Paks",
    ]
    for f in comp.get("files", []):
        fname = f.split("/")[-1]
        for d in candidates:
            if (d / fname).exists():
                return True
    return False


def install_mod(mod: dict, palworld_path: str) -> tuple[bool, str]:
    """Install a mod: BOTH server AND client components if both exist.

    Returns (success, message). If all components succeed, returns True with
    a combined summary. If at least one succeeds, returns True with details
    on what failed. If all fail, returns False.
    """
    comps = mod.get("components", {})
    if not comps:
        return False, "no components"

    # Pre-check: if any component needs UE4SS, refuse without it installed
    needs_ue4ss = any(c.get("needs_ue4ss", True) for c in comps.values())
    if needs_ue4ss:
        s = check_ue4ss(palworld_path)
        if not s.get("installed"):
            return False, "需要先安裝 UE4SS（請用上方「🚀 一鍵安裝 UE4SS」按鈕）"

    results = []
    for role, comp in comps.items():
        ok, msg = _install_component(mod, comp, palworld_path, role)
        results.append((role, ok, msg))

    succeeded = [r[0] for r in results if r[1]]
    failed = [(r[0], r[2]) for r in results if not r[1]]

    if not succeeded:
        return False, "; ".join(r[1] for r in failed)

    # Record install state for verify/auto-update
    mod_name = mod.get("name", "unknown")
    record_mod_installed(mod_name, mod.get("version", ""), succeeded)

    summary = f"{', '.join(succeeded)} installed"
    if failed:
        summary += f" (failed: {', '.join(r[0] for r in failed)})"
    return True, summary


def uninstall_mod(mod: dict, palworld_path: str) -> tuple[bool, str]:
    """Uninstall a mod: BOTH server AND client components if both exist.

    A component that wasn't installed is treated as a no-op (not a failure).
    """
    comps = mod.get("components", {})
    if not comps:
        return False, "no components"

    results = []
    for role, comp in comps.items():
        ok, msg = _uninstall_component(mod, comp, palworld_path, role)
        results.append((role, ok, msg))

    succeeded = [r[0] for r in results if r[1]]
    if not succeeded:
        return False, "nothing to remove"

    # Remove from install state
    mod_name = mod.get("name", "unknown")
    record_mod_uninstalled(mod_name)

    return True, f"{', '.join(succeeded)} removed"


def is_mod_installed(mod: dict, palworld_path: str) -> bool:
    """Check if a mod is fully installed: ALL components must be present."""
    if not palworld_path:
        return False
    comps = mod.get("components", {})
    if not comps:
        return False
    mod_name = mod.get("name", "unknown")
    for role, comp in comps.items():
        if not _is_component_installed(comp, palworld_path, mod_name):
            return False
    return True


# ===========================================================================
# Install state tracking + version check + verify + auto-update
# ===========================================================================

STATE_FILE_NAME = "friend_installer_state.json"
STATE_VERSION = 1


def _state_file_path() -> Path:
    """Path to the state file. Lives next to the running .exe (or __file__)."""
    try:
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent
    except Exception:
        base = Path.cwd()
    return base / STATE_FILE_NAME


def load_installed_state() -> dict:
    """Read the install state file. Returns empty dict on error/missing."""
    path = _state_file_path()
    if not path.exists():
        return {"version": STATE_VERSION, "mods": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "mods" not in data:
            return {"version": STATE_VERSION, "mods": {}}
        return data
    except Exception:
        return {"version": STATE_VERSION, "mods": {}}


def save_installed_state(state: dict) -> bool:
    """Atomically write the state file. Returns True on success."""
    path = _state_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        tmp.replace(path)
        return True
    except Exception as e:
        print(f"[state] save failed: {e!r}", file=sys.stderr)
        return False


def record_mod_installed(mod_name: str, version: str, components: list) -> bool:
    """Mark a mod as installed with its current version + components."""
    state = load_installed_state()
    state.setdefault("mods", {})
    state["mods"][mod_name] = {
        "version": version or "",
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "components": list(components or []),
    }
    return save_installed_state(state)


def record_mod_uninstalled(mod_name: str) -> bool:
    """Remove a mod from the install state."""
    state = load_installed_state()
    if mod_name in state.get("mods", {}):
        del state["mods"][mod_name]
        return save_installed_state(state)
    return True


def get_installed_mod_info(mod_name: str) -> dict | None:
    """Return installed info dict for a mod, or None if never recorded."""
    state = load_installed_state()
    return state.get("mods", {}).get(mod_name)


def _normalize_version(v: str) -> str:
    """Normalize version string for comparison. Lowercase + strip 'v' prefix + strip whitespace."""
    if not v:
        return ""
    s = v.strip().lower()
    if s.startswith("v"):
        s = s[1:]
    return s


def is_upgrade_available(installed_version: str, catalog_version: str) -> bool:
    """Heuristic: True if catalog_version looks newer than installed_version.

    Conservative: only returns True when both look like semver-ish strings
    (e.g. '1.0.0' or '1.2') and the catalog version is greater. If they
    look unrelated (e.g. 'v1.1+v2' vs 'v1.2+fix'), returns False to avoid
    false positives.
    """
    a = _normalize_version(installed_version)
    b = _normalize_version(catalog_version)
    if not a or not b or a == b:
        return False
    # Both must be digit-led for safe comparison
    if not (a[0].isdigit() and b[0].isdigit()):
        return False
    # Compare dotted parts as ints
    def parts(s):
        out = []
        for p in s.split("."):
            digits = ""
            for c in p:
                if c.isdigit():
                    digits += c
                else:
                    break
            try:
                out.append(int(digits) if digits else 0)
            except Exception:
                out.append(0)
        return out
    pa, pb = parts(a), parts(b)
    n = max(len(pa), len(pb))
    pa += [0] * (n - len(pa))
    pb += [0] * (n - len(pb))
    return pb > pa


def verify_all_mods(catalog: dict, palworld_path: str) -> list[dict]:
    """Verify each mod in the catalog against on-disk state.

    Returns a list of dicts:
      [{ name, display, installed_version, catalog_version, status,
         files_ok, components_ok, message }, ...]
    status is one of: 'not_installed', 'up_to_date', 'upgrade_available',
                       'version_unknown', 'files_missing', 'hash_mismatch'
    """
    out = []
    mods = (catalog or {}).get("mods", {}) or {}
    for name, mod in mods.items():
        display = mod.get("display_name_zh") or mod.get("display_name", name)
        catalog_version = mod.get("version", "")
        info = get_installed_mod_info(name) or {}
        installed_version = info.get("version", "")
        comps = mod.get("components", {}) or {}

        # Files-on-disk check
        files_ok = True
        comps_ok = True
        missing = []
        for role, comp in comps.items():
            extract_to = comp.get("extract_to", "")
            if not extract_to:
                continue
            base = Path(palworld_path) / extract_to
            # UE4SS mods put their files in a <modname>/ subfolder
            # (e.g. ue4ss/Mods/BreedingHelper/Scripts/main.lua), while
            # plain .pak mods (LogicMod, Paks mod) drop files directly
            # in extract_to (e.g. ~mods/BreedingHelperUI_P.pak).
            # Heuristic: only UE4SS Lua mods (extract_to ends with ue4ss/Mods)
            # nest their files in a <modname>/ subfolder. LogicMods and
            # plain Pak mods drop files directly in extract_to.
            et_norm = extract_to.replace("\\", "/").rstrip("/")
            if comp.get("needs_ue4ss", True) and et_norm.endswith("ue4ss/Mods"):
                base = base / name
            for f in comp.get("files", []):
                target = base / f
                if not target.exists():
                    files_ok = False
                    comps_ok = False
                    # Show the path the function actually checked
                    rel = str(target.relative_to(Path(palworld_path)))
                    missing.append(rel)

        if not is_mod_installed(mod, palworld_path):
            status = "not_installed"
            message = "未安裝"
        elif not files_ok:
            status = "files_missing"
            message = f"檔案缺失: {', '.join(missing)}"
        elif not installed_version:
            status = "version_unknown"
            message = "已安裝但無版本記錄（之前可能手動裝的）"
        elif not catalog_version:
            status = "up_to_date"
            message = f"已安裝 v{installed_version}（catalog 無版本）"
        elif installed_version == catalog_version:
            status = "up_to_date"
            message = f"v{installed_version}（最新）"
        elif is_upgrade_available(installed_version, catalog_version):
            status = "upgrade_available"
            message = f"v{installed_version} → v{catalog_version}（可更新）"
        else:
            # Same or different but not "upgrade"
            status = "up_to_date"
            message = f"v{installed_version}（catalog: v{catalog_version}）"

        out.append({
            "name": name,
            "display": display,
            "installed_version": installed_version,
            "catalog_version": catalog_version,
            "status": status,
            "files_ok": files_ok,
            "components_ok": comps_ok,
            "message": message,
        })
    return out
