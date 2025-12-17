# 遊戲商城系統 (Game Platform System)

### 內建遊戲

1. **Number Guessing Game** (CLI)
   - 類型: 命令行遊戲
   - 玩家數: 2人
   - 玩法: 輪流猜測數字，猜中得分

2. **Tic Tac Toe** (GUI)
   - 類型: 圖形介面遊戲
   - 玩家數: 2人
   - 玩法: 經典井字遊戲，Tkinter GUI

3. **Multiplayer Snake** (GUI)
   - 類型: 圖形介面遊戲
   - 玩家數: 2-4人
   - 玩法: 多人貪食蛇大戰，即時競技

## 快速開始

### 1. 系統需求

- **操作系統**: Linux (Server端) / Windows/macOS/Linux (Client端)
- **Python版本**: 3.7+
- **依賴套件**: tkinter (GUI遊戲需要)

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
# tkinter 已內建

# Windows
# tkinter 已內建
```

### 2. 手動啟動

```bash
# 1. 下載專案
git clone https://github.com/milktea7654/Network-Programming.git
cd Network-Programming/HW3/game_platform_system

# 腳本啟動
cd /home/c0922/Network-Programming/HW3/game_platform_system
./start.sh

# 2. 啟動服務器 (終端1)
python3 launcher.py

# 或者手動啟動各組件：

# 啟動服務器 (在一個終端)
cd server
python3 main_server.py

# 啟動開發者客戶端 (在另一個終端)
cd developer  
python3 developer_client.py

# 啟動玩家客戶端 (在第三個終端)
cd player
python3 lobby_client.py
```

#### D1: 上架新遊戲 
```
操作步驟：
1. 選擇「1. 上傳新遊戲」
2. 填寫資訊：
   - 遊戲名稱: 例如 "Number Guessing Game"
   - 遊戲簡介: 例如 "經典數字猜謎遊戲"
   - 遊戲類型: 1.CLI / 2.GUI / 3.Multiplayer
   - 最大玩家數: 例如 2
   - 遊戲路徑: 指向遊戲文件或目錄
3. 系統自動打包並上傳到服務器
4. 上傳成功後可在玩家端看到遊戲

錯誤處理：
- 遊戲名稱重複 → 提示更換名稱
- 文件路徑無效 → 檢查路徑是否存在
- 網路連線問題 → 重新嘗試上傳
```

#### D2: 更新遊戲版本 
```
操作步驟：
1. 選擇「2. 更新遊戲版本」
2. 從列表選擇要更新的遊戲
3. 輸入新版本號 (例如: 1.1.0)
4. 輸入更新說明
5. 指定新版本文件路徑
6. 系統上傳新版本並設為最新版

版本管理：
- 版本號不可重複
- 新版本自動成為默認下載版本
- 舊版本保留供特定需求使用
```

#### D3: 下架遊戲 
```
操作步驟：
1. 選擇「3. 下架遊戲」  
2. 從列表選擇要下架的遊戲
3. 確認下架操作 (輸入 y)
4. 遊戲狀態變更為「已下架」

下架效果：
- 不再出現在玩家的遊戲列表中
- 已創建的房間可以繼續使用
- 已下載的玩家仍可本地遊玩
```

#### P1: 瀏覽遊戲商城 
```
商城功能：
1. 「遊戲商城」→「1. 瀏覽遊戲」
   - 顯示所有可用遊戲
   - 包含開發者、類型、版本、評分等資訊
2. 「遊戲商城」→「2. 搜尋遊戲」  
   - 輸入關鍵字搜尋遊戲名稱
3. 遊戲詳細資訊包含：
   - 遊戲名稱、開發者、簡介
   - 類型、最大玩家數、當前版本
   - 平均評分、評論數量、創建時間
```

#### P2: 下載並更新遊戲
```
下載流程：
1. 「遊戲商城」→「3. 下載遊戲」
2. 選擇要下載的遊戲
3. 系統檢查本地版本：
   - 無本地版本 → 直接下載最新版
   - 有舊版本 → 提示是否更新
   - 已是最新 → 跳過下載
4. 下載完成後解壓到獨立目錄

版本檢查機制：
- 每次下載前自動比對版本號
- 支援指定版本下載
- 檔案完整性驗證
- 下載失敗自動清理
```

#### P3: 建立房間並啟動遊戲 
```
房間管理流程：
1. 「大廳管理」→「2. 創建房間」
   - 選擇要遊玩的遊戲
   - 自動檢查本地是否有對應版本
   - 如無則提示先下載
2. 「大廳管理」→「3. 加入房間」  
   - 輸入房間ID加入現有房間
3. 房主操作「4. 開始遊戲」：
   - 檢查所有玩家都有正確版本
   - 啟動遊戲服務器
   - 自動啟動各玩家的遊戲客戶端
4. 遊戲結束後自動記錄遊玩紀錄

錯誤處理：
- 版本不匹配 → 自動下載更新
- 遊戲啟動失敗 → 顯示錯誤原因
- 連線中斷 → 房間狀態正確處理
```

#### P4: 遊戲評分與留言 
```
評論系統：
前置條件：
- 必須實際遊玩過該遊戲（有遊玩紀錄）

操作流程：
1. 「遊戲商城」→「5. 撰寫評論」
2. 輸入遊戲名稱
3. 給予評分 (1-5分)
4. 撰寫評論內容
5. 提交後更新遊戲平均評分

查看評論：
1. 「遊戲商城」→「4. 檢視評論」  
2. 輸入遊戲名稱查看所有評論
3. 顯示平均評分與評論列表

限制機制：
- 未遊玩 → 拒絕評論
- 重複評論 → 覆蓋舊評論
- 評分範圍檢查 (1-5)
```

### 遊戲實作範例

#### 數字猜謎遊戲 (Number Guessing Game)
```
遊戲規則：
- 雙人輪流猜測1-100之間的數字
- 系統給予「太高」或「太低」的提示  
- 猜中者得分，越少次數猜中得分越高
- 共進行10輪，總分高者獲勝

文件結構：
sample_games/number_guessing/
├── game_config.json          # 遊戲配置文件
├── number_guessing_server.py  # 遊戲服務器
└── number_guessing_client.py  # 遊戲客戶端
```

### 遊戲模板創建器
```bash
# 啟動模板創建工具
cd developer
python3 create_game_template.py

# 支援的模板類型：
1. CLI - 雙人命令行遊戲模板
2. GUI - 雙人圖形界面遊戲模板  
3. Multiplayer - 多人遊戲模板

# 自動生成：
- 遊戲配置文件 (game_config.json)
- 服務器端代碼模板
- 客戶端代碼模板
- GUI模板 (包含tkinter界面)
```

### 遊戲規格標準
```json
{
  "name": "遊戲名稱",
  "version": "版本號 (語意化版本)",
  "type": "遊戲類型 (cli/gui/multiplayer)",
  "max_players": "最大玩家數",
  "description": "遊戲描述",
  "author": "開發者名稱",
  "entry_point": {
    "server": "服務器腳本文件名",
    "client": "客戶端腳本文件名"
  },
  "requirements": ["依賴套件列表"]
}
```

## 🔧 技術實作細節

### 網路通信協議
```python
# 標準消息格式
{
  "type": "消息類型",
  "data": {
    # 消息數據
  }
}

# 標準回應格式  
{
  "status": "SUCCESS/ERROR/FAILED",
  "message": "回應訊息",
  "data": {
    # 回應數據
  }
}
```

### 版本管理策略
```
遊戲版本存儲結構：
uploaded_games/ 
├── GameName/
│   ├── 1.0.0/          # 版本目錄
│   │   ├── server.py
│   │   ├── client.py
│   │   └── config.json
│   └── 1.1.0/          # 新版本目錄
│       ├── server.py
│       ├── client.py
│       └── config.json

玩家下載結構：
downloads/PlayerName/
├── GameName/
│   ├── version.txt     # 當前版本記錄
│   └── 1.0.0/          # 版本目錄
│       ├── server.py
│       ├── client.py
│       └── config.json
```
