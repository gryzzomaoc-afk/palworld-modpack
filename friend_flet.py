"""Palworld Friend Mod Installer — Flet (Flutter for Python) edition.

UI: Material Design, dark theme, single-page layout.
Backend logic lives in friend_common.py (shared with tkinter version).

Run: flet run friend_flet.py
Build: flet pack friend_flet.py --name PalworldFriendModInstaller --icon installer.ico
"""
from __future__ import annotations

import base64
import os
import sys
import threading
import time
from pathlib import Path

import flet as ft

from friend_common import (
    CONFIG_FILE, DEFAULT_CATALOG_URL,
    load_config, save_config,
    detect_steam, fetch_catalog,
    check_ue4ss, check_ue4ss_health, install_ue4ss, uninstall_ue4ss,
    install_mod, uninstall_mod, is_mod_installed, verify_mod_install,
    fetch_mods_from_github, GITHUB_DISCOVERY_SCHEME,
    UE4SS_URL,
)

# --- Color palette (dark theme) ---
BG_DARK = "#0a0e0c"
BG_CARD = "#15171c"
BG_CARD_HOVER = "#1c1f26"
BORDER = "#2a2d36"
TEXT_PRIMARY = "#e8eaed"
TEXT_SECONDARY = "#9aa0a6"
TEXT_MUTED = "#5f6368"
ACCENT = "#7c4dff"  # palworld purple
ACCENT_HOVER = "#9b7bff"
SUCCESS = "#4caf50"
WARNING = "#ff9800"
ERROR = "#f44336"
INFO = "#29b6f6"

# --- App title (locked, per user request) ---
APP_TITLE = "帕魯安裝工具 1.0.7 FOR 帕魯不打烊"


def main(page: ft.Page):
    # --- Page config ---
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_DARK
    page.padding = 0
    page.window.width = 820
    page.window.height = 660
    page.window.min_width = 720
    page.window.min_height = 540

    # --- Runtime window icon (needs a .ico file path, not base64) ---
    # Build: `flet pack ... --add-data "installer.ico;."` bundles the .ico
    # Runtime: pyinstaller onefile extracts to sys._MEIPASS
    try:
        if getattr(sys, "frozen", False):
            ico_candidate = Path(sys._MEIPASS) / "installer.ico"
        else:
            ico_candidate = Path(__file__).parent / "installer.ico"
        if ico_candidate.exists():
            page.window.icon = str(ico_candidate)
    except Exception as e:
        print(f"window icon set failed: {e}")

    # --- Theme ---
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary="#ffffff",
            secondary=ACCENT,
            surface=BG_CARD,
            on_surface=TEXT_PRIMARY,
        ),
        use_material3=True,
    )

    # --- State ---
    config = load_config()
    state = {
        "steam_path": None,
        "palworld_path": None,
        "catalog": None,
        "loading": False,
    }

    # --- UI components (built below) ---
    steam_status_text = ft.Text(
        "偵測中…",
        size=13,
        color=TEXT_SECONDARY,
    )
    steam_path_text = ft.Text(
        "",
        size=12,
        color=TEXT_MUTED,
        selectable=True,
    )
    catalog_sync_btn = ft.TextButton(
        "同步 MOD 資料庫",
        icon=ft.Icons.REFRESH,
        style=ft.ButtonStyle(color=ACCENT),
    )
    catalog_loading = ft.ProgressRing(
        width=16,
        height=16,
        stroke_width=2,
        color=ACCENT,
        visible=False,
    )
    ue4ss_status_text = ft.Text("偵測中…", size=13, color=TEXT_SECONDARY)
    ue4ss_install_btn = ft.ElevatedButton(
        "🚀 一鍵安裝 UE4SS",
        icon=ft.Icons.ROCKET_LAUNCH,
        disabled=True,
        style=ft.ButtonStyle(
            bgcolor=ACCENT,
            color="#ffffff",
        ),
    )
    ue4ss_uninstall_btn = ft.OutlinedButton(
        "🗑 卸載 UE4SS",
        icon=ft.Icons.DELETE_OUTLINE,
        disabled=True,
        visible=False,
        style=ft.ButtonStyle(
            color=WARNING,
            side=ft.BorderSide(1, WARNING),
        ),
    )
    ue4ss_open_btn = ft.OutlinedButton(
        "📂 開啟 Win64 資料夾",
        icon=ft.Icons.FOLDER_OPEN,
        style=ft.ButtonStyle(
            color=INFO,
            side=ft.BorderSide(1, INFO),
        ),
    )
    ue4ss_verify_btn = ft.OutlinedButton(
        "🔎 驗證 UE4SS",
        icon=ft.Icons.HEALTH_AND_SAFETY,
        style=ft.ButtonStyle(
            color=INFO,
            side=ft.BorderSide(1, INFO),
        ),
    )
    ue4ss_path_text = ft.Text(
        "",
        size=11,
        color=TEXT_MUTED,
        selectable=True,
    )
    mods_column = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )
    status_text = ft.Text(
        "準備就緒",
        size=12,
        color=TEXT_MUTED,
    )

    def set_status(msg: str, level: str = "info"):
        color = {
            "info": TEXT_SECONDARY,
            "success": SUCCESS,
            "warning": WARNING,
            "error": ERROR,
        }.get(level, TEXT_SECONDARY)
        status_text.value = msg
        status_text.color = color
        try:
            page.update()
        except Exception:
            pass

    def show_snack(msg: str, level: str = "info"):
        color = {
            "info": ACCENT,
            "success": SUCCESS,
            "warning": WARNING,
            "error": ERROR,
        }.get(level, ACCENT)
        try:
            # Flet 0.86.4 uses page.show_dialog(ft.SnackBar(...)) instead of
            # page.show_snack_bar (the latter is only in newer Flet versions).
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(msg, color="#ffffff"),
                    bgcolor=color,
                    duration=3500,
                )
            )
        except Exception:
            pass

    # --- Steam detection ---
    def do_detect_steam(e=None):
        set_status("正在偵測 Steam 路徑…", "info")
        steam, pal = detect_steam()
        state["steam_path"] = steam
        state["palworld_path"] = pal
        if pal:
            steam_status_text.value = "✓ 已找到 Palworld"
            steam_status_text.color = SUCCESS
            steam_path_text.value = pal
            steam_path_text.color = TEXT_SECONDARY
            ue4ss_install_btn.disabled = False
        else:
            steam_status_text.value = "✗ 找不到 Palworld 安裝路徑"
            steam_status_text.color = ERROR
            steam_path_text.value = "(請確認 Steam 已安裝 Palworld)"
            steam_path_text.color = TEXT_MUTED
            ue4ss_install_btn.disabled = True
        page.update()
        do_check_ue4ss()
        if state["palworld_path"]:
            set_status("✓ Steam 偵測完成，按上面「同步」鈕下載 mod 清單", "success")
        else:
            set_status("找不到 Palworld，無法繼續", "error")

    # --- UE4SS prereq ---
    def do_check_ue4ss(e=None):
        s = check_ue4ss(state["palworld_path"])
        state["ue4ss_status"] = s
        # Always show the actual checked path
        if state.get("palworld_path"):
            base = Path(state["palworld_path"]) / "Pal" / "Binaries" / "Win64"
            ue4ss_path_text.value = f"檢查路徑: {base}"
        else:
            ue4ss_path_text.value = ""
        if s.get("error"):
            ue4ss_status_text.value = "— (略過，需先偵測到 Palworld)"
            ue4ss_status_text.color = TEXT_MUTED
            ue4ss_install_btn.disabled = True
            ue4ss_install_btn.text = "🚀 一鍵安裝 UE4SS"
            ue4ss_uninstall_btn.visible = False
        elif s["installed"]:
            ue4ss_status_text.value = f"✓ 已安裝 UE4SS ({s.get('marker', '?')})"
            ue4ss_status_text.color = SUCCESS
            ue4ss_install_btn.text = "🔄 重新安裝 UE4SS"
            ue4ss_install_btn.disabled = False
            ue4ss_uninstall_btn.visible = True
            ue4ss_uninstall_btn.disabled = False
        else:
            ue4ss_status_text.value = "✗ 未在本機 Palworld 安裝 UE4SS"
            ue4ss_status_text.color = ERROR
            ue4ss_install_btn.text = "🚀 一鍵安裝 UE4SS"
            ue4ss_install_btn.disabled = False
            ue4ss_uninstall_btn.visible = False
        page.update()

    def do_install_ue4ss(e=None):
        if not state["palworld_path"]:
            show_snack("請先偵測到 Palworld 路徑", "error")
            return
        ue4ss_install_btn.disabled = True
        ue4ss_uninstall_btn.disabled = True
        set_status("正在下載 UE4SS…", "info")
        show_snack("開始下載 UE4SS (約 7MB)", "info")

        def work():
            ok, msg = install_ue4ss(state["palworld_path"])
            if ok:
                set_status("✓ " + msg, "success")
                show_snack("UE4SS 安裝完成", "success")
            else:
                set_status("✗ " + msg, "error")
                show_snack("UE4SS 安裝失敗：" + msg, "error")
            do_check_ue4ss()
            render_mods()

        threading.Thread(target=work, daemon=True).start()

    def do_uninstall_ue4ss(e=None):
        if not state["palworld_path"]:
            return
        ue4ss_install_btn.disabled = True
        ue4ss_uninstall_btn.disabled = True
        set_status("正在卸載 UE4SS…", "info")

        def work():
            ok, msg = uninstall_ue4ss(state["palworld_path"])
            if ok:
                set_status("✓ " + msg, "success")
                show_snack("UE4SS 已卸載", "success")
            else:
                set_status("✗ " + msg, "error")
                show_snack("卸載失敗：" + msg, "error")
            do_check_ue4ss()
            render_mods()

        threading.Thread(target=work, daemon=True).start()

    # Wire UE4SS buttons (catalog button wired later, after do_refresh_catalog is defined)
    def do_open_ue4ss_folder(e=None):
        if not state.get("palworld_path"):
            return
        import subprocess
        folder = Path(state["palworld_path"]) / "Pal" / "Binaries" / "Win64"
        try:
            subprocess.Popen(["explorer", str(folder)])
        except Exception as ex:
            show_snack(f"開啟失敗: {ex}", "error")

    def do_verify_ue4ss(e=None):
        """Run check_ue4ss_health + verify each installed mod, show results."""
        if not state.get("palworld_path"):
            show_snack("請先偵測 Palworld 路徑", "error")
            return
        health = check_ue4ss_health(state["palworld_path"])
        lines = []
        if health["ok"]:
            lines.append("✓ UE4SS 健全檢查: 全部通過")
        else:
            lines.append("✗ UE4SS 健全檢查: 有問題")
            for issue in health["issues"]:
                lines.append(f"   - {issue}")
        for c in health["checks"]:
            mark = "✓" if c["ok"] else ("✗" if c.get("severity") == "required" else "·")
            lines.append(f"   {mark} {c['name']}")

        # Verify each installed mod
        cat = state.get("catalog")
        if cat and cat.get("mods"):
            lines.append("")
            lines.append("=== 已安裝 mod 驗證 ===")
            any_mod_failed = False
            for mod_name, mod in cat["mods"].items():
                if is_mod_installed(mod, state["palworld_path"]):
                    v = verify_mod_install(mod, state["palworld_path"])
                    if v["ok"]:
                        lines.append(f"✓ {mod_name}: 全部檔案到位")
                    else:
                        any_mod_failed = True
                        lines.append(f"✗ {mod_name}: 有問題")
                        for role, info in v["components"].items():
                            for issue in info.get("issues", []):
                                lines.append(f"   - [{role}] {issue}")
            if not any_mod_failed and not any(is_mod_installed(m, state["palworld_path"]) for m in (cat.get("mods") or {}).values()):
                lines.append("(沒有已安裝的 mod)")

        title = "驗證結果"
        msg = "\n".join(lines)
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(msg, selectable=True, size=12),
            actions=[ft.TextButton("關閉", on_click=lambda e: page.pop_dialog())],
        )
        page.show_dialog(dlg)

    ue4ss_install_btn.on_click = do_install_ue4ss
    ue4ss_uninstall_btn.on_click = do_uninstall_ue4ss
    ue4ss_open_btn.on_click = do_open_ue4ss_folder
    ue4ss_verify_btn.on_click = do_verify_ue4ss

    # --- Catalog fetch (with visible loading state) ---
    def do_refresh_catalog(e=None):
        # Guard against re-entry
        if state.get("syncing"):
            return
        state["syncing"] = True
        url = config.get("catalog_url") or DEFAULT_CATALOG_URL
        # Show spinner on the button + update status
        catalog_sync_btn.disabled = True
        catalog_sync_btn.text = "同步中..."
        catalog_loading.visible = True
        set_status("正在同步 MOD 資料庫...", "info")
        page.update()

        def work():
            try:
                # v1.0.8+: GitHub folder-discovery pipeline.  When the
                # default URL is the GITHUB_DISCOVERY_SCHEME sentinel
                # (or a user-pinned value matches it), call
                # fetch_mods_from_github() instead of fetching a single
                # friend-catalog.json.  Custom file:// or http(s):// URLs
                # still fall through to fetch_catalog() so forks / local
                # tests keep working.
                if url.startswith(GITHUB_DISCOVERY_SCHEME):
                    cat = fetch_mods_from_github()
                else:
                    cat = fetch_catalog(url)
                state["catalog"] = cat
                mods = cat.get("mods", {}) if isinstance(cat, dict) else {}
                state["syncing"] = False
                catalog_sync_btn.disabled = False
                catalog_sync_btn.text = "同步 MOD 資料庫"
                catalog_loading.visible = False
                set_status(f"✓ 同步成功，找到 {len(mods)} 個 mod", "success")
                render_mods()
            except Exception as err:
                state["syncing"] = False
                catalog_sync_btn.disabled = False
                catalog_sync_btn.text = "同步 MOD 資料庫"
                catalog_loading.visible = False
                set_status("✗ 同步失敗: " + str(err), "error")
                show_snack("Catalog 同步失敗：" + str(err), "error")
                page.update()

        threading.Thread(target=work, daemon=True).start()

    # Wire catalog button (delayed - do_refresh_catalog must be defined first)
    catalog_sync_btn.on_click = do_refresh_catalog

    # --- Mod details dialog (Chinese features + usage) ---
    def show_mod_details(name, mod):
        """Open a dialog showing the mod's features_zh + usage_zh in detail."""
        display = mod.get("display_name_zh") or mod.get("display_name", name)
        version = mod.get("version", "?")
        source = mod.get("source", "")
        features = mod.get("features_zh") or []
        usage = mod.get("usage_zh") or ""

        body_sections = []

        if features:
            feat_lines = "\n".join(f"  • {f}" for f in features)
            body_sections.append(ft.Text("功能特色", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY))
            body_sections.append(ft.Container(height=4))
            body_sections.append(ft.Text(feat_lines, size=12, color=TEXT_SECONDARY))

        if usage:
            if body_sections:
                body_sections.append(ft.Container(height=14))
            body_sections.append(ft.Text("使用說明", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY))
            body_sections.append(ft.Container(height=4))
            body_sections.append(ft.Text(usage, size=12, color=TEXT_SECONDARY, selectable=True))

        if source:
            if body_sections:
                body_sections.append(ft.Container(height=14))
            body_sections.append(ft.Text("來源", size=11, color=TEXT_MUTED, weight=ft.FontWeight.BOLD))
            body_sections.append(ft.Text(source, size=10, color=TEXT_MUTED, selectable=True))

        dlg = ft.AlertDialog(
            title=ft.Text(f"{display}（v{version}）"),
            content=ft.Container(
                content=ft.Column(body_sections, tight=True, scroll=ft.ScrollMode.AUTO),
                width=480,
            ),
            actions=[
                ft.TextButton("關閉", on_click=lambda e: page.pop_dialog()),
            ],
        )
        page.show_dialog(dlg)

    # --- Mods rendering ---
    def render_mods():
        mods_column.controls.clear()
        cat = state.get("catalog")
        if not cat:
            mods_column.controls.append(
                ft.Container(
                    content=ft.Text("(尚未同步 Catalog)", color=TEXT_MUTED, size=12),
                    padding=10,
                )
            )
            page.update()
            return
        mods_dict = cat.get("mods", {}) or {}
        if not mods_dict:
            mods_column.controls.append(
                ft.Container(
                    content=ft.Text("(Catalog 是空的)", color=TEXT_MUTED, size=12),
                    padding=10,
                )
            )
            page.update()
            return
        for name, mod in mods_dict.items():
            # Prefer Chinese display name / description when available
            display = mod.get("display_name_zh") or mod.get("display_name", name)
            version = mod.get("version", "?")
            desc = mod.get("description_zh") or mod.get("description", "")
            installed = is_mod_installed(mod, state.get("palworld_path"))
            has_details = bool(mod.get("features_zh") or mod.get("usage_zh"))
            mods_column.controls.append(
                build_mod_card(name, mod, display, version, desc, installed, has_details)
            )
        page.update()

    def build_mod_card(name, mod, display, version, desc, installed, has_details=False):
        status_chip = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if installed else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        size=14,
                        color=SUCCESS if installed else TEXT_MUTED,
                    ),
                    ft.Text(
                        "已安裝" if installed else "未安裝",
                        size=11,
                        color=SUCCESS if installed else TEXT_MUTED,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
        )

        def on_install(e):
            if not state.get("palworld_path"):
                show_snack("請先偵測 Palworld 路徑", "error")
                return
            btn.disabled = True
            set_status(f"正在安裝 {display}…", "info")

            def work():
                ok, msg = install_mod(mod, state["palworld_path"])
                if ok:
                    set_status(f"✓ {display} 安裝完成", "success")
                    show_snack(f"{display} 安裝完成", "success")
                else:
                    set_status(f"✗ {display} 安裝失敗: {msg}", "error")
                    show_snack(f"{display} 安裝失敗: {msg}", "error")
                render_mods()

            threading.Thread(target=work, daemon=True).start()

        def on_uninstall(e):
            if not state.get("palworld_path"):
                return
            btn.disabled = True
            set_status(f"正在卸載 {display}…", "info")

            def work():
                ok, msg = uninstall_mod(mod, state["palworld_path"])
                if ok:
                    set_status(f"✓ {display} 已卸載", "success")
                    show_snack(f"{display} 已卸載", "success")
                else:
                    set_status(f"✗ {display} 卸載失敗: {msg}", "error")
                    show_snack(f"{display} 卸載失敗: {msg}", "error")
                render_mods()

            threading.Thread(target=work, daemon=True).start()

        if installed:
            btn = ft.ElevatedButton(
                "卸載",
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=on_uninstall,
                style=ft.ButtonStyle(
                    bgcolor=BG_CARD_HOVER,
                    color=WARNING,
                    side=ft.BorderSide(1, WARNING),
                ),
            )
        else:
            btn = ft.ElevatedButton(
                "安裝",
                icon=ft.Icons.DOWNLOAD,
                on_click=on_install,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT,
                    color="#ffffff",
                ),
            )

        # "查看詳情" button — only show if mod has features_zh or usage_zh
        actions_row = [status_chip, btn]
        if has_details:
            actions_row.insert(
                0,
                ft.TextButton(
                    "查看詳情",
                    icon=ft.Icons.INFO_OUTLINE,
                    on_click=lambda e: show_mod_details(name, mod),
                    style=ft.ButtonStyle(color=ACCENT),
                ),
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(display, size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                            ft.Text(f"v{version}", size=11, color=TEXT_MUTED),
                                        ],
                                        spacing=8,
                                        tight=True,
                                    ),
                                    ft.Text(name, size=10, color=TEXT_MUTED, italic=True),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            *actions_row,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=6),
                    ft.Text(desc, size=12, color=TEXT_SECONDARY, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                spacing=0,
            ),
            padding=14,
            border_radius=10,
            bgcolor=BG_CARD,
            border=ft.Border.all(1, BORDER),
            ink=True,
        )

    # --- Build layout ---
    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PETS, color=ACCENT, size=28),
                ft.Column(
                    [
                        ft.Text(APP_TITLE, size=18, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Text("一鍵安裝 / 卸載朋友端 mod · Powered by Flet", size=10, color=TEXT_MUTED),
                    ],
                    spacing=0,
                ),
            ],
            spacing=12,
        ),
        padding=ft.Padding(20, 16, 20, 16),
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
    )

    steam_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCATION_ON, color=ACCENT, size=18),
                        ft.Text("Steam / Palworld 偵測", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "重新偵測 Steam 路徑",
                            icon=ft.Icons.REFRESH,
                            on_click=do_detect_steam,
                            style=ft.ButtonStyle(color=ACCENT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=6),
                steam_status_text,
                ft.Container(height=2),
                steam_path_text,
            ],
            spacing=0,
        ),
        padding=14,
        border_radius=10,
        bgcolor=BG_CARD,
        border=ft.Border.all(1, BORDER),
    )

    ue4ss_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING_AMBER, color=WARNING, size=18),
                        ft.Text("前置需求 (UE4SS mod loader)", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ],
                    spacing=8,
                ),
                ft.Container(height=6),
                ue4ss_status_text,
                ft.Container(height=10),
                ft.Row(
                    [ue4ss_install_btn, ue4ss_uninstall_btn, ue4ss_open_btn, ue4ss_verify_btn],
                    spacing=8,
                    wrap=True,
                ),
                ft.Container(height=6),
                ue4ss_path_text,
            ],
            spacing=0,
        ),
        padding=14,
        border_radius=10,
        bgcolor=BG_CARD,
        border=ft.Border.all(1, BORDER),
    )

    catalog_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.CLOUD_SYNC, color=ACCENT, size=18),
                        ft.Text("MOD 資料庫", size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Container(expand=True),
                        catalog_loading,
                        catalog_sync_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                ft.Text("可安裝的 Mod:", size=12, color=TEXT_SECONDARY),
                ft.Container(height=8),
                ft.Container(
                    content=mods_column,
                    height=240,
                    border=ft.Border.all(1, BORDER),
                    border_radius=8,
                    padding=8,
                    bgcolor=BG_DARK,
                ),
            ],
            spacing=0,
        ),
        padding=14,
        border_radius=10,
        bgcolor=BG_CARD,
        border=ft.Border.all(1, BORDER),
    )

    status_bar = ft.Container(
        content=status_text,
        padding=ft.Padding(16, 8, 16, 8),
        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
        bgcolor=BG_CARD,
    )

    body = ft.Container(
        content=ft.Column(
            [
                steam_card,
                ue4ss_card,
                catalog_card,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=14,
        expand=True,
    )

    page.add(
        ft.Column(
            [
                header,
                body,
                status_bar,
            ],
            spacing=0,
            expand=True,
        )
    )

    # --- Initial scan ---
    def initial():
        time.sleep(0.2)
        do_detect_steam()

    threading.Thread(target=initial, daemon=True).start()


if __name__ == "__main__":
    ft.app(target=main)
