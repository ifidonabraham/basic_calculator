"""Render a 1080x1920 silent text Reel (H.264 + silent AAC) from a JSON spec.

Usage: python3 make_video.py spec.json OUT.mp4

spec = {
  "tag": "Then vs Now", "title": "Firewalls: 2005 vs Today",
  "handle": "@ifidonabraham249",
  "scenes": [{"label": "2005", "text": "...", "sec": 5}, ...],
  "question": "Does your router ...?"
}
"""
import json
import os
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG, PANEL, ACCENT, TEXT, MUTED = "#0b1220", "#111a2e", "#38bdf8", "#f1f5f9", "#94a3b8"
FD = "/usr/share/fonts/opentype/inter/"
PAD = 90
TOP_SAFE, BOTTOM_SAFE = 220, 1620  # keep text clear of Reels UI


def font(name, size):
    return ImageFont.truetype(FD + name, size)


def wrap(d, text, fnt, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, name, start, min_size, max_w, max_h, lead=1.22):
    size = start
    while size >= min_size:
        f = font(name, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) * size * lead <= max_h:
            return f, lines, size
        size -= 4
    f = font(name, min_size)
    return f, wrap(d, text, f, max_w), min_size


def base(tag_text, idx, total, handle):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    f = font("Inter-Bold.otf", 36)
    tw = d.textlength(tag_text.upper(), font=f)
    d.rounded_rectangle([PAD, TOP_SAFE - 20, PAD + tw + 60, TOP_SAFE + 56], radius=38, fill=PANEL, outline=ACCENT, width=3)
    d.text((PAD + 30, TOP_SAFE - 3), tag_text.upper(), font=f, fill=ACCENT)
    # progress dots
    x = PAD
    for i in range(total):
        d.rounded_rectangle([x, BOTTOM_SAFE + 40, x + 60, BOTTOM_SAFE + 50], radius=5, fill=ACCENT if i <= idx else PANEL)
        x += 76
    d.text((PAD, BOTTOM_SAFE + 80), handle, font=font("Inter-SemiBold.otf", 34), fill=MUTED)
    return img, d


def scene_png(path, kind, tag_text, text, idx, total, handle, sub=None):
    img, d = base(tag_text, idx, total, handle)
    box_w, y0 = W - 2 * PAD, TOP_SAFE + 150
    if kind == "hook":
        f, lines, size = fit(d, text, "Inter-Bold.otf", 128, 72, box_w, 760)
        y = 560
        for ln in lines:
            d.text((PAD, y), ln, font=f, fill=TEXT)
            y += int(size * 1.2)
        if sub:
            fs = font("Inter-Regular.otf", 50)
            y += 40
            for ln in wrap(d, sub, fs, box_w):
                d.text((PAD, y), ln, font=fs, fill=MUTED)
                y += 66
    elif kind == "cta":
        f, lines, size = fit(d, text, "Inter-Bold.otf", 88, 56, box_w, 700)
        y = 600
        for ln in lines:
            d.text((PAD, y), ln, font=f, fill=TEXT)
            y += int(size * 1.22)
        fs = font("Inter-SemiBold.otf", 46)
        d.text((PAD, y + 50), "Tell me below", font=fs, fill=ACCENT)
    else:  # content scene
        f, lines, size = fit(d, text, "Inter-SemiBold.otf", 78, 46, box_w, 900)
        total_h = int(len(lines) * size * 1.25)
        y = y0 + 120 + max(0, (900 - total_h) // 3)
        d.rectangle([PAD, y, PAD + 10, y + total_h], fill=ACCENT)
        for ln in lines:
            d.text((PAD + 44, y), ln, font=f, fill=TEXT)
            y += int(size * 1.25)
    img.save(path)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def encode_scene(png, out, dur):
    tmp = out + ".part.mp4"
    fade = 0.35
    vf = (f"format=yuv420p,loop=-1:1,trim=duration={dur},"
          f"fade=t=in:st=0:d={fade},fade=t=out:st={dur - fade}:d={fade}")
    run(["ffmpeg", "-y", "-framerate", "30", "-i", png, "-vf", vf, "-an",
         "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", tmp])
    os.rename(tmp, out)


def build(spec, out_mp4, keep_pngs=None):
    scenes = spec["scenes"]
    items = [("hook", spec["tag"], spec["title"], 3.0, spec.get("sub"))]
    items += [("content", s["label"], s["text"], float(s.get("sec", 5)), None) for s in scenes]
    items += [("cta", "Your turn", spec["question"], 4.0, None)]
    total = len(items)
    work = tempfile.mkdtemp(prefix="reel_")
    files = []
    for i, (kind, tag, text, dur, sub) in enumerate(items):
        png = os.path.join(work, f"s{i}.png")
        scene_png(png, kind, tag, text, i, total, spec["handle"], sub)
        if keep_pngs:
            os.makedirs(keep_pngs, exist_ok=True)
            Image.open(png).save(os.path.join(keep_pngs, f"s{i}.png"))
        mp4 = os.path.join(work, f"s{i}.mp4")
        encode_scene(png, mp4, dur)
        files.append(mp4)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as fh:
        fh.write("".join(f"file '{p}'\n" for p in files))
    silent = os.path.join(work, "all.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    tmp = out_mp4 + ".part.mp4"
    run(["ffmpeg", "-y", "-i", silent, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-shortest", "-movflags", "+faststart", tmp])
    os.rename(tmp, out_mp4)
    return sum(i[3] for i in items)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    secs = build(spec, sys.argv[2], keep_pngs=os.environ.get("KEEP_PNGS"))
    print("ok", sys.argv[2], f"{secs:.0f}s")
