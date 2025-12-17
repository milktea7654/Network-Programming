#!/usr/bin/env python3
import socket
import threading
import json
import sys

class TicTacToeServer:
    def __init__(self, port, host='0.0.0.0'):
        self.port = port
        self.host = host
        self.players = {}
        self.board = [' '] * 9
        self.current_player = 'X'
        self.game_started = False
        self.game_over = False
        self.winner = None
        self.lock = threading.Lock()
        
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(2)
        print(f"[Server] Tic Tac Toe Server started on port {self.port}")
        
        try:
            while len(self.players) < 2:
                client_socket, addr = server_socket.accept()
                print(f"[Server] Player connected from {addr}")
                
                with self.lock:
                    if len(self.players) == 0:
                        symbol = 'X'
                    elif len(self.players) == 1:
                        symbol = 'O'
                    else:
                        client_socket.close()
                        continue
                    
                    self.players[symbol] = {
                        'socket': client_socket,
                        'addr': addr
                    }
                
                thread = threading.Thread(target=self.handle_client, args=(client_socket, symbol))
                thread.daemon = True
                thread.start()
            
            print("[Server] Both players connected, game starting!")
            self.game_started = True
            self.broadcast_game_state()
            
            while not self.game_over:
                threading.Event().wait(0.1)
                
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, symbol):
        try:
            self.send_message(client_socket, {
                'type': 'WELCOME',
                'symbol': symbol,
                'message': f'You are player {symbol}'
            })
            
            while not self.game_over:
                data = self.receive_message(client_socket)
                if not data:
                    break
                
                msg_type = data.get('type')
                
                if msg_type == 'MOVE':
                    self.handle_move(symbol, data.get('position'))
                    
        except Exception as e:
            print(f"[Server] Error with player {symbol}: {e}")
        finally:
            print(f"[Server] Player {symbol} disconnected")
    
    def handle_move(self, symbol, position):
        with self.lock:
            if self.game_over:
                return
            
            if self.current_player != symbol:
                return
            
            if position < 0 or position >= 9:
                return
            
            if self.board[position] != ' ':
                return
            
            self.board[position] = symbol
            
            if self.check_winner(symbol):
                self.game_over = True
                self.winner = symbol
            elif ' ' not in self.board:
                self.game_over = True
                self.winner = 'TIE'
            else:
                self.current_player = 'O' if self.current_player == 'X' else 'X'
            
            self.broadcast_game_state()
    
    def check_winner(self, symbol):
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        
        for combo in winning_combinations:
            if all(self.board[i] == symbol for i in combo):
                return True
        return False
    
    def broadcast_game_state(self):
        state = {
            'type': 'STATE',
            'board': self.board,
            'current_player': self.current_player,
            'game_over': self.game_over,
            'winner': self.winner
        }
        
        for player_info in self.players.values():
            try:
                self.send_message(player_info['socket'], state)
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
    # 支持兩種呼叫方式：
    # python server.py <port>
    # python server.py <host> <port>
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        server = TicTacToeServer(port, host)
    elif len(sys.argv) >= 2:
        port = int(sys.argv[1])
        server = TicTacToeServer(port)
    else:
        port = 9001
        server = TicTacToeServer(port)
    server.start()
