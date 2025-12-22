def myai():
    import random
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets

    EMPTY, BLACK, WHITE = ".", "B", "W"
    DIRS = [(-1,-1),(-1,0),(-1,1),
            (0,-1),       (0,1),
            (1,-1),(1,0),(1,1)]

    def opp(p): return WHITE if p == BLACK else BLACK
    def inside(r,c): return 0 <= r < 8 and 0 <= c < 8

    def new_board():
        b = [[EMPTY]*8 for _ in range(8)]
        b[3][3]=WHITE; b[3][4]=BLACK
        b[4][3]=BLACK; b[4][4]=WHITE
        return b

    def flips_dir(b,p,r,c,dr,dc):
        rr,cc=r+dr,c+dc; out=[]
        while inside(rr,cc) and b[rr][cc]==opp(p):
            out.append((rr,cc)); rr+=dr; cc+=dc
        return out if out and inside(rr,cc) and b[rr][cc]==p else []

    def legal(b,p):
        return [(r,c) for r in range(8) for c in range(8)
                if b[r][c]==EMPTY and
                any(flips_dir(b,p,r,c,dr,dc) for dr,dc in DIRS)]

    def move(b,p,r,c):
        f=[]
        for dr,dc in DIRS:
            f+=flips_dir(b,p,r,c,dr,dc)
        if not f: return False
        b[r][c]=p
        for rr,cc in f: b[rr][cc]=p
        return True

    board = new_board()
    turn = BLACK

    box = widgets.Text(placeholder="d3", description="Move:")
    btn = widgets.Button(description="Place", button_style="primary")
    msg = widgets.HTML()

    def draw():
        clear_output(wait=True)
        html="<table style='border-collapse:collapse'>"
        html+="<tr><td></td>"+"".join(f"<td>{c}</td>" for c in "abcdefgh")+"</tr>"
        for r in range(8):
            html+=f"<tr><td>{r+1}</td>"
            for c in range(8):
                ch="●" if board[r][c]==BLACK else "○" if board[r][c]==WHITE else ""
                html+=f"<td style='width:40px;height:40px;background:#2e7d32;color:white;text-align:center;font-size:22px;border:1px solid black'>{ch}</td>"
            html+="</tr>"
        html+="</table>"
        display(HTML("<h3>Othello (auto start)</h3>"))
        display(HTML(html))
        display(widgets.HBox([box,btn]))
        display(msg)

    def on_click(_):
        nonlocal turn
        s=box.value.lower().replace(" ",""); box.value=""
        if len(s)<2: return
        r=int(s[1])-1 if s[0].isalpha() else int(s[:-1])-1
        c=ord(s[0])-97 if s[0].isalpha() else ord(s[-1])-97
        if not inside(r,c): return
        if move(board,BLACK,r,c):
            draw()

    btn.on_click(on_click)
    draw()


# ===== ここが最重要 =====
# Colabで import された瞬間に自動起動
try:
    import google.colab
    myai()
except Exception:
    pass
