# Reads the vector floor plans (PDF, 1:200) of Abrahama 1A and writes plans.json
# in the model frame used by build_abrahama.py, plus debug images.
#   py -3.11 -E -P plans_to_json.py <pdf folder> <site.json> <plans.json> <debug dir>
# Layers in the PDFs, told apart by line weight:
#   1.01 / 0.86 black  wall faces (partitions / exterior)
#   0.58 black         door swings, windows, stairs
#   0.29 black         column hatching, label boxes
#   grey               furniture, ignored
import pymupdf, glob, os, math, json, re, sys
from shapely.geometry import LineString, Polygon, MultiPolygon, Point, box as sbox
from shapely.ops import unary_union, polygonize
from shapely import affinity
from PIL import Image, ImageDraw

PDF_DIR, SITE, OUT, DBG = sys.argv[1:5]
K = 0.0254 / 72 * 200            # metres per PDF point at 1:200
FILES = {'00': 'PIWNICA', '01': 'PARTER', '02': 'I PIETRO', '03': 'II PIETRO',
         '04': 'III PIETRO', '05': 'IV PIETRO', '06': 'V PIETRO'}


def load(key):
    f = [x for x in glob.glob(os.path.join(PDF_DIR, key + ' ABRAHAMA*.pdf'))][0]
    p = pymupdf.open(f)[0]
    M = p.rotation_matrix

    def T(pt):
        q = pymupdf.Point(pt) * M
        return (q.x * K, -q.y * K)

    segs, arcs = [], []
    for g in p.get_drawings():
        col = g.get('color') or (0, 0, 0)
        w = round(g.get('width') or 0, 2)
        c = round(col[0], 2)
        for it in g['items']:
            if it[0] == 'l':
                segs.append((T(it[1]), T(it[2]), w, c))
            elif it[0] == 'qu':
                q = it[1]
                pts = [T(q.ul), T(q.ur), T(q.lr), T(q.ll)]
                for i in range(4):
                    segs.append((pts[i], pts[(i + 1) % 4], w, c))
            elif it[0] == 'c':
                arcs.append(([T(it[1]), T(it[2]), T(it[3]), T(it[4])], w, c))
    words = []
    for (x0, y0, x1, y1, txt, *_r) in p.get_text('words'):
        # words come in the unrotated page space, like the drawings
        words.append((txt, T(((x0 + x1) / 2.0, (y0 + y1) / 2.0))))
    return segs, arcs, words


def length(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def wall_lines(segs):
    return [(a, b) for (a, b, w, c) in segs if c == 0 and w in (0.86, 1.01) and length(a, b) > 0.12]


def outline_of(segs):
    lines = [LineString([a, b]).buffer(0.12, cap_style=2) for (a, b, w, c) in segs
             if c == 0 and w in (0.86, 1.01, 0.58) and length(a, b) > 0.05]
    u = unary_union(lines)
    polys = list(u.geoms) if isinstance(u, MultiPolygon) else [u]
    big = max(polys, key=lambda g: Polygon(g.exterior).area)
    g = Polygon(big.exterior).buffer(-0.12, join_style=2)
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda q: q.area)
    return g


def shift(segs, arcs, words, dx, dy):
    S = [((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), w, c) for (a, b, w, c) in segs]
    A = [([(p[0] + dx, p[1] + dy) for p in pts], w, c) for (pts, w, c) in arcs]
    W = [(t, (p[0] + dx, p[1] + dy)) for (t, p) in words]
    return S, A, W


def bbox_blue(segs):
    xs = [v for (a, b, w, c) in segs if w == 0.86 and c == 0 for v in (a[0], b[0])]
    ys = [v for (a, b, w, c) in segs if w == 0.86 and c == 0 for v in (a[1], b[1])]
    return min(xs), min(ys), max(xs), max(ys)


def correlate(ref, mov, clip, xr=(-12.0, 12.0), yr=(-12.0, 12.0)):
    """Translation that best lays the wall lines of `mov` over `ref` (inside clip)."""
    def pts(lines, d):
        out = []
        for (a, b) in lines:
            n = max(1, int(length(a, b) / 0.1))
            for k in range(n + 1):
                t = k / float(n)
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        return out
    R = set()
    for (x, y) in pts(ref, 0):
        if clip.contains(Point(x, y)):
            R.add((int(round(x / 0.1)), int(round(y / 0.1))))
    P = pts(mov, 0)

    def score(dx, dy):
        n = 0
        for (x, y) in P:
            if (int(round((x + dx) / 0.1)), int(round((y + dy) / 0.1))) in R:
                n += 1
        return n
    best = (0, 0.0, 0.0)
    for dx in [xr[0] + i * 0.2 for i in range(int((xr[1] - xr[0]) / 0.2) + 1)]:
        for dy in [yr[0] + j * 0.2 for j in range(int((yr[1] - yr[0]) / 0.2) + 1)]:
            s = score(dx, dy)
            if s > best[0]:
                best = (s, dx, dy)
    s0, bx, by = best
    for dx in [bx + i * 0.05 for i in range(-8, 9)]:
        for dy in [by + j * 0.05 for j in range(-8, 9)]:
            s = score(dx, dy)
            if s > best[0]:
                best = (s, dx, dy)
    return best


# ---------------------------------------------------------------- alignment
data = {k: load(k) for k in FILES}
ref_bb = bbox_blue(data['02'][0])
shifts = {}
for k in ('01', '03', '04', '05', '06'):
    bb = bbox_blue(data[k][0])
    shifts[k] = (ref_bb[0] - bb[0], ref_bb[1] - bb[1])
# The basement sheet uses the same viewport as the ground floor sheet: the garage
# ramp sits at the same place on both pages, so it takes the ground floor shift.
# The basement sheet is drawn almost in the ground floor viewport; the ramp walls,
# which are the same walls on both sheets, give the remaining 0.18 / 2.42 m.
shifts['00'] = (shifts['01'][0] - 0.18, shifts['01'][1] - 2.42)
for k, (dx, dy) in shifts.items():
    data[k] = shift(*data[k], dx=dx, dy=dy)
    print('sheet %s shift %.2f %.2f' % (k, dx, dy))
outline = outline_of(data['02'][0])

# PDF frame -> model frame: front facade onto Y = 0, X chosen for best overlap with the map
site = json.load(open(SITE))
osm = Polygon(site['office'])
shell = outline.buffer(0.7, join_style=2).buffer(-0.7, join_style=2).simplify(0.3)
front_y, flen = None, 0.0
cs = list(shell.exterior.coords)
for i in range(len(cs) - 1):
    a, b = cs[i], cs[i + 1]
    if abs(a[1] - b[1]) < 0.05 and length(a, b) > flen:
        flen, front_y = length(a, b), (a[1] + b[1]) / 2.0
print('front edge %.2f m at y %.2f' % (flen, front_y))
best = None
for i in range(-200, 201):
    tx = -44.0 + i * 0.05
    g = affinity.translate(shell, xoff=tx, yoff=-front_y)
    iou = g.intersection(osm).area / g.union(osm).area
    if best is None or iou > best[0]:
        best = (iou, tx)
TX, TY = best[1], -front_y
print('model offset %.2f %.2f, overlap with map %.3f' % (TX, TY, best[0]))


def M(p):
    return (round(p[0] + TX, 3), round(p[1] + TY, 3))


# ---------------------------------------------------------------- walls
def angle(a, b):
    t = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
    return t


def pair_walls(lines, between_check):
    """Centre lines of walls drawn as two parallel faces 5-65 cm apart."""
    L = []
    for (a, b) in lines:
        t = angle(a, b)
        L.append((a, b, t))
    pieces = []
    n = len(L)
    for i in range(n):
        a, b, t = L[i]
        ux, uy = math.cos(math.radians(t)), math.sin(math.radians(t))
        nx, ny = -uy, ux
        si0, si1 = sorted((a[0] * ux + a[1] * uy, b[0] * ux + b[1] * uy))
        oi = a[0] * nx + a[1] * ny
        for j in range(i + 1, n):
            c, d, s = L[j]
            dt = abs(t - s)
            if min(dt, 180 - dt) > 1.0:
                continue
            oj = c[0] * nx + c[1] * ny
            off = oj - oi
            if not (0.05 < abs(off) < 0.65):
                continue
            sj0, sj1 = sorted((c[0] * ux + c[1] * uy, d[0] * ux + d[1] * uy))
            o0, o1 = max(si0, sj0), min(si1, sj1)
            if o1 - o0 < 0.2:
                continue
            mid = oi + off / 2.0
            pieces.append({'t': t, 'u': (ux, uy), 'n': (nx, ny), 'off': mid, 's0': o0, 's1': o1,
                           'th': abs(off), 'lo': min(oi, oj), 'hi': max(oi, oj)})
    # drop pieces that have another parallel face inside them (gaps between two walls)
    keep = []
    for p in pieces:
        bad = False
        for (a, b, t) in L:
            dt = abs(t - p['t'])
            if min(dt, 180 - dt) > 1.0:
                continue
            o = a[0] * p['n'][0] + a[1] * p['n'][1]
            if p['lo'] + 0.02 < o < p['hi'] - 0.02:
                s0, s1 = sorted((a[0] * p['u'][0] + a[1] * p['u'][1], b[0] * p['u'][0] + b[1] * p['u'][1]))
                if min(s1, p['s1']) - max(s0, p['s0']) > 0.15:
                    bad = True
                    break
        if not bad:
            keep.append(p)
    return keep


def merge(pieces, gap=0.06):
    groups = {}
    for p in pieces:
        k = (round(p['t'] / 1.0) % 180, round(p['off'] / 0.06), round(p['th'] / 0.05), p.get('g', 0))
        groups.setdefault(k, []).append(p)
    out = []
    for k, ps in groups.items():
        ps.sort(key=lambda p: p['s0'])
        cur = dict(ps[0])
        for p in ps[1:]:
            if p['s0'] <= cur['s1'] + gap:
                cur['s1'] = max(cur['s1'], p['s1'])
            else:
                out.append(cur)
                cur = dict(p)
        out.append(cur)
    return out


def ends(p):
    ux, uy = p['u']
    nx, ny = p['n']
    a = (ux * p['s0'] + nx * p['off'], uy * p['s0'] + ny * p['off'])
    b = (ux * p['s1'] + nx * p['off'], uy * p['s1'] + ny * p['off'])
    return a, b


# ---------------------------------------------------------------- doors
def bez(pts, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
    m = 1 - t
    return (m ** 3 * x0 + 3 * m * m * t * x1 + 3 * m * t * t * x2 + t ** 3 * x3,
            m ** 3 * y0 + 3 * m * m * t * y1 + 3 * m * t * t * y2 + t ** 3 * y3)


def circle3(p1, p2, p3):
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def door_arcs(arcs):
    """Door swings: circular arcs of 0.6-1.35 m radius spanning 60-100 degrees."""
    out = []
    for (pts, w, c) in arcs:
        if c != 0 or w not in (0.58, 0.14):
            continue
        fit = circle3(pts[0], bez(pts, 0.5), pts[3])
        if fit is None:
            continue
        h, r = fit
        if not (0.6 < r < 1.35):
            continue
        a0 = math.atan2(pts[0][1] - h[1], pts[0][0] - h[0])
        a1 = math.atan2(pts[3][1] - h[1], pts[3][0] - h[0])
        span = abs(math.degrees((a1 - a0 + math.pi) % (2 * math.pi) - math.pi))
        if not (60 < span < 100):
            continue
        out.append({'h': h, 'e': (pts[0], pts[3]), 'r': r})
    return out


def attach_doors(walls, doors):
    """Find the wall each door sits in and close the opening in that wall."""
    placed = []
    for dd in doors:
        h = dd['h']
        best = None
        for e in dd['e']:
            mid = ((h[0] + e[0]) / 2.0, (h[1] + e[1]) / 2.0)
            t = angle(h, e)
            for wi, p in enumerate(walls):
                dt = abs(t - p['t'])
                if min(dt, 180 - dt) > 7:
                    continue
                o = mid[0] * p['n'][0] + mid[1] * p['n'][1]
                if abs(o - p['off']) > p['th'] / 2.0 + 0.3:
                    continue
                s = mid[0] * p['u'][0] + mid[1] * p['u'][1]
                gap = max(p['s0'] - s, s - p['s1'], 0)
                if gap > 1.7:
                    continue
                score = abs(o - p['off']) + gap * 0.2
                if best is None or score < best[0]:
                    best = (score, wi, mid, e)
        if best is None:
            continue
        _, wi, mid, e = best
        p = walls[wi]
        s = mid[0] * p['u'][0] + mid[1] * p['u'][1]
        sh = h[0] * p['u'][0] + h[1] * p['u'][1]
        se = e[0] * p['u'][0] + e[1] * p['u'][1]
        lo, hi = min(sh, se), max(sh, se)
        placed.append({'wall': wi, 's': s, 'w': dd['r'], 'lo': lo, 'hi': hi, 'h': h})
    # extend walls across their door openings (CAD walls stop at the jambs)
    for d in placed:
        p = walls[d['wall']]
        p['s0'] = min(p['s0'], d['lo'] - 0.05)
        p['s1'] = max(p['s1'], d['hi'] + 0.05)
    # join collinear wall pieces of a wall split by one door
    return placed


# ---------------------------------------------------------------- columns
def columns(segs, outline):
    """Column squares: hatched (0.29) clusters inside the building."""
    hs = [(a, b) for (a, b, w, c) in segs if c == 0 and w == 0.29 and length(a, b) < 0.9]
    pts = []
    for (a, b) in hs:
        pts.append(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, a, b))
    cells = {}
    for (x, y, a, b) in pts:
        cells.setdefault((int(x / 0.6), int(y / 0.6)), []).append((a, b))
    seen = set()
    out = []
    inner = outline.buffer(-0.9)
    for key in cells:
        if key in seen:
            continue
        stack, comp = [key], []
        seen.add(key)
        while stack:
            k = stack.pop()
            comp += cells[k]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (k[0] + dx, k[1] + dy)
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
        xs = [v for (a, b) in comp for v in (a[0], b[0])]
        ys = [v for (a, b) in comp for v in (a[1], b[1])]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        if 0.25 < w < 0.85 and 0.25 < h < 0.85 and len(comp) >= 3 and inner.contains(Point(cx, cy)):
            out.append({'c': (cx, cy), 'w': w, 'h': h})
    return out


# ---------------------------------------------------------------- rooms
LABEL = re.compile(r'^\d\.(K\.)?\d{2}[A-Za-z]?(/\d\.\d{2}[A-Za-z]?)*$')
AREA = re.compile(r'^(\d+[.,]\d{2})m')


def rooms(words):
    labs, areas = [], []
    for (t, p) in words:
        if LABEL.match(t):
            labs.append((t, p))
        m = AREA.match(t)
        if m:
            areas.append((float(m.group(1).replace(',', '.')), p))
    out = []
    for (t, p) in labs:
        a = None
        for (v, q) in areas:
            if abs(q[0] - p[0]) < 2.5 and 0 < p[1] - q[1] < 1.6:
                a = v
        out.append({'label': t, 'p': p, 'area': a})
    return out


# ---------------------------------------------------------------- basement extras
def bay_numbers(words, segs):
    """Parking bays: their number sits in a 2.5 x 5 m box drawn in 0.14 lines."""
    out = []
    thin = [(a, b) for (a, b, w, c) in segs if c == 0 and w == 0.14 and 4.4 < length(a, b) < 6.2]
    for (t, p) in words:
        if not (re.match(r'^\d{1,2}$', t) and 1 <= int(t) <= 60):
            continue
        v = h = 0
        for (a, b) in thin:
            if LineString([a, b]).distance(Point(p)) < 2.6:
                if abs(a[0] - b[0]) < 0.03:
                    v += 1
                elif abs(a[1] - b[1]) < 0.03:
                    h += 1
        if v + h == 0:
            continue
        out.append((int(t), p, 'y' if v >= h else 'x'))
    return out


def column_squares(segs, keep):
    lines = [LineString([a, b]) for (a, b, w, c) in segs
             if c == 0 and w in (0.86, 1.01, 0.58) and length(a, b) > 0.05]
    out = []
    for pg in polygonize(unary_union(lines)):
        x0, y0, x1, y1 = pg.bounds
        w, h = x1 - x0, y1 - y0
        if 0.25 < w < 0.7 and abs(w - h) < 0.12 and pg.area / (w * h) > 0.85 and keep.contains(pg.centroid):
            out.append({'c': (pg.centroid.x, pg.centroid.y), 'w': w, 'h': h})
    return out



def extend_ends(walls, ext_line, reach=0.9, sep_reach=3.6):
    """Close small gaps: run each wall end on until it meets another wall or the
    centre line of the exterior wall, if that happens within `reach` metres."""
    from shapely.geometry import LineString as LS
    def stretched(w, e=0.6):
        a, b = w['a'], w['b']
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        return LS([(a[0] - ux * e, a[1] - uy * e), (b[0] + ux * e, b[1] + uy * e)])
    # targets run on a little past their ends so L-shaped corners close as well
    targets = [stretched(w) for w in walls]
    seps = []
    for i, w in enumerate(walls):
        for end in ('a', 'b'):
            p = w[end]
            q = w['b'] if end == 'a' else w['a']
            L = math.hypot(p[0] - q[0], p[1] - q[1])
            if L < 0.2:
                continue
            ux, uy = (p[0] - q[0]) / L, (p[1] - q[1]) / L
            ray = LS([(p[0] - ux * 0.02, p[1] - uy * 0.02), (p[0] + ux * sep_reach, p[1] + uy * sep_reach)])
            best = None
            cands = [(j, t) for j, t in enumerate(targets) if j != i]
            if ext_line is not None:
                cands.append((-1, ext_line))
            for j, t in cands:
                hit = ray.intersection(t)
                if hit.is_empty:
                    continue
                pts = [hit] if hit.geom_type == 'Point' else [g for g in getattr(hit, 'geoms', []) if g.geom_type == 'Point']
                for h in pts:
                    d = (h.x - p[0]) * ux + (h.y - p[1]) * uy
                    if d > 0.005 and (best is None or d < best[0]):
                        best = (d, j)
            if best is not None:
                d, j = best
                if d <= reach:
                    extra = (walls[j]['th'] / 2.0 if j >= 0 else 0.2) * 0.5
                    w[end] = (round(p[0] + ux * (d + extra), 3), round(p[1] + uy * (d + extra), 3))
                else:
                    # an opening without a door: close it for rooms with a separation line
                    seps.append([(round(p[0], 3), round(p[1], 3)),
                                 (round(p[0] + ux * d, 3), round(p[1] + uy * d, 3))])
    return seps


# ---------------------------------------------------------------- unit fit-out (grey layer)
def grey_wall_lines(segs):
    """Faces of the partitions inside the units; they sit on the grey arrangement layer."""
    return [(a, b) for (a, b, w, c) in segs if c > 0.8 and ((w == 1.01 and length(a, b) > 0.12) or (w == 0.14 and length(a, b) > 1.0))]


def leaf_doors(segs):
    """Doors drawn as an open leaf (0.72) with a thin line back to the other jamb."""
    leaves = [(a, b) for (a, b, w, c) in segs if c > 0.8 and w == 0.72 and 0.65 < length(a, b) < 1.15]
    thin = [(a, b) for (a, b, w, c) in segs if c > 0.8 and w not in (1.01, 0.72) and 0.5 < length(a, b) < 1.8]
    out = []
    for (p, q) in leaves:
        L = length(p, q)
        hit = None
        for (h, tip) in ((p, q), (q, p)):
            for (r, t) in thin:
                for (n0, n1) in ((r, t), (t, r)):
                    if length(tip, n0) < 0.09 and abs(length(h, n1) - L) < 0.2:
                        hit = (h, n1)
        if hit and not any(length(hit[0], o['h']) < 0.2 for o in out):
            out.append({'h': hit[0], 'e': (hit[1], hit[1]), 'r': L})
    return out


def wall_poly(w, grow=0.02):
    return LineString([w['a'], w['b']]).buffer(w['th'] / 2.0 + grow, cap_style=3)


def close_necks(free, r=0.7):
    """Split free space at openings narrower than 2r. Returns the room cores grown
    back to full size and one chord per opening, usable as a room separation line."""
    polys = list(free.geoms) if free.geom_type == 'MultiPolygon' else [free]
    comps, chords = [], []
    for F in polys:
        cores = F.buffer(-r, join_style=1)
        if cores.is_empty:
            continue
        cl = list(cores.geoms) if cores.geom_type == 'MultiPolygon' else [cores]
        grown = [c.buffer(r, join_style=1).intersection(F) for c in cl]
        comps += grown
        if len(grown) < 2:
            continue
        rest = F.difference(unary_union([g.buffer(0.01) for g in grown]))
        necks = list(rest.geoms) if rest.geom_type in ('MultiPolygon', 'GeometryCollection') else [rest]
        for n in necks:
            if n.is_empty or n.geom_type != 'Polygon' or n.area < 0.003:
                continue
            touch = [g for g in grown if g.distance(n) < 0.04]
            if len(touch) < 2:
                continue
            # The opening is roughly a rectangle: gap length by wall thickness. The
            # closing line runs through its middle along one of its two axes; the right
            # axis is the one whose ends land in walls on both sides.
            mrr = n.minimum_rotated_rectangle
            if mrr.geom_type != 'Polygon':
                continue
            cs = list(mrr.exterior.coords)
            c = n.centroid
            best = None
            for (p0, p1) in ((cs[0], cs[1]), (cs[1], cs[2])):
                d = length(p0, p1)
                if d < 0.02:
                    continue
                ux, uy = (p1[0] - p0[0]) / d, (p1[1] - p0[1]) / d
                probe = LineString([(c.x - ux * 4, c.y - uy * 4), (c.x + ux * 4, c.y + uy * 4)])
                cut = probe.intersection(n)
                if cut.is_empty:
                    continue
                parts = [g for g in (list(cut.geoms) if hasattr(cut, 'geoms') else [cut]) if g.geom_type == 'LineString']
                if not parts:
                    continue
                seg_ = max(parts, key=lambda g: g.length)
                (ax, ay), (bx, by) = seg_.coords[0], seg_.coords[-1]
                if (ax - c.x) * ux + (ay - c.y) * uy > 0:
                    (ax, ay), (bx, by) = (bx, by), (ax, ay)
                # test just past the jambs (a thin cross wall may be the jamb); the line
                # itself runs 0.2 m on so that it reaches the wall bodies in Revit
                if F.contains(Point(ax - ux * 0.05, ay - uy * 0.05)) or F.contains(Point(bx + ux * 0.05, by + uy * 0.05)):
                    continue                       # this axis runs along the passage, not across it
                if best is None or seg_.length < best[0]:
                    best = (seg_.length, (ax - ux * 0.2, ay - uy * 0.2), (bx + ux * 0.2, by + uy * 0.2))
            if best and 0.1 < best[0] < 2 * r + 0.8:
                chords.append([(round(best[1][0], 3), round(best[1][1], 3)), (round(best[2][0], 3), round(best[2][1], 3))])
    return comps, chords


def facade_openings(segs, shell_pts, to_model):
    """Windows read off the pier rhythm: hatched piers (0.29) along each outer wall,
    openings are the gaps between them."""
    hatch = [(to_model(a), to_model(b)) for (a, b, w, c) in segs if c == 0 and w == 0.29 and length(a, b) < 1.3]
    out = []
    n = len(shell_pts)
    poly = Polygon(shell_pts)
    for i in range(n):
        a, b = shell_pts[i], shell_pts[(i + 1) % n]
        L = length(a, b)
        if L < 2.0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -uy, ux
        if not poly.contains(Point((a[0] + b[0]) / 2.0 + nx * 0.3, (a[1] + b[1]) / 2.0 + ny * 0.3)):
            nx, ny = -nx, -ny
        iv = []
        for (p, q) in hatch:
            ok = True
            ss = []
            for t in (p, q):
                dn = (t[0] - a[0]) * nx + (t[1] - a[1]) * ny
                sv = (t[0] - a[0]) * ux + (t[1] - a[1]) * uy
                if not (-0.3 < dn < 0.85 and -0.2 < sv < L + 0.2):
                    ok = False
                ss.append(sv)
            if ok:
                iv.append((min(ss), max(ss)))
        iv.sort()
        piers = []
        for (s0, s1) in iv:
            if piers and s0 <= piers[-1][1] + 0.12:
                piers[-1][1] = max(piers[-1][1], s1)
            else:
                piers.append([s0, s1])
        piers = [p for p in piers if p[1] - p[0] > 0.2]
        if len(piers) < 2:
            continue
        gaps = []
        for j in range(len(piers) - 1):
            g0, g1 = piers[j][1], piers[j + 1][0]
            pier_before = piers[j][1] - piers[j][0]
            if 0.6 <= g1 - g0 <= 7.0:
                gaps.append([g0, g1, pier_before])
        merged = []
        for g in gaps:
            if merged and g[2] <= 0.45 and abs(g[0] - g[2] - merged[-1][1]) < 0.05 \
                    and g[1] - g[0] >= 1.5 and merged[-1][1] - merged[-1][0] >= 1.5:
                merged[-1][1] = g[1]            # a slim mullion between two tall lights: one bay
            else:
                merged.append([g[0], g[1]])
        for (g0, g1) in merged:
            sm = (g0 + g1) / 2.0
            out.append({'p': (round(a[0] + ux * sm, 3), round(a[1] + uy * sm, 3)), 'w': round(g1 - g0, 2)})
    return out

# ---------------------------------------------------------------- run
result = {'note': 'Model frame metres. Generated from the PDF floor plans by plans_to_json.py.',
          'offset': [TX, TY], 'floors': {}}
shell_m = [M(p) for p in list(shell.exterior.coords)[:-1]]
result['shell'] = shell_m
for k in FILES:
    segs, arcs, words = data[k]
    if k == '00':
        # garage outline: close the door gaps, keep the part around the garage centre
        lines = [LineString([a, b]).buffer(2.5, cap_style=2, join_style=2) for (a, b, w, c) in segs
                 if c == 0 and w in (0.86, 1.01) and length(a, b) > 0.3]
        u = unary_union(lines)
        polys = list(u.geoms) if isinstance(u, MultiPolygon) else [u]
        centre = Point(44.5, -23.0)          # garage centre in sheet coordinates
        bodies = [Polygon(g.exterior) for g in polys]
        ol = max(bodies, key=lambda q: q.area).buffer(-2.5, join_style=2)
        if isinstance(ol, MultiPolygon):
            ol = max(ol.geoms, key=lambda q: q.area)
    else:
        ol = outline
    ext_zone = ol.exterior.buffer(0.95)

    def keep(pieces, grey):
        out = []
        for p in pieces:
            a, b = ends(p)
            Ls = LineString([a, b])
            if p['s1'] - p['s0'] < 0.25:
                continue
            if grey:
                if not (0.04 <= p['th'] <= 0.3) or p['s1'] - p['s0'] < 0.4:
                    continue
            else:
                if p['th'] < 0.075:
                    continue
                if p['th'] > 0.3 and p['s1'] - p['s0'] < 0.9:
                    continue                               # column faces
            if k != '00' and ext_zone.contains(Ls):
                continue                                   # exterior walls come from the shell
            if not ol.buffer(0.3).contains(Ls) and k != '00':
                continue
            p['g'] = 1 if grey else 0
            out.append(p)
        return out

    walls = keep(merge(pair_walls(wall_lines(segs), None)), False)
    if k != '00':
        walls += keep(merge(pair_walls(grey_wall_lines(segs), None)), True)
    # furniture drawn like walls (reception desks, counters) stands free: keep only
    # fit-out walls that touch the building's own walls, directly or through each other
    if k != '00':
        geo = [LineString(ends(p)) for p in walls]
        anchored = [not p['g'] for p in walls]
        ring = ol.exterior
        changed = True
        while changed:
            changed = False
            for i, p in enumerate(walls):
                if anchored[i]:
                    continue
                if geo[i].distance(ring) < 0.75 or any(anchored[j] and geo[i].distance(geo[j]) < 0.3 for j in range(len(walls))):
                    anchored[i] = True
                    changed = True
        walls = [p for i, p in enumerate(walls) if anchored[i]]
    doors = door_arcs(arcs) + leaf_doors(segs)
    placed = attach_doors(walls, doors)
    walls = merge(walls, gap=0.35)
    placed = attach_doors(walls, doors)                    # again, on the merged walls
    cols = columns(segs, ol)
    labels = rooms(words)
    fl = {
        'walls': [{'a': M(ends(p)[0]), 'b': M(ends(p)[1]), 'th': round(p['th'], 3), 'g': p.get('g', 0)} for p in walls],
        'doors': [{'wall': d['wall'], 'p': M((d['s'] * walls[d['wall']]['u'][0] + walls[d['wall']]['off'] * walls[d['wall']]['n'][0],
                                              d['s'] * walls[d['wall']]['u'][1] + walls[d['wall']]['off'] * walls[d['wall']]['n'][1])),
                   'w': round(d['w'], 2), 'h': M(d['h'])} for d in placed],
        'columns': [{'c': M(c['c']), 'w': round(c['w'], 2), 'h': round(c['h'], 2)} for c in cols],
    }
    if k == '00':
        fl['outline'] = [M(p) for p in list(ol.simplify(0.1).exterior.coords)[:-1]]
        fl['bays'] = [{'n': n, 'p': M(p), 'axis': ax} for (n, p, ax) in bay_numbers(words, segs)]
        fl['columns'] = [{'c': M(c['c']), 'w': round(c['w'], 2), 'h': round(c['h'], 2)}
                         for c in column_squares(segs, ol.buffer(-0.5))]
    fl['lines'] = [[M(a), M(b), w] for (a, b, w, c) in segs if c == 0 and w in (0.58, 0.86, 1.01)]
    inner_poly = Polygon(shell_m).buffer(-0.4, join_style=2) if k != '00' else Polygon(fl['outline']).buffer(-0.25, join_style=2)
    extend_ends(fl['walls'], None if k == '00' else Polygon(shell_m).buffer(-0.2, join_style=2).exterior, 0.9, 0.9)
    # units: space cut by the building's own walls; rooms: cut by the fit-out as well
    hard = unary_union([wall_poly(w) for w in fl['walls'] if not w['g']] or [Point(1e6, 1e6).buffer(0.01)])
    every = unary_union([wall_poly(w) for w in fl['walls']] or [Point(1e6, 1e6).buffer(0.01)])
    # columns narrow the openings they stand in
    cols_u = unary_union([sbox(c['c'][0] - c['w'] / 2.0, c['c'][1] - c['h'] / 2.0, c['c'][0] + c['w'] / 2.0, c['c'][1] + c['h'] / 2.0)
                          for c in fl['columns']] or [Point(1e6, 1e6).buffer(0.01)])
    hard = hard.union(cols_u)
    every = every.union(cols_u)
    units, unit_chords = close_necks(inner_poly.difference(hard))
    rooms_g, chords = close_necks(inner_poly.difference(every))
    lab_m = [(r['label'], M(r['p']), r['area']) for r in labels]
    unit_of = []
    for u in units:
        ls = [(t, a) for (t, p, a) in lab_m if u.contains(Point(p))]
        unit_of.append(ls)
    # a compartment without its own label takes the label of the unit it opens into
    adj = {}
    for (ca, cb) in unit_chords:
        line = LineString([ca, cb])
        near = [j for j, u in enumerate(units) if u.distance(line) < 0.3]
        for j in near:
            adj.setdefault(j, set()).update(near)
    for it in range(4):
        for j, ls in enumerate(unit_of):
            if ls or units[j].area < 4:
                continue
            cands = [unit_of[m] for m in adj.get(j, ()) if m != j and unit_of[m]]
            cands.sort(key=lambda c: ('.K.' in c[0][0], -len(c)))
            if cands:
                unit_of[j] = [(cands[0][0][0], None)] if False else list(cands[0])
    seen_area = set()
    out_rooms, summary = [], {}
    outlines = []
    for g in rooms_g:
        if g.area < 1.2:
            continue
        # Revit closes a room only where walls really touch; small gaps at corners
        # leak. So every room also gets its own outline as room separation lines.
        gs = g.simplify(0.06)
        ring = gs.exterior if gs.geom_type == 'Polygon' else max(gs.geoms, key=lambda q: q.area).exterior
        rc = list(ring.coords)
        for i in range(len(rc) - 1):
            if length(rc[i], rc[i + 1]) > 0.04:
                outlines.append([(round(rc[i][0], 3), round(rc[i][1], 3)), (round(rc[i + 1][0], 3), round(rc[i + 1][1], 3))])
        rp = g.representative_point()
        ui = None
        for j, u in enumerate(units):
            if u.contains(rp):
                ui = j
        ls = unit_of[ui] if ui is not None else []
        label = '+'.join(t for (t, a) in ls) if ls else ''
        pa = sum(a for (t, a) in ls if a) if ls else None
        out_rooms.append({'label': label, 'p': (round(rp.x, 3), round(rp.y, 3)), 'model_area': round(g.area, 2),
                          'area': pa or None, 'bbox': [round(v, 2) for v in g.bounds]})
        if label:
            e = summary.setdefault(label, {'model_area': 0.0, 'area': pa or None, 'bbox': list(g.bounds), 'rooms': 0})
            e['model_area'] += g.area
            e['rooms'] += 1
            bb = e['bbox']
            e['bbox'] = [min(bb[0], g.bounds[0]), min(bb[1], g.bounds[1]), max(bb[2], g.bounds[2]), max(bb[3], g.bounds[3])]
    # the largest room of a unit carries the plain label
    for label in summary:
        rs = sorted([r for r in out_rooms if r['label'] == label], key=lambda r: -r['model_area'])
        for i, r in enumerate(rs):
            r['n'] = i + 1
        summary[label]['model_area'] = round(summary[label]['model_area'], 1)
        summary[label]['bbox'] = [round(v, 2) for v in summary[label]['bbox']]
    fl['rooms'] = out_rooms
    fl['units'] = summary
    fl['seps'] = outlines
    if k != '00':
        fl['openings'] = facade_openings(segs, shell_m, M)
    print('   units:', ', '.join('%s %.0f/%s' % (t, v['model_area'], ('%.0f' % v['area']) if v['area'] else '-')
                                 for t, v in sorted(summary.items())))
    result['floors'][k] = fl
    print(k, FILES[k], 'walls', len(fl['walls']), 'doors', len(fl['doors']), 'of', len(doors), 'arcs',
          'columns', len(fl['columns']), 'rooms', len(fl['rooms']), 'seps', len(fl['seps']), 'openings', len(fl.get('openings', [])))

    # debug image
    sc = 14
    W, H = int(95 * sc), int(50 * sc)
    im = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(im)
    T = lambda p: ((p[0] + 40) * sc, (35 - p[1]) * sc)
    dr.polygon([T(p) for p in shell_m], outline=(220, 140, 0))
    dr.polygon([T(p) for p in site['office']], outline=(160, 160, 255))
    for (a, b, w, c) in segs:
        if c == 0 and w in (0.86, 1.01):
            dr.line([T(M(a)), T(M(b))], fill=(205, 205, 205))
    for wl in fl['walls']:
        dr.line([T(wl['a']), T(wl['b'])], fill=(200, 0, 0) if not wl['g'] else (0, 0, 220), width=max(1, int(wl['th'] * sc)))
    for d in fl['doors']:
        x, y = T(d['p'])
        dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(0, 150, 0))
    for c in fl['columns']:
        x, y = T(c['c'])
        dr.rectangle((x - 3, y - 3, x + 3, y + 3), fill=(0, 0, 200))
    for r in fl['rooms']:
        dr.text(T(r['p']), r['label'], fill=(0, 0, 0))
    for (a, b) in fl['seps']:
        dr.line([T(a), T(b)], fill=(0, 170, 0), width=2)
    im.save(os.path.join(DBG, 'plan_%s.png' % k))

json.dump(result, open(OUT, 'w'), separators=(',', ':'))
print('written', OUT)
