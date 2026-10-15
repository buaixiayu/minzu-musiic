# -*- coding: utf-8 -*-
"""下载山河回响 e30 仫佬族曲库全部音频 -> 仫岭音集/assets/audio，并生成 songs.json
直链全部已过期，主要走 musicdl 按源重签；B站用官方 api(avid+bvid) 精确解析。"""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))                 # minzu-musiic/webui
ROOT = os.path.dirname(HERE)                                      # minzu-musiic
APP = os.path.join(os.path.dirname(ROOT), '仫岭音集')
AUDIO = os.path.join(APP, 'assets', 'audio')
E30 = os.path.join(ROOT, 'webui', 'ethnos_cache', 'e30_仫佬族.json')
FFMPEG = os.path.join(ROOT, 'venv', 'Scripts', 'ffmpeg.exe')
FFPROBE = os.path.join(ROOT, 'venv', 'Scripts', 'ffprobe.exe')
os.makedirs(AUDIO, exist_ok=True)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)

PROXY = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or ''
PROXIES = {'http': PROXY, 'https': PROXY} if PROXY else None
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

CLIENT_MAP = {'B站': 'BilibiliMusicClient', '酷我': 'KuwoMusicClient', '网易云': 'MyFreeMP3MusicClient',
              'MyFreeMP3': 'MyFreeMP3MusicClient', '酷狗音乐': 'KugouMusicClient',
              'TwoT58': 'TwoT58MusicClient', '微信公众号': 'WeixinMusicClient'}


def client_of(track):
    s = (track.get('_song') or {}).get('source') or ''
    if s.endswith('MusicClient'):
        return s
    s2 = track.get('source') or ''
    if s2.endswith('MusicClient'):
        return s2
    return CLIENT_MAP.get(track.get('source_cn', ''), CLIENT_MAP.get(s2, ''))


def core_title(name):
    m = re.findall(r'《([^》]{2,24})》', name or '')
    if m:
        t = m[-1]
        if len(t) >= 2:
            return t
    n = re.split(r'\s*[-—–｜|]\s*', name or '')[0]
    return n[:18]


def kws_for(track):
    name = track.get('song_name', '')
    singer = track.get('singers', '') or ''
    core = core_title(name)
    seen, out = set(), []
    for kw in [f'{core} {singer}'.strip(), core, f'{core} 仫佬', name[:16], name]:
        kw = kw.strip()
        if kw and kw not in seen:
            seen.add(kw); out.append(kw)
    return out


def probe_dur(path):
    try:
        out = subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
                              '-of', 'csv=p=0', path], capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip())
    except Exception:
        return 0.0


REF = {'bilivideo.com': 'https://www.bilibili.com/', 'akamaized.net': 'https://www.bilibili.com/',
       'music.126.net': 'https://music.163.com/', 'kuwo.cn': 'https://www.kuwo.cn/',
       'kugou.com': 'https://www.kugou.com/', 'gtimg.com': 'https://mp.weixin.qq.com/',
       '2t58.com': 'https://www.2t58.com/'}


def ref_for(url):
    host = urlparse(url).netloc
    for k, v in REF.items():
        if k in host:
            return v
    return 'https://www.bilibili.com/'


def dl(url, path, timeout=150):
    r = requests.get(url, headers={'User-Agent': UA, 'Referer': ref_for(url)},
                     proxies=PROXIES, stream=True, timeout=timeout)
    r.raise_for_status()
    n = 0
    with open(path, 'wb') as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk); n += len(chunk)
    return n


def to_mp3(src, dst):
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', src, '-vn', '-c:a', 'libmp3lame',
                    '-b:a', '320k', '-ar', '44100', '-ac', '2', dst], check=True)


def to_m4a(src, dst):
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', src, '-vn', '-c:a', 'aac',
                    '-b:a', '192k', dst], check=True)


def paths(i, ext):
    if ext == 'flac': return f'{i:03d}.flac', f'{i:03d}.mp3'
    if ext == 'mp4':  return f'{i:03d}.mp4', f'{i:03d}.m4a'
    if ext in ('m4a', 'mp3'): return f'{i:03d}.{ext}', f'{i:03d}.{ext}'
    return f'{i:03d}.bin', f'{i:03d}.m4a'


def finalize(tmp, final, ext):
    if ext == 'flac':
        to_mp3(tmp, final); os.remove(tmp)
    elif ext == 'mp4':
        to_m4a(tmp, final); os.remove(tmp)
    else:
        if os.path.abspath(tmp) != os.path.abspath(final):
            os.replace(tmp, final)
    return final


def bili_official(track):
    """B站：官方 api 按 avid+bvid 解析音频流"""
    s = track.get('_song') or {}
    avid, bvid = s.get('identifier'), track.get('album') or ''
    if not avid or not str(bvid).startswith('BV'):
        return None, None
    try:
        from musicdl.modules.sources import bilibili as bm
        b = bm.BilibiliMusicClient()
        res = b._parsewithofficialapiv1(
            search_result={'id': avid, 'bvid': bvid, 'author': track.get('singers', ''),
                           'pic': '', 'title': track.get('song_name', '')},
            song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides={})
        if isinstance(res, list):
            res = res[0] if res else None
        if res and getattr(res, 'download_url', None):
            return res.download_url, (res.ext or 'm4a').lower()
    except Exception as e:
        print(f'    bili-official err: {type(e).__name__} {str(e)[:80]}')
    return None, None


def search_fallback(track, client):
    from musicdl import musicdl
    import logging; logging.disable(logging.CRITICAL)
    c = musicdl.MusicClient(music_sources=[client],
                            init_music_clients_cfg={client: {'work_dir': 'downloads',
                                'search_size_per_source': 20, 'max_retries': 1}})
    name = track.get('song_name', '')
    singer = track.get('singers', '') or ''
    core = core_title(name)
    for kw in kws_for(track):
        try:
            songs = c.music_clients[client].search(keyword=kw, num_threadings=1,
                                                   request_overrides={}, rule={}) or []
        except Exception:
            continue
        best, best_score = None, 0
        for s in songs:
            sn, sg = (s.song_name or ''), (s.singers or '')
            score = 0
            if core and core in sn: score += 2
            if singer and (singer in sg or sg in singer): score += 2
            if core and sn[:4] == core[:4]: score += 1
            if score > best_score:
                best, best_score = s, score
            if best_score >= 4:
                break
        if best and best_score >= 2 and getattr(best, 'download_url', None):
            return best.download_url, (best.ext or '').lower(), best.song_name, best.singers
    return None, None, None, None


def fetch_one(i, track):
    nm = track.get('song_name', '')
    ext = (track.get('ext') or '').lower()
    _, finn = paths(i, ext)
    fin = os.path.join(AUDIO, finn)
    if os.path.exists(fin) and os.path.getsize(fin) > 20000:
        return i, True, fin
    client = client_of(track)
    # 候选 URL 序列：(url, ext, how)
    cands = []
    raw = (track.get('_song') or {}).get('download_url') or ''
    if raw and 'search.bilibili.com' not in raw and 'kugou.com/song' not in raw:
        cands.append((raw, ext, 'direct'))
    if client == 'BilibiliMusicClient':
        u, e = bili_official(track)
        if u:
            cands.append((u, e, 'bili-official'))
    if client:
        u, e, rn, rs = search_fallback(track, client)
        if u:
            cands.append((u, e, f'search:{str(rn)[:14]}|{str(rs)[:8]}'))
    if not cands:
        return i, False, f'no-url client={client}'
    last = 'none'
    for url, fext, how in cands:
        try:
            tmp = os.path.join(AUDIO, f'{i:03d}_src.{fext or ext or "mp3"}')
            if dl(url, tmp) <= 20000 or probe_dur(tmp) <= 5:
                if os.path.exists(tmp):
                    os.remove(tmp)
                last = f'bad-payload({how})'
                continue
            if os.path.exists(fin):
                os.remove(fin)
            return i, True, finalize(tmp, fin, fext or ext)
        except Exception as e:
            last = f'dl-err {type(e).__name__}({how})'
            continue
    return i, False, last


def main():
    only = None
    if len(sys.argv) > 1:
        only = set(int(x) for x in sys.argv[1].split(','))
    tracks = json.load(open(E30, encoding='utf-8'))['tracks']
    idxs = [i for i in range(1, len(tracks) + 1) if not only or i in only]
    print(f'e30 tracks: {len(tracks)}, processing {len(idxs)} -> {AUDIO}')
    ok, fail = 0, []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_one, i, tracks[i - 1]) for i in idxs]
        for fu in as_completed(futs):
            i, good, info = fu.result()
            try:
                sz = os.path.getsize(info) // 1024 if good else 0
            except Exception:
                sz = -1
            if good and sz > 0:
                ok += 1
                print(f'  [{i:02d}] OK {sz}KB  {tracks[i-1]["song_name"][:24]}')
            else:
                fail.append((i, info))
                print(f'  [{i:02d}] FAIL {info if not good else "vanished"}  {tracks[i-1]["song_name"][:24]}')
    print(f'\nok={ok} fail={len(fail)} elapsed={time.time()-t0:.0f}s')
    for i, r in fail:
        print(f'  FAIL {i:02d} :: {r}')
    # songs.json
    songs = []
    for i, t in enumerate(tracks, 1):
        f = next((f'{i:03d}.{e}' for e in ('mp3', 'm4a', 'flac', 'm4s', 'ogg', 'wav')
                  if os.path.exists(os.path.join(AUDIO, f'{i:03d}.{e}'))), None)
        if not f:
            continue
        p = os.path.join(AUDIO, f)
        songs.append({'idx': i, 'name': t.get('song_name', ''), 'singer': t.get('singers', ''),
                      'source': t.get('source_cn', ''), 'file': f'assets/audio/{f}',
                      'duration': round(probe_dur(p), 1), 'ext': f.rsplit('.', 1)[-1],
                      'identifier': str((t.get('_song') or {}).get('identifier') or ''),
                      'album': t.get('album') or ''})
    json.dump(songs, open(os.path.join(APP, 'assets', 'songs.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    total = sum(os.path.getsize(os.path.join(AUDIO, s['file'].split('/')[-1])) for s in songs)
    print(f'songs.json: {len(songs)}/63 entries, total {total/1048576:.1f} MB')
    miss = [i for i in range(1, 64) if i not in {s["idx"] for s in songs}]
    if miss:
        print('missing idx:', miss)


if __name__ == '__main__':
    main()
