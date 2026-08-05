# Changelog (更新日誌)

All dates in GMT+8.

## v1.1.2 (2026-08-06) — mod added (no .exe rebuild needed)

### Added (新增)
- **SimpleBuildingBlueprints (簡易建築藍圖)** — Leafnwind 的 UE4SS Lua mod +
  LogicMods 組合包。蓋好的基地可以存成藍圖、一鍵複製 / 重建 / 給朋友分享。
  - 64 個 .lua + 150KB C++ DLL（v0.1.12）
  - 原位置吸附、Free Camera、碰撞 / 支撐 / 素材三重驗證
  - **Client-only**：所有計算本地，server 端零負擔
  - 64 KB LogicMods .pak
- **多 component manifest 支援** — `client`（UE4SS Lua mod）+ `client-assets`
  （LogicMods .pak）兩個 component，installer 會依序裝到對的位置
  - 自動建 `enabled.txt`、加 `BlueprintResearch : 1` 進 mods.txt
  - 驗證 / 卸載 / state 全部跟著更新

### Notes
- **不需重抓 zip**：v1.1.1 的 .exe 已經支援「repo-driven + 多 component」，
  按「同步 MOD 資料庫」就會看到第 5 張 mod 卡
- 朋友那邊開 sync → 看到「簡易建築藍圖」→ 一鍵安裝 → 自動裝兩個 component

## v1.1.1 (2026-08-04)

### Changed (優化)
- **同步 MOD 資料庫加速** — `fetch_mods_from_github()` 改用
  `ThreadPoolExecutor` 平行抓 manifest.json。4 個 mod 時從 2-3 秒
  壓到 **0.6-0.9 秒**（3 次實測 min 645ms / median 662ms / max 878ms）。
  TLS 握手從 4 次序列變 4 次並行，server 端 roundtrip 仍只有 1 次
  （GitHub Contents API 拿 mods/ 清單那步要先拿才能抓 manifest）。
- **Cap 並行度 8** — 預留 2x 成長空間，目前 4 個 mod 沒浪費。

### Fixed (修正)
- **Mod 詳情 dialog 版本標籤 double-v** — BreedingHelper 版本字串
  自帶 `v` 前綴 (`v1.1+v2`)，UI 又在前綴加一個 `v`，變 `vv1.1+v2`。
  新增 `_fmt_version()` 統一處理：已帶 `v` 不再加、未帶才加。
  影響：標題列、卡片的版本小字、「更新到 v…」按鈕。

### Notes
- 朋友需要重抓 zip 才能拿到加速版（UI 內 Python 直譯，不重 build 沒效）。
- 內部 User-Agent 從 `1.0.8` 升到 `1.1.1`（只是 log 標記用，GitHub 不在意）。

## v1.1.0 (2026-08-02)

### Added (新增)
- **YetAnotherMinimap (小地圖雷達)** — Paldar 非官方最新版的小地圖
  mod 加進 friend installer。顯示帕魯、寶箱、地下城、快速旅行、玩家
  基地、死亡位置、技能果樹、稀有帕魯、BOSS 等資訊。純 client-side，
  server 端不用裝。
- **BlueEyesChaosMaxDragon (青眼混沌龍 / Xenolord 替換)** — 純視覺
  mod，把 Xenolord 帕魯外觀換成《遊戲王》的「青眼混沌龍」。每個
  客戶端各自渲染，沒裝的朋友看到原本的 Xenolord。IP 屬於 Konami，
  mod by sv_boy。
- **Mod 卡片全中文化** — UI 改用 `display_name_zh` + `description_zh`
  顯示，catalog 預設就是繁體中文。
- **「查看詳情」按鈕** — 每張 mod 卡多一個 Info 按鈕，點下去跳出
  AlertDialog，裡面有完整「功能特色」bullet list + 「使用說明」段落
  + 來源連結。
- **每個 mod 加 `usage_zh` 欄位** — manifest 範例更新，所有 mod 都有
  完整的中文使用說明（熱鍵、設定路徑、注意事項）。
- **朋友 installer 重新打包成 .zip 發布** — 包含 .exe + SHA256.txt +
  使用說明.txt，下載一次就包含所有需要的東西。

### Friend installer
- 朋友工具 v1.1.0 — **4 個 mod 自動抓到**（BreedingHelper + UltraWeather +
  YetAnotherMinimap + BlueEyesChaosMaxDragon），全部中文卡片 + 中文使用說明。
- 下載連結：https://github.com/gryzzomaoc-afk/palworld-modpack/releases/download/v1.1.0/PalworldFriendModInstaller-v1.1.0.zip

### Fixed (修正)
- **Mod install 鎖定邏輯** — 當 mod 需要 UE4SS 但沒裝時，按鈕變成「🔒 需先裝
  UE4SS」鎖頭，點下去跳 snack 提示去上方裝 UE4SS。Server-side 也擋一層
  防止 bypass UI。
- **LogicMod 安裝偵測** — YAM 之前裝完顯示「未安裝」是因為 detect 函式只認
  `ue4ss/Mods/<name>/` 跟 `Paks/~mods/`，沒認 `Paks/LogicMods/`。修完讀
  manifest 的 `extract_to` 欄位。
- **YAM client.zip 重新包裝** — 之前是 .pak rename 成 .zip（installer 解
  zip 失敗），現在是真正含 .pak 的 zip。

### Added (驗證 + 自動更新)
- **🔍 驗證所有 MOD 按鈕** — catalog 卡右上有「🔍 驗證所有 MOD」，點下去
  跳 AlertDialog，列出每個 mod 的狀態：
  - ✓ 最新 — 已裝且等於 catalog 版本
  - ⚠ 可更新 — 裝了但有新版
  - ○ 未安裝
  - ✗ 檔案缺失 — 裝了但檔案不見
  - ? 無版本記錄 — 之前可能手動裝的
- **⬆️ 更新按鈕** — mod 卡如果已裝 + 有新版，按鈕區會多一個橘色
  「⬆️ 更新到 v1.2」按鈕（點下去直接覆蓋安裝新版本，不用先卸載）。
- **state file** — `friend_installer_state.json`（放在 .exe 旁邊）會記錄
  每個 mod 安裝的版本、時間、components。同步 catalog 後自動比對。
- **install_mod 自動記錄** — 之後安裝/卸載 mod 都會自動更新 state。

### Notes
- v1.1.0 之後每加新 mod 不用朋友重抓 .exe（除非 UI 有改）— repo-driven
  架構保留，朋友只要按「同步 MOD 資料庫」就會看到新 mod。
- 從 v1.0.x 升級到 v1.1.0：需要重抓 .zip（UI 改了），朋友的 .exe 重灌。
- BlueEyesChaosMaxDragon 屬於《遊戲王》IP 衍生作品，僅供朋友間測試
  使用，請勿商業化。如原作者 sv_boy 要求下架請告知。

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
