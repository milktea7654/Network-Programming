import socket
import threading
import time
import sys
from datetime import datetime
from protocol import send_message, recv_message, ProtocolError
from tetris_logic import TetrisGame
import random

LOBBY_HOST = 'localhost'
LOBBY_PORT = 10002


class GameServer:
    def __init__(self, port, room_id):
        self.port = port
        self.room_id = room_id
        self.running = False
        self.players = {}
        self.spectators = {}
        self.seed = random.randint(0, 2**31 - 1)
        self.drop_interval = 500 
        self.game_start_time = None
        self.lock = threading.Lock()
        self.game_started = False
        self.game_ended = False
    def start(self):
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.port))
        server_socket.listen(5)
        print(f"[Game Server] Room {self.room_id} listening on port {self.port}")
        game_thread = threading.Thread(target=self.game_loop)
        game_thread.daemon = True
        game_thread.start()
        try:
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    print(f"[Game] New connection from {addr}")
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[Game] Accept error: {e}")
        except KeyboardInterrupt:
            print("\n[Game Server] Shutting down...")
        finally:
            server_socket.close()
    def handle_client(self, client_socket, addr):
        user_id = None
        is_spectator = False
        try:
            hello = recv_message(client_socket)
            if hello.get('type') != 'HELLO':
                send_message(client_socket, {'type': 'ERROR', 'message': 'Expected HELLO'})
                return
            user_id = hello.get('userId')
            username = hello.get('username', str(user_id))
            room_id = hello.get('roomId')
            is_spectator = hello.get('spectate', False)
            if room_id != self.room_id:
                send_message(client_socket, {'type': 'ERROR', 'message': 'Invalid room'})
                return
            if is_spectator:
                with self.lock:
                    self.spectators[user_id] = {
                        'socket': client_socket,
                        'name': username
                    }
                    print(f"[Game] Spectator {username} joined")
                send_message(client_socket, {
                    'type': 'WELCOME',
                    'role': 'SPECTATOR',
                    'seed': self.seed,
                    'bagRule': '7bag',
                    'gravityPlan': {
                        'mode': 'fixed',
                        'dropMs': self.drop_interval
                    }
                })
                while self.running:
                    time.sleep(1)
                return
            with self.lock:
                if len(self.players) >= 2:
                    send_message(client_socket, {'type': 'ERROR', 'message': 'Game full'})
                    return
                role = 'P1' if len(self.players) == 0 else 'P2'
                game = TetrisGame(seed=self.seed)
                self.players[user_id] = {
                    'socket': client_socket,
                    'role': role,
                    'game': game,
                    'username': username,
                    'ready': False
                }
                print(f"[Game] Player {username} (ID: {user_id}) joined as {role}")
            send_message(client_socket, {
                'type': 'WELCOME',
                'role': role,
                'seed': self.seed,
                'bagRule': '7bag',
                'gravityPlan': {
                    'mode': 'fixed',
                    'dropMs': self.drop_interval
                }
            })
            with self.lock:
                self.players[user_id]['ready'] = True
                if len(self.players) == 2 and all(p['ready'] for p in self.players.values()):
                    self.game_started = True
                    self.game_start_time = datetime.now()
                    print("[Game] Game started!")
            while self.running:
                msg = recv_message(client_socket)
                self.handle_player_message(user_id, msg)
        except (ConnectionError, ProtocolError) as e:
            print(f"[Game] Connection error from {addr}: {e}")
        except Exception as e:
            print(f"[Game] Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if user_id:
                with self.lock:
                    if is_spectator and user_id in self.spectators:
                        del self.spectators[user_id]
                        print(f"[Game] Spectator {user_id} disconnected")
                    elif user_id in self.players:
                        del self.players[user_id]
                        print(f"[Game] Player {user_id} disconnected")
                        if len(self.players) < 2 and self.game_started and not self.game_ended:
                            print("[Game] Player disconnected. Not enough players. Ending game...")
                            self.end_game_insufficient_players()
            client_socket.close()
    def handle_player_message(self, user_id, msg):
        msg_type = msg.get('type')
        if msg_type == 'INPUT':
            action = msg.get('action')
            with self.lock:
                if user_id not in self.players:
                    return
                game = self.players[user_id]['game']
                if game.game_over:
                    return
                if action == 'LEFT':
                    game.move_left()
                elif action == 'RIGHT':
                    game.move_right()
                elif action == 'CW':
                    game.rotate_cw()
                elif action == 'CCW':
                    game.rotate_ccw()
                elif action == 'SOFT_DROP':
                    game.soft_drop()
                elif action == 'HARD_DROP':
                    game.hard_drop()
                elif action == 'HOLD':
                    game.hold()
                self.broadcast_snapshot(user_id)
                self.check_game_end()
    def game_loop(self):
        last_drop_time = time.time()
        while self.running:
            time.sleep(0.05)  
            if not self.game_started or self.game_ended:
                continue
            current_time = time.time()

            with self.lock:
                if len(self.players) < 2 and self.game_started and not self.game_ended:
                    print("[Game] Not enough players during game loop. Ending game...")
                    self.end_game_insufficient_players()
                    continue
            if current_time - last_drop_time >= self.drop_interval / 1000.0:
                last_drop_time = current_time
                with self.lock:
                    for user_id, player in self.players.items():
                        game = player['game']
                        if not game.game_over:
                            game.soft_drop()
                            self.broadcast_snapshot(user_id)
                    self.check_game_end()
    def broadcast_snapshot(self, user_id):
        if user_id not in self.players:
            return
        player = self.players[user_id]
        game = player['game']
        state = game.get_state()
        snapshot = {
            'type': 'SNAPSHOT',
            'userId': user_id,
            'username': player['username'],
            'role': player['role'],
            'boardRLE': game.compress_board(),
            'active': state['current'],
            'hold': state['hold'],
            'next': state['next'],
            'score': state['score'],
            'lines': state['lines'],
            'level': state['level'],
            'gameOver': state['gameOver'],
            'timestamp': time.time()
        }
        for pid, p in self.players.items():
            try:
                send_message(p['socket'], snapshot)
            except:
                pass
        for sid, s in self.spectators.items():
            try:
                send_message(s['socket'], snapshot)
            except:
                pass
    def check_game_end(self):
        if self.game_ended:
            return
        if len(self.players) < 2:
            return
        game_over_count = sum(1 for p in self.players.values() if p['game'].game_over)
        if game_over_count > 0:
            self.game_ended = True
            results = []
            winner_id = None
            max_score = -1
            for user_id, player in self.players.items():
                game = player['game']
                result = {
                    'userId': user_id,
                    'score': game.score,
                    'lines': game.lines_cleared,
                    'maxCombo': 0,  
                    'gameOver': game.game_over
                }
                results.append(result)
                if game.score > max_score:
                    max_score = game.score
                    winner_id = user_id
            end_msg = {
                'type': 'GAME_END',
                'results': results,
                'winner': winner_id
            }

            for player in self.players.values():
                try:
                    send_message(player['socket'], end_msg)
                except:
                    pass

            for spectator in self.spectators.values():
                try:
                    send_message(spectator['socket'], end_msg)
                except:
                    pass

            self.notify_lobby_game_end(results)
            print(f"[Game] Game ended. Winner: {winner_id}")

            threading.Timer(5.0, self.shutdown).start()
    def end_game_insufficient_players(self):
        if self.game_ended:
            return
        self.game_ended = True

        results = []
        winner_id = None
        for user_id, player in self.players.items():
            game = player['game']
            result = {
                'userId': user_id,
                'score': game.score,
                'lines': game.lines_cleared,
                'maxCombo': 0,
                'gameOver': False
            }
            results.append(result)
            winner_id = user_id

        end_msg = {
            'type': 'GAME_END',
            'results': results,
            'winner': winner_id,
            'reason': 'insufficient_players'
        }

        for player in self.players.values():
            try:
                send_message(player['socket'], end_msg)
            except:
                pass

        for spectator in self.spectators.values():
            try:
                send_message(spectator['socket'], end_msg)
            except:
                pass

        self.notify_lobby_game_end(results)
        print(f"[Game] Game ended due to insufficient players. Winner: {winner_id}")

        threading.Timer(2.0, self.shutdown).start()
    def notify_lobby_game_end(self, results):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LOBBY_HOST, LOBBY_PORT))
            request = {
                'action': 'game_ended',
                'data': {
                    'roomId': self.room_id,
                    'startAt': self.game_start_time.isoformat() if self.game_start_time else datetime.now().isoformat(),
                    'results': results
                }
            }
            send_message(sock, request)
            recv_message(sock)
            sock.close()
        except Exception as e:
            print(f"[Game] Failed to notify lobby: {e}")
    def shutdown(self):
        self.running = False
        print("[Game Server] Shutting down...")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 game_server.py <port> <room_id>")
        sys.exit(1)
    port = int(sys.argv[1])
    room_id = int(sys.argv[2])
    server = GameServer(port, room_id)
    server.start()
