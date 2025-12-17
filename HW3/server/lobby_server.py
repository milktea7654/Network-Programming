import socket
import threading
import os
import sys
import shutil
import zipfile
import subprocess
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from data_manager import DataManager
from models import Room
from protocol import NetworkProtocol, GameProtocol, ResponseCode

class LobbyServer:
    
    def __init__(self, host: str = "localhost", port: int = 8002, data_manager: DataManager = None):
        self.host = host
        self.port = port
        if data_manager:
            self.data_manager = data_manager
            print(f"   LobbyServer: 使用共用 DataManager (ID: {id(data_manager)})")
        else:
            self.data_manager = DataManager("./data")
            print(f"   LobbyServer: 創建新 DataManager (ID: {id(self.data_manager)})")
        
        self.upload_dir = "./uploaded_games"
        
        self.server_socket = None
        self.running = False
        self.clients = {}
        self.game_servers = {}
        self.next_game_port = 9000
    
    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            print(f"Lobby Server 啟動於 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    print(f"玩家客戶端連接: {address}")
                    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"接受連接時出錯: {e}")
        
        except Exception as e:
            print(f"啟動Lobby Server失敗: {e}")
        finally:
            self.cleanup()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        for process in self.game_servers.values():
            try:
                process.terminate()
            except:
                pass
    
    def monitor_game_server(self, room_id: str, game_process):
        import time
        try:
            print(f"[MONITOR] 開始監控房間 {room_id} 的遊戲服務器 (PID: {game_process.pid})")
            
            game_process.wait()
            
            print(f"[MONITOR] 遊戲服務器進程已結束 (房間: {room_id}, 退出碼: {game_process.returncode})")
            
            if room_id in self.data_manager.rooms:
                room = self.data_manager.rooms[room_id]
                room.status = "waiting"
                room.game_server_port = None
                self.data_manager.save_data()
                print(f"[MONITOR] 房間 {room_id} 狀態已重置為 waiting")
            
            if room_id in self.game_servers:
                del self.game_servers[room_id]
                
        except Exception as e:
            print(f"[MONITOR] 監控遊戲服務器時出錯: {e}")
    
    def cleanup(self):
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.clients.clear()
        
        if self.server_socket:
            self.server_socket.close()
    
    def handle_client(self, client_socket: socket.socket):
        client_addr = None
        try:
            client_addr = client_socket.getpeername()
            print(f"[CLIENT] 開始處理客戶端: {client_addr}")
        except:
            print(f"[CLIENT] 無法獲取客戶端地址")
        
        try:
            while self.running:
                message = NetworkProtocol.receive_message(client_socket)
                if not message:
                    print(f"[CLIENT] 客戶端 {client_addr} 斷開連接")
                    break
                
                msg_type = message.get('type', 'UNKNOWN')
                print(f"[CLIENT] 收到消息類型: {msg_type}")
                
                response = self.process_message(client_socket, message)
                if response:
                    print(f"[CLIENT] 準備發送回應: {response.get('status')}")
                    if not NetworkProtocol.send_message(client_socket, response):
                        print(f"[CLIENT] 發送回應失敗")
                        break
                    print(f"[CLIENT] 回應已發送")
                    
        except Exception as e:
            print(f"[CLIENT] 處理客戶端時出錯: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client_socket in self.clients:
                username = self.clients[client_socket]
                print(f"玩家 {username} 斷開連接，進行清理...")
                
                rooms_to_clean = []
                for room_id, room in self.data_manager.rooms.items():
                    if username in room.players:
                        print(f"   從房間 {room_id} 移除玩家 {username}")
                        room.players.remove(username)
                        
                        if not room.players:
                            rooms_to_clean.append(room_id)
                            print(f"   房間 {room_id} 已空，將被刪除")
                        elif room.host == username and room.players:
                            room.host = room.players[0]
                            print(f"   房主已轉移給 {room.host}")
                
                for room_id in rooms_to_clean:
                    del self.data_manager.rooms[room_id]
                
                if rooms_to_clean or any(username in room.players for room in self.data_manager.rooms.values()):
                    self.data_manager.save_data()
                
                self.data_manager.set_user_online(username, False)
                del self.clients[client_socket]
                
                print(f" 玩家 {username} 清理完成")
            client_socket.close()
    
    def process_message(self, client_socket: socket.socket, message: Dict[str, Any]) -> Dict[str, Any]:

        msg_type = message.get('type')
        data = message.get('data', {})
        
        try:
            if msg_type == NetworkProtocol.MSG_REGISTER:
                return self.handle_register(data)
            elif msg_type == NetworkProtocol.MSG_LOGIN:
                return self.handle_login(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_LOGOUT:
                return self.handle_logout(client_socket)
            elif msg_type == NetworkProtocol.MSG_LIST_GAMES:
                return self.handle_list_games()
            elif msg_type == NetworkProtocol.MSG_GET_GAME_INFO:
                return self.handle_get_game_info(data)
            elif msg_type == NetworkProtocol.MSG_DOWNLOAD_GAME:
                return self.handle_download_game(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_LIST_ROOMS:
                return self.handle_list_rooms()
            elif msg_type == NetworkProtocol.MSG_CREATE_ROOM:
                return self.handle_create_room(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_JOIN_ROOM:
                return self.handle_join_room(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_LEAVE_ROOM:
                return self.handle_leave_room(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_START_GAME:
                return self.handle_start_game(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_ADD_REVIEW:
                return self.handle_add_review(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_GET_REVIEWS:
                return self.handle_get_reviews(data)
            elif msg_type == NetworkProtocol.MSG_GET_PLAYER_RECORDS:
                return self.handle_get_player_records(client_socket)
            else:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "未知的消息類型"
                )
                
        except Exception as e:
            print(f"處理消息時出錯: {e}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"服務器內部錯誤: {str(e)}"
            )
    
    def handle_register(self, data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[REGISTER] 收到註冊請求")
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[REGISTER] 用戶名: {username}, 密碼長度: {len(password)}")
        
        if not username or not password:
            print(f"[REGISTER] 註冊失敗: 用戶名或密碼為空")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名和密碼不能為空"
            )
        
        if self.data_manager.create_user(username, password, 'player'):
            print(f"[REGISTER] 註冊成功: {username}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "註冊成功"
            )
        else:
            print(f"[REGISTER] 註冊失敗: 用戶名已存在 - {username}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名已存在"
            )
    
    def handle_login(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = self.data_manager.authenticate_user(username, password, 'player')
        if user:
            if user.is_online:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "該帳號已在其他裝置登入"
                )
            
            self.clients[client_socket] = username
            self.data_manager.set_user_online(username, True)
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "登入成功",
                {'username': username}
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "帳號或密碼錯誤"
            )
    
    def handle_logout(self, client_socket: socket.socket) -> Dict[str, Any]:

        if client_socket in self.clients:
            username = self.clients[client_socket]
            print(f"玩家 {username} 主動登出，進行清理...")
            
            rooms_to_clean = []
            for room_id, room in self.data_manager.rooms.items():
                if username in room.players:
                    print(f"   從房間 {room_id} 移除玩家 {username}")
                    room.players.remove(username)

                    if not room.players:
                        rooms_to_clean.append(room_id)
                        print(f"   房間 {room_id} 已空，將被刪除")
                    elif room.host == username and room.players:
                        room.host = room.players[0]
                        print(f"   房主已轉移給 {room.host}")

            for room_id in rooms_to_clean:
                del self.data_manager.rooms[room_id]

            if rooms_to_clean or any(username in room.players for room in self.data_manager.rooms.values()):
                self.data_manager.save_data()

            self.data_manager.set_user_online(username, False)
            del self.clients[client_socket]
            
            print(f" 玩家 {username} 登出清理完成")
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "登出成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "未登入"
            )
    
    def handle_list_games(self) -> Dict[str, Any]:
        self.data_manager.load_data()
        games = self.data_manager.get_active_games()
        print(f" DEBUG: 重新載入後獲取到 {len(games)} 個活躍遊戲")
        print(f" DEBUG: 所有遊戲與狀態:")
        for name, game in self.data_manager.games.items():
            status = "已上架" if game.is_active else "已下架"
            print(f"   - {name}: {status}")
        
        games_data = []
        for game in games:
            games_data.append({
                'name': game.name,
                'developer': game.developer,
                'description': game.description,
                'type': game.game_type,
                'max_players': game.max_players,
                'current_version': game.current_version,
                'rating': game.get_average_rating(),
                'rating_count': game.rating_count,
                'created_at': game.created_at.strftime("%Y-%m-%d")
            })
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取遊戲列表成功",
            {'games': games_data}
        )
    
    def handle_get_game_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        game_name = data.get('name', '').strip()
        
        if game_name not in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲不存在"
            )
        
        game = self.data_manager.games[game_name]
        if not game.is_active:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲已下架"
            )
        
        game_info = {
            'name': game.name,
            'developer': game.developer,
            'description': game.description,
            'type': game.game_type,
            'max_players': game.max_players,
            'current_version': game.current_version,
            'versions': [{'version': v, 'uploaded_at': info['uploaded_at'].strftime("%Y-%m-%d %H:%M"), 
                         'description': info['description']} 
                        for v, info in game.versions.items()],
            'rating': game.get_average_rating(),
            'rating_count': game.rating_count,
            'reviews': game.reviews[-10:],  
            'created_at': game.created_at.strftime("%Y-%m-%d")
        }
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取遊戲信息成功",
            {'game': game_info}
        )
    
    def handle_download_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        game_name = data.get('name', '').strip()
        version = data.get('version', '').strip()
        
        if game_name not in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲不存在"
            )
        
        game = self.data_manager.games[game_name]
        if not game.is_active:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲已下架"
            )
        
        if not version:
            version = game.current_version
        
        if version not in game.versions:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "指定版本不存在"
            )
        
        game_dir = os.path.join(self.upload_dir, game_name, version)
        if not os.path.exists(game_dir):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲文件不存在"
            )

        temp_zip = f"/tmp/{game_name}_v{version}_{uuid.uuid4().hex}.zip"
        
        try:
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(game_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, game_dir)
                        zipf.write(file_path, arcname)
            
            response = NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "準備發送遊戲文件",
                {'name': game_name, 'version': version}
            )
            NetworkProtocol.send_message(client_socket, response)
            
            if GameProtocol.send_file(client_socket, temp_zip):
                os.remove(temp_zip)
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_SUCCESS,
                    "遊戲下載完成"
                )
            else:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "發送遊戲文件失敗"
                )
                
        except Exception as e:
            print(f"下載遊戲時出錯: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"下載失敗: {str(e)}"
            )
    
    def handle_list_rooms(self) -> Dict[str, Any]:
        rooms = self.data_manager.get_active_rooms()
        
        rooms_data = []
        for room in rooms:
            game = self.data_manager.games.get(room.game_name)
            rooms_data.append({
                'room_id': room.room_id,
                'host': room.host,
                'game_name': room.game_name,
                'game_version': room.game_version,
                'max_players': room.max_players,
                'current_players': len(room.players),
                'players': room.players,
                'status': room.status,
                'game_server_port': room.game_server_port,
                'created_at': room.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取房間列表成功",
            {'rooms': rooms_data}
        )
    
    def handle_create_room(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        game_name = data.get('game_name', '').strip()
        game_version = data.get('game_version', '').strip()
        
        if game_name not in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲不存在"
            )
        
        game = self.data_manager.games[game_name]
        if not game.is_active:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲已下架"
            )
        
        if not game_version:
            game_version = game.current_version
        
        if game_version not in game.versions:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "指定版本不存在"
            )

        room_id = str(uuid.uuid4())[:8]

        room = Room(room_id, username, game_name, game_version, game.max_players)
        
        if self.data_manager.create_room(room):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "房間創建成功",
                {
                    'room_id': room_id,
                    'game_name': game_name,
                    'game_version': game_version,
                    'max_players': game.max_players
                }
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "創建房間失敗"
            )
    
    def handle_join_room(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        room_id = data.get('room_id', '').strip()
        
        room = self.data_manager.get_room(room_id)
        if not room:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "房間不存在"
            )
        
        if room.is_full():
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "房間已滿"
            )
        
        if username in room.players:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "您已在房間中"
            )
        
        if room.add_player(username):
            self.data_manager.save_data()
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "加入房間成功",
                {
                    'room_id': room_id,
                    'players': room.players,
                    'game_name': room.game_name
                }
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "加入房間失敗"
            )
    
    def handle_leave_room(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        room_id = data.get('room_id', '').strip()
        
        room = self.data_manager.get_room(room_id)
        if not room:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "房間不存在"
            )
        
        if username not in room.players:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "您不在該房間中"
            )
        
        room.remove_player(username)
        
        if not room.players:
            self.data_manager.remove_room(room_id)
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "房間已解散"
            )
        elif username == room.host:
            room.host = room.players[0]
            self.data_manager.save_data()
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                f"離開房間成功，房主已轉移給 {room.host}"
            )
        else:
            self.data_manager.save_data()
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "離開房間成功"
            )
    
    def handle_start_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        room_id = data.get('room_id', '').strip()
        
        room = self.data_manager.get_room(room_id)
        if not room:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "房間不存在"
            )
        
        if username != room.host:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "只有房主可以開始遊戲"
            )
        
        if len(room.players) < 2:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "至少需要2名玩家才能開始遊戲"
            )
    
        game_port = self.next_game_port
        self.next_game_port += 1
        
        try:
            game_server_path = self.find_game_server(room.game_name, room.game_version)
            if not game_server_path:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "找不到遊戲服務器文件"
                )
            
            import subprocess
            
            game_server_path = os.path.abspath(game_server_path)
            game_server_dir = os.path.dirname(game_server_path)
            
            print(f"[DEBUG] 啟動遊戲服務器: {game_server_path}")
            print(f"[DEBUG] 工作目錄: {game_server_dir}")
            print(f"[DEBUG] 參數: port={game_port}")
            print(f"[DEBUG] Python: {sys.executable}")
            
            game_process = subprocess.Popen([
                sys.executable, "-u", game_server_path, str(game_port)
            ], 
            cwd=game_server_dir)
            
            self.game_servers[room_id] = game_process
            
            print(f"[DEBUG] 遊戲服務器進程已啟動 PID: {game_process.pid}")
            
            monitor_thread = threading.Thread(
                target=self.monitor_game_server,
                args=(room_id, game_process),
                daemon=True
            )
            monitor_thread.start()
            room.game_server_port = game_port
            room.status = "playing"
            
            print(f"[DEBUG] 準備添加遊戲記錄，玩家列表: {room.players}")
            for player in room.players:
                print(f"[DEBUG] 添加記錄: 玩家={player}, 遊戲={room.game_name}, 版本={room.game_version}")
                self.data_manager.add_game_record(player, room.game_name, room.game_version)
            
            print(f"[DEBUG] 房間狀態已更新並保存: port={game_port}")
            
            import time
            print(f"[DEBUG] 等待遊戲服務器啟動...")
            time.sleep(2)  

            if game_process.poll() is not None:
                error_msg = f" 遊戲服務器啟動失敗 (退出碼: {game_process.returncode})"
                print(f"[ERROR] {error_msg}")
                print(f"[ERROR] 請查看上方的遊戲服務器輸出以了解詳細錯誤")
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    error_msg
                )
            
            print(f"[DEBUG]  遊戲服務器進程運行中 (PID: {game_process.pid})")
            print(f"[DEBUG] 遊戲服務器應該正在監聽 0.0.0.0:{game_port}")
            print(f"[DEBUG] 客戶端將使用 lobby_server 地址連接到端口 {game_port}")
            
            time.sleep(1)
            try:
                import socket as test_socket
                s = test_socket.socket(test_socket.AF_INET, test_socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex(('localhost', game_port))
                s.close()
                if result == 0:
                    print(f"[DEBUG]  端口 {game_port} 確認已開放")
                else:
                    print(f"[WARNING]   端口 {game_port} 無法連接 (錯誤碼: {result})")
                    print(f"[WARNING] 遊戲服務器可能還在初始化中...")
            except Exception as e:
                print(f"[WARNING] 端口檢查失敗: {e}")
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "遊戲已開始",
                {
                    'room_id': room_id,
                    'game_server_port': game_port,
                    'players': room.players
                }
            )
            
        except Exception as e:
            print(f"啟動遊戲服務器失敗: {e}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"啟動遊戲失敗: {str(e)}"
            )
    
    def find_game_server(self, game_name: str, version: str) -> Optional[str]:
        version_dir = os.path.abspath(os.path.join(self.upload_dir, game_name, version))
        print(f"[DEBUG] 查找遊戲服務器於: {version_dir}")
        
        if not os.path.exists(version_dir):
            print(f"[ERROR] 版本目錄不存在: {version_dir}")
            return None
        
        for filename in os.listdir(version_dir):
            if filename.endswith('_server.py'):
                server_path = os.path.join(version_dir, filename)
                if os.path.exists(server_path):
                    print(f"[DEBUG] 找到遊戲服務器: {server_path}")
                    return server_path
        
        print(f"[ERROR] 在 {version_dir} 中找不到 *_server.py 文件")
        return None
    
    def handle_add_review(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:

        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        game_name = data.get('game_name', '').strip()
        rating = data.get('rating', 0)
        comment = data.get('comment', '').strip()
        
        if not game_name or rating < 1 or rating > 5:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲名稱不能為空，評分須介於1-5分"
            )
        
        if self.data_manager.add_review(username, game_name, rating, comment):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "評論添加成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "添加評論失敗：未玩過該遊戲或遊戲不存在"
            )
    
    def handle_get_reviews(self, data: Dict[str, Any]) -> Dict[str, Any]:
        game_name = data.get('game_name', '').strip()
        
        if game_name not in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲不存在"
            )
        
        game = self.data_manager.games[game_name]
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取評論成功",
            {
                'reviews': game.reviews,
                'average_rating': game.get_average_rating(),
                'rating_count': game.rating_count
            }
        )
    
    def handle_get_player_records(self, client_socket: socket.socket) -> Dict[str, Any]:
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        records = self.data_manager.get_player_records(username)
        
        print(f"[DEBUG] handle_get_player_records: username={username}, 找到 {len(records)} 條記錄")
        
        records_data = []
        for record in records:
            records_data.append({
                'game_name': record.game_name,
                'game_version': record.game_version,
                'played_at': record.played_at.strftime("%Y-%m-%d %H:%M"),
                'has_reviewed': record.has_reviewed
            })
        
        print(f"[DEBUG] 準備返回記錄數據: {records_data}")
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取記錄成功",
            {'records': records_data}
        )

if __name__ == "__main__":
    server = LobbyServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n正在關閉Lobby Server...")
        server.stop()