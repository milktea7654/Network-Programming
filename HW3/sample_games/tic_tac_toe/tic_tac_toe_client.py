#!/usr/bin/env python3
import socket
import threading
import json
import sys
import tkinter as tk
from tkinter import messagebox

class TicTacToeClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.my_symbol = None
        self.board = [' '] * 9
        self.current_player = 'X'
        self.game_over = False
        self.winner = None
        
        self.root = tk.Tk()
        self.root.title("Tic Tac Toe")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        self.status_label = tk.Label(self.root, text="Connecting...", font=('Arial', 14))
        self.status_label.pack(pady=10)
        
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(pady=20)
        
        self.buttons = []
        for i in range(9):
            row = i // 3
            col = i % 3
            btn = tk.Button(
                self.game_frame,
                text=' ',
                font=('Arial', 32, 'bold'),
                width=5,
                height=2,
                command=lambda pos=i: self.make_move(pos),
                bg='white',
                activebackground='lightgray'
            )
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons.append(btn)
        
        self.info_label = tk.Label(self.root, text="", font=('Arial', 12))
        self.info_label.pack(pady=10)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        threading.Thread(target=self.connect_to_server, daemon=True).start()
    
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"[Client] Connected to {self.host}:{self.port}")
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            print(f"[Client] Connection failed: {e}")
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
                    self.my_symbol = data.get('symbol')
                    self.root.after(0, self.update_welcome)
                
                elif msg_type == 'STATE':
                    self.board = data.get('board')
                    self.current_player = data.get('current_player')
                    self.game_over = data.get('game_over')
                    self.winner = data.get('winner')
                    self.root.after(0, self.update_board)
                    
        except Exception as e:
            print(f"[Client] Receive error: {e}")
        finally:
            print("[Client] Disconnected from server")
            if not self.game_over:
                self.root.after(0, lambda: messagebox.showinfo("Info", "Disconnected from server"))
    
    def update_welcome(self):
        self.status_label.config(text=f"You are: {self.my_symbol}")
        self.update_status()
    
    def update_board(self):
        for i, symbol in enumerate(self.board):
            self.buttons[i].config(text=symbol)
            if symbol == 'X':
                self.buttons[i].config(fg='blue')
            elif symbol == 'O':
                self.buttons[i].config(fg='red')
        
        self.update_status()
        
        if self.game_over:
            self.show_game_over()
    
    def update_status(self):
        if self.game_over:
            if self.winner == 'TIE':
                self.info_label.config(text="Game Over: It's a TIE!", fg='orange')
            elif self.winner == self.my_symbol:
                self.info_label.config(text="🎉 You WIN! 🎉", fg='green')
            else:
                self.info_label.config(text="You LOSE!", fg='red')
        else:
            if self.current_player == self.my_symbol:
                self.info_label.config(text="Your turn!", fg='green')
            else:
                self.info_label.config(text="Opponent's turn...", fg='blue')
    
    def make_move(self, position):
        if self.game_over:
            return
        
        if self.current_player != self.my_symbol:
            messagebox.showwarning("Wait", "It's not your turn!")
            return
        
        if self.board[position] != ' ':
            messagebox.showwarning("Invalid", "This cell is already taken!")
            return
        
        self.send_message({
            'type': 'MOVE',
            'position': position
        })
    
    def show_game_over(self):
        for btn in self.buttons:
            btn.config(state='disabled')
        
        if self.winner == 'TIE':
            result = "It's a TIE!"
        elif self.winner == self.my_symbol:
            result = "🎉 You WIN! 🎉"
        else:
            result = "You LOSE!"
        
        messagebox.showinfo("Game Over", result)
    
    def send_message(self, data):
        try:
            message = json.dumps(data).encode('utf-8')
            self.socket.sendall(len(message).to_bytes(4, 'big') + message)
        except Exception as e:
            print(f"[Client] Send error: {e}")
    
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
        print("Usage: python3 tic_tac_toe_client.py <host> <port>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    client = TicTacToeClient(host, port)
    client.run()
