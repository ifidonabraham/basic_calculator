"""Render a 1080x1350 (4:5) Instagram card.

Usage: python3 make_card.py OUT.jpg "TAG" "Title text" "Hook line" "@handle"
"""
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG, PANEL, ACCENT, TEXT, MUTED = "#0b1220", "#111a2e", "#38bdf8", "#f1f5f9", "#94a3b8"
FONT_DIR = "/usr/share/fonts/opentype/inter/"


def font(name, size):
    return ImageFont.truetype(FONT_DIR + name, size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(out, tag, title, hook, handle):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    pad = 90
    d.rectangle([0, 0, W, 14], fill=ACCENT)

    # tag pill
    f_tag = font("Inter-Bold.otf", 34)
    tw = d.textlength(tag.upper(), font=f_tag)
    d.rounded_rectangle([pad, 130, pad + tw + 60, 130 + 76], radius=38, fill=PANEL, outline=ACCENT, width=3)
    d.text((pad + 30, 130 + 17), tag.upper(), font=f_tag, fill=ACCENT)

    # title: shrink until it fits in 5 lines
    size = 112
    while size > 56:
        f_title = font("Inter-Bold.otf", size)
        lines = wrap(d, title, f_title, W - 2 * pad)
        if len(lines) <= 5:
            break
        size -= 6
    y = 300
    for ln in lines:
        d.text((pad, y), ln, font=f_title, fill=TEXT)
        y += int(size * 1.18)

    # hook
    f_hook = font("Inter-Regular.otf", 46)
    y += 40
    d.rectangle([pad, y, pad + 10, y + 10 + 62 * len(wrap(d, hook, f_hook, W - 2 * pad - 40))], fill=ACCENT)
    for ln in wrap(d, hook, f_hook, W - 2 * pad - 40):
        d.text((pad + 40, y), ln, font=f_hook, fill=MUTED)
        y += 62

    # footer
    f_foot = font("Inter-SemiBold.otf", 36)
    d.text((pad, H - 150), handle, font=f_foot, fill=TEXT)
    d.text((pad, H - 100), "Tech explained simply", font=font("Inter-Regular.otf", 30), fill=MUTED)
    img.save(out, "JPEG", quality=92)


if __name__ == "__main__":
    make_card(*sys.argv[1:6])
