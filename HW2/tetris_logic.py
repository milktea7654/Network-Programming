import random
import copy

SHAPES = {
    'I': [
        [[0, 0, 0, 0],
         [1, 1, 1, 1],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 1, 0]],
        [[0, 0, 0, 0],
         [0, 0, 0, 0],
         [1, 1, 1, 1],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0]]
    ],
    'O': [
        [[1, 1],
         [1, 1]],
        [[1, 1],
         [1, 1]],
        [[1, 1],
         [1, 1]],
        [[1, 1],
         [1, 1]]
    ],
    'T': [
        [[0, 1, 0],
         [1, 1, 1],
         [0, 0, 0]],
        [[0, 1, 0],
         [0, 1, 1],
         [0, 1, 0]],
        [[0, 0, 0],
         [1, 1, 1],
         [0, 1, 0]],
        [[0, 1, 0],
         [1, 1, 0],
         [0, 1, 0]]
    ],
    'S': [
        [[0, 1, 1],
         [1, 1, 0],
         [0, 0, 0]],
        [[0, 1, 0],
         [0, 1, 1],
         [0, 0, 1]],
        [[0, 0, 0],
         [0, 1, 1],
         [1, 1, 0]],
        [[1, 0, 0],
         [1, 1, 0],
         [0, 1, 0]]
    ],
    'Z': [
        [[1, 1, 0],
         [0, 1, 1],
         [0, 0, 0]],
        [[0, 0, 1],
         [0, 1, 1],
         [0, 1, 0]],
        [[0, 0, 0],
         [1, 1, 0],
         [0, 1, 1]],
        [[0, 1, 0],
         [1, 1, 0],
         [1, 0, 0]]
    ],
    'J': [
        [[1, 0, 0],
         [1, 1, 1],
         [0, 0, 0]],
        [[0, 1, 1],
         [0, 1, 0],
         [0, 1, 0]],
        [[0, 0, 0],
         [1, 1, 1],
         [0, 0, 1]],
        [[0, 1, 0],
         [0, 1, 0],
         [1, 1, 0]]
    ],
    'L': [
        [[0, 0, 1],
         [1, 1, 1],
         [0, 0, 0]],
        [[0, 1, 0],
         [0, 1, 0],
         [0, 1, 1]],
        [[0, 0, 0],
         [1, 1, 1],
         [1, 0, 0]],
        [[1, 1, 0],
         [0, 1, 0],
         [0, 1, 0]]
    ]
}

SHAPE_NAMES = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']

SHAPE_COLORS = {
    'I': 1, 'O': 2, 'T': 3, 'S': 4, 'Z': 5, 'J': 6, 'L': 7
}


class TetrisGame:
    def __init__(self, width=10, height=20, seed=None):
        self.width = width
        self.height = height
        self.board = [[0] * width for _ in range(height)]
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.game_over = False
        self.current_piece = None
        self.current_shape = None
        self.current_x = 0
        self.current_y = 0
        self.current_rotation = 0
        self.hold_piece = None
        self.can_hold = True
        self.bag = []
        self.next_pieces = []
        if seed is not None:
            random.seed(seed)
        self.refill_bag()
        for _ in range(5):
            self.next_pieces.append(self.get_next_from_bag())
        self.spawn_piece()
    def refill_bag(self):
        self.bag = SHAPE_NAMES.copy()
        random.shuffle(self.bag)
    def get_next_from_bag(self):
        if not self.bag:
            self.refill_bag()
        return self.bag.pop(0)
    def spawn_piece(self):
        if not self.next_pieces:
            return False
        self.current_shape = self.next_pieces.pop(0)
        self.next_pieces.append(self.get_next_from_bag())
        self.current_piece = SHAPES[self.current_shape]
        self.current_rotation = 0
        self.current_x = self.width // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0
        self.can_hold = True
        if not self.is_valid_position():
            self.game_over = True
            return False
        return True
    def is_valid_position(self, x=None, y=None, rotation=None):
        if x is None:
            x = self.current_x
        if y is None:
            y = self.current_y
        if rotation is None:
            rotation = self.current_rotation
        shape = self.current_piece[rotation]
        for row in range(len(shape)):
            for col in range(len(shape[0])):
                if shape[row][col]:
                    board_x = x + col
                    board_y = y + row
                    if board_x < 0 or board_x >= self.width:
                        return False
                    if board_y >= self.height:
                        return False
                    if board_y >= 0 and self.board[board_y][board_x]:
                        return False
        return True
    def move_left(self):
        if self.game_over:
            return False
        if self.is_valid_position(x=self.current_x - 1):
            self.current_x -= 1
            return True
        return False
    def move_right(self):
        if self.game_over:
            return False
        if self.is_valid_position(x=self.current_x + 1):
            self.current_x += 1
            return True
        return False
    def rotate_cw(self):
        if self.game_over:
            return False
        new_rotation = (self.current_rotation + 1) % 4
        if self.is_valid_position(rotation=new_rotation):
            self.current_rotation = new_rotation
            return True
        return False
    def rotate_ccw(self):
        if self.game_over:
            return False
        new_rotation = (self.current_rotation - 1) % 4
        if self.is_valid_position(rotation=new_rotation):
            self.current_rotation = new_rotation
            return True
        return False
    def soft_drop(self):
        if self.game_over:
            return False
        if self.is_valid_position(y=self.current_y + 1):
            self.current_y += 1
            self.score += 1
            return True
        else:
            self.lock_piece()
            return False
    def hard_drop(self):
        if self.game_over:
            return 0
        drop_distance = 0
        while self.is_valid_position(y=self.current_y + 1):
            self.current_y += 1
            drop_distance += 1
        self.score += drop_distance * 2
        self.lock_piece()
        return drop_distance
    def hold(self):
        if self.game_over or not self.can_hold:
            return False
        if self.hold_piece is None:
            self.hold_piece = self.current_shape
            self.spawn_piece()
        else:
            self.hold_piece, self.current_shape = self.current_shape, self.hold_piece
            self.current_piece = SHAPES[self.current_shape]
            self.current_rotation = 0
            self.current_x = self.width // 2 - len(self.current_piece[0]) // 2
            self.current_y = 0
        self.can_hold = False
        return True
    def lock_piece(self):
        shape = self.current_piece[self.current_rotation]
        color = SHAPE_COLORS[self.current_shape]
        for row in range(len(shape)):
            for col in range(len(shape[0])):
                if shape[row][col]:
                    board_y = self.current_y + row
                    board_x = self.current_x + col
                    if 0 <= board_y < self.height:
                        self.board[board_y][board_x] = color
        lines = self.clear_lines()
        if lines > 0:
            self.lines_cleared += lines
            scores = [0, 100, 300, 500, 800]
            self.score += scores[min(lines, 4)] * self.level
            self.level = self.lines_cleared // 10 + 1
        self.spawn_piece()
    def clear_lines(self):
        lines_to_clear = []
        for y in range(self.height):
            if all(self.board[y]):
                lines_to_clear.append(y)
        for y in lines_to_clear:
            del self.board[y]
            self.board.insert(0, [0] * self.width)
        return len(lines_to_clear)
    def get_ghost_y(self):
        ghost_y = self.current_y
        while self.is_valid_position(y=ghost_y + 1):
            ghost_y += 1
        return ghost_y
    def get_state(self):
        return {
            'board': copy.deepcopy(self.board),
            'current': {
                'shape': self.current_shape,
                'x': self.current_x,
                'y': self.current_y,
                'rotation': self.current_rotation
            },
            'hold': self.hold_piece,
            'next': self.next_pieces[:5],
            'score': self.score,
            'lines': self.lines_cleared,
            'level': self.level,
            'gameOver': self.game_over
        }
    def compress_board(self):
        result = []
        for row in self.board:
            row_str = ''.join(str(cell) for cell in row)
            result.append(row_str)
        return '|'.join(result)
