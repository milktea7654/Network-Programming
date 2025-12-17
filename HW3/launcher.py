import os
import sys
import subprocess
import time
import signal

def get_project_root():
    return os.path.dirname(os.path.abspath(__file__))

def start_server():
    print("啟動遊戲平台服務器...")
    
    server_dir = os.path.join(get_project_root(), "server")
    main_server = os.path.join(server_dir, "main_server.py")
    
    if not os.path.exists(main_server):
        print(f"找不到主服務器文件: {main_server}")
        return False
    
    try:
        os.chdir(server_dir)
        process = subprocess.Popen([sys.executable, "main_server.py"])
        print(f"服務器已啟動 (PID: {process.pid})")
        print("服務器地址:")
        print("   Developer Server: localhost:8001")
        print("   Lobby Server:     localhost:8002")
        print("\n請按 Ctrl+C 停止服務器")
        
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n正在停止服務器...")
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
            print("服務器已停止")
        
        return True
    except Exception as e:
        print(f"啟動服務器失敗: {e}")
        return False

def start_developer_client():
    print("啟動開發者客戶端...")
    
    developer_dir = os.path.join(get_project_root(), "developer")
    client_script = os.path.join(developer_dir, "developer_client.py")
    
    if not os.path.exists(client_script):
        print(f"找不到開發者客戶端: {client_script}")
        return False
    
    try:
        os.chdir(developer_dir)
        subprocess.run([sys.executable, "-B", "developer_client.py"])
        return True
    except Exception as e:
        print(f"啟動開發者客戶端失敗: {e}")
        return False

def start_lobby_client():
    print("啟動玩家大廳客戶端...")
    
    player_dir = os.path.join(get_project_root(), "player")
    client_script = os.path.join(player_dir, "lobby_client.py")
    
    if not os.path.exists(client_script):
        print(f"找不到大廳客戶端: {client_script}")
        return False
    
    try:
        os.chdir(player_dir)
        subprocess.run([sys.executable, "-B", "lobby_client.py"])
        return True
    except Exception as e:
        print(f"啟動大廳客戶端失敗: {e}")
        return False

def main():
    print("遊戲平台系統啟動器")
    print("="*40)
    
    while True:
        print("\n請選擇操作:")
        print("1. 啟動服務器")
        print("2. 啟動開發者客戶端")
        print("3. 啟動玩家大廳客戶端")
        print("0. 退出")
        print("-"*40)
        
        try:
            choice = input("請輸入選項編號: ").strip()
            
            if choice == "0":
                print("再見！")
                break
            elif choice == "1":
                start_server()
            elif choice == "2":
                start_developer_client()
            elif choice == "3":
                start_lobby_client()
            else:
                print("無效選項，請重新選擇")
        
        except KeyboardInterrupt:
            print("\n\n程序被中斷，退出中...")
            break
        except Exception as e:
            print(f"操作失敗: {e}")
        
        if choice != "0":
            input("\n按Enter鍵繼續...")

if __name__ == "__main__":
    main()