# -*- coding: utf-8 -*-
"""把《仫佬族新增歌曲.docx》中的 10 首歌曲按 SKILL.md(mountainriverechoes-ingest) 录入 e30 仫佬族曲库。
- 网易云: _parsewithofficialapiv1 按 song id 官方解析(禁止第三方链)
- B 站   : av->bvid(view API) + BilibiliMusicClient._parsewithofficialapiv1
- 咪咕   : MiguMusicClient.search(仅官方解析)
- 合并   : 复用主程序 _dedup_key/_ethnos_payload/_atomic_write_json, warm 优先, 原子落盘
用法: python webui/ingest_mulao.py            # 干跑(只解析不写库)
      python webui/ingest_mulao.py --apply    # 解析 + 合并写入 e30
"""
import sys, json, shutil, time, threading, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os = __import__('os'); os.chdir(str(ROOT / 'webui'))

from webui import mountainriverechoes as mre
from musicdl.modules import SongInfo
from musicdl.modules.sources import netease as ne_mod
from musicdl.modules.sources import bilibili as bili_mod
from musicdl.modules.sources import migu as migu_mod
from musicdl.modules.sources import kuwo as kuwo_mod

import urllib.request as urlreq

GROUP = 'e30'
TARGETS = [
    {'name': '墙贝歌(仫佬族民歌)', 'singer': '雷佳',        'plat': 'kuwo',    'kw': '墙贝歌'},
    {'name': '仫佬族婚俗',          'singer': '仫佬余音',    'plat': 'netease', 'id': 1950172868},
    {'name': '稻香坡上歌（仫佬族）', 'singer': '黄鹂声声',    'plat': 'netease', 'id': 3433302904},
    {'name': '字谜歌',             'singer': '仫佬余音',    'plat': 'netease', 'id': 1950172871},
    {'name': '祝寿歌',             'singer': '仫佬余音',    'plat': 'netease', 'id': 1950171883},
    {'name': '刺绣',              'singer': '仫佬余音',    'plat': 'netease', 'id': 1950171868},
    {'name': '罗城仫佬族自治县成立40周年主题曲《魅力罗城》', 'singer': '广西罗城县文化馆', 'plat': 'bili', 'bvid': 'BV1pXUWYvEPX'},
    {'name': '“家国团圆 盛世欢歌”2026 罗城仫佬族古歌暨走坡保护成果展示', 'singer': '广西罗城县文化馆', 'plat': 'bili', 'bvid': 'BV1Jkps6cExX'},
    {'name': '仫佬族的情歌',        'singer': '我是两小时',  'plat': 'bili', 'bvid': 'BV1JM4y1e7H7'},
    {'name': '仫佬族歌曲，喜乐',     'singer': '黑暗亵渎',   'plat': 'bili', 'bvid': 'BV1DyHweTEjt'},
]

def bili_view_by_bvid(bvid):
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    req = urlreq.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com'})
    with urlreq.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode('utf-8'))
    if d.get('code') != 0:
        raise RuntimeError(f"view code={d.get('code')} {d.get('message')}")
    dd = d['data']
    return {'aid': dd.get('aid'), 'title': dd['title'],
            'author': (dd.get('owner') or {}).get('name', ''), 'pic': dd.get('pic', '')}

def resolve(t):
    plat = t['plat']
    if plat == 'netease':
        nc = ne_mod.NeteaseMusicClient()
        si = nc._parsewithofficialapiv1(search_result={'id': t['id']},
                                        song_info_flac=None,
                                        lossless_quality_is_sufficient=False)
        return si
    if plat == 'bili':
        v = bili_view_by_bvid(t['bvid'])
        bili = bili_mod.BilibiliMusicClient()
        res = bili._parsewithofficialapiv1(
            search_result={'id': v['aid'] or t['bvid'], 'bvid': t['bvid'],
                           'author': t['singer'] or v['author'],
                           'pic': v['pic'], 'title': v['title']},
            song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides={})
        if isinstance(res, list):
            res = res[0] if res else None
        return res
    if plat == 'migu':
        mg = migu_mod.MiguMusicClient()
        songs = mg.search(keyword=t['kw'], num_threadings=1, request_overrides={}, rule={}) or []
        for s in songs:
            if t['kw'].split('(')[0] in (s.song_name or ''):
                return s
        return songs[0] if songs else None
    if plat == 'kuwo':
        kw = kuwo_mod.KuwoMusicClient()
        songs = kw.search(keyword=t['kw'], num_threadings=1, request_overrides={}, rule={}) or []
        for s in songs:
            if t['singer'] in (s.singers or '') and t['kw'].split('(')[0] in (s.song_name or ''):
                return s
        for s in songs:
            if t['kw'].split('(')[0] in (s.song_name or ''):
                return s
        return songs[0] if songs else None
    return None

# ---------- 解析(干跑) ----------
songs = []
print("=== 解析阶段 ===")
for t in TARGETS:
    try:
        si = resolve(t)
    except Exception as e:
        si = None; err = repr(e)
    else:
        err = ''
    ok = isinstance(si, SongInfo) and getattr(si, 'with_valid_download_url', False)
    if ok:
        songs.append(si)
        print(f"  [OK] {t['name'][:26]:26s} | {si.singers[:12]:12s} | ext={si.ext} | id={si.identifier} | url={str(si.download_url)[:48]}")
    else:
        print(f"  [FAIL] {t['name'][:26]:26s} | {err[:120]}")
print(f"解析成功 {len(songs)}/{len(TARGETS)}")

# ---------- 合并写库(安全追加式, 不整份重建, 保护 e30 已贴的人工歌手标签) ----------
def append_into(group_key, new_songs):
    path = mre._cache_path(group_key)
    d = json.loads(path.read_text(encoding='utf-8'))
    tracks = d.get('tracks') or []
    existing_keys = set()
    for t in tracks:
        s = SongInfo.fromdict(t.get('_song') or {})
        if s.song_name:
            existing_keys.add(mre._dedup_key(s))
    added = 0
    for s in new_songs:
        if s is None:
            continue
        k = mre._dedup_key(s)
        if k in existing_keys:
            continue
        brief = mre.song_brief(s, 'Ethnos', len(tracks))
        real = (s.source or '').removesuffix('MusicClient')
        if isinstance(s.download_url, str) and s.download_url.startswith('ytdlp:'):
            real = 'Bilibili' if 'bilibili.com' in s.download_url else 'YouTube'
        elif isinstance(s.download_url, str) and 'res.wx.qq.com' in s.download_url:
            real = '光音·微信'
        brief['source'] = real or 'Ethnos'
        brief['source_cn'] = mre.SOURCE_NAMES.get(real, real) if real else '民族音乐'
        tracks.append(dict(brief, _song=mre._slim_song(s.todict())))
        existing_keys.add(k)
        added += 1
    d['tracks'] = tracks
    d['count'] = len(tracks)
    d['built_at'] = time.time()
    mre._atomic_write_json(path, d)
    return added, len(tracks)

if '--apply' in sys.argv:
    # 剔除名单检查
    deny = set()
    dlp = ROOT / 'webui' / 'ethnos_cache' / 'e30_denylist.json'
    if dlp.exists():
        dl = json.load(open(dlp, encoding='utf-8'))
        deny = {str(x).strip().lower() for x in (dl if isinstance(dl, list) else dl.get('songs', []))}
    hits = [t['name'] for t in TARGETS
            if any(d == t['name'].lower() or (len(d) >= 4 and d in t['name'].lower()) for d in deny)]
    if hits:
        print("⚠️ 以下曲名命中 e30_denylist，请先确认:", hits)
    # 手动备份
    e30 = ROOT / 'webui' / 'ethnos_cache' / 'e30_仫佬族.json'
    bak = e30.with_suffix(f'.json.bak_pre_ingest_{datetime.datetime.now():%Y%m%d_%H%M%S}')
    shutil.copy(e30, bak)
    print("backup ->", bak.name)
    added, total = append_into(GROUP, songs)
    print(f"✅ 新增 {added} 条, e30 曲库现有总计 {total} 条")
else:
    print("(干跑模式：未写库。加 --apply 执行合并写入)")
