# -*- coding: utf-8 -*-
"""仫岭音集 UI 纹样资产生成器：全部抽象单线几何，PIL 绘制"""
import math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(os.path.dirname(ROOT), '仫岭音集', 'assets', 'img')
os.makedirs(OUT, exist_ok=True)

RICE = (233, 223, 204)      # 柔和米白
CINNABAR = (178, 59, 43)    # 哑光朱砂红
GOLD = (154, 123, 79)       # 暗金


def bez(p0, p1, p2, p3, n=60):
    pts = []
    for k in range(n + 1):
        t = k / n
        mt = 1 - t
        pts.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0],
                    mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
    return pts


def stroke(d, pts, w, color):
    d.line(pts, fill=color, width=w, joint='curve')
    r = w / 2
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=color)


def volute(cx, cy, r0, turns=1.15, shrink=0.72, n=46, phase=math.radians(205)):
    pts = []
    for k in range(n + 1):
        t = k / n
        a = phase + t * turns * 2 * math.pi
        r = r0 * (1 - shrink * t)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------- 1. 回字土布织纹 72px 平铺单元（2x 绘制） ----------
def gen_tile():
    S = 144
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 3
    c = RICE + (255,)
    # 四枚回字 + 经纬连线 + 单元外框
    hui = 'M12 36V12h24v24H19V19h10v10h-6v-6'
    for ox, oy in ((0, 0), (36, 0), (0, 36), (36, 36)):
        d.line(bez((12+ox, 36+oy), (12+ox, 12+oy), (36+ox, 12+oy), (36+ox, 36+oy)), fill=c, width=w, joint='curve')
        # 用折线精确重绘回字（避免贝塞尔失真）
    for ox, oy in ((0, 0), (36, 0), (0, 36), (36, 36)):
        pts = [(12+ox, 36+oy), (12+ox, 12+oy), (36+ox, 12+oy), (36+ox, 36+oy),
               (19+ox, 36+oy), (19+ox, 19+oy), (29+ox, 19+oy), (29+ox, 29+oy),
               (23+ox, 29+oy), (23+ox, 23+oy)]
        d.line(pts, fill=c, width=w, joint='curve')
    # 经纬连线
    d.line([(0, 36), (12, 36)], fill=c, width=w)
    d.line([(60, 36), (72, 36)], fill=c, width=w)
    d.line([(36, 0), (36, 12)], fill=c, width=w)
    d.line([(36, 60), (36, 72)], fill=c, width=w)
    d.rectangle([0, 0, 71, 71], outline=c, width=w)
    img.save(os.path.join(OUT, 'tile_hui.png'))
    print('tile_hui.png', img.size)


# ---------- 2. 凤凰流线（标题栏下沿，2x） ----------
def gen_phoenix_line():
    W, H = 2400, 18
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    main = (bez((0, 12), (180, 12), (300, 5), (464, 7)) +
            bez((464, 7), (628, 9), (756, 6), (900, 8)) +
            bez((900, 8), (1120, 11), (1700, 6), (2400, 8)))
    stroke(d, main, 4, CINNABAR + (255,))
    # 两段凤羽上扬
    stroke(d, bez((524, 6), (560, 1), (596, 1), (624, 4)), 3, CINNABAR + (220,))
    stroke(d, bez((612, 7), (640, 4), (668, 4), (696, 7)), 2, CINNABAR + (140,))
    img.save(os.path.join(OUT, 'phoenix_line.png'))
    print('phoenix_line.png', img.size)


# ---------- 3. 极简石榴（2x，20px 显示） ----------
def gen_pom():
    S = 40
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 3
    c = GOLD + (255,)
    # 果体（圆）
    d.ellipse([7, 13, 33, 37], outline=c, width=w)
    # 果萼
    d.line([(20, 13), (20, 7)], fill=c, width=w)
    d.line([(15, 8), (18, 3)], fill=c, width=w)
    d.line([(25, 8), (22, 3)], fill=c, width=w)
    # 内部籽粒暗示
    d.arc([13, 24, 20, 34], 200, 340, fill=c, width=w - 1)
    d.arc([20, 24, 27, 34], 200, 340, fill=c, width=w - 1)
    img.save(os.path.join(OUT, 'pom.png'))
    print('pom.png', img.size)


# ---------- 4. 双鱼曲线（2x，17px 显示） ----------
def gen_fish():
    S = 34
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 3
    c = GOLD + (255,)
    d.ellipse([3, 3, 31, 31], outline=c, width=w)
    d.line(bez((17, 5), (8, 12), (8, 22), (17, 29)), fill=c, width=w, joint='curve')
    d.line(bez((17, 5), (26, 12), (26, 22), (17, 29)), fill=c, width=w, joint='curve')
    img.save(os.path.join(OUT, 'fish.png'))
    print('fish.png', img.size)


# ---------- 5. 混沌花分隔线（2x） ----------
def gen_chaos_sep():
    W, H = 400, 24
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = GOLD + (110,)
    d.line([(0, 12), (168, 12)], fill=c, width=2)
    d.line([(232, 12), (400, 12)], fill=c, width=2)
    stroke(d, volute(200, 12, 9, turns=1.1, shrink=0.7, n=40), 2, GOLD + (200,))
    img.save(os.path.join(OUT, 'chaos_sep.png'))
    print('chaos_sep.png', img.size)


# ---------- 6. 回字角标（2x，22px 显示） ----------
def gen_hui_mark():
    S = 44
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 3
    c = GOLD + (255,)
    pts = [(6, 38), (6, 6), (38, 6), (38, 38), (17, 38), (17, 17),
           (27, 17), (27, 27), (22, 27), (22, 22)]
    d.line(pts, fill=c, width=w, joint='curve')
    img.save(os.path.join(OUT, 'hui_mark.png'))
    print('hui_mark.png', img.size)


# ---------- 7. 心形（收藏，2x，16px 显示） ----------
def gen_heart():
    S = 34
    for name, filled in (('heart', False), ('heart_full', True)):
        img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        col = CINNABAR + (255,) if filled else RICE + (120,)
        # 心形路径（贝塞尔近似）
        p = (bez((17, 30), (3, 21), (3, 11), (11, 6), n=20) +
             bez((11, 6), (15, 3.5), (17, 6), (17, 9), n=12) +
             bez((17, 9), (17, 6), (19, 3.5), (23, 6), n=12) +
             bez((23, 6), (31, 11), (31, 21), (17, 30), n=20))
        if filled:
            d.polygon(p, fill=col)
        else:
            stroke(d, p, 3, col)
        img.save(os.path.join(OUT, name + '.png'))
        print(name + '.png', img.size)


if __name__ == '__main__':
    gen_tile()
    gen_phoenix_line()
    gen_pom()
    gen_fish()
    gen_chaos_sep()
    gen_hui_mark()
    gen_heart()
    print('all UI motifs ->', OUT)
