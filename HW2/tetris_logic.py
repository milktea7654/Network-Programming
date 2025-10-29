"""
Tetris Game Logic - 俄羅斯方塊遊戲邏輯
"""
import random
import copy

# 方塊形狀定義（使用 SRS 旋轉系統）
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

# 方塊顏色（用於顯示）
SHAPE_COLORS = {
    'I': 1, 'O': 2, 'T': 3, 'S': 4, 'Z': 5, 'J': 6, 'L': 7
}


class TetrisGame:
    """俄羅斯方塊遊戲邏輯"""
    
    def __init__(self, width=10, height=20, seed=None):
        self.width = width
        self.height = height
        self.board = [[0] * width for _ in range(height)]
        
        # 遊戲狀態
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.game_over = False
        
        # 當前方塊
        self.current_piece = None
        self.current_shape = None
        self.current_x = 0
        self.current_y = 0
        self.current_rotation = 0
        
        # Hold 功能
        self.hold_piece = None
        self.can_hold = True
        
        # 方塊序列（7-bag）
        self.bag = []
        self.next_pieces = []
        
        # 隨機種子
        if seed is not None:
            random.seed(seed)
        
        # 初始化方塊序列
        self.refill_bag()
        for _ in range(5):
            self.next_pieces.append(self.get_next_from_bag())
        
        # 生成第一個方塊
        self.spawn_piece()
    
    def refill_bag(self):
        """重新填充 7-bag"""
        self.bag = SHAPE_NAMES.copy()
        random.shuffle(self.bag)
    
    def get_next_from_bag(self):
        """從 bag 中取出下一個方塊"""
        if not self.bag:
            self.refill_bag()
        return self.bag.pop(0)
    
    def spawn_piece(self):
        """生成新方塊"""
        if not self.next_pieces:
            return False
        
        self.current_shape = self.next_pieces.pop(0)
        self.next_pieces.append(self.get_next_from_bag())
        
        self.current_piece = SHAPES[self.current_shape]
        self.current_rotation = 0
        self.current_x = self.width // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0
        self.can_hold = True
        
        # 檢查是否可以放置（遊戲結束判定）
        if not self.is_valid_position():
            self.game_over = True
            return False
        
        return True
    
    def is_valid_position(self, x=None, y=None, rotation=None):
        """檢查位置是否有效"""
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
                    
                    # 檢查邊界
                    if board_x < 0 or board_x >= self.width:
                        return False
                    if board_y >= self.height:
                        return False
                    
                    # 檢查碰撞（忽略頂部溢出）
                    if board_y >= 0 and self.board[board_y][board_x]:
                        return False
        
        return True
    
    def move_left(self):
        """左移"""
        if self.game_over:
            return False
        
        if self.is_valid_position(x=self.current_x - 1):
            self.current_x -= 1
            return True
        return False
    
    def move_right(self):
        """右移"""
        if self.game_over:
            return False
        
        if self.is_valid_position(x=self.current_x + 1):
            self.current_x += 1
            return True
        return False
    
    def rotate_cw(self):
        """順時針旋轉"""
        if self.game_over:
            return False
        
        new_rotation = (self.current_rotation + 1) % 4
        if self.is_valid_position(rotation=new_rotation):
            self.current_rotation = new_rotation
            return True
        return False
    
    def rotate_ccw(self):
        """逆時針旋轉"""
        if self.game_over:
            return False
        
        new_rotation = (self.current_rotation - 1) % 4
        if self.is_valid_position(rotation=new_rotation):
            self.current_rotation = new_rotation
            return True
        return False
    
    def soft_drop(self):
        """軟降（下移一格）"""
        if self.game_over:
            return False
        
        if self.is_valid_position(y=self.current_y + 1):
            self.current_y += 1
            self.score += 1
            return True
        else:
            # 鎖定方塊
            self.lock_piece()
            return False
    
    def hard_drop(self):
        """硬降（直接降到底）"""
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
        """Hold 功能"""
        if self.game_over or not self.can_hold:
            return False
        
        if self.hold_piece is None:
            # 第一次 hold
            self.hold_piece = self.current_shape
            self.spawn_piece()
        else:
            # 交換 hold 和當前方塊
            self.hold_piece, self.current_shape = self.current_shape, self.hold_piece
            self.current_piece = SHAPES[self.current_shape]
            self.current_rotation = 0
            self.current_x = self.width // 2 - len(self.current_piece[0]) // 2
            self.current_y = 0
        
        self.can_hold = False
        return True
    
    def lock_piece(self):
        """鎖定方塊到棋盤"""
        shape = self.current_piece[self.current_rotation]
        color = SHAPE_COLORS[self.current_shape]
        
        for row in range(len(shape)):
            for col in range(len(shape[0])):
                if shape[row][col]:
                    board_y = self.current_y + row
                    board_x = self.current_x + col
                    if 0 <= board_y < self.height:
                        self.board[board_y][board_x] = color
        
        # 清除完整行
        lines = self.clear_lines()
        
        # 計分
        if lines > 0:
            self.lines_cleared += lines
            # 計分規則：1 行 100 分，2 行 300 分，3 行 500 分，4 行 800 分
            scores = [0, 100, 300, 500, 800]
            self.score += scores[min(lines, 4)] * self.level
            
            # 升級（每 10 行）
            self.level = self.lines_cleared // 10 + 1
        
        # 生成新方塊
        self.spawn_piece()
    
    def clear_lines(self):
        """清除完整行"""
        lines_to_clear = []
        
        for y in range(self.height):
            if all(self.board[y]):
                lines_to_clear.append(y)
        
        for y in lines_to_clear:
            del self.board[y]
            self.board.insert(0, [0] * self.width)
        
        return len(lines_to_clear)
    
    def get_ghost_y(self):
        """獲取幽靈方塊（預覽位置）的 Y 座標"""
        ghost_y = self.current_y
        while self.is_valid_position(y=ghost_y + 1):
            ghost_y += 1
        return ghost_y
    
    def get_state(self):
        """獲取當前遊戲狀態"""
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
        """壓縮棋盤（RLE 編碼）"""
        # 簡單的行程長度編碼
        result = []
        for row in self.board:
            row_str = ''.join(str(cell) for cell in row)
            result.append(row_str)
        return '|'.join(result)
