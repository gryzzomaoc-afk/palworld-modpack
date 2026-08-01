# 更新日誌

## v1.0.7 (2026-08-02)

### 新增
- **Pal 運行檢查** — install/uninstall 前自動偵測 Palworld.exe 是否在跑，跑了就拒絕安裝（避免 .pak/.dll 被 lock）
- **自動備份** — install_ue4ss / uninstall_ue4ss / install_mod 前先把現有資料夾備份成 `*.bak-<timestamp>\`，可手動回滾
- **UE4SS 健全檢查 (`check_ue4ss_health`)** — 不只查 `UE4SS.dll`，還驗 `Mods/shared/UEHelpers/UEHelpers.lua` 等 5 個關鍵檔案
- **Mod 驗證 (`verify_mod_install`)** — 裝完檢查 catalog 列的檔案是否都在對位置
- **🔎 驗證 UE4SS 按鈕**（UI） — 點下去跑所有驗證，dialog 顯示結果
- **安裝失敗自動回滾** — install_ue4ss layout 驗證失敗時自動從備份還原

### 修正
- **install_mod 報錯 bug** — `_install_component` 內 `backup_msg` 在 client 分支沒初始化，導致 client 安裝時回傳 `ok=False` 但檔案其實裝好了
- **verify_mod_install 誤用 SHA256** — 之前拿 catalog zip 層級 SHA256 對 inner file，現在改成單純 existence check

### 已知問題
- friend installer 不會保留使用者自訂的 Lua patch（例：`try_hook_widget_tick` v2 fix）。要 patch 自己 server 端再 push 一版給朋友。

## v1.0.6 (2026-08-01)
- 初次完整版
- friend_flet.py 完整 UI（深色主題、Flet 0.86.4）
- install_ue4ss 從 Okaetsu 下載，自動解壓
- install_mod 處理 UE4SS mod + .pak mod
- SHA256 驗證（zip 層級）
- mods.txt append（不覆蓋）
- enabled.txt 自動建立
