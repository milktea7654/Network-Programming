"""
Game Server - 遊戲伺服器
處理雙人俄羅斯方塊遊戲邏輯和同步
"""
import socket
import threading
import time
import sys
from datetime import datetime
from protocol import send_message, recv_message, ProtocolError
from tetris_logic import TetrisGame
import random

LOBBY_HOST = 'localhost'
LOBBY_PORT = 10002


class GameServer:
    def __init__(self, port, room_id):
        self.port = port
        self.room_id = room_id
        self.running = False
        
        # 玩家連接：{user_id: {'socket': socket, 'role': 'P1'|'P2', 'game': TetrisGame}}
        self.players = {}
        
        # 遊戲設定
        self.seed = random.randint(0, 2**31 - 1)
        self.drop_interval = 500  # 毫秒
        self.game_start_time = None
        
        # 鎖
        self.lock = threading.Lock()
        
        # 遊戲狀態
        self.game_started = False
        self.game_ended = False
    
    def start(self):
        """啟動遊戲伺服器"""
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.port))
        server_socket.listen(5)
        
        print(f"[Game Server] Room {self.room_id} listening on port {self.port}")
        
        # 啟動遊戲循環線程
        game_thread = threading.Thread(target=self.game_loop)
        game_thread.daemon = True
        game_thread.start()
        
        try:
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    print(f"[Game] New connection from {addr}")
                    
                    # 為每個連接創建新線程
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[Game] Accept error: {e}")
        except KeyboardInterrupt:
            print("\n[Game Server] Shutting down...")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, addr):
        """處理客戶端連接"""
        user_id = None
        
        try:
            # 等待 HELLO 訊息
            hello = recv_message(client_socket)
            
            if hello.get('type') != 'HELLO':
                send_message(client_socket, {'type': 'ERROR', 'message': 'Expected HELLO'})
                return
            
            user_id = hello.get('userId')
            room_id = hello.get('roomId')
            
            if room_id != self.room_id:
                send_message(client_socket, {'type': 'ERROR', 'message': 'Invalid room'})
                return
            
            # 分配角色
            with self.lock:
                if len(self.players) >= 2:
                    send_message(client_socket, {'type': 'ERROR', 'message': 'Game full'})
                    return
                
                role = 'P1' if len(self.players) == 0 else 'P2'
                
                # 創建玩家遊戲實例
                game = TetrisGame(seed=self.seed)
                
                self.players[user_id] = {
                    'socket': client_socket,
                    'role': role,
                    'game': game,
                    'ready': False
                }
                
                print(f"[Game] Player {user_id} joined as {role}")
            
            # 發送 WELCOME 訊息
            send_message(client_socket, {
                'type': 'WELCOME',
                'role': role,
                'seed': self.seed,
                'bagRule': '7bag',
                'gravityPlan': {
                    'mode': 'fixed',
                    'dropMs': self.drop_interval
                }
            })
            
            # 標記為就緒
            with self.lock:
                self.players[user_id]['ready'] = True
                
                # 如果兩個玩家都就緒，開始遊戲
                if len(self.players) == 2 and all(p['ready'] for p in self.players.values()):
                    self.game_started = True
                    self.game_start_time = datetime.now()
                    print("[Game] Game started!")
            
            # 處理玩家輸入
            while self.running:
                msg = recv_message(client_socket)
                self.handle_player_message(user_id, msg)
                
        except (ConnectionError, ProtocolError) as e:
            print(f"[Game] Connection error from {addr}: {e}")
        except Exception as e:
            print(f"[Game] Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理玩家
            if user_id and user_id in self.players:
                with self.lock:
                    del self.players[user_id]
                print(f"[Game] Player {user_id} disconnected")
            
            client_socket.close()
    
    def handle_player_message(self, user_id, msg):
        """處理玩家訊息"""
        msg_type = msg.get('type')
        
        if msg_type == 'INPUT':
            # 處理玩家輸入
            action = msg.get('action')
            
            with self.lock:
                if user_id not in self.players:
                    return
                
                game = self.players[user_id]['game']
                
                if game.game_over:
                    return
                
                # 執行動作
                if action == 'LEFT':
                    game.move_left()
                elif action == 'RIGHT':
                    game.move_right()
                elif action == 'CW':
                    game.rotate_cw()
                elif action == 'CCW':
                    game.rotate_ccw()
                elif action == 'SOFT_DROP':
                    game.soft_drop()
                elif action == 'HARD_DROP':
                    game.hard_drop()
                elif action == 'HOLD':
                    game.hold()
                
                # 廣播狀態更新
                self.broadcast_snapshot(user_id)
                
                # 檢查遊戲是否結束
                self.check_game_end()
    
    def game_loop(self):
        """遊戲主循環（重力）"""
        last_drop_time = time.time()
        
        while self.running:
            time.sleep(0.05)  # 50ms
            
            if not self.game_started or self.game_ended:
                continue
            
            current_time = time.time()
            
            # 重力下降
            if current_time - last_drop_time >= self.drop_interval / 1000.0:
                last_drop_time = current_time
                
                with self.lock:
                    for user_id, player in self.players.items():
                        game = player['game']
                        if not game.game_over:
                            game.soft_drop()
                            self.broadcast_snapshot(user_id)
                    
                    # 檢查遊戲是否結束
                    self.check_game_end()
    
    def broadcast_snapshot(self, user_id):
        """廣播玩家狀態快照（需要在鎖內調用）"""
        if user_id not in self.players:
            return
        
        player = self.players[user_id]
        game = player['game']
        state = game.get_state()
        
        snapshot = {
            'type': 'SNAPSHOT',
            'userId': user_id,
            'role': player['role'],
            'boardRLE': game.compress_board(),
            'active': state['current'],
            'hold': state['hold'],
            'next': state['next'],
            'score': state['score'],
            'lines': state['lines'],
            'level': state['level'],
            'gameOver': state['gameOver'],
            'timestamp': time.time()
        }
        
        # 發送給所有玩家
        for pid, p in self.players.items():
            try:
                send_message(p['socket'], snapshot)
            except:
                pass
    
    def check_game_end(self):
        """檢查遊戲是否結束（需要在鎖內調用）"""
        if self.game_ended:
            return
        
        if len(self.players) < 2:
            return
        
        # 檢查是否有玩家遊戲結束
        game_over_count = sum(1 for p in self.players.values() if p['game'].game_over)
        
        if game_over_count > 0:
            # 遊戲結束
            self.game_ended = True
            
            # 收集結果
            results = []
            winner_id = None
            max_score = -1
            
            for user_id, player in self.players.items():
                game = player['game']
                result = {
                    'userId': user_id,
                    'score': game.score,
                    'lines': game.lines_cleared,
                    'maxCombo': 0,  # 暫不實作 combo
                    'gameOver': game.game_over
                }
                results.append(result)
                
                if game.score > max_score:
                    max_score = game.score
                    winner_id = user_id
            
            # 廣播遊戲結束
            end_msg = {
                'type': 'GAME_END',
                'results': results,
                'winner': winner_id
            }
            
            for player in self.players.values():
                try:
                    send_message(player['socket'], end_msg)
                except:
                    pass
            
            # 通知 Lobby Server
            self.notify_lobby_game_end(results)
            
            print(f"[Game] Game ended. Winner: {winner_id}")
            
            # 5 秒後關閉伺服器
            threading.Timer(5.0, self.shutdown).start()
    
    def notify_lobby_game_end(self, results):
        """通知 Lobby Server 遊戲結束"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LOBBY_HOST, LOBBY_PORT))
            
            request = {
                'action': 'game_ended',
                'data': {
                    'roomId': self.room_id,
                    'startAt': self.game_start_time.isoformat() if self.game_start_time else datetime.now().isoformat(),
                    'results': results
                }
            }
            
            send_message(sock, request)
            recv_message(sock)  # 接收回應
            
            sock.close()
        except Exception as e:
            print(f"[Game] Failed to notify lobby: {e}")
    
    def shutdown(self):
        """關閉伺服器"""
        self.running = False
        print("[Game Server] Shutting down...")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 game_server.py <port> <room_id>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    room_id = int(sys.argv[2])
    
    server = GameServer(port, room_id)
    server.start()
