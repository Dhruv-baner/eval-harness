"""Assemble public/index.html: one self-contained file (fonts, styles, scripts and data inlined)."""
import base64, glob, json, os
from paths import RESULTS, PUBLIC, ROOT

UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
load = lambda n: json.load(open(os.path.join(RESULTS, n)))
res, ext = load('results.json'), load('extras.json')
for v in res['cleaners'].values():
    v['all'].pop('examples', None)
ext.pop('viewer', None)
data = dict(results=res, extras=ext, network=load('network.json'), audit=load('audit.json'), demo=load('demo.json'))
blob = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')

def font_face(file, family, weight, stretch=None):
    b64 = base64.b64encode(open(os.path.join(FONTS, file), 'rb').read()).decode()
    st = f'font-stretch:{stretch};' if stretch else ''
    return f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{b64}) format("woff2");font-weight:{weight};{st}font-style:normal;font-display:swap}}\n'

css = font_face('archivo-latin-wdth-normal.woff2', 'Archivo', '100 900', '62% 125%')
for w in (400, 500, 600):
    css += font_face(f'ibm-plex-mono-latin-{w}-normal.woff2', 'Plex Mono', str(w))
css += open(os.path.join(UI, 'style.css'), encoding='utf-8').read()
js = ''.join(open(os.path.join(UI, f), encoding='utf-8').read() + '\n' for f in ('a_core.js', 'b_console.js', 'c1_sections.js', 'c2_sections.js', 'd_boot.js')).replace('/*__DATA__*/', blob)
js = js.replace('</script', '<\\/script')
html = open(os.path.join(UI, 'shell.html'), encoding='utf-8').read().replace('/*__CSS__*/', css).replace('/*__JS__*/', js)
os.makedirs(PUBLIC, exist_ok=True)
open(os.path.join(PUBLIC, 'index.html'), 'w', encoding='utf-8').write(html)
print('wrote public/index.html', round(len(html) / 1024), 'KB')
