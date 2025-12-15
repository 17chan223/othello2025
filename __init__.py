from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import math
import time

# ========= 基本設定 =========
EMPTY = 0
BLACK = 1   # 人間
WHITE = -1  # AI

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1),
]

# 位置評価（角を強く、角隣を弱く、辺を強め）
POS_WEIGHTS = [
    [120, -20,  20,   5,   5,  20, -20, 120],
    [-20, -40,  -5,  -5,  -5,  -5, -40, -20],
    [ 20,  -5,  15,   3,   3,  15,  -5,  20],
    [  5,  -5,   3,   3,   3,   3,  -5,   5],
    [  5,  -5,   3,   3,   3,   3,  -5,   5],
    [ 20,  -5,  15,   3,   3,  15,  -5,  20],
    [-20, -40,  -5,  -5,  -5,  -5, -40, -20],
    [120, -20,  20,   5,   5,  20, -20, 120],
]

def opponent(player: int) -> int:
    return -player

def inside(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8

# ========= 盤面 =========
@dataclass(frozen=True)
class Move:
    r: int
    c: int

class Board:
    def __init__(self):
        self.grid = [[EMPTY for _ in range(8)] for _ in range(8)]
        # 初期配置
        self.grid[3][3] = WHITE
        self.grid[3][4] = BLACK
        self.grid[4][3] = BLACK
        self.grid[4][4] = WHITE

    def copy(self) -> "Board":
        b = Board.__new__(Board)
        b.grid = [row[:] for row in self.grid]
        return b

    def count(self) -> Tuple[int, int]:
        black = sum(1 for r in range(8) for c in range(8) if self.grid[r][c] == BLACK)
        white = sum(1 for r in range(8) for c in range(8) if self.grid[r][c] == WHITE)
        return black, white

    def print(self):
        # 列ラベル
        print("  a b c d e f g h")
        for r in range(8):
            row = []
            for c in range(8):
                v = self.grid[r][c]
                if v == BLACK:
                    row.append("●")
                elif v == WHITE:
                    row.append("○")
                else:
                    row.append("・")
            print(f"{r+1} " + " ".join(row))
        b, w = self.count()
        print(f"score: ●={b}  ○={w}")

    def _flips_in_dir(self, player: int, r: int, c: int, dr: int, dc: int) -> List[Tuple[int, int]]:
        flips = []
        rr, cc = r + dr, c + dc
        if not inside(rr, cc) or self.grid[rr][cc] != opponent(player):
            return []
        while inside(rr, cc) and self.grid[rr][cc] == opponent(player):
            flips.append((rr, cc))
            rr += dr
            cc += dc
        if inside(rr, cc) and self.grid[rr][cc] == player:
            return flips
        return []

    def legal_moves(self, player: int) -> List[Move]:
        moves = []
        for r in range(8):
            for c in range(8):
                if self.grid[r][c] != EMPTY:
                    continue
                ok = False
                for dr, dc in DIRECTIONS:
                    if self._flips_in_dir(player, r, c, dr, dc):
                        ok = True
                        break
                if ok:
                    moves.append(Move(r, c))
        return moves

    def apply_move(self, player: int, move: Move) -> bool:
        if self.grid[move.r][move.c] != EMPTY:
            return False
        flips_all = []
        for dr, dc in DIRECTIONS:
            flips_all.extend(self._flips_in_dir(player, move.r, move.c, dr, dc))
        if not flips_all:
            return False
        self.grid[move.r][move.c] = player
        for rr, cc in flips_all:
            self.grid[rr][cc] = player
        return True

    def has_any_move(self, player: int) -> bool:
        return len(self.legal_moves(player)) > 0

    def game_over(self) -> bool:
        return (not self.has_any_move(BLACK)) and (not self.has_any_move(WHITE))

# ========= 評価関数 =========
def mobility(board: Board, player: int) -> int:
    return len(board.legal_moves(player)) - len(board.legal_moves(opponent(player)))

def positional_score(board: Board, player: int) -> int:
    s = 0
    for r in range(8):
        for c in range(8):
            if board.grid[r][c] == player:
                s += POS_WEIGHTS[r][c]
            elif board.grid[r][c] == opponent(player):
                s -= POS_WEIGHTS[r][c]
    return s

def corner_score(board: Board, player: int) -> int:
    corners = [(0,0),(0,7),(7,0),(7,7)]
    s = 0
    for r,c in corners:
        if board.grid[r][c] == player:
            s += 25
        elif board.grid[r][c] == opponent(player):
            s -= 25
    return s

def disc_diff(board: Board, player: int) -> int:
    b, w = board.count()
    my = b if player == BLACK else w
    op = w if player == BLACK else b
    return my - op

def evaluate(board: Board, player: int) -> float:
    # 終盤は石差を重視
    empties = sum(1 for r in range(8) for c in range(8) if board.grid[r][c] == EMPTY)
    if board.game_over():
        d = disc_diff(board, player)
        if d > 0: return 1e6 + d
        if d < 0: return -1e6 + d
        return 0

    pos = positional_score(board, player)
    cor = corner_score(board, player)
    mob = mobility(board, player)

    # 係数（序盤/中盤/終盤で少し変える）
    if empties > 40:
        return 1.0*pos + 25.0*cor + 4.0*mob
    elif empties > 15:
        return 1.2*pos + 30.0*cor + 6.0*mob
    else:
        return 0.8*pos + 35.0*cor + 2.0*mob + 8.0*disc_diff(board, player)

# ========= AI（αβミニマックス） =========
def order_moves(board: Board, player: int, moves: List[Move]) -> List[Move]:
    # 角優先、位置重みでざっくりソート（枝刈り効率UP）
    def key(m: Move):
        w = POS_WEIGHTS[m.r][m.c]
        if (m.r, m.c) in [(0,0),(0,7),(7,0),(7,7)]:
            w += 1000
        return w
    return sorted(moves, key=key, reverse=True)

def alphabeta(board: Board, player_to_move: int, root_player: int,
              depth: int, alpha: float, beta: float,
              tt: Dict[Tuple[Tuple[int,...], int, int], Tuple[float, Optional[Move]]]) -> Tuple[float, Optional[Move]]:
    # トランスポジションテーブルキー
    key_grid = tuple(tuple(row) for row in board.grid)
    key = (key_grid, player_to_move, depth)
    if key in tt:
        return tt[key]

    if depth == 0 or board.game_over():
        val = evaluate(board, root_player)
        tt[key] = (val, None)
        return val, None

    moves = board.legal_moves(player_to_move)
    if not moves:
        # パス
        val, _ = alphabeta(board, opponent(player_to_move), root_player, depth-1, alpha, beta, tt)
        tt[key] = (val, None)
        return val, None

    best_move = None
    if player_to_move == root_player:
        # 最大化
        value = -math.inf
        for m in order_moves(board, player_to_move, moves):
            b2 = board.copy()
            b2.apply_move(player_to_move, m)
            v, _ = alphabeta(b2, opponent(player_to_move), root_player, depth-1, alpha, beta, tt)
            if v > value:
                value, best_move = v, m
            alpha = max(alpha, value)
            if alpha >= beta:
                break
    else:
        # 最小化
        value = math.inf
        for m in order_moves(board, player_to_move, moves):
            b2 = board.copy()
            b2.apply_move(player_to_move, m)
            v, _ = alphabeta(b2, opponent(player_to_move), root_player, depth-1, alpha, beta, tt)
            if v < value:
                value, best_move = v, m
            beta = min(beta, value)
            if alpha >= beta:
                break

    tt[key] = (value, best_move)
    return value, best_move

def ai_choose_move(board: Board, ai_player: int, max_depth: int = 4, time_limit_sec: float = 1.2) -> Optional[Move]:
    # 反復深化（時間制限まで深くする）
    start = time.time()
    best = None
    tt: Dict[Tuple[Tuple[int,...], int, int], Tuple[float, Optional[Move]]] = {}
    for depth in range(1, max_depth + 1):
        if time.time() - start > time_limit_sec:
            break
        val, move = alphabeta(board, ai_player, ai_player, depth, -math.inf, math.inf, tt)
        if time.time() - start > time_limit_sec:
            break
        if move is not None:
            best = move
    return best

# ========= 入力 =========
def parse_move(s: str) -> Optional[Move]:
    s = s.strip().lower()
    if s in ("pass", "p"):
        return None
    # "d3" 形式
    if len(s) == 2 and s[0] in "abcdefgh" and s[1] in "12345678":
        c = ord(s[0]) - ord("a")
        r = int(s[1]) - 1
        return Move(r, c)
    # "3 4" 形式(1-indexed)
    parts = s.replace(",", " ").split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        r = int(parts[0]) - 1
        c = int(parts[1]) - 1
        if inside(r, c):
            return Move(r, c)
    return None

def move_to_str(m: Move) -> str:
    return f"{chr(ord('a')+m.c)}{m.r+1}"

# ========= ゲームループ =========
def main():
    board = Board()
    human = BLACK
    ai = WHITE

    print("Othello: 人間=●(黒)  AI=○(白)")
    print("入力例: d3  または 3 4   / パスは 'pass'")
    print()

    turn = BLACK  # 黒から
    while not board.game_over():
        board.print()
        print()

        moves = board.legal_moves(turn)
        if not moves:
            print(("●" if turn == BLACK else "○") + " は置ける手がないのでパス。\n")
            turn = opponent(turn)
            continue

        if turn == human:
            while True:
                s = input("あなたの手 (例 d3): ")
                m = parse_move(s)
                if m is None:
                    print("パスはできません（置ける手があります）。もう一度。")
                    continue
                if board.apply_move(human, m):
                    break
                print("その手は置けません。合法手を選んでください。")
        else:
            print("AI思考中...")
            m = ai_choose_move(board, ai_player=ai, max_depth=5, time_limit_sec=1.5)
            if m is None:
                # 念のため
                print("AIはパス。\n")
            else:
                board.apply_move(ai, m)
                print(f"AIの手: {move_to_str(m)}\n")

        turn = opponent(turn)

    board.print()
    b, w = board.count()
    print("\n=== 終局 ===")
    if b > w:
        print(f"あなたの勝ち！ ●={b} ○={w}")
    elif w > b:
        print(f"AIの勝ち。 ●={b} ○={w}")
    else:
        print(f"引き分け。 ●={b} ○={w}")

if __name__ == "__main__":
    main()
