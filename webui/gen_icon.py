# -*- coding: utf-8 -*-
"""仫岭音集 ICON 生成器：128×128 圆角方形，哑光藏青底 + 单线朱砂凤凰 + 底边回旋混沌花"""
import math, os, random
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))          # minzu-musiic/webui
ROOT = os.path.dirname(HERE)                               # minzu-musiic
OUT = os.path.join(os.path.dirname(ROOT), '仫岭音集', 'assets', 'img')
os.makedirs(OUT, exist_ok=True)

S = 1024                      # 超采样画布
INDIGO = (44, 61, 89, 255)    # 哑光藏青 #2C3D59
INDIGO_LT = (62, 82, 116, 255)
CINNABAR = (178, 59, 43, 255) # 哑光朱砂红 #B23B2B
NOISE = 10                    # 磨砂颗粒强度


def bez(p0, p1, p2, p3, n=60):
    pts = []
    for k in range(n + 1):
        t = k / n
        mt = 1 - t
        x = mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0]
        y = mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


def stroke(draw, pts, w, color):
    draw.line(pts, fill=color, width=w, joint='curve')
    r = w / 2
    for p in (pts[0], pts[-1]):
        draw.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=color)


def volute(cx, cy, r0, turns=1.15, shrink=0.72, n=46, phase=math.radians(205)):
    """涡卷（混沌花单元）：螺旋收卷"""
    pts = []
    for k in range(n + 1):
        t = k / n
        a = phase + t * turns * 2 * math.pi
        r = r0 * (1 - shrink * t)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def build():
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆角方形底
    rad = int(S * 0.225)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=rad, fill=INDIGO)
    # 内缘细线（工艺感，非渐变）
    d.rounded_rectangle([10, 10, S - 11, S - 11], radius=rad - 10,
                        outline=(58, 78, 112, 110), width=3)

    # ===== 单线抽象凤凰（朱砂红，等宽单线）=====
    W = 46
    # 主体一笔：尾尖(左下) -> 体 -> 颈 -> 头 -> 喙(右上挑)
    body = (bez((150, 830), (250, 775), (330, 700), (410, 640)) +
            bez((410, 640), (490, 580), (530, 505), (595, 440)) +
            bez((595, 440), (635, 400), (675, 380), (710, 390)) +
            bez((710, 390), (745, 400), (756, 420), (744, 446)))
    stroke(d, body, W, CINNABAR)
    # 翅：自体中段向左上扬起，梢右指（不与头颈交叠）
    wing = (bez((405, 645), (372, 545), (392, 435), (472, 362)) +
            bez((472, 362), (514, 332), (560, 338), (586, 368)))
    stroke(d, wing, W, CINNABAR)
    # 尾羽流线：短收，不越底边涡卷带
    tail = (bez((196, 798), (152, 836), (122, 868), (112, 896)))
    stroke(d, tail, int(W * 0.82), CINNABAR)

    # ===== 底边回旋混沌花（三枚涡卷）=====
    CW = 20
    for cx in (330, 512, 694):
        stroke(d, volute(cx, 930, 46), CW, CINNABAR)

    # ===== 微磨砂颗粒 =====
    random.seed(7)
    noise = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    nd = ImageDraw.Draw(noise)
    for _ in range(int(S * S * 0.06)):
        x, y = random.randrange(S), random.randrange(S)
        v = random.choice([(0, 0, 0, NOISE), (255, 255, 255, NOISE)])
        nd.point((x, y), fill=v)
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=rad, fill=255)
    img.paste(noise, (0, 0), Image.composite(noise.split()[3], Image.new('L', (S, S), 0), mask))

    # 缩放到 256 出图
    img256 = img.resize((256, 256), Image.LANCZOS)
    img256.save(os.path.join(OUT, 'icon.png'))
    img128 = img.resize((128, 128), Image.LANCZOS)
    img128.save(os.path.join(OUT, 'icon_128.png'))
    # ICO 多尺寸
    img.save(os.path.join(OUT, 'icon.ico'), sizes=[(16, 16), (24, 24), (32, 32),
                                                   (48, 48), (64, 64), (128, 128), (256, 256)])
    print('icon written ->', OUT)

    # ===== 凤凰标识（透明底，播放栏/文档用）=====
    lg = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lg)
    stroke(ld, body, W, CINNABAR)
    stroke(ld, wing, W, CINNABAR)
    stroke(ld, tail, int(W * 0.82), CINNABAR)
    lg.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, 'logo_mark.png'))
    print('logo_mark.png written')


if __name__ == '__main__':
    build()
