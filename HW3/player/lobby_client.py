import socket
import os
import sys
import time
import zipfile
import tempfile
import subprocess
import argparse
from typing import Dict, Any, Optional, List

SERVER_HOST = "linux2.cs.nycu.edu.tw" 
SERVER_PORT = 8002

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from protocol import NetworkProtocol, GameProtocol

class LobbyClient:
    
    def __init__(self, server_host: str = SERVER_HOST, server_port: int = SERVER_PORT):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.is_logged_in = False
        self.downloads_dir = f"./downloads/{socket.gethostname()}"  
        os.makedirs(self.downloads_dir, exist_ok=True)
        
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(30.0)
            print(f"已連接到大廳服務器 {self.server_host}:{self.server_port}")
            
            time.sleep(0.1)
            return True
        except socket.timeout:
            print(f" 連接超時: 無法連接到 {self.server_host}:{self.server_port}")
            print("請確認:")
            print("   1. 服務器是否在運行")
            print("   2. 網絡連接是否正常")
            print("   3. 防火牆設置是否阻擋連接")
            return False
        except ConnectionRefusedError:
            print(f" 連接被拒絕: 服務器未在 {self.server_host}:{self.server_port} 監聽")
            print("請啟動服務器後再試")
            return False
        except Exception as e:
            print(f" 連接失敗: {e}")
            return False
    
    def disconnect(self):

        if self.socket:
            if self.is_logged_in:
                self.logout()
            self.socket.close()
            self.socket = None
            print("已斷開連接")
    
    def send_request(self, msg_type: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if not self.socket:
            print("未連接到服務器")
            return None
        
        try:
            self.socket.settimeout(0.1)
            try:
                while True:
                    leftover = self.socket.recv(1024, socket.MSG_DONTWAIT)
                    if not leftover:
                        break
                    print(f"清除殘留數據: {len(leftover)} bytes")
            except BlockingIOError:
                pass
            except Exception:
                pass
            finally:
                self.socket.settimeout(30.0) 
            
            message = NetworkProtocol.create_message(msg_type, data)
            
            if not NetworkProtocol.send_message(self.socket, message):
                print(f"發送 {msg_type} 消息失敗")
                return None
            
            response = NetworkProtocol.receive_message(self.socket)
            return response
                
        except socket.error as e:
            print(f"Socket 錯誤: {e}")
            print("提示: 請確認服務器是否在運行")
            return None
        except Exception as e:
            print(f"請求處理失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def register(self, username: str, password: str) -> bool:

        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_REGISTER, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f" {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "註冊失敗"
            print(f" {error_msg}")
            return False
    
    def login(self, username: str, password: str) -> bool:
        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_LOGIN, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = username
            self.is_logged_in = True
            print(f" {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登入失敗"
            print(f" {error_msg}")
            return False
    
    def logout(self) -> bool:
        if not self.is_logged_in:
            print("您尚未登入")
            return False
        
        response = self.send_request(NetworkProtocol.MSG_LOGOUT)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = None
            self.is_logged_in = False
            print(f" {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登出失敗"
            print(f" {error_msg}")
            return False
    
    def list_games(self) -> Optional[List[Dict]]:
        response = self.send_request(NetworkProtocol.MSG_LIST_GAMES)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            games = response.get('data', {}).get('games', [])
            return games
        else:
            error_msg = response.get('message') if response else "獲取遊戲列表失敗"
            print(f" {error_msg}")
            return None
    
    def get_game_info(self, game_name: str) -> Optional[Dict]:

        data = {'name': game_name}
        response = self.send_request(NetworkProtocol.MSG_GET_GAME_INFO, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            return response.get('data', {}).get('game')
        else:
            error_msg = response.get('message') if response else "獲取遊戲信息失敗"
            print(f" {error_msg}")
            return None
    
    def download_game(self, game_name: str, version: str = None) -> bool:

        if not self.is_logged_in:
            print(" 請先登入")
            return False
        

        local_version = self.get_local_game_version(game_name)
        if local_version and not version:
            print(f"本地已有遊戲 {game_name} v{local_version}")
            update = input("是否檢查更新？ (Y/N): ").strip().lower()
            if update != 'y':
                return True
        
        data = {'name': game_name}
        if version:
            data['version'] = version
        
        response = self.send_request(NetworkProtocol.MSG_DOWNLOAD_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"{response.get('message')}")
            
            game_info = response.get('data', {})
            downloaded_version = game_info.get('version', '1.0.0')
            
            if local_version == downloaded_version:
                print(f" 本地已是最新版本 v{downloaded_version}")
                return True
            
            game_dir = os.path.join(self.downloads_dir, game_name)
            version_dir = os.path.join(game_dir, downloaded_version)
            os.makedirs(version_dir, exist_ok=True)
            
            temp_zip = os.path.join(version_dir, f"{game_name}.zip")
            
            try:
                if GameProtocol.receive_file(self.socket, temp_zip):
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        zip_ref.extractall(version_dir)
                    
                    os.remove(temp_zip)
                    
                    self.save_game_version(game_name, downloaded_version)
                    
                    print(f"遊戲 {game_name} v{downloaded_version} 下載完成")
                    return True
                else:
                    print("接收遊戲文件失敗")
                    return False
                    
            except Exception as e:
                print(f"下載處理失敗: {e}")
                return False
        else:
            error_msg = response.get('message') if response else "下載請求失敗"
            print(f" {error_msg}")
            return False
    
    def get_local_game_version(self, game_name: str) -> Optional[str]:
        version_file = os.path.join(self.downloads_dir, game_name, "version.txt")
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        return None
    
    def save_game_version(self, game_name: str, version: str):
        game_dir = os.path.join(self.downloads_dir, game_name)
        os.makedirs(game_dir, exist_ok=True)
        
        version_file = os.path.join(game_dir, "version.txt")
        with open(version_file, 'w') as f:
            f.write(version)
    
    def list_rooms(self) -> Optional[List[Dict]]:
        response = self.send_request(NetworkProtocol.MSG_LIST_ROOMS)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            rooms = response.get('data', {}).get('rooms', [])
            return rooms
        else:
            error_msg = response.get('message') if response else "獲取房間列表失敗"
            print(f" {error_msg}")
            return None
    
    def create_room(self, game_name: str, game_version: str = None) -> Optional[str]:
        if not self.is_logged_in:
            print(" 請先登入")
            return None
        
        data = {
            'game_name': game_name,
            'game_version': game_version or ''
        }
        
        response = self.send_request(NetworkProtocol.MSG_CREATE_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            room_info = response.get('data', {})
            room_id = room_info.get('room_id')
            print(f"房間創建成功")
            print(f"房間ID: {room_id}")
            print(f"遊戲: {room_info.get('game_name')} v{room_info.get('game_version')}")
            return room_id
        else:
            error_msg = response.get('message') if response else "創建房間失敗"
            print(f" {error_msg}")
            return None
    
    def join_room(self, room_id: str) -> bool:
        if not self.is_logged_in:
            print("請先登入")
            return False
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_JOIN_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            room_info = response.get('data', {})
            print(f"成功加入房間 {room_id}")
            print(f"當前玩家: {', '.join(room_info.get('players', []))}")
            return True
        else:
            error_msg = response.get('message') if response else "加入房間失敗"
            print(f" {error_msg}")
            return False
    
    def leave_room(self, room_id: str) -> bool:
        if not self.is_logged_in:
            print("請先登入")
            return False
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_LEAVE_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f" {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "離開房間失敗"
            print(f" {error_msg}")
            return False
    
    def start_game(self, room_id: str) -> Optional[Dict]:
        if not self.is_logged_in:
            print("請先登入")
            return None
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_START_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            game_info = response.get('data', {})
            print(f" {response.get('message')}")
            print(f"遊戲服務器: {game_info.get('game_server_host')}:{game_info.get('game_server_port')}")
            return game_info
        else:
            error_msg = response.get('message') if response else "開始遊戲失敗"
            print(f" {error_msg}")
            return None
    
    def launch_game_client(self, game_name: str, game_version: str, server_host: str, server_port: int) -> bool:
        version_dir = os.path.join(self.downloads_dir, game_name, game_version)
        if not os.path.exists(version_dir):
            print(f"本地沒有遊戲 {game_name} v{game_version}")
            print("請先下載遊戲")
            return False

        client_script_name = None
        for filename in os.listdir(version_dir):
            if filename.endswith('_client.py'):
                client_script_name = filename
                break
        
        if not client_script_name:
            print(f"找不到遊戲客戶端文件")
            return False

        client_script_path = os.path.abspath(os.path.join(version_dir, client_script_name))
        
        if not os.path.exists(client_script_path):
            print(f"遊戲客戶端文件不存在: {client_script_path}")
            return False
        
        try:
            print(f"\n{'='*60}")
            print(f"正在啟動遊戲客戶端...")
            print(f"{'='*60}")
            print(f"執行: {client_script_path}")
            print(f"連接到: {server_host}:{server_port}")
            print(f"玩家: {self.username}")
            print(f"{'='*60}\n")

            cmd = [sys.executable, client_script_path, server_host, str(server_port), self.username]

            result = subprocess.run(cmd, cwd=os.path.abspath(version_dir))
            
            print(f"\n{'='*60}")
            print(f"遊戲已結束 (退出碼: {result.returncode})")
            print(f"{'='*60}")
            
            return True
            
        except Exception as e:
            print(f"啟動遊戲客戶端失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_review(self, game_name: str, rating: float, comment: str) -> bool:
        if not self.is_logged_in:
            print("請先登入")
            return False
        
        data = {
            'game_name': game_name,
            'rating': rating,
            'comment': comment
        }
        
        response = self.send_request(NetworkProtocol.MSG_ADD_REVIEW, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f" {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "添加評論失敗"
            print(f" {error_msg}")
            return False
    
    def get_reviews(self, game_name: str) -> Optional[Dict]:
        data = {'game_name': game_name}
        response = self.send_request(NetworkProtocol.MSG_GET_REVIEWS, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            return response.get('data', {})
        else:
            error_msg = response.get('message') if response else "獲取評論失敗"
            print(f" {error_msg}")
            return None
    
    def get_player_records(self) -> Optional[List[Dict]]:
        if not self.is_logged_in:
            print(" 請先登入")
            return None
        
        print(f"[DEBUG] 請求玩家遊戲記錄...")
        response = self.send_request(NetworkProtocol.MSG_GET_PLAYER_RECORDS)
        print(f"[DEBUG] 收到記錄回應: {response}")
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            records = response.get('data', {}).get('records', [])
            print(f"[DEBUG] 解析到 {len(records)} 條記錄")
            return records
        else:
            error_msg = response.get('message') if response else "獲取遊戲記錄失敗"
            print(f" {error_msg}")
            return None

class LobbyUI:
    
    def __init__(self, server_host: str = SERVER_HOST, server_port: int = SERVER_PORT):
        self.client = LobbyClient(server_host=server_host, server_port=server_port)
        self.running = True
        self.current_room_id = None
        self.username = None 
    
    def show_main_menu(self):
        print("\n" + "="*50)
        print("遊戲大廳平台")
        print("="*50)
        
        if self.client.is_logged_in:
            print(f"當前用戶: {self.client.username}")
        else:
            print("尚未登入")
        
        print("\n 請選擇操作:")
        
        if not self.client.is_logged_in:
            print("1. 註冊新帳號")
            print("2. 登入帳號")
        else:
            print("1. 遊戲商城")
            print("2. 大廳管理")
            print("3. 我的記錄")
            print("4. 登出")
        
        print("0. 退出程式")
        print("-"*50)
    
    def show_store_menu(self):
        """顯示商城選單"""
        print("\n" + "="*30)
        print("遊戲商城")
        print("="*30)
        print("1. 瀏覽遊戲")
        print("2. 搜尋遊戲")
        print("3. 下載遊戲")
        print("4. 檢視評論")
        print("5. 撰寫評論")
        print("0. 返回主選單")
        print("-"*30)
    
    def show_lobby_menu(self):
        """顯示大廳選單"""
        print("\n" + "="*30)
        print("大廳管理")
        print("="*30)
        print("1. 瀏覽房間")
        print("2. 創建房間")
        print("3. 加入房間")
        if self.current_room_id:
            print(f"4. 進入我的房間 ({self.current_room_id})")
        print("0. 返回主選單")
        print("-"*30)
    
    def get_user_choice(self, max_choice: int) -> int:
        while True:
            try:
                choice = input("請輸入選項編號: ").strip()
                choice_num = int(choice)
                if 0 <= choice_num <= max_choice:
                    return choice_num
                else:
                    print(f"請輸入 0 到 {max_choice} 之間的數字")
            except ValueError:
                print("請輸入有效的數字")
    
    def run(self):
        print("玩家大廳客戶端啟動中...")
        
        if not self.client.connect():
            print("無法連接到服務器，程序退出")
            return
        
        try:
            while self.running:
                self.show_main_menu()
                
                if not self.client.is_logged_in:
                    max_choice = 2
                else:
                    max_choice = 4
                
                choice = self.get_user_choice(max_choice)
                
                if choice == 0:
                    self.running = False
                elif not self.client.is_logged_in:
                    if choice == 1:
                        self.handle_register()
                    elif choice == 2:
                        self.handle_login()
                else:
                    if choice == 1:
                        self.handle_store()
                    elif choice == 2:
                        self.handle_lobby()
                    elif choice == 3:
                        self.handle_records()
                    elif choice == 4:
                        self.client.logout()
        
        finally:
            self.client.disconnect()
            print("玩家大廳客戶端已關閉")
    
    def handle_register(self):

        print("\n註冊新帳號")
        print("-"*30)
        
        username = input("用戶名: ").strip()
        password = input("密碼: ").strip()
        
        if username and password:
            self.client.register(username, password)
        else:
            print("用戶名和密碼不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_login(self):

        print("\n登入賬號")
        print("-"*30)
        
        username = input("用戶名: ").strip()
        password = input("密碼: ").strip()
        
        if username and password:
            if self.client.login(username, password):
                self.username = username  
        else:
            print("用戶名和密碼不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_store(self):

        while True:
            self.show_store_menu()
            choice = self.get_user_choice(5)
            
            if choice == 0:
                break
            elif choice == 1:
                self.show_games_list()
            elif choice == 2:
                self.search_games()
            elif choice == 3:
                self.download_game()
            elif choice == 4:
                self.view_reviews()
            elif choice == 5:
                self.write_review()
    
    def handle_lobby(self):

        while True:
            self.show_lobby_menu()
            max_choice = 4 if self.current_room_id else 3
            choice = self.get_user_choice(max_choice)
            
            if choice == 0:
                break
            elif choice == 1:
                self.show_rooms_list()
            elif choice == 2:
                self.create_room()
            elif choice == 3:
                self.join_room()
            elif choice == 4 and self.current_room_id:
                self.manage_current_room()
    
    def manage_current_room(self):
        import time
        
        while self.current_room_id:
            rooms = self.client.list_rooms()
            current_room = None
            for room in rooms:
                if room['room_id'] == self.current_room_id:
                    current_room = room
                    break
            
            if not current_room:
                print("房間已不存在")
                self.current_room_id = None
                input("按Enter鍵繼續...")
                return
            
            if current_room['status'] == 'playing' and current_room['host'] != self.username:
                print("\n" + "="*50)
                print(" 遊戲已開始！房主已啟動遊戲服務器")
                print("="*50)
                print("正在為您啟動遊戲客戶端...")
                
                if not current_room.get('game_server_port'):
                    print("等待遊戲服務器信息同步...")
                    time.sleep(2)
                    
                    rooms = self.client.list_rooms()
                    for room in rooms:
                        if room['room_id'] == self.current_room_id:
                            current_room = room
                            break
                
                self.join_started_game(current_room)
                
                print("\n遊戲已結束，等待房間狀態更新...")
                time.sleep(2)
                continue
            
            print("\n" + "="*50)
            print(f" 房間管理 - {self.current_room_id}")
            print("="*50)
            print(f" 遊戲: {current_room['game_name']} v{current_room['game_version']}")
            print(f" 房主: {current_room['host']}")
            print(f" 玩家: {', '.join(current_room['players'])} ({len(current_room['players'])}/{current_room['max_players']})")
            print(f" 狀態: {current_room['status']}")
            print("="*50)
            
            print("\n 房間操作")
            print("1.  刷新房間資訊")
            print("2.  開始遊戲 (僅房主)")
            print("3.  離開房間")
            print("0.  返回大廳")
            
            if current_room['host'] != self.username:
                import select
                import sys
                
                print("\n請選擇操作 (0-3): ", end='', flush=True)
                
                ready, _, _ = select.select([sys.stdin], [], [], 3.0)
                
                if ready:
                    choice_input = sys.stdin.readline().strip()
                else:
                    print("")
                    time.sleep(0.5)
                    continue
            else:
                choice_input = input("\n請選擇操作 (0-3): ").strip()
            
            try:
                choice = int(choice_input)
            except ValueError:
                print(" 請輸入有效的數字")
                time.sleep(1)
                continue
            
            if choice == 0:
                return
            elif choice == 1:
                continue
            elif choice == 2:
                if current_room['host'] == self.username:
                    self.start_game_in_room()
                else:
                    print(" 只有房主才能開始遊戲")
                    input("按Enter鍵繼續...")
            elif choice == 3:
                if self.leave_current_room():
                    return
            else:
                print(" 無效的選擇")
                input("按Enter鍵繼續...")
    
    def handle_records(self):

        print("\n 我的遊戲記錄")
        print("-"*30)
        
        records = self.client.get_player_records()
        if not records:
            print("您還沒有遊戲記錄")
        else:
            for i, record in enumerate(records, 1):
                review_status = " 已評論" if record['has_reviewed'] else " 未評論"
                print(f"{i}. {record['game_name']} v{record['game_version']}")
                print(f"    遊玩時間: {record['played_at']}")
                print(f"    評論狀態: {review_status}")
                print()
        
        input("按Enter鍵繼續...")
    
    def show_games_list(self):
        """顯示遊戲列表"""
        print("\n 遊戲列表 (從服務器即時更新)")
        print("-"*50)
        
        games = self.client.list_games()
        print(f" 獲取到 {len(games) if games else 0} 個遊戲")
        if not games:
            print("目前沒有可用的遊戲")
        else:
            for i, game in enumerate(games, 1):
                rating_display = f"{game['rating']:.1f}/5.0 ({game['rating_count']}人)" if game['rating_count'] > 0 else "暫無評分"
                print(f"{i}. {game['name']}")
                print(f"    開發者: {game['developer']}")
                print(f"    簡介: {game['description'] or '無簡介'}")
                print(f"    類型: {game['type']} | 最大玩家: {game['max_players']}")
                print(f"    版本: v{game['current_version']} |  評分: {rating_display}")
                print()
        
        input("按Enter鍵繼續...")
    
    def search_games(self):
        """搜尋遊戲"""
        print("\n 搜尋遊戲")
        print("-"*30)
        
        keyword = input("請輸入遊戲名稱關鍵字: ").strip().lower()
        if not keyword:
            print(" 關鍵字不能為空")
            input("按Enter鍵繼續...")
            return
        
        games = self.client.list_games()
        if not games:
            print("目前沒有可用的遊戲")
        else:
            matches = [game for game in games if keyword in game['name'].lower()]
            
            if not matches:
                print(f" 沒有找到包含 '{keyword}' 的遊戲")
            else:
                print(f"\n找到 {len(matches)} 個結果:")
                for i, game in enumerate(matches, 1):
                    rating_display = f"{game['rating']:.1f}/5.0" if game['rating_count'] > 0 else "暫無評分"
                    print(f"{i}. {game['name']} - {game['developer']} (v{game['current_version']}) {rating_display}")
        
        input("按Enter鍵繼續...")
    
    def download_game(self):
        """下載遊戲"""
        print("\n 下載遊戲")
        print("-"*30)
        
        games = self.client.list_games()
        if not games:
            print("目前沒有可用的遊戲")
            input("按Enter鍵繼續...")
            return
        
        print("可下載的遊戲:")
        for i, game in enumerate(games, 1):
            print(f"{i}. {game['name']} v{game['current_version']} - {game['developer']}")
        
        try:
            game_idx = int(input("\n選擇要下載的遊戲編號: ").strip()) - 1
            if 0 <= game_idx < len(games):
                game = games[game_idx]
                self.client.download_game(game['name'])
            else:
                print(" 無效的遊戲編號")
        except ValueError:
            print(" 請輸入有效的數字")
        
        input("\n按Enter鍵繼續...")
    
    def view_reviews(self):
        """查看評論"""
        print("\n 查看遊戲評論")
        print("-"*30)
        
        game_name = input("請輸入遊戲名稱: ").strip()
        if not game_name:
            print(" 遊戲名稱不能為空")
            input("按Enter鍵繼續...")
            return
        
        reviews_data = self.client.get_reviews(game_name)
        if reviews_data:
            reviews = reviews_data.get('reviews', [])
            average_rating = reviews_data.get('average_rating', 0)
            rating_count = reviews_data.get('rating_count', 0)
            
            print(f"\n {game_name} 的評論")
            print(f" 平均評分: {average_rating:.1f}/5.0 ({rating_count}人評分)")
            print("-"*40)
            
            if not reviews:
                print("暫無評論")
            else:
                for i, review in enumerate(reviews[-10:], 1):  
                    print(f"{i}.  玩家 {review['player']} |  {review['rating']}/5")
                    print(f"    {review['comment']}")
                    print(f"    遊玩時間: {review['created_at']}")
                    print()
        
        input("按Enter鍵繼續...")
    
    def write_review(self):
        """撰寫評論"""
        print("\n 撰寫遊戲評論")
        print("-"*50)
        
        records = self.client.get_player_records()
        if not records:
            print(" 您還沒有遊戲記錄")
            print(" 提示：您需要先玩過遊戲才能評論")
            input("\n按Enter鍵繼續...")
            return
        
        print(" 您玩過的遊戲：")
        print("-"*50)
        
        reviewable_games = []
        for i, record in enumerate(records, 1):
            review_status = " 已評論" if record.get('has_reviewed', False) else " 未評論"
            print(f"{i}. {record['game_name']} v{record['game_version']}")
            print(f"    遊玩時間: {record.get('played_at', 'Unknown')}")
            print(f"    評論狀態: {review_status}")
            print()
            reviewable_games.append(record)
        
        print("0. 返回")
        print("-"*50)
        
        try:
            choice = int(input("\n請選擇要評論的遊戲 (輸入編號): ").strip())
            if choice == 0:
                return
            if choice < 1 or choice > len(reviewable_games):
                print(" 無效的選擇")
                input("\n按Enter鍵繼續...")
                return
        except ValueError:
            print(" 請輸入有效的數字")
            input("\n按Enter鍵繼續...")
            return
        
        selected_game = reviewable_games[choice - 1]
        game_name = selected_game['game_name']
        
        if selected_game.get('has_reviewed', False):
            confirm = input(f"\n  您已對《{game_name}》發表過評論，要覆蓋舊評論嗎？ (Y/N): ").strip().lower()
            if confirm != 'y':
                print(" 取消評論")
                input("\n按Enter鍵繼續...")
                return
        
        print(f"\n 為《{game_name}》撰寫評論")
        print("-"*50)
        
        try:
            rating = float(input(" 評分 (1-5): ").strip())
            if not 1 <= rating <= 5:
                print(" 評分必須在1-5之間")
                input("\n按Enter鍵繼續...")
                return
        except ValueError:
            print(" 請輸入有效的評分")
            input("\n按Enter鍵繼續...")
            return
        
        comment = input(" 評論內容 (可選，直接Enter跳過): ").strip()
        
        if self.client.add_review(game_name, rating, comment):
            print(f"\n 評論提交成功！")
            print(f"   遊戲: {game_name}")
            print(f"   評分: {rating}/5.0")
            if comment:
                print(f"   評論: {comment}")
        else:
            print("\n 評論提交失敗")
        
        input("\n按Enter鍵繼續...")
    
    def show_rooms_list(self):
        """顯示房間列表"""
        print("\n 房間列表")
        print("-"*50)
        
        rooms = self.client.list_rooms()
        if not rooms:
            print("目前沒有活躍的房間")
        else:
            for i, room in enumerate(rooms, 1):
                status_emoji = "" if room['status'] == 'waiting' else ""
                print(f"{i}. {status_emoji} 房間 {room['room_id']}")
                print(f"    遊戲: {room['game_name']} v{room['game_version']}")
                print(f"    房主: {room['host']}")
                print(f"    玩家: {room['current_players']}/{room['max_players']}")
                print(f"    創建時間: {room['created_at']}")
                print()
        
        input("按Enter鍵繼續...")
    
    def create_room(self):
        print("\n 創建房間")
        print("-"*30)
        
        games = self.client.list_games()
        if not games:
            print(" 目前沒有可用的遊戲")
            input("按Enter鍵繼續...")
            return
        
        print("可選遊戲:")
        for i, game in enumerate(games, 1):
            local_version = self.client.get_local_game_version(game['name'])
            if local_version:
                version_info = f"v{game['current_version']} (本地: v{local_version})"
            else:
                version_info = f"v{game['current_version']} (未下載)"
            print(f"{i}. {game['name']} {version_info} ({game['type']})")
        
        try:
            game_idx = int(input("\n選擇遊戲編號: ").strip()) - 1
            if 0 <= game_idx < len(games):
                game = games[game_idx]
                
                local_version = self.client.get_local_game_version(game['name'])
                
                if not local_version:
                    print(f"\n  您還沒有下載遊戲 '{game['name']}'")
                    download = input("是否現在下載? (Y/N): ").strip().upper()
                    if download == 'Y':
                        if not self.client.download_game(game['name'], game['current_version']):
                            print(" 遊戲下載失敗，無法創建房間")
                            input("按Enter鍵繼續...")
                            return
                    else:
                        print(" 需要下載遊戲才能創建房間")
                        input("按Enter鍵繼續...")
                        return
                elif local_version != game['current_version']:
                    print(f"\n  您的本地版本 (v{local_version}) 與最新版本 (v{game['current_version']}) 不符")
                    update = input("是否更新到最新版本? (Y/N): ").strip().upper()
                    if update == 'Y':
                        if not self.client.download_game(game['name'], game['current_version']):
                            print(" 遊戲更新失敗")
                            use_old = input("是否使用舊版本創建房間? (Y/N): ").strip().upper()
                            if use_old != 'Y':
                                input("按Enter鍵繼續...")
                                return
                
                print("\n 正在創建房間...")
                room_id = self.client.create_room(game['name'], game['current_version'])
                
                if room_id:
                    self.current_room_id = room_id
                    print(f"\n 房間創建成功！")
                    print(f" 房間ID: {room_id}")
                    print(f" 遊戲: {game['name']} v{game['current_version']}")
                    print(f" 房主: {self.username}")
                    print("\n 您現在在房間裡，可以等待其他玩家加入或開始遊戲")
                    input("\n按Enter鍵進入房間管理...")
                    self.manage_current_room()
                else:
                    print(" 建立房間失敗，請稍後再試")
                    input("按Enter鍵繼續...")
            else:
                print(" 無效的遊戲編號")
                input("\n按Enter鍵繼續...")
        except ValueError:
            print(" 請輸入有效的數字")
            input("\n按Enter鍵繼續...")
        except Exception as e:
            print(f" 發生錯誤: {e}")
            input("\n按Enter鍵繼續...")
    
    def join_room(self):
        """加入房間"""
        print("\n 加入房間")
        print("-"*30)
        
        room_id = input("請輸入房間ID: ").strip()
        if not room_id:
            print(" 房間ID不能為空")
            input("\n按Enter鍵繼續...")
        else:
            if self.client.join_room(room_id):
                self.current_room_id = room_id
                print(f"\n 成功加入房間！")
                print(f" 房間ID: {room_id}")
                input("\n按Enter鍵進入房間管理...")
                self.manage_current_room()
            else:
                input("\n按Enter鍵繼續...")
    
    def start_game_in_room(self):
        print(f"\n 開始遊戲 (房間: {self.current_room_id})")
        print("-"*30)
        
        try:
            game_info = self.client.start_game(self.current_room_id)
            if not game_info:
                print(" 無法啟動遊戲，請稍後再試")
                input("按Enter鍵繼續...")
                return
            
            rooms = self.client.list_rooms()
            current_room = None
            for room in rooms:
                if room['room_id'] == self.current_room_id:
                    current_room = room
                    break
            
            if not current_room:
                print(" 房間信息獲取失敗")
                self.current_room_id = None
                input("按Enter鍵繼續...")
                return
            
            game_name = current_room['game_name']
            game_version = current_room['game_version']
            
            local_version = self.client.get_local_game_version(game_name)
            if local_version != game_version:
                print(f" 需要下載/更新遊戲到版本 {game_version}")
                if self.client.download_game(game_name, game_version):
                    print(" 遊戲已更新到最新版本")
                else:
                    print(" 遊戲下載失敗，無法啟動")
                    print(" 提示：您的狀態已返回房間，可以稍後再試")
                    input("按Enter鍵繼續...")
                    return
            
            server_host = self.client.server_host
            server_port = game_info.get('game_server_port')
            
            if not server_port:
                print(" 遊戲服務器端口信息不完整")
                print(" 提示：請聯繫管理員或稍後再試")
                input("按Enter鍵繼續...")
                return
            
            print(f"\n 正在連接遊戲服務器...")
            print(f"   服務器: {server_host}:{server_port}")
            
            import time
            max_retries = 5
            connected = False
            
            for attempt in range(max_retries):
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.settimeout(1.0)
                    test_socket.connect((server_host, server_port))
                    test_socket.close()
                    connected = True
                    print(" 遊戲服務器已準備就緒")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"   嘗試 {attempt + 1}/{max_retries}... 等待中")
                        time.sleep(1)
                    else:
                        print(f"\n 無法連接到遊戲服務器: {e}")
                        print(" 遊戲服務器可能尚未啟動或發生錯誤")
                        print("\n您的狀態已返回房間，請稍後再試")
            
            if not connected:
                input("\n按Enter鍵繼續...")
                return
            
            if self.client.launch_game_client(game_name, game_version, server_host, server_port):
                pass
            else:
                print("\n 啟動遊戲客戶端失敗")
                print(" 可能的原因:")
                print("   - 遊戲文件損壞，請重新下載")
                print("   - 遊戲服務器連接失敗")
                print("   - 系統資源不足")
                print("\n您的狀態已返回房間，可以稍後再試")
        
        except Exception as e:
            print(f"\n 啟動遊戲時發生錯誤: {e}")
            print(" 您的狀態已返回房間")
        
        input("\n按Enter鍵繼續...")
    
    def start_game(self):
        self.start_game_in_room()
    
    def join_started_game(self, room_info):
        try:
            game_name = room_info['game_name']
            game_version = room_info['game_version']
            
            local_version = self.client.get_local_game_version(game_name)
            if local_version != game_version:
                print(f" 需要下載/更新遊戲到版本 {game_version}")
                if self.client.download_game(game_name, game_version):
                    print(" 遊戲已更新到最新版本")
                else:
                    print(" 遊戲下載失敗，無法加入遊戲")
                    input("按Enter鍵繼續...")
                    return
            
            server_host = self.client.server_host
            server_port = room_info.get('game_server_port')
            
            print(f"[DEBUG] 房間信息: port={server_port}, status={room_info.get('status')}")
            print(f"[DEBUG] 使用 lobby server 地址: {server_host}")
            
            if not server_port:
                print(" 遊戲服務器端口信息不完整")
                print(" 提示：遊戲服務器可能尚未完全啟動")
                print(" 請按「刷新」重新檢測或稍等片刻")
                input("按Enter鍵繼續...")
                return
            
            print(f"\n 正在連接遊戲服務器...")
            print(f"   服務器: {server_host}:{server_port}")
            
            import time
            max_retries = 5
            connected = False
            
            for attempt in range(max_retries):
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.settimeout(1.0)
                    test_socket.connect((server_host, server_port))
                    test_socket.close()
                    connected = True
                    print(" 遊戲服務器已準備就緒")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"   嘗試 {attempt + 1}/{max_retries}... 等待中")
                        time.sleep(1)
                    else:
                        print(f"\n 無法連接到遊戲服務器: {e}")
                        print(" 遊戲服務器可能已關閉")
            
            if not connected:
                input("\n按Enter鍵繼續...")
                return
            
            if self.client.launch_game_client(game_name, game_version, server_host, server_port):
                pass
            else:
                print("\n 啟動遊戲客戶端失敗")
                print(" 可能的原因:")
                print("   - 遊戲文件損壞，請重新下載")
                print("   - 系統資源不足")
        
        except Exception as e:
            print(f"\n 加入遊戲時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按Enter鍵繼續...")
    
    def leave_current_room(self):
        """離開當前房間"""
        if self.current_room_id:
            if self.client.leave_room(self.current_room_id):
                print(f" 已離開房間 {self.current_room_id}")
                self.current_room_id = None
                input("按Enter鍵繼續...")
                return True
            else:
                input("按Enter鍵繼續...")
                return False
        else:
            print(" 您不在任何房間中")
            input("\n按Enter鍵繼續...")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='玩家大廳客戶端')
    parser.add_argument('--host', default=SERVER_HOST, help=f'服務器地址 (預設: {SERVER_HOST})')
    parser.add_argument('--port', type=int, default=SERVER_PORT, help=f'服務器端口 (預設: {SERVER_PORT})')
    args = parser.parse_args()
    
    ui = LobbyUI(server_host=args.host, server_port=args.port)
    try:
        ui.run()
    except KeyboardInterrupt:
        print("\n\n 程序被中斷，正在退出...")
    except Exception as e:
        print(f"\n 程序出現錯誤: {e}")