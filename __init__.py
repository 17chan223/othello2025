def myai():
    import random
    import math
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets

    EMPTY, BLACK, WHITE = ".", "B", "W"
    DIRS = [(-1,-1),(-1,0),(-1,1),
            (0,-1),       (0,1),
            (1,-1),(1,0),(1,1)]

    # 典型的な盤面重み（角が最強、角近辺は危険）
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
    CORNERS = {(0,0),(0,7),(7,0),(7,7)}
    X_SQ = {(1,1),(1,6),(6,1),(6,6)}
    C_SQ = {(0,1),(1,0),(0,6),(1,7),(6,0),(7,1),(6,7),(7,6)}

    def opp(p): return WHITE if p == BLACK else BLACK
    def inside(r,c): return 0 <= r < 8 and 0 <= c < 8

    def new_board():
        b = [[EMPTY]*8 for _ in range(8)]
        b[3][3]=WHITE; b[3][4]=BLACK
        b[4][3]=BLACK; b[4][4]=WHITE
        return b

    def count(b):
        bc = sum(x==BLACK for row in b for x in row)
        wc = sum(x==WHITE for row in b for x in row)
        return bc, wc

    def empties(b):
        return sum(x==EMPTY for row in b for x in row)

    def flips_dir(b, p, r, c, dr, dc):
        rr, cc = r+dr, c+dc
        o = opp(p)
        out = []
        while inside(rr,cc) and b[rr][cc] == o:
            out.append((rr,cc))
            rr += dr; cc += dc
        if out and inside(rr,cc) and b[rr][cc] == p:
            return out
        return []

    def legal_moves(b, p):
        mv = []
        for r in range(8):
            for c in range(8):
                if b[r][c] != EMPTY: 
                    continue
                ok = False
                for dr,dc in DIRS:
                    if flips_dir(b,p,r,c,dr,dc):
                        ok = True
                        break
                if ok:
                    mv.append((r,c))
        return mv

    # 高速化：打って、ひっくり返した座標リストを返す（undo用）
    def do_move(b, p, r, c):
        if b[r][c] != EMPTY:
            return None
        allflips = []
        for dr,dc in DIRS:
            allflips.extend(flips_dir(b,p,r,c,dr,dc))
        if not allflips:
            return None
        b[r][c] = p
        for rr,cc in allflips:
            b[rr][cc] = p
        return allflips

    def undo_move(b, p, r, c, flips):
        b[r][c] = EMPTY
        o = opp(p)
        for rr,cc in flips:
            b[rr][cc] = o

    def parse(s):
        s = (s or "").strip().lower().replace(" ", "")
        if len(s) < 2:
            return None
        if s[0].isalpha():
            col = s[0]; row = s[1:]
        else:
            row = s[:-1]; col = s[-1]
        if not ("a" <= col <= "h"):
            return None
        try:
            r = int(row)-1
        except:
            return None
        c = ord(col)-97
        if not inside(r,c):
            return None
        return (r,c)

    def to_coord(r,c):
        return chr(97+c) + str(r+1)

    def moves_text(mvs):
        return " ".join(sorted(to_coord(r,c) for r,c in mvs)) if mvs else "(none)"

    # --- 強い評価関数 ---
    def evaluate(b):
        """
        WHITE（CPU）視点で大きいほど良い
        - 盤面重み
        - 角
        - 機動力（合法手の数）
        - 角周り（角が空のときのX/C罰）
        - 終盤は石差比重UP
        """
        bc, wc = count(b)
        e = empties(b)

        # positional
        pos = 0
        for r in range(8):
            row = b[r]
            wr = WGT[r]
            for c in range(8):
                if row[c] == WHITE:
                    pos += wr[c]
                elif row[c] == BLACK:
                    pos -= wr[c]

        # corners
        corner = 0
        for r,c in CORNERS:
            if b[r][c] == WHITE: corner += 200
            elif b[r][c] == BLACK: corner -= 200

        # mobility
        mW = len(legal_moves(b, WHITE))
        mB = len(legal_moves(b, BLACK))
        mob = 0
        if mW + mB != 0:
            mob = 80 * (mW - mB) / (mW + mB)

        # corner adjacency penalty if corner empty
        danger = 0
        for (r,c) in (X_SQ | C_SQ):
            cr = 0 if r < 4 else 7
            cc = 0 if c < 4 else 7
            if b[cr][cc] == EMPTY:
                if b[r][c] == WHITE: danger -= 60
                elif b[r][c] == BLACK: danger += 60

        # disc diff: late game weight
        disc = 0
        if bc + wc != 0:
            disc = 100 * (wc - bc) / (wc + bc)

        # 終盤ほど石差を重く、序盤は機動力と位置を重視
        if e >= 40:      # 序盤
            return pos + corner + mob + 0.2*disc + danger
        elif e >= 15:    # 中盤
            return 0.9*pos + corner + 0.7*mob + 0.8*disc + danger
        else:            # 終盤
            return 0.4*pos + corner + 0.2*mob + 2.2*disc + danger

    # --- αβ探索 ---
    TT = {}  # transposition table: (key, depth, player) -> value

    def board_key(b):
        # 文字列化（軽量TT用）
        return "".join("".join(row) for row in b)

    def order_moves(b, p, mvs):
        # 角優先 + 盤面重みが良い手を先に（枝刈り効く）
        def score(m):
            r,c = m
            s = 0
            if (r,c) in CORNERS: s += 10000
            s += WGT[r][c] * (1 if p == WHITE else -1)
            return -s
        return sorted(mvs, key=score)

    def alphabeta(b, p, depth, alpha, beta):
        key = (board_key(b), depth, p)
        if key in TT:
            return TT[key]

        mvs = legal_moves(b, p)
        if depth == 0 or (not mvs and not legal_moves(b, opp(p))):
            val = evaluate(b)
            TT[key] = val
            return val

        if not mvs:
            # pass
            val = alphabeta(b, opp(p), depth-1, alpha, beta)
            TT[key] = val
            return val

        mvs = order_moves(b, p, mvs)

        if p == WHITE:  # maximize
            best = -1e18
            for r,c in mvs:
                flips = do_move(b, p, r, c)
                val = alphabeta(b, opp(p), depth-1, alpha, beta)
                undo_move(b, p, r, c, flips)
                if val > best: best = val
                if best > alpha: alpha = best
                if alpha >= beta:
                    break
            TT[key] = best
            return best
        else:           # minimize
            best = 1e18
            for r,c in mvs:
                flips = do_move(b, p, r, c)
                val = alphabeta(b, opp(p), depth-1, alpha, beta)
                undo_move(b, p, r, c, flips)
                if val < best: best = val
                if best < beta: beta = best
                if alpha >= beta:
                    break
            TT[key] = best
            return best

    def choose_cpu_move(b):
        mvs = legal_moves(b, WHITE)
        if not mvs:
            return None

        e = empties(b)
        # 深さ：Colabで重すぎない範囲で段階的に強化
        # 序盤～中盤: 4, 終盤: 5（空きが少ないほど読める）
        depth = 4 if e > 18 else 5

        # 角があれば即取り（探索より確実に強い）
        corners = [m for m in mvs if m in CORNERS]
        if corners:
            return random.choice(corners)

        TT.clear()
        best_val = -1e18
        best = []
        mvs2 = order_moves(b, WHITE, mvs)

        alpha, beta = -1e18, 1e18
        for r,c in mvs2:
            flips = do_move(b, WHITE, r, c)
            val = alphabeta(b, BLACK, depth-1, alpha, beta)
            undo_move(b, WHITE, r, c, flips)

            if val > best_val:
                best_val = val
                best = [(r,c)]
            elif abs(val - best_val) < 1e-9:
                best.append((r,c))

            if best_val > alpha:
                alpha = best_val

        return random.choice(best)

    # --- UI（Colab用）---
    board = new_board()
    turn = BLACK
    passes = 0
    over = False

    move_box = widgets.Text(value="", placeholder="e.g. d3", description="Move:", layout=widgets.Layout(width="220px"))
    place_btn = widgets.Button(description="Place", button_style="primary")
    reset_btn = widgets.Button(description="Reset", button_style="warning")
    msg = widgets.HTML()

    def board_html(b, highlight):
        hl = set(highlight)
        cols = "abcdefgh"
        html = []
        html.append("<table style='border-collapse:collapse'>")
        html.append("<tr><td style='width:22px'></td>" + "".join(
            f"<td style='width:40px;text-align:center;font-weight:700'>{cols[c]}</td>" for c in range(8)
        ) + "</tr>")
        for r in range(8):
            html.append("<tr>")
            html.append(f"<td style='width:22px;text-align:center;font-weight:700'>{r+1}</td>")
            for c in range(8):
                bg = "#a8d5a2" if (r,c) in hl else "#2e7d32"
                v = b[r][c]
                ch = "●" if v == BLACK else ("○" if v == WHITE else "")
                html.append(
                    f"<td style='width:40px;height:40px;text-align:center;"
                    f"background:{bg};color:white;font-size:22px;font-weight:700;"
                    f"border:1px solid #222'>{ch}</td>"
                )
            html.append("</tr>")
        html.append("</table>")
        return "".join(html)

    def render():
        clear_output(wait=True)
        bc, wc = count(board)
        human_valid = legal_moves(board, BLACK) if (turn == BLACK and not over) else []
        display(HTML("<h3>Othello (Human=B vs Strong CPU=W) — myai</h3>"))
        display(HTML(f"<div style='margin:6px 0'>Score: B={bc}  W={wc} &nbsp; | &nbsp; Turn: <b>{turn}</b></div>"))
        display(HTML(board_html(board, human_valid)))
        if not over:
            display(HTML(f"<div>Valid moves (You): <b>{moves_text(legal_moves(board, BLACK))}</b></div>"))
        display(widgets.HBox([move_box, place_btn, reset_btn]))
        display(msg)

    def check_end():
        nonlocal over
        full = all(x != EMPTY for row in board for x in row)
        if passes >= 2 or full:
            bc, wc = count(board)
            if bc > wc:
                res = "You win!"
            elif wc > bc:
                res = "CPU wins!"
            else:
                res = "Draw!"
            msg.value = f"<b>Game Over:</b> {res}"
            over = True
            return True
        return False

    def cpu_turn():
        nonlocal turn, passes
        while (not over) and turn == WHITE:
            mvs = legal_moves(board, WHITE)
            if mvs:
                passes = 0
                mv = choose_cpu_move(board)
                r,c = mv
                do_move(board, WHITE, r, c)
                msg.value = f"CPU played: <b>{to_coord(r,c)}</b>"
                turn = BLACK
            else:
                passes += 1
                msg.value = "CPU has no valid moves → PASS"
                turn = BLACK
            if check_end():
                return

    def on_place(_):
        nonlocal turn, passes
        if over:
            msg.value = "Game is over. Press Reset."
            render()
            return
        if turn != BLACK:
            msg.value = "Wait for CPU..."
            render()
            return

        human_mvs = legal_moves(board, BLACK)
        if not human_mvs:
            passes += 1
            msg.value = "You have no valid moves → PASS"
            turn = WHITE
            if check_end():
                render()
                return
            cpu_turn()
            render()
            return

        mv = parse(move_box.value)
        move_box.value = ""
        if mv is None:
            msg.value = "Invalid format. Use like d3 (or 3d)."
            render()
            return
        r,c = mv
        flips = do_move(board, BLACK, r, c)
        if flips is None:
            msg.value = "Illegal move. Choose from valid moves."
            render()
            return

        passes = 0
        msg.value = f"You played: <b>{to_coord(r,c)}</b>"
        turn = WHITE
        if check_end():
            render()
            return
        cpu_turn()
        render()

    def on_reset(_):
        nonlocal board, turn, passes, over
        board = new_board()
        turn = BLACK
        passes = 0
        over = False
        msg.value = "Reset done."
        move_box.value = ""
        render()

    place_btn.on_click(on_place)
    reset_btn.on_click(on_reset)

    render()
