## 使用流程

### 1. 準備階段
```bash
# Clone 代碼
git clone https://github.com/milktea7654/Network-Programming.git
cd Network-Programming/HW3/game_platform_system

# 腳本啟動
cd /home/c0922/Network-Programming/HW3/game_platform_system
./start.sh

#手動啟動

# 終端1 - 服務器
cd /home/c0922/Network-Programming/HW3/game_platform_system/server
python3 main_server.py

# 終端2 - 開發者客戶端
cd /home/c0922/Network-Programming/HW3/game_platform_system/developer
python3 developer_client.py

# 終端3 - 玩家客戶端
cd /home/c0922/Network-Programming/HW3/game_platform_system/player
python3 lobby_client.py
```


### 2. Demo 開發者功能（終端2）
```bash
cd developer
python3 developer_client.py

# 依序操作：
# 1. 註冊 dev1/123456
# 2. 上傳 3 個遊戲
# 3. 更新一個遊戲版本
# 4. 下架一個遊戲
# 5. 查看統計
```

### 3. Demo 玩家功能（終端3-4）
```bash
# 玩家1
cd player
python3 lobby_client.py
# 1. 註冊 player1/123456
# 2. 瀏覽商城
# 3. 下載 Tic Tac Toe
# 4. 創建房間

# 玩家2（新終端）
cd player
python3 lobby_client.py
# 1. 登入 player2/123456
# 2. 加入房間
# 3. 等待開始

# 玩家1
# 4. 開始遊戲
# 5. 遊玩 GUI 遊戲
# 6. 撰寫評論
```

### 4. Demo 多人遊戲（終端3-6）
```bash
# 啟動 3-4 個玩家客戶端
# 都下載 Multiplayer Snake
# 一個玩家創建房間
# 其他玩家加入
# 房主開始遊戲
# 展示多人同時遊玩
```


### 清理數據
```bash
cd server/data
rm -f *.json
# 重啟服務器會重新初始化
```

### 清理下載的遊戲
```bash
cd player/downloads
rm -rf *
```