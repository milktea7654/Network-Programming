"""
Lobby Server - 大廳伺服器
處理使用者註冊、登入、房間管理、配對等功能
"""
import socket
import threading
import json
from datetime import datetime
from protocol import send_message, recv_message, ProtocolError
import hashlib
import subprocess
import time

LOBBY_HOST = '0.0.0.0'
LOBBY_PORT = 10002
DB_HOST = 'localhost'
DB_PORT = 10001

# 遊戲伺服器 port 範圍
GAME_SERVER_PORT_START = 10100
GAME_SERVER_PORT_END = 10200


class LobbyServer:
    def __init__(self, host=LOBBY_HOST, port=LOBBY_PORT):
        self.host = host
        self.port = port
        self.running = False
        
        # 線上使用者：{user_id: {'socket': socket, 'name': str, 'room_id': int or None}}
        self.online_users = {}
        
        # 使用者 socket 映射：{socket: user_id}
        self.socket_to_user = {}
        
        # 房間成員：{room_id: [user_id1, user_id2]}
        self.room_members = {}
        
        # 邀請列表：{user_id: [{'from_user_id': int, 'room_id': int, 'room_name': str}]}
        self.invitations = {}
        
        # 遊戲伺服器：{room_id: {'port': int, 'process': subprocess.Popen}}
        self.game_servers = {}
        
        # Port 分配
        self.next_game_port = GAME_SERVER_PORT_START
        
        # 鎖
        self.lock = threading.Lock()
    
    def start(self):
        """啟動大廳伺服器"""
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)
        
        print(f"[Lobby Server] Listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    print(f"[Lobby] New connection from {addr}")
                    
                    # 為每個連接創建新線程
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n[Lobby Server] Shutting down...")
        finally:
            server_socket.close()
            self.cleanup_game_servers()
    
    def handle_client(self, client_socket, addr):
        """處理客戶端請求"""
        user_id = None
        
        try:
            while True:
                # 接收請求
                request = recv_message(client_socket)
                action = request.get('action')
                
                print(f"[Lobby] Request from {addr}: {action}")
                
                # 處理請求
                response = self.process_request(request, client_socket, user_id)
                
                # 更新 user_id（登入後）
                if action == 'login' and response.get('success'):
                    user_id = response.get('userId')
                elif action == 'logout':
                    user_id = None
                
                # 發送回應
                send_message(client_socket, response)
                
        except (ConnectionError, ProtocolError) as e:
            print(f"[Lobby] Connection error from {addr}: {e}")
        except Exception as e:
            print(f"[Lobby] Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理使用者連接
            if user_id:
                self.handle_user_disconnect(user_id)
            client_socket.close()
            print(f"[Lobby] Connection closed: {addr}")
    
    def process_request(self, request, client_socket, user_id):
        """處理各種請求"""
        action = request.get('action')
        data = request.get('data', {})
        
        try:
            if action == 'register':
                return self.register_user(data)
            elif action == 'login':
                return self.login_user(data, client_socket)
            elif action == 'logout':
                return self.logout_user(user_id)
            elif action == 'list_online':
                return self.list_online_users()
            elif action == 'list_rooms':
                return self.list_rooms()
            elif action == 'create_room':
                return self.create_room(user_id, data)
            elif action == 'join_room':
                return self.join_room(user_id, data)
            elif action == 'leave_room':
                return self.leave_room(user_id)
            elif action == 'invite_user':
                return self.invite_user(user_id, data)
            elif action == 'list_invitations':
                return self.list_invitations(user_id)
            elif action == 'accept_invitation':
                return self.accept_invitation(user_id, data)
            elif action == 'start_game':
                return self.start_game(user_id)
            elif action == 'game_ended':
                return self.handle_game_ended(data)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def register_user(self, data):
        """註冊使用者"""
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not all([name, email, password]):
            return {'success': False, 'error': 'Missing required fields'}
        
        # 計算密碼雜湊
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # 透過 DB Server 創建使用者
        response = self.db_request({
            'collection': 'User',
            'action': 'create',
            'data': {
                'name': name,
                'email': email,
                'passwordHash': password_hash
            }
        })
        
        return response
    
    def login_user(self, data, client_socket):
        """登入使用者"""
        name = data.get('name')
        password = data.get('password')
        
        if not all([name, password]):
            return {'success': False, 'error': 'Missing required fields'}
        
        # 查詢使用者
        response = self.db_request({
            'collection': 'User',
            'action': 'query',
            'data': {'name': name}
        })
        
        if not response.get('success') or not response.get('data'):
            return {'success': False, 'error': 'User not found'}
        
        user = response['data'][0]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user['passwordHash'] != password_hash:
            return {'success': False, 'error': 'Invalid password'}
        
        # 更新最後登入時間
        self.db_request({
            'collection': 'User',
            'action': 'update',
            'data': {
                'id': user['id'],
                'updates': {'lastLoginAt': datetime.now().isoformat()}
            }
        })
        
        # 加入線上列表
        with self.lock:
            self.online_users[user['id']] = {
                'socket': client_socket,
                'name': user['name'],
                'room_id': None
            }
            self.socket_to_user[client_socket] = user['id']
            self.invitations[user['id']] = []
        
        return {'success': True, 'userId': user['id'], 'name': user['name']}
    
    def logout_user(self, user_id):
        """登出使用者"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        self.handle_user_disconnect(user_id)
        return {'success': True}
    
    def handle_user_disconnect(self, user_id):
        """處理使用者斷線"""
        with self.lock:
            if user_id in self.online_users:
                user_info = self.online_users[user_id]
                
                # 如果在房間中，離開房間
                if user_info['room_id']:
                    self.leave_room(user_id)
                
                # 移除 socket 映射
                if user_info['socket'] in self.socket_to_user:
                    del self.socket_to_user[user_info['socket']]
                
                # 移除線上使用者
                del self.online_users[user_id]
                
                # 清理邀請
                if user_id in self.invitations:
                    del self.invitations[user_id]
                
                print(f"[Lobby] User {user_id} disconnected")
    
    def list_online_users(self):
        """列出線上使用者"""
        with self.lock:
            users = [
                {'userId': uid, 'name': info['name'], 'inRoom': info['room_id'] is not None}
                for uid, info in self.online_users.items()
            ]
        return {'success': True, 'users': users}
    
    def list_rooms(self):
        """列出公開房間"""
        response = self.db_request({
            'collection': 'Room',
            'action': 'query',
            'data': {}
        })
        
        if not response.get('success'):
            return response
        
        rooms = response.get('data', [])
        
        # 加入當前成員數資訊
        with self.lock:
            for room in rooms:
                room['memberCount'] = len(self.room_members.get(room['id'], []))
        
        return {'success': True, 'rooms': rooms}
    
    def create_room(self, user_id, data):
        """創建房間"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        name = data.get('name')
        visibility = data.get('visibility', 'public')
        
        if not name:
            return {'success': False, 'error': 'Room name required'}
        
        # 檢查是否已在房間中
        with self.lock:
            if self.online_users[user_id]['room_id']:
                return {'success': False, 'error': 'Already in a room'}
        
        # 創建房間
        response = self.db_request({
            'collection': 'Room',
            'action': 'create',
            'data': {
                'name': name,
                'hostUserId': user_id,
                'visibility': visibility,
                'inviteList': []
            }
        })
        
        if not response.get('success'):
            return response
        
        room_id = response['id']
        
        # 房主自動加入房間
        with self.lock:
            self.online_users[user_id]['room_id'] = room_id
            self.room_members[room_id] = [user_id]
        
        return {'success': True, 'roomId': room_id}
    
    def join_room(self, user_id, data):
        """加入房間"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        room_id = data.get('roomId')
        
        if not room_id:
            return {'success': False, 'error': 'Room ID required'}
        
        # 檢查房間是否存在
        room_response = self.db_request({
            'collection': 'Room',
            'action': 'read',
            'data': {'id': room_id}
        })
        
        if not room_response.get('success'):
            return {'success': False, 'error': 'Room not found'}
        
        room = room_response['data']
        
        # 檢查房間是否已滿（2人）
        with self.lock:
            members = self.room_members.get(room_id, [])
            if len(members) >= 2:
                return {'success': False, 'error': 'Room is full'}
            
            # 檢查是否已在房間中
            if self.online_users[user_id]['room_id']:
                return {'success': False, 'error': 'Already in a room'}
            
            # 加入房間
            self.online_users[user_id]['room_id'] = room_id
            if room_id not in self.room_members:
                self.room_members[room_id] = []
            self.room_members[room_id].append(user_id)
        
        return {'success': True}
    
    def leave_room(self, user_id):
        """離開房間"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        with self.lock:
            room_id = self.online_users[user_id]['room_id']
            
            if not room_id:
                return {'success': False, 'error': 'Not in a room'}
            
            # 從房間移除
            if room_id in self.room_members:
                self.room_members[room_id].remove(user_id)
                
                # 如果房間空了，刪除房間
                if len(self.room_members[room_id]) == 0:
                    del self.room_members[room_id]
                    
                    # 從資料庫刪除
                    self.db_request({
                        'collection': 'Room',
                        'action': 'delete',
                        'data': {'id': room_id}
                    })
            
            self.online_users[user_id]['room_id'] = None
        
        return {'success': True}
    
    def invite_user(self, user_id, data):
        """邀請使用者加入房間"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        target_user_id = data.get('targetUserId')
        
        with self.lock:
            room_id = self.online_users[user_id]['room_id']
            
            if not room_id:
                return {'success': False, 'error': 'Not in a room'}
            
            if target_user_id not in self.online_users:
                return {'success': False, 'error': 'Target user not online'}
            
            if self.online_users[target_user_id]['room_id']:
                return {'success': False, 'error': 'Target user already in a room'}
            
            # 獲取房間資訊
            room_response = self.db_request({
                'collection': 'Room',
                'action': 'read',
                'data': {'id': room_id}
            })
            
            if not room_response.get('success'):
                return {'success': False, 'error': 'Room not found'}
            
            room = room_response['data']
            
            # 加入邀請列表
            if target_user_id not in self.invitations:
                self.invitations[target_user_id] = []
            
            self.invitations[target_user_id].append({
                'from_user_id': user_id,
                'from_user_name': self.online_users[user_id]['name'],
                'room_id': room_id,
                'room_name': room['name']
            })
        
        return {'success': True}
    
    def list_invitations(self, user_id):
        """列出邀請"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        with self.lock:
            invites = self.invitations.get(user_id, [])
        
        return {'success': True, 'invitations': invites}
    
    def accept_invitation(self, user_id, data):
        """接受邀請"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        room_id = data.get('roomId')
        
        with self.lock:
            # 移除邀請
            self.invitations[user_id] = [
                inv for inv in self.invitations.get(user_id, [])
                if inv['room_id'] != room_id
            ]
        
        # 加入房間
        return self.join_room(user_id, {'roomId': room_id})
    
    def start_game(self, user_id):
        """啟動遊戲"""
        if not user_id:
            return {'success': False, 'error': 'Not logged in'}
        
        with self.lock:
            room_id = self.online_users[user_id]['room_id']
            
            if not room_id:
                return {'success': False, 'error': 'Not in a room'}
            
            members = self.room_members.get(room_id, [])
            
            if len(members) != 2:
                return {'success': False, 'error': 'Need exactly 2 players'}
            
            # 檢查房間資訊
            room_response = self.db_request({
                'collection': 'Room',
                'action': 'read',
                'data': {'id': room_id}
            })
            
            if not room_response.get('success'):
                return {'success': False, 'error': 'Room not found'}
            
            room = room_response['data']
            
            # 只有房主可以開始遊戲
            if room['hostUserId'] != user_id:
                return {'success': False, 'error': 'Only host can start game'}
            
            # 分配 port
            game_port = self.next_game_port
            self.next_game_port += 1
            if self.next_game_port > GAME_SERVER_PORT_END:
                self.next_game_port = GAME_SERVER_PORT_START
            
            # 啟動遊戲伺服器（在背景執行）
            try:
                process = subprocess.Popen(
                    ['python3', 'game_server.py', str(game_port), str(room_id)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                self.game_servers[room_id] = {
                    'port': game_port,
                    'process': process
                }
                
                # 更新房間狀態
                self.db_request({
                    'collection': 'Room',
                    'action': 'update',
                    'data': {
                        'id': room_id,
                        'updates': {'status': 'playing'}
                    }
                })
                
                # 獲取玩家資訊
                player_names = [self.online_users[uid]['name'] for uid in members]
                
                return {
                    'success': True,
                    'gamePort': game_port,
                    'players': members,
                    'playerNames': player_names
                }
                
            except Exception as e:
                return {'success': False, 'error': f'Failed to start game server: {e}'}
    
    def handle_game_ended(self, data):
        """處理遊戲結束"""
        room_id = data.get('roomId')
        results = data.get('results')
        
        if not room_id:
            return {'success': False, 'error': 'Room ID required'}
        
        # 更新房間狀態
        self.db_request({
            'collection': 'Room',
            'action': 'update',
            'data': {
                'id': room_id,
                'updates': {'status': 'idle'}
            }
        })
        
        # 記錄遊戲日誌
        with self.lock:
            members = self.room_members.get(room_id, [])
        
        self.db_request({
            'collection': 'GameLog',
            'action': 'create',
            'data': {
                'matchId': f"{room_id}_{int(time.time())}",
                'roomId': room_id,
                'users': members,
                'startAt': data.get('startAt', datetime.now().isoformat()),
                'endAt': datetime.now().isoformat(),
                'results': results
            }
        })
        
        # 清理遊戲伺服器
        with self.lock:
            if room_id in self.game_servers:
                try:
                    self.game_servers[room_id]['process'].terminate()
                except:
                    pass
                del self.game_servers[room_id]
        
        return {'success': True}
    
    def cleanup_game_servers(self):
        """清理所有遊戲伺服器"""
        with self.lock:
            for room_id, game_info in self.game_servers.items():
                try:
                    game_info['process'].terminate()
                except:
                    pass
    
    def db_request(self, request):
        """向資料庫伺服器發送請求"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((DB_HOST, DB_PORT))
            
            send_message(sock, request)
            response = recv_message(sock)
            
            sock.close()
            return response
        except Exception as e:
            return {'success': False, 'error': f'DB request failed: {e}'}


if __name__ == '__main__':
    server = LobbyServer()
    server.start()
