# -*- coding: utf-8 -*-
"""并行搜索各音乐平台中仫佬族相关歌曲。逐步落盘，单源超时保护。仅只读搜索。"""
import sys, os, json, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / 'webui'))
os.chdir(str(BASE / 'webui'))

from musicdl import musicdl

ETHNOS_SOURCES = ['MyFreeMP3MusicClient', 'MiguMusicClient', 'TwoT58MusicClient',
                  'KuwoMusicClient', 'KugouMusicClient', 'YinyuekuMusicClient',
                  'BilibiliMusicClient']
DB_DIR = BASE / 'downloads'
RAW = BASE / 'webui' / 'mulao_search_raw.json'

cfg = {}
for s in ETHNOS_SOURCES:
    c = {'work_dir': str(DB_DIR), 'search_size_per_source': 20, 'max_retries': 1}
    if s in {'KugouMusicClient', 'KuwoMusicClient'}:
        c['search_size_per_source'] = 30
    cfg[s] = c

client = musicdl.MusicClient(music_sources=ETHNOS_SOURCES, init_music_clients_cfg=cfg)

KEYWORDS = ['仫佬族', '仫佬族山歌', '仫佬族民歌', '依饭节', '古条歌', '罗城',
            '走坡', '墙贝歌', '仫佬族敬酒歌', '唱响山歌感党恩', '姚亮', '银悦西']

_lock = threading.Lock()
seen = set()
# 若已有部分结果则续接
if RAW.exists():
    try:
        for r in json.load(open(RAW, encoding='utf-8')):
            seen.add((r.get('song_name', '').strip(), r.get('singers', ''), r.get('src_client', '')))
    except Exception:
        pass
all_results = []
if RAW.exists():
    try:
        all_results = json.load(open(RAW, encoding='utf-8'))
    except Exception:
        all_results = []

def song_fields(s):
    d = {}
    for a in ['song_name', 'singers', 'source', 'source_cn', 'id', 'album',
             'protocol', 'ext', 'url', 'lyric', 'cover']:
        try:
            v = getattr(s, a, None)
            if v is not None:
                d[a] = v if isinstance(v, (str, int, float)) else str(v)
        except Exception:
            pass
    d['download_url'] = str(getattr(s, 'download_url', '') or '')
    return d

def search_source(kw, src):
    try:
        songs = client.music_clients[src].search(keyword=kw, num_threadings=1,
                                                 request_overrides={}, rule={}) or []
    except Exception:
        return []
    out = []
    for s in songs:
        f = song_fields(s)
        nm = (f.get('song_name') or '').strip()
        if not nm:
            continue
        f['kw'] = kw
        f['src_client'] = src
        out.append(f)
    return out

def search_keyword(kw):
    local = []
    with ThreadPoolExecutor(max_workers=len(ETHNOS_SOURCES)) as ex:
        futs = {ex.submit(search_source, kw, src): src for src in ETHNOS_SOURCES}
        for fu in as_completed(futs):
            try:
                local.extend(fu.result(timeout=90))
            except Exception:
                pass
    return local

t0 = time.time()
for kw in KEYWORDS:
    res = search_keyword(kw)
    with _lock:
        for f in res:
            key = (f.get('song_name', '').strip(), f.get('singers', ''), f.get('src_client', ''))
            if key in seen:
                continue
            seen.add(key)
            all_results.append(f)
        # 每个关键词完成即落盘
        json.dump(all_results, open(RAW, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"[done] kw={kw!r} 本词 {len(res)} 累计 {len(all_results)}  用时 {time.time()-t0:.1f}s", flush=True)

print("TOTAL unique:", len(all_results), "->", RAW)
from collections import defaultdict
sample = {}
for r in all_results:
    sc = r.get('src_client')
    if sc not in sample:
        sample[sc] = r
for sc, r in sample.items():
    print("SAMPLE", sc, "::", json.dumps(r, ensure_ascii=False)[:500])
