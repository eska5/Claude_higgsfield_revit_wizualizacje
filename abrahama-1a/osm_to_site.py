# Converts an OpenStreetMap extract (Overpass JSON) around Abrahama 1A into
# model coordinates for build_abrahama.py and draws a debug map.
#   py osm_to_site.py <area.json> <site.json> <debug.png>
# Model frame (metres): X runs along the front facade (north-east is -X),
# Y points from the car park to the railway, front facade lies on Y = 0.
# Map data (c) OpenStreetMap contributors, ODbL.
import json, math, sys
from PIL import Image, ImageDraw

LAT0, LON0 = 54.392671, 18.5804234
TH = math.radians(42.9)
OFFY = 11.4
OFFICE = 103471012
R = 330.0


def model(la, lo):
    x = (lo - LON0) * 111320 * math.cos(math.radians(LAT0))
    y = (la - LAT0) * 111200
    u = x * math.cos(TH) + y * math.sin(TH)
    v = -x * math.sin(TH) + y * math.cos(TH)
    return (round(-u, 2), round(OFFY - v, 2))


d = json.load(open(sys.argv[1], encoding='utf-8'))
nodes = {e['id']: model(e['lat'], e['lon']) for e in d['elements'] if e['type'] == 'node'}
out = {'office': None, 'buildings': [], 'roads': [], 'rails': [], 'trams': [], 'fences': [],
       'walls': [], 'hedges': [], 'parking': [], 'grass': [], 'woods': [], 'pitches': [],
       'tracks': [], 'platforms': [], 'tree_rows': [], 'trees': [], 'water': [], 'embankments': []}

DEFAULT_H = {'roof': 4.0, 'garage': 2.8, 'garages': 2.8, 'shed': 2.6, 'outbuilding': 3.0,
             'service': 3.0, 'detached': 8.0, 'house': 8.0, 'semidetached_house': 8.0,
             'apartments': 16.0, 'retail': 6.0, 'commercial': 8.0, 'office': 14.0,
             'school': 12.0, 'university': 16.0, 'warehouse': 7.0, 'industrial': 7.0}
ROAD_W = {'primary': 10.5, 'primary_link': 6.0, 'tertiary': 7.0, 'residential': 6.0, 'service': 4.5,
          'footway': 2.0, 'path': 1.6, 'cycleway': 2.2, 'track': 3.0, 'steps': 2.0}


def near(pts):
    return any(abs(x) < R and abs(y) < R for x, y in pts)


for e in d['elements']:
    if e['type'] == 'node' and e.get('tags', {}).get('natural') == 'tree':
        p = nodes[e['id']]
        if near([p]):
            out['trees'].append(p)
    if e['type'] != 'way':
        continue
    t = e.get('tags', {})
    pts = [nodes[n] for n in e['nodes'] if n in nodes]
    if len(pts) < 2 or not near(pts):
        continue
    closed = pts[0] == pts[-1] and len(pts) > 3
    if e['id'] == OFFICE:
        out['office'] = pts[:-1]
    elif 'building' in t and closed:
        try:
            h = float(t['height']) if 'height' in t else float(t['building:levels']) * 3.3 + 0.8
        except Exception:
            h = DEFAULT_H.get(t['building'], 6.5)
        out['buildings'].append({'p': pts[:-1], 'h': h, 'kind': t['building'], 'roof': t.get('roof:shape', ''),
                                 'name': t.get('name', ''), 'id': e['id']})
    elif 'railway' in t:
        k = t['railway']
        if k == 'platform':
            out['platforms'].append({'p': pts[:-1] if closed else pts, 'closed': closed})
        elif k == 'rail':
            out['rails'].append({'p': pts, 'bridge': t.get('bridge', ''), 'emb': t.get('embankment', ''),
                                 'layer': t.get('layer', ''), 'service': t.get('service', '')})
        elif k == 'tram':
            out['trams'].append({'p': pts})
    elif 'highway' in t:
        k = t['highway']
        w = ROAD_W.get(k, 4.0)
        try:
            if 'lanes' in t:
                w = max(w, float(t['lanes']) * 3.3)
        except Exception:
            pass
        out['roads'].append({'p': pts, 'w': w, 'kind': k, 'area': bool(closed and t.get('area') == 'yes'),
                             'tunnel': t.get('tunnel', ''), 'bridge': t.get('bridge', ''), 'service': t.get('service', '')})
    elif t.get('barrier') == 'fence':
        out['fences'].append({'p': pts})
    elif t.get('barrier') in ('wall', 'retaining_wall'):
        out['walls'].append({'p': pts})
    elif t.get('barrier') == 'hedge':
        out['hedges'].append({'p': pts})
    elif t.get('amenity') == 'parking' and closed:
        out['parking'].append({'p': pts[:-1], 'surface': t.get('surface', '')})
    elif t.get('leisure') == 'pitch' and closed:
        out['pitches'].append({'p': pts[:-1], 'sport': t.get('sport', '')})
    elif t.get('leisure') == 'track' and closed:
        out['tracks'].append({'p': pts[:-1]})
    elif (t.get('landuse') == 'grass' or t.get('leisure') in ('garden', 'park') or t.get('natural') == 'grassland') and closed:
        out['grass'].append({'p': pts[:-1]})
    elif t.get('natural') in ('wood', 'scrub') and closed:
        out['woods'].append({'p': pts[:-1]})
    elif t.get('natural') == 'tree_row':
        out['tree_rows'].append({'p': pts})
    elif t.get('natural') == 'water' and closed:
        out['water'].append({'p': pts[:-1]})
    elif t.get('man_made') == 'embankment':
        out['embankments'].append({'p': pts})

json.dump(out, open(sys.argv[2], 'w'), separators=(',', ':'))
print({k: len(v) for k, v in out.items()})


def draw(path, half, sc):
    W = int(2 * half * sc)
    im = Image.new('RGB', (W, W), (236, 236, 228))
    dr = ImageDraw.Draw(im)

    def T(p):
        return ((p[0] + half) * sc, (half - p[1]) * sc)

    def poly(pts, fill, outline=None):
        dr.polygon([T(p) for p in pts], fill=fill, outline=outline)

    def line(pts, fill, w):
        dr.line([T(p) for p in pts], fill=fill, width=max(1, int(w * sc)))

    for g in out['grass']:
        poly(g['p'], (190, 220, 170))
    for g in out['woods']:
        poly(g['p'], (140, 190, 130))
    for g in out['parking']:
        poly(g['p'], (215, 205, 190), (150, 140, 120))
    for g in out['tracks']:
        poly(g['p'], (200, 110, 90))
    for g in out['pitches']:
        poly(g['p'], (120, 200, 110))
    for r in out['roads']:
        c = (120, 120, 125) if r['kind'] not in ('footway', 'path', 'steps', 'cycleway') else (200, 170, 150)
        if r['area']:
            poly(r['p'], c)
        else:
            line(r['p'], c, r['w'])
    for r in out['embankments']:
        line(r['p'], (60, 150, 60), 0.6)
    for r in out['trams']:
        line(r['p'], (160, 60, 160), 0.8)
    for r in out['rails']:
        line(r['p'], (20, 20, 20) if not r['bridge'] else (220, 0, 0), 1.2)
    for g in out['platforms']:
        if g['closed']:
            poly(g['p'], (170, 170, 200))
        else:
            line(g['p'], (170, 170, 200), 3)
    for b in out['buildings']:
        poly(b['p'], (200, 190, 185), (90, 80, 80))
    for f in out['fences']:
        line(f['p'], (0, 90, 200), 0.5)
    for f in out['walls']:
        line(f['p'], (200, 0, 200), 0.7)
    for f in out['hedges']:
        line(f['p'], (0, 140, 0), 1.0)
    for f in out['tree_rows']:
        line(f['p'], (0, 110, 0), 2.0)
    for p in out['trees']:
        x, y = T(p)
        dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(0, 110, 0))
    poly(out['office'], (240, 210, 150), (160, 60, 0))
    g = 50 if half > 150 else 10
    k = -int(half // g) * g
    while k <= half:
        col = (210, 210, 210) if k else (255, 120, 0)
        dr.line([T((k, -half)), T((k, half))], fill=col, width=1)
        dr.line([T((-half, k)), T((half, k))], fill=col, width=1)
        dr.text(T((k, -half + 14.0 / sc)), str(k), fill=(0, 0, 0))
        dr.text(T((-half + 2.0 / sc, k)), str(k), fill=(0, 0, 0))
        k += g
    if half < 150:
        for b in out['buildings']:
            cx = sum(p[0] for p in b['p']) / len(b['p'])
            cy = sum(p[1] for p in b['p']) / len(b['p'])
            if abs(cx) < half and abs(cy) < half:
                dr.text(T((cx - 3, cy)), '%g' % b['h'], fill=(120, 0, 0))
    im.save(path)


draw(sys.argv[3], 330, 2.4)
draw(sys.argv[3].replace('.png', '_near.png'), 100, 8)
