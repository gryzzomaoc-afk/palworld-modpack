# PlayerRadar

在 Palworld dedicated server 上看到**所有在線玩家**的位置，並在地圖上顯示、列表、按一下就能傳送過去。

適用於 32 槽 dedi server（client 端 `FindAllOf` 只能看到 replication 範圍內的少數人，server 端看得到全部 32 人）。

---

## 架構

```
                        ┌──────────────────────────┐
                        │   Dedicated Server       │
   PalServer.exe         │  192.168.1.112           │
   + UE4SS              │  Pal\Binaries\Win64\ue4ss\│
   + PlayerRadar-Server │  └─ Mods\PlayerRadar-Server\ │ 每 1s 寫
                        │      ↓                       │ positions.json
                        └──────┬───────────────────────┘
                               │ 共用資料夾 (UNC / SMB)
                               ▼
                        ┌──────────────────────────┐
                        │   Your Client            │
   Palworld.exe         │  (你打 game 那台)        │
   + UE4SS              │  Pal\Binaries\Win64\ue4ss\│
   + PlayerRadar-Client │  └─ Mods\PlayerRadar-Client\ │ 每 1s 讀
                        │      ↓                       │
                        │   in-game map 上加 marker  │
                        │   點 list 傳送             │
                        └──────────────────────────┘
```

兩個 mod 透過**共用 JSON 檔**通訊（`positions.json`）：
- **Server** 寫：把所有 32 個玩家位置寫成 JSON
- **Client** 讀：解析 JSON，把 marker 畫到 in-game map

---

## Server 端安裝（dedicated server 192.168.1.112）

### 1. 確認 UE4SS 已裝

PlayerRadar-Server 是 UE4SS Lua mod，需要 Okaetsu RE-UE4SS `experimental-palworld`。

如果之前裝 WTDSE 0.9.0 時已經裝了，UE4SS 已經在 `Pal\Binaries\Win64\ue4ss\` 裡。沒有的話：

- 下載：https://github.com/Okaetsu/RE-UE4SS/releases/download/experimental-palworld/UE4SS-Palworld.zip
- 解到 `Pal\Binaries\Win64\ue4ss\`

### 2. 建立共用資料夾

在 server 上開一個 Windows 共用資料夾（任何位置都行）：

```
\\192.168.1.112\palradar$\
```

權限：給你自己（admin）讀寫、給其他 client user 至少「讀」權限。

### 3. 解 PlayerRadar-Server

把 `PlayerRadar-Server.zip` 解到：

```
Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\
├── enabled.txt
├── config.lua
└── Scripts\
    └── main.lua
```

### 4. 編輯 `config.lua`

```lua
return {
    output_path = "C:\\palradar\\positions.json",   -- 或 UNC: "\\\\192.168.1.112\\palradar$\\positions.json"
    write_interval_seconds = 1.0,
    server_label = "CrazyChips's server",
    console_command = "pradar",
}
```

`output_path` 可以是 server 本地路徑（自己寫自己讀），也可以直接寫到共用資料夾。建議直接寫到共用資料夾，client 就不用再被 SMB 隔一層。

### 5. 改 `mods.txt`

```
WorldTreeDragonSuperEvolution : 1
PalSchema : 1
WorldTreeDragonNativeWarp : 1
PlayerRadar-Server : 1
```

### 6. 啟動 server，看 UE4SS.log

應該看到：
```
[PlayerRadar-Server] v1.0.0 loaded
[PlayerRadar-Server] output -> C:\palradar\positions.json
[PlayerRadar-Server] console: registered (try 'pradar help' in the PalServer window)
[PlayerRadar-Server] write loop started (every 1s)
[PlayerRadar-Server] wrote 1 player(s) -> C:\palradar\positions.json
[PlayerRadar-Server] wrote 1 player(s) -> C:\palradar\positions.json
...
```

---

## Client 端安裝（你打 game 那台 + 朋友）

### 方法 A：透過 friend installer（推薦）

1. 開 v1.0.8 friend installer
2. 按「同步 MOD 資料庫」→ 會看到 `PlayerRadar-Client` 出現
3. 點安裝

### 方法 B：手動

把 `PlayerRadar-Client.zip` 解到：
```
Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Client\
├── enabled.txt
├── config.lua
└── Scripts\
    └── main.lua
```

### 改 `mods.txt`

```
BreedingHelper : 1
PlayerRadar-Client : 1
```

### 編輯 `config.lua`

```lua
return {
    server_json_path = "\\\\192.168.1.112\\palradar$\\positions.json",  -- 跟 server 端 output_path 一樣
    refresh_interval_seconds = 1.0,
    map_refresh_interval_seconds = 0,       -- 0 = 只在按 M 時刷新
    local_poll_interval_seconds = 2.0,
    list_hotkey = "M",
    teleport_hotkey = "T",
    teleport_offset_back = 200.0,
    console_command = "pradar",
}
```

`server_json_path` 跟 server 的 `output_path` **完全一樣**。

如果朋友沒有讀 share 權限，設成 `""`（空字串）就會 fallback 到本地 `FindAllOf`（看到附近的人）。

---

## 使用方式

### Hotkey（listen-server / single-player）

| 按鍵 | 動作 |
|---|---|
| **M** | 重新讀 server JSON + 列出所有玩家 + 重新畫 in-game map marker |
| **T** | 把自己傳送到最近玩家背後 200 cm |

### Console command（在遊戲內按 ` 打開）

```
pradar list                          列出所有玩家
pradar bring <idx>                   把自己傳送到玩家 <idx> 位置
pradar teleport                      傳送到最近玩家（跟按 T 一樣）
pradar refresh                       重新讀 server JSON
pradar help                           顯示幫助
```

範例：
```
> pradar list
[PlayerRadar-Client] list: 3 player(s) [source=server, ts=1754123456]
[PlayerRadar-Client]   [1] Alice           (1234, 5678,  120)
[PlayerRadar-Client]   [2] Bob             (2000, 3000,   95)
[PlayerRadar-Client]   [3] Charlie         (5000, 1000,  130)

> pradar bring 2
[PlayerRadar-Client] bring: teleported to Bob @ (2000, 3000, 95)
```

### Server admin console（在 PalServer 視窗打）

```
pradar list              列出所有在線玩家
pradar flush             立即寫一次 JSON
pradar help              顯示幫助
```

---

## JSON 格式

`positions.json` 的內容（給 developer 參考）：

```json
{
  "ts": 1754123456,
  "server": "CrazyChips's server",
  "players": [
    {"name": "Alice",   "x": 1234.5, "y": 5678.9, "z":  120.0},
    {"name": "Bob",     "x": 2000.0, "y": 3000.0, "z":   95.0},
    {"name": "Charlie", "x": 5000.0, "y": 1000.0, "z":  130.0}
  ]
}
```

Client 端會讀這個檔案，每 1s 重抓一次。

---

## 朋友裝會看到什麼？

朋友裝 `PlayerRadar-Client` 但沒讀 `positions.json` 的權限（沒 server share 帳號）→ 自動 fallback 到本地 `FindAllOf("PalPlayerCharacter")`：

- 朋友會看到**自己附近 replication 範圍內的玩家**（不是全部 32 人，但足夠找朋友）
- 按 T 還是能用
- 列表 / 傳送 都能用

如果朋友也想要看 32 人全部 → 把 `server_json_path` 改指向你能 read 的 share 路徑（給朋友一個 read-only 帳號）。

---

## 疑難排解

### Q: Server 啟動沒看到 `PlayerRadar-Server` log？

- 確認 `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\enabled.txt` 存在（不是空的也 OK，是檔案就好）
- 確認 `Mods\mods.txt` 有 `PlayerRadar-Server : 1`
- 看 `UE4SS.log` 有沒有紅字（Lua 語法錯誤會印出來）

### Q: `wrote 0 player(s)` 一直出現？

- Server 端沒人連線。`FindAllOf("PalPlayerCharacter")` 在 server 沒玩家的時候回傳空 array，這是正常的
- 等朋友連上後 log 數字會更新

### Q: Client 端 log 一直 `refresh: server read failed`？

- `server_json_path` 路徑打錯（注意 `\\` 要 escape 成 `\\\\`）
- Server 沒開共用資料夾
- 朋友 client 沒讀 share 權限 → 改用 `FindAllOf` fallback（清空 path 就好）

### Q: 按 M 沒看到 marker？

- 確認**地圖已經打開**（按 M 開地圖 → 再按一次觸發 marker refresh）
- 確認 UE4SS.log 沒 crash（marker 創建失敗會 log `Setup Icon yielded no icon widget`）
- 部分 Palworld 版本地圖 widget 路徑不同 → 找 log 裡的 `WBP_Map_Base_C` / `WBP_Map_Body_MW5` 關鍵字

### Q: 按 T 沒傳送？

- 看 log 有沒有 `K2_SetActorLocation failed`
- 通常是 server 拒絕了 client 端的傳送（極少見，server 通常不驗證 client 自己的 pawn 移動）
- 試試離目標玩家更近的位置再按 T

### Q: 朋友端看不到全部 32 人？

- 朋友沒讀 share 權限 → fallback 只看到附近的人
- 解法：給朋友 share 的 read 權限，並把 `server_json_path` 設成他能讀的 UNC 路徑

---

## 已知限制

- **沒做 in-game list widget**（點 player 列表傳送）— 目前靠 console `pradar bring <idx>` 選特定玩家
- **marker 是純視覺，不能點**— 按 M 才更新，沒法即時點選
- **server 端位置 client 端讀**有最多 1 秒延遲（寫入週期是 1s）
- **傳送有時候被 server reject**（看 log），這是 Palworld 的 server-side validation，目前無法解決（極少見）

---

## 卸載

1. 停止 PalServer（server 端）或退出 Palworld（client 端）
2. 刪除 `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\`（server）
3. 刪除 `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Client\`（client）
4. 從 `mods.txt` 移除對應行
5. server 端的 `positions.json` 檔可以留著（會被下次啟動覆蓋）

---

## 檔案位置速查

| 角色 | 檔案 | 路徑 |
|---|---|---|
| Server | mod 程式 | `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Server\` |
| Server | positions.json | `output_path` 設定的位置 |
| Server | UE4SS 設定 | `Pal\Binaries\Win64\ue4ss\UE4SS-settings.ini` |
| Client | mod 程式 | `Pal\Binaries\Win64\ue4ss\Mods\PlayerRadar-Client\` |
| Client | UE4SS log | `Pal\Binaries\Win64\ue4ss\UE4SS.log` |
| 共用 | positions.json | `\\192.168.1.112\palradar$\positions.json`（或你選的路徑） |

---

## 變更歷史

- **1.0.0** (2026-08-02): 初版
  - Server: 每 1s 寫 positions.json
  - Client: 讀 JSON + 渲染 in-game map marker + T 鍵傳送 + console 命令
  - 朋友端 fallback: 讀不到 JSON 時用 `FindAllOf`
