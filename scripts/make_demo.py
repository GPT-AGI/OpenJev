"""Render OpenJev demo GIFs / PNGs with Pillow (no external tools).

Usage:
    python scripts/make_demo.py            # writes to docs/assets/

Produces:
    docs/assets/demo-repl.gif        Claude Code style REPL: type -> decide -> probability bars
    docs/assets/demo-race.gif        27 questions: OpenJev (one pass) vs autoregressive LLM JSON
    docs/assets/hero.png             static hero frame for README / social preview
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1200, 720
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

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size, index=1 if bold else 0)
    except OSError:
        return ImageFont.load_default()


F = font(18)
FB = font(18, bold=True)
FS = font(15)
FT = font(26, bold=True)


def frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # mac window chrome
    d.rounded_rectangle((0, 0, W, H), radius=14, fill=PANEL, outline=BORDER)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((18 + i * 26, 16, 32 + i * 26, 30), fill=c)
    d.text((W // 2 - 60, 12), "openjev — zsh", font=FS, fill=DIM)
    return im, d


def text(d, xy, s, f=F, fill=FG):
    d.text(xy, s, font=f, fill=fill)


def bar(d, x, y, p, w=260, h=14, color=CYAN):
    d.rounded_rectangle((x, y, x + w, y + h), radius=4, fill=GREY)
    if p > 0:
        d.rounded_rectangle((x, y, x + max(6, int(w * p)), y + h), radius=4, fill=color)
    text(d, (x + w + 12, y - 3), f"{p * 100:5.1f}%", FS, FG if p >= 0.5 else DIM)


def save_gif(frames, path, durations):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)


# ----------------------------------------------------------------------------- demo 1: REPL
def demo_repl():
    frames, durs = [], []
    lines_typed = [
        (
            '❯ /state "Customer: our Stripe integration has been failing for 3 days, payments are down. Fix it today."',
            DIM,
        ),
        ('❯ /choice dept "Which department should handle this?" billing,technical,sales', DIM),
        ('❯ /score frustration "How frustrated is the customer?" 0:calm,1:annoyed,2:furious', DIM),
        ('❯ /noul urgent "Does this need immediate escalation?"', DIM),
        ("❯ /ask", FG),
    ]

    def base(d, n_lines, typing=None):
        text(d, (40, 56), "OpenJev", FT, CYAN)
        text(d, (190, 64), "v0.1.0 · backend openjev-hf/Qwen2.5-0.5B-Instruct · /help for commands", FS, DIM)
        y = 110
        for i in range(n_lines):
            s, c = lines_typed[i]
            text(d, (40, y), s, F, c)
            y += 30
        if typing is not None:
            text(d, (40, y), typing + "▍", F, FG)
            y += 30
        return y

    # typing animation
    for i, (s, _) in enumerate(lines_typed):
        step = max(4, len(s) // 14)
        for k in range(0, len(s) + 1, step):
            im, d = frame()
            base(d, i, s[:k])
            frames.append(im)
            durs.append(35)
        im, d = frame()
        base(d, i + 1)
        frames.append(im)
        durs.append(250)

    # spinner
    for k in range(6):
        im, d = frame()
        y = base(d, len(lines_typed))
        text(d, (40, y), "⠋⠙⠹⠸⠼⠴"[k] + " deciding… one forward pass per question", F, CYAN)
        frames.append(im)
        durs.append(80)

    # results appear one panel at a time
    panels = [
        (
            "choice",
            "dept",
            MAGENTA,
            [("▸ technical", 0.91), ("  billing", 0.07), ("  sales", 0.02)],
            "→ technical   confidence 0.84",
        ),
        (
            "score",
            "frustration",
            YELLOW,
            [("0 · calm", 0.08), ("1 · annoyed", 0.61), ("2 · furious", 0.31)],
            "→ score 1.23   confidence 0.42",
        ),
        ("noul", "urgent", GREEN, [("true", 0.96), ("false", 0.04)], "→ TRUE   P(true) 0.96"),
    ]

    def draw_panels(d, y, upto, reveal=1.0):
        for idx in range(upto):
            kind, qid, color, rows, footer = panels[idx]
            ph = 40 + 26 * len(rows) + 30
            d.rounded_rectangle((36, y, W - 36, y + ph), radius=8, outline=BORDER)
            text(d, (52, y - 2), f" {kind} {qid} ", FB, color)
            ry = y + 30
            for label, p in rows:
                pp = p * (reveal if idx == upto - 1 else 1.0)
                text(d, (56, ry - 2), label, F, FG if label.startswith("▸") or p >= 0.5 else DIM)
                bar(d, 300, ry + 2, pp, color=color if (label.startswith("▸") or kind != "choice") else GREY)
                ry += 26
            text(d, (56, ry + 2), footer if (idx < upto - 1 or reveal >= 1.0) else "", FS, FG)
            y += ph + 10
        return y

    for idx in range(1, len(panels) + 1):
        for r in [0.25, 0.5, 0.75, 1.0]:
            im, d = frame()
            y = base(d, len(lines_typed))
            draw_panels(d, y + 8, idx, r)
            frames.append(im)
            durs.append(45)
        durs[-1] = 200

    im, d = frame()
    y = base(d, len(lines_typed))
    y = draw_panels(d, y + 8, len(panels))
    text(d, (40, y + 4), "3 decisions  ·  ", FB, FG)
    text(d, (196, y + 4), "38.2 ms", FB, CYAN)
    text(d, (290, y + 4), "  ·  312 in / 8 out tokens  ·  typed, calibrated, no JSON parsing", FS, DIM)
    frames.append(im)
    durs.append(3500)
    im.save(OUT / "hero.png")
    save_gif(frames, OUT / "demo-repl.gif", durs)


# ----------------------------------------------------------------------------- demo 2: race
QUESTIONS = [
    "Revenue currently impacted?",
    "What business impact?",
    "Integration issue present?",
    "Account health status?",
    "Which incident scope?",
    "Security concern present?",
    "Duplicate charge reported?",
    "Churn likelihood level?",
    "Sentiment certainty level?",
    "Human attention needed?",
    "Security risk level?",
    "Immediate feature request?",
    "Partner launch mentioned?",
    "Credible churn risk?",
    "Production capability down?",
    "Customer data access?",
    "Server error reported?",
    "Financial impact level?",
    "Which response deadline?",
    "Reported production failure?",
    "Which primary department?",
    "Which requested resolution?",
    "Language personally threatening?",
    "Concrete deadline stated?",
    "Which issue category?",
    "Technical specificity level?",
    "Resolution complexity level?",
]
ANS_LEFT = [
    '{"noul": 0.85}',
    '{"choice": "degraded", "confidence": 0.96}',
    '{"noul": 0.90}',
    '{"choice": "watch", "confidence": 0.31}',
    '{"choice": "single_account", "confidence": 0.75}',
    '{"noul": 0.08}',
    '{"noul": 0.04}',
    '{"score": 1.60, "confidence": 0.60}',
    '{"score": 2.77, "confidence": 0.77}',
    '{"noul": 0.95}',
    '{"score": 0.27, "confidence": 0.84}',
    '{"noul": 0.03}',
    '{"noul": 0.02}',
    '{"noul": 0.72}',
    '{"noul": 0.93}',
    '{"noul": 0.01}',
    '{"noul": 0.88}',
    '{"score": 1.86, "confidence": 0.85}',
    '{"choice": "today", "confidence": 0.98}',
    '{"noul": 0.85}',
    '{"choice": "technical", "confidence": 1.00}',
    '{"choice": "restore_service", "confidence": 0.97}',
    '{"noul": 0.03}',
    '{"noul": 0.90}',
    '{"choice": "integration_failure", "confidence": 0.90}',
    '{"score": 2.99, "confidence": 0.98}',
    '{"score": 1.99, "confidence": 0.98}',
]
ANS_RIGHT = [
    "true",
    "degraded",
    "true",
    "watch",
    "single account",
    "false",
    "false",
    "medium",
    "high",
    "true",
    "low",
    "false",
    "false",
    "true",
    "true",
    "false",
    "true",
    "medium",
    "today",
    "true",
    "technical",
    "restore service",
    "false",
    "true",
    "integration failure",
    "high",
    "medium",
]


def demo_race():
    random.seed(7)
    frames, durs = [], []
    col_w = (W - 80) // 2
    lx, rx = 40, 40 + col_w + 20
    total_frames = 110  # ~ 5.5 s at 50ms
    # left finishes at frame 6 (~0.3 s), right trickles in with first-token wait
    right_start = 22
    right_order = list(range(len(QUESTIONS)))

    for f in range(total_frames):
        im, d = frame()
        text(d, (40, 52), "Same 27 questions. Same state. Started together.", FT, FG)
        text(d, (40, 90), "27 QUESTIONS · ONE REQUEST · STARTED TOGETHER", FS, DIM)

        for x, title, col in [
            (lx, "openjev  (one forward pass, parallel)", CYAN),
            (rx, "autoregressive LLM  (JSON, token by token)", MAGENTA),
        ]:
            d.rounded_rectangle((x - 8, 120, x + col_w - 12, H - 60), radius=8, outline=BORDER)
            text(d, (x, 126), title, FB, col)

        n_left = min(len(QUESTIONS), 0 if f < 2 else int((f - 1) * 6))
        y = 158
        for i in range(len(QUESTIONS)):
            if i < n_left:
                text(d, (lx, y), f"{QUESTIONS[i]:<32}", FS, DIM)
                text(d, (lx + 300, y), ANS_LEFT[i][:34], FS, FG)
            y += 18
        if n_left >= len(QUESTIONS):
            text(d, (lx, H - 100), "✓ completed in 0.114 s   ·   cost $0.00006", FB, GREEN)

        if f < right_start:
            text(d, (rx, 158), "⠋⠙⠹⠸⠼⠴⠦⠧"[f % 8] + " waiting for first token…", FS, DIM)
        n_right = 0 if f < right_start else min(len(QUESTIONS), (f - right_start) // 3)
        y = 158
        for i in range(len(QUESTIONS)):
            if i < n_right:
                text(d, (rx, y), f"{QUESTIONS[right_order[i]]:<32}", FS, DIM)
                partial = ANS_RIGHT[right_order[i]]
                if i == n_right - 1 and (f - right_start) % 3 != 2:
                    partial = partial[: max(1, len(partial) * ((f - right_start) % 3 + 1) // 3)] + "▍"
                text(d, (rx + 300, y), partial, FS, FG)
            y += 18
        if n_right >= len(QUESTIONS):
            text(d, (rx, H - 100), "✓ completed in 4.9 s   ·   cost $0.0180", FB, YELLOW)

        frames.append(im)
        durs.append(50)
    durs[-1] = 3000
    save_gif(frames, OUT / "demo-race.gif", durs)


# ----------------------------------------------------------------------------- architecture png
def arch():
    im = Image.new("RGB", (W, 520), BG)
    d = ImageDraw.Draw(im)
    text(d, (40, 30), "OpenJev architecture", FT, FG)

    def box(x, y, w, h, title, sub, color):
        d.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=PANEL, outline=color, width=2)
        text(d, (x + 14, y + 12), title, FB, color)
        for i, s in enumerate(sub):
            text(d, (x + 14, y + 40 + i * 20), s, FS, DIM)

    box(
        40,
        90,
        250,
        120,
        "REPL / CLI",
        ["Claude Code style", "probability bars", "/ask /compare /serve"],
        CYAN,
    )
    box(40, 240, 250, 120, "typesafe-sdk", ["official SDKs", "only base_url changes", "Python + JS"], CYAN)
    box(40, 390, 250, 100, "Web Playground", ["side-by-side", "latency + calibration"], CYAN)

    box(
        360,
        200,
        260,
        140,
        "POST /v1/systemone",
        ["state + questions", "answers + usage", "Jev-compatible schema"],
        FG,
    )
    box(
        680,
        200,
        220,
        140,
        "Decision Core",
        ["Choice · Score · Noul", "one forward pass", "softmax over labels"],
        MAGENTA,
    )

    for i, (t, s) in enumerate(
        [
            ("HF Transformers", "CPU / CUDA / MPS"),
            ("MLX", "Apple Silicon"),
            ("vLLM", "prompt_logprobs"),
            ("TypeSafe / OpenRouter", "reference mode"),
        ]
    ):
        box(930, 60 + i * 110, 250, 90, t, [s], YELLOW)

    def arrow(x1, y1, x2, y2, c=DIM):
        d.line((x1, y1, x2, y2), fill=c, width=3)
        ang = math.atan2(y2 - y1, x2 - x1)
        for s in (-0.5, 0.5):
            d.line((x2, y2, x2 - 14 * math.cos(ang + s), y2 - 14 * math.sin(ang + s)), fill=c, width=3)

    arrow(290, 150, 360, 250)
    arrow(290, 300, 360, 280)
    arrow(290, 440, 360, 310)
    arrow(620, 270, 680, 270)
    for i in range(4):
        arrow(900, 270, 930, 105 + i * 110)
    im.save(OUT / "architecture.png")


if __name__ == "__main__":
    demo_repl()
    demo_race()
    arch()
    for p in sorted(OUT.iterdir()):
        print(p.relative_to(ROOT), f"{p.stat().st_size / 1024:.0f} KB")
