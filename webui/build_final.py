# -*- coding: utf-8 -*-
"""从原始搜索结果中筛选真正缺失的仫佬族歌曲，并为每首构造稳定的可播放链接。
阶段A: 严格相关性过滤 + 与现有曲库(及剔除名单)去重
阶段B: 对每条非bilibili候选，按其来源用曲名回查 identifier，构造精确歌曲页链接
"""
import json, re, sys, time
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

_alnum = re.compile(r'[\w\u4e00-\u9fff]+')
def norm(s):
    return ''.join(_alnum.findall(str(s).lower()))

def core_name(name):
    n = str(name).replace('《', '').replace('》', '')
    n = re.split(r'\s*[-—–]\s*', n)[0]
    n = re.split(r'[_】]', n)[0]
    for suf in ['mv', '高清版', '官方发布', '原创音乐mv', '原唱', '伴奏', '现场版',
               '好听视频', '好看视频', '完整版', '音乐mv', '（', '(', '【仫佬族】',
               '民族·', '唱民族·', '仫佬族', '仫佬']:
        n = n.replace(suf, '')
    return norm(n)

# 基线(现有53首)的 (core, singer) 与 (core,'')，以及所有基线 core 用于包含去重
baseline = set()
baseline_cores = set()
for t in e30['tracks']:
    c = core_name(t.get('song_name', ''))
    sg = norm(t.get('singers', ''))
    baseline.add((c, sg)); baseline.add((c, ''))
    if c:
        baseline_cores.add(c)

# 仫佬族专属账号：只发仫佬族内容，无仫佬字样也可信
MULAO_ACCOUNTS = {'仫佬余音', '广西罗城县文化馆', '哆哆唱国学'}
# 个体艺人：曲目庞杂，仅保留歌名含仫佬主题者
MULAO_ARTISTS = {'姚亮', '银悦西', '覃大军', '仫佬族姚亮', '雷佳'}
# 强主题词：歌名含这些即视为仫佬族歌曲
STRONG = ['仫佬', '依饭', '古条']
# “走坡”为多义泛词，仅当歌手为仫佬相关或歌名另有仫佬/罗城/民族字样时才算
MUSIC_TOKEN = re.compile(r'歌|唱|曲|乐|奏|山歌|民乐|mv|音乐|舞|戏|弹|乐器|演奏|录制')
NONSONG = re.compile(r'科普|了解|介绍|风俗|习惯|起源|关系|旅游|vlog|记录|听书|故事|'
                     r'解密|解读|盘点|冷知识|美食|美景|打卡|一分钟|为什么|如何|怎样|'
                     r'民族科普|篇\d|第\d+章|有声|喜马拉雅|简介|知多少|走进|探秘|'
                     r'我居然|第一次|减轻|疲劳|知乎|盘点')
AUDIOBOOK = re.compile(r'听书|有声|篇\d|第\d+章|喜马拉雅')

def is_mulao(name, singer):
    n = str(name); s = str(singer)
    if any(t in n for t in STRONG):
        return True
    if '走坡' in n and (s in MULAO_ACCOUNTS or s in MULAO_ARTISTS
                         or any(t in n for t in ['仫佬', '罗城', '民族'])):
        return True
    if s in MULAO_ACCOUNTS:
        return True
    if s in MULAO_ARTISTS and any(t in n for t in ['罗城', '民族']):
        return True
    return False

def bili_aid(du):
    m = re.search(r'/(\d{6,})/\1-', du or '')
    return m.group(1) if m else None

# 阶段A: 过滤 + 去重
phaseA = []
for r in raw:
    nm = (r.get('song_name') or '').strip()
    sg = (r.get('singers') or '').strip()
    sc = r.get('src_client', '')
    if not nm:
        continue
    c = core_name(nm); sgn = norm(sg)
    if (c, sgn) in baseline or (c, '') in baseline:
        continue
    # 包含去重：候选曲名是某基线曲名的子串(长度>=3)，视为同一首已收录
    if len(c) >= 3 and any(bc != c and c in bc for bc in baseline_cores):
        continue
    low = nm.lower()
    if any(d and (d == low or (len(d) >= 4 and d in low)) for d in deny):
        continue
    if not is_mulao(nm, sg):
        continue
    if AUDIOBOOK.search(nm) or AUDIOBOOK.search(sg) or '喜马拉雅' in sg:
        continue
    if sc == 'BilibiliMusicClient' and not MUSIC_TOKEN.search(nm):
        continue
    if sc == 'BilibiliMusicClient' and NONSONG.search(nm):
        continue
    phaseA.append({'song_name': nm, 'singers': sg, 'src_client': sc,
                   'source_cn': r.get('source_cn') or r.get('source') or '',
                   'download_url': r.get('download_url', '') or ''})

# 二次去重(同曲多名/多源)，保留首个
seen = set(); candidates = []
for c in phaseA:
    key = (core_name(c['song_name']), norm(c['singers']))
    if key in seen:
        continue
    seen.add(key); candidates.append(c)

print(f"raw={len(raw)}  阶段A过滤后={len(candidates)}")

# 阶段B: 回查 identifier 构造精确可播放链接
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(BASE / 'webui'))
os = __import__('os'); os.chdir(str(BASE / 'webui'))
from musicdl import musicdl
ETHNOS = ['MyFreeMP3MusicClient', 'MiguMusicClient', 'TwoT58MusicClient',
          'KuwoMusicClient', 'KugouMusicClient', 'YinyuekuMusicClient', 'BilibiliMusicClient']
cfg = {s: {'work_dir': str(BASE / 'downloads'), 'search_size_per_source': 5, 'max_retries': 1} for s in ETHNOS}
client = musicdl.MusicClient(music_sources=ETHNOS, init_music_clients_cfg=cfg)

SRC_LABEL = {'MyFreeMP3MusicClient': '网易云音乐', 'MiguMusicClient': '咪咕音乐',
             'KuwoMusicClient': '酷我音乐', 'KugouMusicClient': '酷狗音乐',
             'YinyuekuMusicClient': '音乐库', 'TwoT58MusicClient': '5sing/TwoT58',
             'BilibiliMusicClient': '哔哩哔哩'}

def exact_url(sc, name):
    try:
        songs = client.music_clients[sc].search(keyword=name, num_threadings=1,
                                                request_overrides={}, rule={}) or []
    except Exception:
        return '', ''
    for s in songs:
        sid = getattr(s, 'identifier', None)
        if not sid:
            continue
        # 校验回查结果与曲名一致，避免同名词串味
        rn = (getattr(s, 'song_name', '') or '')
        if name not in rn and rn not in name and core_name(name) not in core_name(rn):
            continue
        if sc == 'KuwoMusicClient':
            return f'https://www.kuwo.cn/play_detail/{sid}', '酷我音乐'
        if sc == 'KugouMusicClient':
            return f'https://www.kugou.com/song/#hash={sid}', '酷狗音乐'
        if sc == 'MiguMusicClient':
            return f'https://music.migu.cn/v3/music/song/{sid}', '咪咕音乐'
        if sc == 'MyFreeMP3MusicClient':
            return f'https://music.163.com/song?id={sid}', '网易云音乐'
        if sc == 'TwoT58MusicClient':
            return f'https://www.2t58.com/play/{sid}', '5sing'
        if sc == 'YinyuekuMusicClient':
            return f'https://www.yinyueku.com/song/{sid}.html', '音乐库'
    return '', ''

final = []
for c in candidates:
    sc = c['src_client']
    url, plat = '', SRC_LABEL.get(sc, c['source_cn'])
    if sc == 'BilibiliMusicClient':
        aid = bili_aid(c['download_url'])
        if aid:
            url = f'https://www.bilibili.com/video/av{aid}'; plat = '哔哩哔哩'
    else:
        url, p = exact_url(sc, c['song_name'])
        if p:
            plat = p
    if not url:
        # 兜底：平台搜索页(永久可播放)
        q = c['song_name']
        if sc == 'KuwoMusicClient': url = f'https://www.kuwo.cn/search/list?key={q}'
        elif sc == 'KugouMusicClient': url = f'https://www.kugou.com/search/?keyword={q}'
        elif sc == 'MiguMusicClient': url = f'https://music.migu.cn/v3/music/search?keyword={q}'
        elif sc == 'MyFreeMP3MusicClient': url = f'https://music.163.com/#/search/m/?s={q}'
        else: url = f'https://www.bilibili.com/search?keyword={q}'
    c['url'] = url; c['platform'] = plat
    final.append(c)
    print(f"  + {c['song_name'][:30]!r} | {c['singers'][:14]!r} | {plat} | {url[:60]}", flush=True)

json.dump(final, open(BASE / 'webui' / 'mulao_final.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print("\nFINAL new 仫佬族 songs:", len(final), "-> webui/mulao_final.json")
