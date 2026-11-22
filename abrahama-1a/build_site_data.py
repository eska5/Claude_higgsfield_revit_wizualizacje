"""Writes strona/a/data.js and strona/b/data.js: the four units, their floors and where they sit in the pictures.
Unit outlines come from plans.json (model metres) and are mapped onto the floor
cut-away frames with one affine fit taken from the building corners."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))


def to_frame(p):
    x, y = p
    return [round((22.87 * x + 3.61 * y + 688.4) / 16.0, 2), round((2.03 * x - 20.59 * y + 690.3) / 9.0, 2)]


def band(quad, z0, z1):
    """Storey band on the front facade. quad = the facade corners in the frame, per cent:
    bottom-left, bottom-right, top-right, top-left (ground to roof, 23.1 m)."""
    def at(lo, hi, z):
        t = z / 23.1
        return [round(lo[0] + (hi[0] - lo[0]) * t, 2), round(lo[1] + (hi[1] - lo[1]) * t, 2)]
    bl, br, tr, tl = quad
    return [at(bl, tl, z0), at(br, tr, z0), at(br, tr, z1), at(bl, tl, z1)]


# facade corners of the angled hero of version B, measured on the picture
QUAD_B = [[35.5, 50.5], [73.6, 64.2], [75.2, 26.1], [34.9, 21.9]]

UNITS = [
    dict(num='201', label='2.01 / 2.09', level='p1', area=211.72, type='Biuro z własną strefą wejściową',
         outline=[(-28.8, 0.4), (-13.1, 0.4), (-13.1, 23.1), (-28.8, 23.1)],
         lede='Narożny lokal na I piętrze, od frontu i od szczytu budynku, z oknami na trzy strony.'),
    dict(num='305', label='3.05', level='p2', area=120.40, type='Kameralne biuro',
         outline=[(4.0, 14.4), (18.5, 14.4), (18.5, 22.1), (13.0, 22.1), (13.0, 25.1), (4.0, 25.1)],
         lede='Kompaktowy lokal na II piętrze od strony torów, podzielony na trzy pokoje.'),
    dict(num='412', label='4.12', level='p3', area=179.51, type='Biuro narożne',
         outline=[(-28.8, 0.4), (-12.6, 0.4), (-12.6, 14.2), (-28.8, 14.2)],
         lede='Narożny lokal na III piętrze z frontowymi oknami, z open space i salą spotkań.'),
    dict(num='506', label='5.06 / 5.07', level='p4', area=383.78, type='Siedziba firmy',
         outline=[(-28.8, 0.4), (12.1, 0.4), (12.1, 12.6), (-28.8, 12.6)],
         lede='Największy lokal: ponad połowa frontu IV piętra, z open space, gabinetami i salami spotkań.'),
]
LEVELS = [('p1', 'I piętro', 'I', 4.6, 8.3), ('p2', 'II piętro', 'II', 8.3, 12.0), ('p3', 'III piętro', 'III', 12.0, 15.7), ('p4', 'IV piętro', 'IV', 15.7, 19.4)]

homes = []
for u in UNITS:
    poly = [to_frame(p) for p in u['outline']]
    pin = [round(sum(p[0] for p in poly) / len(poly), 2), round(sum(p[1] for p in poly) / len(poly), 2)]
    homes.append(dict(num=u['num'], label=u['label'], level=u['level'], type=u['type'], area=u['area'], lede=u['lede'], poly=poly, pin=pin))
ENTRANCE = dict(id='wejscie', nav='Wejście', button='Wejście główne', eyebrow='Od ulicy Abrahama', title='Wejście główne',
                alt='Wejście główne do biurowca Abrahama 1A',
                lede='Od furtki do drzwi prowadzi kamienny chodnik między dwoma parkingami: prywatnym po lewej i ogólnodostępnym po prawej. '
                     'Wjazd na każdy z nich prowadzi przez osobną bramę ze szlabanem.')
SECTION = dict(id='przekroj', nav='Przekrój', button='Zajrzyj do środka', eyebrow='Budynek w przekroju', title='Sześć kondygnacji i garaż',
               alt='Budynek Abrahama 1A przecięty wzdłuż frontu: wszystkie piętra i garaż podziemny',
               lede='Budynek otwarty wzdłuż frontu: parter, pięć pięter biur wokół klatki schodowej i wind, a pod nimi garaż z własnym zjazdem.',
               facts=[['Kondygnacje naziemne', '6'], ['Garaż', 'poziom −1'], ['Lokale w ofercie', 'piętra I–IV']])
GARAGE = dict(id='garaz', nav='Garaż', button='Garaż', eyebrow='Poziom −1', title='Garaż podziemny',
              alt='Garaż podziemny biurowca Abrahama 1A w przekroju',
              lede='Pod całym budynkiem: miejsca postojowe przy dwóch alejkach, pomieszczenia techniczne i zjazd rampą od strony parkingu.',
              facts=[['Wjazd', 'rampa przy szczycie budynku'], ['Dostęp', 'klatka schodowa i windy']])
VERSIONS = {
    'a': dict(quad=[[24.4, 51.3], [79.0, 51.3], [79.0, 12.7], [24.4, 12.7]], scenes=[ENTRANCE],
              times=[dict(id='day', label='Dzień', t=0.0), dict(id='dusk', label='Zmierzch', t=5.0)],
              intro=dict(eyebrow='Gdańsk · ul. Abrahama 1A · centrum biurowe',
                         lede='Biurowiec z piaskowca: parter i pięć pięter, garaż podziemny, dwa parkingi za szlabanami i zielony dziedziniec od ulicy.')),
    'b': dict(quad=QUAD_B, scenes=[SECTION, GARAGE, ENTRANCE], times=[dict(id='day', label='Dzień', t=0.0)], base='../a/assets/',
              own=['img/aerial-day.jpg'] + ['img/%s.jpg' % n for n in ('przekroj', 'garaz', 'wejscie')]
                  + ['video/loop-%s.mp4' % n for n in ('day', 'przekroj', 'garaz', 'wejscie')]
                  + [v for n in ('p1', 'p2', 'p3', 'p4', 'przekroj', 'garaz', 'wejscie') for v in ('video/aerial-to-%s.mp4' % n, 'video/%s-to-aerial.mp4' % n)],
              intro=dict(eyebrow='Gdańsk · ul. Abrahama 1A · centrum biurowe',
                         lede='Biurowiec z piaskowca: parter i pięć pięter, garaż podziemny, dwa parkingi za szlabanami. Zajrzyj do środka, zjedź do garażu albo wejdź do lokalu.')),
}
for key, ver in VERSIONS.items():
    levels = [dict(id=i, label=l, short=sh, homes=[h['num'] for h in homes if h['level'] == i], polys=[band(ver['quad'], z0, z1)]) for (i, l, sh, z0, z1) in LEVELS]
    tour = dict(name='Abrahama 1A', homes=homes, levels=levels, scenes=ver['scenes'], intro=ver['intro'],
                stats=dict(units=len(homes), smallest=min(h['area'] for h in homes), largest=max(h['area'] for h in homes), floors=6),
                times=ver['times'], timelapseLength=5.0)
    if 'base' in ver:
        tour.update(base=ver['base'], own=ver['own'])
    open(os.path.join(HERE, 'strona', key, 'data.js'), 'w', encoding='utf-8').write(
        '// Generated by build_site_data.py from the Revit model. Do not edit by hand.\nwindow.TOUR = ' + json.dumps(tour, ensure_ascii=False, separators=(',', ':')) + '\n')
print('ok')
