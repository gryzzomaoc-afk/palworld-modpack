# Changelog (更新日誌)

All dates in GMT+8.

## v1.0.9 (2026-08-02)

### Removed (移除)
- **PlayerRadar-Server** + **PlayerRadar-Client** removed from `mods/`.
  - User-feedback-driven: too experimental, required a complex server-side install
    (samba share + UE4SS on dedicated server) that turned out to be too brittle
    for friends to set up reliably.
  - Friend installer auto-discovers 2 mods now: **BreedingHelper** + **UltraWeather**.

### Notes
- No .exe rebuild required — the v1.0.8 installer is repo-driven, so friends
  who already downloaded `PalworldFriendModInstaller.exe` will see the trimmed
  catalog the next time they click "同步 MOD 資料庫".
- If a friend had already installed PlayerRadar on their local client, the
  mod folder is still there but the installer will no longer offer updates
  or verify it. They can delete `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Client\`
  manually to clean up.

## v1.0.8 (2026-08-02)

### Added (新增)
- **Repo-driven mod discovery** — `fetch_mods_from_github()` lists `mods/` via
  the GitHub Contents API and pulls each `manifest.json`. Adding a new mod no
  longer requires rebuilding the .exe.
- **PlayerRadar-Server** — UE4SS Lua mod for dedicated server; lists all
  online players' positions to a JSON file.
- **PlayerRadar-Client** — UE4SS Lua mod for client; reads the server JSON
  and renders in-game map markers (M key to refresh, T key to teleport).
- **UltraWeather** — UE4SS Lua mod (Fr4nsson workshop 4504); Sky Creator
  schedule, volumetric clouds, dynamic height fog.

### Removed (移除)
- **features_zh UI render** — per user decision "client downloads .exe ONCE",
  reverted to keep the .exe stable. Feature descriptions remain in each
  mod's `manifest.json` for future use.

### Fixed (修正)
- **PlayerRadar config.lua** — moved into `Scripts/` so `require("config")`
  resolves (BREEDER-style structure, see UE4SS Lua file structure gotcha).
- **PlayerRadar find pattern** — replaced `StaticFindObject` with
  `FindAllOf("PalPlayerCharacter")` for cross-build compatibility.

### Notes
- v1.0.8 release asset uploaded as raw PyInstaller binary (88.88 MB, SHA256
  `bafa13aac6693559e85c9f456995f977c1808f3ffdef385d776f894ae114fa2c`).
- Release body and CHANGELOG switched to English-only to avoid GitHub
  API mojibake.
- Friend installer still ships only **BreedingHelper** + **UltraWeather**
  to regular friends as of v1.0.9 (PlayerRadar was a v1.0.8 experiment).

## v1.0.7 (2026-08-02)

### Added (新增)
- **Pal running check** — install_ue4ss / uninstall_ue4ss / _install_component all check if Palworld.exe is running first; refuse to proceed if so (prevents .pak / .dll lock issues).
- **Auto-backup** — before any destructive install/uninstall, snapshot the existing mod folder to `Mods/<name>.bak-<timestamp>` (or `ue4ss.bak-<timestamp>` for the whole UE4SS dir). User can manually restore if needed.
- **UE4SS layout health check** (`check_ue4ss_health`) — verifies 5 critical files beyond just `UE4SS.dll`: `UE4SS-settings.ini`, `Mods/`, `Mods/shared/UEHelpers/UEHelpers.lua`, `Mods/mods.txt`.
- **Mod verification** (`verify_mod_install`) — after install, checks all `files[]` entries from the catalog exist at expected paths.
- **In-UI verify button** — verify button on the UE4SS card runs `check_ue4ss_health` + `verify_mod_install` for all installed mods, shows results in a dialog.
- **Auto-rollback on install failure** — if `install_ue4ss` layout verification fails, automatically restore from the backup snapshot so user isn't left with a broken install.

### Fixed (修正)
- **`_install_component` client branch bug** — `backup_msg` variable was not initialized in the client (non-UE4SS) path, causing `UnboundLocalError: backup_msg referenced before assignment` which made client installs report `ok=False` even though the file was actually written.
- **`verify_mod_install` SHA256 misuse** — was hashing on-disk files and comparing to the catalog zip-level SHA256 (which is the whole archive hash, not per-file). Now just checks file existence.
- **Catalog UTF-8 BOM + mojibake** — PowerShell `Set-Content -Encoding UTF8` prepends a UTF-8 BOM and the file had been re-saved with wrong encoding at some point. Catalog is now strict UTF-8 (no BOM) and Chinese characters verified correct.
- **Bundled catalog lookup** — `friend_common._default_catalog_path()` now checks `sys._MEIPASS` first (where PyInstaller / Flet onefile unpacks `--add-data` files), so the .exe no longer falls back to a broken GitHub catalog when the bundled one is right there.
- **Flet 0.86.4 API compatibility** — `page.show_snack_bar` → `page.show_dialog(ft.SnackBar(...))`; `page.open` → `page.show_dialog`; `data.decode("utf-8")` → `data.decode("utf-8-sig")` for catalog.

### Friend installer
- Single friend tool downloads ~60 MB self-contained `.exe` (Flet 0.86.4 + Python 3.11 embeddable).
- Catalog has only **BreedingHelper v1.1+v2** (CrazyChips custom build, includes the v2 try_hook_widget_tick fix that prevents the F8 crash on dedicated server).
- First-run SmartScreen warning documented in USAGE.md with bypass steps.

### Known issues
- Friend installer does NOT preserve user-customized Lua patches. If a friend needs to add their own Lua fix on top, they have to re-apply after install.
- `install_ue4ss` layout verification assumes the Okaetsu zip structure (UEHelpers at `Mods/shared/UEHelpers/UEHelpers.lua`). If upstream changes the layout, the verification will fail and the install will auto-rollback; would need to update `check_ue4ss_health` expected paths.

## v1.0.6 (2026-08-01)
- Initial complete release.
- friend_flet.py full Flet UI (dark theme, Flet 0.86.4).
- install_ue4ss downloads Okaetsu, extracts.
- install_mod handles UE4SS mod + .pak mod.
- SHA256 verification (zip-level).
- mods.txt append (not overwrite).
- enabled.txt auto-created.
