#!/usr/bin/env python3
"""the-passport-page-of-a-countr-2-20261121-0318 — invented passport spread.

Draws a 1024x1024 image of an open passport spread from a country that
does not exist: the Republic of Kaldera, a volcanic island nation.
Left page: data page with portrait, consistent issue/expiry dates and a
machine-readable zone with correct ICAO check digits. Right page: visa
and a chain of arrival/departure stamps from neighbouring countries whose
dates agree with each other and with the passport's issue date.
The telling detail: an ash-season travel ban and a volcano levy stamp.

Standard library only. Fully deterministic: no clock, no randomness,
no dependence on dict/hash ordering. Two runs produce identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# --------------------------------------------------------------------------
# Embedded 5x7 bitmap font (A-Z, 0-9, punctuation). Each glyph is 7 rows
# of 5 columns; 'X' = ink, '.' = empty.
# --------------------------------------------------------------------------
FONT_SRC = {
    "A": (".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"),
    "B": ("XXXX.", "X...X", "X...X", "XXXX.", "X...X", "X...X", "XXXX."),
    "C": (".XXXX", "X....", "X....", "X....", "X....", "X....", ".XXXX"),
    "D": ("XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."),
    "E": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"),
    "F": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."),
    "G": (".XXXX", "X....", "X....", "X..XX", "X...X", "X...X", ".XXXX"),
    "H": ("X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"),
    "I": ("XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "XXXXX"),
    "J": ("..XXX", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."),
    "K": ("X...X", "X..X.", "X.X..", "XX...", "X.X..", "X..X.", "X...X"),
    "L": ("X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"),
    "M": ("X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"),
    "N": ("X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"),
    "O": (".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "P": ("XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."),
    "Q": (".XXX.", "X...X", "X...X", "X...X", "X.X.X", "X..X.", ".XX.X"),
    "R": ("XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"),
    "S": (".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."),
    "T": ("XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."),
    "U": ("X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "V": ("X...X", "X...X", "X...X", "X...X", "X...X", ".X.X.", "..X.."),
    "W": ("X...X", "X...X", "X...X", "X.X.X", "X.X.X", "XX.XX", "X...X"),
    "X": ("X...X", "X...X", ".X.X.", "..X..", ".X.X.", "X...X", "X...X"),
    "Y": ("X...X", "X...X", ".X.X.", "..X..", "..X..", "..X..", "..X.."),
    "Z": ("XXXXX", "....X", "...X.", "..X..", ".X...", "X....", "XXXXX"),
    "0": (".XXX.", "X...X", "X..XX", "X.X.X", "XX..X", "X...X", ".XXX."),
    "1": ("..X..", ".XX..", "..X..", "..X..", "..X..", "..X..", "XXXXX"),
    "2": (".XXX.", "X...X", "....X", "...X.", "..X..", ".X...", "XXXXX"),
    "3": ("XXXXX", "....X", "...X.", "..XX.", "....X", "X...X", ".XXX."),
    "4": ("...X.", "..XX.", ".X.X.", "X..X.", "XXXXX", "...X.", "...X."),
    "5": ("XXXXX", "X....", "XXXX.", "....X", "....X", "X...X", ".XXX."),
    "6": (".XXX.", "X....", "X....", "XXXX.", "X...X", "X...X", ".XXX."),
    "7": ("XXXXX", "....X", "...X.", "..X..", "..X..", "..X..", "..X.."),
    "8": (".XXX.", "X...X", "X...X", ".XXX.", "X...X", "X...X", ".XXX."),
    "9": (".XXX.", "X...X", "X...X", ".XXXX", "....X", "....X", ".XXX."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", "..X..", "..X.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..X..", ".X..."),
    ":": (".....", ".....", "..X..", ".....", ".....", "..X..", "....."),
    "-": (".....", ".....", ".....", ".XXX.", ".....", ".....", "....."),
    "\u2013": (".....", ".....", ".....", "XXXXX", ".....", ".....", "....."),
    "'": ("..X..", "..X..", ".....", ".....", ".....", ".....", "....."),
    "\u00b7": (".....", ".....", ".....", "..X..", ".....", ".....", "....."),
    "<": ("...X.", "..X..", ".X...", "X....", ".X...", "..X..", "...X."),
    ">": (".X...", "..X..", "...X.", "....X", "...X.", "..X..", ".X..."),
    "/": ("....X", "....X", "...X.", "..X..", ".X...", "X....", "X...."),
    "!": ("..X..", "..X..", "..X..", "..X..", "..X..", ".....", "..X.."),
    "(": ("...X.", "..X..", ".X...", ".X...", ".X...", "..X..", "...X."),
    ")": (".X...", "..X..", "...X.", "...X.", "...X.", "..X..", "...X."),
    "+": (".....", "..X..", "..X..", "XXXXX", "..X..", "..X..", "....."),
    "=": (".....", ".....", "XXXXX", ".....", "XXXXX", ".....", "....."),
    "&": (".XX..", "X..X.", "X..X.", ".XX..", "X.X.X", "X..X.", ".XX.X"),
}

# Pre-parse glyphs into lists of (dx, dy) ink pixels.
FONT = {}
for _ch, _rows in FONT_SRC.items():
    _pts = []
    for _y, _row in enumerate(_rows):
        for _x, _c in enumerate(_row):
            if _c == "X":
                _pts.append((_x, _y))
    FONT[_ch] = _pts

# --------------------------------------------------------------------------
# Canvas + drawing primitives
# --------------------------------------------------------------------------
canvas = bytearray(W * H * 3)


def rect(x, y, w, h, c):
    """Filled axis-aligned rectangle, clipped to the canvas."""
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    stride = W * 3
    off = y0 * stride + x0 * 3
    for _ in range(y1 - y0):
        canvas[off:off + len(row)] = row
        off += stride


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        off = (y * W + x) * 3
        canvas[off] = c[0]
        canvas[off + 1] = c[1]
        canvas[off + 2] = c[2]


def line(x0, y0, x1, y1, c, t=1):
    """Thick Bresenham line (t = thickness in pixels)."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    half = t // 2
    while True:
        rect(x0 - half, y0 - half, t, t, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, c):
    """Filled circle via scanlines."""
    for yy in range(max(0, cy - r), min(H, cy + r + 1)):
        d = r * r - (yy - cy) * (yy - cy)
        if d < 0:
            continue
        half = int(math.isqrt(d))
        rect(cx - half, yy, 2 * half + 1, 1, c)


def ring(cx, cy, r, c, t=2):
    """Circle outline of thickness t."""
    for yy in range(max(0, cy - r - t), min(H, cy + r + t + 1)):
        for xx in range(max(0, cx - r - t), min(W, cx + r + t + 1)):
            d = math.hypot(xx - cx, yy - cy)
            if r - t <= d <= r:
                px(xx, yy, c)


def vgrad(x, y, w, h, c0, c1):
    """Vertical linear gradient from c0 (top) to c1 (bottom)."""
    for i in range(h):
        f = i / max(1, h - 1)
        c = (
            int(c0[0] + (c1[0] - c0[0]) * f),
            int(c0[1] + (c1[1] - c0[1]) * f),
            int(c0[2] + (c1[2] - c0[2]) * f),
        )
        rect(x, y + i, w, 1, c)


def rect_outline(x, y, w, h, c, t=2):
    rect(x, y, w, t, c)
    rect(x, y + h - t, w, t, c)
    rect(x, y, t, h, c)
    rect(x + w - t, y, t, h, c)


def text_width(s, scale, gap):
    if not s:
        return 0
    return len(s) * 5 * scale + (len(s) - 1) * gap


def draw_text(s, x, y, scale, c, gap=None):
    """Draw a string with the bitmap font. Uppercase-only; unknown -> space."""
    if gap is None:
        gap = scale
    s = s.upper()
    cx = x
    for ch in s:
        pts = FONT.get(ch)
        if pts:
            for dx, dy in pts:
                rect(cx + dx * scale, y + dy * scale, scale, scale, c)
        cx += 5 * scale + gap


def center_text(s, cx, y, scale, c, gap=None):
    if gap is None:
        gap = scale
    draw_text(s, cx - text_width(s, scale, gap) // 2, y, scale, c, gap)


def wave(x0, x1, y, amp, period, c):
    """One guilloche sine wave."""
    for x in range(x0, x1):
        yy = y + int(amp * math.sin((x - x0) * 2.0 * math.pi / period))
        px(x, yy, c)
        px(x, yy + 1, c)


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
DESK = (26, 30, 40)
DESK_DARK = (15, 17, 25)
PAGE = (238, 232, 214)
PAGE_EDGE = (214, 206, 184)
INK = (22, 32, 54)
NAVY = (22, 32, 54)
TEAL = (14, 74, 68)
TEAL_LT = (30, 110, 100)
GOLD = (176, 141, 62)
GOLD_LT = (206, 178, 110)
LABEL = (96, 96, 92)
RULE = (150, 142, 120)
MRZ_BG = (224, 226, 230)
STAMP_BLUE = (32, 72, 142)
STAMP_RED = (168, 42, 42)
STAMP_GREEN = (32, 108, 62)
STAMP_PURPLE = (92, 52, 122)
SKIN = (212, 176, 138)
SKIN_DK = (196, 158, 120)
HAIR = (58, 40, 26)
JACKET = (30, 44, 80)
WHITE = (255, 255, 255)

# --------------------------------------------------------------------------
# Machine-readable zone (ICAO 9303 check digits)
# --------------------------------------------------------------------------
def mrz_value(ch):
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    return ord(ch) - 55  # A=10 ... Z=35


def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        total += mrz_value(ch) * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<KLD" + "VOSS<<ELARA<MIREN"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "KLD047118"
    nat = "KLD"
    dob = "940314"   # 14 MAR 1994
    sex = "F"
    exp = "330601"   # 01 JUN 2033
    pers = "VOSS940314<<<<"  # 14 chars
    body = (doc + mrz_check(doc) + nat + dob + mrz_check(dob) + sex
            + exp + mrz_check(exp) + pers + mrz_check(pers))
    line2 = body + mrz_check(body)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# --------------------------------------------------------------------------
# Portrait (stylised photo of the holder, Elara Miren Voss)
# --------------------------------------------------------------------------
def portrait(x, y, w, h):
    vgrad(x, y, w, h, (178, 190, 202), (148, 162, 178))
    cx = x + w // 2
    # hair back + top bun
    disc(cx, y + 52, 40, HAIR)
    disc(cx, y + 24, 13, HAIR)
    # face
    disc(cx, y + 88, 33, SKIN)
    # hair strands framing the face
    rect(x + 30, y + 46, 10, 56, HAIR)
    rect(x + 110, y + 46, 10, 56, HAIR)
    # brows + eyes
    rect(cx - 22, y + 74, 14, 3, HAIR)
    rect(cx + 8, y + 74, 14, 3, HAIR)
    rect(cx - 20, y + 82, 10, 4, (20, 18, 16))
    rect(cx + 10, y + 82, 10, 4, (20, 18, 16))
    px(cx - 17, y + 82, WHITE)
    px(cx + 13, y + 82, WHITE)
    # nose + lips
    line(cx, y + 88, cx, y + 104, SKIN_DK, 2)
    rect(cx - 5, y + 104, 10, 2, SKIN_DK)
    rect(cx - 9, y + 114, 18, 5, (150, 90, 80))
    # neck + shoulders (jacket + shirt)
    rect(cx - 9, y + 120, 18, 18, SKIN_DK)
    rect(x + 8, y + 138, 44, 14, JACKET)
    rect(x + 98, y + 138, 44, 14, JACKET)
    rect(x + 52, y + 138, 46, 14, JACKET)
    rect(x + 8, y + 152, 134, 38, JACKET)
    rect(cx - 7, y + 138, 14, 30, WHITE)
    line(cx - 16, y + 140, cx, y + 156, (200, 200, 200), 2)
    line(cx + 16, y + 140, cx, y + 156, (200, 200, 200), 2)


# --------------------------------------------------------------------------
# Stamps
# --------------------------------------------------------------------------
def stamp_rect(x, y, w, h, color, lines):
    """Rectangular ink stamp; lines = [(text, scale), ...] centred."""
    rect_outline(x, y, w, h, color, 3)
    rect_outline(x + 6, y + 6, w - 12, h - 12, color, 1)
    total = sum(7 * s + 6 for _, s in lines) + 8 * (len(lines) - 1)
    cy = y + (h - total) // 2
    for text, scale in lines:
        center_text(text, x + w // 2, cy, scale, color)
        cy += 7 * scale + 8


def stamp_circle(cx, cy, r, color, lines):
    ring(cx, cy, r, color, 3)
    ring(cx, cy, r - 7, color, 1)
    total = sum(7 * s + 6 for _, s in lines) + 8 * (len(lines) - 1)
    y = cy - total // 2
    for text, scale in lines:
        center_text(text, cx, y, scale, color)
        y += 7 * scale + 8


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def page_frame(x, y, w, h):
    rect(x + 6, y + 8, w, h, DESK_DARK)          # drop shadow
    rect(x, y, w, h, PAGE)
    rect_outline(x + 10, y + 10, w - 20, h - 20, GOLD, 2)
    rect_outline(x + 16, y + 16, w - 32, h - 32, RULE, 1)


def data_page(x, y, w, h):
    page_frame(x, y, w, h)
    # header band
    rect(x, y, w, 66, TEAL)
    rect(x, y + 66, w, 3, GOLD)
    disc(x + 34, y + 33, 17, GOLD)
    draw_text("K", x + 27, y + 22, 3, TEAL)
    center_text("REPUBLIC OF KALDERA", x + w // 2 + 12, y + 14, 2, WHITE)
    center_text("MINISTRY OF THE INTERIOR", x + w // 2 + 12, y + 40, 1,
                GOLD_LT)
    # title
    center_text("PASSPORT", x + w // 2, y + 82, 3, NAVY)
    rect(x + 60, y + 112, w - 120, 2, NAVY)
    wave(x + 26, x + w - 26, y + 122, 2, 46, GOLD_LT)
    # photo
    px0, py0, pw, ph = x + 26, y + 130, 150, 190
    portrait(px0, py0, pw, ph)
    rect_outline(px0, py0, pw, ph, NAVY, 3)
    ring(px0 + pw - 12, py0 + ph - 12, 14, GOLD, 2)
    # fields beside the photo
    fx = x + 196
    fy = y + 132
    for i, (label, value) in enumerate((
            ("TYPE", "P"),
            ("CODE", "KLD"),
            ("PASSPORT NO.", "KLD 047 118"))):
        yy = fy + i * 62
        draw_text(label, fx, yy, 1, LABEL)
        draw_text(value, fx, yy + 11, 2, NAVY)
    # field rows
    rows = (
        ("SURNAME", "VOSS"),
        ("GIVEN NAMES", "ELARA MIREN"),
        ("NATIONALITY", "KALDERAN"),
        ("DATE OF BIRTH", "14 MAR 1994"),
        ("SEX", "F"),
        ("PLACE OF BIRTH", "PORT EMBER"),
        ("DATE OF ISSUE", "02 JUN 2023"),
        ("DATE OF EXPIRY", "01 JUN 2033"),
        ("AUTHORITY", "MINISTRY OF THE INTERIOR"),
    )
    yy = y + 340
    for label, value in rows:
        draw_text(label, x + 26, yy, 1, LABEL)
        draw_text(value, x + 26, yy + 11, 2, NAVY)
        rect(x + 26, yy + 28, w - 52, 1, PAGE_EDGE)
        yy += 32
    # observations — the telling detail
    oy = y + 636
    rect_outline(x + 26, oy, w - 52, 52, NAVY, 2)
    draw_text("OBSERVATIONS", x + 34, oy + 7, 1, LABEL)
    draw_text("ASH SEASON TRAVEL BAN: NO DEPARTURES NOV-FEB.",
              x + 34, oy + 24, 1, STAMP_RED)
    draw_text("VOLCANO LEVY PAID AT ISSUE.", x + 34, oy + 37, 1, STAMP_RED)
    # microtext
    draw_text("REPUBLIC OF KALDERA \u00b7 MINISTRY OF THE INTERIOR \u00b7 "
              "PORT EMBER \u00b7", x + 26, y + 700, 1, LABEL)
    # machine-readable zone
    rect(x, y + 712, w, 88, MRZ_BG)
    rect(x, y + 712, w, 2, NAVY)
    l1, l2 = mrz_lines()
    draw_text(l1, x + 15, y + 726, 2, NAVY, gap=0)
    draw_text(l2, x + 15, y + 748, 2, NAVY, gap=0)
    center_text("KLD \u00b7 1", x + w // 2, y + 776, 1, LABEL)


def stamps_page(x, y, w, h):
    page_frame(x, y, w, h)
    center_text("VISAS", x + w // 2, y + 22, 3, NAVY)
    center_text("STAMPS AND ENDORSEMENTS", x + w // 2, y + 52, 1, LABEL)
    rect(x + 60, y + 70, w - 120, 2, NAVY)
    wave(x + 26, x + w - 26, y + 80, 2, 46, GOLD_LT)
    # visitor visa sticker
    vx, vy, vw, vh = x + 26, y + 92, w - 52, 110
    rect_outline(vx, vy, vw, vh, TEAL, 2)
    rect(vx, vy, vw, 26, TEAL)
    center_text("VISITOR VISA - ISLE OF TARN", vx + vw // 2, vy + 8, 1, WHITE)
    draw_text("VALID 90 DAYS \u00b7 SINGLE ENTRY", vx + 12, vy + 38, 1, NAVY)
    draw_text("ISSUED 08 MAY 2024 - PORT EMBER", vx + 12, vy + 56, 1, NAVY)
    draw_text("FEE PAID 25 KLD \u00b7 VISA NO. T-8814", vx + 12, vy + 74, 1,
              NAVY)
    ring(vx + vw - 34, vy + 76, 18, GOLD, 2)
    draw_text("T", vx + vw - 40, vy + 68, 2, GOLD)
    # six stamps, one plausible travel chain, all after the 02 JUN 2023 issue
    stamps = (
        ("DEPARTED", "PORT EMBER", "09 MAY 2024", STAMP_BLUE),
        ("ARRIVED", "ISLE OF TARN", "10 MAY 2024", STAMP_GREEN),
        ("DEPARTED", "ISLE OF TARN", "02 JUL 2024", STAMP_GREEN),
        ("ARRIVED", "SAN MERIDIAN", "02 JUL 2024", STAMP_PURPLE),
        ("DEPARTED", "SAN MERIDIAN", "17 AUG 2024", STAMP_RED),
        ("ARRIVED", "PORT EMBER", "18 AUG 2024", STAMP_BLUE),
    )
    for i, (kind, place, date, color) in enumerate(stamps):
        sx = x + 26 + (i % 2) * 218
        sy = y + 220 + (i // 2) * 116
        stamp_rect(sx, sy, 200, 104, color,
                   [(kind, 2), (place, 1), (date, 1)])
    # volcano levy fee stamp
    fx, fy, fw, fh = x + 26, y + 580, w - 52, 64
    rect_outline(fx, fy, fw, fh, STAMP_RED, 3)
    rect_outline(fx + 6, fy + 6, fw - 12, fh - 12, STAMP_RED, 1)
    center_text("VOLCANO LEVY - PAID 40 KLD", fx + fw // 2, fy + 14, 2,
                STAMP_RED)
    center_text("ASH SEASON TRAVEL BAN IN FORCE NOV-FEB",
                fx + fw // 2, fy + 40, 1, STAMP_RED)
    # bottom ornament
    wave(x + 26, x + w - 26, y + 700, 2, 46, GOLD_LT)
    center_text("REPUBLIC OF KALDERA", x + w // 2, y + 724, 1, NAVY)
    center_text("KLD \u00b7 2", x + w // 2, y + 776, 1, LABEL)


# --------------------------------------------------------------------------
# PNG encoder (stdlib only)
# --------------------------------------------------------------------------
def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png():
    raw = bytearray()
    stride = W * 3
    for yy in range(H):
        raw.append(0)  # filter: None
        raw.extend(canvas[yy * stride:(yy + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    rect(0, 0, W, H, DESK)
    rect(0, 0, W, 14, DESK_DARK)
    rect(0, H - 14, W, 14, DESK_DARK)
    data_page(30, 100, 470, 800)
    rect(500, 100, 24, 800, (12, 13, 20))  # spine shadow
    stamps_page(524, 100, 470, 800)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as f:
        f.write(encode_png())


if __name__ == "__main__":
    main()
