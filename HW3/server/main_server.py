#!/usr/bin/env python3
"""
遊戲平台主服務器啟動器
同時啟動 Developer Server 和 Lobby Server
"""
import threading
import time
import signal
import sys
from developer_server import DeveloperServer
from lobby_server import LobbyServer
from data_manager import DataManager

class GamePlatformServer:
    """遊戲平台服務器"""
    
    def __init__(self):
        # 創建共用的 DataManager 實例
        print("\n" + "="*60)
        print("📋 初始化遊戲平台服務器")
        print("="*60)
        
        shared_data_manager = DataManager("./data")
        print(f"\n📦 DataManager 實例 ID: {id(shared_data_manager)}")
        print(f"   當前用戶數: {len(shared_data_manager.users)}")
        print(f"   當前遊戲數: {len(shared_data_manager.games)}")
        if shared_data_manager.games:
            print(f"   遊戲列表:")
            for name, game in shared_data_manager.games.items():
                status = "✅已上架" if game.is_active else "❌已下架"
                print(f"      - {name} ({status})")
        
        # 兩個服務器共用同一個 DataManager
        self.developer_server = DeveloperServer(host="0.0.0.0", port=8001, data_manager=shared_data_manager)
        self.lobby_server = LobbyServer(host="0.0.0.0", port=8002, data_manager=shared_data_manager)
        
        print(f"\n🔗 確認共用狀態:")
        print(f"   DeveloperServer DataManager ID: {id(self.developer_server.data_manager)}")
        print(f"   LobbyServer DataManager ID: {id(self.lobby_server.data_manager)}")
        print(f"   是否為同一個實例: {id(self.developer_server.data_manager) == id(self.lobby_server.data_manager)}")
        print("="*60 + "\n")
        
        self.running = False
    
    def start(self):
        """啟動所有服務器"""
        print("=" * 50)
        print("遊戲平台服務器啟動中...")
        print("=" * 50)
        
        # 啟動 Developer Server
        dev_thread = threading.Thread(
            target=self.developer_server.start,
            daemon=True
        )
        dev_thread.start()
        
        time.sleep(1)  # 等待開發者服務器啟動
        
        # 啟動 Lobby Server
        lobby_thread = threading.Thread(
            target=self.lobby_server.start,
            daemon=True
        )
        lobby_thread.start()
        
        time.sleep(1)  # 等待大廳服務器啟動
        
        self.running = True
        
        print("\n🎮 遊戲平台服務器已啟動！")
        print("━" * 50)
        print("📋 服務器信息:")
        print(f"   • Developer Server: localhost:8001")
        print(f"   • Lobby Server:     localhost:8002")
        print("━" * 50)
        print("💡 使用說明:")
        print("   1. 開發者請連接到 localhost:8001")
        print("   2. 玩家請連接到 localhost:8002")
        print("   3. 按 Ctrl+C 停止服務器")
        print("━" * 50)
        
        try:
            # 主線程保持運行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """停止所有服務器"""
        print("\n\n🔄 正在關閉遊戲平台服務器...")
        
        self.running = False
        
        # 停止服務器
        self.developer_server.stop()
        self.lobby_server.stop()
        
        print("✅ 遊戲平台服務器已安全關閉")
        sys.exit(0)

def signal_handler(signum, frame):
    """信號處理器"""
    print("\n收到停止信號...")
    if hasattr(signal_handler, 'server'):
        signal_handler.server.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 註冊信號處理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 創建並啟動服務器
    server = GamePlatformServer()
    signal_handler.server = server
    
    try:
        server.start()
    except Exception as e:
        print(f"❌ 服務器啟動失敗: {e}")
        sys.exit(1)