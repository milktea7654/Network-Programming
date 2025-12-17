#!/usr/bin/env python3
"""
數字猜謎遊戲 - 遊戲服務器端
雙人競賽猜測隨機數字
"""
import socket
import threading
import json
import sys
import random
from typing import Dict, List

class NumberGuessingServer:
    """數字猜謎遊戲服務器"""
    
    def __init__(self, host: str = "localhost", port: int = 0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.players = {}  # {socket: player_info}
        self.game_state = {
            "current_player": 0,
            "player_count": 0,
            "max_players": 2,
            "status": "waiting",  # waiting, playing, finished
            "target_number": 0,
            "attempts": [],  # 猜測記錄
            "winner": None,
            "round": 0,
            "max_rounds": 10
        }
        self.running = False
    
    def start(self, target_port: int = None):
        """啟動遊戲服務器"""
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
            
            print(f"🎮 數字猜謎遊戲服務器啟動於 {self.host}:{self.port}")
            
            # 初始化遊戲
            self.init_game()
            
            while self.running and self.game_state["player_count"] < self.game_state["max_players"]:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"玩家連接: {address}")
                    
                    # 為每個玩家創建處理線程
                    player_thread = threading.Thread(
                        target=self.handle_player,
                        args=(client_socket,),
                        daemon=True
                    )
                    player_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"接受連接時出錯: {e}")
            
            # 等待遊戲結束
            while self.running and self.game_state["status"] == "playing":
                import time
                time.sleep(0.1)
                
        except Exception as e:
            print(f"啟動服務器失敗: {e}")
        finally:
            self.cleanup()
    
    def init_game(self):
        """初始化遊戲狀態"""
        self.game_state["target_number"] = random.randint(1, 100)
        self.game_state["attempts"] = []
        self.game_state["round"] = 1
        print(f"🎯 目標數字已設定: {self.game_state['target_number']}")  # 調試用，實際遊戲中不顯示
    
    def handle_player(self, client_socket: socket.socket):
        """處理玩家連接"""
        player_id = self.game_state["player_count"]
        self.game_state["player_count"] += 1
        
        player_info = {
            "id": player_id,
            "socket": client_socket,
            "name": f"Player{player_id + 1}",
            "score": 0,
            "guesses": 0
        }
        
        self.players[client_socket] = player_info
        
        try:
            # 發送歡迎消息
            self.send_message(client_socket, {
                "type": "welcome",
                "player_id": player_id,
                "message": f"歡迎加入數字猜謎遊戲！您是{player_info['name']}"
            })
            
            # 如果玩家滿員，開始遊戲
            if self.game_state["player_count"] >= self.game_state["max_players"]:
                self.start_game()
            
            # 處理玩家消息
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
            print(f"處理玩家時出錯: {e}")
        finally:
            # 玩家斷線處理
            if client_socket in self.players:
                del self.players[client_socket]
                self.game_state["player_count"] -= 1
            client_socket.close()
            
            # 如果遊戲中有玩家離開，結束遊戲
            if self.game_state["status"] == "playing":
                self.end_game("玩家離線，遊戲結束")
    
    def start_game(self):
        """開始遊戲"""
        self.game_state["status"] = "playing"
        
        # 通知所有玩家遊戲開始
        self.broadcast_message({
            "type": "game_start",
            "message": f"遊戲開始！目標數字在 1-100 之間，共 {self.game_state['max_rounds']} 回合",
            "game_state": self.get_public_game_state()
        })
        
        print("🚀 遊戲開始！")
        self.prompt_current_player()
    
    def handle_player_action(self, client_socket: socket.socket, message: Dict):
        """處理玩家動作"""
        if self.game_state["status"] != "playing":
            return
        
        player_info = self.players.get(client_socket)
        if not player_info:
            return
        
        action_type = message.get("type")
        
        # 檢查是否輪到該玩家
        if player_info["id"] != self.game_state["current_player"]:
            self.send_message(client_socket, {
                "type": "error",
                "message": "還沒輪到您的回合"
            })
            return
        
        # 處理猜測動作
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
        """檢查猜測是否有效"""
        try:
            guess = int(guess_data.get("number", 0))
            return 1 <= guess <= 100
        except (ValueError, TypeError):
            return False
    
    def process_guess(self, player_info: Dict, guess_data: Dict):
        """處理猜測"""
        guess = int(guess_data.get("number"))
        player_info["guesses"] += 1
        
        # 記錄猜測
        attempt = {
            "player": player_info["name"],
            "guess": guess,
            "round": self.game_state["round"]
        }
        self.game_state["attempts"].append(attempt)
        
        # 判斷結果
        target = self.game_state["target_number"]
        
        if guess == target:
            # 猜中了！
            player_info["score"] += max(11 - player_info["guesses"], 1)  # 越少次數猜中得分越高
            
            self.broadcast_message({
                "type": "correct_guess",
                "message": f"🎉 {player_info['name']} 猜中了！數字是 {target}",
                "player": player_info["name"],
                "guess": guess,
                "score": player_info["score"],
                "game_state": self.get_public_game_state()
            })
            
            # 開始下一輪或結束遊戲
            self.next_round()
            
        else:
            # 沒猜中，給提示
            hint = "太高了" if guess > target else "太低了"
            
            self.broadcast_message({
                "type": "wrong_guess",
                "message": f"{player_info['name']} 猜測 {guess} - {hint}",
                "player": player_info["name"],
                "guess": guess,
                "hint": hint,
                "game_state": self.get_public_game_state()
            })
            
            # 切換到下一個玩家
            self.next_turn()
    
    def next_turn(self):
        """切換到下一個玩家"""
        self.game_state["current_player"] = (self.game_state["current_player"] + 1) % self.game_state["max_players"]
        self.prompt_current_player()
    
    def prompt_current_player(self):
        """提示當前玩家行動"""
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
        """下一輪遊戲"""
        self.game_state["round"] += 1
        
        if self.game_state["round"] > self.game_state["max_rounds"]:
            # 遊戲結束
            self.determine_winner()
        else:
            # 新一輪
            self.game_state["target_number"] = random.randint(1, 100)
            print(f"🎯 第{self.game_state['round']}輪目標數字: {self.game_state['target_number']}")
            
            # 重置玩家猜測次數
            for player_info in self.players.values():
                player_info["guesses"] = 0
            
            self.broadcast_message({
                "type": "new_round",
                "message": f"第 {self.game_state['round']} 輪開始！新的目標數字已設定",
                "round": self.game_state["round"],
                "game_state": self.get_public_game_state()
            })
            
            # 從第一個玩家開始
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
            winner_message = f"🏆 {scores[0][0]} 獲勝！"
        
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
        
        print(f"🏁 遊戲結束: {message}")
        
        # 延遲關閉服務器
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
            "recent_attempts": self.game_state["attempts"][-5:]  # 最近5次猜測
        }
    
    def send_message(self, client_socket: socket.socket, message: Dict):
        """發送消息給特定玩家"""
        try:
            data = json.dumps(message, ensure_ascii=False)
            client_socket.send(data.encode('utf-8'))
        except Exception as e:
            print(f"發送消息失敗: {e}")
    
    def broadcast_message(self, message: Dict):
        """廣播消息給所有玩家"""
        for client_socket in self.players:
            self.send_message(client_socket, message)
    
    def stop(self):
        """停止服務器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("🔄 遊戲服務器已停止")
    
    def cleanup(self):
        """清理資源"""
        for client_socket in list(self.players.keys()):
            client_socket.close()
        self.players.clear()
        
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        server = NumberGuessingServer()
        server.start(port)
    else:
        print("使用方法: python number_guessing_server.py <port>")