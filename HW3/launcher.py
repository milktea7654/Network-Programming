#!/usr/bin/env python3
"""
系統啟動腳本
提供便捷的方式啟動各個組件
"""
import os
import sys
import subprocess
import time
import signal

def get_project_root():
    """獲取專案根目錄"""
    return os.path.dirname(os.path.abspath(__file__))

def start_server():
    """啟動服務器"""
    print("🚀 啟動遊戲平台服務器...")
    
    server_dir = os.path.join(get_project_root(), "server")
    main_server = os.path.join(server_dir, "main_server.py")
    
    if not os.path.exists(main_server):
        print(f"❌ 找不到主服務器文件: {main_server}")
        return False
    
    try:
        os.chdir(server_dir)
        process = subprocess.Popen([sys.executable, "main_server.py"])
        print(f"✅ 服務器已啟動 (PID: {process.pid})")
        print("📋 服務器地址:")
        print("   • Developer Server: localhost:8001")
        print("   • Lobby Server:     localhost:8002")
        print("\n⚠️  請按 Ctrl+C 停止服務器")
        
        # 等待用戶中斷
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🔄 正在停止服務器...")
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
            print("✅ 服務器已停止")
        
        return True
    except Exception as e:
        print(f"❌ 啟動服務器失敗: {e}")
        return False

def start_developer_client():
    """啟動開發者客戶端"""
    print("🎨 啟動開發者客戶端...")
    
    developer_dir = os.path.join(get_project_root(), "developer")
    client_script = os.path.join(developer_dir, "developer_client.py")
    
    if not os.path.exists(client_script):
        print(f"❌ 找不到開發者客戶端: {client_script}")
        return False
    
    try:
        os.chdir(developer_dir)
        subprocess.run([sys.executable, "-B", "developer_client.py"])
        return True
    except Exception as e:
        print(f"❌ 啟動開發者客戶端失敗: {e}")
        return False

def start_lobby_client():
    """啟動玩家大廳客戶端"""
    print("🏛️ 啟動玩家大廳客戶端...")
    
    player_dir = os.path.join(get_project_root(), "player")
    client_script = os.path.join(player_dir, "lobby_client.py")
    
    if not os.path.exists(client_script):
        print(f"❌ 找不到大廳客戶端: {client_script}")
        return False
    
    try:
        os.chdir(player_dir)
        subprocess.run([sys.executable, "-B", "lobby_client.py"])
        return True
    except Exception as e:
        print(f"❌ 啟動大廳客戶端失敗: {e}")
        return False

def create_sample_game():
    """創建並上傳範例遊戲"""
    print("🎮 準備範例遊戲...")
    
    sample_dir = os.path.join(get_project_root(), "sample_games", "number_guessing")
    if not os.path.exists(sample_dir):
        print("❌ 找不到範例遊戲")
        return False
    
    print(f"📁 範例遊戲位置: {sample_dir}")
    print("📝 遊戲說明: 數字猜謎遊戲 - 雙人競賽猜測1-100之間的數字")
    print("💡 上傳說明:")
    print("   1. 啟動開發者客戶端")
    print("   2. 註冊/登入開發者帳號")
    print("   3. 選擇「上傳新遊戲」")
    print("   4. 填寫遊戲信息:")
    print(f"      - 遊戲名稱: Number Guessing Game")
    print(f"      - 遊戲簡介: 經典的數字猜謎遊戲")
    print(f"      - 遊戲類型: CLI")
    print(f"      - 最大玩家數: 2")
    print(f"      - 遊戲路徑: {sample_dir}")
    
    return True

def create_game_template():
    """創建遊戲模板"""
    print("🛠️ 啟動遊戲模板創建工具...")
    
    developer_dir = os.path.join(get_project_root(), "developer")
    template_script = os.path.join(developer_dir, "create_game_template.py")
    
    if not os.path.exists(template_script):
        print(f"❌ 找不到模板創建工具: {template_script}")
        return False
    
    try:
        os.chdir(developer_dir)
        subprocess.run([sys.executable, "create_game_template.py"])
        return True
    except Exception as e:
        print(f"❌ 啟動模板創建工具失敗: {e}")
        return False

def show_system_info():
    """顯示系統信息"""
    print("\n" + "="*60)
    print("🎮 遊戲平台系統信息")
    print("="*60)
    
    project_root = get_project_root()
    
    print(f"📁 專案路徑: {project_root}")
    print(f"🐍 Python版本: {sys.version}")
    
    print("\n📋 組件結構:")
    components = [
        ("server/", "服務器端（Developer Server + Lobby Server）"),
        ("developer/", "開發者客戶端"),
        ("player/", "玩家大廳客戶端"),
        ("sample_games/", "範例遊戲")
    ]
    
    for component, description in components:
        component_path = os.path.join(project_root, component)
        status = "✅" if os.path.exists(component_path) else "❌"
        print(f"   {status} {component:15} - {description}")
    
    print("\n🌐 網路端口:")
    print("   • 8001: Developer Server (開發者服務器)")
    print("   • 8002: Lobby Server (大廳服務器)")
    print("   • 9000+: Game Servers (遊戲服務器動態分配)")
    
    print("="*60)

def main():
    """主函數"""
    print("🎮 遊戲平台系統啟動器")
    print("="*40)
    
    while True:
        print("\n📋 請選擇操作:")
        print("1. 啟動服務器")
        print("2. 啟動開發者客戶端")
        print("3. 啟動玩家大廳客戶端")
        print("4. 範例遊戲說明")
        print("5. 創建遊戲模板")
        print("6. 系統信息")
        print("0. 退出")
        print("-"*40)
        
        try:
            choice = input("請輸入選項編號: ").strip()
            
            if choice == "0":
                print("👋 再見！")
                break
            elif choice == "1":
                start_server()
            elif choice == "2":
                start_developer_client()
            elif choice == "3":
                start_lobby_client()
            elif choice == "4":
                create_sample_game()
            elif choice == "5":
                create_game_template()
            elif choice == "6":
                show_system_info()
            else:
                print("❌ 無效選項，請重新選擇")
        
        except KeyboardInterrupt:
            print("\n\n👋 程序被中斷，退出中...")
            break
        except Exception as e:
            print(f"❌ 操作失敗: {e}")
        
        if choice != "0":
            input("\n按Enter鍵繼續...")

if __name__ == "__main__":
    main()