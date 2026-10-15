# -*- coding: utf-8 -*-
"""剔除与现有曲库重复的近似曲目(同歌手前缀匹配)，并校验每条链接可访问。"""
import json, re, sys, time
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent.parent
E30 = BASE / 'webui' / 'ethnos_cache' / 'e30_仫佬族.json'
SRC = BASE / 'webui' / 'mulao_final.json'

e30 = json.load(open(E30, encoding='utf-8'))
cands = json.load(open(SRC, encoding='utf-8'))

_alnum = re.compile(r'[\w\u4e00-\u9fff]+')
def norm(s):
    return ''.join(_alnum.findall(str(s).lower()))
def light_norm(name):
    s = re.sub(r'[【】()（）\s\-—–、，,。·:：]', '', str(name))
    return norm(s)

baseline = []
for t in e30['tracks']:
    baseline.append((light_norm(t.get('song_name', '')), norm(t.get('singers', ''))))

kept = []
dropped = []
for c in cands:
    cc = light_norm(c['song_name']); cs = norm(c['singers'])
    is_dup = False
    for bc, bs in baseline:
        if bs == cs and cc and bc and (cc in bc or bc in cc) and len(cc) >= 4 and len(bc) >= 4:
            is_dup = True; break
    if is_dup:
        dropped.append(c['song_name']); continue
    kept.append(c)

print("dropped as library-duplicate:", dropped)

# 校验链接可访问性
def check(url):
    try:
        req = urllib.request.Request(url, method='HEAD',
                                     headers={'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=15)
        return r.status
    except Exception as e:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            r = urllib.request.urlopen(req, timeout=15)
            return r.status
        except Exception as e2:
            return f"ERR:{type(e2).__name__}"

for c in kept:
    c['http_status'] = check(c['url'])
    print(f"  [{c['http_status']}] {c['song_name'][:30]} -> {c['url'][:60]}", flush=True)
    time.sleep(0.3)

json.dump(kept, open(BASE / 'webui' / 'mulao_curated.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print("\nCURATED new 仫佬族 songs:", len(kept), "-> webui/mulao_curated.json")
