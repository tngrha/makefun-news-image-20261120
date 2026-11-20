#!/usr/bin/env python3
"""The World on One Page -- Friday 20 November 2026.

make.fun competition news-image-20261120 entry. Pure Python 3.13 standard
library only (the sandbox is python:3.13-slim with no Pillow and no fonts):
a hand-rolled RGB framebuffer, a 5x7 bitmap font, flat geometric pictograms,
a dotted-grid world map from simplified continent polygons, and a hand PNG
encoder. Writes /output/entry.png (PNG, 1024x1024, <= 1 MiB). Fully
deterministic: no randomness, no clock, no network; two runs are
byte-identical.

Content: 35 verified stories from Friday 20 November 2026 -- 1 hero +
11 illustrated panels + 23 numbered one-line briefs -- across 6 continents,
each with one concrete number or fact. Disputed claims are attributed.
Sources are listed in the footer.
"""

import binascii
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
PAPER = (250, 248, 242)
INK = (28, 28, 30)
NAVY = (18, 38, 74)
NAVY_DARK = (12, 26, 52)
RED = (178, 34, 52)
GOLD = (214, 154, 32)
GREY = (105, 105, 108)
RULE = (196, 192, 182)
MAP_LAND = (206, 214, 224)
MAP_BG = (240, 244, 248)
WHITE = (255, 255, 255)
SKY = (188, 216, 238)
SKY2 = (226, 238, 246)
NIGHT = (32, 40, 68)
FIRE = (238, 116, 28)
GREEN_D = (24, 120, 58)

REGION_COLORS = {
    "EUROPE": (31, 90, 180),
    "ASIA": (190, 40, 40),
    "MIDDLE EAST": (215, 110, 20),
    "AFRICA": (20, 130, 60),
    "N. AMERICA": (110, 50, 160),
    "S. AMERICA": (0, 130, 140),
    "OCEANIA": (150, 100, 40),
    "GLOBAL": (18, 38, 74),
    "SCIENCE": (90, 60, 140),
}

# --------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph: 7 rows of 5 pixels, '#' = ink.
# --------------------------------------------------------------------------
_FONT_RAW = {
    " ": "...../...../...../...../...../...../.....",
    "!": "..#../..#../..#../..#../..#../...../..#..",
    '"': ".#.#./.#.#./.#.#./...../...../...../.....",
    "#": ".#.#./.#.#./#####/.#.#./#####/.#.#./.#.#.",
    "$": "..#../.####/#.#../.###./..#.#/####./..#..",
    "%": "##..#/##.#./...#./..#../.#.../.#.##/#..##",
    "&": ".##../#..#./#.#../.#.../#.#.#/#..#./.##.#",
    "'": "..#../..#../.#.../...../...../...../.....",
    "(": "...#./..#../.#.../.#.../.#.../..#../...#.",
    ")": ".#.../..#../...#./...#./...#./..#../.#...",
    "*": "...../.#.#./..#../#####/..#../.#.#./.....",
    "+": "...../..#../..#../#####/..#../..#../.....",
    ",": "...../...../...../...../...../.##../.#...",
    "-": "...../...../...../#####/...../...../.....",
    ".": "...../...../...../...../...../...../.##..",
    "/": "....#/....#/...#./..#../.#.../#..../#....",
    "0": ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    "1": "..#../.##../..#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####",
    "3": ".###./#...#/....#/..##./....#/#...#/.###.",
    "4": "...#./..##./.#.#./#..#./#####/...#./...#.",
    "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": "..##./.#.../#..../####./#...#/#...#/.###.",
    "7": "#####/....#/...#./..#../..#../..#../..#..",
    "8": ".###./#...#/#...#/.###./#...#/#...#/.###.",
    "9": ".###./#...#/#...#/.####/....#/...#./.##..",
    ":": "...../.##../.##../...../.##../.##../.....",
    ";": "...../.##../.##../...../.##../.##../.#...",
    "<": "....#/...#./..#../.#.../..#../...#./....#",
    "=": "...../...../#####/...../#####/...../.....",
    ">": "#..../.#.../..#../...#./..#../.#.../#....",
    "?": ".###./#...#/....#/..##./..#../...../..#..",
    "@": ".###./#...#/#.###/#.#.#/#.###/#..../.###.",
    "A": ".###./#...#/#...#/#####/#...#/#...#/#...#",
    "B": "####./#...#/#...#/####./#...#/#...#/####.",
    "C": ".####/#..../#..../#..../#..../#..../.####",
    "D": "####./#...#/#...#/#...#/#...#/#...#/####.",
    "E": "#####/#..../#..../####./#..../#..../#####",
    "F": "#####/#..../#..../####./#..../#..../#....",
    "G": ".####/#..../#..../#.###/#...#/#...#/.###.",
    "H": "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    "I": "#####/..#../..#../..#../..#../..#../#####",
    "J": "..###/...#./...#./...#./...#./#..#./.##..",
    "K": "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    "L": "#..../#..../#..../#..../#..../#..../#####",
    "M": "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    "N": "#...#/##..#/##..#/#.#.#/#..##/#..##/#...#",
    "O": ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    "P": "####./#...#/#...#/####./#..../#..../#....",
    "Q": ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    "R": "####./#...#/#...#/####./#.#../#..#./#...#",
    "S": ".####/#..../#..../.###./....#/....#/####.",
    "T": "#####/..#../..#../..#../..#../..#../..#..",
    "U": "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    "V": "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    "W": "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    "X": "#...#/.#.#./..#../..#../..#../.#.#./#...#",
    "Y": "#...#/#...#/.#.#./..#../..#../..#../..#..",
    "Z": "#####/....#/...#./..#../.#.../#..../#####",
    "[": ".###./.#.../.#.../.#.../.#.../.#.../.###.",
    "]": ".###./...#./...#./...#./...#./...#./.###.",
    "_": "...../...../...../...../...../...../#####",
    "a": "...../...../.###./....#/.####/#...#/.####",
    "b": "#..../#..../####./#...#/#...#/#...#/####.",
    "c": "...../...../.####/#..../#..../#..../.####",
    "d": "....#/....#/.####/#...#/#...#/#...#/.####",
    "e": "...../...../.###./#...#/#####/#..../.###.",
    "f": "..##./.#.../#####/.#.../.#.../.#.../.#...",
    "g": "...../.####/#...#/#...#/.####/....#/.###.",
    "h": "#..../#..../####./#...#/#...#/#...#/#...#",
    "i": "..#../...../.##../..#../..#../..#../.###.",
    "j": "...#./...../..##./...#./...#./...#./.##..",
    "k": "#..../#..../#..#./#.#../##.../#.#../#..#.",
    "l": ".##../..#../..#../..#../..#../..#../.###.",
    "m": "...../...../##.#./#.#.#/#.#.#/#.#.#/#.#.#",
    "n": "...../...../####./#...#/#...#/#...#/#...#",
    "o": "...../...../.###./#...#/#...#/#...#/.###.",
    "p": "...../...../####./#...#/####./#..../#....",
    "q": "...../...../.####/#...#/.####/....#/....#",
    "r": "...../...../#.##./##..#/#..../#..../#....",
    "s": "...../...../.####/#..../.###./....#/####.",
    "t": ".#.../.#.../#####/.#.../.#.../.#.../..##.",
    "u": "...../...../#...#/#...#/#...#/#..##/.##.#",
    "v": "...../...../#...#/#...#/#...#/.#.#./..#..",
    "w": "...../...../#...#/#...#/#.#.#/#.#.#/.#.#.",
    "x": "...../...../#...#/.#.#./..#../.#.#./#...#",
    "y": "...../...../#...#/#...#/.####/....#/.###.",
    "z": "...../...../#####/...#./..#../.#.../#####",
    "|": "..#../..#../..#../..#../..#../..#../..#..",
    "~": "...../...../.##.#/#..##/...../...../.....",
    "·": "...../...../...../.##../.##../...../.....",
    "°": ".##../#..#./#..#./.##../...../...../.....",
    "×": "...../#...#/.#.#./..#../.#.#./#...#/.....",
    "£": "..###/.#.../.#.../#####/.#.../.#.../#####",
    "€": "..###/.#.../#####/.#.../#####/.#.../..###",
    "–": "...../...../...../#####/...../...../.....",
    "—": "...../...../...../#####/...../...../.....",
    "‘": "..#../..#../.#.../...../...../...../.....",
    "’": "..#../..#../.#.../...../...../...../.....",
    "“": ".#.#./.#.#./.#.#./...../...../...../.....",
    "”": ".#.#./.#.#./.#.#./...../...../...../.....",
    "Ñ": "#...#/##..#/##..#/#.#.#/#..##/#..##/#...#",
    "ñ": "...../...../####./#...#/#...#/#...#/#...#",
}
FONT = {ch: rows.split("/") for ch, rows in _FONT_RAW.items()}
EMPTY_GLYPH = ["....."] * 7


# --------------------------------------------------------------------------
# Framebuffer + primitives
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bg * (w * h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(color)

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def rect(self, x, y, w, h, color):
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.px(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def thick_line(self, x0, y0, x1, y1, color, t=2):
        for ox in range(t):
            for oy in range(t):
                self.line(x0 + ox, y0 + oy, x1 + ox, y1 + oy, color)

    def circle(self, cx, cy, r, color, fill=True):
        r2 = r * r
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if fill:
                    if d2 <= r2:
                        self.px(xx, yy, color)
                else:
                    if r2 - 2 * r <= d2 <= r2:
                        self.px(xx, yy, color)

    def poly(self, pts, color):
        """Scanline polygon fill (even-odd)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, min(ys))
        y1 = min(self.h - 1, max(ys))
        n = len(pts)
        for yy in range(y0, y1 + 1):
            nodes = []
            for i in range(n):
                xa, ya = pts[i]
                xb, yb = pts[(i + 1) % n]
                if ya == yb:
                    continue
                if (ya <= yy < yb) or (yb <= yy < ya):
                    nodes.append(xa + (yy - ya) * (xb - xa) / (yb - ya))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                xa = int(round(nodes[k]))
                xb = int(round(nodes[k + 1]))
                self.fill_rect(xa, yy, xb - xa + 1, 1, color)

    def text(self, x, y, s, color, scale=1, bold=False):
        """Draw text with the 5x7 font; returns the advance width in px."""
        adv = 6 * scale
        cx = x
        for ch in s:
            glyph = FONT.get(ch, EMPTY_GLYPH)
            for row in range(7):
                line = glyph[row]
                for col in range(5):
                    if line[col] == "#":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
                        if bold:
                            self.fill_rect(cx + col * scale + 1,
                                           y + row * scale, scale, scale,
                                           color)
            cx += adv
        return cx - x


def text_width(s, scale=1):
    return len(s) * 6 * scale


def wrap(s, max_chars):
    """Greedy word wrap to at most max_chars characters per line."""
    words = s.split()
    lines = []
    cur = ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, s, color, scale, max_chars, leading, bold=False,
               max_lines=None):
    lines = wrap(s, max_chars)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, ln in enumerate(lines):
        cv.text(x, y + i * leading, ln, color, scale, bold)
    return y + len(lines) * leading


# --------------------------------------------------------------------------
# PNG encoder (8-bit RGB, filter 0 scanlines, zlib)
# --------------------------------------------------------------------------
def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)
        raw.extend(cv.buf[yy * stride:(yy + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# --------------------------------------------------------------------------
# Pictograms (flat geometric scenes drawn inside a box)
# --------------------------------------------------------------------------
def draw_flag(cv, x, y, w, h, kind):
    """Flag on a pole; pole at x, flag flies to the right."""
    cv.vline(x, y, h + 8, (70, 70, 76))
    cv.vline(x + 1, y, h + 8, (70, 70, 76))
    fx = x + 2
    if kind == "us":
        cv.fill_rect(fx, y, w, h, WHITE)
        for i in range(3):
            cv.fill_rect(fx, y + i * (h // 3), w, max(1, h // 6), RED)
        cv.fill_rect(fx, y, w // 2, h // 2, NAVY)
    elif kind == "china":
        cv.fill_rect(fx, y, w, h, (222, 41, 16))
        cv.circle(fx + 4, y + 4, 2, (255, 222, 0))
        cv.circle(fx + 9, y + 2, 1, (255, 222, 0))
        cv.circle(fx + 10, y + 6, 1, (255, 222, 0))
    elif kind == "russia":
        t = h // 3
        cv.fill_rect(fx, y, w, t, WHITE)
        cv.fill_rect(fx, y + t, w, t, (0, 57, 166))
        cv.fill_rect(fx, y + 2 * t, w, h - 2 * t, (213, 43, 30))
    elif kind == "venezuela":
        t = h // 3
        cv.fill_rect(fx, y, w, t, (252, 209, 22))
        cv.fill_rect(fx, y + t, w, t, (0, 45, 114))
        cv.fill_rect(fx, y + 2 * t, w, h - 2 * t, (206, 17, 38))
    cv.rect(fx, y, w, h, (120, 120, 126))


def skyline(cv, x, y, w, h, color, heights):
    """Row of building rectangles sitting on the bottom of the box."""
    n = len(heights)
    bw = w // n
    for i, frac in enumerate(heights):
        bh = max(3, int(h * frac))
        cv.fill_rect(x + i * bw + 1, y + h - bh, bw - 2, bh, color)


def pic_summit(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY2)
    cv.fill_rect(x, y, w, h // 2, SKY)
    cv.circle(x + w - 34, y + 22, 11, (250, 200, 60))
    skyline(cv, x, y + h - 46, w, 46, NAVY_DARK,
            [0.5, 0.8, 0.62, 0.95, 0.55, 0.75, 0.45, 0.88, 0.6, 0.7])
    cv.fill_rect(x, y + h - 4, w, 4, NAVY_DARK)
    fy = y + 18
    draw_flag(cv, x + 26, fy, 34, 20, "us")
    draw_flag(cv, x + 110, fy - 6, 34, 20, "china")
    draw_flag(cv, x + 194, fy, 34, 20, "russia")


def pic_kyiv(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NIGHT)
    skyline(cv, x, y + h - 14, w, 14, (18, 22, 40),
            [0.6, 0.9, 0.5, 0.8, 0.65, 0.95, 0.55, 0.75])
    # missile arc (dashed) + explosion star
    for i in range(12):
        t = i / 11.0
        px = int(x + 8 + t * (w - 60))
        py = int(y + 4 + (t * t) * (h - 16))
        if i % 2 == 0:
            cv.fill_rect(px, py, 3, 2, (255, 190, 80))
    ex, ey = x + w - 38, y + h - 16
    cv.circle(ex, ey, 4, FIRE)
    cv.circle(ex, ey, 2, (255, 220, 120))
    for dx, dy in [(8, 0), (-8, 0), (0, -7), (6, -6), (-6, -6), (5, 5), (-5, 5)]:
        cv.line(ex, ey, ex + dx, ey + dy, FIRE)
    for sx, sy in [(10, 6), (40, 3), (70, 8), (120, 4), (160, 7)]:
        cv.px(x + sx % max(1, w - 4), y + sy, WHITE)


def pic_tower(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY2)
    tx = x + w // 2 - 9
    cv.fill_rect(tx, y + 2, 18, h - 2, (90, 100, 120))
    cv.fill_rect(tx - 2, y + 2, 22, 3, (70, 80, 100))
    for r in range(3):
        for c in range(3):
            cv.fill_rect(tx + 3 + c * 5, y + 7 + r * 5, 3, 3, (200, 220, 240))
    # shattered windows near the top
    cv.fill_rect(tx + 3, y + 7, 3, 3, (30, 30, 36))
    cv.fill_rect(tx + 8, y + 12, 3, 3, (30, 30, 36))
    cv.circle(tx + 22, y + 6, 3, (150, 150, 156))
    cv.circle(tx + 27, y + 3, 2, (170, 170, 176))
    skyline(cv, x, y + h - 8, w, 8, (140, 150, 168), [0.7, 0.5, 0.9, 0.6])


def pic_court(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY2)
    cx = x + w // 2
    # pediment
    cv.poly([(cx - 30, y + 10), (cx + 30, y + 10), (cx, y + 2)], NAVY)
    cv.fill_rect(cx - 30, y + 10, 60, 3, NAVY)
    for i in range(5):
        cv.fill_rect(cx - 26 + i * 12, y + 13, 5, h - 18, NAVY)
    cv.fill_rect(cx - 32, y + h - 5, 64, 3, NAVY)
    cv.fill_rect(cx - 36, y + h - 2, 72, 2, NAVY)


def pic_chart_up(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    base = y + h - 4
    bars = [0.25, 0.4, 0.55, 0.75, 0.95]
    bw = w // 8
    for i, f in enumerate(bars):
        bh = int((h - 8) * f)
        cv.fill_rect(x + 10 + i * bw, base - bh, bw - 6, bh, (160, 190, 230))
    pts = [(x + 12 + i * bw, base - int((h - 8) * f)) for i, f in enumerate(bars)]
    for i in range(len(pts) - 1):
        cv.thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                      GREEN_D, 2)
    ax, ay = pts[-1]
    cv.poly([(ax, ay - 6), (ax - 6, ay + 2), (ax + 2, ay + 3)], GREEN_D)


def pic_chart_down(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    top = y + 4
    pts = [(x + 12, top), (x + w // 3, top + 6), (x + w // 2, top + 4),
           (x + 2 * w // 3, top + 12), (x + w - 16, y + h - 8)]
    for i in range(len(pts) - 1):
        cv.thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)
    ax, ay = pts[-1]
    cv.poly([(ax, ay + 6), (ax - 6, ay - 2), (ax + 3, ay - 3)], RED)


def pic_globe(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY2)
    cx, cy, r = x + w // 2, y + h // 2, min(13, h // 2 - 1)
    cv.circle(cx, cy, r, (70, 140, 210))
    cv.circle(cx, cy, r, NAVY, fill=False)
    cv.hline(cx - r, cy, 2 * r + 1, NAVY)
    cv.hline(cx - r + 3, cy - r // 2, 2 * r - 5, NAVY)
    cv.hline(cx - r + 3, cy + r // 2, 2 * r - 5, NAVY)
    cv.vline(cx, cy - r, 2 * r + 1, NAVY)
    cv.circle(cx - r // 2, cy - r // 3, 3, GREEN_D)
    cv.circle(cx + r // 3, cy + r // 4, 2, GREEN_D)
    cv.circle(x + w - 20, y + 8, 5, (250, 200, 60))


def pic_jet(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    # dashed border
    for i in range(0, w, 12):
        cv.fill_rect(x + i, y + h - 5, 7, 2, RED)
    jx, jy = x + w // 2, y + 10
    cv.poly([(jx - 16, jy), (jx + 14, jy + 2), (jx + 16, jy + 4),
             (jx - 12, jy + 4)], NAVY_DARK)
    cv.poly([(jx - 2, jy + 3), (jx + 4, jy + 3), (jx + 8, jy + 9),
             (jx - 6, jy + 9)], NAVY_DARK)
    cv.poly([(jx - 14, jy), (jx - 10, jy - 6), (jx - 7, jy)], NAVY_DARK)
    cv.line(x + 8, jy + 2, jx - 18, jy + 2, WHITE)
    cv.line(x + 8, jy + 5, jx - 16, jy + 5, WHITE)


def pic_radar(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (16, 40, 28))
    cx, cy, r = x + w // 2, y + h // 2, min(13, h // 2 - 1)
    cv.circle(cx, cy, r, (40, 200, 110), fill=False)
    cv.circle(cx, cy, r * 2 // 3, (40, 200, 110), fill=False)
    cv.circle(cx, cy, r // 3, (40, 200, 110), fill=False)
    cv.line(cx, cy, cx + r, cy - r // 2, (120, 255, 170))
    cv.circle(cx - 5, cy + 3, 2, (255, 220, 90))
    cv.circle(cx + 6, cy - 4, 2, (255, 220, 90))


def pic_virus(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (240, 232, 220))
    cx, cy, r = x + w // 2, y + h // 2, 8
    for dx, dy in [(10, 0), (-10, 0), (0, 9), (0, -9), (7, 6), (-7, 6),
                   (7, -6), (-7, -6)]:
        cv.line(cx, cy, cx + dx, cy + dy, (170, 60, 60))
        cv.circle(cx + dx, cy + dy, 2, (170, 60, 60))
    cv.circle(cx, cy, r, (205, 80, 80))
    cv.circle(cx - 3, cy - 2, 2, (240, 160, 160))
    cv.circle(cx + 3, cy + 3, 2, (240, 160, 160))


def pic_flags(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY2)
    draw_flag(cv, x + w // 2 - 46, y + 3, 30, 12, "us")
    draw_flag(cv, x + w // 2 + 14, y + 3, 30, 12, "venezuela")


def pic_voyager(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (10, 12, 34))
    for sx, sy in [(8, 5), (30, 12), (52, 4), (90, 9), (130, 5), (170, 11),
                   (200, 6), (60, 20), (150, 18)]:
        if x + sx < x + w - 2:
            cv.px(x + sx, y + sy, WHITE)
    # dashed trajectory
    for i in range(0, w - 40, 10):
        cv.fill_rect(x + 6 + i, y + h - 8 - i // 12, 5, 1, (120, 150, 220))
    vx, vy = x + w - 52, y + 3
    cv.fill_rect(vx, vy + 3, 16, 7, (200, 200, 208))
    cv.poly([(vx + 16, vy + 3), (vx + 30, vy), (vx + 30, vy + 14),
             (vx + 16, vy + 10)], (230, 230, 238))
    cv.line(vx + 8, vy + 10, vx + 8, vy + 17, (200, 200, 208))
    cv.circle(x + w - 14, y + 6, 3, (250, 220, 120))


PICTOGRAMS = {
    "summit": pic_summit,
    "kyiv": pic_kyiv,
    "tower": pic_tower,
    "court": pic_court,
    "chart_up": pic_chart_up,
    "chart_down": pic_chart_down,
    "globe": pic_globe,
    "jet": pic_jet,
    "radar": pic_radar,
    "virus": pic_virus,
    "flags": pic_flags,
    "voyager": pic_voyager,
}

# --------------------------------------------------------------------------
# World map: simplified continent polygons in (lon, lat), equirectangular.
# --------------------------------------------------------------------------
CONTINENTS = [
    # North America
    [(-168, 66), (-161, 70), (-152, 71), (-140, 70), (-128, 70), (-115, 68),
     (-102, 69), (-92, 69), (-85, 66), (-82, 62), (-80, 58), (-78, 62),
     (-72, 58), (-65, 52), (-60, 47), (-64, 45), (-68, 44), (-70, 42),
     (-74, 40), (-75, 37), (-79, 34), (-81, 31), (-81, 26), (-83, 28),
     (-86, 30), (-90, 29), (-94, 30), (-97, 27), (-97, 22), (-96, 18),
     (-94, 18), (-91, 19), (-90, 21), (-88, 16), (-87, 15), (-85, 11),
     (-83, 9), (-79, 9), (-78, 8), (-80, 9), (-84, 12), (-87, 13),
     (-90, 14), (-93, 15), (-95, 16), (-97, 16), (-101, 18), (-104, 20),
     (-107, 23), (-110, 24), (-112, 29), (-115, 32), (-119, 34), (-122, 37),
     (-124, 43), (-124, 48), (-128, 51), (-133, 56), (-140, 60), (-148, 61),
     (-155, 59), (-160, 58), (-164, 60), (-166, 61)],
    # Greenland
    [(-45, 60), (-42, 65), (-40, 70), (-30, 68), (-22, 70), (-20, 74),
     (-22, 78), (-30, 80), (-45, 80), (-55, 76), (-58, 72), (-55, 68),
     (-52, 64), (-48, 61)],
    # South America
    [(-78, 7), (-76, 10), (-73, 11), (-70, 12), (-65, 11), (-62, 10),
     (-60, 8), (-55, 6), (-52, 4), (-50, 0), (-46, -2), (-42, -3),
     (-38, -5), (-35, -8), (-37, -11), (-39, -14), (-39, -17), (-40, -21),
     (-42, -23), (-47, -25), (-49, -28), (-52, -32), (-54, -34), (-57, -37),
     (-58, -39), (-62, -39), (-63, -41), (-65, -43), (-65, -46), (-67, -49),
     (-68, -52), (-69, -54), (-71, -54), (-73, -51), (-74, -48), (-74, -44),
     (-73, -40), (-72, -36), (-71, -31), (-70, -27), (-70, -22), (-70, -18),
     (-72, -16), (-75, -15), (-77, -12), (-78, -9), (-79, -6), (-81, -4),
     (-81, -1), (-80, 1), (-79, 4), (-77, 5)],
    # Africa
    [(-6, 35), (-2, 35), (3, 37), (8, 37), (10, 37), (11, 34), (15, 32),
     (20, 32), (25, 32), (30, 31), (32, 31), (34, 28), (36, 24), (38, 21),
     (40, 16), (42, 13), (43, 12), (46, 11), (48, 11), (51, 12), (51, 10),
     (50, 7), (47, 4), (42, 0), (41, -3), (40, -7), (40, -11), (39, -15),
     (37, -18), (36, -21), (35, -24), (34, -27), (32, -29), (29, -31),
     (27, -33), (24, -34), (20, -35), (19, -34), (17, -32), (16, -29),
     (15, -27), (14, -23), (13, -19), (13, -15), (12, -11), (13, -7),
     (12, -4), (10, -1), (9, 2), (9, 4), (6, 4), (3, 6), (0, 5), (-3, 5),
     (-7, 4), (-11, 7), (-14, 8), (-16, 12), (-17, 15), (-17, 18),
     (-16, 21), (-16, 24), (-15, 27), (-13, 28), (-10, 30), (-8, 32)],
    # Madagascar
    [(44, -16), (47, -14), (50, -16), (49, -20), (47, -24), (45, -25),
     (44, -22), (43, -19)],
    # Europe (mainland + Scandinavia)
    [(-9, 37), (-9, 43), (-4, 44), (-1, 46), (-2, 48), (0, 49), (2, 51),
     (5, 53), (8, 54), (8, 56), (9, 57), (10, 59), (6, 60), (5, 61),
     (8, 63), (11, 65), (13, 67), (16, 68), (20, 70), (24, 71), (28, 71),
     (31, 70), (35, 67), (40, 66), (44, 64), (46, 60), (44, 55), (40, 52),
     (38, 49), (36, 46), (33, 45), (31, 46), (29, 44), (28, 41), (26, 40),
     (24, 38), (23, 36), (22, 37), (20, 39), (19, 41), (16, 39), (16, 41),
     (14, 42), (12, 44), (10, 44), (8, 44), (6, 43), (3, 42), (3, 41),
     (0, 39), (-2, 37), (-5, 36)],
    # Britain
    [(-6, 50), (-4, 50), (-2, 51), (0, 51), (1, 52), (0, 54), (-1, 55),
     (-2, 57), (-4, 58), (-6, 58), (-7, 57), (-6, 55), (-5, 54), (-4, 53),
     (-3, 52), (-5, 51)],
    # Ireland
    [(-10, 52), (-8, 52), (-6, 52), (-6, 54), (-7, 55), (-9, 54), (-10, 53)],
    # Iceland
    [(-22, 64), (-18, 63), (-14, 64), (-15, 66), (-20, 66), (-22, 65)],
    # Asia
    [(27, 38), (30, 36), (36, 36), (36, 33), (35, 29), (38, 24), (40, 18),
     (42, 14), (43, 12), (45, 12), (49, 14), (54, 16), (58, 20), (59, 22),
     (57, 24), (54, 26), (51, 28), (49, 29), (48, 27), (50, 24), (54, 24),
     (57, 24), (58, 26), (57, 27), (58, 26), (61, 25), (63, 25), (66, 25),
     (68, 23), (70, 22), (72, 21), (72, 19), (73, 15), (75, 11), (77, 8),
     (80, 10), (80, 13), (81, 15), (83, 17), (85, 19), (87, 21), (89, 22),
     (91, 22), (92, 20), (93, 18), (95, 16), (97, 15), (98, 12), (99, 9),
     (100, 6), (101, 3), (103, 2), (104, 6), (105, 9), (107, 9),
     (109, 12), (109, 15), (108, 20), (111, 21), (115, 23), (118, 25),
     (120, 27), (122, 31), (121, 34), (122, 38), (126, 38), (127, 36),
     (129, 38), (128, 40), (130, 42), (133, 43), (136, 42), (139, 43),
     (141, 46), (142, 50), (142, 54), (145, 59), (150, 59), (152, 56),
     (155, 53), (157, 52), (156, 51), (158, 53), (160, 57), (162, 61),
     (169, 66), (178, 65), (178, 68), (172, 70), (163, 70), (155, 71),
     (148, 71), (141, 72), (134, 72), (127, 72), (120, 73), (113, 74),
     (106, 75), (100, 77), (94, 76), (87, 74), (80, 73), (74, 72),
     (68, 71), (62, 69), (56, 68), (50, 68), (44, 67), (38, 66), (33, 66),
     (32, 69), (30, 70), (29, 66), (30, 61), (31, 56), (33, 52), (35, 48),
     (37, 45), (38, 43), (36, 42), (33, 42), (30, 41), (28, 41), (27, 39)],
    # Japan
    [(130, 31), (132, 33), (134, 34), (136, 34), (138, 35), (140, 36),
     (141, 38), (141, 40), (142, 42), (143, 43), (141, 44), (140, 42),
     (139, 39), (138, 36), (136, 35), (134, 34), (132, 33), (130, 32)],
    # Borneo
    [(109, 1), (113, 2), (117, 3), (119, 2), (118, -1), (115, -3), (111, -2),
     (109, 0)],
    # Sumatra
    [(95, 5), (99, 2), (103, -2), (106, -6), (104, -5), (100, -1), (97, 3)],
    # Java
    [(106, -6), (110, -7), (114, -8), (114, -9), (110, -8), (106, -7)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -9), (147, -9),
     (142, -8), (137, -7), (132, -4)],
    # Australia
    [(113, -22), (114, -28), (115, -34), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (137, -35), (139, -37), (140, -38), (145, -38),
     (147, -38), (150, -37), (153, -30), (153, -27), (151, -24), (149, -20),
     (146, -19), (145, -15), (143, -11), (142, -11), (142, -13), (141, -17),
     (140, -18), (136, -15), (136, -12), (135, -12), (133, -11), (130, -12),
     (126, -14), (122, -17), (118, -20), (114, -21)],
    # New Zealand
    [(167, -46), (169, -44), (171, -42), (173, -41), (174, -40), (176, -38),
     (178, -37), (176, -37), (175, -39), (174, -41), (172, -42), (170, -43),
     (168, -46)],
]


def project(lon, lat, mx, my, mw, mh):
    x = mx + (lon + 180.0) / 360.0 * mw
    y = my + (82.0 - lat) / 137.0 * mh
    return int(round(x)), int(round(y))


def draw_map(cv, mx, my, mw, mh, pins):
    cv.fill_rect(mx, my, mw, mh, MAP_BG)
    # graticule every 30 degrees
    grat = (222, 230, 240)
    for lon in range(-150, 181, 30):
        gx, _ = project(lon, 0, mx, my, mw, mh)
        cv.vline(gx, my, mh, grat)
    for lat in range(-30, 61, 30):
        _, gy = project(0, lat, mx, my, mw, mh)
        cv.hline(mx, gy, mw, grat)
    # land
    for poly_ll in CONTINENTS:
        pts = [project(lon, lat, mx, my, mw, mh) for lon, lat in poly_ll]
        cv.poly(pts, MAP_LAND)
        for i in range(len(pts)):
            xa, ya = pts[i]
            xb, yb = pts[(i + 1) % len(pts)]
            cv.line(xa, ya, xb, yb, (150, 165, 185))
    cv.rect(mx, my, mw, mh, (150, 165, 185))
    cv.text(mx + 6, my + 5, "WHERE IT HAPPENED", NAVY, 1, bold=True)
    # pins
    for num, lon, lat, color, dx, dy in pins:
        cx, cy = project(lon, lat, mx, my, mw, mh)
        cx += dx
        cy += dy
        cv.circle(cx, cy, 7, WHITE)
        cv.circle(cx, cy, 6, color)
        s = str(num)
        cv.text(cx - text_width(s, 1) // 2, cy - 3, s, WHITE, 1, bold=True)
    # deep-space star for the Voyager story (pin 12)
    sx, sy = mx + mw - 16, my + 12
    cv.circle(sx, sy, 7, WHITE)
    cv.circle(sx, sy, 6, (90, 60, 140))
    cv.text(sx - text_width("12", 1) // 2, sy - 3, "12", WHITE, 1, bold=True)


# --------------------------------------------------------------------------
# Stories -- all verified from Friday 20 November 2026 reporting.
# --------------------------------------------------------------------------
# (number, region, topic, headline, summary, pictogram, (lon, lat) pin or None)
PANELS = [
    (2, "EUROPE", "UKRAINE WAR", "KYIV HIT BY 110 MISSILES IN OVERNIGHT STRIKE",
     "Russia fired about 110 missiles and 400 drones over 10 hours, killing 9 "
     "and injuring 28. Bridges over the Dnipro were targeted.",
     "kyiv", (30.5, 50.4)),
    (3, "N. AMERICA", "MARKETS", "ANTHROPIC IPO RAISES RECORD $81.3B",
     "The AI firm's Nasdaq debut closed at $97, up 17% from its $83 offer "
     "price, valuing it near $1.5 trillion. Ticker: ANT.",
     "chart_up", (-74.0, 40.7)),
    (4, "GLOBAL", "JUSTICE", "ICJ RULES MYANMAR COMMITTED GENOCIDE",
     "In a 9-6 vote, the World Court found Myanmar committed genocide "
     "against the Rohingya. Over 1.3M were displaced.",
     "court", (4.3, 52.1)),
    (5, "MIDDLE EAST", "SAUDI", "MISSILE HITS RIYADH TOWER",
     "A Houthi missile damaged the 80-story PIF tower, shattering windows "
     "across up to 8 floors. No injuries.",
     "tower", (46.7, 24.6)),
    (6, "GLOBAL", "CLIMATE", "COP31 DRAFT DROPS FOSSIL PHASE-OUT",
     "The Antalya draft dropped fossil-fuel phase-out language and the "
     "$120bn adaptation figure.",
     "globe", (30.7, 36.9)),
    (7, "EUROPE", "NATO", "POLAND: RUSSIA VIOLATED AIRSPACE",
     "Warsaw says 2 missiles and a jet drone fell on Polish soil. NATO "
     "jets scrambled.",
     "jet", (19.0, 52.0)),
    (8, "GLOBAL", "MARKETS", "STOCKS FALL A FIFTH DAY ON AI DOUBTS",
     "The S&P 500 lost 2.0% and the Dow 1,101 points. Japan's Nikkei fell "
     "4.8%; South Korea halted sell orders.",
     "chart_down", (126.9, 37.5)),
    (9, "ASIA", "DEFENCE", "INDIA OPENS RANGES TO JAPANESE DRILLS",
     "At the Tokyo 2+2, India agreed Japanese forces may fire missiles on "
     "its ranges, a first.",
     "radar", (139.7, 35.7)),
    (10, "AFRICA", "HEALTH", "DR CONGO EBOLA: 11,376 CASES",
     "ECDC counts 11,376 Bundibugyo cases and 5,568 deaths. Kenya "
     "discharged its last patient Nov 11.",
     "virus", (23.0, -2.5)),
    (11, "S. AMERICA", "VENEZUELA", "US, VENEZUELA SIGN MILITARY DEAL",
     "Hegseth signed the pact in Caracas, the first US defence visit this "
     "century.",
     "flags", (-66.9, 10.5)),
    (12, "SCIENCE", "SPACE", "VOYAGER 1 REACHES ONE LIGHT-DAY",
     "NASA's probe is 26 billion km away, 49 years after launch. "
     "BepiColombo reached Mercury.",
     "voyager", None),
]

BRIEFS = [
    "UK-EU youth mobility deal for 100,000 a year set for Brussels summit",
    "Estonia to close road border with Russia from Dec 1 for six months",
    "UK unveils £260M aid for Ukraine with 1,000+ long-range drones",
    "Ukraine hits Kerch bridge a third time in four days; rail halted",
    "US Senate passes energy permitting overhaul 62 to 33",
    "US Senate blocks Iran war-powers limit 51 to 48",
    "Trump: no Iran decision until new year; Pentagon cost put at $48.3B",
    "Israel crosses Gaza \"Yellow Line\" in first incursion since truce",
    "Iraq orders Iran-backed militia out of Jurf al-Nasr",
    "IAEA: North Korea expanding uranium enrichment at Yongbyon",
    "Pakistan says 22 militants killed in northwest raids",
    "US loses measles elimination status after 26 years",
    "White House replaces cyber director after week of outages",
    "California AG subpoenas Nvidia over chips to China",
    "IMF warns global public debt nearing 100% of world GDP",
    "Brazil central bank sells $1B; real down 18% in a month",
    "Gold falls 4.2% as US 10-year yield holds above 5%",
    "GTA 6 launch tops $2.3B, biggest entertainment launch ever (est.)",
    "Trump posthumously pardons baseball star Pete Rose",
    "Fiji declares disaster, Tonga emergency over El Niño drought",
    "Haiti forces kill 34 suspected gang members in Martissant",
    "Sudan drone strike kills 10 at South Kordofan gold mine",
    "US consortium wins Kenya Mrima Hill minerals deal, $60B+ est.",
]

LEGEND = [
    (1, "SHENZHEN", REGION_COLORS["ASIA"]),
    (2, "KYIV", REGION_COLORS["EUROPE"]),
    (3, "NEW YORK", REGION_COLORS["N. AMERICA"]),
    (4, "THE HAGUE", REGION_COLORS["GLOBAL"]),
    (5, "RIYADH", REGION_COLORS["MIDDLE EAST"]),
    (6, "ANTALYA", REGION_COLORS["GLOBAL"]),
    (7, "POLAND", REGION_COLORS["EUROPE"]),
    (8, "SEOUL", REGION_COLORS["GLOBAL"]),
    (9, "TOKYO", REGION_COLORS["ASIA"]),
    (10, "DR CONGO", REGION_COLORS["AFRICA"]),
    (11, "CARACAS", REGION_COLORS["S. AMERICA"]),
    (12, "DEEP SPACE", REGION_COLORS["SCIENCE"]),
]


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
def draw_panel(cv, x, y, w, h, num, region, topic, headline, summary, pic):
    color = REGION_COLORS[region]
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK)
    cv.fill_rect(x, y, w, 4, color)
    # number badge + region label
    cv.fill_rect(x + 6, y + 7, 18, 13, color)
    s = str(num)
    cv.text(x + 6 + (18 - text_width(s, 1)) // 2, y + 10, s, WHITE, 1, bold=True)
    cv.text(x + 29, y + 10, region + " · " + topic, color, 1, bold=True)
    # headline (scale 2, bold, max 2 lines)
    max_h = (w - 12) // 12
    hy = y + 24
    hlines = wrap(headline, max_h)[:2]
    for i, ln in enumerate(hlines):
        cv.text(x + 6, hy + i * 16, ln, INK, 2, bold=True)
    sy = hy + len(hlines) * 16 + 2
    # summary (scale 1, max 3 lines)
    max_s = (w - 12) // 6
    draw_block(cv, x + 6, sy, summary, INK, 1, max_s, 9, max_lines=3)
    # illustration banner
    PICTOGRAMS[pic](cv, x + 6, y + h - 30, w - 12, 24)


def render():
    cv = Canvas(W, H, PAPER)
    M = 16
    CW = W - 2 * M  # 992

    # --- Masthead ---
    cv.fill_rect(0, 0, W, 86, NAVY)
    cv.fill_rect(0, 86, W, 4, RED)
    cv.text(20, 14, "THE WORLD ON ONE PAGE", WHITE, 5, bold=True)
    cv.text(20, 58, "FRIDAY 20 NOVEMBER 2026", GOLD, 2, bold=True)
    s = "35 STORIES"
    cv.text(W - 20 - text_width(s, 3), 14, s, WHITE, 3, bold=True)
    s = "6 CONTINENTS"
    cv.text(W - 20 - text_width(s, 2), 58, s, GOLD, 2, bold=True)

    # --- Day in numbers strip ---
    ny = 98
    cv.text(M, ny, "DAY IN NUMBERS", RED, 1, bold=True)
    rest = ("  9-6 ICJ VOTE · 110 MISSILES ON KYIV · $81.3B IPO · "
            "11,376 EBOLA CASES · 100% GLOBAL DEBT · $2.3B GTA 6")
    cv.text(M + text_width("DAY IN NUMBERS", 1), ny, rest, INK, 1)
    cv.hline(M, 112, CW, RULE)

    # --- Hero (story 1) ---
    hx, hy, hw, hh = M, 118, CW, 150
    cv.fill_rect(hx, hy, hw, hh, WHITE)
    cv.rect(hx, hy, hw, hh, NAVY)
    cv.rect(hx + 1, hy + 1, hw - 2, hh - 2, NAVY)
    cv.fill_rect(hx, hy, hw, 5, REGION_COLORS["ASIA"])
    cv.fill_rect(hx + 10, hy + 10, 24, 18, REGION_COLORS["ASIA"])
    cv.text(hx + 10 + (24 - text_width("1", 2)) // 2, hy + 12, "1", WHITE, 2,
            bold=True)
    cv.text(hx + 42, hy + 12, "ASIA · DIPLOMACY", REGION_COLORS["ASIA"], 2,
            bold=True)
    draw_block(cv, hx + 10, hy + 34,
               "TRUMP, XI AND PUTIN HOLD FIRST THREE-WAY SUMMIT", INK, 4, 26,
               30, bold=True, max_lines=2)
    draw_block(cv, hx + 10, hy + 97,
               "The leaders met for about 70 minutes in Shenzhen and signed "
               "a four-point declaration on nuclear risk, UN reform, energy "
               "and the ICC.",
               INK, 2, 52, 17, max_lines=3)
    pic_summit(cv, hx + 664, hy + 10, 318, 130)

    # --- Panel rows ---
    row_a = PANELS[0:3]
    row_b = PANELS[3:7]
    row_c = PANELS[7:11]
    # Row A: 3 across
    y = 274
    widths = [325, 325, 326]
    x = M
    for i, p in enumerate(row_a):
        draw_panel(cv, x, y, widths[i], 130, *p[:6])
        x += widths[i] + 8
    # Row B: 4 across
    y = 410
    x = M
    for p in row_b:
        draw_panel(cv, x, y, 242, 126, *p[:6])
        x += 242 + 8
    # Row C: 4 across
    y = 542
    x = M
    for p in row_c:
        draw_panel(cv, x, y, 242, 120, *p[:6])
        x += 242 + 8

    # --- Map strip ---
    pins = []
    for num, region, topic, headline, summary, pic, pin in PANELS:
        if pin is not None:
            dx, dy = 0, 0
            if num == 2:
                dy = -3  # Kyiv nudged up, away from Antalya
            if num == 6:
                dy = 3   # Antalya nudged down
            pins.append((num, pin[0], pin[1], REGION_COLORS[region], dx, dy))
    pins.insert(0, (1, 114.0, 22.5, REGION_COLORS["ASIA"], 0, 0))
    draw_map(cv, M, 668, CW, 104, pins)
    # legend line
    lx = M
    ly = 780
    for num, name, color in LEGEND:
        ns = str(num)
        cv.text(lx, ly, ns, color, 1, bold=True)
        lx += text_width(ns, 1) + 4
        cv.text(lx, ly, name, INK, 1)
        lx += text_width(name, 1)
        if num != 12:
            cv.text(lx, ly, " · ", GREY, 1)
            lx += text_width(" · ", 1)

    # --- Briefs ---
    by = 798
    cv.text(M, by, "ALSO ON FRIDAY 20 NOVEMBER", NAVY, 2, bold=True)
    cv.hline(M, by + 20, CW, RED)
    col_x = [M, M + 504]
    row_y0 = by + 28
    for i, brief in enumerate(BRIEFS):
        col = 0 if i < 12 else 1
        row = i if i < 12 else i - 12
        x = col_x[col]
        y = row_y0 + row * 13
        ns = str(13 + i) + "."
        cv.text(x, y, ns, NAVY, 1, bold=True)
        cv.text(x + 24, y, brief, INK, 1)

    # --- Footer ---
    cv.fill_rect(0, 988, W, 36, NAVY)
    s1 = ("SOURCES: BBC · REUTERS · AFP · AP · CNN · WSJ · UN NEWS · "
          "AL JAZEERA · THE GUARDIAN · ECDC · FRANCE 24")
    cv.text((W - text_width(s1, 1)) // 2, 994, s1, WHITE, 1)
    s2 = "ONE PAGE · ONE DAY · 35 STORIES VERIFIED AGAINST 20 NOVEMBER 2026 REPORTING"
    cv.text((W - text_width(s2, 1)) // 2, 1008, s2, GOLD, 1)

    return cv


def main():
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
        out = os.path.join(out_dir, "entry.png")
    cv = render()
    data = encode_png(cv)
    with open(out, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
