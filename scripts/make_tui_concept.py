"""Concept animation of the OpenJev TUI running a real case (the maze) from cached data.

No API calls: replays results/maze.json (real Jev decisions) inside a mock-up of the
OpenJev terminal UI. Left pane: live maze. Right pane: streaming JSON answer, per-move
probability bars, and rolling confidence / latency sparklines.

    .venv/bin/python scripts/make_tui_concept.py
    -> docs/assets/tui-maze-concept.gif, docs/assets/tui-maze-concept.png
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STEPS = json.loads((ROOT / "results" / "maze.json").read_text())
OUT = ROOT / "docs" / "assets"

MAZE = [
    "##########",
    "#S.....#.#",
    "#.####.#.#",
    "#.#..#.#.#",
    "#.#.##.#.#",
    "#.#....#.#",
    "#.######.#",
    "#........#",
    "#.######G#",
    "##########",
]
MOVES = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
ARROW = {"up": "↑", "down": "↓", "left": "←", "right": "→"}

W, H = 1280, 760
BG = (13, 17, 23)
PANEL = (22, 27, 34)
BORDER = (48, 54, 61)
FG = (230, 237, 243)
DIM = (139, 148, 158)
CYAN = (56, 189, 248)
MAGENTA = (232, 121, 249)
YELLOW = (250, 204, 21)
GREEN = (74, 222, 128)
RED = (248, 113, 113)
GREY = (70, 76, 84)
WALL = (30, 36, 44)
FLOOR = (44, 50, 60)
PATH = (36, 99, 140)

FONT = "/System/Library/Fonts/Menlo.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


F = font(16)
FB = font(16, True)
FS = font(13)
FT = font(22, True)
FM = font(28, True)


def chrome():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W, H), 14, fill=PANEL, outline=BORDER)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((18 + i * 26, 16, 32 + i * 26, 30), fill=c)
    d.text((W // 2 - 110, 12), "openjev play maze — zsh", font=FS, fill=DIM)
    return im, d


def box(d, x0, y0, x1, y1, title, color):
    d.rounded_rectangle((x0, y0, x1, y1), 8, outline=BORDER)
    d.rectangle((x0 + 12, y0 - 9, x0 + 20 + len(title) * 9.7, y0 + 9), fill=PANEL)
    d.text((x0 + 16, y0 - 10), title, font=FB, fill=color)


def bar(d, x, y, p, w, color, label_right=True):
    d.rounded_rectangle((x, y, x + w, y + 12), 3, fill=GREY)
    if p > 0:
        d.rounded_rectangle((x, y, x + max(5, int(w * p)), y + 12), 3, fill=color)
    if label_right:
        d.text((x + w + 8, y - 3), f"{p:.2f}", font=FS, fill=FG if p >= 0.5 else DIM)


def sparkline(d, x, y, w, h, values, color, vmin, vmax, hi_idx=None):
    d.rectangle((x, y, x + w, y + h), fill=(17, 21, 27), outline=BORDER)
    if len(values) < 1:
        return
    n = max(len(values), 2)
    pts = []
    for i, v in enumerate(values):
        px = x + 6 + (w - 12) * i / (n - 1 if n > 1 else 1)
        py = y + h - 6 - (h - 12) * (v - vmin) / (vmax - vmin)
        pts.append((px, py))
    if len(pts) > 1:
        d.line(pts, fill=color, width=2)
    for i, p in enumerate(pts):
        r = 4 if i == hi_idx else 2
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=color)


# positions along the path
positions = [tuple(STEPS[0]["pos"])]
for st in STEPS:
    dlt = MOVES[st["move"]]
    positions.append((positions[-1][0] + dlt[0], positions[-1][1] + dlt[1]))
GOAL = next((i, j) for i, r in enumerate(MAZE) for j, ch in enumerate(r) if ch == "G")


def draw_maze(d, x0, y0, cell, k, phase):
    """k = number of completed steps, phase in [0,1] = progress of the move k."""
    for i, row in enumerate(MAZE):
        for j, ch in enumerate(row):
            c = WALL if ch == "#" else FLOOR
            d.rectangle(
                (x0 + j * cell, y0 + i * cell, x0 + (j + 1) * cell - 2, y0 + (i + 1) * cell - 2), fill=c
            )
    for p in positions[: k + 1]:
        i, j = p
        d.rectangle(
            (x0 + j * cell, y0 + i * cell, x0 + (j + 1) * cell - 2, y0 + (i + 1) * cell - 2), fill=PATH
        )
    gi, gj = GOAL
    d.rectangle(
        (x0 + gj * cell, y0 + gi * cell, x0 + (gj + 1) * cell - 2, y0 + (gi + 1) * cell - 2), fill=GREEN
    )
    d.text((x0 + gj * cell + cell // 2 - 7, y0 + gi * cell + cell // 2 - 12), "G", font=FT, fill=BG)
    # agent interpolated
    a = positions[k]
    b = positions[min(k + 1, len(positions) - 1)] if k < len(STEPS) else a
    ai = a[0] + (b[0] - a[0]) * phase
    aj = a[1] + (b[1] - a[1]) * phase
    cx = x0 + aj * cell + cell // 2 - 1
    cy = y0 + ai * cell + cell // 2 - 1
    r = cell // 2 - 6
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=MAGENTA)
    if k >= len(STEPS):
        d.text((cx - 7, cy - 12), "G", font=FT, fill=BG)
    # candidate arrows for the current decision
    if k < len(STEPS) and phase == 0:
        st = STEPS[k]
        for mv, p in st["probs"].items():
            di, dj = MOVES[mv]
            tx = x0 + (a[1] + dj) * cell + cell // 2 - 8
            ty = y0 + (a[0] + di) * cell + cell // 2 - 14
            col = MAGENTA if mv == st["move"] else (DIM if p < 0.3 else YELLOW)
            d.text((tx, ty), ARROW[mv], font=FM, fill=col)


def json_lines(st, reveal):
    body = [
        "{",
        '  "model": "jev-1.13.0",',
        '  "answers": {',
        '    "move": {',
        '      "type": "choice",',
        f'      "choice": "{st["move"]}",',
        '      "probabilities": {',
    ]
    items = list(st["probs"].items())
    for i, (mv, p) in enumerate(items):
        body.append(f'        "{mv}": {p:.2f}' + ("," if i < len(items) - 1 else ""))
    body += [
        "      },",
        f'      "confidence": {st["confidence"]:.2f}',
        "    }",
        "  },",
        f'  "latency_ms": {st["latency_ms"]:.0f}',
        "}",
    ]
    n = int(len(body) * reveal)
    return body[:n], body


def render(k, phase, json_reveal, spinner=None):
    im, d = chrome()
    # header
    d.text((40, 50), "OpenJev", font=FT, fill=CYAN)
    d.text((150, 56), "❯ openjev play maze --backend typesafe --model jev-latest", font=F, fill=DIM)

    # ---------------- left: maze
    LX0, LY0, LX1, LY1 = 40, 100, 560, 700
    box(d, LX0, LY0, LX1, LY1, "state · maze 10×10", CYAN)
    draw_maze(d, LX0 + 40, LY0 + 30, 44, k, phase)
    done = k >= len(STEPS)
    status = f"step {min(k, len(STEPS))}/{len(STEPS)}"
    if done:
        status += "   ✓ GOAL · shortest path"
    d.text((LX0 + 20, LY1 - 60), status, font=FB, fill=GREEN if done else FG)
    d.text(
        (LX0 + 20, LY1 - 36), "● agent  ■ path  ■ goal  ↑↓←→ candidates (bright = chosen)", font=FS, fill=DIM
    )

    # ---------------- right top: decision + bars
    RX0, RX1 = 590, W - 40
    box(d, RX0, 100, RX1, 300, "decision · Choice(up, down, left, right)", MAGENTA)
    if k < len(STEPS):
        st = STEPS[k]
        if spinner is not None:
            d.text((RX0 + 20, 125), spinner + " deciding…", font=F, fill=CYAN)
        else:
            d.text((RX0 + 20, 125), f"→ {st['move']}", font=FT, fill=MAGENTA)
            d.text(
                (RX0 + 150, 130),
                f"confidence {st['confidence']:.2f}   {st['latency_ms']:.0f} ms",
                font=F,
                fill=FG,
            )
        y = 165
        for mv in ["up", "down", "left", "right"]:
            p = st["probs"].get(mv)
            if p is None:
                d.text((RX0 + 20, y - 2), f"{mv:<6}", font=F, fill=GREY)
                d.text((RX0 + 100, y - 2), "wall", font=FS, fill=GREY)
            else:
                chosen = mv == st["move"] and spinner is None
                d.text((RX0 + 20, y - 2), f"{mv:<6}", font=FB if chosen else F, fill=FG if chosen else DIM)
                bar(d, RX0 + 100, y, 0 if spinner else p, 380, MAGENTA if chosen else GREY)
            y += 30
    else:
        total = sum(s["latency_ms"] for s in STEPS) / 1000
        d.text((RX0 + 20, 130), "GOAL reached", font=FT, fill=GREEN)
        d.text(
            (RX0 + 20, 170),
            f"{len(STEPS)} moves · {total:.1f} s wall-clock · 0 tokens generated",
            font=F,
            fill=FG,
        )
        d.text((RX0 + 20, 200), "controller = pos + MOVES[answer.choice]", font=FS, fill=DIM)
        avg_conf = sum(s["confidence"] for s in STEPS) / len(STEPS)
        d.text(
            (RX0 + 20, 240),
            f"mean confidence {avg_conf:.2f} · min {min(s['confidence'] for s in STEPS):.2f} at corners",
            font=FS,
            fill=DIM,
        )

    # ---------------- right middle: JSON stream
    box(d, RX0, 325, RX1, 545, "response · /v1/systemone", YELLOW)
    if k < len(STEPS):
        lines, full = json_lines(STEPS[k], json_reveal)
        y = 340
        for ln in lines:
            col = FG
            if '"choice"' in ln or '"confidence"' in ln:
                col = MAGENTA
            elif "latency" in ln:
                col = CYAN
            d.text((RX0 + 20, y), ln, font=FS, fill=col)
            y += 14
        if len(lines) < len(full):
            d.text((RX0 + 20, y), "▍", font=FS, fill=FG)
    else:
        d.text(
            (RX0 + 20, 345), "session saved → ~/.openjev/sessions/maze-2026-09-20.jsonl", font=FS, fill=DIM
        )
        d.text((RX0 + 20, 365), "14 requests · 14 answers · schema-valid 14/14", font=FS, fill=FG)

    # ---------------- right bottom: sparklines
    box(d, RX0, 570, RX1, 700, "telemetry · rolling", CYAN)
    confs = [s["confidence"] for s in STEPS[: min(k + (0 if spinner else 1), len(STEPS))]]
    lats = [s["latency_ms"] for s in STEPS[: min(k + (0 if spinner else 1), len(STEPS))]]
    d.text((RX0 + 20, 582), "confidence", font=FS, fill=DIM)
    sparkline(d, RX0 + 20, 600, 290, 80, confs, MAGENTA, 0, 1, hi_idx=len(confs) - 1)
    d.text((RX0 + 335, 582), "latency ms", font=FS, fill=DIM)
    sparkline(d, RX0 + 335, 600, 290, 80, lats, CYAN, 200, 900, hi_idx=len(lats) - 1)
    if confs:
        d.text((RX0 + 20, 683), f"now {confs[-1]:.2f}  mean {sum(confs) / len(confs):.2f}", font=FS, fill=FG)
        d.text(
            (RX0 + 335, 683), f"now {lats[-1]:.0f}  p50 {sorted(lats)[len(lats) // 2]:.0f}", font=FS, fill=FG
        )
    return im


def main():
    frames, durs = [], []
    for k in range(len(STEPS)):
        # spinner while "deciding"
        for s in range(3):
            frames.append(render(k, 0.0, 0.0, spinner="⠋⠙⠹⠸⠼⠴"[s]))
            durs.append(70)
        # JSON streams in
        for r in (0.35, 0.7, 1.0):
            frames.append(render(k, 0.0, r))
            durs.append(90)
        durs[-1] = 320
        # agent slides
        for ph in (0.33, 0.66, 1.0):
            frames.append(render(k, ph, 1.0))
            durs.append(60)
    final = render(len(STEPS), 0.0, 1.0)
    frames.append(final)
    durs.append(4000)
    final.save(OUT / "tui-maze-concept.png")
    frames[0].save(
        OUT / "tui-maze-concept.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durs,
        loop=0,
        optimize=True,
    )
    print(
        OUT / "tui-maze-concept.gif",
        f"{(OUT / 'tui-maze-concept.gif').stat().st_size / 1024:.0f} KB",
        len(frames),
        "frames",
    )


if __name__ == "__main__":
    main()
