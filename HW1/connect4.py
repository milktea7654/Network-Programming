ROWS, COLS = 6, 7
EMPTY = 0
A_STONE = 1
B_STONE = 2

class Connect4:
    def __init__(self):
        self.board = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]
        self.turn = 'A'  
        self.winner = None

    def copy_state(self):
        return {
            'board': [row[:] for row in self.board],
            'turn': self.turn,
            'winner': self.winner
        }

    def drop(self, col):
        if self.winner is not None:
            raise ValueError('game finished')
        if not (0 <= col < COLS):
            raise ValueError('invalid column')
        stone = A_STONE if self.turn == 'A' else B_STONE
        for r in range(ROWS-1, -1, -1):
            if self.board[r][col] == EMPTY:
                self.board[r][col] = stone
                if self._check_win(r, col, stone):
                    self.winner = self.turn
                elif all(self.board[0][c] != EMPTY for c in range(COLS)):
                    self.winner = 'draw'
                else:
                    self.turn = 'B' if self.turn == 'A' else 'A'
                return
        raise ValueError('column full')

    def _check_win(self, r, c, stone):
        return any(self._count_dir(r, c, dr, dc, stone) + self._count_dir(r, c, -dr, -dc, stone) - 1 >= 4
                   for dr, dc in [(0,1),(1,0),(1,1),(1,-1)])

    def _count_dir(self, r, c, dr, dc, stone):
        cnt = 0
        i, j = r, c
        while 0 <= i < ROWS and 0 <= j < COLS and self.board[i][j] == stone:
            cnt += 1
            i += dr
            j += dc
        return cnt