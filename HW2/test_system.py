"""
簡單的測試腳本 - 測試 Database Server 和 Lobby Server 的基本功能
"""
import socket
import time
from protocol import send_message, recv_message
import hashlib

DB_HOST = 'localhost'
DB_PORT = 10001
LOBBY_HOST = 'localhost'
LOBBY_PORT = 10002


def test_database():
    """測試資料庫伺服器"""
    print("=== Testing Database Server ===\n")
    
    try:
        # 連接到資料庫伺服器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((DB_HOST, DB_PORT))
        print(f"✓ Connected to Database Server at {DB_HOST}:{DB_PORT}")
        
        # 測試創建使用者
        print("\n1. Creating test user...")
        password_hash = hashlib.sha256("testpass".encode()).hexdigest()
        request = {
            'collection': 'User',
            'action': 'create',
            'data': {
                'name': 'testuser',
                'email': 'test@example.com',
                'passwordHash': password_hash
            }
        }
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            user_id = response.get('id')
            print(f"✓ User created with ID: {user_id}")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        # 關閉連接
        sock.close()
        
        # 測試查詢
        print("\n2. Querying users...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((DB_HOST, DB_PORT))
        
        request = {
            'collection': 'User',
            'action': 'query',
            'data': {}
        }
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            users = response.get('data', [])
            print(f"✓ Found {len(users)} user(s):")
            for user in users:
                print(f"  - {user['name']} ({user['email']})")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        sock.close()
        
        print("\n✓ Database Server test completed!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Database Server test failed: {e}\n")
        return False


def test_lobby():
    """測試大廳伺服器"""
    print("=== Testing Lobby Server ===\n")
    
    try:
        # 連接到大廳伺服器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((LOBBY_HOST, LOBBY_PORT))
        print(f"✓ Connected to Lobby Server at {LOBBY_HOST}:{LOBBY_PORT}")
        
        # 測試註冊
        print("\n1. Registering user...")
        request = {
            'action': 'register',
            'data': {
                'name': 'player1',
                'email': 'player1@test.com',
                'password': '123456'
            }
        }
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            print(f"✓ User registered successfully")
        else:
            print(f"Note: {response.get('error')} (may already exist)")
        
        # 測試登入
        print("\n2. Logging in...")
        request = {
            'action': 'login',
            'data': {
                'name': 'player1',
                'password': '123456'
            }
        }
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            user_id = response.get('userId')
            username = response.get('name')
            print(f"✓ Logged in as {username} (ID: {user_id})")
        else:
            print(f"✗ Login failed: {response.get('error')}")
            sock.close()
            return False
        
        # 測試列出線上使用者
        print("\n3. Listing online users...")
        request = {'action': 'list_online', 'data': {}}
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            users = response.get('users', [])
            print(f"✓ Online users ({len(users)}):")
            for user in users:
                print(f"  - {user['name']}")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        # 測試創建房間
        print("\n4. Creating room...")
        request = {
            'action': 'create_room',
            'data': {
                'name': 'Test Room',
                'visibility': 'public'
            }
        }
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            room_id = response.get('roomId')
            print(f"✓ Room created with ID: {room_id}")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        # 測試列出房間
        print("\n5. Listing rooms...")
        request = {'action': 'list_rooms', 'data': {}}
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            rooms = response.get('rooms', [])
            print(f"✓ Rooms ({len(rooms)}):")
            for room in rooms:
                print(f"  - [{room['id']}] {room['name']} ({room['visibility']}) - {room['memberCount']}/2 players")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        # 測試登出
        print("\n6. Logging out...")
        request = {'action': 'logout', 'data': {}}
        send_message(sock, request)
        response = recv_message(sock)
        
        if response.get('success'):
            print("✓ Logged out successfully")
        else:
            print(f"✗ Failed: {response.get('error')}")
        
        sock.close()
        
        print("\n✓ Lobby Server test completed!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Lobby Server test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*50)
    print("  Tetris Battle - System Test")
    print("="*50 + "\n")
    
    print("This script will test the basic functionality of:")
    print("  1. Database Server (port 10001)")
    print("  2. Lobby Server (port 10002)")
    print("\nMake sure both servers are running before continuing.\n")
    
    input("Press Enter to start testing...")
    print()
    
    # 測試資料庫伺服器
    db_ok = test_database()
    time.sleep(1)
    
    # 測試大廳伺服器
    lobby_ok = test_lobby()
    
    # 總結
    print("="*50)
    print("  Test Summary")
    print("="*50)
    print(f"Database Server: {'✓ PASS' if db_ok else '✗ FAIL'}")
    print(f"Lobby Server:    {'✓ PASS' if lobby_ok else '✗ FAIL'}")
    print("="*50)
    
    if db_ok and lobby_ok:
        print("\n✓ All tests passed! System is ready.")
        print("\nYou can now:")
        print("  1. Run 'python3 lobby_client.py' to start the client")
        print("  2. Register/login and create rooms")
        print("  3. Start a game with 2 players")
    else:
        print("\n✗ Some tests failed. Please check the servers.")


if __name__ == '__main__':
    main()
