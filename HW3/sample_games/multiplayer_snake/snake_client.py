#!/usr/bin/env python3
import socket
import threading
import json
import sys
import tkinter as tk
from tkinter import messagebox

class SnakeClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.my_player_id = None
        self.my_color = None
        self.players = {}
        self.food = []
        self.grid_width = 30
        self.grid_height = 20
        self.cell_size = 20
        self.game_over = False
        
        self.root = tk.Tk()
        self.root.title("Multiplayer Snake")
        canvas_width = self.grid_width * self.cell_size
        canvas_height = self.grid_height * self.cell_size
        self.root.geometry(f"{canvas_width + 250}x{canvas_height + 100}")
        self.root.resizable(False, False)
        
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(left_frame, text="Connecting...", font=('Arial', 12))
        self.status_label.pack(pady=5)
        
        self.canvas = tk.Canvas(
            left_frame,
            width=canvas_width,
            height=canvas_height,
            bg='black',
            highlightthickness=1,
            highlightbackground='white'
        )
        self.canvas.pack()
        
        right_frame = tk.Frame(main_frame, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(right_frame, text=" Scoreboard", font=('Arial', 14, 'bold')).pack(pady=10)
        
        self.score_frame = tk.Frame(right_frame)
        self.score_frame.pack(fill=tk.BOTH, expand=True)
        
        self.score_labels = {}
        
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=5)
        tk.Label(controls_frame, text=" Controls: ↑↓←→ or WASD", font=('Arial', 10)).pack()
        
        self.root.bind('<Up>', lambda e: self.change_direction('UP'))
        self.root.bind('<Down>', lambda e: self.change_direction('DOWN'))
        self.root.bind('<Left>', lambda e: self.change_direction('LEFT'))
        self.root.bind('<Right>', lambda e: self.change_direction('RIGHT'))
        self.root.bind('w', lambda e: self.change_direction('UP'))
        self.root.bind('s', lambda e: self.change_direction('DOWN'))
        self.root.bind('a', lambda e: self.change_direction('LEFT'))
        self.root.bind('d', lambda e: self.change_direction('RIGHT'))
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        threading.Thread(target=self.connect_to_server, daemon=True).start()
    
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            print(f" 連接失敗: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to connect: {e}"))
            self.root.quit()
    
    def receive_messages(self):
        try:
            while True:
                data = self.receive_message()
                if not data:
                    break
                
                msg_type = data.get('type')
                
                if msg_type == 'WELCOME':
                    self.my_player_id = data.get('player_id')
                    self.my_color = data.get('color')
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"You are Player {self.my_player_id} ({self.my_color})"
                    ))
                
                elif msg_type == 'STATE':
                    self.players = data.get('players', {})
                    self.food = data.get('food', [])
                    self.grid_width = data.get('grid_width', 30)
                    self.grid_height = data.get('grid_height', 20)
                    self.root.after(0, self.render_game)
                
                elif msg_type == 'GAME_OVER':
                    rankings = data.get('rankings', [])
                    self.game_over = True
                    self.root.after(0, lambda: self.show_game_over(rankings))
                    
        except Exception as e:
            print(f" 接收消息錯誤: {e}")
        finally:
            print(" 與服務器斷開連接")
    
    def render_game(self):
        self.canvas.delete('all')
        
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                x1 = x * self.cell_size
                y1 = y * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                self.canvas.create_rectangle(x1, y1, x2, y2, outline='gray', fill='black')
        
        for pos in self.food:
            x1 = pos[0] * self.cell_size
            y1 = pos[1] * self.cell_size
            x2 = x1 + self.cell_size
            y2 = y1 + self.cell_size
            self.canvas.create_oval(x1+2, y1+2, x2-2, y2-2, fill='yellow', outline='gold')
        
        for player_id, player_data in self.players.items():
            if not player_data['alive']:
                continue
            
            snake = player_data['snake']
            color = player_data['color']
            
            for i, pos in enumerate(snake):
                x1 = pos[0] * self.cell_size
                y1 = pos[1] * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                if i == 0:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='white', width=2)
                else:
                    brightness = 0.7 if i % 2 == 0 else 0.5
                    dark_color = self.darken_color(color, brightness)
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=dark_color, outline=color)
        
        for widget in self.score_labels.values():
            widget.destroy()
        self.score_labels.clear()
        
        sorted_players = sorted(
            self.players.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        for i, (player_id, player_data) in enumerate(sorted_players):
            status = "" if not player_data['alive'] else ""
            is_me = " (YOU)" if str(player_id) == str(self.my_player_id) else ""
            
            label = tk.Label(
                self.score_frame,
                text=f"{status} P{player_id}{is_me}: {player_data['score']}",
                font=('Arial', 11, 'bold' if str(player_id) == str(self.my_player_id) else 'normal'),
                fg=player_data['color'],
                bg='lightgray' if str(player_id) == str(self.my_player_id) else 'white'
            )
            label.pack(pady=2, fill=tk.X, padx=5)
            self.score_labels[player_id] = label
    
    def darken_color(self, color, factor):
        colors = {
            'red': '#8B0000',
            'blue': '#00008B',
            'green': '#006400',
            'yellow': '#B8860B'
        }
        return colors.get(color, color)
    
    def change_direction(self, direction):
        if self.game_over:
            return
        
        self.send_message({
            'type': 'DIRECTION',
            'direction': direction
        })
    
    def show_game_over(self, rankings):
        result_text = " Game Over!\n\nFinal Rankings:\n"
        for i, (player_id, score) in enumerate(rankings):
            medal = ["1st", "2nd", "3rd"][i] if i < 3 else f"{i+1}."
            is_me = " (YOU)" if str(player_id) == str(self.my_player_id) else ""
            result_text += f"{medal} Player {player_id}{is_me}: {score} points\n"
        
        messagebox.showinfo("Game Over", result_text)
    
    def send_message(self, data):
        try:
            message = json.dumps(data).encode('utf-8')
            self.socket.sendall(len(message).to_bytes(4, 'big') + message)
        except Exception as e:
            print(f" 發送消息失敗: {e}")
    
    def receive_message(self):
        try:
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, 'big')
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            return json.loads(data.decode('utf-8'))
        except:
            return None
    
    def on_closing(self):
        if self.socket:
            self.socket.close()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 snake_client.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    client = SnakeClient(host, port)
    client.run()
