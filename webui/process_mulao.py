# -*- coding: utf-8 -*-
"""将搜索结果( mulao_search_raw.json )与现有仫佬族曲库( e30 )比对，
产出山河回响网页中缺失的仫佬族歌曲候选清单，并构造各平台可播放链接。"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / 'webui' / 'mulao_search_raw.json'
E30 = BASE / 'webui' / 'ethnos_cache' / 'e30_仫佬族.json'
DENY = BASE / 'webui' / 'ethnos_cache' / 'e30_denylist.json'

raw = json.load(open(RAW, encoding='utf-8'))
e30 = json.load(open(E30, encoding='utf-8'))
deny = set()
if DENY.exists():
    dl = json.load(open(DENY, encoding='utf-8'))
    deny = {str(x).strip().lower() for x in (dl if isinstance(dl, list) else dl.get('songs', []))}

# ---- 归一化 ----
_alnum = re.compile(r'[\w\u4e00-\u9fff]+')
def norm(s):
    return ''.join(_alnum.findall(str(s).lower()))

def core_name(name):
    n = str(name)
    # 去掉书名号
    n = n.replace('《', '').replace('》', '')
    # 去掉常见平台/版本后缀
    n = re.split(r'\s*[-—–]\s*', n)[0]
    n = re.split(r'[__】]', n)[0]
    for suf in ['mv', '高清版', '官方发布', '原创音乐mv', '原唱', '伴奏', '现场版',
               '好听视频', '好看视频', '完整版', '音乐mv', '（', '(']:
        n = n.replace(suf, '')
    return norm(n)

# 基线：现有 53 首的 (core, singer) 集合
baseline = set()
for t in e30['tracks']:
    nm = core_name(t.get('song_name', ''))
    sg = norm(t.get('singers', ''))
    baseline.add((nm, sg))
    baseline.add((nm, ''))  # 仅按曲名也能命中(同曲不同歌手来源仍视为已收录)

# ---- 相关性判定（是否确为仫佬族歌曲）----
KNOWN_ARTISTS = {'姚亮', '银悦西', '覃大军', '仫佬族姚亮', '雷佳', '广西罗城县文化馆'}
INHERENT_KW = {'仫佬族', '仫佬', '仫佬族山歌', '仫佬族民歌', '依饭节', '古条歌',
               '走坡', '墙贝歌', '仫佬族敬酒歌', '唱响山歌感党恩'}
def is_mulao(name, singer, kw):
    if '仫佬' in str(name):
        return True, '曲名含仫佬'
    if str(singer) in KNOWN_ARTISTS:
        return True, f'歌手为仫佬族相关艺人({singer})'
    if kw in INHERENT_KW:
        return True, f'检索词即仫佬族主题({kw})'
    if any(k in str(name) for k in ['走坡', '依饭', '古条', '罗城仫佬', '仫佬族']):
        return True, '曲名含仫佬族主题词'
    return False, ''

# ---- 构造可播放链接 ----
def playable_url(r):
    sc = r.get('src_client', '')
    sid = str(r.get('id', '') or '')
    du = r.get('download_url', '') or ''
    if sc == 'BilibiliMusicClient':
        if sid.startswith('BV'):
            return f'https://www.bilibili.com/video/{sid}', 'bilibili'
        if du.startswith('http'):
            return du, 'bilibili'
    if sc == 'MyFreeMP3MusicClient':
        if sid:
            return f'https://music.163.com/song?id={sid}', '网易云音乐'
        if du.startswith('http'):
            return du, '网易云音乐'
    if sc == 'MiguMusicClient':
        if sid:
            return f'https://music.migu.cn/v3/music/song/{sid}', '咪咕音乐'
    if sc == 'KuwoMusicClient':
        if sid:
            return f'https://www.kuwo.cn/play_detail/{sid}', '酷我音乐'
    if sc == 'KugouMusicClient':
        if sid:
            return f'https://www.kugou.com/song/#hash={sid}', '酷狗音乐'
    if sc == 'TwoT58MusicClient':
        if sid:
            return f'https://www.2t58.com/play/{sid}', '5sing/TwoT58'
    if sc == 'YinyuekuMusicClient':
        if sid:
            return f'http://www.yinyueku.com/song/{sid}.html', '音乐库'
    if du.startswith('http'):
        return du, '直链'
    return '', '未知'

# ---- 主流程 ----
candidates = []
for r in raw:
    nm = r.get('song_name', '').strip()
    sg = (r.get('singers', '') or '').strip()
    if not nm:
        continue
    c = core_name(nm)
    sgn = norm(sg)
    # 去重：与基线同曲
    if (c, sgn) in baseline or (c, '') in baseline:
        continue
    # 去重：落在人工剔除名单(非仫佬)里
    low = nm.lower()
    if any(d and (d == low or (len(d) >= 4 and d in low)) for d in deny):
        continue
    rel, reason = is_mulao(nm, sg, r.get('kw', ''))
    if not rel:
        continue
    url, plat = playable_url(r)
    candidates.append({
        'song_name': nm, 'singers': sg, 'source': r.get('source_cn', r.get('source', '')),
        'platform': plat, 'url': url, 'kw': r.get('kw', ''),
        'rel_reason': reason, 'id': str(r.get('id', '') or ''),
        'src_client': r.get('src_client', ''),
    })

# 二次去重（同曲多名/多源），保留首个且有链接的
seen2 = set()
final = []
for c in candidates:
    key = (core_name(c['song_name']), norm(c['singers']))
    if key in seen2:
        continue
    seen2.add(key)
    final.append(c)

out = {
    'total_raw': len(raw),
    'candidates_after_filter': len(candidates),
    'final_new': len(final),
    'items': final,
}
json.dump(out, open(BASE / 'webui' / 'mulao_new_candidates.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print(f"raw={len(raw)}  过滤后候选={len(candidates)}  去重后新歌={len(final)}")
print("="*60)
for i, c in enumerate(final, 1):
    print(f"{i:3d}. {c['song_name'][:34]!r} | {c['singers'][:18]!r} | {c['platform']} | {c['rel_reason']}")
    print(f"     URL: {c['url']}")
