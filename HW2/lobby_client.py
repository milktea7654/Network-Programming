"""
Lobby Client - 大廳客戶端 (CLI)
"""
import socket
import threading
import time
import subprocess
from protocol import send_message, recv_message, ProtocolError

LOBBY_HOST = 'localhost'  # 或改為課程機的 IP
LOBBY_PORT = 10002


class LobbyClient:
    def __init__(self, host=LOBBY_HOST, port=LOBBY_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.logged_in = False
        self.user_id = None
        self.username = None
        self.in_room = False
        self.current_room_id = None
    
    def connect(self):
        """連接到大廳伺服器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[Connected to Lobby Server at {self.host}:{self.port}]")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_request(self, action, data=None):
        """發送請求並接收回應"""
        try:
            request = {'action': action, 'data': data or {}}
            send_message(self.socket, request)
            response = recv_message(self.socket)
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def register(self):
        """註冊"""
        print("\n=== Register ===")
        name = input("Username: ").strip()
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        response = self.send_request('register', {
            'name': name,
            'email': email,
            'password': password
        })
        
        if response.get('success'):
            print("✓ Registration successful!")
        else:
            print(f"✗ Registration failed: {response.get('error')}")
    
    def login(self):
        """登入"""
        print("\n=== Login ===")
        name = input("Username: ").strip()
        password = input("Password: ").strip()
        
        response = self.send_request('login', {
            'name': name,
            'password': password
        })
        
        if response.get('success'):
            self.logged_in = True
            self.user_id = response.get('userId')
            self.username = response.get('name')
            print(f"✓ Welcome, {self.username}!")
        else:
            print(f"✗ Login failed: {response.get('error')}")
    
    def logout(self):
        """登出"""
        response = self.send_request('logout')
        
        if response.get('success'):
            self.logged_in = False
            self.user_id = None
            self.username = None
            print("✓ Logged out")
        else:
            print(f"✗ Logout failed: {response.get('error')}")
    
    def list_online_users(self):
        """列出線上使用者"""
        response = self.send_request('list_online')
        
        if response.get('success'):
            users = response.get('users', [])
            print(f"\n=== Online Users ({len(users)}) ===")
            for user in users:
                status = "(In Room)" if user.get('inRoom') else "(Available)"
                print(f"  [{user['userId']}] {user['name']} {status}")
        else:
            print(f"✗ Failed to list users: {response.get('error')}")
    
    def list_rooms(self):
        """列出房間"""
        response = self.send_request('list_rooms')
        
        if response.get('success'):
            rooms = response.get('rooms', [])
            print(f"\n=== Rooms ({len(rooms)}) ===")
            for room in rooms:
                visibility = room.get('visibility', 'public')
                status = room.get('status', 'idle')
                member_count = room.get('memberCount', 0)
                print(f"  [{room['id']}] {room['name']} | {visibility} | {status} | {member_count}/2 players")
        else:
            print(f"✗ Failed to list rooms: {response.get('error')}")
    
    def create_room(self):
        """創建房間"""
        print("\n=== Create Room ===")
        name = input("Room name: ").strip()
        visibility = input("Visibility (public/private) [public]: ").strip() or 'public'
        
        response = self.send_request('create_room', {
            'name': name,
            'visibility': visibility
        })
        
        if response.get('success'):
            self.in_room = True
            self.current_room_id = response.get('roomId')
            print(f"✓ Room created! Room ID: {self.current_room_id}")
        else:
            print(f"✗ Failed to create room: {response.get('error')}")
    
    def join_room(self):
        """加入房間"""
        self.list_rooms()
        print("\n=== Join Room ===")
        room_id = input("Enter room ID: ").strip()
        
        try:
            room_id = int(room_id)
        except ValueError:
            print("✗ Invalid room ID")
            return
        
        response = self.send_request('join_room', {'roomId': room_id})
        
        if response.get('success'):
            self.in_room = True
            self.current_room_id = room_id
            print(f"✓ Joined room {room_id}")
        else:
            print(f"✗ Failed to join room: {response.get('error')}")
    
    def leave_room(self):
        """離開房間"""
        response = self.send_request('leave_room')
        
        if response.get('success'):
            self.in_room = False
            self.current_room_id = None
            print("✓ Left room")
        else:
            print(f"✗ Failed to leave room: {response.get('error')}")
    
    def invite_user(self):
        """邀請使用者"""
        self.list_online_users()
        print("\n=== Invite User ===")
        user_id = input("Enter user ID to invite: ").strip()
        
        try:
            user_id = int(user_id)
        except ValueError:
            print("✗ Invalid user ID")
            return
        
        response = self.send_request('invite_user', {'targetUserId': user_id})
        
        if response.get('success'):
            print("✓ Invitation sent")
        else:
            print(f"✗ Failed to invite: {response.get('error')}")
    
    def list_invitations(self):
        """列出邀請"""
        response = self.send_request('list_invitations')
        
        if response.get('success'):
            invites = response.get('invitations', [])
            print(f"\n=== Invitations ({len(invites)}) ===")
            for i, invite in enumerate(invites):
                print(f"  {i+1}. From {invite['from_user_name']} to room '{invite['room_name']}' (ID: {invite['room_id']})")
            return invites
        else:
            print(f"✗ Failed to list invitations: {response.get('error')}")
            return []
    
    def accept_invitation(self):
        """接受邀請"""
        invites = self.list_invitations()
        
        if not invites:
            print("No invitations")
            return
        
        choice = input("\nEnter invitation number to accept (or 0 to cancel): ").strip()
        
        try:
            choice = int(choice)
            if choice == 0:
                return
            if 1 <= choice <= len(invites):
                invite = invites[choice - 1]
                response = self.send_request('accept_invitation', {'roomId': invite['room_id']})
                
                if response.get('success'):
                    self.in_room = True
                    self.current_room_id = invite['room_id']
                    print(f"✓ Joined room '{invite['room_name']}'")
                else:
                    print(f"✗ Failed to accept invitation: {response.get('error')}")
            else:
                print("✗ Invalid choice")
        except ValueError:
            print("✗ Invalid input")
    
    def start_game(self):
        """開始遊戲"""
        if not self.in_room:
            print("✗ You are not in a room")
            return
        
        print("\nStarting game...")
        response = self.send_request('start_game')
        
        if response.get('success'):
            game_port = response.get('gamePort')
            players = response.get('players', [])
            player_names = response.get('playerNames', [])
            
            print(f"✓ Game server started on port {game_port}")
            print(f"  Players: {', '.join(player_names)}")
            
            # 啟動遊戲客戶端
            print("\nLaunching game client...")
            try:
                # 在本地啟動遊戲客戶端
                subprocess.Popen([
                    'python3', 'game_client.py',
                    self.host,  # 使用大廳伺服器的主機（遊戲伺服器在同一台機器）
                    str(game_port),
                    str(self.user_id),
                    str(self.current_room_id)
                ])
                print("Game client launched! The game window should appear shortly.")
            except Exception as e:
                print(f"✗ Failed to launch game client: {e}")
                print(f"You can manually run: python3 game_client.py {self.host} {game_port} {self.user_id} {self.current_room_id}")
        else:
            print(f"✗ Failed to start game: {response.get('error')}")
    
    def main_menu(self):
        """主選單"""
        while self.connected:
            if not self.logged_in:
                print("\n=== Main Menu ===")
                print("1. Register")
                print("2. Login")
                print("3. Quit")
                
                choice = input("\nChoice: ").strip()
                
                if choice == '1':
                    self.register()
                elif choice == '2':
                    self.login()
                elif choice == '3':
                    break
            else:
                if self.in_room:
                    print(f"\n=== Lobby (In Room {self.current_room_id}) ===")
                    print("1. Leave Room")
                    print("2. Invite User")
                    print("3. Start Game (Host only)")
                    print("4. Logout")
                    
                    choice = input("\nChoice: ").strip()
                    
                    if choice == '1':
                        self.leave_room()
                    elif choice == '2':
                        self.invite_user()
                    elif choice == '3':
                        self.start_game()
                    elif choice == '4':
                        self.logout()
                else:
                    print(f"\n=== Lobby (Logged in as {self.username}) ===")
                    print("1. List Online Users")
                    print("2. List Rooms")
                    print("3. Create Room")
                    print("4. Join Room")
                    print("5. View Invitations")
                    print("6. Logout")
                    
                    choice = input("\nChoice: ").strip()
                    
                    if choice == '1':
                        self.list_online_users()
                    elif choice == '2':
                        self.list_rooms()
                    elif choice == '3':
                        self.create_room()
                    elif choice == '4':
                        self.join_room()
                    elif choice == '5':
                        self.accept_invitation()
                    elif choice == '6':
                        self.logout()
        
        # 清理
        if self.socket:
            self.socket.close()
        print("\nGoodbye!")
    
    def run(self):
        """執行客戶端"""
        if self.connect():
            self.main_menu()


if __name__ == '__main__':
    import sys
    
    host = LOBBY_HOST
    port = LOBBY_PORT
    
    # 允許從命令列指定伺服器
    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    
    client = LobbyClient(host, port)
    client.run()
