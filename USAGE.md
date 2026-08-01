# 使用教學 - 帕魯不打烊 朋友端 Mod 安裝工具

> 下載連結：https://github.com/gryzzomaoc-afk/palworld-modpack/releases/download/v1.0.2/PalworldFriendModInstaller.exe

## 0. 下載並開啟

1. 點上面的下載連結，瀏覽器會下載一個約 60MB 的 .exe 檔
2. **雙擊執行**（不用裝 Python，工具已打包）
3. Windows SmartScreen 可能會跳警告「無法辨識的應用程式」→ 點「其他資訊」→「仍要執行」（這是因為我們沒花錢簽章，檔案本身安全）

開啟後你會看到一個深色主題的視窗，分三個區塊：
- **Steam / Palworld 偵測**（紫）
- **前置需求 UE4SS**（橘）
- **MOD 資料庫**（紫）

---

## 1. 自動偵測 Steam + Palworld

開啟後工具會**自動**偵測你電腦的：
- Steam 安裝路徑
- Palworld 安裝路徑

如果偵測成功，「Steam / Palworld 偵測」卡會顯示：
- 綠 ✓「已找到 Palworld」
- 完整路徑 `C:\Program Files (x86)\Steam\steamapps\common\Palworld`

**如果沒偵測到**（顯示紅 ✗）：
- 確認 Steam 裝在預設路徑 `C:\Program Files (x86)\Steam\`
- 確認 Steam 庫存裡有 Palworld
- 按「**重新偵測 Steam 路徑**」鈕重試

---

## 2. UE4SS 前置檢查

工具會自動檢查你本機 Palworld 有沒有裝 UE4SS（mod 用的框架）。

| 狀態 | 說明 |
|---|---|
| ✓ 已安裝 UE4SS | 可以裝任何 mod（包含 UE4SS 類） |
| ⚠ 路徑存在但缺少 UE4SS.dll | 裝一半，重新安裝 |
| ✗ 未安裝 UE4SS | 純 Paks mod 可以裝；UE4SS 類的 mod 必須先裝 UE4SS |

**裝 UE4SS**：按「🚀 一鍵安裝 UE4SS」→ 工具從 Okaetsu 官方下載並解壓到 Palworld 對應資料夾（`Pal\Binaries\Win64\ue4ss\`）。約 7MB，下載 + 解壓約 10 秒。

裝完後按「📂 開啟 Win64 資料夾」可以直接看到 `ue4ss\` 資料夾內容。

---

## 3. 同步 MOD 資料庫

按「**同步 MOD 資料庫**」鈕（在 MOD 資料庫卡右上角）：

1. 工具會從 GitHub 拉最新的 mod 清單
2. 鈕會變成「同步中...」+ 顯示轉圈圈（spinner）
3. 同步完會列出所有可安裝的 mod，每個顯示：
   - Mod 名稱 + 版本
   - 描述
   - 「已安裝」或「未安裝」狀態 chip
   - 「安裝」或「卸載」按鈕

**現在 GitHub 上的 mod**：
- **BreedingHelper（育種助手）** v1.1 — 純 Paks mod，不需 UE4SS

---

## 4. 安裝 mod

點 mod 卡的「📥 安裝」鈕：
1. 跳確認對話框（防誤觸）
2. 工具從 GitHub 下載 mod 的 zip
3. 解壓到正確位置：
   - Paks mod → `Pal/Content/Paks/~mods/`
   - UE4SS mod → `Pal/Binaries/Win64/ue4ss/Mods/<mod名稱>/`
4. 完成後按鈕自動變成「🗑 卸載」（表示已安裝）

**安裝 mod 類型對照**：
| Mod 類型 | 安裝位置 | 需 UE4SS? |
|---|---|---|
| Paks mod（`.pak` 檔） | `Pal/Content/Paks/~mods/` | ❌ |
| UE4SS mod（`.lua` 腳本） | `Pal/Binaries/Win64/ue4ss/Mods/<mod名稱>/` | ✅ |

工具會自動判斷，不用自己選。

---

## 5. ⚠️ 開遊戲前請先關閉 Palworld

**重要**：安裝 / 卸載 mod 時如果 Palworld 正在跑，.pak 檔會被 lock 住，要重啟遊戲才生效。

建議流程：
1. **完全關掉 Palworld**（不是最小化，是真的關掉）
2. 用工具裝 / 卸 mod
3. 再開 Palworld

---

## 6. 進入遊戲驗證

開 Palworld 連到你朋友提供的 server IP：

**育種助手（BreedingHelper）驗證**：
- 進遊戲後打開任意配種面板
- 應該會看到「BreedingHelper」相關的 UI 增強（繁中、計算配種、染色/IV 鎖定等功能）
- 沒看到的話參考下方「疑難排解」

---

## 7. 卸載 mod

點 mod 卡的「🗑 卸載」鈕：
1. 跳確認對話框（防誤觸）
2. 工具刪除 mod 資料夾 + 從 `mods.txt` 移除對應 entry
3. 自動備份 `mods.txt` 成 `mods.txt.bak.<時間戳>`
4. 完成後按鈕變回「📥 安裝」

---

## 疑難排解

### Q: 裝完 mod 進遊戲沒效果？

**檢查清單**：
1. ☐ Palworld 已經**完全關掉**後再開（不是最小化）
2. ☐ 用 `verify` 鈕看 mod 卡是不是「已安裝」狀態
3. ☐ 重啟 Steam 再開 Palworld（Steam 有時會 cache）
4. ☐ 檢查防毒軟體（Windows Defender / 其他）有沒有把 .pak 或 .dll 隔離
5. ☐ 檢查檔案實際位置（按「📂 開啟 Win64 資料夾」）

### Q: 出現「URL UNKNOWN」或下載失敗？

- 確認網路連得到 `raw.githubusercontent.com`（在瀏覽器開 https://github.com 看得到網站就 OK）
- 如果公司 / 學校網路擋 GitHub，要用家裡網路
- 工具需要對 GitHub 發出 HTTPS request

### Q: 顯示「找不到 Palworld 安裝路徑」？

- 確認 Steam 不是用 Steam Play (Linux 相容) 裝的
- 如果你把 Steam 裝在 D槽或別槽，工具可能偵測不到，按「重新偵測」沒用就要手動指定路徑（目前不支援，是已知限制）
- 確認 Palworld 確實有在 Steam 庫存並至少下載過

### Q: 工具閃退 / 沒開？

- 確認 Windows 是 Win10 以上（Win7 不支援）
- 用工作管理員確認沒有殘留 `PalworldFriendModInstaller.exe` 進程
- 重新下載（可能下載到一半斷）

### Q: 朋友的 server 改了 mod 但我的工具看不到？

- 工具的 catalog 有 60 秒 cache，按「同步 MOD 資料庫」會強制重抓最新
- 如果 server 端的 mod 沒推到 GitHub catalog（`friend-catalog.json`），那 server 端裝的 mod 你這邊看不到 — 跟朋友（server 管理員）確認

---

## 給管理員（薯條）

- 工具的源碼在這個 repo 內（`friend-tool/`）
- Catalog 在 `friend-catalog.json`（GitHub root）
- 加新 mod 流程：
  1. 把 mod zip 推到 GitHub（例：`NewMod-client.zip`）
  2. 編輯 `friend-catalog.json` 加 entry（記得填 `files` 欄位才會偵測已安裝）
  3. 朋友重開工具 → 同步 → 看到新 mod → 安裝
- 改完介面要出新版本：
  1. 改 source
  2. `cd friend-tool && flet pack friend_flet.py -n PalworldFriendModInstaller -i installer.ico --add-data "installer.ico;."`
  3. 上傳新版本到 GitHub Releases（v1.0.3, v1.0.4...）
  4. 朋友從 https://github.com/gryzzomaoc-afk/palworld-modpack/releases/latest 抓最新

---

## 聯絡

有問題找 server 管理員（薯條），或在 Discord 的 🖥️-伺服器狀態 頻道回報。
