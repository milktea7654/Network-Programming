#!/usr/bin/env python3
"""
網路通信協議定義
統一服務端與客戶端的通信格式
"""
import json
import socket
from typing import Dict, Any, Optional

class NetworkProtocol:
    """網路通信協議"""
    
    # 消息類型定義
    MSG_REGISTER = "REGISTER"
    MSG_LOGIN = "LOGIN" 
    MSG_LOGOUT = "LOGOUT"
    MSG_UPLOAD_GAME = "UPLOAD_GAME"
    MSG_UPDATE_GAME = "UPDATE_GAME"
    MSG_REMOVE_GAME = "REMOVE_GAME"
    MSG_LIST_GAMES = "LIST_GAMES"
    MSG_GET_GAME_INFO = "GET_GAME_INFO"
    MSG_DOWNLOAD_GAME = "DOWNLOAD_GAME"
    MSG_CREATE_ROOM = "CREATE_ROOM"
    MSG_JOIN_ROOM = "JOIN_ROOM"
    MSG_LEAVE_ROOM = "LEAVE_ROOM"
    MSG_LIST_ROOMS = "LIST_ROOMS"
    MSG_START_GAME = "START_GAME"
    MSG_ADD_REVIEW = "ADD_REVIEW"
    MSG_GET_REVIEWS = "GET_REVIEWS"
    MSG_GET_PLAYER_RECORDS = "GET_PLAYER_RECORDS"
    
    # 回應狀態
    STATUS_SUCCESS = "SUCCESS"
    STATUS_ERROR = "ERROR"
    STATUS_FAILED = "FAILED"

    @staticmethod
    def create_message(msg_type: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """創建標準消息格式"""
        return {
            'type': msg_type,
            'data': data or {}
        }
    
    @staticmethod
    def create_response(status: str, message: str = "", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """創建標準回應格式"""
        return {
            'status': status,
            'message': message,
            'data': data or {}
        }
    
    @staticmethod
    def send_message(sock: socket.socket, message: Dict[str, Any]) -> bool:
        """發送消息"""
        try:
            json_data = json.dumps(message, ensure_ascii=False)
            data = json_data.encode('utf-8')
            
            # 先發送數據長度
            length = len(data)
            sock.sendall(length.to_bytes(4, 'big'))
            
            # 再發送實際數據
            sock.sendall(data)
            return True
            
        except Exception as e:
            print(f"發送消息失敗: {e}")
            return False
    
    @staticmethod
    def receive_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
        """接收消息"""
        try:
            # 接收數據長度
            length_data = sock.recv(4)
            if len(length_data) != 4:
                return None
            
            length = int.from_bytes(length_data, 'big')
            
            # 檢查長度是否合理（防止異常大的數據）
            if length > 100 * 1024 * 1024:  # 100MB 限制
                print(f"❌ 數據長度異常: {length} bytes")
                return None
            
            # 接收實際數據
            data = b''
            while len(data) < length:
                chunk = sock.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            # 嘗試解碼，如果失敗則嘗試其他編碼
            try:
                json_str = data.decode('utf-8')
            except UnicodeDecodeError as e:
                print(f"⚠️ UTF-8解碼失敗，嘗試使用 latin-1: {e}")
                # 嘗試 latin-1 作為後備
                json_str = data.decode('latin-1')
            
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失敗: {e}")
            print(f"   數據預覽: {data[:100] if len(data) > 100 else data}")
            return None
        except Exception as e:
            print(f"接收消息失敗: {e}")
            import traceback
            traceback.print_exc()
            return None

class GameProtocol:
    """遊戲文件傳輸協議"""
    
    @staticmethod
    def send_file(sock: socket.socket, file_path: str) -> bool:
        """發送文件"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # 發送文件大小
            size = len(data)
            sock.sendall(size.to_bytes(8, 'big'))
            
            # 發送文件數據
            sock.sendall(data)
            return True
            
        except Exception as e:
            print(f"發送文件失敗: {e}")
            return False
    
    @staticmethod
    def receive_file(sock: socket.socket, save_path: str) -> bool:
        """接收文件"""
        try:
            # 接收文件大小
            size_data = sock.recv(8)
            if len(size_data) != 8:
                return False
            
            size = int.from_bytes(size_data, 'big')
            
            # 接收文件數據
            data = b''
            while len(data) < size:
                chunk = sock.recv(min(size - len(data), 8192))
                if not chunk:
                    return False
                data += chunk
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(data)
            
            return True
            
        except Exception as e:
            print(f"接收文件失敗: {e}")
            return False

# 響應代碼定義
class ResponseCode:
    """響應代碼"""
    
    # 成功代碼
    SUCCESS = 200
    CREATED = 201
    
    # 客戶端錯誤
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    
    # 服務端錯誤
    INTERNAL_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503