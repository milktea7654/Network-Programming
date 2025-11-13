import struct
import socket
import json

MAX_MESSAGE_LENGTH = 65536

class ProtocolError(Exception):
    pass


def send_message(sock: socket.socket, data: dict) -> None:
    message = json.dumps(data, ensure_ascii=False).encode('utf-8')
    length = len(message)
    if length > MAX_MESSAGE_LENGTH:
        raise ProtocolError(f"Message too large: {length} bytes (max {MAX_MESSAGE_LENGTH})")
    header = struct.pack('!I', length)
    _send_all(sock, header + message)


def recv_message(sock: socket.socket) -> dict:
    header = _recv_all(sock, 4)
    if not header:
        raise ConnectionError("Connection closed")
    length = struct.unpack('!I', header)[0]
    if length <= 0 or length > MAX_MESSAGE_LENGTH:
        raise ProtocolError(f"Invalid message length: {length}")
    message = _recv_all(sock, length)
    if not message:
        raise ConnectionError("Connection closed while reading message body")
    try:
        data = json.loads(message.decode('utf-8'))
        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"Failed to decode message: {e}")


def _send_all(sock: socket.socket, data: bytes) -> None:
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise ConnectionError("Socket connection broken")
        total_sent += sent


def _recv_all(sock: socket.socket, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("Socket connection broken")
        data.extend(chunk)
    return bytes(data)
