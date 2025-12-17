import socket
import json
import threading
import sys

class NumberGuessingClient:

    def __init__(self):
        self.socket = None
        self.player_name = None
        self.player_order = None 
        self.game_state = {}
        self.running = False
        self.my_turn = False
        self.buffer = ""  
    
    def connect(self, host: str = "localhost", port: int = 9000, player_name: str = "Unknown"):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.running = True

            import json
            hello_msg = json.dumps({"player_name": player_name}) + "\n"
            
            bytes_sent = self.socket.send(hello_msg.encode('utf-8'))
            
            import time
            time.sleep(0.1)
            
            print(f" 已連接到數字猜謎遊戲服務器 {host}:{port}")
            return True
            
        except Exception as e:
            print(f" 連接失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self):
        if not self.running:
            print(" 尚未連接到服務器")
            return
        
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        print(" 歡迎來到數字猜謎遊戲！")
        print("遊戲規則: 猜測1-100之間的數字，越少次數猜中得分越高")
        print("等待其他玩家加入...")
        
        try:
            while self.running:
                if self.my_turn:
                    self.handle_player_input()
                else:
                    import time
                    time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("\n 遊戲被中斷")
        finally:
            self.disconnect()
    
    def receive_messages(self):
        try:
            while self.running:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                received = data.decode('utf-8')
                self.buffer += received
                
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self.handle_server_message(message)
                        except json.JSONDecodeError as e:
                            print(f" 接收到無效的消息格式: {line[:50]}...")
                
        except Exception as e:
            if self.running:
                print(f" 接收消息時出錯: {e}")
        finally:
            self.running = False
    
    def handle_server_message(self, message: dict):

        msg_type = message.get("type")
        
        if msg_type == "welcome":
            self.player_name = message.get("player_name")
            self.player_order = message.get("player_order")
            print(f"\n{message.get('message')}")
            print(f"等待其他玩家加入...")
            
        elif msg_type == "game_start":
            print(f"\n {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "turn_change":
            self.game_state["current_player"] = message.get("current_player")
            print(f"\n {message.get('message')}")
            self.check_my_turn()
            
        elif msg_type == "correct_guess":
            print(f"\n {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            self.my_turn = False
            
        elif msg_type == "wrong_guess":
            print(f"\n {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "new_round":
            print(f"\n {message.get('message')}")
            self.game_state = message.get("game_state", {})
            self.display_game_status()
            
        elif msg_type == "game_end":
            print(f"\n {message.get('message')}")
            self.running = False
            import time
            time.sleep(3)
            
        elif msg_type == "error":
            print(f"\n {message.get('message')}")
            
        else:
            print(f"\n {message.get('message', str(message))}")
    
    def check_my_turn(self):
        current_player = self.game_state.get("current_player", -1)
        self.my_turn = (current_player == self.player_order)
        
        if self.my_turn:
            min_range = self.game_state.get("min_range", 1)
            max_range = self.game_state.get("max_range", 100)
    
    def display_game_status(self):
        """顯示遊戲狀態"""
        print("\n" + "="*40)
        print(" 遊戲狀態")
        print("="*40)
        
        min_range = self.game_state.get("min_range", 1)
        max_range = self.game_state.get("max_range", 100)
        print(f" 當前範圍: {min_range} ~ {max_range}")
        
        round_num = self.game_state.get("round", 1)
        max_rounds = self.game_state.get("max_rounds", 1)
        print(f"第 {round_num}/{max_rounds} 輪")
        
        players = self.game_state.get("players", [])
        print("玩家得分:")
        for player in players:
            print(f"   {player['name']}: {player['score']}分 (本輪猜測{player['guesses']}次)")
        
        attempts = self.game_state.get("recent_attempts", [])
        if attempts:
            print(" 最近猜測記錄:")
            for attempt in attempts[-3:]: 
                if attempt.get("round") == round_num:  
                    print(f"   {attempt['player']}: {attempt['guess']}")
        
        print("="*40)
    
    def handle_player_input(self):

        while self.my_turn and self.running:
            try:
                min_range = self.game_state.get("min_range", 1)
                max_range = self.game_state.get("max_range", 100)
                guess_input = input(f"\n 請猜測一個 {min_range}-{max_range} 之間的數字: ").strip()
                
                if guess_input.lower() in ['quit', 'exit', 'q']:
                    self.running = False
                    break
                
                try:
                    guess = int(guess_input)
                    if min_range <= guess <= max_range:
                        message = {
                            "type": "guess",
                            "data": {"number": guess}
                        }
                        
                        self.send_message(message)
                        self.my_turn = False  
                        break
                    else:
                        print(f" 請輸入 {min_range}-{max_range} 之間的數字")
                except ValueError:
                    print(" 請輸入有效的數字")
            
            except KeyboardInterrupt:
                self.running = False
                break
    
    def send_message(self, message: dict):
        try:
            if self.socket:
                data = json.dumps(message, ensure_ascii=False)
                self.socket.send(data.encode('utf-8'))
        except Exception as e:
            print(f" 發送消息失敗: {e}")
    
    def disconnect(self):
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        print("已斷開連接")

if __name__ == "__main__":
    client = NumberGuessingClient()
    
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        player_name = sys.argv[3] if len(sys.argv) > 3 else "Player"
    else:
        host = "localhost"
        port = 9000
        player_name = "Player"
    
    if client.connect(host, port, player_name):
        client.start()
    else:
        print(" 無法連接到遊戲服務器")