import socket
import threading
import time
import subprocess
from protocol import send_message, recv_message, ProtocolError

LOBBY_HOST = 'localhost'
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
        self.room_check_thread = None
        self.stop_checking = False
        self.game_launched = False
    def connect(self):
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
        try:
            request = {'action': action, 'data': data or {}}
            send_message(self.socket, request)
            response = recv_message(self.socket)
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            return {'success': False, 'error': str(e)}
    def register(self):
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
        response = self.send_request('logout')
        if response.get('success'):
            self.logged_in = False
            self.user_id = None
            self.username = None
            print("✓ Logged out")
        else:
            print(f"✗ Logout failed: {response.get('error')}")
    def list_online_users(self):
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

            self.start_room_check()
        else:
            print(f"✗ Failed to create room: {response.get('error')}")
    def join_room(self):
        print("\n=== Join Room ===")
        room_id = input("Room ID: ").strip()
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

            self.start_room_check()
        else:
            print(f"✗ Failed to join room: {response.get('error')}")
    def leave_room(self):
        response = self.send_request('leave_room')
        if response.get('success'):
            self.in_room = False
            self.current_room_id = None
            self.stop_checking = True
            self.game_launched = False
            print("✓ Left room")
        else:
            print(f"✗ Failed to leave room: {response.get('error')}")
    def start_room_check(self):
        if self.room_check_thread and self.room_check_thread.is_alive():
            return
        self.stop_checking = False
        self.room_check_thread = threading.Thread(target=self.check_room_status, daemon=True)
        self.room_check_thread.start()
    def check_room_status(self):
        last_status = None
        while not self.stop_checking and self.in_room:
            try:

                response = self.send_request('list_rooms')
                if response.get('success'):
                    rooms = response.get('rooms', [])
                    current_room = next((r for r in rooms if r['id'] == self.current_room_id), None)
                    if current_room:
                        status = current_room.get('status')

                        if status in ['idle', 'waiting'] and last_status == 'playing':
                            print("\n\n🎮 Game ended. You can start a new game.")
                            self.game_launched = False

                        if status == 'playing' and last_status != 'playing' and not self.game_launched:
                            print("\n\n🎮 Game is starting! Launching game client...")

                            self.game_launched = True

                            game_info = self.send_request('get_game_info', {'roomId': self.current_room_id})
                            if game_info.get('success'):
                                game_port = game_info.get('gamePort')
                                try:
                                    subprocess.Popen([
                                        'python3', 'game_client.py',
                                        self.host,
                                        str(game_port),
                                        str(self.user_id),
                                        str(self.current_room_id),
                                        self.username
                                    ])
                                    print("✓ Game client launched!")
                                except Exception as e:
                                    print(f"✗ Failed to launch: {e}")
                                    print(f"Manual: python3 game_client.py {self.host} {game_port} {self.user_id} {self.current_room_id} {self.username}")
                        last_status = status
                time.sleep(2)
            except Exception as e:

                time.sleep(2)
    def invite_user(self):
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

                    self.start_room_check()
                else:
                    print(f"✗ Failed to accept invitation: {response.get('error')}")
            else:
                print("✗ Invalid choice")
        except ValueError:
            print("✗ Invalid input")
    def spectate_game(self):
        self.list_rooms()
        print("\n=== Spectate Game ===")
        room_id = input("Enter room ID to spectate: ").strip()
        try:
            room_id = int(room_id)
        except ValueError:
            print("✗ Invalid room ID")
            return
        print(f"\nConnecting to spectate room {room_id}...")
        response = self.send_request('spectate_room', {'roomId': room_id})
        if response.get('success'):
            game_port = response.get('gamePort')
            player_names = response.get('playerNames', [])
            print(f"✓ Connected to game on port {game_port}")
            print(f"  Players: {', '.join(player_names)}")

            print("\nLaunching spectator client...")
            try:
                subprocess.Popen([
                    'python3', 'game_client.py',
                    self.host,
                    str(game_port),
                    str(self.user_id),
                    str(room_id),
                    self.username,
                    'spectate'
                ])
                print("Spectator client launched! The game window should appear shortly.")
            except Exception as e:
                print(f"✗ Failed to launch spectator client: {e}")
                print(f"You can manually run: python3 game_client.py {self.host} {game_port} {self.user_id} {room_id} {self.username} spectate")
        else:
            print(f"✗ Failed to spectate: {response.get('error')}")
    def start_game(self):
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

            print("\nLaunching game client...")
            try:

                subprocess.Popen([
                    'python3', 'game_client.py',
                    self.host,
                    str(game_port),
                    str(self.user_id),
                    str(self.current_room_id),
                    self.username
                ])
                print("Game client launched! The game window should appear shortly.")

                self.game_launched = True
            except Exception as e:
                print(f"✗ Failed to launch game client: {e}")
                print(f"You can manually run: python3 game_client.py {self.host} {game_port} {self.user_id} {self.current_room_id} {self.username}")
        else:
            print(f"✗ Failed to start game: {response.get('error')}")
    def main_menu(self):
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
                    print("6. Spectate Game")
                    print("7. Logout")
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
                        self.spectate_game()
                    elif choice == '7':
                        self.logout()

        if self.socket:
            self.socket.close()
        print("\nGoodbye!")
    def run(self):
        if self.connect():
            self.main_menu()


if __name__ == '__main__':
    import sys
    host = LOBBY_HOST
    port = LOBBY_PORT

    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    client = LobbyClient(host, port)
    client.run()
