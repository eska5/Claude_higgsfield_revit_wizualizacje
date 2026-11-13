"""Pick two camera spots per home from the ray-cast sight lines.

View A looks out toward the facade the home sits on, view B looks back in.
A spot needs clearance all round and the longest clear fan in its direction.
"""
import json, math, os
from proj import HERE, load

N = 12
ANG = [2 * math.pi * i / N for i in range(N)]


def fan(ds, i):
    vals = [ds[(i - 1) % N], ds[i], ds[(i + 1) % N]]
    return min(vals), sum(min(v, 45.0) for v in vals) / 3.0


def best(cands, axis, zone, facade_y, avoid=None):
    top = None
    for x, y, ds in cands:
        if min(ds) < 2.2:
            continue
        dist_to_facade = abs(y - facade_y)
        if zone == 'inner' and dist_to_facade < 12.0:
            continue
        if zone == 'outer' and dist_to_facade > 14.0:
            continue
        if avoid and math.hypot(x - avoid[0], y - avoid[1]) < 7.0:
            continue
        for i, a in enumerate(ANG):
            d = (math.cos(a), math.sin(a))
            if d[0] * axis[0] + d[1] * axis[1] < 0.80:
                continue
            lo, mean = fan(ds, i)
            if lo < 5.0:
                continue
            score = mean + 0.25 * ds[i]
            if top is None or score > top[0]:
                top = (score, x, y, a)
    return top


def main():
    out = {}
    for level in ['L2', 'L3', 'L4', 'L5']:
        data = load('rays_%s.json' % level)
        for num, room in sorted(data.items()):
            ymid = 0.5 * (room['bbmin'][1] + room['bbmax'][1])
            river = ymid > 5.0
            outward = (0.0, 1.0) if river else (0.0, -1.0)
            facade_y = room['bbmax'][1] if river else room['bbmin'][1]
            a = best(room['cands'], outward, 'inner', facade_y) or best(room['cands'], outward, 'any', facade_y)
            inward = (-outward[0], -outward[1])
            b = best(room['cands'], inward, 'outer', facade_y, avoid=(a[1], a[2]) if a else None) or best(room['cands'], inward, 'any', facade_y)
            views = {}
            for key, hit in (('a', a), ('b', b)):
                if hit:
                    views[key] = {'eye': [hit[1], hit[2], room['z']], 'dir': [round(math.cos(hit[3]), 4), round(math.sin(hit[3]), 4)], 'score': round(hit[0], 1)}
            out[num] = {'level': level, 'side': 'river' if river else 'street', 'views': views}
            print(num, level, out[num]['side'], {k: (v['eye'][:2], v['dir'], v['score']) for k, v in views.items()})
    with open(os.path.join(HERE, 'room_cams.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f)


if __name__ == '__main__':
    main()
