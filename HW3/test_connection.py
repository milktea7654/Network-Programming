#!/usr/bin/env python3
"""測試連接腳本"""
import sys
import os

# 模擬 launcher 的環境
print("=" * 60)
print("測試 Developer Client")
print("=" * 60)

project_root = os.path.dirname(os.path.abspath(__file__))
developer_dir = os.path.join(project_root, "developer")
sys.path.insert(0, developer_dir)
os.chdir(developer_dir)

import developer_client
from developer_client import DeveloperClient
SERVER_HOST = developer_client.SERVER_HOST
SERVER_PORT = developer_client.SERVER_PORT

print(f"SERVER_HOST 常數: {SERVER_HOST}")
print(f"SERVER_PORT 常數: {SERVER_PORT}")

client = DeveloperClient()
print(f"客戶端實例 host: {client.server_host}")
print(f"客戶端實例 port: {client.server_port}")

print("\n嘗試連接...")
if client.connect():
    print("✅ 連接成功！")
    client.disconnect()
else:
    print("❌ 連接失敗")

print("\n" + "=" * 60)
print("測試 Lobby Client")
print("=" * 60)

player_dir = os.path.join(project_root, "player")
sys.path.insert(0, player_dir)
os.chdir(player_dir)

import lobby_client
from lobby_client import LobbyClient
LOBBY_HOST = lobby_client.SERVER_HOST
LOBBY_PORT = lobby_client.SERVER_PORT

print(f"SERVER_HOST 常數: {LOBBY_HOST}")
print(f"SERVER_PORT 常數: {LOBBY_PORT}")

lobby_client = LobbyClient()
print(f"客戶端實例 host: {lobby_client.server_host}")
print(f"客戶端實例 port: {lobby_client.server_port}")

print("\n嘗試連接...")
if lobby_client.connect():
    print("✅ 連接成功！")
    lobby_client.disconnect()
else:
    print("❌ 連接失敗")
