# 快速開始指南

## 在課程機上部署

### 1. 上傳所有檔案到課程機

```bash
# 在本地端
scp -r HW2/ <你的帳號>@<課程機IP>:~/Network-Programming/
```

### 2. 在課程機上啟動伺服器

```bash
ssh <你的帳號>@<課程機IP>
cd ~/Network-Programming/HW2
./start_servers.sh
```

伺服器會啟動在背景，輸出如下：
```
Starting Database Server...
Starting Lobby Server...
==========================================
Servers are running:
  Database Server (PID: 12345) on port 10001
  Lobby Server (PID: 12346) on port 10002
==========================================
```

## 在本地端測試

### 1. 安裝依賴

```bash
cd ~/Network-Programming/HW2
pip3 install -r requirements.txt
```

### 2. 啟動第一個客戶端

```bash
python3 lobby_client.py <課程機IP> 10002
```

在選單中：
1. 選擇 `2` (Login) 或 `1` (Register)
2. 如果是新使用者，先註冊：
   - Username: player1
   - Email: player1@test.com
   - Password: 123456
3. 然後登入
4. 選擇 `3` (Create Room)
   - Room name: TestRoom
   - Visibility: public

### 3. 啟動第二個客戶端（在另一個終端）

```bash
python3 lobby_client.py <課程機IP> 10002
```

在選單中：
1. 註冊並登入（使用不同的帳號，例如 player2）
2. 選擇 `4` (Join Room)
3. 輸入房間 ID（從房間列表中看到）

### 4. 開始遊戲

在第一個客戶端（房主）：
1. 選擇 `3` (Start Game)
2. 遊戲視窗會自動開啟

在第二個客戶端：
- 遊戲視窗也會自動開啟

### 5. 遊戲操作

- **左/右方向鍵**: 移動方塊
- **上方向鍵 / X**: 順時針旋轉
- **Z**: 逆時針旋轉
- **下方向鍵**: 軟降（加速下落）
- **空白鍵**: 硬降（直接降到底）
- **C**: Hold（保留當前方塊）
- **ESC**: 退出遊戲

### 6. 遊戲結束

- 當其中一位玩家的方塊頂到棋盤頂部，遊戲結束
- 螢幕會顯示勝負結果
- 按 ESC 退出遊戲視窗
- 可以回到大廳再開新的一局

## 快速測試腳本

如果你在 Linux 系統且有 gnome-terminal：

```bash
./test_game.sh <課程機IP>
```

這會自動開啟兩個終端視窗，每個都執行一個客戶端。

## 常見問題

### Q: pygame 安裝失敗
A: 確保已安裝開發工具：
```bash
sudo apt-get install python3-dev python3-pygame
```
或使用 pip：
```bash
pip3 install pygame --user
```

### Q: 連接失敗
A: 檢查：
1. 課程機的防火牆是否允許 port 10001, 10002
2. IP 位址是否正確
3. 伺服器是否正在運行

### Q: 遊戲視窗沒有出現
A: 
1. 檢查是否安裝了 pygame
2. 手動啟動遊戲客戶端：
   ```bash
   python3 game_client.py <課程機IP> <遊戲port> <你的user_id> <room_id>
   ```

### Q: 如何停止伺服器
A: 在執行 `start_servers.sh` 的終端按 Ctrl+C，或：
```bash
pkill -f db_server.py
pkill -f lobby_server.py
pkill -f game_server.py
```

## 檢查伺服器狀態

```bash
# 檢查是否在運行
ps aux | grep "server.py"

# 檢查 port 是否在監聽
netstat -tulpn | grep -E "10001|10002"
```

## Demo 建議流程

1. **展示資料庫功能**：
   - 註冊多個使用者
   - 顯示線上使用者列表

2. **展示房間管理**：
   - 創建公開和私有房間
   - 顯示房間列表
   - 邀請功能

3. **展示遊戲**：
   - 兩位玩家進入房間
   - 開始遊戲
   - 展示各種操作（移動、旋轉、Hold、硬降）
   - 顯示對手棋盤同步
   - 遊戲結束顯示勝負

4. **展示錯誤處理**：
   - 嘗試加入已滿的房間
   - 非房主嘗試開始遊戲
   - 斷線重連

## 進階設定

### 修改遊戲速度

編輯 `game_server.py`：
```python
self.drop_interval = 500  # 毫秒，改小會加快下落速度
```

### 修改棋盤大小

編輯 `tetris_logic.py`：
```python
def __init__(self, width=10, height=20, seed=None):
    # 修改 width 和 height
```

### 查看資料庫內容

```bash
sqlite3 game_database.db
```

SQL 指令：
```sql
SELECT * FROM User;
SELECT * FROM Room;
SELECT * FROM GameLog;
```
