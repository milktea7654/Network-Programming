#!/usr/bin/env python3
"""
Player Client - Lobby Client
玩家大廳客戶端 - 用於遊戲瀏覽、下載、房間管理等操作
"""
import socket
import os
import sys
import zipfile
import tempfile
import subprocess
from typing import Dict, Any, Optional, List

# 添加服務器路徑以導入協議
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from protocol import NetworkProtocol, GameProtocol

class LobbyClient:
    """大廳客戶端"""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8002):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.is_logged_in = False
        self.downloads_dir = f"./downloads/{socket.gethostname()}"  # 為每個客戶端創建獨立下載目錄
        os.makedirs(self.downloads_dir, exist_ok=True)
        
    def connect(self) -> bool:
        """連接到服務器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✅ 已連接到大廳服務器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False
    
    def disconnect(self):
        """斷開連接"""
        if self.socket:
            if self.is_logged_in:
                self.logout()
            self.socket.close()
            self.socket = None
            print("📡 已斷開連接")
    
    def send_request(self, msg_type: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """發送請求並接收回應"""
        if not self.socket:
            print("❌ 未連接到服務器")
            return None
        
        message = NetworkProtocol.create_message(msg_type, data)
        
        if NetworkProtocol.send_message(self.socket, message):
            response = NetworkProtocol.receive_message(self.socket)
            return response
        else:
            print("❌ 發送消息失敗")
            return None
    
    def register(self, username: str, password: str) -> bool:
        """註冊新用戶"""
        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_REGISTER, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"✅ {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "註冊失敗"
            print(f"❌ {error_msg}")
            return False
    
    def login(self, username: str, password: str) -> bool:
        """登入"""
        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_LOGIN, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = username
            self.is_logged_in = True
            print(f"✅ {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登入失敗"
            print(f"❌ {error_msg}")
            return False
    
    def logout(self) -> bool:
        """登出"""
        if not self.is_logged_in:
            print("❌ 您尚未登入")
            return False
        
        response = self.send_request(NetworkProtocol.MSG_LOGOUT)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = None
            self.is_logged_in = False
            print(f"✅ {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登出失敗"
            print(f"❌ {error_msg}")
            return False
    
    def list_games(self) -> Optional[List[Dict]]:
        """獲取遊戲列表"""
        response = self.send_request(NetworkProtocol.MSG_LIST_GAMES)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            games = response.get('data', {}).get('games', [])
            return games
        else:
            error_msg = response.get('message') if response else "獲取遊戲列表失敗"
            print(f"❌ {error_msg}")
            return None
    
    def get_game_info(self, game_name: str) -> Optional[Dict]:
        """獲取遊戲詳細信息"""
        data = {'name': game_name}
        response = self.send_request(NetworkProtocol.MSG_GET_GAME_INFO, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            return response.get('data', {}).get('game')
        else:
            error_msg = response.get('message') if response else "獲取遊戲信息失敗"
            print(f"❌ {error_msg}")
            return None
    
    def download_game(self, game_name: str, version: str = None) -> bool:
        """下載遊戲"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return False
        
        # 檢查本地版本
        local_version = self.get_local_game_version(game_name)
        if local_version and not version:
            print(f"📦 本地已有遊戲 {game_name} v{local_version}")
            update = input("是否檢查更新？ (y/N): ").strip().lower()
            if update != 'y':
                return True
        
        data = {'name': game_name}
        if version:
            data['version'] = version
        
        # 發送下載請求
        response = self.send_request(NetworkProtocol.MSG_DOWNLOAD_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"📤 {response.get('message')}")
            
            # 接收遊戲信息
            game_info = response.get('data', {})
            downloaded_version = game_info.get('version', '1.0.0')
            
            # 如果本地版本相同，跳過下載
            if local_version == downloaded_version:
                print(f"✅ 本地已是最新版本 v{downloaded_version}")
                return True
            
            # 創建遊戲目錄
            game_dir = os.path.join(self.downloads_dir, game_name)
            version_dir = os.path.join(game_dir, downloaded_version)
            os.makedirs(version_dir, exist_ok=True)
            
            # 接收遊戲文件
            temp_zip = os.path.join(version_dir, f"{game_name}.zip")
            
            try:
                if GameProtocol.receive_file(self.socket, temp_zip):
                    # 解壓遊戲文件
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        zip_ref.extractall(version_dir)
                    
                    # 刪除zip文件
                    os.remove(temp_zip)
                    
                    # 更新版本信息
                    self.save_game_version(game_name, downloaded_version)
                    
                    print(f"✅ 遊戲 {game_name} v{downloaded_version} 下載完成")
                    return True
                else:
                    print("❌ 接收遊戲文件失敗")
                    return False
                    
            except Exception as e:
                print(f"❌ 下載處理失敗: {e}")
                return False
        else:
            error_msg = response.get('message') if response else "下載請求失敗"
            print(f"❌ {error_msg}")
            return False
    
    def get_local_game_version(self, game_name: str) -> Optional[str]:
        """獲取本地遊戲版本"""
        version_file = os.path.join(self.downloads_dir, game_name, "version.txt")
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        return None
    
    def save_game_version(self, game_name: str, version: str):
        """保存遊戲版本信息"""
        game_dir = os.path.join(self.downloads_dir, game_name)
        os.makedirs(game_dir, exist_ok=True)
        
        version_file = os.path.join(game_dir, "version.txt")
        with open(version_file, 'w') as f:
            f.write(version)
    
    def list_rooms(self) -> Optional[List[Dict]]:
        """獲取房間列表"""
        response = self.send_request(NetworkProtocol.MSG_LIST_ROOMS)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            rooms = response.get('data', {}).get('rooms', [])
            return rooms
        else:
            error_msg = response.get('message') if response else "獲取房間列表失敗"
            print(f"❌ {error_msg}")
            return None
    
    def create_room(self, game_name: str, game_version: str = None) -> Optional[str]:
        """創建房間"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return None
        
        data = {
            'game_name': game_name,
            'game_version': game_version or ''
        }
        
        response = self.send_request(NetworkProtocol.MSG_CREATE_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            room_info = response.get('data', {})
            room_id = room_info.get('room_id')
            print(f"✅ 房間創建成功")
            print(f"📋 房間ID: {room_id}")
            print(f"🎮 遊戲: {room_info.get('game_name')} v{room_info.get('game_version')}")
            return room_id
        else:
            error_msg = response.get('message') if response else "創建房間失敗"
            print(f"❌ {error_msg}")
            return None
    
    def join_room(self, room_id: str) -> bool:
        """加入房間"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return False
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_JOIN_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            room_info = response.get('data', {})
            print(f"✅ 成功加入房間 {room_id}")
            print(f"👥 當前玩家: {', '.join(room_info.get('players', []))}")
            return True
        else:
            error_msg = response.get('message') if response else "加入房間失敗"
            print(f"❌ {error_msg}")
            return False
    
    def leave_room(self, room_id: str) -> bool:
        """離開房間"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return False
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_LEAVE_ROOM, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"✅ {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "離開房間失敗"
            print(f"❌ {error_msg}")
            return False
    
    def start_game(self, room_id: str) -> Optional[Dict]:
        """開始遊戲"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return None
        
        data = {'room_id': room_id}
        response = self.send_request(NetworkProtocol.MSG_START_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            game_info = response.get('data', {})
            print(f"🎮 {response.get('message')}")
            print(f"🌐 遊戲服務器: {game_info.get('game_server_host')}:{game_info.get('game_server_port')}")
            return game_info
        else:
            error_msg = response.get('message') if response else "開始遊戲失敗"
            print(f"❌ {error_msg}")
            return None
    
    def launch_game_client(self, game_name: str, game_version: str, server_host: str, server_port: int) -> bool:
        """啟動遊戲客戶端"""
        # 檢查本地遊戲是否存在
        version_dir = os.path.join(self.downloads_dir, game_name, game_version)
        if not os.path.exists(version_dir):
            print(f"❌ 本地沒有遊戲 {game_name} v{game_version}")
            print("請先下載遊戲")
            return False
        
        # 查找遊戲客戶端入口
        client_script = None
        for filename in os.listdir(version_dir):
            if filename.endswith('_client.py'):
                client_script = os.path.join(version_dir, filename)
                break
        
        if not client_script or not os.path.exists(client_script):
            print(f"❌ 找不到遊戲客戶端文件")
            return False
        
        try:
            # 啟動遊戲客戶端
            print(f"🚀 正在啟動遊戲客戶端...")
            print(f"📁 執行: {client_script}")
            print(f"🌐 連接到: {server_host}:{server_port}")
            
            # 使用subprocess啟動遊戲客戶端
            process = subprocess.Popen([
                sys.executable, client_script, server_host, str(server_port)
            ], cwd=version_dir)
            
            print(f"✅ 遊戲客戶端已啟動 (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ 啟動遊戲客戶端失敗: {e}")
            return False
    
    def add_review(self, game_name: str, rating: float, comment: str) -> bool:
        """添加遊戲評論"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return False
        
        data = {
            'game_name': game_name,
            'rating': rating,
            'comment': comment
        }
        
        response = self.send_request(NetworkProtocol.MSG_ADD_REVIEW, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"✅ {response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "添加評論失敗"
            print(f"❌ {error_msg}")
            return False
    
    def get_reviews(self, game_name: str) -> Optional[Dict]:
        """獲取遊戲評論"""
        data = {'game_name': game_name}
        response = self.send_request(NetworkProtocol.MSG_GET_REVIEWS, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            return response.get('data', {})
        else:
            error_msg = response.get('message') if response else "獲取評論失敗"
            print(f"❌ {error_msg}")
            return None
    
    def get_player_records(self) -> Optional[List[Dict]]:
        """獲取玩家遊戲記錄"""
        if not self.is_logged_in:
            print("❌ 請先登入")
            return None
        
        response = self.send_request(NetworkProtocol.MSG_GET_PLAYER_RECORDS)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            records = response.get('data', {}).get('records', [])
            return records
        else:
            error_msg = response.get('message') if response else "獲取遊戲記錄失敗"
            print(f"❌ {error_msg}")
            return None

class LobbyUI:
    """大廳用戶界面"""
    
    def __init__(self):
        self.client = LobbyClient()
        self.running = True
        self.current_room_id = None
    
    def show_main_menu(self):
        """顯示主選單"""
        print("\n" + "="*50)
        print("🏛️ 遊戲大廳平台")
        print("="*50)
        
        if self.client.is_logged_in:
            print(f"👤 當前用戶: {self.client.username}")
        else:
            print("👤 尚未登入")
        
        print("\n📋 請選擇操作:")
        
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
        print("🏪 遊戲商城")
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
        print("🏛️ 大廳管理")
        print("="*30)
        print("1. 瀏覽房間")
        print("2. 創建房間")
        print("3. 加入房間")
        if self.current_room_id:
            print("4. 開始遊戲")
            print("5. 離開房間")
        print("0. 返回主選單")
        print("-"*30)
    
    def get_user_choice(self, max_choice: int) -> int:
        """獲取用戶選擇"""
        while True:
            try:
                choice = input("請輸入選項編號: ").strip()
                choice_num = int(choice)
                if 0 <= choice_num <= max_choice:
                    return choice_num
                else:
                    print(f"❌ 請輸入 0 到 {max_choice} 之間的數字")
            except ValueError:
                print("❌ 請輸入有效的數字")
    
    def run(self):
        """運行用戶界面"""
        print("🚀 玩家大廳客戶端啟動中...")
        
        if not self.client.connect():
            print("❌ 無法連接到服務器，程序退出")
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
            print("👋 玩家大廳客戶端已關閉")
    
    def handle_register(self):
        """處理註冊"""
        print("\n📝 註冊新帳號")
        print("-"*30)
        
        username = input("用戶名: ").strip()
        password = input("密碼: ").strip()
        
        if username and password:
            self.client.register(username, password)
        else:
            print("❌ 用戶名和密碼不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_login(self):
        """處理登入"""
        print("\n🔑 登入帳號")
        print("-"*30)
        
        username = input("用戶名: ").strip()
        password = input("密碼: ").strip()
        
        if username and password:
            self.client.login(username, password)
        else:
            print("❌ 用戶名和密碼不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_store(self):
        """處理商城功能"""
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
        """處理大廳功能"""
        while True:
            self.show_lobby_menu()
            max_choice = 5 if self.current_room_id else 3
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
                self.start_game()
            elif choice == 5 and self.current_room_id:
                self.leave_current_room()
    
    def handle_records(self):
        """處理遊戲記錄"""
        print("\n📊 我的遊戲記錄")
        print("-"*30)
        
        records = self.client.get_player_records()
        if not records:
            print("您還沒有遊戲記錄")
        else:
            for i, record in enumerate(records, 1):
                review_status = "✅ 已評論" if record['has_reviewed'] else "❌ 未評論"
                print(f"{i}. {record['game_name']} v{record['game_version']}")
                print(f"   📅 遊玩時間: {record['played_at']}")
                print(f"   💬 評論狀態: {review_status}")
                print()
        
        input("按Enter鍵繼續...")
    
    def show_games_list(self):
        """顯示遊戲列表"""
        print("\n🎮 遊戲列表")
        print("-"*50)
        
        games = self.client.list_games()
        if not games:
            print("目前沒有可用的遊戲")
        else:
            for i, game in enumerate(games, 1):
                rating_display = f"{game['rating']:.1f}/5.0 ({game['rating_count']}人)" if game['rating_count'] > 0 else "暫無評分"
                print(f"{i}. {game['name']}")
                print(f"   👨‍💻 開發者: {game['developer']}")
                print(f"   📝 簡介: {game['description'] or '無簡介'}")
                print(f"   🏷️ 類型: {game['type']} | 👥 最大玩家: {game['max_players']}")
                print(f"   📦 版本: v{game['current_version']} | ⭐ 評分: {rating_display}")
                print()
        
        input("按Enter鍵繼續...")
    
    def search_games(self):
        """搜尋遊戲"""
        print("\n🔍 搜尋遊戲")
        print("-"*30)
        
        keyword = input("請輸入遊戲名稱關鍵字: ").strip().lower()
        if not keyword:
            print("❌ 關鍵字不能為空")
            input("按Enter鍵繼續...")
            return
        
        games = self.client.list_games()
        if not games:
            print("目前沒有可用的遊戲")
        else:
            matches = [game for game in games if keyword in game['name'].lower()]
            
            if not matches:
                print(f"❌ 沒有找到包含 '{keyword}' 的遊戲")
            else:
                print(f"\n找到 {len(matches)} 個結果:")
                for i, game in enumerate(matches, 1):
                    rating_display = f"{game['rating']:.1f}/5.0" if game['rating_count'] > 0 else "暫無評分"
                    print(f"{i}. {game['name']} - {game['developer']} (v{game['current_version']}) ⭐{rating_display}")
        
        input("按Enter鍵繼續...")
    
    def download_game(self):
        """下載遊戲"""
        print("\n📥 下載遊戲")
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
                print("❌ 無效的遊戲編號")
        except ValueError:
            print("❌ 請輸入有效的數字")
        
        input("\n按Enter鍵繼續...")
    
    def view_reviews(self):
        """查看評論"""
        print("\n💬 查看遊戲評論")
        print("-"*30)
        
        game_name = input("請輸入遊戲名稱: ").strip()
        if not game_name:
            print("❌ 遊戲名稱不能為空")
            input("按Enter鍵繼續...")
            return
        
        reviews_data = self.client.get_reviews(game_name)
        if reviews_data:
            reviews = reviews_data.get('reviews', [])
            average_rating = reviews_data.get('average_rating', 0)
            rating_count = reviews_data.get('rating_count', 0)
            
            print(f"\n🎮 {game_name} 的評論")
            print(f"⭐ 平均評分: {average_rating:.1f}/5.0 ({rating_count}人評分)")
            print("-"*40)
            
            if not reviews:
                print("暫無評論")
            else:
                for i, review in enumerate(reviews[-10:], 1):  # 只顯示最近10條
                    print(f"{i}. 👤 {review['player']} | ⭐ {review['rating']}/5")
                    print(f"   📝 {review['comment']}")
                    print(f"   📅 {review['created_at']}")
                    print()
        
        input("按Enter鍵繼續...")
    
    def write_review(self):
        """撰寫評論"""
        print("\n✍️ 撰寫遊戲評論")
        print("-"*30)
        
        game_name = input("遊戲名稱: ").strip()
        if not game_name:
            print("❌ 遊戲名稱不能為空")
            input("按Enter鍵繼續...")
            return
        
        try:
            rating = float(input("評分 (1-5): ").strip())
            if not 1 <= rating <= 5:
                print("❌ 評分必須在1-5之間")
                input("按Enter鍵繼續...")
                return
        except ValueError:
            print("❌ 請輸入有效的評分")
            input("按Enter鍵繼續...")
            return
        
        comment = input("評論內容: ").strip()
        
        self.client.add_review(game_name, rating, comment)
        input("\n按Enter鍵繼續...")
    
    def show_rooms_list(self):
        """顯示房間列表"""
        print("\n🏠 房間列表")
        print("-"*50)
        
        rooms = self.client.list_rooms()
        if not rooms:
            print("目前沒有活躍的房間")
        else:
            for i, room in enumerate(rooms, 1):
                status_emoji = "⏳" if room['status'] == 'waiting' else "🎮"
                print(f"{i}. {status_emoji} 房間 {room['room_id']}")
                print(f"   🎯 遊戲: {room['game_name']} v{room['game_version']}")
                print(f"   👑 房主: {room['host']}")
                print(f"   👥 玩家: {room['current_players']}/{room['max_players']}")
                print(f"   📅 創建時間: {room['created_at']}")
                print()
        
        input("按Enter鍵繼續...")
    
    def create_room(self):
        """創建房間"""
        print("\n🏗️ 創建房間")
        print("-"*30)
        
        games = self.client.list_games()
        if not games:
            print("目前沒有可用的遊戲")
            input("按Enter鍵繼續...")
            return
        
        print("可選遊戲:")
        for i, game in enumerate(games, 1):
            print(f"{i}. {game['name']} v{game['current_version']} ({game['type']})")
        
        try:
            game_idx = int(input("\n選擇遊戲編號: ").strip()) - 1
            if 0 <= game_idx < len(games):
                game = games[game_idx]
                room_id = self.client.create_room(game['name'], game['current_version'])
                if room_id:
                    self.current_room_id = room_id
            else:
                print("❌ 無效的遊戲編號")
        except ValueError:
            print("❌ 請輸入有效的數字")
        
        input("\n按Enter鍵繼續...")
    
    def join_room(self):
        """加入房間"""
        print("\n🚪 加入房間")
        print("-"*30)
        
        room_id = input("請輸入房間ID: ").strip()
        if not room_id:
            print("❌ 房間ID不能為空")
        else:
            if self.client.join_room(room_id):
                self.current_room_id = room_id
        
        input("\n按Enter鍵繼續...")
    
    def start_game(self):
        """開始遊戲"""
        print(f"\n🎮 開始遊戲 (房間: {self.current_room_id})")
        print("-"*30)
        
        game_info = self.client.start_game(self.current_room_id)
        if game_info:
            # 獲取房間信息以確定遊戲和版本
            rooms = self.client.list_rooms()
            current_room = None
            for room in rooms:
                if room['room_id'] == self.current_room_id:
                    current_room = room
                    break
            
            if current_room:
                # 檢查並下載遊戲（如果需要）
                game_name = current_room['game_name']
                game_version = current_room['game_version']
                
                local_version = self.client.get_local_game_version(game_name)
                if local_version != game_version:
                    print(f"📥 需要下載/更新遊戲到版本 {game_version}")
                    if self.client.download_game(game_name, game_version):
                        print("✅ 遊戲已更新到最新版本")
                    else:
                        print("❌ 遊戲下載失敗，無法啟動")
                        input("按Enter鍵繼續...")
                        return
                
                # 啟動遊戲客戶端
                server_host = game_info.get('game_server_host')
                server_port = game_info.get('game_server_port')
                
                if self.client.launch_game_client(game_name, game_version, server_host, server_port):
                    print("🎉 遊戲已啟動！請在新開的遊戲窗口中進行遊戲")
                else:
                    print("❌ 啟動遊戲客戶端失敗")
        
        input("\n按Enter鍵繼續...")
    
    def leave_current_room(self):
        """離開當前房間"""
        if self.current_room_id:
            if self.client.leave_room(self.current_room_id):
                self.current_room_id = None
        else:
            print("❌ 您不在任何房間中")
        
        input("\n按Enter鍵繼續...")

if __name__ == "__main__":
    ui = LobbyUI()
    try:
        ui.run()
    except KeyboardInterrupt:
        print("\n\n👋 程序被中斷，正在退出...")
    except Exception as e:
        print(f"\n❌ 程序出現錯誤: {e}")