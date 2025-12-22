# a020/__init__.py
import random

def myai(board, stone):
    """
    sakura.othello が呼ぶAI関数
      - board: 盤面
      - stone: 手番（たぶん othello.BLACK / othello.WHITE など）
    戻り値:
      - (x, y) 形式（※ sakura側は x,y = ... と受け取っている）
    """
    moves = _valid_moves(board, stone)
    if not moves:
        return None  # 置けないならパス（sakura側が処理する）

    # 角優先
    corners = {(0,0),(0,7),(7,0),(7,7)}
    corner_moves = [m for m in moves if m in corners]
    if corner_moves:
        return random.choice(corner_moves)

    # それ以外：簡易評価（角周りは避ける、反転数が多いほど良い）
    best = None
    best_score = -10**9
    for x, y in moves:
        sc = _move_score(board, stone, x, y)
        if sc > best_score:
            best_score = sc
            best = (x, y)
    return best


# ---- 以下は内部処理 ----

DIRS = [(-1,-1),(-1,0),(-1,1),
        (0,-1),       (0,1),
        (1,-1),(1,0),(1,1)]

# 角の斜め/隣（序盤危険）
X_SQ = {(1,1),(1,6),(6,1),(6,6)}
C_SQ = {(0,1),(1,0),(0,6),(1,7),(6,0),(7,1),(6,7),(7,6)}

def _inside(x, y):
    return 0 <= x < 8 and 0 <= y < 8

def _cell(board, x, y):
    # board[x][y] でも board[y][x] でもあり得るので、両方試す
    try:
        return board[x][y]
    except Exception:
        return board[y][x]

def _set_cell(board, x, y, v):
    try:
        board[x][y] = v
    except Exception:
        board[y][x] = v

def _is_empty(v):
    # sakura側の空表現が '.' や 0 など複数あり得るので広めに対応
    return v in (0, ".", "0", None, " ")

def _opp(stone):
    # 石の表現が文字でも数値でも「異なる値」として扱えるように
    # board内に stone 以外の「もう一方の石」を探して推定するのが本当は安全だが、
    # sakuraは通常 BLACK/WHITE の2値なので、ここは board を見て推定する。
    return None  # 呼び出し側で推定する

def _infer_opponent(board, stone):
    vals = set()
    for i in range(8):
        for j in range(8):
            v = _cell(board, i, j)
            if not _is_empty(v):
                vals.add(v)
    # 盤面に2種類あるなら stoneじゃない方
    for v in vals:
        if v != stone:
            return v
    # まだ1種類しかないなら「stoneと違う適当な値」は作れないので、
    # ここでは stone を返してしまう（この場合そもそも合法手判定に支障が出るが、初期盤面なら通常2種ある）
    return stone

def _flips(board, stone, x, y, dx, dy, opp):
    xx, yy = x + dx, y + dy
    out = []
    while _inside(xx, yy) and _cell(board, xx, yy) == opp:
        out.append((xx, yy))
        xx += dx
        yy += dy
    if out and _inside(xx, yy) and _cell(board, xx, yy) == stone:
        return out
    return []

def _valid_moves(board, stone):
    opp = _infer_opponent(board, stone)
    moves = []
    for x in range(8):
        for y in range(8):
            if not _is_empty(_cell(board, x, y)):
                continue
            ok = False
            for dx, dy in DIRS:
                if _flips(board, stone, x, y, dx, dy, opp):
                    ok = True
                    break
            if ok:
                moves.append((x, y))
    return moves

def _move_score(board, stone, x, y):
    # 危険マスを避ける（角が空いてる序盤ほど効くが簡易でOK）
    score = 0
    if (x, y) in X_SQ:
        score -= 30
    if (x, y) in C_SQ:
        score -= 15

    # 反転数が多いほど加点
    opp = _infer_opponent(board, stone)
    flips = 0
    for dx, dy in DIRS:
        flips += len(_flips(board, stone, x, y, dx, dy, opp))
    score += flips

    return score
