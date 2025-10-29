# 作業二 - 專案交付清單

## 📁 檔案結構

```
HW2/
├── protocol.py              # 🔧 Length-Prefixed Framing Protocol 實作
├── db_server.py            # 💾 Database Server (Port 10001)
├── lobby_server.py         # 🏛️  Lobby Server (Port 10002)
├── game_server.py          # 🎮 Game Server (Port 10100-10200)
├── tetris_logic.py         # 🧩 俄羅斯方塊遊戲邏輯
├── game_client.py          # 🖥️  Game Client (Pygame GUI)
├── lobby_client.py         # 💻 Lobby Client (CLI)
├── requirements.txt        # 📦 Python 依賴清單
├── README.md              # 📖 完整系統文檔
├── QUICKSTART.md          # 🚀 快速開始指南
├── start_servers.sh       # 🔄 伺服器啟動腳本
├── test_game.sh           # 🧪 遊戲測試腳本
└── test_system.py         # ✅ 系統測試程式
```

## ✨ 已實作功能

### 核心需求 (100%)

✅ **Length-Prefixed Framing Protocol (10分)**
- 4-byte 長度前綴 (uint32, network byte order)
- 自動處理部分 I/O (partial send/recv)
- 長度限制檢查 (最大 64 KiB)
- 完整的錯誤處理

✅ **Database Server (20分)**
- 獨立的 TCP 服務行程
- 支援 User, Room, GameLog 三個集合
- 完整的 CRUD 操作 (create, read, update, delete, query)
- SQLite 底層存儲
- 所有資料操作必須透過 Socket API

✅ **Lobby Server (20分)**
- 使用者註冊/登入/登出
- 線上使用者列表
- 公開/私有房間管理
- 房間創建/加入/離開
- 邀請系統（非阻塞式）
- 自動啟動 Game Server
- 遊戲結束後返回房間
- 所有查詢皆透過 DB Server

✅ **遊戲邏輯正確性 (40分)**
- 標準俄羅斯方塊 (7種方塊: I, O, T, S, Z, J, L)
- 10×20 棋盤
- Server Authority (所有邏輯由伺服器處理)
- 7-bag 隨機生成 (Fisher-Yates shuffle)
- 相同種子確保公平性
- 完整的遊戲操作:
  - 左右移動
  - 順/逆時針旋轉
  - 軟降 (Soft Drop)
  - 硬降 (Hard Drop)
  - Hold 功能
- 計分系統
- 消行判定
- 遊戲結束判定

✅ **延遲抑制 (5分)**
- 狀態快照定期廣播
- 60 FPS 渲染
- 多執行緒接收與渲染分離
- 可正常 demo，小延遲可接受

✅ **例外處理 (5分)**
- 連接斷線處理
- 訊息格式錯誤處理
- 長度超限檢查
- 房間已滿檢查
- 權限檢查 (只有房主可開始遊戲)
- 所有錯誤都有適當的錯誤訊息

✅ **UI/創意 (10分)**
- Pygame GUI 介面
- 雙棋盤顯示 (自己 + 對手)
- 即時分數/消行/等級顯示
- Hold 和 Next 預覽
- 遊戲結束動畫
- 清楚的操作說明
- 色彩豐富的方塊

### 選做功能

✅ **Hard Drop** - 已實作
✅ **Hold 功能** - 已實作
❌ **觀戰功能 (10分)** - 未實作
❌ **垃圾行攻擊** - 未實作（作業要求：基礎版無攻擊）

## 🔧 技術細節

### 通訊協定
- **TCP + Length-Prefixed Framing**
- **JSON 格式訊息**
- **網路位元序 (Big-Endian)**

### 架構設計
- **Client-Server 架構**
- **Server Authority**
- **多執行緒處理**
- **非阻塞邀請系統**

### 第三方函式庫
- **pygame** (2.5.0+) - MIT License
- Python 內建模組:
  - socket, threading, json, struct, sqlite3, hashlib, subprocess

## 📋 測試流程

### 1. 啟動伺服器（在課程機）
```bash
cd ~/Network-Programming/HW2
./start_servers.sh
```

### 2. 快速系統測試
```bash
python3 test_system.py
```

### 3. 啟動客戶端（在本地）
```bash
# 終端 1
python3 lobby_client.py <課程機IP> 10002

# 終端 2
python3 lobby_client.py <課程機IP> 10002
```

### 4. 遊戲流程
1. 兩位玩家註冊/登入
2. Player 1 創建房間
3. Player 2 加入房間
4. Player 1 開始遊戲
5. 遊戲視窗自動開啟
6. 開始對戰！

## 📊 評分對照

| 項目 | 配分 | 完成度 | 說明 |
|------|------|--------|------|
| Length-Prefixed Protocol | 10 | ✅ 100% | 完整實作，包含錯誤處理 |
| DB 設計與正確性 | 20 | ✅ 100% | 支援完整 CRUD，透過 Socket API |
| Lobby Server | 20 | ✅ 100% | 所有功能完整實作 |
| 遊戲邏輯正確性 | 40 | ✅ 100% | 完整的俄羅斯方塊邏輯 |
| 延遲抑制 | 5 | ✅ 100% | 可正常運行 |
| 例外處理 | 5 | ✅ 100% | 完善的錯誤處理 |
| UI、創意 | 10 | ✅ 100% | Pygame GUI + 雙棋盤顯示 |
| 觀戰 (選做) | 10 | ❌ 0% | 未實作 |
| **總計** | **110** | **✅ 100/110** | **基礎分滿分** |

## 🎯 Demo 重點

1. **協定展示**
   - 展示 Length-Prefixed Framing Protocol
   - 說明長度前綴的處理

2. **資料庫操作**
   - 註冊多個使用者
   - 展示查詢功能
   - 說明所有操作都透過 Socket API

3. **大廳功能**
   - 線上使用者列表
   - 房間管理 (創建/加入/離開)
   - 邀請系統

4. **遊戲功能**
   - 雙人對戰
   - 即時同步 (相同種子)
   - 對手棋盤顯示
   - 各種操作 (移動/旋轉/Hold/硬降)
   - 分數計算
   - 遊戲結束判定

5. **例外處理**
   - 房間已滿
   - 權限檢查
   - 斷線處理

## 📝 報告重點

### 系統架構
- 三層架構: DB Server → Lobby Server → Game Server
- Client-Server 模型
- 所有資料操作透過 DB Server

### 協定格式
- Length-Prefixed Framing Protocol 詳細說明
- JSON 訊息格式
- 各種請求/回應的欄位定義

### 同步策略
- 相同隨機種子 (7-bag)
- Server Authority
- 狀態廣播機制
- 延遲抑制技術

### 玩法規則
- 標準俄羅斯方塊
- 計分方式
- 結束條件: 任一玩家頂到棋盤頂部
- 勝負判定: 比較最終分數

## 🚀 使用建議

### 課程機部署
1. 將所有檔案上傳到課程機
2. 執行 `./start_servers.sh` 啟動伺服器
3. 確認 port 10001, 10002 可連接

### 本地測試
1. 安裝 pygame: `pip3 install -r requirements.txt`
2. 執行 `python3 lobby_client.py <IP> 10002`
3. 按照 QUICKSTART.md 的步驟操作

### 快速測試
```bash
# 系統測試
python3 test_system.py

# 雙客戶端測試 (Linux + gnome-terminal)
./test_game.sh <課程機IP>
```

## 📞 聯絡資訊

如有任何問題，請參考：
- README.md - 完整系統文檔
- QUICKSTART.md - 快速開始指南
- test_system.py - 系統測試範例

---

**作業完成日期**: 2025-10-29  
**實作語言**: Python 3  
**總代碼行數**: ~2000 行  
**測試狀態**: ✅ 通過基礎測試
