#!/usr/bin/env python3
import socket
import threading
import json
import sys
import random
import time

class SnakeServer:
    def __init__(self, port):
        self.port = port
        self.host = '0.0.0.0'
        self.players = {}
        self.food = []
        self.game_started = False
        self.game_over = False
        self.lock = threading.Lock()
        
        self.grid_width = 30
        self.grid_height = 20
        self.max_players = 4
        self.colors = ['red', 'blue', 'green', 'yellow']
        self.spawn_positions = [
            (5, 5), (25, 5), (5, 15), (25, 15)
        ]
        
        self.generate_food(5)
        
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.max_players)
        print(f"[Server] Multiplayer Snake Server started on port {self.port}")
        
        threading.Thread(target=self.accept_connections, args=(server_socket,), daemon=True).start()
        threading.Thread(target=self.game_loop, daemon=True).start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
        finally:
            server_socket.close()
    
    def accept_connections(self, server_socket):
        while len(self.players) < self.max_players:
            try:
                client_socket, addr = server_socket.accept()
                print(f"[Server] Player connected from {addr}")
                
                with self.lock:
                    player_id = len(self.players) + 1
                    if player_id > self.max_players:
                        client_socket.close()
                        continue
                    
                    color = self.colors[player_id - 1]
                    spawn_pos = self.spawn_positions[player_id - 1]
                    
                    self.players[player_id] = {
                        'socket': client_socket,
                        'addr': addr,
                        'snake': [spawn_pos, (spawn_pos[0]-1, spawn_pos[1])],
                        'direction': 'RIGHT',
                        'next_direction': 'RIGHT',
                        'color': color,
                        'score': 0,
                        'alive': True
                    }
                
                thread = threading.Thread(target=self.handle_client, args=(client_socket, player_id))
                thread.daemon = True
                thread.start()
                
                if len(self.players) >= 2 and not self.game_started:
                    self.game_started = True
                    print("[Server] Game starting!")
                    
            except Exception as e:
                print(f"[Server] Accept error: {e}")
                break
    
    def handle_client(self, client_socket, player_id):
        try:
            self.send_message(client_socket, {
                'type': 'WELCOME',
                'player_id': player_id,
                'color': self.players[player_id]['color']
            })
            
            while not self.game_over:
                data = self.receive_message(client_socket)
                if not data:
                    break
                
                msg_type = data.get('type')
                
                if msg_type == 'DIRECTION':
                    direction = data.get('direction')
                    with self.lock:
                        if player_id in self.players and self.players[player_id]['alive']:
                            current = self.players[player_id]['direction']
                            opposites = {'UP': 'DOWN', 'DOWN': 'UP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
                            if direction != opposites.get(current):
                                self.players[player_id]['next_direction'] = direction
                                
        except Exception as e:
            print(f"[Server] Error with player {player_id}: {e}")
        finally:
            print(f"[Server] Player {player_id} disconnected")
            with self.lock:
                if player_id in self.players:
                    self.players[player_id]['alive'] = False
    
    def game_loop(self):
        while not self.game_started:
            time.sleep(0.1)
        
        print("[Server] Game loop started")
        
        while not self.game_over:
            time.sleep(0.15)
            
            with self.lock:
                alive_count = sum(1 for p in self.players.values() if p['alive'])
                if alive_count <= 1 and len(self.players) >= 2:
                    self.game_over = True
                    self.broadcast_game_over()
                    break
                
                for player_id, player in self.players.items():
                    if not player['alive']:
                        continue
                    
                    player['direction'] = player['next_direction']
                    
                    head = player['snake'][0]
                    direction = player['direction']
                    
                    if direction == 'UP':
                        new_head = (head[0], head[1] - 1)
                    elif direction == 'DOWN':
                        new_head = (head[0], head[1] + 1)
                    elif direction == 'LEFT':
                        new_head = (head[0] - 1, head[1])
                    elif direction == 'RIGHT':
                        new_head = (head[0] + 1, head[1])
                    
                    if (new_head[0] < 0 or new_head[0] >= self.grid_width or
                        new_head[1] < 0 or new_head[1] >= self.grid_height):
                        player['alive'] = False
                        continue
                    
                    if new_head in player['snake']:
                        player['alive'] = False
                        continue
                    
                    for other_id, other in self.players.items():
                        if other_id != player_id and other['alive']:
                            if new_head in other['snake']:
                                player['alive'] = False
                                break
                    
                    if not player['alive']:
                        continue
                    
                    player['snake'].insert(0, new_head)
                    
                    if new_head in self.food:
                        self.food.remove(new_head)
                        player['score'] += 10
                        self.generate_food(1)
                    else:
                        player['snake'].pop()
                
                self.broadcast_game_state()
    
    def generate_food(self, count):
        for _ in range(count):
            while True:
                pos = (random.randint(0, self.grid_width-1), random.randint(0, self.grid_height-1))
                
                occupied = False
                for player in self.players.values():
                    if pos in player['snake']:
                        occupied = True
                        break
                
                if not occupied and pos not in self.food:
                    self.food.append(pos)
                    break
    
    def broadcast_game_state(self):
        players_data = {}
        for pid, player in self.players.items():
            players_data[pid] = {
                'snake': player['snake'],
                'color': player['color'],
                'score': player['score'],
                'alive': player['alive']
            }
        
        state = {
            'type': 'STATE',
            'players': players_data,
            'food': self.food,
            'grid_width': self.grid_width,
            'grid_height': self.grid_height
        }
        
        for player in self.players.values():
            try:
                self.send_message(player['socket'], state)
            except:
                pass
    
    def broadcast_game_over(self):
        scores = [(pid, p['score']) for pid, p in self.players.items()]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        message = {
            'type': 'GAME_OVER',
            'rankings': scores
        }
        
        for player in self.players.values():
            try:
                self.send_message(player['socket'], message)
            except:
                pass
    
    def send_message(self, sock, data):
        try:
            message = json.dumps(data).encode('utf-8')
            sock.sendall(len(message).to_bytes(4, 'big') + message)
        except:
            pass
    
    def receive_message(self, sock):
        try:
            length_bytes = sock.recv(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, 'big')
            data = b''
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            return json.loads(data.decode('utf-8'))
        except:
            return None

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9002
    server = SnakeServer(port)
    server.start()
