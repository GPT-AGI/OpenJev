"""Xiaohongshu cover (3:4, 1242x1656) from the maze TUI final frame with headline overlay.

    .venv/bin/python scripts/make_cover.py
    -> docs/assets/social/cover-xhs.png  (+ 3 headline variants)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "assets" / "tui-maze-concept.png"
OUT = ROOT / "docs" / "assets" / "social"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1242, 1656
BG = (13, 17, 23)
FG = (240, 244, 248)
DIM = (160, 170, 182)
CYAN = (56, 189, 248)
MAGENTA = (232, 121, 249)
YELLOW = (250, 204, 21)
GREEN = (74, 222, 128)

CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"


def cjk(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(CJK, size, index=2 if bold else 0)


def mono(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO, size, index=1 if bold else 0)


def glow_text(im: Image.Image, xy, text, font, fill, glow, radius=18, stroke=0):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, text, font=font, fill=glow + (255,), stroke_width=stroke + 6, stroke_fill=glow + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    d.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=BG)


def highlight_box(d: ImageDraw.ImageDraw, xy, text, font, box_fill, text_fill, pad=(28, 14), radius=16):
    x, y = xy
    l, t, r, b = d.textbbox((x, y), text, font=font)
    d.rounded_rectangle((l - pad[0], t - pad[1], r + pad[0], b + pad[1]), radius=radius, fill=box_fill)
    d.text((x, y), text, font=font, fill=text_fill)
    return b + pad[1]


def build(headline_lines, kicker, tagline, out_name, accent=YELLOW):
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)

    # subtle grid + vignette
    for gx in range(0, W, 62):
        d.line((gx, 0, gx, H), fill=(20, 25, 33, 255), width=1)
    for gy in range(0, H, 62):
        d.line((0, gy, W, gy), fill=(20, 25, 33, 255), width=1)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200, -300, W + 200, 700), fill=(56, 189, 248, 38))
    gd.ellipse((200, H - 500, W + 300, H + 300), fill=(232, 121, 249, 34))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)

    # kicker
    y = 96
    y = highlight_box(d, (72, y), kicker, cjk(40), (255, 255, 255, 235), BG, pad=(22, 10), radius=12)

    # headline
    y += 34
    for i, line in enumerate(headline_lines):
        size = 118 if i == 0 else 118
        f = cjk(size)
        color = accent if i == len(headline_lines) - 1 else FG
        glow_text(im, (66, y), line, f, color, accent if color == accent else (56, 189, 248), radius=22, stroke=3)
        y += size + 22
    d = ImageDraw.Draw(im)

    # tagline
    y += 10
    ft = cjk(40, bold=False)
    line, lines = "", []
    for ch in tagline:
        if d.textlength(line + ch, font=ft) > W - 144:
            lines.append(line); line = ch
        else:
            line += ch
    lines.append(line)
    for ln in lines:
        d.text((72, y), ln, font=ft, fill=DIM)
        y += 54
    y += 20

    # screenshot card
    shot = Image.open(SRC).convert("RGBA")
    card_w = W - 96 - 150
    scale = card_w / shot.width
    shot = shot.resize((card_w, int(shot.height * scale)), Image.LANCZOS)
    card_y = y + 10
    # shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(((W - card_w) // 2 + 10, card_y + 24, (W + card_w) // 2 + 10, card_y + shot.height + 24), 26, fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    im.alpha_composite(sh)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.width, shot.height), 24, fill=255)
    im.paste(shot, ((W - shot.width) // 2, card_y), mask)
    d = ImageDraw.Draw(im)
    cx0 = (W - shot.width) // 2
    d.rounded_rectangle((cx0, card_y, cx0 + shot.width, card_y + shot.height), 24, outline=(70, 80, 95, 255), width=2)
    y = card_y + shot.height + 44

    # stat chips
    chips = [
        ("14", "步", "最短路径", GREEN),
        ("0", "", "生成 token", MAGENTA),
        ("0.3", "s", "回答27个问题", CYAN),
        ("<1", "分钱", "130次API调用", YELLOW),
    ]
    cw = (W - 96 - 3 * 18) // 4
    for i, (big, unit, small, col) in enumerate(chips):
        x = 48 + i * (cw + 18)
        d.rounded_rectangle((x, y, x + cw, y + 150), 20, fill=(22, 27, 34, 255), outline=col + (200,), width=2)
        fb, fu = mono(54), cjk(30)
        bw = d.textlength(big, font=fb) + (d.textlength(unit, font=fu) + 4 if unit else 0)
        bx = x + (cw - bw) / 2
        d.text((bx, y + 22), big, font=fb, fill=col)
        if unit:
            d.text((bx + d.textlength(big, font=fb) + 4, y + 44), unit, font=fu, fill=col)
        fs = cjk(26, bold=False)
        sw = d.textlength(small, font=fs)
        d.text((x + (cw - sw) / 2, y + 100), small, font=fs, fill=DIM)
    y += 150 + 40

    # footer
    fy = max(y, H - 120)
    d.text((72, fy), "GitHub · GPT-AGI/OpenJev", font=mono(34), fill=FG)
    d.text((72, fy + 46), "全部实验脚本开源，一条命令可复现", font=cjk(26, bold=False), fill=DIM)
    tag = "全网首测"
    ft = cjk(30)
    tw = d.textlength(tag, font=ft)
    d.rounded_rectangle((W - 72 - tw - 44, fy - 4, W - 72, fy + 52), 14, fill=accent)
    d.text((W - 72 - tw - 22, fy + 4), tag, font=ft, fill=BG)

    path = OUT / out_name
    im.convert("RGB").save(path, quality=95)
    print(path)


if __name__ == "__main__":
    build(
        ["评测一个", "不会说话的大模型", "我让它走迷宫"],
        "前OpenAI大佬创业 · 爆火新模型 Jev",
        "不生成一个字，只回答选项和概率。14步最短路径走出，它「犹豫」的地方和人一样。",
        "cover-xhs.png",
    )
    build(
        ["不生成文字的AI", "比GPT快40倍？", "我实测了4个花活"],
        "Jev 首发评测 · 鹈鹕 / 3D地形 / 延迟 / 迷宫",
        "27个问题只要0.3秒，加问题不加时间。130次调用花了不到1分钱。",
        "cover-xhs-v2.png",
        accent=CYAN,
    )
    build(
        ["这个AI", "一个字都不说", "却把迷宫走成了最短路"],
        "TypeSafe Jev · System One 模型实测",
        "每步只问一句「上下左右选哪个」。置信度在拐角掉到0.62，走廊里0.99。",
        "cover-xhs-v3.png",
        accent=MAGENTA,
    )
