# Colab-friendly Othello (Human vs CPU) using ipywidgets
# Run this cell in Google Colab.

import random
import time
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

EMPTY = "."
BLACK = "B"  # Human
WHITE = "W"  # CPU

DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
              (0, -1),          (0, 1),
              (1, -1),  (1, 0), (1, 1)]

CORNERS = {(0,0),(0,7),(7,0),(7,7)}
X_SQUARES = {(1,1),(1,6),(6,1),(6,6)}
C_SQUARES = {(0,1),(1,0),(0,6),(1,7),(6,0),(7,1),(6,7),(7,6)}

def opponent(p):
    return WHITE if p == BLACK else BLACK

def in_bounds(r,c):
    return 0 <= r < 8 and 0 <= c < 8

def new_board():
    b = [[EMPTY]*8 for _ in range(8)]
    b[3][3] = WHITE
    b[3][4] = BLACK
    b[4][3] = BLACK
    b[4][4] = WHITE
    return b

def count_stones(board):
    b = sum(cell == BLACK for row in board for cell in row)
    w = sum(cell == WHITE for row in board for cell in row)
    return b, w

def flippable_in_direction(board, player, r, c, dr, dc):
    rr, cc = r+dr, c+dc
    opp = opponent(player)
    flips = []
    while in_bounds(rr,cc) and board[rr][cc] == opp:
        flips.append((rr,cc))
        rr += dr
        cc += dc
    if flips and in_bounds(rr,cc) and board[rr][cc] == player:
        return flips
    return []

def get_valid_moves(board, player):
    moves = []
    for r in range(8):
        for c in range(8):
            if board[r][c] != EMPTY:
                continue
            for dr, dc in DIRECTIONS:
                if flippable_in_direction(board, player, r, c, dr, dc):
                    moves.append((r,c))
                    break
    return moves

def apply_move(board, player, r, c):
    if board[r][c] != EMPTY:
        return False
    all_flips = []
    for dr, dc in DIRECTIONS:
        all_flips += flippable_in_direction(board, player, r, c, dr, dc)
    if not all_flips:
        return False
    board[r][c] = player
    for rr, cc in all_flips:
        board[rr][cc] = player
    return True

def copy_board(board):
    return [row[:] for row in board]

def to_coord(r,c):
    return chr(ord('a')+c) + str(r+1)

def parse_move(s):
    s = (s or "").strip().lower().replace(" ", "")
    if len(s) < 2:
        return None
    # letter+digit or digit+letter
    if s[0].isalpha() and s[1:].isdigit():
        col_ch = s[0]
        row_ch = s[1:]
    elif s[-1].isalpha() and s[:-1].isdigit():
        row_ch = s[:-1]
        col_ch = s[-1]
    else:
        return None
    if not ("a" <= col_ch <= "h"):
        return None
    try:
        row = int(row_ch) - 1
    except:
        return None
    col = ord(col_ch) - ord('a')
    if not in_bounds(row,col):
        return None
    return (row,col)

def evaluate_simple(board, cpu):
    # stone diff
    b_cnt, w_cnt = count_stones(board)
    diff = (w_cnt - b_cnt) if cpu == WHITE else (b_cnt - w_cnt)

    # corners
    corner_score = 0
    for (r,c) in CORNERS:
        if board[r][c] == cpu:
            corner_score += 50
        elif board[r][c] == opponent(cpu):
            corner_score -= 50

    # danger near empty corners
    danger_score = 0
    near = X_SQUARES | C_SQUARES
    for (r,c) in near:
        cr = 0 if r < 4 else 7
        cc = 0 if c < 4 else 7
        if board[cr][cc] == EMPTY:
            if board[r][c] == cpu:
                danger_score -= 12
            elif board[r][c] == opponent(cpu):
                danger_score += 12

    return diff + corner_score + danger_score

def cpu_choose_move(board, cpu):
    moves = get_valid_moves(board, cpu)
    if not moves:
        return None
    corners = [m for m in moves if m in CORNERS]
    if corners:
        return random.choice(corners)

    best_score = None
    best_moves = []
    for (r,c) in moves:
        b2 = copy_board(board)
        apply_move(b2, cpu, r, c)
        sc = evaluate_simple(b2, cpu)
        if best_score is None or sc > best_score:
            best_score = sc
            best_moves = [(r,c)]
        elif sc == best_score:
            best_moves.append((r,c))
    return random.choice(best_moves)

def board_html(board, valid_moves_for_human):
    # render as HTML table (green board). highlight valid moves.
    vm = set(valid_moves_for_human)
    def cell_style(r,c,cell):
        base = "width:38px;height:38px;text-align:center;vertical-align:middle;border:1px solid #333;"
        if (r,c) in vm:
            base += "background:#a8d5a2;"  # highlight
        else:
            base += "background:#2e7d32;"
        base += "font-size:22px;font-weight:700;color:white;"
        return base

    cols = "abcdefgh"
    html = []
    html.append("<div style='font-family:monospace'>")
    html.append("<div style='margin-bottom:6px'>Columns: a b c d e f g h</div>")
    html.append("<table style='border-collapse:collapse'>")
    # header row
    html.append("<tr><td style='width:24px'></td>")
    for c in range(8):
        html.append(f"<td style='width:38px;text-align:center;font-weight:700'>{cols[c]}</td>")
    html.append("</tr>")
    for r in range(8):
        html.append("<tr>")
        html.append(f"<td style='width:24px;text-align:center;font-weight:700'>{r+1}</td>")
        for c in range(8):
            v = board[r][c]
            ch = "●" if v == BLACK else ("○" if v == WHITE else "")
            html.append(f"<td style='{cell_style(r,c,v)}'>{ch}</td>")
        html.append("</tr>")
    html.append("</table></div>")
    return "".join(html)

# ---- UI / Game State ----
board = new_board()
turn = BLACK
consecutive_passes = 0
game_over = False

move_box = widgets.Text(
    value="",
    placeholder="e.g. d3",
    description="Move:",
    layout=widgets.Layout(width="220px")
)
place_btn = widgets.Button(description="Place", button_style="primary")
reset_btn = widgets.Button(description="Reset", button_style="warning")
msg = widgets.HTML("")
out = widgets.Output()

def status_text():
    b_cnt, w_cnt = count_stones(board)
    return f"Score: B={b_cnt}  W={w_cnt} &nbsp; | &nbsp; Turn: <b>{turn}</b> (You=B, CPU=W)"

def valid_moves_text(moves):
    return "Valid moves: " + (" ".join(sorted(to_coord(r,c) for r,c in moves)) if moves else "(none)")

def render():
    clear_output(wait=True)
    human_valid = get_valid_moves(board, BLACK)
    display(HTML("<h3>Othello (Human vs CPU) - Colab</h3>"))
    display(HTML(f"<div style='margin:6px 0'>{status_text()}</div>"))
    display(HTML(board_html(board, human_valid if turn == BLACK and not game_over else [])))
    display(widgets.HBox([move_box, place_btn, reset_btn]))
    display(msg)

def end_if_needed():
    global game_over
    full = all(cell != EMPTY for row in board for cell in row)
    if consecutive_passes >= 2 or full:
        b_cnt, w_cnt = count_stones(board)
        if b_cnt > w_cnt:
            result = "BLACK (You) wins!"
        elif w_cnt > b_cnt:
            result = "WHITE (CPU) wins!"
        else:
            result = "Draw!"
        game_over = True
        msg.value = f"<b>Game Over:</b> {result}"
        return True
    return False

def do_cpu_turns_if_needed():
    global turn, consecutive_passes
    # CPU plays whenever it's CPU's turn, handle passes too.
    while not game_over and turn == WHITE:
        cpu_moves = get_valid_moves(board, WHITE)
        if cpu_moves:
            consecutive_passes = 0
            mv = cpu_choose_move(board, WHITE)
            r, c = mv
            apply_move(board, WHITE, r, c)
            msg.value = f"CPU plays: <b>{to_coord(r,c)}</b>"
            turn = BLACK
        else:
            consecutive_passes += 1
            msg.value = "CPU has no valid moves → PASS"
            turn = BLACK
        if end_if_needed():
            return

def on_place(_):
    global turn, consecutive_passes, game_over
    if game_over:
        msg.value = "Game is over. Press Reset."
        render()
        return
    if turn != BLACK:
        msg.value = "Wait for CPU..."
        render()
        return

    human_moves = get_valid_moves(board, BLACK)
    if not human_moves:
        # human must pass
        consecutive_passes += 1
        msg.value = "You have no valid moves → PASS"
        turn = WHITE
        if end_if_needed():
            render()
            return
        do_cpu_turns_if_needed()
        render()
        return

    mv = parse_move(move_box.value)
    move_box.value = ""
    if mv is None:
        msg.value = "Invalid format. Use like d3 (or 3d)."
        render()
        return

    r, c = mv
    if not apply_move(board, BLACK, r, c):
        msg.value = "Illegal move. Choose from valid moves."
        render()
        return

    consecutive_passes = 0
    msg.value = f"You played: <b>{to_coord(r,c)}</b>"
    turn = WHITE

    if end_if_needed():
        render()
        return

    do_cpu_turns_if_needed()
    render()

def on_reset(_):
    global board, turn, consecutive_passes, game_over
    board = new_board()
    turn = BLACK
    consecutive_passes = 0
    game_over = False
    msg.value = "Reset done."
    move_box.value = ""
    render()

place_btn.on_click(on_place)
reset_btn.on_click(on_reset)

render()
