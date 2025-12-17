import socket
import threading
import json
import sys
import random
from typing import Dict, List

class NumberGuessingServer:
    
    def __init__(self, host: str = "localhost", port: int = 0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.players = {} 
        self.players_lock = threading.Lock()  
        self.game_state = {
            "current_player": 0,
            "player_count": 0,
            "max_players": 2,
            "status": "waiting",  
            "target_number": 0,
            "attempts": [],  
            "winner": None,
            "round": 0,
            "max_rounds": 1, 
            "min_range": 1, 
            "max_range": 100  
        }
        self.running = False
    
    def start(self, target_port: int = None):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if target_port:
                self.port = target_port
                self.server_socket.bind((self.host, self.port))
            else:
                self.server_socket.bind((self.host, 0))
                self.port = self.server_socket.getsockname()[1]
            
            self.server_socket.listen(2)
            self.running = True
            
            print(f" 數字猜謎遊戲服務器啟動於 {self.host}:{self.port}")
            print(f"[SERVER] 等待玩家連接... (最多 {self.game_state['max_players']} 人)")
            sys.stdout.flush() 
            
            self.init_game()
            
            while self.running and self.game_state["player_count"] < self.game_state["max_players"]:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"[SERVER] 玩家連接: {address}")
                    sys.stdout.flush()
                    
                    player_thread = threading.Thread(
                        target=self.handle_player,
                        args=(client_socket,),
                        daemon=True
                    )
                    player_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"[SERVER] 接受連接時出錯: {e}")
                        sys.stdout.flush()
            
            while self.running and self.game_state["status"] == "playing":
                import time
                time.sleep(0.1)
                
        except Exception as e:
            print(f" [SERVER] 啟動服務器失敗: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            sys.exit(1)  
        finally:
            self.cleanup()
    
    def init_game(self):
        self.game_state["target_number"] = random.randint(1, 100)
        self.game_state["attempts"] = []
        self.game_state["round"] = 1
        self.game_state["min_range"] = 1
        self.game_state["max_range"] = 100
        print(f" 目標數字已設定: {self.game_state['target_number']}")  
    
    def handle_player(self, client_socket: socket.socket):

        player_name = None
        player_id = None 
        buffer = ""  
        
        print(f"[SERVER] handle_player 線程啟動")
        sys.stdout.flush()
        
        try:
            print(f"[SERVER] 等待接收玩家名稱...")
            sys.stdout.flush()
            
            while '\n' not in buffer:
                print(f"[SERVER] 調用 recv()...")
                sys.stdout.flush()
                
                data = client_socket.recv(1024)
                
                print(f"[SERVER] recv() 返回: {len(data) if data else 0} 字節")
                sys.stdout.flush()
                
                if not data:
                    print(f"[SERVER] 連接關閉 (收到空數據)")
                    sys.stdout.flush()
                    client_socket.close()
                    return
                
                received = data.decode('utf-8')
                print(f"[SERVER] 收到數據: {repr(received)}")
                sys.stdout.flush()
                
                buffer += received
                print(f"[SERVER] 當前緩衝區: {repr(buffer)}")
                sys.stdout.flush()
            
            line, buffer = buffer.split('\n', 1)
            print(f"[SERVER] 提取行: {line}")
            sys.stdout.flush()
            
            hello_msg = json.loads(line.strip())
            player_name = hello_msg.get('player_name', 'Unknown')
            print(f"[SERVER] 收到玩家名稱: {player_name}")
            sys.stdout.flush()
            
            with self.players_lock:
                player_id = self.game_state["player_count"]
                self.game_state["player_count"] += 1
                
                player_info = {
                    "id": player_id,
                    "socket": client_socket,
                    "name": player_name,
                    "score": 0,
                    "guesses": 0
                }
                
                self.players[client_socket] = player_info
                print(f"[SERVER] {player_name} 已連接 (順序: {player_id + 1})")
                sys.stdout.flush()
                
                players_ready = self.game_state["player_count"] >= self.game_state["max_players"]
                
        except Exception as e:
            print(f"[SERVER] 接收玩家名稱失敗: {e}")
            client_socket.close()
            return
        
        try:
            self.send_message(client_socket, {
                "type": "welcome",
                "player_name": player_name,
                "player_order": player_id,
                "message": f"歡迎加入數字猜謎遊戲！您是 {player_name}"
            })
            
            if players_ready:
                print(f"[SERVER] 玩家已滿 ({self.game_state['player_count']}/{self.game_state['max_players']})，開始遊戲")
                sys.stdout.flush()
                import time
                time.sleep(0.5)
                self.start_game()
            
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    message = json.loads(data.decode('utf-8'))
                    self.handle_player_action(client_socket, message)
                    
                except json.JSONDecodeError:
                    print("接收到無效的JSON數據")
                except Exception as e:
                    print(f"處理玩家消息時出錯: {e}")
                    break
        
        except Exception as e:
            print(f"[SERVER] 處理玩家時出錯: {e}")
            import traceback
            traceback.print_exc()
        finally:
            player_name = None
            with self.players_lock:
                if client_socket in self.players:
                    player_name = self.players[client_socket]['name']
                    del self.players[client_socket]
                    self.game_state["player_count"] -= 1
            
            if player_name:
                print(f"[SERVER] {player_name} 已斷開連接")
                sys.stdout.flush()
            
            try:
                client_socket.close()
            except:
                pass
            
            if self.game_state["status"] == "playing":
                self.end_game("玩家離線，遊戲結束")
    
    def start_game(self):
        self.game_state["status"] = "playing"
        
        print(f"[SERVER]  遊戲開始！準備廣播給 {len(self.players)} 個玩家")
        sys.stdout.flush()
        
        game_start_msg = {
            "type": "game_start",
            "message": f"遊戲開始！目標數字在 1-100 之間，共 {self.game_state['max_rounds']} 回合",
            "game_state": self.get_public_game_state()
        }
        
        print(f"[SERVER] 發送 game_start 消息: {game_start_msg}")
        sys.stdout.flush()
        
        self.broadcast_message(game_start_msg)
        
        print(f"[SERVER] game_start 消息已廣播")
        sys.stdout.flush()
        
        self.prompt_current_player()
    
    def handle_player_action(self, client_socket: socket.socket, message: Dict):

        if self.game_state["status"] != "playing":
            return
        
        player_info = self.players.get(client_socket)
        if not player_info:
            return
        
        action_type = message.get("type")
        
        if player_info["id"] != self.game_state["current_player"]:
            self.send_message(client_socket, {
                "type": "error",
                "message": "還沒輪到您的回合"
            })
            return
        
        if action_type == "guess":
            guess_data = message.get("data")
            if self.is_valid_guess(guess_data):
                self.process_guess(player_info, guess_data)
            else:
                self.send_message(client_socket, {
                    "type": "error",
                    "message": "無效的猜測，請輸入1-100之間的數字"
                })
    
    def is_valid_guess(self, guess_data) -> bool:
        try:
            guess = int(guess_data.get("number", 0))
            min_r = self.game_state["min_range"]
            max_r = self.game_state["max_range"]
            return min_r <= guess <= max_r
        except (ValueError, TypeError):
            return False
    
    def process_guess(self, player_info: Dict, guess_data: Dict):

        guess = int(guess_data.get("number"))
        player_info["guesses"] += 1
        
        attempt = {
            "player": player_info["name"],
            "guess": guess,
            "round": self.game_state["round"]
        }
        self.game_state["attempts"].append(attempt)
        
        target = self.game_state["target_number"]
        
        if guess == target:
            player_info["score"] += max(11 - player_info["guesses"], 1)  
            
            self.broadcast_message({
                "type": "correct_guess",
                "message": f" {player_info['name']} 猜中了！數字是 {target}",
                "player": player_info["name"],
                "guess": guess,
                "score": player_info["score"],
                "game_state": self.get_public_game_state()
            })
            
            self.next_round()
            
        else:
            if guess > target:
                hint = "太高了"
                self.game_state["max_range"] = guess - 1  
            else:
                hint = "太低了"
                self.game_state["min_range"] = guess + 1  
            
            range_msg = f"新範圍: {self.game_state['min_range']}~{self.game_state['max_range']}"
            
            self.broadcast_message({
                "type": "wrong_guess",
                "message": f"{player_info['name']} 猜測 {guess} - {hint}\n{range_msg}",
                "player": player_info["name"],
                "guess": guess,
                "hint": hint,
                "min_range": self.game_state["min_range"],
                "max_range": self.game_state["max_range"],
                "game_state": self.get_public_game_state()
            })
            
            self.next_turn()
    
    def next_turn(self):
        self.game_state["current_player"] = (self.game_state["current_player"] + 1) % self.game_state["max_players"]
        self.prompt_current_player()
    
    def prompt_current_player(self):
        current_player = None
        for player_info in self.players.values():
            if player_info["id"] == self.game_state["current_player"]:
                current_player = player_info
                break
        
        if current_player:
            self.broadcast_message({
                "type": "turn_change",
                "current_player": self.game_state["current_player"],
                "message": f"輪到 {current_player['name']} 猜測數字"
            })
    
    def next_round(self):
        self.game_state["round"] += 1
        
        if self.game_state["round"] > self.game_state["max_rounds"]:
            self.determine_winner()
        else:
            self.game_state["target_number"] = random.randint(1, 100)
            print(f" 第{self.game_state['round']}輪目標數字: {self.game_state['target_number']}")
            
            for player_info in self.players.values():
                player_info["guesses"] = 0
            
            self.broadcast_message({
                "type": "new_round",
                "message": f"第 {self.game_state['round']} 輪開始！新的目標數字已設定",
                "round": self.game_state["round"],
                "game_state": self.get_public_game_state()
            })
            
            self.game_state["current_player"] = 0
            self.prompt_current_player()
    
    def determine_winner(self):
        """確定獲勝者"""
        scores = []
        for player_info in self.players.values():
            scores.append((player_info["name"], player_info["score"]))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if len(scores) >= 2 and scores[0][1] == scores[1][1]:
            winner_message = "遊戲平局！"
        else:
            winner_message = f" {scores[0][0]} 獲勝！"
        
        score_info = "\n".join([f"{name}: {score}分" for name, score in scores])
        
        self.end_game(f"{winner_message}\n\n最終得分:\n{score_info}")
    
    def end_game(self, message: str):
        """結束遊戲"""
        self.game_state["status"] = "finished"
        
        self.broadcast_message({
            "type": "game_end",
            "message": message,
            "final_state": self.get_public_game_state()
        })
        
        print(f" 遊戲結束: {message}")
        
        threading.Timer(3.0, self.stop).start()
    
    def get_public_game_state(self) -> Dict:
        """獲取公開的遊戲狀態"""
        players_info = []
        for player_info in self.players.values():
            players_info.append({
                "name": player_info["name"],
                "score": player_info["score"],
                "guesses": player_info["guesses"]
            })
        
        return {
            "current_player": self.game_state["current_player"],
            "round": self.game_state["round"],
            "max_rounds": self.game_state["max_rounds"],
            "status": self.game_state["status"],
            "player_count": self.game_state["player_count"],
            "players": players_info,
            "recent_attempts": self.game_state["attempts"][-5:],
            "min_range": self.game_state.get("min_range", 1),
            "max_range": self.game_state.get("max_range", 100)
        }
    
    def send_message(self, client_socket: socket.socket, message: Dict):
        try:
            data = json.dumps(message, ensure_ascii=False)
            client_socket.send(data.encode('utf-8') + b'\n')
        except (BrokenPipeError, OSError) as e:
            pass
        except Exception as e:
            print(f"[SERVER] 發送消息失敗: {e}")
    
    def broadcast_message(self, message: Dict):
        with self.players_lock:
            sockets = list(self.players.keys())
        
        print(f"[SERVER] broadcast_message: 準備發送給 {len(sockets)} 個玩家")
        sys.stdout.flush()
        
        for i, client_socket in enumerate(sockets):
            print(f"[SERVER] broadcast_message: 發送給玩家 {i+1}")
            sys.stdout.flush()
            self.send_message(client_socket, message)
            print(f"[SERVER] broadcast_message: 玩家 {i+1} 發送完成")
            sys.stdout.flush()
    
    def stop(self):
        """停止服務器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print(" 遊戲服務器已停止")
    
    def cleanup(self):
        """清理資源"""
        for client_socket in list(self.players.keys()):
            client_socket.close()
        self.players.clear()
        
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python number_guessing_server.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    server = NumberGuessingServer(host="0.0.0.0", port=port)
    server.start(port)