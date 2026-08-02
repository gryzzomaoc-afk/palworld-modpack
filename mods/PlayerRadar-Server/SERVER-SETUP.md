# PlayerRadar-Server 部署指南

給 dedicated server 管理員（CrazyChips），一步一步裝在 192.168.1.112。

---

## 流程總覽

```
1. 確認 UE4SS 已裝                    ← 你之前裝 WTDSE 0.9.0 時應該有了
2. 開共用資料夾 share                 ← 給 client 端讀 positions.json
3. 解 PlayerRadar-Server.zip
4. 改 config.lua                       ← 設 output_path
5. 改 mods.txt                         ← 加 PlayerRadar-Server : 1
6. 啟動 PalServer，看 UE4SS.log
7. 確認 positions.json 1 秒更新一次
```

預估 10-15 分鐘，前提是 UE4SS 已經在。

---

## Step 1: 確認 UE4SS 已在

PlayerRadar-Server 是 UE4SS Lua mod，需要 Okaetsu RE-UE4SS `experimental-palworld` 才能跑。

如果之前已經裝 WTDSE 0.9.0，這個就有了。檢查：

```
PS> Test-Path 'E:\SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\ue4ss\UE4SS.dll'
True
```

回 True → 跳到 Step 2。
回 False → 去 https://github.com/Okaetsu/RE-UE4SS/releases/download/experimental-palworld/UE4SS-Palworld.zip 下載解到 `Pal\Binaries\Win64\ue4ss\`（保持原本的 `PalServer.exe` 不動，只新增 `ue4ss\` 子資料夾）。

---

## Step 2: 開共用資料夾

PlayerRadar-Server 寫的 `positions.json` 必須讓 client 端讀到。**最簡單的方式**是直接寫到 Windows 共用資料夾。

### 2.1 建立資料夾

在 server 任何位置（建議根目錄或固定路徑），建一個資料夾：

```
mkdir C:\palradar
```

### 2.2 共用

PowerShell（管理員）：

```powershell
New-SmbShare -Name "palradar$" -Path "C:\palradar" `
    -FullAccess "BUILTIN\Administrators" `
    -ReadAccess "Everyone" `
    -Description "PlayerRadar positions.json (PlayerRadar-Server writes, PlayerRadar-Client reads)"
```

或者用 GUI：
1. 對 `C:\palradar` 右鍵 → 內容 → 共用 → 共用這個資料夾
2. 共用名稱：`palradar$`（`$` 表示隱藏共用）
3. 權限：Everyone 讀，管理員讀寫
4. 防火牆允許檔案共用（一般家用網路都開了）

### 2.3 從 client 端測試能讀

在你 local 機器（打 game 那台）開檔案總管，網址列輸入：

```
\\192.168.1.112\palradar$
```

應該能進去看到 `C:\palradar\` 內容（現在是空的）。如果有認證視窗跳出，輸入 server 的 admin 帳號密碼。

**如果不行** → 檢查：
- 防火牆（server 端「檔案及印表機共用」要開）
- 網路探索（網路和共用中心 → 進階共用設定 → 開啟網路探索 + 檔案共用）
- 密碼保護共用（如果開啟，要輸入帳號）

---

## Step 3: 解 PlayerRadar-Server

把 `server.zip` 解到 `Pal\Binaries\Win64\ue4ss\Mods\`。解完會得到：

```
E:\SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\
├── enabled.txt
└── Scripts\
    ├── config.lua
    └── main.lua
```

**用 PowerShell 解（最穩）**：

```powershell
Expand-Archive -LiteralPath "C:\Users\yason\Downloads\server.zip" `
    -DestinationPath "E:\SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\ue4ss\Mods\" `
    -Force
```

或用 7-Zip / Windows 內建解壓都行。

---

## Step 4: 改 config.lua

編輯 `E:\...\Mods\PlayerRadar-Server\Scripts\config.lua`：

```lua
return {
    -- 寫到共用資料夾（client 直接讀同一個 UNC path）
    output_path = "C:\\palradar\\positions.json",

    -- 寫入頻率（秒）。1s 對玩家即時性來說夠用。
    write_interval_seconds = 1.0,

    -- Server 標籤，會寫進 JSON（client log 會看到）
    server_label = "CrazyChips's server",

    -- Console command（server admin 在 PalServer 視窗打）
    console_command = "pradar",
}
```

**`output_path` 怎麼設**：

| 你想怎麼做 | `output_path` 寫法 |
|---|---|
| 寫到共用資料夾（推薦） | `"C:\\palradar\\positions.json"` |
| 直接寫到 share 的 UNC（也 OK） | `"\\\\192.168.1.112\\palradar$\\positions.json"` |
| 不開 share，先測試 | `"C:\\Users\\CrazyChips\\AppData\\Local\\Temp\\palradar_server.json"` |

**`\\` escape 注意**：Lua 字串裡的 `\` 要寫成 `\\`。`C:\palradar\positions.json` 在 Lua 裡是 `"C:\\palradar\\positions.json"`。UNC 路徑 `\\192.168.1.112\palradar$\file` 在 Lua 裡是 `"\\\\192.168.1.112\\palradar$\\file"`。

---

## Step 5: 改 mods.txt

編輯 `E:\...\ue4ss\Mods\mods.txt`，加 `PlayerRadar-Server : 1`：

```ini
CheatManagerEnablerMod : 0
ConsoleCommandsMod : 0
ConsoleEnablerMod : 0
SplitScreenMod : 0
LineTraceMod : 0
BPML_GenericFunctions : 1
BPModLoaderMod : 1


; Built-in keybinds, do not move up!
Keybinds : 1



WorldTreeDragonSuperEvolution : 1
WorldTreeDragonNativeWarp : 1
PalSchema : 1
PlayerRadar-Server : 1
```

---

## Step 6: 啟動 PalServer

正常啟動 PalworldServer.exe。**UE4SS 會自動 load**。

### 6.1 看 UE4SS.log

開 `E:\...\ue4ss\UE4SS.log`，找這幾行：

```
[2026-08-02 XX:XX:XX] Starting Lua mod 'PlayerRadar-Server'
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] v1.0.0 loaded
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] output -> C:\palradar\positions.json
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] console: registered (try 'pradar help' in the PalServer window)
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] write loop started (every 1s)
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] wrote 1 player(s) -> C:\palradar\positions.json
[2026-08-02 XX:XX:XX] [Lua] [PlayerRadar-Server] wrote 1 player(s) -> C:\palradar\positions.json
```

**正常**：`write loop started` + 持續的 `wrote N player(s)` 訊息。
**異常**：見下方疑難排解。

### 6.2 用 console command 驗證

在 PalServer 的 cmd 視窗（黑色那個）打：

```
pradar list
```

應該看到類似的輸出：
```
[PlayerRadar-Server] list: 1 player(s)
[PlayerRadar-Server]   [1] CrazyChips                (1234, 5678, 120)
```

（如果這時候沒有 client 連上來，N = 0 是正常的。等朋友連上後會更新）

---

## Step 7: 確認 positions.json 有更新

在你 server 開另一個 cmd：

```powershell
Get-Content "C:\palradar\positions.json"
```

應該看到：

```json
{"ts":1754123456,"server":"CrazyChips's server","players":[{"name":"CrazyChips","x":1234.5,"y":5678.9,"z":120.0}]}
```

過 1 秒再跑一次，`ts` 數字會變（時間戳更新）。

如果檔案不存在 / 沒更新 → 見下方疑難排解。

---

## 疑難排解

### Q: UE4SS.log 完全沒出現 `[PlayerRadar-Server]`？

- 確認 `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\enabled.txt` 存在（檔案存在就 enable，不需有內容）
- 確認 `mods.txt` 有 `PlayerRadar-Server : 1`（沒被拼錯字）
- 確認 zip 解出來的資料夾結構是 `PlayerRadar-Server\Scripts\main.lua`（不是 `PlayerRadar-Server\main.lua` 或多一層子目錄）
- 確認 UE4SS 本身有 load（log 開頭有 `Starting mods`）

### Q: 看到 `Failed to execute main script`？

- 重新裝一次（卸載 + 重新安裝）— 可能是舊的壞檔案還在
- 確認 zip 是用 v1.0.1 之後的版本（manifest.json 的 sha256 要對得上 `f112461b...` 或之後）

### Q: `wrote 0 player(s)` 一直出現？

- 沒人連上 server。`FindAllOf("PalPlayerCharacter")` 在 server 沒 client 時回傳空 array，正常
- 等朋友連進來 log 數字會更新
- 如果有人連線但還是 0 → 你的 PalServer 可能用 listen-server mode 不是 dedicated，這時 UE4SS mod 不會跑

### Q: positions.json 沒被建立？

- 看 log 是不是有 `write FAILED` → 路徑問題（檢查 `output_path` 是否合法）
- 目錄不存在會自動 `mkdir`，但權限不夠時會失敗
- 用 `dir C:\palradar\` 確認資料夾可寫

### Q: Client 端 `refresh: server read failed`？

- 從你 client 端 `Test-Path "\\192.168.1.112\palradar$\positions.json"` → 應該 True
- 共用沒設好（回到 Step 2）
- 防火牆擋住 SMB（家用網路應該不會，但 corporate network 會）
- 路徑 escape 寫錯（檢查 `\\` 是否寫成 `\\\\`）

### Q: Server admin console 沒回應 `pradar help`？

- 確認 PalServer 是用「互動式」cmd 視窗跑（不是 `-log` 背景）
- 確認 console command 有 register（log 裡有 `console: registered`）
- 部分 PalServer 版本會把 stdout 導到 log 檔，console 指令可能要走 RCON

---

## 驗證 checklist

裝完後**逐項檢查**：

- [ ] `Pal\Binaries\Win64\ue4ss\UE4SS.log` 有 `[PlayerRadar-Server] v1.0.0 loaded`
- [ ] log 有 `write loop started (every 1s)`
- [ ] `C:\palradar\positions.json` 存在且每秒更新
- [ ] 在 PalServer cmd 視窗打 `pradar list` 有回應
- [ ] 從你 client 端 `\\192.168.1.112\palradar$\positions.json` 能讀
- [ ] client 端 friend installer 裝 `PlayerRadar-Client` + config 指向同一個 path → 進遊戲按 M 看到 marker

全部打勾 → 完整鏈路通了。

---

## 卸載

```powershell
# 1. 停 PalServer
Stop-Process -Name "PalServer" -Force

# 2. 移除 mod 資料夾
Remove-Item -LiteralPath "E:\...\Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server" -Recurse -Force

# 3. 從 mods.txt 移除對應行
# 把 "PlayerRadar-Server : 1" 刪掉

# 4. 啟動 PalServer
& "E:\...\PalServer.exe"
```

`positions.json` 檔可以留著（不會再被更新，但也不會被自動刪）。
