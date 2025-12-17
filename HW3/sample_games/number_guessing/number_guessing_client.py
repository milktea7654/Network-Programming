#!/usr/bin/env python3
"""
數字猜謎遊戲 - 遊戲客戶端
雙人競賽猜測隨機數字
"""
import socket
import json
import threading
import sys

class NumberGuessingClient:
    """數字猜謎遊戲客戶端"""
    
    def __init__(self):
        self.socket = None
        self.player_id = None
        self.game_state = {}
        self.running = False
        self.my_turn = False
    
    def connect(self, host: str = "localhost", port: int = 9000):
        """連接到遊戲服務器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.running = True
            
            print(f"✅ 已連接到數字猜謎遊戲服務器 {host}:{port}")
            return True
            
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False
    
    def start(self):
        """開始遊戲客戶端"""
        if not self.running:
            print("❌ 尚未連接到服務器")
            return
        
        # 啟動消息接收線程
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        print("🎮 歡迎來到數字猜謎遊戲！")
        print("遊戲規則: 猜測1-100之間的數字，越少次數猜中得分越高")
        print("等待其他玩家加入...")
        
        try:
            # 主遊戲循環
            while self.running:
                if self.my_turn:
                    self.handle_player_input()
                else:
                    # 等待輪到自己
                    import time
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n🔄 遊戲被中斷")
        finally:
            self.disconnect()
    
    def receive_messages(self):
        """接收服務器消息"""
        try:
            while self.running:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self.handle_server_message(message)
                except json.JSONDecodeError:
                    print("❌ 接收到無效的消息格式")
                
        except Exception as e:
            if self.running:
                print(f"❌ 接收消息時出錯: {e}")
        finally:
            self.running = False
    
    def handle_server_message(self, message: dict):
        """處理服務器消息"""
        msg_type = message.get("type")
        
        if msg_type == "welcome":
            self.player_id = message.get("player_id")
            print(f"\n{message.get('message')}")
            
        elif msg_type == "game_start":
            print(f"\n🚀 {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "turn_change":
            self.game_state["current_player"] = message.get("current_player")
            print(f"\n🎯 {message.get('message')}")
            self.check_my_turn()
            
        elif msg_type == "correct_guess":
            print(f"\n🎉 {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            self.my_turn = False
            
        elif msg_type == "wrong_guess":
            print(f"\n❌ {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "new_round":
            print(f"\n🔄 {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "game_end":
            print(f"\n🏁 {message.get('message')}")
            print("遊戲結束，3秒後自動退出...")
            self.running = False
            
        elif msg_type == "error":
            print(f"\n❌ {message.get('message')}")
            
        else:
            print(f"\n📨 {message.get('message', str(message))}")
    
    def check_my_turn(self):
        """檢查是否輪到自己"""
        current_player = self.game_state.get("current_player")
        self.my_turn = (current_player == self.player_id)
        
        if self.my_turn:
            print("\n⭐ 輪到您了！請輸入您的猜測:")
    
    def display_game_status(self):
        """顯示遊戲狀態"""
        print("\n" + "="*40)
        print("📋 遊戲狀態")
        print("="*40)
        
        # 顯示輪數信息
        round_num = self.game_state.get("round", 1)
        max_rounds = self.game_state.get("max_rounds", 10)
        print(f"🔢 第 {round_num}/{max_rounds} 輪")
        
        # 顯示玩家信息
        players = self.game_state.get("players", [])
        print("👥 玩家得分:")
        for player in players:
            print(f"   {player['name']}: {player['score']}分 (本輪猜測{player['guesses']}次)")
        
        # 顯示最近的猜測記錄
        attempts = self.game_state.get("recent_attempts", [])
        if attempts:
            print("📝 最近猜測記錄:")
            for attempt in attempts[-3:]:  # 只顯示最近3次
                if attempt.get("round") == round_num:  # 只顯示當前輪的記錄
                    print(f"   {attempt['player']}: {attempt['guess']}")
        
        print("="*40)
    
    def handle_player_input(self):
        """處理玩家輸入"""
        while self.my_turn and self.running:
            try:
                print("\n🎯 請猜測一個1-100之間的數字:")
                guess_input = input("您的猜測: ").strip()
                
                if guess_input.lower() in ['quit', 'exit', 'q']:
                    self.running = False
                    break
                
                try:
                    guess = int(guess_input)
                    if 1 <= guess <= 100:
                        # 發送猜測到服務器
                        message = {
                            "type": "guess",
                            "data": {"number": guess}
                        }
                        
                        self.send_message(message)
                        self.my_turn = False  # 發送猜測後不再是自己的回合
                        print(f"📤 已提交猜測: {guess}")
                        break
                    else:
                        print("❌ 請輸入1-100之間的數字")
                except ValueError:
                    print("❌ 請輸入有效的數字")
            
            except KeyboardInterrupt:
                self.running = False
                break
    
    def send_message(self, message: dict):
        """發送消息到服務器"""
        try:
            if self.socket:
                data = json.dumps(message, ensure_ascii=False)
                self.socket.send(data.encode('utf-8'))
        except Exception as e:
            print(f"❌ 發送消息失敗: {e}")
    
    def disconnect(self):
        """斷開連接"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        print("📡 已斷開連接")

if __name__ == "__main__":
    client = NumberGuessingClient()
    
    # 從命令行參數獲取服務器信息
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    else:
        host = "localhost"
        port = 9000
    
    if client.connect(host, port):
        client.start()
    else:
        print("❌ 無法連接到遊戲服務器")