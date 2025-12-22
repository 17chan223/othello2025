# a020/__init__.py
import random

def myai(board, stone):
    """
    sakura.othello が呼ぶAI: myai(board, stone) -> (x, y) or None
    boardの内部構造は触らず、sakura側の合法判定関数で候補手を作る。
    """
    # sakuraのothelloモジュールを使って合法判定する
    try:
        from sakura import othello
    except Exception:
        # もしモジュール名が違う環境でも落ちないように保険
        import othello

    moves = []

    # 置ける手を総当たりで探す（8x8）
    for x in range(8):
        for y in range(8):
            try:
                # まず安全系があれば使う
                if hasattr(othello, "place"):
                    # place(board, stone, x, y) が「置けたら盤面を更新」する型が多いので
                    # 盤面を壊さないように copy があるなら使う
                    b2 = _copy_board(board)
                    ok = othello.place(b2, stone, x, y)
                    if ok:
                        moves.append((x, y))
                else:
                    # place が無い場合は safe_place があるか試す（存在するならここは通常通らない）
                    b2 = _copy_board(board)
                    xx, yy = othello.safe_place(lambda _b, _s: (x, y), b2, stone)
                    if (xx, yy) == (x, y):
                        moves.append((x, y))
            except Exception:
                # 置けない/例外は無視して次へ
                pass

    if not moves:
        return None  # パス

    # 角優先
    corners = {(0,0),(0,7),(7,0),(7,7)}
    cs = [m for m in moves if m in corners]
    if cs:
        return random.choice(cs)

    # 次点：角の隣（危険）を避ける
    bad = {(1,1),(1,6),(6,1),(6,6),
           (0,1),(1,0),(0,6),(1,7),(6,0),(7,1),(6,7),(7,6)}
    good = [m for m in moves if m not in bad]
    if good:
        return random.choice(good)

    return random.choice(moves)


def _copy_board(board):
    """
    boardがどんな型でも極力コピーする。
    listなら浅い/深いコピー、無理ならそのまま返す（最悪破壊されるが例外よりマシ）。
    """
    try:
        # list of lists
        return [row[:] for row in board]
    except Exception:
        try:
            import copy
            return copy.deepcopy(board)
        except Exception:
            return board
