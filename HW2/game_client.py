"""
Game Client - 遊戲客戶端 (Pygame GUI)
"""
import pygame
import socket
import threading
import sys
from protocol import send_message, recv_message, ProtocolError
from tetris_logic import SHAPES, SHAPE_COLORS

# 顏色定義
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)
COLORS = [
    BLACK,           # 0: 空
    (0, 255, 255),   # 1: I - 青色
    (255, 255, 0),   # 2: O - 黃色
    (128, 0, 128),   # 3: T - 紫色
    (0, 255, 0),     # 4: S - 綠色
    (255, 0, 0),     # 5: Z - 紅色
    (0, 0, 255),     # 6: J - 藍色
    (255, 165, 0),   # 7: L - 橘色
]

# 遊戲設定
BLOCK_SIZE = 25
GRID_WIDTH = 10
GRID_HEIGHT = 20
SMALL_BLOCK_SIZE = 12  # 對手棋盤的方塊大小


class GameClient:
    def __init__(self, game_host, game_port, user_id, room_id):
        self.game_host = game_host
        self.game_port = game_port
        self.user_id = user_id
        self.room_id = room_id
        
        # 初始化 Pygame
        pygame.init()
        
        # 視窗大小
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tetris Battle")
        
        # 字體
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 20)
        
        # 遊戲狀態
        self.running = True
        self.connected = False
        self.role = None
        
        # 自己的狀態
        self.my_board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.my_active = None
        self.my_hold = None
        self.my_next = []
        self.my_score = 0
        self.my_lines = 0
        self.my_level = 1
        self.my_game_over = False
        
        # 對手的狀態
        self.opponent_board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.opponent_active = None
        self.opponent_score = 0
        self.opponent_lines = 0
        self.opponent_game_over = False
        
        # 遊戲結果
        self.game_ended = False
        self.winner = None
        
        # Socket
        self.socket = None
        
        # 鎖
        self.lock = threading.Lock()
    
    def connect(self):
        """連接到遊戲伺服器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.game_host, self.game_port))
            
            # 發送 HELLO
            send_message(self.socket, {
                'type': 'HELLO',
                'version': 1,
                'roomId': self.room_id,
                'userId': self.user_id
            })
            
            # 接收 WELCOME
            welcome = recv_message(self.socket)
            
            if welcome.get('type') == 'WELCOME':
                self.role = welcome.get('role')
                self.connected = True
                print(f"[Client] Connected as {self.role}")
                
                # 啟動接收線程
                thread = threading.Thread(target=self.receive_loop)
                thread.daemon = True
                thread.start()
                
                return True
            else:
                print(f"[Client] Connection failed: {welcome}")
                return False
                
        except Exception as e:
            print(f"[Client] Connection error: {e}")
            return False
    
    def receive_loop(self):
        """接收訊息循環"""
        try:
            while self.running and self.connected:
                msg = recv_message(self.socket)
                self.handle_message(msg)
        except (ConnectionError, ProtocolError) as e:
            print(f"[Client] Connection lost: {e}")
            self.connected = False
        except Exception as e:
            print(f"[Client] Receive error: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_message(self, msg):
        """處理接收到的訊息"""
        msg_type = msg.get('type')
        
        if msg_type == 'SNAPSHOT':
            # 更新狀態
            user_id = msg.get('userId')
            
            with self.lock:
                if user_id == self.user_id:
                    # 自己的狀態
                    self.update_my_state(msg)
                else:
                    # 對手的狀態
                    self.update_opponent_state(msg)
        
        elif msg_type == 'GAME_END':
            # 遊戲結束
            with self.lock:
                self.game_ended = True
                self.winner = msg.get('winner')
                print(f"[Client] Game ended. Winner: {self.winner}")
    
    def update_my_state(self, snapshot):
        """更新自己的狀態"""
        # 解壓縮棋盤
        board_rle = snapshot.get('boardRLE', '')
        if board_rle:
            rows = board_rle.split('|')
            self.my_board = [[int(c) for c in row] for row in rows]
        
        self.my_active = snapshot.get('active')
        self.my_hold = snapshot.get('hold')
        self.my_next = snapshot.get('next', [])
        self.my_score = snapshot.get('score', 0)
        self.my_lines = snapshot.get('lines', 0)
        self.my_level = snapshot.get('level', 1)
        self.my_game_over = snapshot.get('gameOver', False)
    
    def update_opponent_state(self, snapshot):
        """更新對手的狀態"""
        # 解壓縮棋盤
        board_rle = snapshot.get('boardRLE', '')
        if board_rle:
            rows = board_rle.split('|')
            self.opponent_board = [[int(c) for c in row] for row in rows]
        
        self.opponent_active = snapshot.get('active')
        self.opponent_score = snapshot.get('score', 0)
        self.opponent_lines = snapshot.get('lines', 0)
        self.opponent_game_over = snapshot.get('gameOver', False)
    
    def send_input(self, action):
        """發送輸入"""
        if not self.connected or self.my_game_over:
            return
        
        try:
            send_message(self.socket, {
                'type': 'INPUT',
                'userId': self.user_id,
                'action': action
            })
        except Exception as e:
            print(f"[Client] Send error: {e}")
    
    def handle_events(self):
        """處理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.send_input('LEFT')
                elif event.key == pygame.K_RIGHT:
                    self.send_input('RIGHT')
                elif event.key == pygame.K_UP or event.key == pygame.K_x:
                    self.send_input('CW')
                elif event.key == pygame.K_z:
                    self.send_input('CCW')
                elif event.key == pygame.K_DOWN:
                    self.send_input('SOFT_DROP')
                elif event.key == pygame.K_SPACE:
                    self.send_input('HARD_DROP')
                elif event.key == pygame.K_c:
                    self.send_input('HOLD')
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def draw_board(self, board, active, x_offset, y_offset, block_size=BLOCK_SIZE):
        """繪製棋盤"""
        # 繪製邊框
        pygame.draw.rect(
            self.screen, WHITE,
            (x_offset - 2, y_offset - 2, 
             GRID_WIDTH * block_size + 4, GRID_HEIGHT * block_size + 4),
            2
        )
        
        # 繪製棋盤背景
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color = COLORS[board[y][x]] if board[y][x] < len(COLORS) else WHITE
                pygame.draw.rect(
                    self.screen, color,
                    (x_offset + x * block_size, y_offset + y * block_size,
                     block_size - 1, block_size - 1)
                )
        
        # 繪製當前方塊
        if active:
            shape_name = active.get('shape')
            rotation = active.get('rotation', 0)
            ax = active.get('x', 0)
            ay = active.get('y', 0)
            
            if shape_name and shape_name in SHAPES:
                shape = SHAPES[shape_name][rotation]
                color = COLORS[SHAPE_COLORS[shape_name]]
                
                for row in range(len(shape)):
                    for col in range(len(shape[0])):
                        if shape[row][col]:
                            px = ax + col
                            py = ay + row
                            if 0 <= py < GRID_HEIGHT and 0 <= px < GRID_WIDTH:
                                pygame.draw.rect(
                                    self.screen, color,
                                    (x_offset + px * block_size, y_offset + py * block_size,
                                     block_size - 1, block_size - 1)
                                )
    
    def draw_preview(self, shape_name, x_offset, y_offset, block_size=20):
        """繪製預覽方塊"""
        if not shape_name or shape_name not in SHAPES:
            return
        
        shape = SHAPES[shape_name][0]
        color = COLORS[SHAPE_COLORS[shape_name]]
        
        for row in range(len(shape)):
            for col in range(len(shape[0])):
                if shape[row][col]:
                    pygame.draw.rect(
                        self.screen, color,
                        (x_offset + col * block_size, y_offset + row * block_size,
                         block_size - 1, block_size - 1)
                    )
    
    def draw(self):
        """繪製遊戲畫面"""
        self.screen.fill(DARK_GRAY)
        
        with self.lock:
            # 繪製自己的棋盤（左側）
            my_x_offset = 50
            my_y_offset = 50
            self.draw_board(self.my_board, self.my_active, my_x_offset, my_y_offset)
            
            # 繪製標題
            title = self.font.render(f"You ({self.role})", True, WHITE)
            self.screen.blit(title, (my_x_offset, my_y_offset - 35))
            
            # 繪製分數資訊
            info_x = my_x_offset + GRID_WIDTH * BLOCK_SIZE + 20
            info_y = my_y_offset
            
            score_text = self.small_font.render(f"Score: {self.my_score}", True, WHITE)
            lines_text = self.small_font.render(f"Lines: {self.my_lines}", True, WHITE)
            level_text = self.small_font.render(f"Level: {self.my_level}", True, WHITE)
            
            self.screen.blit(score_text, (info_x, info_y))
            self.screen.blit(lines_text, (info_x, info_y + 25))
            self.screen.blit(level_text, (info_x, info_y + 50))
            
            # 繪製 Hold
            if self.my_hold:
                hold_label = self.small_font.render("Hold:", True, WHITE)
                self.screen.blit(hold_label, (info_x, info_y + 90))
                self.draw_preview(self.my_hold, info_x, info_y + 115)
            
            # 繪製 Next
            next_label = self.small_font.render("Next:", True, WHITE)
            self.screen.blit(next_label, (info_x, info_y + 200))
            
            for i, shape in enumerate(self.my_next[:3]):
                self.draw_preview(shape, info_x, info_y + 225 + i * 60, block_size=15)
            
            # 繪製對手的棋盤（右側，縮小版）
            opp_x_offset = 500
            opp_y_offset = 50
            self.draw_board(self.opponent_board, self.opponent_active, 
                          opp_x_offset, opp_y_offset, SMALL_BLOCK_SIZE)
            
            # 繪製對手標題
            opp_title = self.font.render("Opponent", True, WHITE)
            self.screen.blit(opp_title, (opp_x_offset, opp_y_offset - 35))
            
            # 繪製對手分數
            opp_info_x = opp_x_offset
            opp_info_y = opp_y_offset + GRID_HEIGHT * SMALL_BLOCK_SIZE + 20
            
            opp_score = self.small_font.render(f"Score: {self.opponent_score}", True, WHITE)
            opp_lines = self.small_font.render(f"Lines: {self.opponent_lines}", True, WHITE)
            
            self.screen.blit(opp_score, (opp_info_x, opp_info_y))
            self.screen.blit(opp_lines, (opp_info_x, opp_info_y + 25))
            
            # 遊戲結束訊息
            if self.game_ended:
                overlay = pygame.Surface((self.width, self.height))
                overlay.set_alpha(128)
                overlay.fill(BLACK)
                self.screen.blit(overlay, (0, 0))
                
                if self.winner == self.user_id:
                    result_text = "YOU WIN!"
                    color = (0, 255, 0)
                else:
                    result_text = "YOU LOSE!"
                    color = (255, 0, 0)
                
                big_font = pygame.font.Font(None, 72)
                result = big_font.render(result_text, True, color)
                rect = result.get_rect(center=(self.width // 2, self.height // 2))
                self.screen.blit(result, rect)
                
                esc_text = self.small_font.render("Press ESC to exit", True, WHITE)
                esc_rect = esc_text.get_rect(center=(self.width // 2, self.height // 2 + 60))
                self.screen.blit(esc_text, esc_rect)
            
            # 操作說明
            if not self.game_ended:
                help_y = self.height - 80
                help_texts = [
                    "Controls: Arrow Keys = Move/Rotate, Space = Hard Drop, C = Hold, ESC = Quit"
                ]
                for i, text in enumerate(help_texts):
                    help_surface = self.small_font.render(text, True, GRAY)
                    self.screen.blit(help_surface, (10, help_y + i * 20))
        
        pygame.display.flip()
    
    def run(self):
        """主循環"""
        clock = pygame.time.Clock()
        
        while self.running:
            self.handle_events()
            self.draw()
            clock.tick(60)  # 60 FPS
        
        # 清理
        if self.socket:
            self.socket.close()
        pygame.quit()


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 game_client.py <host> <port> <user_id> <room_id>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    user_id = int(sys.argv[3])
    room_id = int(sys.argv[4])
    
    client = GameClient(host, port, user_id, room_id)
    
    if client.connect():
        client.run()
    else:
        print("Failed to connect to game server")
