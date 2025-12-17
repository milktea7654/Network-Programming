### basic
scp -r /home/c0922/Network-Programming/HW{number}/ wqzheng@linux2.cs.nycu.edu.tw:~/

ssh wqzheng@linux2.cs.nycu.edu.tw

### HW1
python3 lobby_server.py --host 0.0.0.0 --port 12000

python3 player_b.py --lobby-host 127.0.0.1 --lobby-port 12000 --username testA --password 123 --udp-port 18000

python3 player_a.py --lobby-host linux2.cs.nycu.edu.tw --lobby-port 12000 --username milktea --password 7654 --scan-hosts linux2.cs.nycu.edu.tw --scan-port-start 18000 --scan-port-end 18020

### HW2

# Database Server
python3 db_server.py

# Lobby Server  
python3 lobby_server.py

# Check server
ps aux | grep "server.py"
netstat -tulpn | grep -E "10001|10002"

# Player
python3 lobby_client.py linux2.cs.nycu.edu.tw 10002

# test system
python3 test_system.py

# SQLite command
sqlite3 ~/HW2/game_database.db
> SELECT * FROM User;
> SELECT * FROM Room;
> SELECT * FROM GameLog;
> DELETE FROM GameLog;
> DELETE FROM Room;
> DELETE FROM User;
> DELETE FROM User WHERE name='player1';
> DELETE FROM Room WHERE id=1;
> .quit

rm ~/HW2/game_database.db

# Register
   - Username: player1
   - Email: player1@test.com
   - Password: 123456
   
# Login
   - Username: player1
   - Password: 123456

# Create Room
   - Room name: TestRoom
   - Visibility: public
   - 記下房間 ID

# List Room

# Join Room
   - 輸入房間 ID

# Spectator
    - 輸入房間 ID


【遊戲操作】
- 左/右方向鍵: 移動
- 上方向鍵/X: 順時針旋轉
- Z: 逆時針旋轉
- 下方向鍵: 軟降
- 空白鍵: 硬降
- C: Hold
- ESC: 退出

【其他功能】
13. 選擇 7 (View Stats) 查看個人統計
14. 選擇 8 (List Online Users) 查看線上使用者
15. 選擇 9 (Logout) 登出

###HW3

# Server (on linux2)
cd ~/Network-Programming/HW3/server && python3 main_server.py

# Developer client (local, connect to linux2)
cd ~/Network-Programming/HW3/developer && python3 developer_client.py

# Player client (local, connect to linux2)
cd ~/Network-Programming/HW3/player && python3 lobby_client.py

# Launcher (會自動連到設定的伺服器)
cd ~/Network-Programming/HW3 && python3 launcher.py

# Test connection
nc -zv linux2.cs.nycu.edu.tw 8001
nc -zv linux2.cs.nycu.edu.tw 8002

# Clear Python cache
find ~/Network-Programming/HW3 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find ~/Network-Programming/HW3 -name "*.pyc" -delete

# Initial server (reset data)
rm -f ~/Network-Programming/HW3/server/data/*.json

# Uninstall games
rm -rf ~/Network-Programming/HW3/player/downloads/*

# Upload to linux2
cd /home/c0922 && scp -r Network-Programming wqzheng@linux2.cs.nycu.edu.tw:~/
