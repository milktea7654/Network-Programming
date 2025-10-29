"""
Length-Prefixed Framing Protocol Implementation
用於 TCP 通訊的長度前綴協議
"""
import struct
import socket
import json

# 最大訊息長度：64 KiB
MAX_MESSAGE_LENGTH = 65536

class ProtocolError(Exception):
    """協議錯誤"""
    pass


def send_message(sock: socket.socket, data: dict) -> None:
    """
    發送一個 JSON 訊息，使用長度前綴協議
    
    Args:
        sock: socket 連接
        data: 要發送的字典資料
    """
    # 將字典轉換為 JSON 字串，然後編碼為 UTF-8
    message = json.dumps(data, ensure_ascii=False).encode('utf-8')
    length = len(message)
    
    # 檢查長度限制
    if length > MAX_MESSAGE_LENGTH:
        raise ProtocolError(f"Message too large: {length} bytes (max {MAX_MESSAGE_LENGTH})")
    
    # 打包長度前綴（4 bytes, network byte order, big-endian）
    header = struct.pack('!I', length)
    
    # 發送完整訊息（長度 + 內容）
    _send_all(sock, header + message)


def recv_message(sock: socket.socket) -> dict:
    """
    接收一個 JSON 訊息，使用長度前綴協議
    
    Args:
        sock: socket 連接
        
    Returns:
        接收到的字典資料
    """
    # 先讀取 4 bytes 的長度前綴
    header = _recv_all(sock, 4)
    if not header:
        raise ConnectionError("Connection closed")
    
    # 解析長度
    length = struct.unpack('!I', header)[0]
    
    # 驗證長度
    if length <= 0 or length > MAX_MESSAGE_LENGTH:
        raise ProtocolError(f"Invalid message length: {length}")
    
    # 讀取訊息本體
    message = _recv_all(sock, length)
    if not message:
        raise ConnectionError("Connection closed while reading message body")
    
    # 解碼並解析 JSON
    try:
        data = json.loads(message.decode('utf-8'))
        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"Failed to decode message: {e}")


def _send_all(sock: socket.socket, data: bytes) -> None:
    """
    確保發送所有資料（處理部分發送）
    
    Args:
        sock: socket 連接
        data: 要發送的位元組資料
    """
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise ConnectionError("Socket connection broken")
        total_sent += sent


def _recv_all(sock: socket.socket, length: int) -> bytes:
    """
    確保接收指定長度的資料（處理部分接收）
    
    Args:
        sock: socket 連接
        length: 要接收的位元組數
        
    Returns:
        接收到的位元組資料
    """
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("Socket connection broken")
        data.extend(chunk)
    return bytes(data)
