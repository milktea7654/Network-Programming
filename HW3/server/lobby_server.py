#!/usr/bin/env python3
"""
Lobby Server
處理玩家相關的請求：遊戲瀏覽、下載、房間管理、遊戲啟動等
"""
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
    """大廳服務器"""
    
    def __init__(self, host: str = "localhost", port: int = 8002, data_dir: str = "./data"):
        self.host = host
        self.port = port
        self.data_manager = DataManager(data_dir)
        self.upload_dir = "./uploaded_games"
        
        self.server_socket = None
        self.running = False
        self.clients = {}  # {socket: username}
        self.game_servers = {}  # {room_id: process}
        self.next_game_port = 9000  # 遊戲服務器端口起始
    
    def start(self):
        """啟動服務器"""
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
                    print(f"玩家客戶端連接: {address}")
                    
                    # 為每個客戶端創建處理線程
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
        """停止服務器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 關閉所有遊戲服務器
        for process in self.game_servers.values():
            try:
                process.terminate()
            except:
                pass
    
    def cleanup(self):
        """清理資源"""
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.clients.clear()
        
        if self.server_socket:
            self.server_socket.close()
    
    def handle_client(self, client_socket: socket.socket):
        """處理客戶端請求"""
        try:
            while self.running:
                message = NetworkProtocol.receive_message(client_socket)
                if not message:
                    break
                
                response = self.process_message(client_socket, message)
                if response:
                    NetworkProtocol.send_message(client_socket, response)
                    
        except Exception as e:
            print(f"處理客戶端時出錯: {e}")
        finally:
            # 客戶端斷線處理
            if client_socket in self.clients:
                username = self.clients[client_socket]
                self.data_manager.set_user_online(username, False)
                del self.clients[client_socket]
            client_socket.close()
    
    def process_message(self, client_socket: socket.socket, message: Dict[str, Any]) -> Dict[str, Any]:
        """處理消息"""
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
        """處理註冊"""
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名和密碼不能為空"
            )
        
        if self.data_manager.create_user(username, password, 'player'):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "註冊成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名已存在"
            )
    
    def handle_login(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理登入"""
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = self.data_manager.authenticate_user(username, password, 'player')
        if user:
            # 檢查是否已經在線
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
        """處理登出"""
        if client_socket in self.clients:
            username = self.clients[client_socket]
            self.data_manager.set_user_online(username, False)
            del self.clients[client_socket]
            
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
        """獲取遊戲列表"""
        games = self.data_manager.get_active_games()
        
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
        """獲取遊戲詳細信息"""
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
            'reviews': game.reviews[-10:],  # 最近10條評論
            'created_at': game.created_at.strftime("%Y-%m-%d")
        }
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取遊戲信息成功",
            {'game': game_info}
        )
    
    def handle_download_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理遊戲下載"""
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
        
        # 如果未指定版本，使用最新版本
        if not version:
            version = game.current_version
        
        if version not in game.versions:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "指定版本不存在"
            )
        
        # 準備遊戲文件
        game_dir = os.path.join(self.upload_dir, game_name, version)
        if not os.path.exists(game_dir):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲文件不存在"
            )
        
        # 創建臨時zip文件
        temp_zip = f"/tmp/{game_name}_v{version}_{uuid.uuid4().hex}.zip"
        
        try:
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(game_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, game_dir)
                        zipf.write(file_path, arcname)
            
            # 通知客戶端準備接收文件
            response = NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "準備發送遊戲文件",
                {'name': game_name, 'version': version}
            )
            NetworkProtocol.send_message(client_socket, response)
            
            # 發送文件
            if GameProtocol.send_file(client_socket, temp_zip):
                # 刪除臨時文件
                os.remove(temp_zip)
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_SUCCESS,
                    "遊戲下載完成"
                )
            else:
                # 刪除臨時文件
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
        """獲取房間列表"""
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
                'created_at': room.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取房間列表成功",
            {'rooms': rooms_data}
        )
    
    def handle_create_room(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理創建房間"""
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
        
        # 如果未指定版本，使用最新版本
        if not game_version:
            game_version = game.current_version
        
        if game_version not in game.versions:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "指定版本不存在"
            )
        
        # 生成房間ID
        room_id = str(uuid.uuid4())[:8]
        
        # 創建房間
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
        """處理加入房間"""
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
        """處理離開房間"""
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
        
        # 如果房間空了或者房主離開了，刪除房間
        if not room.players or username == room.host:
            self.data_manager.remove_room(room_id)
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "房間已解散"
            )
        else:
            self.data_manager.save_data()
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "離開房間成功"
            )
    
    def handle_start_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理開始遊戲"""
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
        
        # 啟動遊戲服務器
        game_port = self.next_game_port
        self.next_game_port += 1
        
        try:
            # 啟動遊戲服務器進程
            game_server_path = self.find_game_server(room.game_name, room.game_version)
            if not game_server_path:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "找不到遊戲服務器文件"
                )
            
            # 使用subprocess啟動遊戲服務器
            import subprocess
            game_process = subprocess.Popen([
                sys.executable, game_server_path, str(game_port)
            ], cwd=os.path.dirname(game_server_path))
            
            # 記錄遊戲服務器進程
            self.game_servers[room_id] = game_process
            
            room.game_server_port = game_port
            room.status = "playing"
            
            # 記錄玩家遊戲紀錄
            for player in room.players:
                self.data_manager.add_game_record(player, room.game_name, room.game_version)
            
            self.data_manager.save_data()
            
            # 等待遊戲服務器啟動
            import time
            time.sleep(2)
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "遊戲已開始",
                {
                    'room_id': room_id,
                    'game_server_host': self.host,
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
        """查找遊戲服務器文件"""
        version_dir = os.path.join(self.upload_dir, game_name, version)
        if not os.path.exists(version_dir):
            return None
        
        # 查找服務器腳本
        for filename in os.listdir(version_dir):
            if filename.endswith('_server.py'):
                server_path = os.path.join(version_dir, filename)
                if os.path.exists(server_path):
                    return server_path
        
        return None
    
    def handle_add_review(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理添加評論"""
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
        """獲取遊戲評論"""
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
        """獲取玩家遊戲記錄"""
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        username = self.clients[client_socket]
        records = self.data_manager.get_player_records(username)
        
        records_data = []
        for record in records:
            records_data.append({
                'game_name': record.game_name,
                'game_version': record.game_version,
                'played_at': record.played_at.strftime("%Y-%m-%d %H:%M"),
                'has_reviewed': record.has_reviewed
            })
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取遊戲記錄成功",
            {'records': records_data}
        )

if __name__ == "__main__":
    server = LobbyServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n正在關閉Lobby Server...")
        server.stop()