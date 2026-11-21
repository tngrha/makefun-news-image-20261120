#!/usr/bin/env python3
"""The World on One Page - Friday 20 November 2026.

A deterministic one-page world-news poster rendered with a hand-rolled
RGB framebuffer, a home-made 5x7 bitmap font, flat geometric shapes and
a hand-written PNG encoder. Python 3.13 standard library only.
Writes /output/entry.png (override with argv[1] or MAKEFUN_OUTPUT_DIR).
"""

import binascii
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 232)
INK = (20, 33, 61)
INK_SOFT = (52, 64, 92)
RED = (192, 57, 43)
TEAL = (29, 120, 116)
AMBER = (232, 163, 61)
SKY = (174, 205, 226)
OCEAN = (196, 220, 236)
LAND = (222, 205, 160)
LAND_EDGE = (168, 148, 106)
WHITE = (255, 255, 255)
GREY = (120, 128, 140)
GREEN = (46, 139, 87)
PURPLE = (110, 84, 160)
PINK = (214, 120, 140)

# ---------------------------------------------------------------- framebuffer
FB = bytearray(W * H * 3)


def fill_all(color):
    r, g, b = color
    row = bytes((r, g, b)) * W
    for y in range(H):
        FB[y * W * 3:(y + 1) * W * 3] = row


def px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        FB[i] = color[0]
        FB[i + 1] = color[1]
        FB[i + 2] = color[2]


def rect(x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        FB[i:i + len(row)] = row


def rect_outline(x, y, w, h, color, t=1):
    rect(x, y, w, t, color)
    rect(x, y + h - t, w, t, color)
    rect(x, y, t, h, color)
    rect(x + w - t, y, t, h, color)


def line(x0, y0, x1, y1, color, t=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for oy in range(t):
            for ox in range(t):
                px(x + ox, y + oy, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def circle(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                px(xx, yy, color)


def ring(cx, cy, r, color, t=1):
    for yy in range(cy - r - t, cy + r + t + 1):
        for xx in range(cx - r - t, cx + r + t + 1):
            d = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
            if (r - t) * (r - t) <= d <= (r + t) * (r + t):
                px(xx, yy, color)


def poly(points, color):
    """Scanline polygon fill. points: list of (x, y)."""
    ys = [p[1] for p in points]
    y_lo = max(0, int(min(ys)))
    y_hi = min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y_lo, y_hi + 1):
        nodes = []
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if y0 == y1:
                continue
            if (y0 <= y < y1) or (y1 <= y < y0):
                nodes.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        nodes.sort()
        for i in range(0, len(nodes) - 1, 2):
            xa = max(0, int(nodes[i]))
            xb = min(W - 1, int(nodes[i + 1]))
            if xb >= xa:
                rect(xa, y, xb - xa + 1, 1, color)


def tri(x0, y0, x1, y1, x2, y2, color):
    poly([(x0, y0), (x1, y1), (x2, y2)], color)


def star(cx, cy, r, color):
    """Five-point star, flat."""
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    poly(pts, color)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, 5 bits per row, MSB = leftmost pixel.
FONT = {
    " ": [0, 0, 0, 0, 0, 0, 0],
    "!": [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100],
    '"': [0b01010, 0b01010, 0b01010, 0, 0, 0, 0],
    "#": [0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010],
    "$": [0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
    "%": [0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011],
    "&": [0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101],
    "'": [0b00100, 0b00100, 0b01000, 0, 0, 0, 0],
    "(": [0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010],
    ")": [0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000],
    "+": [0, 0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0],
    ",": [0, 0, 0, 0, 0b01100, 0b00100, 0b01000],
    "-": [0, 0, 0, 0b01110, 0, 0, 0],
    ".": [0, 0, 0, 0, 0, 0b01100, 0b01100],
    "/": [0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000],
    "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "2": [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
    "3": [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    ":": [0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0],
    ";": [0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000],
    "=": [0, 0, 0b11111, 0, 0b11111, 0, 0],
    "?": [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0, 0b00100],
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "D": [0b11100, 0b10010, 0b10001, 0b10001, 0b10001, 0b10010, 0b11100],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111],
    "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "J": [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    "S": [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    "X": [0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b01010, 0b10001],
    "Y": [0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    "a": [0, 0, 0b01110, 0b00001, 0b01111, 0b10001, 0b01111],
    "b": [0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b11110],
    "c": [0, 0, 0b01110, 0b10000, 0b10000, 0b10001, 0b01110],
    "d": [0b00001, 0b00001, 0b01111, 0b10001, 0b10001, 0b10001, 0b01111],
    "e": [0, 0, 0b01110, 0b10001, 0b11111, 0b10000, 0b01110],
    "f": [0b00110, 0b01001, 0b01000, 0b11110, 0b01000, 0b01000, 0b01000],
    "g": [0, 0b01111, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110],
    "h": [0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001],
    "i": [0b00100, 0, 0b01100, 0b00100, 0b00100, 0b00100, 0b01110],
    "j": [0b00010, 0, 0b00110, 0b00010, 0b00010, 0b10010, 0b01100],
    "k": [0b10000, 0b10000, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010],
    "l": [0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "m": [0, 0, 0b11010, 0b10101, 0b10101, 0b10101, 0b10101],
    "n": [0, 0, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001],
    "o": [0, 0, 0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
    "p": [0, 0, 0b11110, 0b10001, 0b11110, 0b10000, 0b10000],
    "q": [0, 0, 0b01111, 0b10001, 0b01111, 0b00001, 0b00001],
    "r": [0, 0, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000],
    "s": [0, 0, 0b01111, 0b10000, 0b01110, 0b00001, 0b11110],
    "t": [0b01000, 0b01000, 0b11100, 0b01000, 0b01000, 0b01001, 0b00110],
    "u": [0, 0, 0b10001, 0b10001, 0b10001, 0b10011, 0b01101],
    "v": [0, 0, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "w": [0, 0, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010],
    "x": [0, 0, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001],
    "y": [0, 0, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110],
    "z": [0, 0, 0b11111, 0b00010, 0b00100, 0b01000, 0b11111],
}

CHAR_W = 6  # glyph 5px + 1px tracking, times scale
CHAR_H = 8  # glyph 7px + 1px leading, times scale


def text_w(s, scale=1):
    return len(s) * CHAR_W * scale - scale


def draw_text(x, y, s, color, scale=1):
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            glyph = FONT["?"]
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += CHAR_W * scale
    return cx


def draw_text_centered(cx, y, s, color, scale=1):
    draw_text(cx - text_w(s, scale) // 2, y, s, color, scale)


def wrap(s, max_chars):
    """Greedy word wrap into lines of at most max_chars characters."""
    lines = []
    cur = ""
    for word in s.split(" "):
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur = cur + " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(x, y, s, color, max_chars, scale=1, max_lines=3, line_gap=1):
    lines = wrap(s, max_chars)[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(x, y + i * (CHAR_H * scale + line_gap), ln, color, scale)
    return len(lines)


# ---------------------------------------------------------------- PNG encoder
def png_bytes():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw.extend(FB[y * stride:(y + 1) * stride])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- news data
# 12 lead panels: pin, region, lon, lat, headline, summary, illustration, tint
PANELS = [
    (1, "EUROPE", 19.0, 52.0, "RUSSIAN MISSILES FALL IN POLAND",
     "NATO jets scrambled after missiles and a drone fell on Polish soil.",
     "missiles", (250, 232, 220)),
    (2, "EUROPE", 30.5, 50.4, "110 MISSILES STRIKE KYIV",
     "Three Dnipro bridges hit; 9 killed, 28 hurt in the year's biggest attack.",
     "bridges", (226, 232, 246)),
    (3, "N. AMERICA", -74.0, 40.7, "AI ROUT: WALL ST IN CORRECTION",
     "S&P 500 -3.7%, Nasdaq -5.3%; Nvidia falls 14% as SEC probes its accounts.",
     "chart", (250, 224, 224)),
    (4, "N. AMERICA", -122.4, 37.8, "ANTHROPIC'S RECORD IPO FADES",
     "Shares slip 8.5% to $88.91 after record $81.3bn debut.",
     "ipo", (232, 240, 224)),
    (5, "MIDDLE EAST", 56.5, 26.5, "HORMUZ BLOCKADE TIGHTENS",
     "Iran stages 14 tankers to run US blockade; IEA warns of energy shock.",
     "tanker", (224, 238, 244)),
    (6, "EUROPE", 4.35, 50.85, "UK AND EU SIGN RESET DEALS",
     "Food trade, carbon markets, youth mobility agreed at Brussels summit.",
     "flags", (228, 236, 250)),
    (7, "S. AMERICA", -75.5, -11.0, "M6.7 QUAKE HITS PERU",
     "Deep tremor damages homes and a hospital; one person hurt.",
     "quake", (248, 236, 214)),
    (8, "EUROPE", 36.6, 45.3, "UKRAINE DROPS KERCH BRIDGE SPAN",
     "Drones collapse road section; Moscow vows revenge.",
     "span", (224, 234, 240)),
    (9, "MIDDLE EAST", 44.4, 33.0, "IRAQI FORCES ENTER JURF AL-NASR",
     "Army enters town for first time in 12 years as militia pulls back.",
     "town", (246, 238, 222)),
    (10, "ASIA", 139.7, 35.7, "NIKKEI SINKS 5%; JAPAN EYES N-SUBS",
     "Inflation at year high; Tokyo funds nuclear submarine study.",
     "japan", (250, 230, 230)),
    (11, "CLIMATE", 30.7, 36.9, "COP31 TALKS RUN PAST DEADLINE",
     "Draft omitting fossil fuels sparks protest at Antalya summit.",
     "climate", (226, 242, 228)),
    (12, "SPACE", 0.0, 0.0, "BEPICOLOMBO REACHES MERCURY",
     "ESA-JAXA probe arrives after an eight-year journey.",
     "mercury", (232, 228, 246)),
]

# 40 briefs: region, one-line story (wraps to at most two lines)
BRIEFS = [
    ("USA", "Trump demands a 'real deal' from Iran; no rush before Jan 1"),
    ("USA", "Senate blocks Iran war-powers resolution, 51-48"),
    ("USA", "Treasury sanctions four Iranian oil trustees"),
    ("MIDEAST", "Saudi defences down three Houthi missiles over Riyadh"),
    ("MIDEAST", "Israeli strikes kill Palestinians in Gaza"),
    ("EUROPE", "Estonia to shut Russia border from Dec 1 after sabotage"),
    ("EUROPE", "Denmark expels Russian attache over rapper plot"),
    ("EUROPE", "Denmark ratifies US security deal on Greenland"),
    ("EUROPE", "EU mobilises EUR 1bn more military aid for Ukraine"),
    ("EUROPE", "EU Commission disburses EUR 7.9bn to Ukraine"),
    ("EUROPE", "Putin offers Kostiantynivka truce; Kyiv says no"),
    ("EUROPE", "Boone, Brunnermeier nominated for ECB board"),
    ("EUROPE", "Sanchez and Feijoo clash in Spanish election debate"),
    ("USA", "Man convicted of starting deadly Palisades Fire"),
    ("USA", "Judge approves $7.25bn Bayer Roundup settlement"),
    ("USA", "Nikhil Gupta gets 235 months for Pannun murder plot"),
    ("USA", "Trump: contractors must warn White House before Congress"),
    ("USA", "Trump threatens tax on AI data centres built abroad"),
    ("USA", "Trump and Xi agree humans stay in military AI loop"),
    ("USA", "US loses measles elimination status"),
    ("USA", "California subpoenas Nvidia over China risks"),
    ("N.AMERICA", "Hegseth memo curbs defence cooperation with Canada"),
    ("N.AMERICA", "Canada budget passes 162-151; BC Tories take power"),
    ("ASIA", "Political violence in Bangladesh ahead of Hasina return"),
    ("ASIA", "Pakistan minister in Delhi, first since 2025 conflict"),
    ("ASIA", "TSMC, Samsung pause advanced chip sales to China"),
    ("ASIA", "China bars Bloomberg reporter from trilateral summit"),
    ("AFRICA", "Funeral mourners' boat capsizes in Nigeria's Bayelsa"),
    ("AFRICA", "Migrant boat capsizes off Senegal; dozens missing"),
    ("AFRICA", "Phumzile Mlambo-Ngcuka, SA first woman deputy PM, dies at 71"),
    ("AFRICA", "Egypt-IMF final review: $2.3bn rides on board vote"),
    ("AFRICA", "Troops mass on Ethiopia-Eritrea border"),
    ("LATAM", "Argentina Senate backs disability framework 71-0"),
    ("LATAM", "Brazil ends 6x1 week; 42-hour week from Dec 16"),
    ("TECH", "Google launches Gemini 4 Neon, million-token context"),
    ("CRYPTO", "Bitcoin slides to about $61,700, lowest since July"),
    ("CRYPTO", "SEC charges eight over fake crypto platforms"),
    ("SPACE", "NASA: Artemis III stays in orbit; landing moves to IV"),
    ("SCIENCE", "One CRISPR dose kept monkey blood fats low for 3 years"),
    ("SPORT", "Alcaraz beats Cobolli to top ATP Finals group in Turin"),
]

REGION_COLORS = {
    "USA": (70, 90, 170),
    "N. AMERICA": (70, 90, 170),
    "N.AMERICA": (70, 90, 170),
    "S. AMERICA": (46, 139, 87),
    "LATAM": (46, 139, 87),
    "EUROPE": (29, 120, 116),
    "MIDDLE EAST": (200, 120, 40),
    "MIDEAST": (200, 120, 40),
    "ASIA": (190, 60, 90),
    "AFRICA": (160, 110, 30),
    "CLIMATE": (60, 150, 90),
    "SPACE": (110, 84, 160),
    "SCIENCE": (90, 130, 170),
    "TECH": (80, 80, 180),
    "CRYPTO": (200, 150, 30),
    "SPORT": (40, 160, 110),
}

DAY_NUMBERS = [
    ("S&P 500", "-3.7%"),
    ("NASDAQ", "-5.3%"),
    ("NIKKEI", "-5.1%"),
    ("BRENT OIL", "$89.87"),
    ("BITCOIN", "$61,700"),
    ("VIX FEAR", "35.9"),
]

# UTC timeline: hour of day, short label
TIMELINE = [
    (1.5, "Missiles fall in Poland"),
    (3.5, "110 missiles hit Kyiv"),
    (6.0, "Nikkei closes -5.1%"),
    (14.0, "EU-UK summit deals"),
    (16.0, "EU: EUR 1bn for Ukraine"),
    (21.0, "Wall St closes in correction"),
    (23.8, "M6.7 quake, Peru (19:09 local)"),
]

# ---------------------------------------------------------------- world map
# Coarse continent outlines in (lon, lat), drawn equirectangular.
CONTINENTS = [
    # North America
    [(-168, 66), (-150, 70), (-135, 69), (-125, 70), (-115, 68), (-105, 68),
     (-95, 69), (-88, 66), (-82, 62), (-80, 58), (-76, 56), (-70, 52),
     (-64, 50), (-56, 47), (-60, 46), (-66, 44), (-70, 42), (-72, 40),
     (-74, 39), (-75, 36), (-76, 34), (-79, 33), (-81, 31), (-81, 26),
     (-82, 28), (-84, 30), (-87, 30), (-89, 29), (-92, 29), (-95, 29),
     (-97, 26), (-97, 23), (-96, 20), (-94, 18), (-92, 15), (-90, 14),
     (-87, 13), (-84, 12), (-82, 9), (-79, 9), (-78, 8), (-80, 10),
     (-83, 15), (-86, 16), (-88, 17), (-90, 21), (-91, 19), (-94, 17),
     (-96, 16), (-99, 17), (-102, 18), (-104, 19), (-106, 21), (-108, 23),
     (-110, 24), (-112, 27), (-114, 29), (-116, 31), (-117, 33), (-120, 35),
     (-122, 37), (-124, 40), (-124, 45), (-123, 48), (-126, 50), (-130, 54),
     (-134, 57), (-138, 59), (-142, 60), (-147, 61), (-152, 60), (-156, 58),
     (-160, 56), (-164, 59), (-166, 61), (-168, 66)],
    # Greenland
    [(-46, 60), (-42, 61), (-38, 64), (-32, 68), (-24, 70), (-20, 73),
     (-20, 77), (-26, 80), (-36, 82), (-48, 81), (-56, 78), (-57, 74),
     (-55, 70), (-53, 66), (-52, 62), (-50, 60), (-46, 60)],
    # South America
    [(-79, 9), (-76, 10), (-72, 12), (-68, 11), (-64, 10), (-60, 8),
     (-56, 6), (-52, 5), (-50, 1), (-46, -1), (-42, -3), (-38, -5),
     (-35, -8), (-36, -11), (-39, -14), (-39, -18), (-40, -21), (-42, -23),
     (-46, -24), (-48, -27), (-50, -30), (-52, -33), (-54, -35), (-57, -38),
     (-59, -39), (-62, -41), (-64, -43), (-65, -46), (-66, -48), (-67, -50),
     (-68, -52), (-68, -55), (-70, -54), (-72, -52), (-73, -49), (-73, -46),
     (-73, -43), (-72, -40), (-72, -37), (-71, -33), (-71, -30), (-70, -27),
     (-70, -23), (-70, -19), (-71, -17), (-74, -16), (-76, -14), (-77, -11),
     (-78, -8), (-79, -6), (-81, -4), (-81, -1), (-80, 1), (-78, 3),
     (-77, 5), (-78, 7), (-79, 9)],
    # Africa
    [(-17, 15), (-16, 18), (-16, 22), (-15, 25), (-13, 28), (-10, 30),
     (-8, 32), (-6, 34), (-3, 35), (0, 36), (3, 37), (7, 37), (10, 37),
     (11, 35), (13, 33), (15, 32), (19, 30), (22, 33), (25, 32), (28, 31),
     (30, 31), (32, 31), (33, 29), (34, 27), (35, 24), (36, 22), (37, 20),
     (38, 18), (39, 16), (40, 15), (42, 12), (43, 12), (46, 11), (48, 11),
     (51, 12), (51, 10), (50, 8), (48, 5), (45, 2), (42, -1), (41, -4),
     (40, -8), (40, -11), (39, -14), (38, -17), (36, -20), (35, -23),
     (34, -26), (32, -28), (30, -30), (28, -32), (26, -34), (23, -34),
     (20, -35), (18, -33), (17, -31), (16, -28), (15, -25), (14, -22),
     (13, -19), (12, -16), (13, -13), (13, -10), (12, -7), (12, -4),
     (10, -1), (9, 2), (9, 4), (6, 4), (4, 5), (2, 6), (-1, 5), (-4, 5),
     (-7, 4), (-9, 5), (-11, 6), (-13, 8), (-15, 10), (-17, 12), (-17, 15)],
    # Madagascar
    [(44, -16), (46, -15), (49, -14), (50, -16), (49, -19), (48, -21),
     (47, -23), (46, -25), (45, -25), (44, -23), (44, -20), (43, -17),
     (44, -16)],
    # Eurasia (Europe + Asia, one coarse outline)
    [(-9, 43), (-9, 45), (-5, 48), (-2, 50), (0, 51), (2, 51), (4, 52),
     (6, 53), (8, 54), (8, 56), (7, 57), (9, 57), (11, 58), (13, 56),
     (16, 55), (19, 55), (21, 56), (22, 58), (24, 59), (26, 59), (28, 59),
     (29, 60), (28, 62), (26, 61), (24, 62), (23, 64), (23, 66), (25, 68),
     (28, 70), (32, 70), (36, 68), (40, 67), (45, 68), (50, 69), (55, 69),
     (60, 70), (66, 70), (72, 72), (78, 72), (84, 73), (90, 75), (96, 76),
     (102, 77), (108, 75), (114, 73), (120, 73), (126, 72), (132, 72),
     (138, 72), (144, 72), (150, 71), (156, 70), (162, 70), (168, 68),
     (174, 66), (178, 65), (178, 63), (172, 61), (168, 60), (163, 60),
     (160, 56), (158, 53), (156, 51), (153, 49), (149, 46), (145, 45),
     (142, 44), (141, 41), (140, 38), (138, 36), (136, 35), (133, 34),
     (130, 33), (127, 34), (124, 33), (122, 31), (121, 28), (119, 26),
     (117, 24), (114, 22), (111, 21), (109, 19), (108, 16), (109, 13),
     (107, 11), (106, 9), (104, 8), (103, 5), (101, 3), (100, 5),
     (99, 8), (98, 10), (97, 13), (96, 16), (94, 17), (92, 16), (91, 18),
     (91, 22), (89, 22), (87, 21), (85, 19), (83, 17), (81, 15),
     (80, 13), (79, 10), (77, 8), (76, 10), (74, 13), (72, 18),
     (72, 21), (70, 22), (68, 23), (66, 25), (63, 25), (60, 25),
     (57, 26), (56, 27), (54, 26), (52, 26), (50, 28), (49, 29),
     (48, 30), (48, 28), (50, 26), (52, 25), (54, 24), (55, 24),
     (57, 25), (58, 23), (59, 22), (58, 20), (56, 18), (54, 17),
     (52, 15), (50, 14), (48, 13), (46, 13), (44, 12), (43, 13),
     (42, 15), (41, 17), (40, 19), (39, 21), (38, 23), (37, 25),
     (36, 27), (35, 29), (34, 29), (35, 31), (36, 33), (36, 35),
     (35, 36), (33, 36), (31, 36), (29, 37), (27, 37), (26, 38),
     (24, 38), (23, 37), (22, 37), (21, 38), (20, 40), (19, 41),
     (18, 40), (17, 40), (16, 39), (16, 38), (17, 40), (18, 41),
     (16, 42), (14, 43), (13, 45), (12, 45), (11, 44), (10, 44),
     (8, 44), (6, 43), (4, 43), (3, 42), (2, 41), (0, 40), (-1, 38),
     (-2, 37), (-4, 37), (-6, 36), (-8, 37), (-9, 38), (-9, 40),
     (-9, 43)],
    # Britain
    [(-5, 50), (-3, 51), (-1, 52), (0, 53), (-1, 55), (-2, 57), (-3, 58),
     (-5, 58), (-6, 56), (-5, 54), (-4, 52), (-5, 50)],
    # Japan
    [(130, 31), (132, 33), (134, 34), (136, 34), (138, 35), (140, 36),
     (141, 39), (141, 42), (142, 44), (143, 44), (142, 42), (140, 40),
     (139, 38), (137, 36), (135, 35), (132, 34), (130, 32), (130, 31)],
    # Indonesia islands (coarse)
    [(95, 5), (99, 2), (102, -1), (105, -4), (106, -6), (103, -5),
     (100, -2), (97, 1), (95, 4), (95, 5)],
    [(109, 1), (112, 3), (115, 4), (118, 2), (119, 0), (117, -2),
     (114, -3), (111, -2), (109, 0), (109, 1)],
    [(105, -6), (109, -6), (113, -7), (114, -8), (110, -8), (106, -7),
     (105, -6)],
    [(119, 0), (121, 1), (123, 0), (122, -2), (120, -3), (119, -2),
     (119, 0)],
    [(131, -1), (136, -2), (141, -3), (146, -5), (147, -7), (143, -6),
     (138, -5), (133, -4), (131, -2), (131, -1)],
    # Australia
    [(113, -22), (113, -25), (114, -28), (115, -32), (115, -34), (117, -35),
     (120, -34), (124, -33), (128, -32), (131, -32), (133, -33), (135, -35),
     (136, -35), (138, -35), (139, -37), (141, -38), (144, -38), (146, -39),
     (149, -38), (150, -37), (151, -34), (153, -31), (153, -28), (152, -25),
     (150, -23), (149, -20), (147, -19), (146, -18), (145, -16), (144, -14),
     (142, -11), (142, -13), (141, -15), (141, -17), (140, -18), (138, -16),
     (136, -15), (135, -13), (134, -12), (132, -11), (130, -12), (128, -14),
     (126, -14), (124, -16), (122, -17), (120, -19), (118, -20), (116, -21),
     (114, -22), (113, -22)],
    # New Zealand
    [(173, -35), (175, -37), (178, -38), (177, -39), (175, -40), (174, -39),
     (173, -36), (173, -35)],
    [(167, -45), (169, -44), (171, -43), (173, -42), (172, -41), (169, -43),
     (167, -45)],
    # Iceland
    [(-22, 64), (-18, 64), (-15, 64), (-14, 65), (-17, 66), (-21, 66),
     (-22, 65), (-22, 64)],
]


# ---------------------------------------------------------------- illustrations
def ellipse_outline(cx, cy, rx, ry, color):
    import math
    steps = 64
    prev = None
    for i in range(steps + 1):
        a = 2 * math.pi * i / steps
        p = (cx + rx * math.cos(a), cy + ry * math.sin(a))
        if prev is not None:
            line(int(prev[0]), int(prev[1]), int(p[0]), int(p[1]), color)
        prev = p


def illus_missiles(x, y, w, h):
    rect(x, y + h - 10, w, 10, (150, 140, 110))
    for i, (mx, my) in enumerate([(x + 60, y + 8), (x + 130, y + 14)]):
        line(mx - 34, my - 2, mx, my + 8, GREY)
        line(mx - 30, my + 4, mx, my + 10, GREY)
        poly([(mx, my + 6), (mx + 16, my + 10), (mx + 2, my + 14)], INK)
        tri(mx + 2, my + 6, mx + 8, my + 2, mx + 9, my + 8, RED)
    tri(x + 180, y + 10, x + 196, y + 16, x + 178, y + 18, INK_SOFT)
    star(x + 60, y + h - 14, 6, AMBER)
    star(x + 132, y + h - 12, 5, AMBER)


def illus_bridges(x, y, w, h):
    rect(x, y + h - 16, w, 16, SKY)
    rect(x, y + h - 30, w, 4, INK_SOFT)
    for bx in (x + 20, x + 95, x + 170):
        rect(bx, y + h - 30, 4, 16, INK_SOFT)
        rect(bx + 44, y + h - 30, 4, 16, INK_SOFT)
        line(bx, y + h - 30, bx + 24, y + h - 40, INK_SOFT)
        line(bx + 48, y + h - 30, bx + 24, y + h - 40, INK_SOFT)
    star(x + 118, y + h - 34, 11, RED)
    star(x + 118, y + h - 34, 6, AMBER)
    for sx in (x + 30, x + 60, x + 180, x + 205):
        rect(sx, y + 8, 12, h - 38, (170, 180, 200))


def illus_chart(x, y, w, h):
    line(x + 14, y + 4, x + 14, y + h - 8, INK)
    line(x + 14, y + h - 8, x + w - 8, y + h - 8, INK)
    pts = [(x + 18, y + 8), (x + 55, y + 14), (x + 80, y + 10),
           (x + 115, y + 24), (x + 145, y + 20), (x + 180, y + 36),
           (x + 215, y + 44)]
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)
    for p in pts:
        circle(p[0], p[1], 2, RED)
    tri(x + 215, y + 52, x + 206, y + 40, x + 224, y + 40, RED)


def illus_ipo(x, y, w, h):
    rect(x + 20, y + h - 14, 70, 6, INK_SOFT)
    for cx in (x + 28, x + 48, x + 68):
        rect(cx, y + 18, 6, h - 32, INK_SOFT)
    tri(x + 18, y + 18, x + 55, y + 6, x + 92, y + 18, INK_SOFT)
    circle(x + 150, y + 18, 10, AMBER)
    rect(x + 140, y + 18, 20, 8, AMBER)
    circle(x + 150, y + 29, 3, INK)
    rect(x + 118, y + 34, 96, 14, INK)
    draw_text(x + 124, y + 37, "$88.91 -8.5%", WHITE, 1)
    line(x + 196, y + 10, x + 212, y + 26, RED, 2)
    tri(x + 214, y + 30, x + 204, y + 24, x + 216, y + 20, RED)


def illus_tanker(x, y, w, h):
    rect(x, y + h - 14, w, 14, SKY)
    poly([(x + 30, y + h - 22), (x + 190, y + h - 22), (x + 178, y + h - 10),
          (x + 44, y + h - 10)], (90, 60, 60))
    for i, c in enumerate([RED, TEAL, AMBER, GREEN, PURPLE]):
        rect(x + 48 + i * 26, y + h - 34, 22, 12, c)
    rect(x + 172, y + h - 40, 14, 18, WHITE)
    rect(x + 174, y + h - 38, 10, 4, INK)
    for dx in range(x + 8, x + w - 8, 16):
        rect(dx, y + 8, 9, 3, RED)
    draw_text(x + 8, y + 14, "BLOCKADE", RED, 1)


def illus_flags(x, y, w, h):
    rect(x + 16, y + 8, 84, 42, (40, 60, 160))
    import math
    for i in range(12):
        a = 2 * math.pi * i / 12
        star(int(x + 58 + 26 * math.cos(a)), int(y + 29 + 14 * math.sin(a)), 3, AMBER)
    rect(x + 130, y + 8, 84, 42, (40, 60, 160))
    line(x + 130, y + 8, x + 214, y + 50, WHITE, 4)
    line(x + 214, y + 8, x + 130, y + 50, WHITE, 4)
    rect(x + 166, y + 8, 12, 42, WHITE)
    rect(x + 130, y + 24, 84, 10, WHITE)
    rect(x + 169, y + 8, 6, 42, RED)
    rect(x + 130, y + 27, 84, 5, RED)
    line(x + 104, y + 29, x + 126, y + 29, TEAL, 2)
    tri(x + 128, y + 29, x + 120, y + 24, x + 120, y + 34, TEAL)


def illus_quake(x, y, w, h):
    rect(x, y + h - 14, w, 14, (160, 130, 90))
    crack = [(x + 10, y + h - 8), (x + 50, y + h - 13), (x + 85, y + h - 7),
             (x + 120, y + h - 13), (x + 160, y + h - 8), (x + 205, y + h - 12)]
    for i in range(len(crack) - 1):
        line(crack[i][0], crack[i][1], crack[i + 1][0], crack[i + 1][1], INK, 2)
    poly([(x + 150, y + h - 14), (x + 152, y + h - 30), (x + 176, y + h - 28),
          (x + 178, y + h - 14)], (200, 170, 130))
    poly([(x + 148, y + h - 30), (x + 164, y + h - 40), (x + 180, y + h - 28)],
         (140, 90, 60))
    seis = [(x + 10, y + 16), (x + 40, y + 16), (x + 55, y + 4), (x + 70, y + 28),
            (x + 85, y + 8), (x + 100, y + 16), (x + 140, y + 16)]
    for i in range(len(seis) - 1):
        line(seis[i][0], seis[i][1], seis[i + 1][0], seis[i + 1][1], RED, 2)


def illus_span(x, y, w, h):
    rect(x, y + h - 14, w, 14, SKY)
    rect(x + 16, y + h - 26, 70, 5, INK_SOFT)
    rect(x + 150, y + h - 26, 66, 5, INK_SOFT)
    poly([(x + 86, y + h - 26), (x + 150, y + h - 26), (x + 142, y + h - 12),
          (x + 94, y + h - 12)], RED)
    rect(x + 30, y + h - 26, 6, 14, INK_SOFT)
    rect(x + 196, y + h - 26, 6, 14, INK_SOFT)
    line(x + 30, y + h - 40, x + 86, y + h - 26, INK_SOFT)
    line(x + 202, y + h - 40, x + 150, y + h - 26, INK_SOFT)
    rect(x + 27, y + h - 44, 6, 20, INK_SOFT)
    rect(x + 199, y + h - 44, 6, 20, INK_SOFT)
    star(x + 118, y + h - 34, 7, AMBER)


def illus_town(x, y, w, h):
    rect(x, y + h - 8, w, 8, (170, 150, 110))
    for i, hx in enumerate((x + 14, x + 58, x + 102, x + 146)):
        rect(hx, y + h - 26, 34, 18, (215, 195, 160))
        tri(hx - 2, y + h - 26, hx + 17, y + h - 38, hx + 36, y + h - 26,
            (150, 100, 70))
        rect(hx + 6, y + h - 20, 7, 7, AMBER)
        rect(hx + 21, y + h - 20, 7, 7, AMBER)
    line(x + 196, y + 6, x + 196, y + h - 8, INK, 2)
    poly([(x + 196, y + 6), (x + 218, y + 10), (x + 196, y + 16)], GREEN)
    circle(x + 196, y + 5, 2, RED)


def illus_japan(x, y, w, h):
    circle(x + 46, y + 22, 16, (210, 60, 60))
    rect(x, y + h - 16, w, 16, SKY)
    rect(x + 96, y + h - 24, 110, 10, INK_SOFT)
    circle(x + 96, y + h - 19, 5, INK_SOFT)
    circle(x + 206, y + h - 19, 5, INK_SOFT)
    rect(x + 140, y + h - 32, 26, 8, INK_SOFT)
    line(x + 153, y + h - 32, x + 153, y + h - 40, INK_SOFT, 2)
    pts = [(x + 104, y + 8), (x + 140, y + 14), (x + 170, y + 12),
           (x + 205, y + 22)]
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)


def illus_climate(x, y, w, h):
    rect(x + 30, y + 6, 10, 36, WHITE)
    rect_outline(x + 30, y + 6, 10, 36, INK)
    rect(x + 32, y + 16, 6, 24, RED)
    circle(x + 35, y + 46, 8, RED)
    circle(x + 35, y + 46, 8, RED)
    ring(x + 35, y + 46, 8, INK)
    poly([(x + 110, y + 44), (x + 130, y + 12), (x + 170, y + 6),
          (x + 168, y + 34), (x + 140, y + 46)], GREEN)
    line(x + 112, y + 42, x + 166, y + 10, (30, 100, 50), 2)
    circle(x + 196, y + 16, 11, AMBER)
    for dx, dy in [(0, -16), (12, -11), (16, 0), (12, 11), (0, 16),
                   (-12, 11), (-16, 0), (-12, -11)]:
        line(x + 196 + dx, y + 16 + dy, x + 196 + dx * 3 // 2,
             y + 16 + dy * 3 // 2, AMBER, 2)


def illus_mercury(x, y, w, h):
    rect(x, y, w, h, (28, 32, 56))
    for sx, sy in [(20, 10), (60, 6), (110, 14), (170, 8), (205, 18),
                   (40, 40), (200, 44), (90, 48)]:
        px(x + sx, y + sy, WHITE)
        px(x + sx + 1, y + sy, WHITE)
    circle(x + 150, y + 30, 20, (170, 165, 155))
    circle(x + 142, y + 24, 4, (140, 135, 125))
    circle(x + 158, y + 34, 3, (140, 135, 125))
    circle(x + 150, y + 40, 3, (140, 135, 125))
    ellipse_outline(x + 150, y + 30, 34, 12, AMBER)
    rect(x + 66, y + 22, 18, 12, (200, 200, 210))
    rect(x + 40, y + 24, 22, 8, (90, 120, 200))
    rect(x + 88, y + 24, 22, 8, (90, 120, 200))
    line(x + 75, y + 22, x + 75, y + 12, (200, 200, 210), 2)
    circle(x + 75, y + 10, 4, (200, 200, 210))


ILLUSTRATIONS = {
    "missiles": illus_missiles,
    "bridges": illus_bridges,
    "chart": illus_chart,
    "ipo": illus_ipo,
    "tanker": illus_tanker,
    "flags": illus_flags,
    "quake": illus_quake,
    "span": illus_span,
    "town": illus_town,
    "japan": illus_japan,
    "climate": illus_climate,
    "mercury": illus_mercury,
}

# ---------------------------------------------------------------- layout
MX = 16            # side margin
CW = W - 2 * MX    # content width = 992
MAP_Y = 132
MAP_H = 190
PANEL_Y = 330
PANEL_H = 142
PANEL_GAP = 6
COL_W = 242
COL_GAP = 8


def map_xy(lon, lat):
    x = MX + (lon + 180.0) / 360.0 * CW
    y = MAP_Y + (75.0 - lat) / 135.0 * MAP_H
    return int(x), int(y)


def draw_header():
    rect(MX, 8, CW, 2, INK)
    draw_text_centered(W // 2, 14, "THE WORLD ON ONE PAGE", INK, 4)
    draw_text_centered(W // 2, 48, "FRIDAY 20 NOVEMBER 2026", RED, 3)
    draw_text_centered(W // 2, 74,
                       "52 VERIFIED STORIES - 12 LEADS + 40 BRIEFS - DATE CHECKED: FRIDAY",
                       INK_SOFT, 1)
    rect(MX, 84, CW, 1, INK_SOFT)


def draw_numbers():
    y = 90
    draw_text(MX, y + 2, "DAY IN NUMBERS", INK, 1)
    bx = MX + 110
    bw = 146
    for i, (name, val) in enumerate(DAY_NUMBERS):
        x = bx + i * (bw + 2)
        rect_outline(x, y, bw, 34, GREY)
        draw_text(x + 6, y + 3, name, GREY, 1)
        col = RED if val.startswith("-") else INK
        draw_text(x + 6, y + 14, val, col, 2)


def draw_map():
    rect(MX, MAP_Y, CW, MAP_H, OCEAN)
    # graticule every 30 degrees
    for lon in range(-150, 181, 30):
        x, _ = map_xy(lon, 0)
        line(x, MAP_Y, x, MAP_Y + MAP_H, (178, 205, 226))
    for lat in range(-60, 76, 30):
        _, y = map_xy(0, lat)
        line(MX, y, MX + CW, y, (178, 205, 226))
    for cont in CONTINENTS:
        pts = [map_xy(lon, lat) for lon, lat in cont]
        poly(pts, LAND)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            line(x0, y0, x1, y1, LAND_EDGE)
    rect_outline(MX, MAP_Y, CW, MAP_H, INK_SOFT)
    draw_text(MX + 6, MAP_Y + 5, "WHERE IT HAPPENED - PINS MATCH THE PANELS BELOW",
              INK, 1)
    # Mercury inset for pin 12
    ix, iy, ir = MX + CW - 46, MAP_Y + MAP_H - 40, 30
    circle(ix, iy, ir, (28, 32, 56))
    ring(ix, iy, ir, INK_SOFT)
    circle(ix + 6, iy + 2, 11, (170, 165, 155))
    circle(ix + 3, iy - 2, 3, (140, 135, 125))
    ellipse_outline(ix + 6, iy + 2, 18, 7, AMBER)
    # pins
    for (num, _reg, lon, lat, _h, _s, _il, _t) in PANELS:
        if num == 12:
            px_, py_ = ix - 16, iy - 14
        else:
            px_, py_ = map_xy(lon, lat)
        circle(px_, py_, 8, WHITE)
        circle(px_, py_, 7, RED)
        label = str(num)
        draw_text(px_ - text_w(label, 1) // 2, py_ - 3, label, WHITE, 1)


def draw_panel(idx, x, y):
    num, region, _lon, _lat, headline, sub, illus, tint = PANELS[idx]
    rect(x, y, COL_W, PANEL_H, WHITE)
    rect_outline(x, y, COL_W, PANEL_H, INK_SOFT)
    # badge strip
    rect(x, y, COL_W, 14, tint)
    circle(x + 9, y + 7, 6, RED)
    draw_text(x + 9 - text_w(str(num), 1) // 2, y + 4, str(num), WHITE, 1)
    rcol = REGION_COLORS.get(region, INK)
    draw_text(x + 20, y + 4, region, rcol, 1)
    draw_text(x + COL_W - 6 - text_w("LEAD", 1), y + 4, "LEAD", GREY, 1)
    # illustration
    rect(x + 4, y + 16, COL_W - 8, 54, tint)
    ILLUSTRATIONS[illus](x + 4, y + 16, COL_W - 8, 54)
    # headline + summary
    draw_wrapped(x + 6, y + 74, headline, INK, 19, scale=2, max_lines=2,
                 line_gap=2)
    draw_wrapped(x + 6, y + 112, sub, INK_SOFT, 38, scale=1, max_lines=2,
                 line_gap=1)


def draw_panels():
    for i in range(12):
        col = i % 4
        row = i // 4
        x = MX + col * (COL_W + COL_GAP)
        y = PANEL_Y + row * (PANEL_H + PANEL_GAP)
        draw_panel(i, x, y)


def draw_briefs():
    y0 = 776
    draw_text(MX, y0, "MORE OF THE DAY - 40 BRIEFS", INK, 1)
    rect(MX, y0 + 9, CW, 1, INK_SOFT)
    top = y0 + 13
    for c in range(4):
        x = MX + c * (COL_W + COL_GAP)
        for r in range(10):
            region, text = BRIEFS[c * 10 + r]
            y = top + r * 16
            full = region + " " + text
            lines = wrap(full, 39)[:2]
            rcol = REGION_COLORS.get(region, INK)
            # first line: region tag in colour, rest in ink
            first = lines[0]
            tag = region
            draw_text(x, y, tag, rcol, 1)
            rest = first[len(tag) + 1:] if first.startswith(tag + " ") else first
            if rest:
                draw_text(x + text_w(tag + " ", 1), y, rest, INK, 1)
            if len(lines) > 1:
                draw_text(x, y + 8, lines[1], INK, 1)
        if c < 3:
            line(x + COL_W + 3, top, x + COL_W + 3, top + 158, (210, 205, 190))


def draw_timeline():
    y_label = 954
    draw_text(MX, y_label, "THE DAY IN UTC", INK, 1)
    axis_y = 984
    x0, x1 = 40, 984
    line(x0, axis_y, x1, axis_y, INK, 2)
    for hr in range(0, 25, 3):
        x = x0 + int(hr / 24.0 * (x1 - x0))
        line(x, axis_y - 3, x, axis_y + 3, INK)
        draw_text_centered(x, axis_y + 6, "%02d" % hr, GREY, 1)
    for i, (hr, label) in enumerate(TIMELINE):
        x = x0 + int(hr / 24.0 * (x1 - x0))
        circle(x, axis_y, 3, RED)
        above = (i % 2 == 0)
        ly = axis_y - 20 if above else axis_y + 16
        hw = text_w(label, 1) // 2
        lx = max(MX + hw, min(W - MX - hw, x))
        if above:
            line(x, axis_y - 4, x, axis_y - 10, RED)
            draw_text_centered(lx, ly, label, INK, 1)
        else:
            line(x, axis_y + 4, x, axis_y + 10, RED)
            draw_text_centered(lx, ly, label, INK, 1)


def draw_footer():
    draw_text_centered(
        W // 2, 1012,
        "Compiled from wire and press reports of Friday 20 November 2026 - drawn by program, no photographs",
        GREY, 1)


def render():
    fill_all(PAPER)
    draw_header()
    draw_numbers()
    draw_map()
    draw_panels()
    draw_briefs()
    draw_timeline()
    draw_footer()
    return png_bytes()


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if out_dir:
        path = os.path.join(out_dir, "entry.png")
    elif len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "/output/entry.png"
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    data = render()
    with open(path, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
