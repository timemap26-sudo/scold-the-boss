#!/usr/bin/env python3
"""Pre-render every boss line in index.html with the free Microsoft Edge neural
Taiwan-Mandarin male voice (zh-TW-YunJheNeural) into voice/<hash>.mp3.

Usage:  pip install edge-tts && python3 tools/gen_voice.py
The file name is the FNV-1a hash of the spoken text, the same hash index.html
computes, so the page finds each clip without a manifest.
"""
import asyncio, os, re, sys
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'voice')
VOICE = 'zh-TW-YunJheNeural'
# Per-stage prosody (Edge TTS rate/pitch), matched to the boss's mood.
PROSODY = {
    'calm':      ('-8%',  '-6Hz'),
    'nervous':   ('+0%',  '-2Hz'),
    'sorry':     ('+12%', '+2Hz'),
    'sad':       ('-12%', '+0Hz'),
    'cry':       ('+5%',  '+6Hz'),
    'breakdown': ('+18%', '+10Hz'),
    'special':   ('+10%', '+2Hz'),
    'other':     ('+0%',  '-4Hz'),
}

def clean(s):  # same as index.html: drop stage directions in full-width parens
    return re.sub(r'（.*?）', '', s).strip()

def fnv(s):  # FNV-1a 32-bit over UTF-16 code units (matches JS charCodeAt)
    h = 0x811c9dc5
    b = s.encode('utf-16-le')
    for i in range(0, len(b), 2):
        u = b[i] | (b[i + 1] << 8)
        h ^= u
        h = (h * 0x01000193) & 0xffffffff
    return format(h, '08x')

def collect():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    items = {}
    for m in re.finditer(r"key: '(\w+)'.*?lines: \[(.*?)\]", src):
        for s in re.findall(r"'([^']+)'", m.group(2)):
            items.setdefault(clean(s), m.group(1))
    sp = re.search(r'const SPECIAL = \[(.*?)\n  \];', src, re.S).group(1)
    for m in re.finditer(r"lines: \[(.*?)\]", sp):
        for s in re.findall(r"'([^']+)'", m.group(1)):
            items.setdefault(clean(s), 'special')
    for s in re.findall(r"(?:say|speakLine)\('([^']+)'", src) + re.findall(r"rage >= 100 \? '([^']+)'", src):
        items.setdefault(clean(s), 'breakdown' if '崩潰' in s else 'other')
    return items

async def main():
    os.makedirs(OUT, exist_ok=True)
    items = collect()
    want = set()
    for text, mood in items.items():
        fn = os.path.join(OUT, fnv(text) + '.mp3'); want.add(os.path.basename(fn))
        if os.path.exists(fn) and '--force' not in sys.argv:
            continue
        rate, pitch = PROSODY[mood]
        await edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch,
                                   proxy=os.environ.get('HTTPS_PROXY')).save(fn)
        print(mood.ljust(10), fnv(text), text)
    for f in os.listdir(OUT):
        if f.endswith('.mp3') and f not in want:
            os.remove(os.path.join(OUT, f)); print('removed stale', f)
    print(len(items), 'lines')

asyncio.run(main())
