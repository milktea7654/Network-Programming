#!/usr/bin/env python3
"""
Developer Server
處理開發者相關的請求：上傳遊戲、更新版本、下架遊戲等
"""
import socket
import threading
import os
import shutil
import zipfile
import tempfile
from datetime import datetime
from typing import Dict, Any
from data_manager import DataManager
from models import Game
from protocol import NetworkProtocol, GameProtocol, ResponseCode

class DeveloperServer:
    """開發者服務器"""
    
    def __init__(self, host: str = "localhost", port: int = 8001, data_dir: str = "./data"):
        self.host = host
        self.port = port
        self.data_manager = DataManager(data_dir)
        self.upload_dir = "./uploaded_games"
        os.makedirs(self.upload_dir, exist_ok=True)
        
        self.server_socket = None
        self.running = False
        self.clients = {}  # {socket: username}
    
    def start(self):
        """啟動服務器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            print(f"Developer Server 啟動於 {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"開發者客戶端連接: {address}")
                    
                    # 為每個客戶端創建處理線程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"接受連接時出錯: {e}")
        
        except Exception as e:
            print(f"啟動Developer Server失敗: {e}")
        finally:
            self.cleanup()
    
    def stop(self):
        """停止服務器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def cleanup(self):
        """清理資源"""
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.clients.clear()
        
        if self.server_socket:
            self.server_socket.close()
    
    def handle_client(self, client_socket: socket.socket):
        """處理客戶端請求"""
        try:
            while self.running:
                message = NetworkProtocol.receive_message(client_socket)
                if not message:
                    break
                
                response = self.process_message(client_socket, message)
                if response:
                    NetworkProtocol.send_message(client_socket, response)
                    
        except Exception as e:
            print(f"處理客戶端時出錯: {e}")
        finally:
            # 客戶端斷線處理
            if client_socket in self.clients:
                username = self.clients[client_socket]
                self.data_manager.set_user_online(username, False)
                del self.clients[client_socket]
            client_socket.close()
    
    def process_message(self, client_socket: socket.socket, message: Dict[str, Any]) -> Dict[str, Any]:
        """處理消息"""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        try:
            if msg_type == NetworkProtocol.MSG_REGISTER:
                return self.handle_register(data)
            elif msg_type == NetworkProtocol.MSG_LOGIN:
                return self.handle_login(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_LOGOUT:
                return self.handle_logout(client_socket)
            elif msg_type == NetworkProtocol.MSG_UPLOAD_GAME:
                return self.handle_upload_game(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_UPDATE_GAME:
                return self.handle_update_game(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_REMOVE_GAME:
                return self.handle_remove_game(client_socket, data)
            elif msg_type == NetworkProtocol.MSG_LIST_GAMES:
                return self.handle_list_developer_games(client_socket)
            else:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "未知的消息類型"
                )
                
        except Exception as e:
            print(f"處理消息時出錯: {e}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"服務器內部錯誤: {str(e)}"
            )
    
    def handle_register(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理註冊"""
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名和密碼不能為空"
            )
        
        if self.data_manager.create_user(username, password, 'developer'):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "註冊成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "用戶名已存在"
            )
    
    def handle_login(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理登入"""
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = self.data_manager.authenticate_user(username, password, 'developer')
        if user:
            # 檢查是否已經在線
            if user.is_online:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "該帳號已在其他裝置登入"
                )
            
            self.clients[client_socket] = username
            self.data_manager.set_user_online(username, True)
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "登入成功",
                {'username': username}
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "帳號或密碼錯誤"
            )
    
    def handle_logout(self, client_socket: socket.socket) -> Dict[str, Any]:
        """處理登出"""
        if client_socket in self.clients:
            username = self.clients[client_socket]
            self.data_manager.set_user_online(username, False)
            del self.clients[client_socket]
            
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "登出成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "未登入"
            )
    
    def handle_upload_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理遊戲上傳"""
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        developer = self.clients[client_socket]
        game_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        game_type = data.get('type', 'cli')
        max_players = data.get('max_players', 2)
        
        if not game_name:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲名稱不能為空"
            )
        
        # 檢查遊戲是否已存在
        if game_name in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲名稱已存在"
            )
        
        # 創建遊戲對象
        game = Game(game_name, developer, description, game_type, max_players)
        
        # 創建遊戲目錄
        game_dir = os.path.join(self.upload_dir, game_name)
        version_dir = os.path.join(game_dir, game.current_version)
        os.makedirs(version_dir, exist_ok=True)
        
        # 接收遊戲文件 (假設為zip文件)
        zip_path = os.path.join(version_dir, f"{game_name}.zip")
        
        try:
            # 通知客戶端準備發送文件
            response = NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "準備接收遊戲文件"
            )
            NetworkProtocol.send_message(client_socket, response)
            
            # 接收zip文件
            if GameProtocol.receive_file(client_socket, zip_path):
                # 解壓文件
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(version_dir)
                
                # 刪除zip文件
                os.remove(zip_path)
                
                # 保存遊戲信息到數據庫
                if self.data_manager.add_game(game):
                    return NetworkProtocol.create_response(
                        NetworkProtocol.STATUS_SUCCESS,
                        "遊戲上傳成功"
                    )
                else:
                    return NetworkProtocol.create_response(
                        NetworkProtocol.STATUS_ERROR,
                        "保存遊戲信息失敗"
                    )
            else:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "接收遊戲文件失敗"
                )
                
        except Exception as e:
            print(f"上傳遊戲時出錯: {e}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"上傳失敗: {str(e)}"
            )
    
    def handle_update_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理遊戲更新"""
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        developer = self.clients[client_socket]
        game_name = data.get('name', '').strip()
        new_version = data.get('version', '').strip()
        update_desc = data.get('description', '')
        
        if not game_name or not new_version:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲名稱和版本號不能為空"
            )
        
        # 檢查遊戲是否存在且屬於該開發者
        if game_name not in self.data_manager.games:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲不存在"
            )
        
        game = self.data_manager.games[game_name]
        if game.developer != developer:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "只能更新自己的遊戲"
            )
        
        # 檢查版本是否已存在
        if new_version in game.versions:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "該版本已存在"
            )
        
        # 創建新版本目錄
        game_dir = os.path.join(self.upload_dir, game_name)
        version_dir = os.path.join(game_dir, new_version)
        os.makedirs(version_dir, exist_ok=True)
        
        # 接收新版本文件
        zip_path = os.path.join(version_dir, f"{game_name}_v{new_version}.zip")
        
        try:
            # 通知客戶端準備發送文件
            response = NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "準備接收新版本文件"
            )
            NetworkProtocol.send_message(client_socket, response)
            
            # 接收zip文件
            if GameProtocol.receive_file(client_socket, zip_path):
                # 解壓文件
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(version_dir)
                
                # 刪除zip文件
                os.remove(zip_path)
                
                # 更新遊戲版本信息
                if self.data_manager.update_game_version(game_name, new_version, update_desc):
                    return NetworkProtocol.create_response(
                        NetworkProtocol.STATUS_SUCCESS,
                        "遊戲更新成功"
                    )
                else:
                    return NetworkProtocol.create_response(
                        NetworkProtocol.STATUS_ERROR,
                        "更新遊戲信息失敗"
                    )
            else:
                return NetworkProtocol.create_response(
                    NetworkProtocol.STATUS_ERROR,
                    "接收更新文件失敗"
                )
                
        except Exception as e:
            print(f"更新遊戲時出錯: {e}")
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                f"更新失敗: {str(e)}"
            )
    
    def handle_remove_game(self, client_socket: socket.socket, data: Dict[str, Any]) -> Dict[str, Any]:
        """處理遊戲下架"""
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        developer = self.clients[client_socket]
        game_name = data.get('name', '').strip()
        
        if not game_name:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "遊戲名稱不能為空"
            )
        
        if self.data_manager.remove_game(game_name, developer):
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_SUCCESS,
                "遊戲下架成功"
            )
        else:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "下架失敗：遊戲不存在或不是您的遊戲"
            )
    
    def handle_list_developer_games(self, client_socket: socket.socket) -> Dict[str, Any]:
        """獲取開發者的遊戲列表"""
        if client_socket not in self.clients:
            return NetworkProtocol.create_response(
                NetworkProtocol.STATUS_ERROR,
                "請先登入"
            )
        
        developer = self.clients[client_socket]
        games = self.data_manager.get_developer_games(developer)
        
        games_data = []
        for game in games:
            games_data.append({
                'name': game.name,
                'description': game.description,
                'type': game.game_type,
                'max_players': game.max_players,
                'current_version': game.current_version,
                'versions': list(game.versions.keys()),
                'is_active': game.is_active,
                'rating': game.get_average_rating(),
                'rating_count': game.rating_count
            })
        
        return NetworkProtocol.create_response(
            NetworkProtocol.STATUS_SUCCESS,
            "獲取遊戲列表成功",
            {'games': games_data}
        )

if __name__ == "__main__":
    server = DeveloperServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n正在關閉Developer Server...")
        server.stop()