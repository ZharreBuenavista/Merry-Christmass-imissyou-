import tkinter as tk
import tkinter.font as tkfont
import math
import time
import random
import ctypes
import re
import gc
import itertools
import os
import sys
import traceback
from functools import lru_cache, partial

# ---------------------------------------------------------------------------
# PASTE YOUR LYRICS HERE.
# Normal LRC lines work:            [03:12.48]So what if I call
# Optional word-level timing too:   [03:12.48]<03:12.48>So <03:12.90>what <03:13.10>if
# Start a line with + to STACK it under the previous line instead of replacing it;
# both then stay on screen and fade out together (the video's ending):
#                                   [03:58.00]+I miss you
# The lines below are already timed to the video (per word); replace them with your own if needed.
# ---------------------------------------------------------------------------
lrc = """
[00:02.55]<00:02.55>I <00:03.20>miss <00:04.55>you
[00:06.55]<00:06.55>You <00:07.25>know <00:07.85>it's <00:09.20>true
[00:10.90]<00:10.90>That <00:11.50>I <00:12.20>miss <00:12.85>you
[00:15.55]<00:15.55>You <00:16.25>know <00:16.90>it's <00:19.20>true
[00:20.25]<00:20.25>So <00:20.30>what <00:20.55>if <00:20.85>I <00:21.85>call?
[00:24.55]<00:24.55>And <00:24.60>you <00:24.90>pick <00:25.25>up <00:25.60>the <00:26.55>phone?
[00:29.25]<00:29.25>And <00:29.55>I <00:29.90>use <00:30.25>this <00:31.20>holiday
[00:32.60]<00:32.60>To <00:32.90>make <00:33.55>my <00:34.20>way <00:34.55>to <00:34.90>your <00:35.55>ghost
[00:38.55]<00:38.55>Or <00:38.60>what <00:38.90>if <00:39.20>you're <00:40.55>lonely
[00:42.85]<00:42.85>And <00:42.90>you <00:43.55>know <00:43.90>I <00:44.20>am <00:44.85>too?
[00:47.55]<00:47.55>And <00:47.90>I <00:48.25>get <00:48.50>the <00:49.20>chance <00:49.60>to <00:50.20>say
[00:50.90]<00:50.90>Merry <00:51.55>Christmas,
[00:52.90]+<00:52.90>I <00:53.20>miss <00:53.90>you
[00:57.60]<00:57.60>I <00:58.40>miss <00:59.00>you
"""

# Or keep your lyrics in a separate .lrc/.txt file and put its path here (overrides lrc above):
lrc_file = ""           # e.g. r"C:\\Users\\you\\Downloads\\lyrics.lrc"

lead_in = 2.0            # start the script this many seconds BEFORE the first word is sung (0 = exactly at it)
start_at = 0.0          # seconds into the song where the overlay begins
end_at = 9999.0         # seconds into the song where it ends
last_line_duration = 1.6   # how long the final line holds before fading
final_fade = 1.2            # the last line, snow and lights all fade out together over this

transparent_color = "#010101"
tint_color = "#081226"
tint_alpha = 0.62
use_blur = False
dpi_aware = True            # real screen pixels -> sharp text, correct centering on scaled displays

font_small = "Georgia"          # small italic serif lines
font_big = "Arial Black"        # banner + big words
font_script = "Segoe Script"    # "Merry"
font_symbol = "Segoe UI Symbol" # snowflake glyph

base_div = 17                   # small text size = screen height / base_div (pixels); smaller number = bigger text
center_x = 0.5                  # where lines are centred: fraction of screen width
center_y = 0.5                  # ... and of screen height
debug_center = False            # True draws a red cross at the screen centre (to check alignment)
auto_effects = True             # lines with no keyword still get one banner/big word + ghost, like the video
text_color = "#F6E7B8"
shadow_color = "#120d0a"
ghost_color = "#1a4f93"         # giant blue word behind the lyrics

color_steps = 128
line_fade_out = 0.5
max_word_gap = 0.6

# Words that get special treatment. Add your own!
#   kind:   banner (coloured card) | big (large plain) | script | medium
#   icon:   "phone" splits the word after `split` letters and pops in a red phone
#   ghost:  giant blue copy of the word drifting behind the lyrics
#   banner: (card colour, text colour); omitted -> cycles through banner_palette
keywords = {
    "you":       dict(kind="banner", ghost=True),
    "miss":      dict(kind="big", color="#E8B8C4", ghost=True),
    "call":      dict(kind="banner", banner=("#EFE6D0", "#C95A52"), ghost=True),
    "true":      dict(kind="big", color="#FF8066"),
    "holiday":   dict(kind="big", color="#FFD23F", ghost=True),
    "ghost":     dict(kind="big", color="#F3F0E6", ghost=True, scatter=True),
    "chance":    dict(kind="banner", banner=("#EFE6D0", "#C95A52"), ghost=True),
    "christmas": dict(kind="banner", banner=("#3EA84B", "#F4EFE3"), ghost=True),
    "merry":     dict(kind="script", color="#FF8066"),
    "phone":     dict(kind="big", color="#F3E9C8", scale=1.9, icon="phone", split=2),
    "lonely":    dict(kind="big", color="#BFD9FF", ghost=True),
}

banner_palette = [("#EFE6D0", "#C9382B"), ("#E8402A", "#F4EFE3"), ("#3EA84B", "#F4EFE3"),
                  ("#E8402A", "#F4EFE3")]
banner_cycle = itertools.cycle(banner_palette)

KIND_SCALE = dict(small=1.0, medium=1.5, big=3.3, banner=3.7, script=1.9)

# small offsets from the centre (x, y) so lines don't all land on exactly the same spot
zones = [
    (0.0, 0.0), (0.0, -0.035), (0.0, 0.035),
    (0.0, -0.015), (0.0, 0.015),
]

auto_styles = itertools.cycle([
    dict(kind="banner", ghost=True),
    dict(kind="big", color="#FFD23F", ghost=True),
    dict(kind="big", color="#E8B8C4", ghost=True),
    dict(kind="banner", ghost=True),
])
stopwords = set("""a an the and or but if so to of in on at for with as is it its i me my we us our you your he she
they them his her this that these those am are was were be been do did does have has had not no yes just oh
what when where who how all up out""".split())

invisible = re.compile("[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
stamp = re.compile(r"^\s*\[(\d+):(\d+(?:\.\d+)?)\](.*)$")
word_tag = re.compile(r"<(\d+):(\d+(?:\.\d+)?)>")


class Gfx:
    def bind(self, canvas):
        call = canvas.tk.call
        cw = canvas._w
        self.coords = partial(call, cw, "coords")
        self.cfg = partial(call, cw, "itemconfigure")
        self.move = partial(call, cw, "move")
        self.delete = partial(call, cw, "delete")
        self.lower = partial(call, cw, "lower")


gfx = Gfx()


def parse_words(text, line_ts):
    """Return (plain text, absolute per-word times or None)."""
    if "<" not in text:
        return text, None
    pieces = word_tag.split(text)
    words, times = [], []
    for wd in pieces[0].split():
        words.append(wd)
        times.append(line_ts)
    for k in range(1, len(pieces) - 2, 3):
        ts = int(pieces[k]) * 60 + float(pieces[k + 1])
        for wd in pieces[k + 2].split():
            words.append(wd)
            times.append(ts)
    if not words:
        return text, None
    return " ".join(words), times


def load_lyrics():
    entries = []
    source = lrc
    if lrc_file:
        with open(lrc_file, encoding="utf-8-sig") as fh:
            source = fh.read()
    for raw in invisible.sub("", source).splitlines():
        m = stamp.match(raw)
        if m:
            ts = int(m.group(1)) * 60 + float(m.group(2))
            text, wt = parse_words(m.group(3).strip(), ts)
            join = text.startswith("+")
            text = text.lstrip("+").strip()
            if wt and join:
                text, wt = parse_words(m.group(3).strip().lstrip("+").strip(), ts)
            entries.append((ts, text, wt, join))
    entries.sort(key=lambda e: e[0])
    lines = []
    for i, (ts, text, wt, join) in enumerate(entries):
        if not text or ts < start_at - 0.01 or ts >= end_at - 0.01:
            continue
        nxt = entries[i + 1][0] if i + 1 < len(entries) else ts + last_line_duration
        offs = [max(0.0, x - ts) for x in wt] if wt else None
        lines.append([ts - start_at, text, max(1.0, nxt - ts), offs, join])
    if not lines:
        raise SystemExit("No lyric lines found. Paste your timestamped lyrics into lrc.")
    # a stacked (+) line keeps the line(s) above it on screen until it ends
    for k in range(len(lines) - 1, 0, -1):
        if lines[k][4]:
            end_k = lines[k][0] + lines[k][2]
            lines[k - 1][2] = max(lines[k - 1][2], end_k - lines[k - 1][0])
    base = lines[0][0]
    return [(s - base, t, d, o, j) for s, t, d, o, j in lines]


def norm(word):
    return re.sub(r"\W+", "", word.lower())


def style_for(parts, i):
    key = norm(parts[i])
    if key == "you" and i > 0 and norm(parts[i - 1]) == "miss":
        return dict(kind="medium", color="#C3CAD6")
    return keywords.get(key)


def auto_pick(parts):
    """For a line with no keyword, pick the longest meaningful word to highlight."""
    if not auto_effects or len(parts) < 2:
        return None, None
    if any(style_for(parts, i) for i in range(len(parts))):
        return None, None
    cands = [i for i, wd in enumerate(parts)
             if len(norm(wd)) >= 3 and norm(wd) not in stopwords]
    if not cands:
        return None, None
    i = max(cands, key=lambda k: (len(norm(parts[k])), k))
    return i, dict(next(auto_styles))


@lru_cache(maxsize=None)
def hex_to_rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


@lru_cache(maxsize=32768)
def _mix(c1, c2, q):
    t = q / color_steps
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def mix(c1, c2, t):
    if t <= 0.0:
        return c1
    if t >= 1.0:
        return c2
    return _mix(c1, c2, int(t * color_steps + 0.5))


def clamp01(v):
    return max(0.0, min(1.0, v))


def ease_out_cubic(p):
    return 1 - (1 - p) ** 3


def ease_in_cubic(p):
    return p ** 3


def ease_in_out(p):
    return p * p * (3 - 2 * p)


def ease_out_back(p):
    c1 = 1.70158
    q = p - 1
    return 1 + (c1 + 1) * q ** 3 + c1 * q ** 2


def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def fine_timer(on):
    try:
        winmm = ctypes.windll.winmm
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)
    except Exception:
        pass


def _hwnd(win):
    win.update_idletasks()
    return ctypes.windll.user32.GetParent(win.winfo_id())


def make_click_through(win):
    try:
        user32 = ctypes.windll.user32
        hwnd = _hwnd(win)
        style = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)
    except Exception:
        pass


def enable_blur(win, tint_hex, opacity=0.6):
    try:
        class Accent(ctypes.Structure):
            _fields_ = [("state", ctypes.c_int), ("flags", ctypes.c_int),
                        ("color", ctypes.c_uint), ("anim", ctypes.c_int)]

        class Data(ctypes.Structure):
            _fields_ = [("attr", ctypes.c_int), ("data", ctypes.c_void_p),
                        ("size", ctypes.c_size_t)]

        r, g, b = hex_to_rgb(tint_hex)
        argb = (int(opacity * 255) << 24) | (b << 16) | (g << 8) | r
        accent = Accent(4, 2, argb, 0)
        data = Data(19, ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p),
                    ctypes.sizeof(accent))
        ctypes.windll.user32.SetWindowCompositionAttribute(_hwnd(win), ctypes.byref(data))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background decoration: christmas lights, snow, sparkles
# ---------------------------------------------------------------------------
class Lights:
    palette = ["#FF3B3B", "#FF9F1C", "#3DDC5A", "#3FA7FF", "#FF5CA8", "#FFD93D"]

    def __init__(self, canvas, sw, sh):
        self.bulbs = []
        self.wires = []
        self.wire_col = None
        swags = max(3, sw // 640)
        per = 8
        seg = sw / swags
        y0 = 16
        sag = sh * 0.045
        bk = sh / 1080
        ci = random.randint(0, len(self.palette) - 1)
        for s in range(swags):
            pts = []
            for j in range(25):
                u = j / 24
                pts += [s * seg + u * seg, y0 + sag * math.sin(math.pi * u)]
            self.wires.append(canvas.create_line(*pts, fill=transparent_color, width=2,
                                                 smooth=True, tags=("lights",)))
        for s in range(swags):
            for j in range(1, per):
                u = j / per
                x = s * seg + u * seg
                y = y0 + sag * math.sin(math.pi * u)
                color = self.palette[ci % len(self.palette)]
                ci += 1
                glow = canvas.create_oval(x - 30 * bk, y - 14 * bk, x + 30 * bk, y + 50 * bk, fill=transparent_color,
                                          outline="", tags=("lights",))
                bulb = canvas.create_oval(x - 15 * bk, y - 2 * bk, x + 15 * bk, y + 34 * bk, fill=transparent_color,
                                          outline="", tags=("lights",))
                self.bulbs.append(dict(glow=glow, bulb=bulb, color=color, sig=None,
                                       ph=random.uniform(0, math.tau),
                                       sp=random.uniform(1.2, 3.2)))

    def update(self, t, env):
        wc = mix(transparent_color, "#10131c", env)
        if wc != self.wire_col:
            self.wire_col = wc
            for w in self.wires:
                gfx.cfg(w, "-fill", wc)
        for b in self.bulbs:
            lvl = env * (0.72 + 0.28 * math.sin(t * b["sp"] + b["ph"]))
            bc = mix("#1a1d26", b["color"], lvl)
            gc_ = mix(transparent_color, b["color"], lvl * 0.3)
            sig = (bc, gc_)
            if sig != b["sig"]:
                b["sig"] = sig
                gfx.cfg(b["glow"], "-fill", gc_)
                gfx.cfg(b["bulb"], "-fill", bc)


class Flake:
    __slots__ = ("sw", "sh", "x", "y", "r", "vy", "ph", "amp", "depth", "item",
                 "col", "gone", "glyph")

    def __init__(self, canvas, sw, sh, glyph):
        self.sw, self.sh, self.glyph = sw, sh, glyph
        self.depth = random.random()
        d = self.depth
        self.r = 2.0 + 4.5 * d
        self.vy = 28 + 85 * d + random.uniform(0, 20)
        self.amp = random.uniform(8, 26)
        self.ph = random.uniform(0, math.tau)
        self.x = random.uniform(0, sw)
        self.y = random.uniform(-sh * 0.1, sh)
        self.gone = False
        self.col = None
        if glyph:
            size = int(18 + 22 * d)
            self.item = canvas.create_text(0, -50, text="\u2744", fill=transparent_color,
                                           font=(font_symbol, -size), tags=("snow",))
        else:
            self.item = canvas.create_oval(0, -50, 1, -49, fill=transparent_color,
                                           outline="", tags=("snow",))

    def update(self, dt, t, ending, env):
        self.y += self.vy * dt
        self.x += (14 + math.sin(t * 0.9 + self.ph) * self.amp) * dt
        if self.y > self.sh + 24 or self.x > self.sw + 30:
            if ending:
                self.gone = True
                gfx.delete(self.item)
                return
            self.y = -random.uniform(6, 80)
            self.x = random.uniform(-self.sw * 0.05, self.sw)
        x, y, r = self.x, self.y, self.r
        if self.glyph:
            gfx.coords(self.item, x, y)
        else:
            gfx.coords(self.item, x - r, y - r, x + r, y + r)
        col = mix(transparent_color, "#EAF3FF" if self.glyph else "#FFFFFF",
                  env * (0.55 + 0.45 * self.depth))
        if col != self.col:
            self.col = col
            gfx.cfg(self.item, "-fill", col)


def build_snow(canvas, sw, sh):
    k = max(0.6, min(1.5, sw / 1920))
    flakes = [Flake(canvas, sw, sh, False) for _ in range(int(130 * k))]
    flakes += [Flake(canvas, sw, sh, True) for _ in range(max(6, int(11 * k)))]
    return flakes


class Sparkle:
    def __init__(self, canvas, x, y, t, size=None):
        self.x, self.y, self.t0 = x, y, t
        self.life = random.uniform(0.9, 1.7)
        self.R = size or random.uniform(7, 15)
        self.col = None
        self.item = canvas.create_polygon(*([0] * 16), fill=transparent_color,
                                          outline="", tags=("spark",))

    def update(self, t):
        age = t - self.t0
        if age > self.life:
            gfx.delete(self.item)
            return False
        a = math.sin(math.pi * age / self.life)
        R = self.R * (0.4 + 0.6 * a)
        r = R * 0.22
        pts = []
        for k in range(8):
            ang = k * math.pi / 4 - math.pi / 2
            rad = R if k % 2 == 0 else r
            pts += [self.x + math.cos(ang) * rad, self.y + math.sin(ang) * rad]
        gfx.coords(self.item, *pts)
        col = mix(transparent_color, "#FFD98A", a)
        if col != self.col:
            self.col = col
            gfx.cfg(self.item, "-fill", col)
        return True


# ---------------------------------------------------------------------------
# Lyrics
# ---------------------------------------------------------------------------
class Word:
    pass


def make_rows(infos):
    rows, run = [], []

    def flush():
        if run:
            r = math.ceil(len(run) / 2)
            b, ex = divmod(len(run), r)
            idx = 0
            for k in range(r):
                s = b + (1 if k >= r - ex else 0)
                rows.append(run[idx:idx + s])
                idx += s
            run.clear()

    for i, inf in enumerate(infos):
        if inf["kind"] == "small":
            run.append(i)
        else:
            flush()
            rows.append([i])
    flush()
    return rows


class LyricLine:
    def __init__(self, canvas, text, start, slot, wtimes, sw, sh, zone, font_for,
                 anchor=None, final=False):
        self.words = []
        self.items = []
        parts = text.split() or [" "]
        n = len(parts)
        base = max(22, int(sh / base_div))
        space = font_for(font_small, base, False, True)[0].measure(" ")
        gap_words = space * 1.1

        auto_i, auto_st = (None, None) if anchor else auto_pick(parts)

        def layout(m):
            infos = []
            for i, wd in enumerate(parts):
                st = auto_st if i == auto_i else style_for(parts, i)
                kind = st["kind"] if st else "small"
                scale = (st.get("scale") if st else None) or KIND_SCALE[kind]
                if kind == "small":
                    scale *= random.uniform(0.95, 1.08)
                size = max(14, int(base * scale * m))
                shown = wd if kind in ("small", "script") else wd.upper()
                if kind == "small":
                    f, spec = font_for(font_small, size, False, True)
                elif kind == "script":
                    f, spec = font_for(font_script, size, False, False)
                else:
                    f, spec = font_for(font_big, size, True, False)
                tw = f.measure(shown)
                th = f.metrics("linespace")
                inf = dict(text=shown, kind=kind, st=st, spec=spec, size=size, w=tw, h=th, font=f)
                if kind == "banner":
                    inf["bw"] = tw + size * 0.76
                    inf["bh"] = size * 1.12
                    inf["ew"], inf["eh"] = inf["bw"], inf["bh"]
                else:
                    inf["ew"], inf["eh"] = tw, th * 0.95
                infos.append(inf)
            rows = make_rows(infos)
            widest = 0
            for row in rows:
                widest = max(widest, sum(infos[i]["ew"] for i in row)
                             + gap_words * (len(row) - 1))
            return infos, rows, widest

        m = 0.62 if anchor else 1.0
        for _ in range(2):
            infos, rows, widest = layout(m)
            if widest <= sw * 0.78:
                break
            m *= sw * 0.78 / widest

        rgap = base * 0.16
        row_h = [max(infos[i]["eh"] for i in row) for row in rows]
        total_h = sum(row_h) + rgap * (len(rows) - 1)
        pos = [None] * n
        y = -total_h / 2
        for row, rh in zip(rows, row_h):
            tot = sum(infos[i]["ew"] for i in row) + gap_words * (len(row) - 1)
            x = random.uniform(-0.006, 0.006) * sw - tot / 2
            cy = y + rh / 2
            for i in row:
                ew = infos[i]["ew"]
                pos[i] = (x + ew / 2, cy + random.uniform(-0.1, 0.1) * base)
                x += ew + gap_words
            y += rh + rgap

        minx = min(pos[i][0] - infos[i]["ew"] / 2 for i in range(n))
        maxx = max(pos[i][0] + infos[i]["ew"] / 2 for i in range(n))
        miny = min(pos[i][1] - infos[i]["eh"] / 2 for i in range(n))
        maxy = max(pos[i][1] + infos[i]["eh"] / 2 for i in range(n))
        margin = 60
        dx = anchor.cx if anchor else sw * (center_x + zone[0])
        if dx + minx < margin:
            dx = margin - minx
        if dx + maxx > sw - margin:
            dx = sw - margin - maxx
        if anchor:
            dy = anchor.bbox[3] + base * 0.25 - miny
            if dy + maxy > sh * 0.94:
                dy = sh * 0.94 - maxy
        else:
            dy = sh * (center_y + zone[1])
            if dy + miny < sh * 0.16:
                dy = sh * 0.16 - miny
            if dy + maxy > sh * 0.9:
                dy = sh * 0.9 - maxy
        self.cx = dx
        self.bbox = (dx + minx, dy + miny, dx + maxx, dy + maxy)

        self.fade = final_fade if final else line_fade_out
        hold_end = start + slot - (0.0 if final else 0.35)
        self.out_start = hold_end
        self.end = hold_end + self.fade + 0.25
        last_max = hold_end - 0.9
        gap_t = (last_max - (start + 0.05)) / max(n - 1, 1)
        gap_t = max(0.12, min(max_word_gap, gap_t))
        timed = wtimes is not None and len(wtimes) == n

        for i, inf in enumerate(infos):
            st, kind = inf["st"], inf["kind"]
            w = Word()
            w.kind = kind
            w.x, w.y = dx + pos[i][0], dy + pos[i][1]
            w.ang = random.uniform(-3, 3) if kind == "small" else random.uniform(-6, 6)
            w.t0 = (start + max(0.0, wtimes[i] - 0.05)) if timed else start + 0.05 + i * gap_t
            w.fade_in = 0.45 if kind in ("banner", "big") else 0.4
            w.fired = w.shown = w.finished = False
            w.sig = None
            w.stagger = random.uniform(0, 0.18)
            w.ph = random.uniform(0, math.tau)
            w.color = (st.get("color") if st else None) or text_color
            w.bw, w.bh = inf.get("bw", 0), inf.get("bh", 0)
            w.bshadow = w.bpoly = w.ghost = None
            w.phone = w.ph_on = w.ph_icon_on = False
            w.scatter = bool(st and st.get("scatter"))
            w.letters, w.sc_on, w.scsig = [], False, None
            w.psig = None
            w.bfill = w.bshadow_col = None
            hid = dict(fill=transparent_color, state="hidden")
            items = []

            if kind == "banner":
                bfill, btext = st.get("banner") or next(banner_cycle)
                w.bfill, w.color = bfill, btext
                w.bshadow = canvas.create_polygon(*([0] * 8), outline="", **hid)
                w.bpoly = canvas.create_polygon(*([0] * 8), outline="", **hid)
                items += [w.bshadow, w.bpoly]

            topts = dict(text=inf["text"], font=inf["spec"], anchor="center",
                         angle=w.ang, tags=("lyric",), **hid)
            w.shadow = canvas.create_text(w.x + 3, w.y + 4, **topts)
            w.main = canvas.create_text(w.x, w.y, **topts)
            items += [w.shadow, w.main]

            if st and st.get("icon") == "phone" and len(inf["text"]) > st.get("split", 2):
                k = st.get("split", 2)
                left, right = inf["text"][:k], inf["text"][k:]
                w.phone = True
                w.ph_size = inf["size"]
                w.ph_lw = inf["font"].measure(left)
                w.ph_rw = inf["font"].measure(right)
                w.ph_tw = inf["w"]
                w.ph_gap = inf["size"] * 0.95
                w.ph_at = min(w.t0 + 0.8, max(w.t0 + 0.2, self.out_start - 1.2))
                popts = dict(font=inf["spec"], anchor="center", angle=w.ang,
                             tags=("lyric",), **hid)
                w.lshadow = canvas.create_text(0, 0, text=left, **popts)
                w.lmain = canvas.create_text(0, 0, text=left, **popts)
                w.rshadow = canvas.create_text(0, 0, text=right, **popts)
                w.rmain = canvas.create_text(0, 0, text=right, **popts)
                w.ph_parts = [w.lshadow, w.lmain, w.rshadow, w.rmain]
                w.ishadow = canvas.create_polygon(*([0] * 8), outline="", **hid)
                w.ibase = canvas.create_polygon(*([0] * 8), outline="", **hid)
                w.idial = canvas.create_oval(0, 0, 1, 1, outline="", **hid)
                w.idot = canvas.create_oval(0, 0, 1, 1, outline="", **hid)
                w.ihandle = canvas.create_line(0, 0, 1, 1, width=max(3, int(inf["size"] * 0.11)),
                                               capstyle="round", **hid)
                w.iknob = canvas.create_oval(0, 0, 1, 1, outline="", **hid)
                w.ph_icon = [w.ishadow, w.ibase, w.idial, w.idot, w.ihandle, w.iknob]
                items += w.ph_parts + w.ph_icon

            if w.scatter:
                txt, fnt = inf["text"], inf["font"]
                for k, ch in enumerate(txt):
                    if ch == " ":
                        continue
                    ox = fnt.measure(txt[:k]) + fnt.measure(ch) / 2 - inf["w"] / 2
                    ls = canvas.create_text(0, 0, text=ch, font=inf["spec"], anchor="center",
                                            angle=w.ang, tags=("lyric",), **hid)
                    lm = canvas.create_text(0, 0, text=ch, font=inf["spec"], anchor="center",
                                            angle=w.ang, tags=("lyric",), **hid)
                    w.letters.append(dict(ox=ox, shadow=ls, main=lm,
                                          delay=random.uniform(0, 0.14),
                                          vx=random.uniform(-0.07, 0.07) * sh,
                                          vy=random.uniform(-0.05, 0.0) * sh,
                                          spin=random.choice([-1, 1]) * random.uniform(140, 330)))
                    items += [ls, lm]

            if st and st.get("ghost") and not anchor:
                px = int(sh * 0.62)
                f, spec = font_for(font_big, px, True, False)
                gw = f.measure(inf["text"])
                if gw > sw * 1.15:
                    px = int(px * sw * 1.15 / gw)
                    f, spec = font_for(font_big, px, True, False)
                w.gx = sw * random.uniform(0.42, 0.58)
                w.gy = sh * random.uniform(0.44, 0.56)
                w.gang = random.uniform(-6, 6)
                w.gvx = random.choice([-1, 1]) * random.uniform(18, 40)
                w.ghost = canvas.create_text(w.gx, w.gy, text=inf["text"], font=spec,
                                             anchor="center", angle=w.gang,
                                             tags=("ghost",), **hid)
                items.append(w.ghost)

            w.items = items
            self.items += items
            self.words.append(w)

        if any(w.ghost for w in self.words):
            gfx.lower("ghost")
        self.sh_ = sh
        if any(w.scatter for w in self.words):
            self.end = max(self.end, self.out_start + 1.4)

    def _scatter(self, w, te):
        """The word breaks into letters that spin and fall (the video's GHOST exit)."""
        cfg, coords, key = gfx.cfg, gfx.coords, transparent_color
        if not w.sc_on:
            w.sc_on = True
            cfg(w.shadow, "-state", "hidden")
            cfg(w.main, "-state", "hidden")
            for L in w.letters:
                cfg(L["shadow"], "-state", "normal")
                cfg(L["main"], "-state", "normal")
        k = 1.0 - clamp01(te / 0.9)
        qa = int(k * color_steps + 0.5)
        if qa != w.scsig:
            w.scsig = qa
            tc, sc = mix(key, w.color, k), mix(key, shadow_color, k)
            for L in w.letters:
                cfg(L["main"], "-fill", tc)
                cfg(L["shadow"], "-fill", sc)
        g = 0.9 * self.sh_
        ar = math.radians(w.ang)
        c, sn = math.cos(ar), math.sin(ar)
        for L in w.letters:
            d = max(0.0, te - L["delay"])
            px = L["ox"] + L["vx"] * d
            py = L["vy"] * d + 0.5 * g * d * d
            x = w.x + px * c + py * sn
            y = w.y - px * sn + py * c
            ang = w.ang + L["spin"] * d
            coords(L["shadow"], x + 3, y + 4)
            coords(L["main"], x, y)
            cfg(L["shadow"], "-angle", ang)
            cfg(L["main"], "-angle", ang)
        if w.ghost:
            cfg(w.ghost, "-fill", mix(key, ghost_color, 1.0 - clamp01(te / 0.18)))

    def _phone(self, w, t, x, y, a):
        """Word splits (PH | ONE?) and a red rotary phone pops in; the handset lifts."""
        cfg, coords = gfx.cfg, gfx.coords
        key = transparent_color
        if not w.ph_on:
            w.ph_on = True
            w.psig = None
            cfg(w.shadow, "-state", "hidden")
            cfg(w.main, "-state", "hidden")
            for it in w.ph_parts:
                cfg(it, "-state", "normal")
        qa = int(a * color_steps + 0.5)
        if qa != w.psig:
            w.psig = qa
            tc, sc = mix(key, w.color, a), mix(key, shadow_color, a)
            cfg(w.lmain, "-fill", tc)
            cfg(w.rmain, "-fill", tc)
            cfg(w.lshadow, "-fill", sc)
            cfg(w.rshadow, "-fill", sc)
            cfg(w.ishadow, "-fill", mix(key, "#0a0d14", a * 0.9))
            cfg(w.ibase, "-fill", mix(key, "#D9381E", a))
            cfg(w.idial, "-fill", mix(key, "#7d170c", a))
            cfg(w.idot, "-fill", mix(key, "#FFB59A", a))
            hc = mix(key, "#F3E9C8", a)
            cfg(w.ihandle, "-fill", hc)
            cfg(w.iknob, "-fill", hc)

        ar = math.radians(w.ang)
        c, sn = math.cos(ar), math.sin(ar)
        s, lw, rw, tw, gp = w.ph_size, w.ph_lw, w.ph_rw, w.ph_tw, w.ph_gap
        se = ease_out_cubic(clamp01((t - w.ph_at) / 0.3))
        tot = lw + gp + rw
        l0, r0 = -tw / 2 + lw / 2, -tw / 2 + lw + rw / 2
        l1 = -tot / 2 + lw / 2
        i1 = -tot / 2 + lw + gp / 2
        r1 = -tot / 2 + lw + gp + rw / 2

        def rot(px, py):
            return x + px * c + py * sn, y - px * sn + py * c

        for shd, mn, px in ((w.lshadow, w.lmain, l0 + (l1 - l0) * se),
                            (w.rshadow, w.rmain, r0 + (r1 - r0) * se)):
            sx, sy = rot(px, 0)
            coords(shd, sx + 3, sy + 4)
            coords(mn, sx, sy)

        if t < w.ph_at + 0.1:
            return
        if not w.ph_icon_on:
            w.ph_icon_on = True
            for it in w.ph_icon:
                cfg(it, "-state", "normal")
        pop = ease_out_back(clamp01((t - w.ph_at - 0.1) / 0.45))
        lift = ease_in_out(clamp01((t - w.ph_at - 0.55) / 0.5))
        ang = lift * math.radians(30) + math.sin(t * 14) * 0.035 * lift
        base_y = 0.36 * s

        def L(u, v):
            return rot(i1 + pop * u * s, base_y + pop * (v - 0.36) * s)

        pts, spts = [], []
        for u, v in ((-0.42, 0.36), (0.42, 0.36), (0.30, 0.12), (-0.30, 0.12)):
            px, py = L(u, v)
            pts += [px, py]
            spts += [px + 4, py + 5]
        coords(w.ishadow, *spts)
        coords(w.ibase, *pts)
        dx, dy = L(0, 0.25)
        rx, ry = 0.15 * s * pop, 0.065 * s * pop
        coords(w.idial, dx - rx, dy - ry, dx + rx, dy + ry)
        r2 = 0.035 * s * pop
        coords(w.idot, dx - r2, dy - r2, dx + r2, dy + r2)
        p1 = L(0.30, 0.07)
        q1 = L(0.30 - 0.66 * math.cos(ang), 0.07 - 0.66 * math.sin(ang))
        coords(w.ihandle, p1[0], p1[1], q1[0], q1[1])
        kr = 0.07 * s * pop
        coords(w.iknob, q1[0] - kr, q1[1] - kr, q1[0] + kr, q1[1] + kr)

    def update(self, t, fire):
        coords, cfg = gfx.coords, gfx.cfg
        for w in self.words:
            if w.finished or t < w.t0:
                continue
            if not w.fired:
                w.fired = True
                if w.kind in ("banner", "big"):
                    fire(w.x, w.y)
            if w.scatter:
                te = t - self.out_start - w.stagger
                if te > 0:
                    if te >= 0.95:
                        w.finished = True
                        for it in w.items:
                            cfg(it, "-state", "hidden")
                    else:
                        self._scatter(w, te)
                    continue
            p = clamp01((t - w.t0) / w.fade_in)
            e = ease_out_cubic(p)
            o = ease_in_cubic(clamp01((t - self.out_start - w.stagger) / self.fade))
            if o >= 1.0:
                w.finished = True
                if w.shown:
                    for it in w.items:
                        cfg(it, "-state", "hidden")
                continue
            a = e * (1 - o)
            ga = ease_out_cubic(clamp01((t - w.t0) / 0.8)) * (1 - o)
            bob_x = math.sin(t * 1.1 + w.ph) * 3.0
            bob_y = math.sin(t * 1.5 + w.ph * 1.3) * 3.0
            x = w.x + bob_x
            y = w.y + (1 - e) * 16 - o * 26 + bob_y

            sig = (int(a * color_steps + 0.5), int(ga * color_steps + 0.5))
            if sig != w.sig:
                w.sig = sig
                extra = () if w.shown else ("-state", "normal")
                w.shown = True
                if w.bpoly:
                    cfg(w.bshadow, "-fill", mix(transparent_color, "#0a0d14", a * 0.9), *extra)
                    cfg(w.bpoly, "-fill", mix(transparent_color, w.bfill, a), *extra)
                cfg(w.shadow, "-fill", mix(transparent_color, shadow_color, a), *extra)
                cfg(w.main, "-fill", mix(transparent_color, w.color, a), *extra)
                if w.ghost:
                    cfg(w.ghost, "-fill", mix(transparent_color, ghost_color, ga), *extra)

            if w.bpoly:
                s = 0.55 + 0.45 * ease_out_back(p)
                hw, hh = w.bw / 2 * s, w.bh / 2 * s
                ar = math.radians(w.ang)
                c, sn = math.cos(ar), math.sin(ar)
                pts, spts = [], []
                for px, py in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
                    rx = px * c + py * sn
                    ry = -px * sn + py * c
                    pts += [x + rx, y + ry]
                    spts += [x + rx + 6, y + ry + 7]
                coords(w.bshadow, *spts)
                coords(w.bpoly, *pts)
            coords(w.shadow, x + 3, y + 4)
            coords(w.main, x, y)
            if w.phone and t >= w.ph_at:
                self._phone(w, t, x, y, a)
            if w.ghost:
                slide = (1 - ease_out_cubic(clamp01((t - w.t0) / 0.9))) * 160
                gx = w.gx + (t - w.t0) * w.gvx - (slide if w.gvx > 0 else -slide)
                coords(w.ghost, gx, w.gy)

        if t >= self.end:
            gfx.delete(*self.items)
            return False
        return True


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class christmas:
    frame_ms = 16

    def __init__(self):
        self.lines = load_lyrics()
        self.end_time = max(s + d for s, _, d, _, _ in self.lines)

        if dpi_aware:
            set_dpi_aware()
        fine_timer(True)
        self.root = tk.Tk()
        self.root.report_callback_exception = self._crash
        self.root.title("Christmas Lyrics Backdrop")
        self.root.overrideredirect(True)
        self.root.configure(bg=tint_color)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 0.0)
        self.set_alpha = partial(self.root.tk.call, "wm", "attributes", self.root._w, "-alpha")
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")
        make_click_through(self.root)
        if use_blur:
            enable_blur(self.root, tint_color, tint_alpha)

        self.win = tk.Toplevel(self.root)
        self.win.title("Christmas Lyrics")
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        self.win.wm_attributes("-transparentcolor", transparent_color)
        self.win.geometry(f"{self.sw}x{self.sh}+0+0")
        self.canvas = tk.Canvas(self.win, width=self.sw, height=self.sh,
                                bg=transparent_color, highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="both", expand=True)
        gfx.bind(self.canvas)
        # centre on what Windows REALLY gave us, not on what we asked for
        try:
            self.win.update()
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw > 200 and ch > 200:
                self.sw, self.sh = cw, ch
            print(f"[lyrics] screen {self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}"
                  f"  canvas {cw}x{ch}  window at {self.win.winfo_rootx()},{self.win.winfo_rooty()}")
        except Exception:
            pass
        if debug_center:  # thin cross at the exact middle, to check alignment
            mx, my = self.sw / 2, self.sh / 2
            self.canvas.create_line(mx - 40, my, mx + 40, my, fill="#FF4040", width=2)
            self.canvas.create_line(mx, my - 40, mx, my + 40, fill="#FF4040", width=2)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.win.bind("<Escape>", lambda e: self.root.destroy())

        self.fonts = {}
        self.lights = Lights(self.canvas, self.sw, self.sh)
        self.snow = build_snow(self.canvas, self.sw, self.sh)

        self.spawned = [False] * len(self.lines)
        self.active = []
        self.sparkles = []
        self.recent_zones = []
        self.prev_line = None
        self.alpha = 0.0
        self.t = 0.0
        self.next_spark = -lead_in + 0.5

        gc.collect()
        gc.freeze()
        gc.set_threshold(30000, 50, 50)

        self.last = time.perf_counter()
        self.t0 = self.last + lead_in
        self.next_frame = self.last
        self._tick()
        self.root.mainloop()
        fine_timer(False)

    def _crash(self, exc, val, tb):
        # never leave a stuck, click-through overlay on screen: log the error and close
        try:
            log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lyrics_error.log")
            with open(log, "w", encoding="utf-8") as fh:
                traceback.print_exception(exc, val, tb, file=fh)
        except Exception:
            pass
        traceback.print_exception(exc, val, tb, file=sys.stderr)
        try:
            self.root.destroy()
        except Exception:
            pass

    def font_for(self, family, px, bold=False, italic=False):
        key = (family, px, bold, italic)
        if key not in self.fonts:
            f = tkfont.Font(family=family, size=-px,
                            weight="bold" if bold else "normal",
                            slant="italic" if italic else "roman")
            style = " ".join(s for s in ("bold" if bold else "", "italic" if italic else "") if s)
            self.fonts[key] = (f, (family, -px, style or "normal"))
        return self.fonts[key]

    def fire(self, x, y):
        for _ in range(3):
            self.sparkles.append(Sparkle(self.canvas, x + random.uniform(-230, 230),
                                         y + random.uniform(-130, 130), self.t))

    def pick_zone(self):
        choices = [z for z in zones if z not in self.recent_zones] or zones
        zone = random.choice(choices)
        self.recent_zones = (self.recent_zones + [zone])[-2:]
        return zone

    def start_line(self, i):
        start, text, slot, wtimes, join = self.lines[i]
        anchor = self.prev_line if join and self.prev_line in self.active else None
        line = LyricLine(self.canvas, text, start, slot, wtimes, self.sw, self.sh,
                         self.pick_zone(), self.font_for, anchor=anchor,
                         final=(i == len(self.lines) - 1))
        if anchor:  # stacked lines leave together
            anchor.out_start, anchor.fade, anchor.end = line.out_start, line.fade, line.end
        self.prev_line = line
        self.active.append(line)
        self.spawned[i] = True

    def _tick(self):
        now = time.perf_counter()
        t = now - self.t0
        dt = min(0.05, now - self.last)
        self.last = now
        self.t = t
        ending = t > self.end_time

        for i, (start, _, _, _, _) in enumerate(self.lines):
            if not self.spawned[i] and t >= start:
                self.start_line(i)

        if not ending and t >= self.next_spark and len(self.sparkles) < 16:
            self.sparkles.append(Sparkle(self.canvas, random.uniform(40, self.sw - 40),
                                         random.uniform(self.sh * 0.1, self.sh * 0.95), t))
            self.next_spark = t + random.uniform(0.12, 0.35)

        env = ease_in_out(clamp01((t + lead_in) / 2.0)) * (1 - ease_in_out(clamp01((t - self.end_time) / final_fade)))

        self.lights.update(t, env)
        for f in self.snow:
            f.update(dt, t, ending, env)
        self.snow = [f for f in self.snow if not f.gone]
        self.sparkles = [s for s in self.sparkles if s.update(t)]
        self.active = [ln for ln in self.active if ln.update(t, self.fire)]

        fade_in = ease_in_out(clamp01((t + lead_in) / 2.0))
        fade_out = ease_in_out(clamp01((t - self.end_time) / (final_fade + 0.5)))
        alpha = round(min(0.96, tint_alpha * fade_in * (1 - fade_out)) * 255) / 255
        try:
            if alpha != self.alpha:
                self.alpha = alpha
                self.set_alpha(alpha)
        except tk.TclError:
            pass

        finished = not (self.snow or self.active or self.sparkles)
        if (ending and t > self.end_time + 1 and finished) or t > self.end_time + 10:
            self.root.destroy()
            return

        self.next_frame += self.frame_ms / 1000.0
        after = time.perf_counter()
        if self.next_frame < after:
            self.next_frame = after
        self.root.after(max(2, int((self.next_frame - after) * 1000)), self._tick)


if __name__ == "__main__":
    christmas()