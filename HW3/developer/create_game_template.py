#!/usr/bin/env python3
"""
遊戲模板創建工具
為開發者提供標準遊戲項目模板
"""
import os
import json
from datetime import datetime

class GameTemplateCreator:
    """遊戲模板創建器"""
    
    def __init__(self):
        self.templates = {
            'cli': '雙人CLI遊戲模板',
            'gui': '雙人GUI遊戲模板',
            'multiplayer': '多人遊戲模板'
        }
    
    def create_game_template(self, game_name: str, game_type: str, target_dir: str = None):
        """創建遊戲模板"""
        if game_type not in self.templates:
            print(f"❌ 不支持的遊戲類型: {game_type}")
            return False
        
        if target_dir is None:
            target_dir = os.path.join("./games", game_name.lower().replace(" ", "_"))
        
        # 創建遊戲目錄
        os.makedirs(target_dir, exist_ok=True)
        
        # 創建配置文件
        self.create_config_file(game_name, game_type, target_dir)
        
        # 根據類型創建相應模板
        if game_type == 'cli':
            self.create_cli_template(game_name, target_dir)
        elif game_type == 'gui':
            self.create_gui_template(game_name, target_dir)
        elif game_type == 'multiplayer':
            self.create_multiplayer_template(game_name, target_dir)
        
        print(f"✅ 遊戲模板已創建: {target_dir}")
        return True
    
    def create_config_file(self, game_name: str, game_type: str, target_dir: str):
        """創建遊戲配置文件"""
        config = {
            "name": game_name,
            "version": "1.0.0",
            "type": game_type,
            "max_players": 2 if game_type != 'multiplayer' else 4,
            "description": f"基於{self.templates[game_type]}創建的遊戲",
            "author": "",
            "created_at": datetime.now().isoformat(),
            "entry_point": {
                "server": f"{game_name.lower().replace(' ', '_')}_server.py",
                "client": f"{game_name.lower().replace(' ', '_')}_client.py"
            },
            "requirements": ["socket", "threading", "json"] + (["tkinter"] if game_type == 'gui' else [])
        }
        
        config_path = os.path.join(target_dir, "game_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def create_cli_template(self, game_name: str, target_dir: str):
        """創建CLI遊戲模板"""
        game_module = game_name.lower().replace(" ", "_")
        
        # 創建服務器端代碼
        server_code = f'''#!/usr/bin/env python3
"""
{game_name} - 遊戲服務器端
雙人CLI遊戲模板
"""
import socket
import threading
import json
import sys
from typing import Dict, List

class {game_name.replace(" ", "")}Server:
    """遊戲服務器"""
    
    def __init__(self, host: str = "localhost", port: int = 0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.players = {{}}  # {{socket: player_info}}
        self.game_state = {{
            "current_player": 0,
            "player_count": 0,
            "max_players": 2,
            "status": "waiting",  # waiting, playing, finished
            "board": None,  # 遊戲狀態
            "winner": None
        }}
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
            
            print(f"🎮 {game_name} 服務器啟動於 {{self.host}}:{{self.port}}")
            
            # 初始化遊戲
            self.init_game()
            
            while self.running and self.game_state["player_count"] < self.game_state["max_players"]:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"玩家連接: {{address}}")
                    
                    # 為每個玩家創建處理線程
                    player_thread = threading.Thread(
                        target=self.handle_player,
                        args=(client_socket,),
                        daemon=True
                    )
                    player_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"接受連接時出錯: {{e}}")
            
            # 等待遊戲結束
            while self.running and self.game_state["status"] == "playing":
                import time
                time.sleep(0.1)
                
        except Exception as e:
            print(f"啟動服務器失敗: {{e}}")
        finally:
            self.cleanup()
    
    def init_game(self):
        """初始化遊戲狀態"""
        # 在這裡初始化具體的遊戲邏輯
        # 例如：棋盤、卡牌等
        self.game_state["board"] = "初始遊戲狀態"
        print("🎯 遊戲已初始化")
    
    def handle_player(self, client_socket: socket.socket):
        """處理玩家連接"""
        player_id = self.game_state["player_count"]
        self.game_state["player_count"] += 1
        
        player_info = {{
            "id": player_id,
            "socket": client_socket,
            "name": f"Player{{player_id + 1}}"
        }}
        
        self.players[client_socket] = player_info
        
        try:
            # 發送歡迎消息
            self.send_message(client_socket, {{
                "type": "welcome",
                "player_id": player_id,
                "message": f"歡迎加入 {{game_name}}！您是玩家 {{player_id + 1}}"
            }})
            
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
                    print(f"處理玩家消息時出錯: {{e}}")
                    break
        
        except Exception as e:
            print(f"處理玩家時出錯: {{e}}")
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
        self.broadcast_message({{
            "type": "game_start",
            "message": "遊戲開始！",
            "game_state": self.get_public_game_state()
        }})
        
        print("🚀 遊戲開始！")
    
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
            self.send_message(client_socket, {{
                "type": "error",
                "message": "還沒輪到您的回合"
            }})
            return
        
        # 處理具體動作
        if action_type == "move":
            # 在這裡實現具體的遊戲邏輯
            move_data = message.get("data")
            if self.is_valid_move(move_data):
                self.apply_move(move_data)
                
                # 檢查遊戲是否結束
                winner = self.check_winner()
                if winner is not None:
                    self.end_game(f"玩家 {{winner + 1}} 獲勝！")
                else:
                    # 切換到下一個玩家
                    self.next_turn()
            else:
                self.send_message(client_socket, {{
                    "type": "error",
                    "message": "無效的移動"
                }})
    
    def is_valid_move(self, move_data) -> bool:
        """檢查移動是否有效"""
        # 在這裡實現具體的移動驗證邏輯
        return True
    
    def apply_move(self, move_data):
        """應用移動"""
        # 在這裡實現具體的移動邏輯
        print(f"應用移動: {{move_data}}")
        
        # 廣播遊戲狀態更新
        self.broadcast_message({{
            "type": "game_update",
            "game_state": self.get_public_game_state()
        }})
    
    def check_winner(self):
        """檢查獲勝者"""
        # 在這裡實現獲勝檢查邏輯
        return None
    
    def next_turn(self):
        """切換到下一個玩家"""
        self.game_state["current_player"] = (self.game_state["current_player"] + 1) % self.game_state["max_players"]
        
        self.broadcast_message({{
            "type": "turn_change",
            "current_player": self.game_state["current_player"],
            "message": f"輪到玩家 {{self.game_state['current_player'] + 1}}"
        }})
    
    def end_game(self, message: str):
        """結束遊戲"""
        self.game_state["status"] = "finished"
        
        self.broadcast_message({{
            "type": "game_end",
            "message": message,
            "final_state": self.get_public_game_state()
        }})
        
        print(f"🏁 遊戲結束: {{message}}")
        
        # 延遲關閉服務器
        threading.Timer(3.0, self.stop).start()
    
    def get_public_game_state(self) -> Dict:
        """獲取公開的遊戲狀態"""
        return {{
            "current_player": self.game_state["current_player"],
            "board": self.game_state["board"],
            "status": self.game_state["status"],
            "player_count": self.game_state["player_count"]
        }}
    
    def send_message(self, client_socket: socket.socket, message: Dict):
        """發送消息給特定玩家"""
        try:
            data = json.dumps(message, ensure_ascii=False)
            client_socket.send(data.encode('utf-8'))
        except Exception as e:
            print(f"發送消息失敗: {{e}}")
    
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
        server = {game_name.replace(" ", "")}Server()
        server.start(port)
    else:
        print("使用方法: python {game_module}_server.py <port>")
'''
        
        # 創建客戶端代碼
        client_code = f'''#!/usr/bin/env python3
"""
{game_name} - 遊戲客戶端
雙人CLI遊戲模板
"""
import socket
import json
import threading
import sys

class {game_name.replace(" ", "")}Client:
    """遊戲客戶端"""
    
    def __init__(self):
        self.socket = None
        self.player_id = None
        self.game_state = {{}}
        self.running = False
        self.my_turn = False
    
    def connect(self, host: str = "localhost", port: int = 9000):
        """連接到遊戲服務器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.running = True
            
            print(f"✅ 已連接到 {game_name} 服務器 {{host}}:{{port}}")
            return True
            
        except Exception as e:
            print(f"❌ 連接失敗: {{e}}")
            return False
    
    def start(self):
        """開始遊戲客戶端"""
        if not self.running:
            print("❌ 尚未連接到服務器")
            return
        
        # 啟動消息接收線程
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        print("🎮 歡迎來到 {game_name}！")
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
            print("\\n🔄 遊戲被中斷")
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
                print(f"❌ 接收消息時出錯: {{e}}")
        finally:
            self.running = False
    
    def handle_server_message(self, message: dict):
        """處理服務器消息"""
        msg_type = message.get("type")
        
        if msg_type == "welcome":
            self.player_id = message.get("player_id")
            print(f"\\n{{message.get('message')}}")
            
        elif msg_type == "game_start":
            print(f"\\n🚀 {{message.get('message')}}")
            self.game_state = message.get("game_state", {{}})
            self.display_game_state()
            self.check_my_turn()
            
        elif msg_type == "game_update":
            self.game_state = message.get("game_state", {{}})
            print("\\n📋 遊戲狀態已更新")
            self.display_game_state()
            
        elif msg_type == "turn_change":
            self.game_state["current_player"] = message.get("current_player")
            print(f"\\n🎯 {{message.get('message')}}")
            self.check_my_turn()
            
        elif msg_type == "game_end":
            print(f"\\n🏁 {{message.get('message')}}")
            print("遊戲結束，3秒後自動退出...")
            self.running = False
            
        elif msg_type == "error":
            print(f"\\n❌ {{message.get('message')}}")
            
        else:
            print(f"\\n📨 未知消息: {{message}}")
    
    def check_my_turn(self):
        """檢查是否輪到自己"""
        current_player = self.game_state.get("current_player")
        self.my_turn = (current_player == self.player_id)
        
        if self.my_turn:
            print("\\n⭐ 輪到您了！請輸入您的操作:")
    
    def display_game_state(self):
        """顯示遊戲狀態"""
        print("\\n" + "="*30)
        print("📋 當前遊戲狀態")
        print("="*30)
        
        # 顯示當前玩家
        current_player = self.game_state.get("current_player", 0)
        print(f"🎯 當前玩家: Player{{current_player + 1}}")
        
        # 顯示遊戲板狀態
        board = self.game_state.get("board")
        print(f"🎲 遊戲狀態: {{board}}")
        
        # 在這裡添加具體的遊戲狀態顯示邏輯
        
        print("="*30)
    
    def handle_player_input(self):
        """處理玩家輸入"""
        print("\\n可用操作:")
        print("1. 執行移動")
        print("2. 查看狀態")
        print("0. 退出遊戲")
        
        try:
            choice = input("請選擇操作 (0-2): ").strip()
            
            if choice == "1":
                self.make_move()
            elif choice == "2":
                self.display_game_state()
            elif choice == "0":
                self.running = False
            else:
                print("❌ 無效選擇，請重新輸入")
        
        except KeyboardInterrupt:
            self.running = False
    
    def make_move(self):
        """執行移動"""
        # 在這裡實現具體的移動邏輯
        print("請輸入您的移動 (例如: 座標、操作等):")
        
        try:
            move_input = input("> ").strip()
            
            # 這裡簡化處理，實際應根據遊戲類型設計具體的輸入格式
            move_data = {{"input": move_input}}
            
            # 發送移動到服務器
            message = {{
                "type": "move",
                "data": move_data
            }}
            
            self.send_message(message)
            self.my_turn = False  # 發送移動後不再是自己的回合
            
        except KeyboardInterrupt:
            self.running = False
    
    def send_message(self, message: dict):
        """發送消息到服務器"""
        try:
            if self.socket:
                data = json.dumps(message, ensure_ascii=False)
                self.socket.send(data.encode('utf-8'))
        except Exception as e:
            print(f"❌ 發送消息失敗: {{e}}")
    
    def disconnect(self):
        """斷開連接"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        print("📡 已斷開連接")

if __name__ == "__main__":
    client = {game_name.replace(" ", "")}Client()
    
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
'''
        
        # 寫入文件
        server_path = os.path.join(target_dir, f"{game_module}_server.py")
        client_path = os.path.join(target_dir, f"{game_module}_client.py")
        
        with open(server_path, 'w', encoding='utf-8') as f:
            f.write(server_code)
        
        with open(client_path, 'w', encoding='utf-8') as f:
            f.write(client_code)
        
        # 設置可執行權限
        os.chmod(server_path, 0o755)
        os.chmod(client_path, 0o755)
    
    def create_gui_template(self, game_name: str, target_dir: str):
        """創建GUI遊戲模板"""
        # GUI版本將在CLI版本基礎上添加tkinter界面
        # 這裡先創建基礎CLI版本
        self.create_cli_template(game_name, target_dir)
        
        # 添加GUI相關代碼(簡化版本)
        gui_code = f'''#!/usr/bin/env python3
"""
{game_name} - GUI客戶端
基於tkinter的圖形界面
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import sys
import os

# 導入CLI客戶端作為基礎
from {game_name.lower().replace(" ", "_")}_client import {game_name.replace(" ", "")}Client

class {game_name.replace(" ", "")}GUI:
    """GUI遊戲界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{game_name} - GUI版本")
        self.root.geometry("800x600")
        
        self.client = {game_name.replace(" ", "")}Client()
        self.setup_ui()
        
    def setup_ui(self):
        """設置用戶界面"""
        # 頂部信息欄
        self.info_frame = tk.Frame(self.root)
        self.info_frame.pack(pady=10)
        
        self.status_label = tk.Label(self.info_frame, text="狀態: 未連接", font=("Arial", 12))
        self.status_label.pack()
        
        # 遊戲區域
        self.game_frame = tk.Frame(self.root, relief=tk.SUNKEN, borderwidth=2)
        self.game_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)
        
        # 在這裡添加具體的遊戲界面元素
        self.game_canvas = tk.Canvas(self.game_frame, bg="white", width=400, height=400)
        self.game_canvas.pack(expand=True, fill=tk.BOTH)
        
        # 控制按鈕區域
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(pady=10)
        
        self.connect_btn = tk.Button(self.control_frame, text="連接遊戲", 
                                   command=self.connect_to_server)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_btn = tk.Button(self.control_frame, text="斷開連接", 
                                      command=self.disconnect_from_server, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        # 消息顯示區域
        self.message_frame = tk.Frame(self.root)
        self.message_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(self.message_frame, text="遊戲訊息:").pack(anchor=tk.W)
        
        self.message_text = tk.Text(self.message_frame, height=6, state=tk.DISABLED)
        self.message_text.pack(fill=tk.X)
        
        scrollbar = tk.Scrollbar(self.message_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.message_text.yview)
    
    def connect_to_server(self):
        """連接到服務器"""
        host = simpledialog.askstring("連接", "請輸入服務器地址:", initialvalue="localhost")
        if not host:
            return
            
        port = simpledialog.askinteger("連接", "請輸入端口號:", initialvalue=9000)
        if not port:
            return
        
        # 在後台線程中連接
        def connect_thread():
            if self.client.connect(host, port):
                self.root.after(0, self.on_connected)
                self.client.start()
            else:
                self.root.after(0, lambda: self.add_message("❌ 連接失敗"))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connected(self):
        """連接成功後的處理"""
        self.status_label.config(text="狀態: 已連接")
        self.connect_btn.config(state=tk.DISABLED)
        self.disconnect_btn.config(state=tk.NORMAL)
        self.add_message("✅ 已連接到遊戲服務器")
        
        # 重寫客戶端的消息處理方法
        original_handle = self.client.handle_server_message
        
        def gui_handle_message(message):
            self.root.after(0, lambda: self.handle_game_message(message))
            original_handle(message)
        
        self.client.handle_server_message = gui_handle_message
    
    def disconnect_from_server(self):
        """斷開連接"""
        self.client.disconnect()
        self.status_label.config(text="狀態: 未連接")
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.add_message("📡 已斷開連接")
    
    def handle_game_message(self, message):
        """處理遊戲消息(GUI版本)"""
        msg_type = message.get("type")
        msg_content = message.get("message", "")
        
        if msg_type == "welcome":
            self.add_message(f"🎮 {{msg_content}}")
        elif msg_type == "game_start":
            self.add_message(f"🚀 {{msg_content}}")
            self.update_game_display(message.get("game_state", {{}}))
        elif msg_type == "game_update":
            self.update_game_display(message.get("game_state", {{}}))
        elif msg_type == "turn_change":
            self.add_message(f"🎯 {{msg_content}}")
        elif msg_type == "game_end":
            self.add_message(f"🏁 {{msg_content}}")
            messagebox.showinfo("遊戲結束", msg_content)
        elif msg_type == "error":
            self.add_message(f"❌ {{msg_content}}")
            messagebox.showerror("錯誤", msg_content)
    
    def update_game_display(self, game_state):
        """更新遊戲顯示"""
        # 清空畫布
        self.game_canvas.delete("all")
        
        # 在這裡實現具體的遊戲狀態顯示
        # 例如繪製棋盤、卡片等
        
        # 示例：顯示當前玩家
        current_player = game_state.get("current_player", 0)
        self.game_canvas.create_text(200, 50, text=f"當前玩家: Player{{current_player + 1}}", 
                                   font=("Arial", 16))
        
        # 示例：顯示遊戲狀態
        board_state = str(game_state.get("board", ""))
        self.game_canvas.create_text(200, 200, text=f"遊戲狀態:\\n{{board_state}}", 
                                   font=("Arial", 12))
    
    def add_message(self, message):
        """添加消息到消息區域"""
        self.message_text.config(state=tk.NORMAL)
        self.message_text.insert(tk.END, message + "\\n")
        self.message_text.see(tk.END)
        self.message_text.config(state=tk.DISABLED)
    
    def run(self):
        """運行GUI"""
        try:
            self.root.mainloop()
        finally:
            if self.client.running:
                self.client.disconnect()

if __name__ == "__main__":
    app = {game_name.replace(" ", "")}GUI()
    app.run()
'''
        
        gui_path = os.path.join(target_dir, f"{game_name.lower().replace(' ', '_')}_gui.py")
        with open(gui_path, 'w', encoding='utf-8') as f:
            f.write(gui_code)
        
        os.chmod(gui_path, 0o755)
    
    def create_multiplayer_template(self, game_name: str, target_dir: str):
        """創建多人遊戲模板"""
        # 多人版本基於CLI版本，但支持更多玩家
        self.create_cli_template(game_name, target_dir)
        
        # 修改配置支持更多玩家
        config_path = os.path.join(target_dir, "game_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config["max_players"] = 4
        config["description"] = f"支持多人遊玩的{game_name}"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def show_template_menu(self):
        """顯示模板選擇菜單"""
        print("\\n" + "="*50)
        print("🎮 遊戲模板創建工具")
        print("="*50)
        print("\\n📋 可用模板:")
        
        for i, (template_type, description) in enumerate(self.templates.items(), 1):
            print(f"{i}. {template_type.upper()} - {description}")
        
        print("0. 退出")
        print("-"*50)
        
        while True:
            try:
                choice = input("請選擇模板類型: ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return None
                elif 1 <= choice_num <= len(self.templates):
                    template_types = list(self.templates.keys())
                    return template_types[choice_num - 1]
                else:
                    print(f"❌ 請輸入 0 到 {len(self.templates)} 之間的數字")
            except ValueError:
                print("❌ 請輸入有效的數字")

def main():
    """主函數"""
    creator = GameTemplateCreator()
    
    print("🚀 歡迎使用遊戲模板創建工具！")
    
    while True:
        template_type = creator.show_template_menu()
        
        if template_type is None:
            print("👋 再見！")
            break
        
        game_name = input("\\n請輸入遊戲名稱: ").strip()
        if not game_name:
            print("❌ 遊戲名稱不能為空")
            continue
        
        target_dir = input(f"請輸入目標目錄 (按Enter使用默認: ./games/{game_name.lower().replace(' ', '_')}): ").strip()
        
        if creator.create_game_template(game_name, template_type, target_dir or None):
            print(f"\\n✅ 模板創建成功！")
            print(f"📁 位置: {target_dir or os.path.join('./games', game_name.lower().replace(' ', '_'))}")
            print("\\n📖 下一步:")
            print("1. 進入遊戲目錄")
            print("2. 編輯遊戲邏輯代碼")
            print("3. 測試遊戲功能")
            print("4. 使用開發者客戶端上傳遊戲")
            
            create_more = input("\\n是否繼續創建其他模板? (y/N): ").strip().lower()
            if create_more != 'y':
                break
        else:
            print("❌ 模板創建失敗")

if __name__ == "__main__":
    main()