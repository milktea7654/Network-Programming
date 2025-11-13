import pygame
import socket
import threading
import sys
from protocol import send_message, recv_message, ProtocolError
from tetris_logic import SHAPES, SHAPE_COLORS


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (30, 30, 30)
BG_COLOR = (20, 20, 35)


COLORS = [
    (40, 40, 40),
    (0, 240, 240),
    (240, 240, 0),
    (160, 0, 240),
    (0, 240, 0),
    (240, 0, 0),
    (0, 90, 240),
    (240, 160, 0),
]


HIGHLIGHT_COLORS = [
    (60, 60, 60),
    (120, 255, 255),
    (255, 255, 180),
    (220, 120, 255),
    (120, 255, 120),
    (255, 120, 120),
    (120, 150, 255),
    (255, 200, 100),
]


SHADOW_COLORS = [
    (20, 20, 20),
    (0, 140, 140),
    (140, 140, 0),
    (80, 0, 140),
    (0, 140, 0),
    (140, 0, 0),
    (0, 50, 140),
    (140, 90, 0),
]


BLOCK_SIZE = 25
GRID_WIDTH = 10
GRID_HEIGHT = 20
SMALL_BLOCK_SIZE = 12


class GameClient:
    def __init__(self, game_host, game_port, user_id, room_id, username=None, spectate=False):
        self.game_host = game_host
        self.game_port = game_port
        self.user_id = user_id
        self.room_id = room_id
        self.username = username or str(user_id)
        self.spectate = spectate

        pygame.init()

        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        title = "Tetris Battle (Spectator)" if spectate else "Tetris Battle"
        pygame.display.set_caption(title)

        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 20)

        self.running = True
        self.connected = False
        self.role = None

        self.my_board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.my_active = None
        self.my_hold = None
        self.my_next = []
        self.my_score = 0
        self.my_lines = 0
        self.my_level = 1
        self.my_game_over = False

        self.opponent_user_id = None
        self.opponent_username = None
        self.opponent_board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.opponent_active = None
        self.opponent_score = 0
        self.opponent_lines = 0
        self.opponent_game_over = False

        self.players = {}

        self.game_ended = False
        self.winner = None

        self.socket = None

        self.lock = threading.Lock()
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.game_host, self.game_port))

            send_message(self.socket, {
                'type': 'HELLO',
                'version': 1,
                'roomId': self.room_id,
                'userId': self.user_id,
                'username': self.username,
                'spectate': self.spectate
            })

            welcome = recv_message(self.socket)
            if welcome.get('type') == 'WELCOME':
                self.role = welcome.get('role')
                self.connected = True
                if self.spectate:
                    print(f"[Spectator] Connected successfully. Waiting for game data...")
                else:
                    print(f"[Client] Connected as {self.role}")

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
        try:
            while self.running and self.connected:
                msg = recv_message(self.socket)
                self.handle_message(msg)
        except (ConnectionError, ProtocolError) as e:

            if not self.game_ended:
                print(f"[Client] Connection lost: {e}")
            self.connected = False
        except Exception as e:
            if not self.game_ended:
                print(f"[Client] Receive error: {e}")
                import traceback
                traceback.print_exc()
    def handle_message(self, msg):
        msg_type = msg.get('type')
        if msg_type == 'SNAPSHOT':

            user_id = msg.get('userId')
            with self.lock:
                if self.spectate:

                    self.update_player_state(user_id, msg)
                elif user_id == self.user_id:

                    self.update_my_state(msg)
                else:

                    self.update_opponent_state(msg)
        elif msg_type == 'GAME_END':

            with self.lock:
                self.game_ended = True
                self.winner = msg.get('winner')
                print(f"[Client] Game ended. Winner: {self.winner}")
    def update_my_state(self, snapshot):

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

        self.opponent_user_id = snapshot.get('userId')
        self.opponent_username = snapshot.get('username', str(self.opponent_user_id))

        board_rle = snapshot.get('boardRLE', '')
        if board_rle:
            rows = board_rle.split('|')
            self.opponent_board = [[int(c) for c in row] for row in rows]
        self.opponent_active = snapshot.get('active')
        self.opponent_score = snapshot.get('score', 0)
        self.opponent_lines = snapshot.get('lines', 0)
        self.opponent_game_over = snapshot.get('gameOver', False)
    def update_player_state(self, user_id, snapshot):
        username = snapshot.get('username', str(user_id))

        board_rle = snapshot.get('boardRLE', '')
        board = [[0] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        if board_rle:
            rows = board_rle.split('|')
            board = [[int(c) for c in row] for row in rows]
        self.players[user_id] = {
            'username': username,
            'board': board,
            'active': snapshot.get('active'),
            'score': snapshot.get('score', 0),
            'lines': snapshot.get('lines', 0),
            'level': snapshot.get('level', 1),
            'game_over': snapshot.get('gameOver', False)
        }
    def send_input(self, action):

        if self.spectate:
            return
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
    def draw_styled_block(self, x, y, block_size, color_idx):
        if color_idx >= len(COLORS):
            color_idx = 0
        base_color = COLORS[color_idx]
        highlight = HIGHLIGHT_COLORS[color_idx]
        shadow = SHADOW_COLORS[color_idx]

        pygame.draw.rect(self.screen, base_color, 
                        (x, y, block_size - 1, block_size - 1))

        if block_size >= 15:

            highlight_width = max(1, block_size // 8)
            pygame.draw.line(self.screen, highlight, 
                           (x, y), (x + block_size - 2, y), highlight_width)
            pygame.draw.line(self.screen, highlight, 
                           (x, y), (x, y + block_size - 2), highlight_width)

            shadow_width = max(1, block_size // 8)
            pygame.draw.line(self.screen, shadow, 
                           (x + block_size - 2, y), 
                           (x + block_size - 2, y + block_size - 2), shadow_width)
            pygame.draw.line(self.screen, shadow, 
                           (x, y + block_size - 2), 
                           (x + block_size - 2, y + block_size - 2), shadow_width)

            if block_size >= 20:
                inner_offset = max(2, block_size // 6)
                inner_size = max(1, block_size // 10)
                pygame.draw.rect(self.screen, highlight,
                               (x + inner_offset, y + inner_offset, 
                                inner_size, inner_size))
    def draw_board(self, board, active, x_offset, y_offset, block_size=BLOCK_SIZE):

        pygame.draw.rect(
            self.screen, WHITE,
            (x_offset - 2, y_offset - 2, 
             GRID_WIDTH * block_size + 4, GRID_HEIGHT * block_size + 4),
            2
        )

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color_idx = board[y][x] if board[y][x] < len(COLORS) else 0
                self.draw_styled_block(
                    x_offset + x * block_size, 
                    y_offset + y * block_size,
                    block_size, 
                    color_idx
                )

        if active:
            shape_name = active.get('shape')
            rotation = active.get('rotation', 0)
            ax = active.get('x', 0)
            ay = active.get('y', 0)
            if shape_name and shape_name in SHAPES:
                shape = SHAPES[shape_name][rotation]
                color_idx = SHAPE_COLORS[shape_name]
                for row in range(len(shape)):
                    for col in range(len(shape[0])):
                        if shape[row][col]:
                            px = ax + col
                            py = ay + row
                            if 0 <= py < GRID_HEIGHT and 0 <= px < GRID_WIDTH:
                                self.draw_styled_block(
                                    x_offset + px * block_size, 
                                    y_offset + py * block_size,
                                    block_size, 
                                    color_idx
                                )
    def draw_preview(self, shape_name, x_offset, y_offset, block_size=20):
        if not shape_name or shape_name not in SHAPES:
            return
        shape = SHAPES[shape_name][0]
        color_idx = SHAPE_COLORS[shape_name]
        for row in range(len(shape)):
            for col in range(len(shape[0])):
                if shape[row][col]:
                    self.draw_styled_block(
                        x_offset + col * block_size, 
                        y_offset + row * block_size,
                        block_size, 
                        color_idx
                    )
    def draw_spectator_view(self):
        player_list = list(self.players.values())
        if len(player_list) == 0:

            wait_text = self.font.render("Waiting for players...", True, WHITE)
            rect = wait_text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(wait_text, rect)
            return

        spacing = 50
        board_width = GRID_WIDTH * BLOCK_SIZE
        total_width = board_width * 2 + spacing
        start_x = (self.width - total_width) // 2
        y_offset = 50

        if len(player_list) >= 1:
            player1 = player_list[0]
            x1 = start_x
            self.draw_board(player1['board'], player1['active'], x1, y_offset)

            title1 = self.font.render(player1['username'], True, WHITE)
            self.screen.blit(title1, (x1, y_offset - 35))

            info_y = y_offset + GRID_HEIGHT * BLOCK_SIZE + 20
            score1 = self.small_font.render(f"Score: {player1['score']}", True, WHITE)
            lines1 = self.small_font.render(f"Lines: {player1['lines']}", True, WHITE)
            level1 = self.small_font.render(f"Level: {player1['level']}", True, WHITE)
            self.screen.blit(score1, (x1, info_y))
            self.screen.blit(lines1, (x1, info_y + 25))
            self.screen.blit(level1, (x1, info_y + 50))

        if len(player_list) >= 2:
            player2 = player_list[1]
            x2 = start_x + board_width + spacing
            self.draw_board(player2['board'], player2['active'], x2, y_offset)

            title2 = self.font.render(player2['username'], True, WHITE)
            self.screen.blit(title2, (x2, y_offset - 35))

            info_y = y_offset + GRID_HEIGHT * BLOCK_SIZE + 20
            score2 = self.small_font.render(f"Score: {player2['score']}", True, WHITE)
            lines2 = self.small_font.render(f"Lines: {player2['lines']}", True, WHITE)
            level2 = self.small_font.render(f"Level: {player2['level']}", True, WHITE)
            self.screen.blit(score2, (x2, info_y))
            self.screen.blit(lines2, (x2, info_y + 25))
            self.screen.blit(level2, (x2, info_y + 50))

        if self.game_ended:
            overlay = pygame.Surface((self.width, self.height))
            overlay.set_alpha(128)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            result_text = f"Winner: {self.players.get(self.winner, {}).get('username', 'Unknown')}"
            color = (0, 255, 0)
            big_font = pygame.font.Font(None, 60)
            result = big_font.render(result_text, True, color)
            rect = result.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(result, rect)
            esc_text = self.small_font.render("Press ESC to exit", True, WHITE)
            esc_rect = esc_text.get_rect(center=(self.width // 2, self.height // 2 + 60))
            self.screen.blit(esc_text, esc_rect)
    def draw(self):
        self.screen.fill(BG_COLOR)
        with self.lock:

            if self.spectate:
                self.draw_spectator_view()
            else:

                self.draw_player_view()
        pygame.display.flip()
    def draw_player_view(self):
        my_x_offset = 50
        my_y_offset = 50
        self.draw_board(self.my_board, self.my_active, my_x_offset, my_y_offset)

        title = self.font.render(f"{self.username} (YOU)", True, WHITE)
        self.screen.blit(title, (my_x_offset, my_y_offset - 35))

        info_x = my_x_offset + GRID_WIDTH * BLOCK_SIZE + 20
        info_y = my_y_offset
        score_text = self.small_font.render(f"Score: {self.my_score}", True, WHITE)
        lines_text = self.small_font.render(f"Lines: {self.my_lines}", True, WHITE)
        level_text = self.small_font.render(f"Level: {self.my_level}", True, WHITE)
        self.screen.blit(score_text, (info_x, info_y))
        self.screen.blit(lines_text, (info_x, info_y + 25))
        self.screen.blit(level_text, (info_x, info_y + 50))

        if self.my_hold:
            hold_label = self.small_font.render("Hold:", True, WHITE)
            self.screen.blit(hold_label, (info_x, info_y + 90))
            self.draw_preview(self.my_hold, info_x, info_y + 115)

        next_label = self.small_font.render("Next:", True, WHITE)
        self.screen.blit(next_label, (info_x, info_y + 200))
        for i, shape in enumerate(self.my_next[:3]):
            self.draw_preview(shape, info_x, info_y + 225 + i * 60, block_size=15)

        opp_x_offset = 500
        opp_y_offset = 50
        self.draw_board(self.opponent_board, self.opponent_active, 
                      opp_x_offset, opp_y_offset, SMALL_BLOCK_SIZE)

        if self.opponent_username:
            opp_title = self.font.render(f"{self.opponent_username}", True, WHITE)
        else:
            opp_title = self.font.render("Waiting...", True, WHITE)
        self.screen.blit(opp_title, (opp_x_offset, opp_y_offset - 35))

        opp_info_x = opp_x_offset
        opp_info_y = opp_y_offset + GRID_HEIGHT * SMALL_BLOCK_SIZE + 20
        opp_score = self.small_font.render(f"Score: {self.opponent_score}", True, WHITE)
        opp_lines = self.small_font.render(f"Lines: {self.opponent_lines}", True, WHITE)
        self.screen.blit(opp_score, (opp_info_x, opp_info_y))
        self.screen.blit(opp_lines, (opp_info_x, opp_info_y + 25))

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

        if not self.game_ended:
            help_y = self.height - 30
            help_texts = [
                "Controls: Arrow Keys = Move/Rotate, Space = Hard Drop, C = Hold, ESC = Quit"
            ]
            for i, text in enumerate(help_texts):
                help_surface = self.small_font.render(text, True, GRAY)
                self.screen.blit(help_surface, (10, help_y + i * 20))
    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_events()
            self.draw()
            clock.tick(60)

        if self.socket:
            self.socket.close()
        pygame.quit()


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python3 game_client.py <host> <port> <user_id> <room_id> [username] [spectate]")
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    user_id = int(sys.argv[3])
    room_id = int(sys.argv[4])
    username = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5].lower() != 'spectate' else None
    spectate = (len(sys.argv) > 5 and sys.argv[5].lower() == 'spectate') or (len(sys.argv) > 6 and sys.argv[6].lower() == 'spectate')
    client = GameClient(host, port, user_id, room_id, username, spectate)
    if client.connect():
        client.run()
    else:
        print("Failed to connect to game server")
