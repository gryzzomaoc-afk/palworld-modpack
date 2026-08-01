# 帕魯不打烊 - 朋友端 Mod 一鍵安裝工具

帕魯不打烊 (PalServer 不打烊) 社群專用的朋友端 mod 安裝工具。

不用裝 Python、雙擊 exe 就能用。

## 下載

從右邊 [Releases](../../releases) 頁面下載最新版的 `PalworldFriendModInstaller.exe`，雙擊執行即可。

> 📖 **完整使用教學**：[USAGE.md](USAGE.md) — 含截圖位置、疑難排解（裝完沒效果、URL UNKNOWN 等）

## 使用步驟

1. **跑起來**：雙擊 `PalworldFriendModInstaller.exe`
2. **自動偵測**：工具會自動找出你電腦上的 Steam + Palworld 安裝位置
3. **同步資料庫**：按「同步 MOD 資料庫」按鈕（會從 GitHub 拉最新的 mod 清單）
4. **選 mod 安裝**：看到 mod 後按「安裝」按鈕，工具會下載並自動解壓到你本機 Palworld
5. **開遊戲**：關掉工具、開 Palworld，mod 會自動載入

## 支援的 mod 類型

| 類型 | 安裝位置 | 需要 UE4SS? |
|---|---|---|
| Paks mod | `Pal/Content/Paks/~mods/` | ❌ |
| UE4SS mod | `Pal/Binaries/Win64/ue4ss/Mods/<mod名稱>/` | ✅ (要先裝 UE4SS) |

工具會自動判斷該裝到哪 — 不用自己選。

## 如果 mod 是 UE4SS 類型

1. 工具會先偵測你本機有沒有裝 UE4SS
2. 沒裝的話按「🚀 一鍵安裝 UE4SS」一鍵裝好（從 Okaetsu 官方下載，安全）
3. 裝完後才能裝 UE4SS 類的 mod

## 常見問題

### 裝完沒效果？

- 確認 Palworld 已經關掉（沒關掉的話 .pak 檔會被 lock）
- 重啟 Steam 再開 Palworld
- 檢查防毒軟體有沒有隔離掉 .pak 檔

### 偵測不到我的 Palworld？

- 確認 Steam 是用預設路徑安裝（`C:\Program Files (x86)\Steam\`）
- 確認 Palworld 已經裝好（Steam 庫存裡看得到）
- 按「重新偵測 Steam 路徑」再試一次

### Mod 跑去哪了？

- Paks mod：`Palworld\Pal\Content\Paks\~mods\*.pak`
- UE4SS mod：`Palworld\Pal\Binaries\Win64\ue4ss\Mods\<mod名稱>\`

## 來源

- 工具原始碼：內部 repo
- Mod catalog：同 repo 的 `friend-catalog.json`
- UE4SS：https://github.com/Okaetsu/RE-UE4SS

## 給管理者（薯條）

這是「帕魯不打烊」專用的朋友端安裝工具，發布在這個 public repo 讓朋友下載。
要更新：
- 改 `friend-catalog.json` 加新 mod
- 把新的 .exe 推到 GitHub Releases
