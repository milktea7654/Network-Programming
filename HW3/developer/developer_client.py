import socket
import os
import sys
import zipfile
import tempfile
import argparse
from typing import Dict, Any, Optional

SERVER_HOST = "linux2.cs.nycu.edu.tw"  
SERVER_PORT = 8001

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from protocol import NetworkProtocol, GameProtocol

class DeveloperClient:

    def __init__(self, server_host: str = SERVER_HOST, server_port: int = SERVER_PORT):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.is_logged_in = False
    
    def _create_game_zip(self, game_path: str, zip_path: str) -> bool:
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isfile(game_path):
                    zipf.write(game_path, os.path.basename(game_path))
                else:
                    for root, dirs, files in os.walk(game_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, game_path)
                            zipf.write(file_path, arcname)
            return True
        except Exception as e:
            print(f"創建遊戲包失敗: {e}")
            return False
        
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"已連接到開發者服務器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"連接失敗: {e}")
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
        
        message = NetworkProtocol.create_message(msg_type, data)
        
        if NetworkProtocol.send_message(self.socket, message):
            response = NetworkProtocol.receive_message(self.socket)
            return response
        else:
            print("發送消息失敗")
            return None
    
    def register(self, username: str, password: str) -> bool:

        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_REGISTER, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"{response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "註冊失敗"
            print(f"{error_msg}")
            return False
    
    def login(self, username: str, password: str) -> bool:

        data = {'username': username, 'password': password}
        response = self.send_request(NetworkProtocol.MSG_LOGIN, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = username
            self.is_logged_in = True
            print(f"{response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登入失敗"
            print(f"{error_msg}")
            return False
    
    def logout(self) -> bool:

        if not self.is_logged_in:
            print("您尚未登入")
            return False
        
        response = self.send_request(NetworkProtocol.MSG_LOGOUT)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            self.username = None
            self.is_logged_in = False
            print(f"{response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "登出失敗"
            print(f"{error_msg}")
            return False
    
    def upload_game(self, game_name: str, description: str, game_type: str, 
                   max_players: int, game_path: str) -> bool:

        if not self.is_logged_in:
            print("請先登入")
            return False
        
        if not os.path.exists(game_path):
            print(f"遊戲路徑不存在: {game_path}")
            return False
        
        data = {
            'name': game_name,
            'description': description,
            'type': game_type,
            'max_players': max_players
        }
        

        response = self.send_request(NetworkProtocol.MSG_UPLOAD_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"{response.get('message')}")
            
            temp_zip = f"/tmp/{game_name}_upload.zip"
            
            try:
                if not self._create_game_zip(game_path, temp_zip):
                    return False
                
                if GameProtocol.send_file(self.socket, temp_zip):
                    print("遊戲文件上傳完成")

                    final_response = NetworkProtocol.receive_message(self.socket)
                    if final_response and final_response.get('status') == NetworkProtocol.STATUS_SUCCESS:
                        print(f"{final_response.get('message')}")
                        return True
                    else:
                        error_msg = final_response.get('message') if final_response else "上傳完成但保存失敗"
                        print(f"{error_msg}")
                        return False
                else:
                    print("遊戲文件發送失敗")
                    return False
                    
            finally:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
        else:
            error_msg = response.get('message') if response else "上傳請求失敗"
            print(f"{error_msg}")
            return False
    
    def update_game(self, game_name: str, new_version: str, description: str, game_path: str) -> bool:
        if not self.is_logged_in:
            print("請先登入")
            return False
        
        if not os.path.exists(game_path):
            print(f"遊戲路徑不存在: {game_path}")
            return False
        
        data = {
            'name': game_name,
            'version': new_version,
            'description': description
        }
        
        response = self.send_request(NetworkProtocol.MSG_UPDATE_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"{response.get('message')}")
            
            temp_zip = f"/tmp/{game_name}_update_v{new_version}.zip"
            
            try:
                if not self._create_game_zip(game_path, temp_zip):
                    return False
                
                if GameProtocol.send_file(self.socket, temp_zip):
                    print("遊戲文件更新完成")
                    
                    final_response = NetworkProtocol.receive_message(self.socket)
                    if final_response and final_response.get('status') == NetworkProtocol.STATUS_SUCCESS:
                        print(f"{final_response.get('message')}")
                        return True
                    else:
                        error_msg = final_response.get('message') if final_response else "更新完成但保存失敗"
                        print(f"{error_msg}")
                        return False
                else:
                    print("遊戲文件發送失敗")
                    return False
                    
            finally:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
        else:
            error_msg = response.get('message') if response else "更新請求失敗"
            print(f"{error_msg}")
            return False
    
    def remove_game(self, game_name: str) -> bool:
        if not self.is_logged_in:
            print("請先登入")
            return False
        
        data = {'name': game_name}
        response = self.send_request(NetworkProtocol.MSG_REMOVE_GAME, data)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            print(f"{response.get('message')}")
            return True
        else:
            error_msg = response.get('message') if response else "下架失敗"
            print(f"{error_msg}")
            return False
    
    def list_my_games(self) -> Optional[list]:
        if not self.is_logged_in:
            print("請先登入")
            return None
        
        response = self.send_request(NetworkProtocol.MSG_LIST_GAMES)
        
        if response and response.get('status') == NetworkProtocol.STATUS_SUCCESS:
            games = response.get('data', {}).get('games', [])
            return games
        else:
            error_msg = response.get('message') if response else "獲取遊戲列表失敗"
            print(f"{error_msg}")
            return None

class DeveloperUI:

    def __init__(self, server_host: str = SERVER_HOST, server_port: int = SERVER_PORT):
        self.client = DeveloperClient(server_host=server_host, server_port=server_port)
        self.running = True
    
    def show_main_menu(self):
        print("\n" + "="*50)
        print("遊戲開發者平台")
        print("="*50)
        
        if self.client.is_logged_in:
            print(f"當前用戶: {self.client.username}")
        else:
            print("尚未登入")
        
        print("\n請選擇操作:")
        
        if not self.client.is_logged_in:
            print("1. 註冊新帳號")
            print("2. 登入帳號")
        else:
            print("1. 上傳新遊戲")
            print("2. 更新遊戲版本")
            print("3. 下架遊戲")
            print("4. 檢視我的遊戲")
            print("5. 登出")
        
        print("0. 退出程式")
        print("-"*50)
    
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
        print("開發者客戶端啟動中...")
        
        if not self.client.connect():
            print("無法連接到服務器，程序退出")
            return
        
        try:
            while self.running:
                self.show_main_menu()
                
                if not self.client.is_logged_in:
                    max_choice = 2
                else:
                    max_choice = 5
                
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
                        self.handle_upload_game()
                    elif choice == 2:
                        self.handle_update_game()
                    elif choice == 3:
                        self.handle_remove_game()
                    elif choice == 4:
                        self.handle_list_games()
                    elif choice == 5:
                        self.client.logout()
        
        finally:
            self.client.disconnect()
            print("開發者客戶端已關閉")
    
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
        print("\n登入帳號")
        print("-"*30)
        
        username = input("用戶名: ").strip()
        password = input("密碼: ").strip()
        
        if username and password:
            self.client.login(username, password)
        else:
            print("用戶名和密碼不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_upload_game(self):
        print("\n上傳新遊戲")
        print("-"*30)
        
        game_name = input("遊戲名稱: ").strip()
        description = input("遊戲簡介: ").strip()
        
        print("\n遊戲類型:")
        print("1. CLI (命令行)")
        print("2. GUI (圖形介面)")
        print("3. Multiplayer (多人)")
        
        type_choice = self.get_user_choice(3)
        type_map = {1: "cli", 2: "gui", 3: "multiplayer"}
        game_type = type_map.get(type_choice, "cli")
        
        try:
            max_players = int(input("最大玩家數: ").strip())
        except ValueError:
            max_players = 2
        
        game_path = input("遊戲文件路徑 (文件或目錄): ").strip()
        
        if game_name and game_path:
            type_display = {"cli": "CLI", "gui": "GUI", "multiplayer": "MULTIPLAYER"}
            print("\n確認上傳資訊:")
            print(f"   遊戲名稱: {game_name}")
            print(f"   簡介: {description}")
            print(f"   類型: {type_display.get(game_type, game_type.upper())}")
            print(f"   最大玩家數: {max_players}")
            print(f"   路徑: {game_path}")
            
            confirm = input("\n確認上傳? (Y/N): ").strip().upper()
            if confirm != 'Y':
                print("已取消上傳")
                input("\n按Enter鍵繼續...")
                return
            
            if self.client.upload_game(game_name, description, game_type, max_players, game_path):
                print("\n修改確認:")
                print(f"   遊戲 '{game_name}' 已成功上架")
                print(f"   版本: v1.0.0")
                print(f"   狀態: 已上架")
        else:
            print("遊戲名稱和路徑不能為空")
        
        input("\n按Enter鍵繼續...")
    
    def handle_update_game(self):
        print("\n更新遊戲版本")
        print("-"*30)
        
        games = self.client.list_my_games()
        if not games:
            print("您還沒有上傳任何遊戲")
            input("\n按Enter鍵繼續...")
            return
        
        print("您的遊戲列表:")
        for i, game in enumerate(games, 1):
            print(f"{i}. {game['name']} (v{game['current_version']}) - {game['type']}")
        
        try:
            game_idx = int(input("\n選擇要更新的遊戲編號: ").strip()) - 1
            if 0 <= game_idx < len(games):
                game_name = games[game_idx]['name']
                
                new_version = input("新版本號: ").strip()
                description = input("更新說明: ").strip()
                game_path = input("新版本文件路徑 (文件或目錄): ").strip()
                
                if new_version and game_path:
                    print("\n確認更新資訊:")
                    print(f"   遊戲名稱: {game_name}")
                    print(f"   當前版本: v{games[game_idx]['current_version']}")
                    print(f"   新版本: v{new_version}")
                    print(f"   更新說明: {description}")
                    print(f"   路徑: {game_path}")
                    
                    confirm = input("\n確認更新? (Y/N): ").strip().upper()
                    if confirm != 'Y':
                        print("已取消更新")
                        input("\n按Enter鍵繼續...")
                        return
                    
                    if self.client.update_game(game_name, new_version, description, game_path):
                        print("\n修改確認:")
                        print(f"   遊戲 '{game_name}' 已更新至 v{new_version}")
                        print(f"   更新說明: {description}")
                        print(f"   狀態: 最新版本已生效")
                else:
                    print("版本號和路徑不能為空")
            else:
                print("無效的遊戲編號")
        except ValueError:
            print("請輸入有效的數字")
        
        input("\n按Enter鍵繼續...")
    
    def handle_remove_game(self):
        print("\n下架遊戲")
        print("-"*30)
        
        games = self.client.list_my_games()
        if not games:
            print("您還沒有上傳任何遊戲")
            input("\n按Enter鍵繼續...")
            return
        
        print("您的遊戲列表:")
        for i, game in enumerate(games, 1):
            status = "已上架" if game['is_active'] else "已下架"
            print(f"{i}. {game['name']} (v{game['current_version']}) - {status}")
        
        try:
            game_idx = int(input("\n選擇要下架的遊戲編號: ").strip()) - 1
            if 0 <= game_idx < len(games):
                game_name = games[game_idx]['name']
                
                confirm = input(f"確定要下架遊戲 '{game_name}' 嗎? (Y/N): ").strip().upper()
                if confirm == 'Y':
                    if self.client.remove_game(game_name):
                        print("\n修改確認:")
                        print(f"   遊戲 '{game_name}' 已下架")
                        print(f"   狀態: 不再顯示於遊戲商城")
                        print(f"   註: 已下載的玩家仍可本地遊玩")
                else:
                    print("已取消下架操作")
            else:
                print("無效的遊戲編號")
        except ValueError:
            print("請輸入有效的數字")
        
        input("\n按Enter鍵繼續...")
    
    def handle_list_games(self):
        print("\n我的遊戲列表")
        print("-"*30)
        
        games = self.client.list_my_games()
        if not games:
            print("您還沒有上傳任何遊戲")
        else:
            for game in games:
                status = "已上架" if game['is_active'] else "已下架"
                rating = f"{game['rating']:.1f}/5.0" if game['rating_count'] > 0 else "暫無評分"
                
                print(f"\n{game['name']}")
                print(f"簡介: {game['description'] or '無'}")
                print(f"類型: {game['type']}")
                print(f"最大玩家數: {game['max_players']}")
                print(f"當前版本: v{game['current_version']}")
                print(f"狀態: {status}")
                print(f"評分: {rating} ({game['rating_count']}人評分)")
                print(f"版本列表: {', '.join([f'v{v}' for v in game['versions']])}")
        
        input("\n按Enter鍵繼續...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='開發者客戶端')
    parser.add_argument('--host', default=SERVER_HOST, help=f'服務器地址 (預設: {SERVER_HOST})')
    parser.add_argument('--port', type=int, default=SERVER_PORT, help=f'服務器端口 (預設: {SERVER_PORT})')
    args = parser.parse_args()
    
    ui = DeveloperUI(server_host=args.host, server_port=args.port)
    try:
        ui.run()
    except KeyboardInterrupt:
        print("\n\n程序被中斷，正在退出...")
    except Exception as e:
        print(f"\n程序出現錯誤: {e}")