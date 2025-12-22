# othello2025/__init__.py
# sakura 対応: myai(board, stone) -> (x, y) or None
# 強めAI: αβ探索 + 評価関数
# 安全対策: sakura.othello.can_place_x_y を IndexError/範囲外で落ちないようにパッチ

from __future__ import annotations

import math
import random
import copy
from typing import Any, List, Optional, Tuple

__all__ = ["myai"]

# -----------------------------
# sakura 互換: 安全パッチ
# -----------------------------
_OTHELLO = None
_PATCHED = False

def _get_othello():
    global _OTHELLO, _PATCHED
    if _OTHELLO is not None:
        return _OTHELLO

    try:
        from sakura import othello as _othello
    except Exception:
        # sakura が無い環境でも import 自体は通す（テスト等）
        _OTHELLO = None
        return None

    _OTHELLO = _othello

    # can_place_x_y が board[y][x] を直に触って落ちることがあるので、握りつぶす
    if not _PATCHED and hasattr(_othello, "can_place_x_y"):
        old = _othello.can_place_x_y

        def safe_can_place_x_y(board, stone, x, y):
            try:
                if not (isinstance(x, int) and isinstance(y, int)):
                    return False
                if not (0 <= x < 8 and 0 <= y < 8):
                    return False
                return bool(old(board, stone, x, y))
            except Exception:
                # IndexError 含め、全部 False 扱いで落とさない
                return False

        _othello.can_place_x_y = safe_can_place_x_y
        _PATCHED = True

    return _othello


# -----------------------------
# 盤面ユーティリティ
# -----------------------------
WGT = [
    [120, -20,  20,   5,   5,  20, -20, 120],
    [-20, -40,  -5,  -5,  -5,  -5, -40, -20],
    [ 20,  -5,  15,   3,   3,  15,  -5,  20],
    [  5,  -5,   3,   3,   3,   3,  -5,   5],
    [  5,  -5,   3,   3,   3,   3,  -5,   5],
    [ 20,  -5,  15,   3,   3,  15,  -5,  20],
    [-20, -40,  -5,  -5,  -5,  -5, -40, -20],
    [120, -20,  20,   5,   5,  20, -20, 120],
]
CORNERS = {(0,0),(7,0),(0,7),(7,7)}
BAD = {(1,1),(6,1),(1,6),(6,6),
       (0,1),(1,0),(0,6),(1,7),(6,0),(7,1),(6,7),(7,6)}

def _deepcopy_board(board: Any) -> Any:
    try:
        return copy.deepcopy(board)
    except Exception:
        return board

def _cell(board: Any, x: int, y: int):
    # sakura は board[y][x] のはず
    try:
        return board[y][x]
    except Exception:
        return None

def _count_discs(board: Any, stone: Any) -> int:
    n = 0
    for y in range(8):
        for x in range(8):
            if _cell(board, x, y) == stone:
                n += 1
    return n

def _empty_count(board: Any) -> int:
    # sakura は空=0
    n = 0
    for y in range(8):
        for x in range(8):
            v = _cell(board, x, y)
            if v == 0 or v is None:
                n += 1
    return n

def _infer_opponent(board: Any, stone: Any):
    # よくある 1/2 形式なら 3-stone
    if isinstance(stone, int) and stone in (1,2):
        return 3 - stone
    # 盤面から stone 以外の石を探す
    vals = set()
    for y in range(8):
        for x in range(8):
            v = _cell(board, x, y)
            if v not in (0, None):
                vals.add(v)
    for v in vals:
        if v != stone:
            return v
    # どうしても分からない場合（ほぼ起きない）
    return stone

def _legal_moves(board: Any, stone: Any) -> List[Tuple[int,int]]:
    othello = _get_othello()
    if othello is None or not hasattr(othello, "can_place_x_y"):
        return []
    moves = []
    for y in range(8):
        for x in range(8):
            if othello.can_place_x_y(board, stone, x, y):
                moves.append((x,y))
    return moves

def _apply_move(board: Any, stone: Any, move: Tuple[int,int]) -> Optional[Any]:
    """盤面コピーに move を適用して返す。失敗なら None。"""
    othello = _get_othello()
    if othello is None or not hasattr(othello, "place"):
        return None
    x,y = move
    b2 = _deepcopy_board(board)
    try:
        ok = othello.place(b2, stone, x, y)  # sakuraの place は盤面更新して True/False を返す想定
        if ok:
            return b2
        return None
    except Exception:
        return None


# -----------------------------
# 評価関数（強め）
# -----------------------------
def _evaluate(board: Any, me: Any) -> float:
    opp = _infer_opponent(board, me)
    empty = _empty_count(board)

    # positional
    pos = 0
    for y in range(8):
        for x in range(8):
            v = _cell(board, x, y)
            if v == me:
                pos += WGT[y][x]
            elif v == opp:
                pos -= WGT[y][x]

    # corners
    corner = 0
    for (x,y) in CORNERS:
        v = _cell(board, x, y)
        if v == me: corner += 250
        elif v == opp: corner -= 250

    # mobility
    m_me = len(_legal_moves(board, me))
    m_op = len(_legal_moves(board, opp))
    mob = 0.0
    if m_me + m_op > 0:
        mob = 100.0 * (m_me - m_op) / (m_me + m_op)

    # danger squares (only if corner empty)
    danger = 0
    for (x,y) in BAD:
        cx = 0 if x < 4 else 7
        cy = 0 if y < 4 else 7
        if _cell(board, cx, cy) == 0:
            v = _cell(board, x, y)
            if v == me: danger -= 50
            elif v == opp: danger += 50

    # disc diff (late game heavy)
    d_me = _count_discs(board, me)
    d_op = _count_discs(board, opp)
    disc = 0.0
    if d_me + d_op > 0:
        disc = 100.0 * (d_me - d_op) / (d_me + d_op)

    if empty >= 40:       # opening
        return pos + corner + mob + 0.2*disc + danger
    elif empty >= 15:     # mid
        return 0.9*pos + corner + 0.7*mob + 0.8*disc + danger
    else:                 # end
        return 0.4*pos + corner + 0.2*mob + 2.2*disc + danger


# -----------------------------
# αβ探索
# -----------------------------
def _order_moves(board: Any, me: Any, moves: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    # 角優先、危険マスは後ろ、盤面重みも利用
    def key(m):
        x,y = m
        if (x,y) in CORNERS:
            return -10_000
        k = -WGT[y][x]
        if (x,y) in BAD:
            k += 500
        return k
    return sorted(moves, key=key)

def _alphabeta(board: Any, turn: Any, me: Any, depth: int, alpha: float, beta: float) -> float:
    opp = _infer_opponent(board, me)

    if depth <= 0:
        return _evaluate(board, me)

    moves = _legal_moves(board, turn)
    # 終局（両者打てない）
    if not moves:
        other = opp if turn == me else me
        if not _legal_moves(board, other):
            return _evaluate(board, me)
        # パス
        return _alphabeta(board, other, me, depth-1, alpha, beta)

    moves = _order_moves(board, me, moves)

    if turn == me:
        v = -1e18
        for mv in moves:
            b2 = _apply_move(board, turn, mv)
            if b2 is None:
                continue
            v = max(v, _alphabeta(b2, opp, me, depth-1, alpha, beta))
            alpha = max(alpha, v)
            if alpha >= beta:
                break
        return v
    else:
        v = 1e18
        for mv in moves:
            b2 = _apply_move(board, turn, mv)
            if b2 is None:
                continue
            v = min(v, _alphabeta(b2, me, me, depth-1, alpha, beta))
            beta = min(beta, v)
            if alpha >= beta:
                break
        return v


# -----------------------------
# 公開AI: myai(board, stone)
# -----------------------------
def myai(board: Any, stone: Any):
    """
    sakura が呼ぶAI関数:
      myai(board, stone) -> (x, y) or None
    """
    othello = _get_othello()
    if othello is None:
        return None

    # 必ず int 範囲で返す
    moves = _legal_moves(board, stone)
    if not moves:
        return None

    # 深さ調整（重すぎない範囲で強め）
    empty = _empty_count(board)
    # 速度と強さのバランス：中盤4、終盤5（Colabでも現実的）
    depth = 4 if empty > 18 else 5

    # 角があるなら即
    corners = [m for m in moves if m in CORNERS]
    if corners:
        return random.choice(corners)

    best_val = -1e18
    best_moves = []
    opp = _infer_opponent(board, stone)

    for mv in _order_moves(board, stone, moves):
        b2 = _apply_move(board, stone, mv)
        if b2 is None:
            continue
        val = _alphabeta(b2, opp, stone, depth-1, -1e18, 1e18)
        if val > best_val:
            best_val = val
            best_moves = [mv]
        elif abs(val - best_val) < 1e-9:
            best_moves.append(mv)

    # 万一 b2 が全部 None だった時の保険（ここで反則は避ける）
    if not best_moves:
        return moves[0]

    x,y = random.choice(best_moves)
    # 絶対に範囲外を返さない
    if not (0 <= x < 8 and 0 <= y < 8):
        x,y = moves[0]
    return (int(x), int(y))
