# Builds the Abrahama 1A office building (Gdansk) with its surroundings in the
# open "Abrahama_1A" Revit document. Run inside Revit (IronPython):
#   STAGES = ['site', 'shell', 'interior']   # optional, default = all
#   exec(open(r'<this file>').read())
# The footprint and the surroundings come from OpenStreetMap (site.json, made by
# osm_to_site.py). Facades, storey heights and the interior layout are estimated
# from drone footage and one letting plan, not surveyed.
# Units below are metres. X runs along the front facade (north-east is -X),
# Y points from the car park to the railway, the front facade lies on Y = 0.
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from System.Collections.Generic import List
import math, json, os

app = __revit__.Application
doc = [d for d in app.Documents if d.Title == 'Abrahama_1A'][0]
HERE = r'C:\Users\USER\Documents\GitHub\AdventOfCode\Claude_higgsfield_revit\abrahama-1a'
SITE = json.load(open(os.path.join(HERE, 'site.json')))
try:
    STAGES
except NameError:
    STAGES = ['site', 'shell', 'interior']
F = 0.3048
LOG = []

FL = [0.0, 4.6, 8.3, 12.0, 15.7, 19.4]   # ground floor + 5 upper floors
TOP = 23.1
LEVEL_NAMES = ['Parter', 'Pietro 1', 'Pietro 2', 'Pietro 3', 'Pietro 4', 'Pietro 5', 'Dach']
EH = 7.0     # height of the railway embankment
# Garage ramp: centre line (x, y, z). It leaves the car park, runs down beside the
# south-west end and turns left under the slanted end facade of the building.
RAMP_PATH = [(43.6, -13.0, 0.0), (43.9, -6.0, -0.4), (44.4, 3.5, -1.8), (42.3, 8.4, -2.5),
             (38.9, 10.3, -2.9), (34.4, 12.35, -3.0), (32.4, 13.3, -3.0)]
FACE_DIR = (0.719, 0.695)      # direction of the slanted south-west end facade
RW = 2.7       # half width of the carriageway
RAMP_D = 3.0


def P(x, y, z=0.0):
    return XYZ(x / F, y / F, z / F)


_seed = [20250911]


def rnd():
    _seed[0] = (_seed[0] * 1103515245 + 12345) % 2147483648
    return _seed[0] / 2147483648.0


# ---------------------------------------------------------------- materials
MATS = {}
MAT_DEF = {
    'A1A Piaskowiec': (228, 212, 176, 0),
    'A1A Piaskowiec ciemny': (206, 188, 152, 0),
    'A1A Szklo': (38, 62, 84, 0),
    'A1A Szklo kurtynowe': (30, 50, 70, 0),
    'A1A Slusarka': (96, 102, 110, 0),
    'A1A Dach': (62, 66, 72, 0),
    'A1A Blacha': (176, 182, 188, 0),
    'A1A Teren': (186, 182, 170, 0),
    'A1A Trawa': (104, 146, 70, 0),
    'A1A Trawa boisko': (88, 170, 72, 0),
    'A1A Bruk': (192, 164, 146, 0),
    'A1A Bruk jasny': (216, 204, 186, 0),
    'A1A Bruk szary': (168, 152, 140, 0),
    'A1A Asfalt': (84, 86, 90, 0),
    'A1A Chodnik': (176, 172, 166, 0),
    'A1A Parking': (150, 148, 144, 0),
    'A1A Tartan': (176, 78, 64, 0),
    'A1A Tluczen': (128, 118, 108, 0),
    'A1A Stal': (58, 60, 64, 0),
    'A1A Plot': (40, 42, 46, 35),
    'A1A Beton': (198, 196, 190, 0),
    'A1A Tynk bialy': (236, 234, 228, 0),
    'A1A Tynk szary': (160, 164, 168, 0),
    'A1A Dachowka': (196, 150, 104, 0),
    'A1A Korona': (62, 110, 56, 0),
    'A1A Korona 2': (84, 128, 62, 0),
    'A1A Korona 3': (104, 140, 70, 0),
    'A1A Iglak': (38, 82, 56, 0),
    'A1A Pien': (92, 72, 54, 0),
    'A1A Zywoplot': (72, 120, 58, 0),
    'A1A Auto bialy': (238, 238, 238, 0),
    'A1A Auto czarny': (34, 36, 40, 0),
    'A1A Auto szary': (132, 136, 142, 0),
    'A1A Auto czerwony': (176, 44, 48, 0),
    'A1A Auto niebieski': (52, 84, 136, 0),
    'A1A Ceglany': (176, 86, 58, 0),
}


def make_materials():
    existing = {}
    for m in FilteredElementCollector(doc).OfClass(Material):
        existing[m.Name] = m
    for name, (r, g, b, tr) in MAT_DEF.items():
        m = existing.get(name)
        if m is None:
            m = doc.GetElement(Material.Create(doc, name))
        m.Color = Color(r, g, b)
        m.Transparency = tr
        m.Shininess = 90 if 'Szklo' in name else 20
        MATS[name] = m.Id


# ------------------------------------------------------------ solid helpers
BUCKET = {}
FAIL = {}


def opts(mat):
    return SolidOptions(MATS[mat], ElementId.InvalidElementId)


def add(cat, name, solid):
    if solid is not None:
        BUCKET.setdefault((cat, name), []).append(solid)


def fail(what):
    FAIL[what] = FAIL.get(what, 0) + 1


def clean(pts, tol=0.015):
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append((float(p[0]), float(p[1])))
    while len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def area2(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a


def ccw(pts):
    pts = clean(pts)
    if area2(pts) < 0:
        pts.reverse()
    return pts


def loop3(pts3):
    cl = CurveLoop()
    n = len(pts3)
    for i in range(n):
        cl.Append(Line.CreateBound(pts3[i], pts3[(i + 1) % n]))
    return cl


def poly(pts, z0, z1, mat, what='poly'):
    """Vertical extrusion of a plan polygon."""
    pts = ccw(pts)
    if len(pts) < 3 or abs(area2(pts)) < 1e-4:
        return None
    try:
        return GeometryCreationUtilities.CreateExtrusionGeometry(
            List[CurveLoop]([loop3([P(x, y, z0) for (x, y) in pts])]), XYZ.BasisZ, (z1 - z0) / F, opts(mat))
    except Exception:
        fail(what)
        return None


def box(x0, y0, z0, x1, y1, z1, mat):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, 'box')


def seg(a, b, w, z0, z1, mat, ext=0.0):
    """A strip of width w from plan point a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 0.05:
        return None
    ux, uy = dx / L, dy / L
    nx, ny = -uy * w / 2.0, ux * w / 2.0
    ax, ay = a[0] - ux * ext, a[1] - uy * ext
    bx, by = b[0] + ux * ext, b[1] + uy * ext
    return poly([(ax - nx, ay - ny), (bx - nx, by - ny), (bx + nx, by + ny), (ax + nx, ay + ny)], z0, z1, mat, 'seg')


def sweep(a, b, profile, mat):
    """Extrude a (lateral, z) profile from plan point a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 0.2:
        return None
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    pts = [P(a[0] + nx * l, a[1] + ny * l, z) for (l, z) in profile]
    for attempt in (0, 1):
        try:
            return GeometryCreationUtilities.CreateExtrusionGeometry(
                List[CurveLoop]([loop3(pts)]), XYZ(ux, uy, 0), L / F, opts(mat))
        except Exception:
            pts.reverse()
    fail('sweep')
    return None


def arched_panel(xc, w, z0, zs, zp, yface, mat, t=0.07):
    x0, x1 = xc - w / 2.0, xc + w / 2.0
    cl = CurveLoop()
    a, b, c, d = P(x0, yface, z0), P(x1, yface, z0), P(x1, yface, zs), P(x0, yface, zs)
    cl.Append(Line.CreateBound(a, b))
    cl.Append(Line.CreateBound(b, c))
    cl.Append(Arc.Create(c, d, P(xc, yface, zp)))
    cl.Append(Line.CreateBound(d, a))
    return GeometryCreationUtilities.CreateExtrusionGeometry(
        List[CurveLoop]([cl]), XYZ.BasisY.Negate(), t / F, opts(mat))


def revolve(profile_rz, mat):
    """Revolve a closed (r, z) profile about the Z axis."""
    fr = Frame(XYZ.Zero, XYZ.BasisX, XYZ.BasisY, XYZ.BasisZ)
    pts = [XYZ(r / F, 0, z / F) for (r, z) in profile_rz]
    for attempt in (0, 1):
        try:
            return GeometryCreationUtilities.CreateRevolvedGeometry(
                fr, List[CurveLoop]([loop3(pts)]), 0.0, 2 * math.pi, opts(mat))
        except Exception:
            pts.reverse()
    return None


def sphere(r, mat):
    fr = Frame(XYZ.Zero, XYZ.BasisX, XYZ.BasisY, XYZ.BasisZ)
    top, bot, mid = XYZ(0, 0, r / F), XYZ(0, 0, -r / F), XYZ(r / F, 0, 0)
    for flip in (False, True):
        try:
            cl = CurveLoop()
            if not flip:
                cl.Append(Arc.Create(bot, top, mid))
                cl.Append(Line.CreateBound(top, bot))
            else:
                cl.Append(Line.CreateBound(bot, top))
                cl.Append(Arc.Create(top, bot, mid))
            return GeometryCreationUtilities.CreateRevolvedGeometry(
                fr, List[CurveLoop]([cl]), 0.0, 2 * math.pi, opts(mat))
        except Exception:
            pass
    return None


def moved(solid, x, y, z):
    return SolidUtils.CreateTransformed(solid, Transform.CreateTranslation(P(x, y, z)))


def inside(pt, pts):
    x, y = pt
    c = False
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def inset(pts, d):
    """Offset a counter-clockwise polygon inwards by d."""
    n = len(pts)
    lines = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        lines.append((x0 + nx * d, y0 + ny * d, x1 - x0, y1 - y0))
    out = []
    for i in range(n):
        ax, ay, adx, ady = lines[i - 1]
        bx, by, bdx, bdy = lines[i]
        den = adx * bdy - ady * bdx
        if abs(den) < 1e-9:
            out.append((bx, by))
        else:
            t = ((bx - ax) * bdy - (by - ay) * bdx) / den
            out.append((ax + adx * t, ay + ady * t))
    return out


# The map draws a 6 m step at the south-west end; the drone footage shows one
# slanted end facade there instead, so that vertex is dropped.
OFFICE = ccw([p for p in SITE['office'] if not (abs(p[0] - 32.98) < 0.6 and abs(p[1] - 5.45) < 0.6)])


def dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dy * t)


def in_ramp(p, m=1.0):
    d = min(dist_seg(p, RAMP_PATH[i], RAMP_PATH[i + 1]) for i in range(len(RAMP_PATH) - 1))
    return d < RW + 0.4 + m


def fence_gate():
    """Where the entrance axis (X = 0) crosses the fence along the street."""
    for f in SITE['fences']:
        pts = f['p']
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a[0] * b[0] <= 0 and a[0] != b[0] and -55 < a[1] < -25 and -55 < b[1] < -25:
                t = -a[0] / (b[0] - a[0])
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                return (0.0, a[1] + (b[1] - a[1]) * t, (b[0] - a[0]) / L, (b[1] - a[1]) / L)
    return (0.0, -40.0, 1.0, 0.0)


GATE = fence_gate()
GATE_HALF = 2.3
# vehicle gates with a barrier: (x, y, direction of the fence line)
VGATES = [(-43.9, -21.8, 0.943, -0.333), (42.05, -52.15, 0.936, -0.353)]
VGATE_HALF = 3.1
OWN_PARK = []
for _g in SITE['parking']:
    if inside((20.0, -11.0), _g['p']):
        OWN_PARK = ccw(_g['p'])
ROADS_NEAR = []
for _r in SITE['roads']:
    if _r['area'] or _r['tunnel']:
        continue
    _walk = _r['kind'] in ('footway', 'path', 'steps', 'cycleway', 'pedestrian')
    for _i in range(len(_r['p']) - 1):
        _a, _b = _r['p'][_i], _r['p'][_i + 1]
        if min(math.hypot(_a[0], _a[1]), math.hypot(_b[0], _b[1])) < 260:
            ROADS_NEAR.append((_a, _b, _r['w'] / 2.0 + (0.3 if _walk else 0.5)))


def on_road(p):
    """True on a carriageway, a pavement, the car park or the entrance path."""
    if OWN_PARK and inside(p, OWN_PARK):
        return True
    if abs(p[0]) < 2.2 and GATE[1] - 1 < p[1] < 0:
        return True
    for (a, b, lim) in ROADS_NEAR:
        if abs(p[0] - a[0]) < 40 and abs(p[1] - a[1]) < 40 and dist_seg(p, a, b) < lim:
            return True
    return False


def gate_clear(p):
    """True where no fence may stand: the pedestrian gate, the vehicle gates."""
    dx, dy = p[0] - GATE[0], p[1] - GATE[1]
    along = dx * GATE[2] + dy * GATE[3]
    perp = abs(dx * GATE[3] - dy * GATE[2])
    if abs(along) < GATE_HALF + 0.9 and perp < 1.0:
        return True
    if math.hypot(dx, dy) < 8.0 and perp > 0.6:
        return True
    for (x, y, ux, uy) in VGATES:
        if math.hypot(p[0] - x, p[1] - y) < VGATE_HALF + 0.3:
            return True
    return False


def fence_y(x):
    """Line of the plot fence along Abrahama street."""
    if x < 0:
        return -21.8 + (x + 43.9) * (-36.2 + 21.8) / (-3.2 + 43.9)
    return -38.5 + (x - 3.3) * (-51.0 + 38.5) / (39.0 - 3.3)


_zc = [0]


def zstep():
    """Tiny height offsets so overlapping ground layers do not flicker."""
    _zc[0] = (_zc[0] + 1) % 24
    return _zc[0] * 0.0004


def blocked(p, m=1.5):
    """True where plants and cars must not go: the office, the ramp."""
    if in_ramp(p, m):
        return True
    return inside(p, OFFICE) or inside((p[0], p[1] - m), OFFICE) or inside((p[0], p[1] + m), OFFICE) \
        or inside((p[0] - m, p[1]), OFFICE) or inside((p[0] + m, p[1]), OFFICE)


# --------------------------------------------------------------- the site
CAR_COLS = ['A1A Auto bialy', 'A1A Auto czarny', 'A1A Auto szary', 'A1A Auto szary',
            'A1A Auto czarny', 'A1A Auto bialy', 'A1A Auto czerwony', 'A1A Auto niebieski']


def car(x, y, ang, z=0.0):
    """A parked car at (x, y); ang = direction of its long axis in degrees."""
    m = CAR_COLS[int(rnd() * len(CAR_COLS))]
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a = (x - ux * 2.2, y - uy * 2.2)
    b = (x + ux * 2.2, y + uy * 2.2)
    add('car', 'Auta', seg(a, b, 1.8, z + 0.25, z + 0.95, m))
    a2 = (x - ux * 1.2, y - uy * 1.2)
    b2 = (x + ux * 1.4, y + uy * 1.4)
    add('car', 'Auta', seg(a2, b2, 1.6, z + 0.95, z + 1.45, 'A1A Auto czarny'))


def street_y(x):
    """Approximate line of the fence between the plot and Abrahama street."""
    return -34.0 - 0.34 * x


def build_ground():
    terrain = box(-340, -340, -6.0, 340, 340, 0.0, 'A1A Teren')
    for i in range(len(RAMP_PATH) - 1):
        cut = seg(RAMP_PATH[i], RAMP_PATH[i + 1], 2 * RW + 0.6, -RAMP_D - 0.5, 0.6, 'A1A Teren', RW * 0.6)
        try:
            terrain = BooleanOperationsUtils.ExecuteBooleanOperation(terrain, cut, BooleanOperationsType.Difference)
        except Exception as ex:
            LOG.append('terrain cut %d failed: %s' % (i, ex))
    add('site', 'Teren', terrain)
    for g in SITE['grass']:
        add('site', 'Trawniki', poly(g['p'], 0.0, 0.02 + zstep(), 'A1A Trawa', 'grass'))
    for g in SITE['woods']:
        add('site', 'Trawniki', poly(g['p'], 0.0, 0.02 + zstep(), 'A1A Trawa', 'grass'))
    for g in SITE['pitches']:
        add('site', 'Boiska', poly(g['p'], 0.03, 0.07, 'A1A Trawa boisko', 'pitch'))
    for g in SITE['parking']:
        cx = sum(p[0] for p in g['p']) / len(g['p'])
        cy = sum(p[1] for p in g['p']) / len(g['p'])
        own = -55 < cx < 40 and -45 < cy < 0
        add('site', 'Parkingi', poly(g['p'], 0.0, 0.034 + zstep(), 'A1A Bruk' if own else 'A1A Parking', 'parking'))
        if not own and math.hypot(cx, cy) < 230:
            fill_parking(g['p'])
    # running track around the rugby pitch north of the railway
    big = None
    for g in SITE['pitches']:
        if big is None or abs(area2(g['p'])) > abs(area2(big)):
            big = g['p']
    if big:
        cx = sum(p[0] for p in big) / len(big)
        cy = sum(p[1] for p in big) / len(big)
        ring = [(cx + (p[0] - cx) * 1.24, cy + (p[1] - cy) * 1.3) for p in big]
        add('site', 'Boiska', poly(ring, 0.0, 0.05, 'A1A Tartan', 'pitch'))


def fill_parking(pts):
    """Scatter parked cars on a grid aligned with the longest edge of a car park."""
    pts = ccw(pts)
    best, ang = 0.0, 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        L = math.hypot(x1 - x0, y1 - y0)
        if L > best:
            best, ang = L, math.atan2(y1 - y0, x1 - x0)
    ca, sa = math.cos(ang), math.sin(ang)
    loc = [(p[0] * ca + p[1] * sa, -p[0] * sa + p[1] * ca) for p in pts]
    u0, u1 = min(p[0] for p in loc), max(p[0] for p in loc)
    v0, v1 = min(p[1] for p in loc), max(p[1] for p in loc)
    v = v0 + 3.0
    row = 0
    while v < v1 - 2.5:
        u = u0 + 1.8
        while u < u1 - 1.5:
            if rnd() < 0.6 and len(BUCKET.get(('car', 'Auta'), [])) < 1100:
                ok = True
                for (du, dv) in ((-1.0, -2.3), (1.0, -2.3), (1.0, 2.3), (-1.0, 2.3)):
                    q = ((u + du) * ca - (v + dv) * sa, (u + du) * sa + (v + dv) * ca)
                    if not inside(q, pts):
                        ok = False
                if ok:
                    car(u * ca - v * sa, u * sa + v * ca, math.degrees(ang) + 90)
            u += 2.7
        v += 5.2 if row % 2 == 0 else 11.5
        row += 1


def build_roads():
    for r in SITE['roads']:
        k = r['kind']
        if r['tunnel']:
            continue
        pts = r['p']
        walk = k in ('footway', 'path', 'steps', 'cycleway', 'pedestrian')
        if walk and not any(math.hypot(p[0], p[1]) < 170 for p in pts):
            continue
        mat = 'A1A Chodnik' if walk else 'A1A Asfalt'
        z1 = 0.05 if walk else 0.06
        if r['area']:
            add('site', 'Drogi', poly(pts, 0.0, z1, mat, 'road'))
            continue
        for i in range(len(pts) - 1):
            mid = ((pts[i][0] + pts[i + 1][0]) / 2.0, (pts[i][1] + pts[i + 1][1]) / 2.0)
            if in_ramp(mid, 1.5) or inside(mid, OFFICE):
                continue
            if not walk and OWN_PARK and inside(mid, OWN_PARK):
                add('site', 'Parking - alejki', seg(pts[i], pts[i + 1], r['w'], 0.0, 0.055, 'A1A Bruk szary', r['w'] * 0.35))
                continue
            add('site', 'Chodniki' if walk else 'Drogi', seg(pts[i], pts[i + 1], r['w'], 0.0, z1, mat, r['w'] * 0.35))
    for r in SITE['trams']:
        for i in range(len(r['p']) - 1):
            add('site', 'Tramwaj', seg(r['p'][i], r['p'][i + 1], 1.6, 0.06, 0.1, 'A1A Stal'))


def build_railway():
    side = 2.6
    run = 1.5 * (EH - 0.4)
    prof = [(-(side + run), 0.0), (side + run, 0.0), (side, EH - 0.4), (-side, EH - 0.4)]
    since = 0.0
    for r in SITE['rails']:
        pts = r['p']
        if all(p[0] < -255 for p in pts):
            z = 0.0
        else:
            z = EH
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.2:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            a2 = (a[0] - ux * 0.4, a[1] - uy * 0.4)
            b2 = (b[0] + ux * 0.4, b[1] + uy * 0.4)
            if z > 0:
                if r['bridge']:
                    add('site', 'Wiadukt kolejowy', seg(a2, b2, 5.6, z - 1.3, z - 0.4, 'A1A Beton'))
                    since += L
                    if since > 22:
                        since = 0.0
                        add('site', 'Wiadukt kolejowy', box(a[0] - 0.7, a[1] - 0.7, 0, a[0] + 0.7, a[1] + 0.7, z - 1.3, 'A1A Beton'))
                else:
                    add('site', 'Nasyp kolejowy', sweep(a2, b2, prof, 'A1A Trawa'))
            add('site', 'Tory', seg(a2, b2, 3.4, z - 0.4, z, 'A1A Tluczen'))
            nx, ny = -uy, ux
            for s in (-0.72, 0.72):
                add('site', 'Tory', seg((a2[0] + nx * s, a2[1] + ny * s), (b2[0] + nx * s, b2[1] + ny * s), 0.12, z, z + 0.16, 'A1A Stal'))
    # catenary gantries over the two tracks, one every ~45 m along the first long track
    longest = None
    for r in SITE['rails']:
        if not all(p[0] < -255 for p in r['p']):
            L = sum(math.hypot(r['p'][i + 1][0] - r['p'][i][0], r['p'][i + 1][1] - r['p'][i][1]) for i in range(len(r['p']) - 1))
            r['_len'] = L
    for r in SITE['rails']:
        if r.get('_len', 0) < 30 or r['bridge']:
            continue
        acc = 20.0
        pts = r['p']
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.2:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            acc += L
            if acc >= 45.0:
                acc = 0.0
                nx, ny = -uy, ux
                px, py = a[0] + nx * 2.4, a[1] + ny * 2.4
                add('mech', 'Trakcja', box(px - 0.15, py - 0.15, EH - 0.4, px + 0.15, py + 0.15, EH + 7.0, 'A1A Stal'))
                add('mech', 'Trakcja', seg((px, py), (a[0] - nx * 1.2, a[1] - ny * 1.2), 0.2, EH + 6.2, EH + 6.5, 'A1A Stal'))
    for g in SITE['platforms']:
        if g['closed']:
            add('site', 'Perony', poly(g['p'], EH - 1.4, EH + 0.6, 'A1A Beton', 'platform'))
            pts = ccw(g['p'])
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                if math.hypot(b[0] - a[0], b[1] - a[1]) > 12:
                    add('mech', 'Perony - balustrady', seg(a, b, 0.08, EH + 0.6, EH + 1.9, 'A1A Blacha'))


def build_barriers():
    gx, gy = GATE[0], GATE[1]
    for f in SITE['fences']:
        pts = f['p']
        if not any(math.hypot(p[0], p[1]) < 220 for p in pts):
            continue
        if sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)) < 3.0:
            continue                        # stray stubs on the pavement in front of the gate
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.3:
                continue
            # steel panel fence built in 2.5 m bays: post, two rails, pickets close to the plot
            n = max(1, int(math.ceil(L / 2.5)))
            for k in range(n):
                p0 = (a[0] + (b[0] - a[0]) * k / float(n), a[1] + (b[1] - a[1]) * k / float(n))
                p1 = (a[0] + (b[0] - a[0]) * (k + 1) / float(n), a[1] + (b[1] - a[1]) * (k + 1) / float(n))
                mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
                if in_ramp(mid, 0.2) or gate_clear(mid):
                    continue
                add('fence', 'Ogrodzenia', seg(p0, p1, 0.06, 0.2, 0.28, 'A1A Stal'))
                add('fence', 'Ogrodzenia', seg(p0, p1, 0.06, 1.5, 1.58, 'A1A Stal'))
                for q in (p0, p1):
                    add('fence', 'Ogrodzenia', box(q[0] - 0.05, q[1] - 0.05, 0, q[0] + 0.05, q[1] + 0.05, 1.7, 'A1A Stal'))
                if math.hypot(mid[0], mid[1]) < 75:
                    m = max(1, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 0.4))
                    for j in range(1, m):
                        t = j / float(m)
                        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
                        add('fence', 'Ogrodzenia', box(x - 0.02, y - 0.02, 0.2, x + 0.02, y + 0.02, 1.58, 'A1A Stal'))
    for f in SITE['walls']:
        for i in range(len(f['p']) - 1):
            add('fence', 'Murki', seg(f['p'][i], f['p'][i + 1], 0.3, 0.0, 1.3, 'A1A Beton'))
    for f in SITE['hedges']:
        for i in range(len(f['p']) - 1):
            add('plant', 'Zywoploty', seg(f['p'][i], f['p'][i + 1], 1.0, 0.0, 1.3, 'A1A Zywoplot'))
    build_gate()
    build_barrier_gates()


def build_gate():
    """Entrance gate in the street fence on the axis of the main entrance."""
    gx, gy, ux, uy = GATE
    nx, ny = -uy, ux
    if ny < 0:
        nx, ny = -nx, -ny                  # n points towards the building
    for s in (-1, 1):
        px, py = gx + ux * s * GATE_HALF, gy + uy * s * GATE_HALF
        add('fence', 'Brama wejsciowa', box(px - 0.3, py - 0.3, 0, px + 0.3, py + 0.3, 2.2, 'A1A Piaskowiec'))
        add('fence', 'Brama wejsciowa', box(px - 0.38, py - 0.38, 2.2, px + 0.38, py + 0.38, 2.35, 'A1A Piaskowiec ciemny'))
        add('mech', 'Latarnie', box(px - 0.16, py - 0.16, 2.35, px + 0.16, py + 0.16, 2.75, 'A1A Tynk bialy'))
        # gate leaf standing open, swung towards the building
        h0 = (px - ux * s * 0.3, py - uy * s * 0.3)
        h1 = (h0[0] + nx * 1.95 - ux * s * 0.25, h0[1] + ny * 1.95 - uy * s * 0.25)
        add('fence', 'Brama wejsciowa', seg(h0, h1, 0.06, 0.2, 0.28, 'A1A Stal'))
        add('fence', 'Brama wejsciowa', seg(h0, h1, 0.06, 1.6, 1.68, 'A1A Stal'))
        for j in range(0, 9):
            t = j / 8.0
            x, y = h0[0] + (h1[0] - h0[0]) * t, h0[1] + (h1[1] - h0[1]) * t
            add('fence', 'Brama wejsciowa', box(x - 0.025, y - 0.025, 0.2, x + 0.025, y + 0.025, 1.68 + 0.25 * math.sin(t * math.pi), 'A1A Stal'))
        # short lengths of fence that tie the gate posts back into the street fence
        e0 = (px + ux * s * 0.3, py + uy * s * 0.3)
        e1 = (px + ux * s * 1.2, py + uy * s * 1.2)
        add('fence', 'Brama wejsciowa', seg(e0, e1, 0.06, 0.2, 0.28, 'A1A Stal'))
        add('fence', 'Brama wejsciowa', seg(e0, e1, 0.06, 1.5, 1.58, 'A1A Stal'))
    # paved threshold between the street pavement and the plot
    add('site', 'Plac wejsciowy', seg((gx - nx * 3.0, gy - ny * 3.0), (gx + nx * 1.0, gy + ny * 1.0), 2 * GATE_HALF - 0.6, 0.05, 0.09, 'A1A Bruk jasny'))


def build_barrier_gates():
    """Vehicle entrances: an opening in the fence with end posts and a boom barrier."""
    for (x, y, ux, uy) in VGATES:
        nx, ny = -uy, ux
        if ny < 0:
            nx, ny = -nx, -ny                 # n points into the plot
        for s in (-1, 1):
            px, py = x + ux * s * VGATE_HALF, y + uy * s * VGATE_HALF
            add('fence', 'Bramy wjazdowe', box(px - 0.1, py - 0.1, 0, px + 0.1, py + 0.1, 1.8, 'A1A Stal'))
        # boom housing on a kerb island, just inside the fence line
        hx, hy = x - ux * (VGATE_HALF - 0.5) + nx * 1.0, y - uy * (VGATE_HALF - 0.5) + ny * 1.0
        add('site', 'Bramy wjazdowe - wysepka', box(hx - 0.5, hy - 0.5, 0.0, hx + 0.5, hy + 0.5, 0.15, 'A1A Beton'))
        add('fence', 'Bramy wjazdowe', box(hx - 0.2, hy - 0.2, 0.15, hx + 0.2, hy + 0.2, 1.2, 'A1A Auto bialy'))
        add('fence', 'Bramy wjazdowe', box(hx - 0.22, hy - 0.22, 1.2, hx + 0.22, hy + 0.22, 1.27, 'A1A Auto czerwony'))
        k = 0
        d = 0.2
        while d < 5.0:
            a = (hx + ux * d, hy + uy * d)
            b = (hx + ux * min(d + 0.6, 5.0), hy + uy * min(d + 0.6, 5.0))
            add('fence', 'Bramy wjazdowe', seg(a, b, 0.09, 0.98, 1.08, 'A1A Auto czerwony' if k % 2 == 0 else 'A1A Auto bialy'))
            d += 0.6
            k += 1
        ex, ey = hx + ux * 5.0, hy + uy * 5.0
        add('fence', 'Bramy wjazdowe', box(ex - 0.05, ey - 0.05, 0, ex + 0.05, ey + 0.05, 0.98, 'A1A Stal'))


def build_context():
    for b in SITE['buildings']:
        pts = b['p']
        h = b['h']
        kind = b['kind']
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        wall, roof = 'A1A Tynk bialy', 'A1A Dach'
        if kind in ('retail', 'commercial', 'warehouse', 'industrial', 'garage', 'garages', 'service', 'roof', 'shed'):
            wall = 'A1A Tynk szary'
        if kind in ('detached', 'house', 'semidetached_house', 'school', 'civic'):
            roof = 'A1A Dachowka'
        if kind in ('school', 'civic', 'university') and cy > 150:
            wall = 'A1A Ceglany'
        hotel = 20 < cx < 110 and 95 < cy < 150 and abs(area2(pts)) > 700
        if hotel:
            wall, roof, h = 'A1A Tynk bialy', 'A1A Dachowka', max(h, 11.0)
        s = poly(pts, 0.0, h, wall, 'building')
        if s is None:
            continue
        add('ctx', 'Otoczenie - budynki', s)
        cap = 2.6 if roof == 'A1A Dachowka' else 0.35
        add('ctxroof', 'Otoczenie - dachy', poly(pts, h, h + cap, roof, 'building roof'))


def build_ramp():
    n = len(RAMP_PATH)
    C = 'A1A Beton'
    for i in range(n - 1):
        a, b = RAMP_PATH[i], RAMP_PATH[i + 1]
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        L2 = math.hypot(dx, dy)
        L3 = math.sqrt(dx * dx + dy * dy + dz * dz)
        ux, uy = dx / L2, dy / L2
        nx, ny = -uy, ux
        e = 0.9                                         # overlap so the bends close
        ax, ay, az = a[0] - ux * e, a[1] - uy * e, a[2] - dz / L2 * e
        if i == 0:
            ax, ay, az = a
        prof = [(-RW, 0.0), (RW, 0.0), (RW, -0.3), (-RW, -0.3)]
        pts = [P(ax + nx * l, ay + ny * l, az + z) for (l, z) in prof]
        length = math.sqrt((b[0] + ux * e - ax) ** 2 + (b[1] + uy * e - ay) ** 2 + (b[2] + dz / L2 * e - az) ** 2)
        for attempt in (0, 1):
            try:
                add('site', 'Wjazd do garazu', GeometryCreationUtilities.CreateExtrusionGeometry(
                    List[CurveLoop]([loop3(pts)]), XYZ(dx / L3, dy / L3, dz / L3), length / F, opts('A1A Asfalt')))
                break
            except Exception:
                pts.reverse()
        if i >= n - 2:
            continue                                    # last stretch is under the building
        # retaining walls with a 1 m parapet on both sides
        for s in (-1, 1):
            o = s * (RW + 0.15)
            wa = (a[0] + nx * o, a[1] + ny * o)
            wb = (b[0] + nx * o, b[1] + ny * o)
            if i == n - 3 and inside(((wa[0] + wb[0]) / 2.0, (wa[1] + wb[1]) / 2.0), OFFICE):
                continue
            zlow = min(a[2], b[2]) - 0.5
            add('site', 'Wjazd do garazu', seg(wa, wb, 0.3, zlow, 1.0, C, 0.3))
            add('fence', 'Wjazd - balustrady', seg(wa, wb, 0.08, 1.0, 1.08, 'A1A Stal', 0.3))
    # portal in the slanted end facade: lintel and the garage door set back under the building
    b = RAMP_PATH[n - 2]
    nx, ny = FACE_DIR                      # along the facade
    ux, uy = -FACE_DIR[1], FACE_DIR[0]     # into the building
    fx, fy = b[0], b[1]
    add('site', 'Wjazd do garazu', seg((fx - nx * (RW + 0.6), fy - ny * (RW + 0.6)), (fx + nx * (RW + 0.6), fy + ny * (RW + 0.6)), 0.5, -0.6, 0.0, C))
    for s in (-1, 1):
        o = s * (RW + 0.3)
        add('site', 'Wjazd do garazu', seg((fx + nx * o - ux * 0.25, fy + ny * o - uy * 0.25), (fx + nx * o + ux * 0.25, fy + ny * o + uy * 0.25), 0.6, -RAMP_D - 0.3, 0.0, C))
    dxp, dyp = fx + ux * 0.9, fy + uy * 0.9
    add('site', 'Wjazd do garazu', seg((dxp - nx * RW, dyp - ny * RW), (dxp + nx * RW, dyp + ny * RW), 0.1, -RAMP_D, -0.6, 'A1A Stal'))
    # approach apron from the car park
    a0 = RAMP_PATH[0]
    add('site', 'Wjazd do garazu', box(a0[0] - RW - 0.3, a0[1] - 7.0, 0.0, a0[0] + RW + 0.3, a0[1] + 0.05, 0.06, 'A1A Asfalt'))
    # raised triangular planter with a curved wall between the forecourt and the ramp
    planter = [(28.2, -3.4), (35.0, -5.8), (40.2, -5.5), (40.8, -1.0), (41.2, 3.5), (39.3, 6.6), (36.0, 7.6), (31.5, 5.6), (28.2, 3.6)]
    add('site', 'Donica przy wjezdzie', poly(planter, 0.0, 0.9, 'A1A Beton', 'planter'))
    add('site', 'Donica przy wjezdzie', poly(inset(ccw(planter), 0.3), 0.9, 1.0, 'A1A Trawa', 'planter'))


def build_forecourt():
    # paved forecourt, lawns and the entrance path in front of the building
    add('site', 'Plac wejsciowy', box(-34, -7.5, 0.06, 37.5, -0.02, 0.075, 'A1A Bruk jasny'))
    add('site', 'Plac wejsciowy', box(-1.5, GATE[1] + 0.8, 0.06, 1.5, -7.5, 0.085, 'A1A Bruk jasny'))
    add('site', 'Plac wejsciowy', box(-34, 0, 0.06, -29.3, 24, 0.075, 'A1A Bruk'))   # yard at the north-east end
    for (xa, xb) in ((-26.0, -3.0), (3.0, 26.0)):
        add('site', 'Trawniki', box(xa, -7.0, 0.075, xb, -4.6, 0.2, 'A1A Trawa boisko'))
    # lawn between the building and the embankment fence
    add('site', 'Trawniki', poly([(-29.3, 24.0), (4.5, 26.5), (36.0, 15.0), (44.0, 17.0), (0.0, 33.0), (-31.0, 45.0)], 0.0, 0.045, 'A1A Trawa', 'lawn'))
    for y in (-9.0, -19.5, -25.5, -31.5):
        if y < GATE[1] + 3.5:
            continue
        for s in (-1, 1):
            add('mech', 'Latarnie', box(s * 2.0 - 0.07, y - 0.07, 0, s * 2.0 + 0.07, y + 0.07, 4.2, 'A1A Stal'))
            add('mech', 'Latarnie', box(s * 2.0 - 0.22, y - 0.22, 4.2, s * 2.0 + 0.22, y + 0.22, 4.7, 'A1A Tynk bialy'))
    # Parking bays as drawn on the map: a main aisle at Y = -15.5 with bays on both
    # sides, a second aisle at Y = -33.1 in the south-west block, and a short aisle
    # at X = -11 with bays facing it (cars there stand along the facade).
    rows = (
        (-11.0, -33.5, 35.5),      # north of the main aisle
        (-20.2, -34.0, -19.5),     # south of the main aisle, towards the left gate
        (-20.2, 5.8, 35.5),        # south of the main aisle, south-west block
        (-28.6, 8.0, 35.5),        # north of the second aisle
        (-37.6, 16.0, 35.5),       # south of the second aisle
    )
    for (y, x0, x1) in rows:
        x = x0
        while x <= x1 + 0.01:
            if abs(x) > 2.9 and inside((x, y), OWN_PARK) and not in_ramp((x, y), 0.5):
                if rnd() < 0.75:
                    car(x, y, 90)
            x += 2.75
    for xc in (-15.8, -6.6):
        y = -20.2
        while y > -27.6:
            if rnd() < 0.8:
                car(xc, y, 0)
            y -= 2.6
    # hedge between the two back-to-back rows of the south-west block
    add('plant', 'Zywoploty', box(7.0, -24.9, 0.05, 36.0, -23.9, 0.75, 'A1A Zywoplot'))


# ------------------------------------------------------------------ plants
PL = {}


def plant_kit():
    for r in (1.3, 1.7, 2.1, 2.6, 3.1, 3.7):
        for m in ('A1A Korona', 'A1A Korona 2', 'A1A Korona 3'):
            PL[('s', r, m)] = sphere(r, m)
    for r in (0.6, 0.85):
        PL[('s', r, 'A1A Zywoplot')] = sphere(r, 'A1A Zywoplot')
    for (r, h) in ((1.4, 2.6), (1.9, 3.2), (2.5, 3.8)):
        PL[('c', r)] = revolve([(0.0, 0.0), (r, 0.0), (0.0, h)], 'A1A Iglak')


RAD = (1.3, 1.7, 2.1, 2.6, 3.1, 3.7)
TREES = []


def nearest(r):
    return min(RAD, key=lambda q: abs(q - r))


def tree(x, y, s=1.0, z=0.0):
    """Deciduous tree: trunk and a crown made of three overlapping globes."""
    if blocked((x, y)) or on_road((x, y)):
        return
    TREES.append((x, y))
    m = ('A1A Korona', 'A1A Korona 2', 'A1A Korona 3')[int(rnd() * 3)]
    h = (2.4 + rnd() * 1.6) * s
    add('plant', 'Drzewa - pnie', box(x - 0.2 * s, y - 0.2 * s, z, x + 0.2 * s, y + 0.2 * s, z + h + 1.5 * s, 'A1A Pien'))
    a = rnd() * 6.28
    for (r, d, dz) in ((3.1 * s, 0.0, 2.4 * s), (2.3 * s, 1.7 * s, 1.5 * s), (2.1 * s, -1.5 * s, 1.9 * s)):
        rr = nearest(r)
        c = PL.get(('s', rr, m))
        if c is not None:
            add('plant', 'Drzewa - korony', moved(c, x + d * math.cos(a), y + d * math.sin(a), z + h + dz))


def conifer(x, y, s=1.0, z=0.0):
    if blocked((x, y)) or on_road((x, y)):
        return
    TREES.append((x, y))
    add('plant', 'Drzewa - pnie', box(x - 0.15, y - 0.15, z, x + 0.15, y + 0.15, z + 1.6 * s, 'A1A Pien'))
    zz = z + 1.2 * s
    for (r, lift) in ((2.5, 2.4), (1.9, 2.2), (1.4, 0.0)):
        c = PL.get(('c', r))
        if c is not None:
            add('plant', 'Iglaki', moved(c, x, y, zz))
        zz += lift * 1.0


def shrub(x, y, r=0.85, z=0.0):
    c = PL.get(('s', r, 'A1A Zywoplot'))
    if c is not None and not in_ramp((x, y), 0.1):
        add('plant', 'Krzewy', moved(c, x, y, z + r * 0.75))


def build_plants():
    plant_kit()
    for p in SITE['trees']:
        tree(p[0], p[1], 0.9 + rnd() * 0.3)
    for r in SITE['tree_rows']:
        pts = r['p']
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 7.0))
            for k in range(n):
                t = (k + 0.5) / n
                tree(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 1.0)

    def scatter(pts, per, lim):
        pts = ccw(pts)
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        n = min(lim, int(abs(area2(pts)) / 2.0 / per))
        tries = 0
        while n > 0 and tries < 400:
            tries += 1
            q = (x0 + rnd() * (x1 - x0), y0 + rnd() * (y1 - y0))
            if inside(q, pts) and abs(q[0]) < 300 and abs(q[1]) < 300:
                ok = True
                for b in SITE['buildings']:
                    if inside(q, b['p']):
                        ok = False
                        break
                if ok:
                    if rnd() < 0.2:
                        conifer(q[0], q[1], 0.9 + rnd() * 0.4)
                    else:
                        tree(q[0], q[1], 0.8 + rnd() * 0.5)
                    n -= 1

    for g in SITE['woods']:
        scatter(g['p'], 70.0, 40)
    for g in SITE['grass']:
        if len(TREES) < 420:
            scatter(g['p'], 260.0, 6)

    # --- planting seen on the drone footage around the plot ---
    y = -44.0
    while y < 12.5:                       # tall trees in the strip behind the east fence
        tree(45.1 + (y + 53.3) * 0.052 + 0.9, y, 1.1 + rnd() * 0.3)
        y += 6.5
    for (x, y) in ((-37.0, -2.5), (-38.0, 4.0), (-37.0, 11.0)):
        conifer(x, y, 1.2)                # spruces by the white buildings at the north-east end
    for (x, y) in ((-20.0, 30.0), (-8.0, 30.5), (12.0, 28.0)):
        tree(x, y, 0.55)                  # small ornamental trees on the lawn behind
    x = 50.0
    while x < 120.0:                      # trees at the toe of the embankment by the station
        tree(x, 12.0 - (x - 50.0) * 0.12 + rnd() * 3.0, 1.2)
        x += 6.0
    # shrubs, not trees, in the green strip inside the street fence
    x = -42.0
    while x < 38.5:
        q = (x + 0.45, fence_y(x) + 1.3)
        if not gate_clear(q) and math.hypot(q[0] - GATE[0], q[1] - GATE[1]) > 3.6 \
                and min(math.hypot(q[0] - g[0], q[1] - g[1]) for g in VGATES) > 5.0 and not on_road(q):
            shrub(q[0], q[1], 0.85)
        x += 2.0
    # clipped globes at the ends of the hedge and on the forecourt lawns
    for (x, y) in ((6.3, -24.4), (36.6, -24.4)):
        shrub(x, y, 0.85)
    for s in (-1, 1):
        for k in range(5):
            shrub(s * (5.0 + k * 4.8), -5.8, 0.6, 0.15)
    # shrubs in the raised planter by the garage ramp
    for (x, y) in ((30.0, -1.5), (32.0, 1.5), (34.0, -2.5), (30.5, 2.0), (36.0, -4.0), (34.0, 1.0),
                   (37.5, -1.0), (38.5, 3.0), (36.0, 4.5), (39.0, -3.5), (33.5, 4.2)):
        shrub(x, y, 0.85, 0.95)
    LOG.append('trees: %d' % len(TREES))


# ------------------------------------------------------------ the building
CAT = {
    'wall': BuiltInCategory.OST_GenericModel, 'win': BuiltInCategory.OST_GenericModel,
    'roof': BuiltInCategory.OST_Roofs, 'mech': BuiltInCategory.OST_GenericModel,
    'site': BuiltInCategory.OST_Site, 'car': BuiltInCategory.OST_Entourage,
    'plant': BuiltInCategory.OST_Planting, 'fence': BuiltInCategory.OST_GenericModel,
    'ctx': BuiltInCategory.OST_GenericModel, 'ctxroof': BuiltInCategory.OST_GenericModel,
}
MARK = 'A1A'


def flush(prefix):
    made = 0
    for (cat, name), solids in sorted(BUCKET.items()):
        cid = ElementId(CAT[cat])
        if not DirectShape.IsValidCategoryId(cid, doc):
            cid = ElementId(BuiltInCategory.OST_GenericModel)
        for k in range(0, len(solids), 300):
            ds = DirectShape.CreateElement(doc, cid)
            try:
                ds.SetShape(List[GeometryObject](solids[k:k + 300]))
            except Exception:
                # fall back to one solid at a time so a single bad solid cannot drop the rest
                good = List[GeometryObject]()
                for s in solids[k:k + 300]:
                    try:
                        one = List[GeometryObject]()
                        one.Add(s)
                        if ds.IsValidShape(one):
                            good.Add(s)
                    except Exception:
                        fail('shape')
                ds.SetShape(good)
            ds.Name = prefix + name
            made += 1
    LOG.append('%s direct shapes: %d, solids: %d' % (prefix, made, sum(len(v) for v in BUCKET.values())))
    BUCKET.clear()


def delete_shapes(prefix):
    old = List[ElementId]()
    for e in FilteredElementCollector(doc).OfClass(DirectShape):
        if e.Name.startswith(prefix) or not (e.Name.startswith('S-') or e.Name.startswith('B-')):
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)


def setup_levels():
    lv = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Elevation > -0.01]
    lv.sort(key=lambda l: l.Elevation)
    want = FL + [TOP]
    while len(lv) < len(want):
        lv.append(Level.Create(doc, (100.0 + len(lv)) / F))
    for i, l in enumerate(lv):
        l.Name = 'tmp-%d' % i
    for i, z in enumerate(want):
        lv[i].Elevation = z / F
        lv[i].Name = LEVEL_NAMES[i]
    extra = [l.Id for l in lv[len(want):]]
    for i in extra:
        try:
            doc.Delete(i)
        except Exception:
            pass
    return lv[:len(want)]


def type_by(cls, *frags):
    for t in FilteredElementCollector(doc).OfClass(cls):
        n = Element.Name.GetValue(t)
        if all(f in n for f in frags):
            return t
    raise Exception('missing type %s' % (frags,))


def wall_type(name, base_frags, mat, width=None):
    for t in FilteredElementCollector(doc).OfClass(WallType):
        if Element.Name.GetValue(t) == name:
            return t
    nt = type_by(WallType, *base_frags).Duplicate(name)
    cs = nt.GetCompoundStructure()
    idx = cs.GetFirstCoreLayerIndex()
    if width:
        cs.SetLayerWidth(idx, width / F)
    for i in range(cs.LayerCount):
        cs.SetMaterialId(i, MATS[mat])
    nt.SetCompoundStructure(cs)
    return nt


WIN = {}


def window_type(w, h):
    key = (int(round(w * 1000)), int(round(h * 1000)))
    if key in WIN:
        return WIN[key]
    name = 'A1A %04d x %04d' % key
    sym = None
    base = None
    for s in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).OfClass(FamilySymbol):
        if Element.Name.GetValue(s) == name:
            sym = s
        if base is None and s.FamilyName.startswith('M_Sta'):
            base = s
    if sym is None:
        sym = base.Duplicate(name)
        for (bip, val) in ((BuiltInParameter.WINDOW_WIDTH, w), (BuiltInParameter.WINDOW_HEIGHT, h)):
            p = sym.get_Parameter(bip)
            if p is None or p.IsReadOnly:
                p = sym.get_Parameter(BuiltInParameter.FAMILY_WIDTH_PARAM if bip == BuiltInParameter.WINDOW_WIDTH else BuiltInParameter.FAMILY_HEIGHT_PARAM)
            p.Set(val / F)
    if not sym.IsActive:
        sym.Activate()
    WIN[key] = sym
    return sym


EXT_T = 0.4
SHELL = {}   # (level index, edge index) -> wall, with edge geometry


def front_layout(L, f):
    """Windows on the front facade: (offset from the middle, width, height, sill).
    Read off the drone footage: a stone base of two storeys, three tall glazed
    strips in the middle (floors 2-5, the centre one arched), an arched glazed
    bay on each side (floors 2-4) and pairs of punched windows between them."""
    out = []
    pairs = (12.0, 23.4)
    if f == 0:
        out.append((0.0, 3.0, 3.4, 0.05))
        for c in (6.5, 12.0, 23.4):
            for s in (-1, 1):
                out.append((s * c, 3.3, 3.2, 0.4))
        for s in (-1, 1):
            out.append((s * 17.75, 2.6, 3.2, 0.05))
        return out
    if f == 1:
        out.append((0.0, 3.0, 2.0, 0.9))
        for s in (-1, 1):
            for c in (6.5, 17.75):
                out.append((s * c, 3.4, 2.4, 0.8))
            for c in pairs:
                for dx in (-1.35, 1.35):
                    out.append((s * c + dx, 1.5, 2.1, 0.8))
        return out
    if f <= 4:
        out.append((0.0, 4.6, 3.5, 0.1))
        for s in (-1, 1):
            out.append((s * 6.5, 3.6, 3.5, 0.1))
            out.append((s * 17.75, 4.2, 3.5 if f < 4 else 2.7, 0.1))
            for c in pairs:
                for dx in (-1.35, 1.35):
                    out.append((s * c + dx, 1.25, 1.6, 1.0))
        return out
    out.append((0.0, 4.6, 2.4, 0.1))
    for s in (-1, 1):
        out.append((s * 6.5, 3.6, 2.7, 0.1))
        for c in (17.75,) + pairs:
            for dx in (-1.25, 0.0, 1.25):
                out.append((s * c + dx, 0.8, 1.2, 1.3))
    return out


def bay_layout(L, f):
    """North-east end bay: glazed strip in the middle, two window columns each side."""
    out = [(0.0, 2.8, 3.3 if f else 3.6, 0.2 if f else 0.05)]
    for dx in (-4.9, -2.9, 2.9, 4.9):
        out.append((dx, 1.25, 1.6 if f else 2.4, 1.0 if f else 0.9))
    return out


def plain_layout(L, f):
    if L < 2.4:
        return []
    n = max(1, int(L / 3.1))
    out = []
    for i in range(n):
        out.append((L * (i + 0.5) / n - L / 2.0, 1.25, 1.6 if f else 2.4, 1.0 if f else 0.9))
    return out


def build_shell(levels):
    stone = wall_type('A1A Elewacja piaskowiec 400', ('300 mm',), 'A1A Piaskowiec', EXT_T)
    ftype = type_by(FloorType, '300 mm')
    center = inset(OFFICE, EXT_T / 2.0)
    n = len(OFFICE)
    cxo = sum(p[0] for p in OFFICE) / n
    cyo = sum(p[1] for p in OFFICE) / n
    for f in range(len(FL)):
        h = (FL[f + 1] if f + 1 < len(FL) else TOP) - FL[f]
        for i in range(n):
            a, b = center[i], center[(i + 1) % n]
            if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.3:
                continue
            w = Wall.Create(doc, Line.CreateBound(P(a[0], a[1], FL[f]), P(b[0], b[1], FL[f])), stone.Id, levels[f].Id, h / F, 0.0, False, False)
            SHELL[(f, i)] = (w, a, b)
    doc.Regenerate()
    flipped = 0
    for (f, i), (w, a, b) in SHELL.items():
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        o = w.Orientation
        if o.X * (mx - cxo) + o.Y * (my - cyo) < 0:
            w.Flip()
            flipped += 1
    LOG.append('exterior walls: %d (flipped %d)' % (len(SHELL), flipped))
    # floor slabs on every level and the roof slab
    for f in range(len(FL) + 1):
        try:
            Floor.Create(doc, List[CurveLoop]([loop3([P(x, y, 0) for (x, y) in OFFICE])]), ftype.Id, levels[f].Id)
        except Exception as ex:
            LOG.append('floor %d: %s' % (f, ex))
    doc.Regenerate()
    # windows
    front_i, bay_i = None, None
    for i in range(n):
        a, b = OFFICE[i], OFFICE[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if abs(a[1]) < 0.3 and abs(b[1]) < 0.3 and L > 40:
            front_i = i
        if a[0] < -28.5 and b[0] < -28.5 and L > 8:
            bay_i = i
    placed, bad = 0, 0
    first_window = [None]
    for (f, i), (w, a, b) in sorted(SHELL.items()):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        if i == front_i:
            lay = front_layout(L, f)
            # offsets are given along +X; flip if the edge runs the other way
            if ux < 0:
                lay = [(-o, ww, hh, ss) for (o, ww, hh, ss) in lay]
        elif i == bay_i:
            lay = bay_layout(L, f)
        else:
            lay = plain_layout(L, f)
        for (o, ww, hh, ss) in lay:
            if abs(o) + ww / 2.0 > L / 2.0 - 0.25:
                continue
            x, y = (a[0] + b[0]) / 2.0 + ux * o, (a[1] + b[1]) / 2.0 + uy * o
            try:
                inst = doc.Create.NewFamilyInstance(P(x, y, FL[f]), window_type(ww, hh), w, levels[f], StructuralType.NonStructural)
                inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(ss / F)
                placed += 1
                # no flipFacing here: flipping moved some windows out of the wall so they stopped cutting it
                first_window[0] = inst
            except Exception:
                bad += 1
    LOG.append('windows: %d placed, %d failed' % (placed, bad))
    # the library glass is 90% transparent; make it read as dark reflective glazing
    if first_window[0] is not None:
        doc.Regenerate()
        for mid in first_window[0].GetMaterialIds(False):
            m = doc.GetElement(mid)
            if m.Transparency >= 50:
                m.Color = Color(34, 54, 74)
                m.Transparency = 8
            else:
                m.Color = Color(70, 74, 80)

    # stone bands, arch heads, canopies and the roof plant as direct shapes
    D = 'A1A Piaskowiec ciemny'
    for (z0, z1, d) in ((0.0, 0.5, 0.06), (FL[1] - 0.35, FL[1], 0.1), (FL[2] - 0.3, FL[2], 0.18), (TOP - 0.45, TOP, 0.5)):
        ring_o = inset(OFFICE, -d)
        for i in range(n):
            a, b = ring_o[i], ring_o[(i + 1) % n]
            c, e = OFFICE[(i + 1) % n], OFFICE[i]
            add('wall', 'Gzymsy', poly([a, b, c, e], z0, z1, D, 'band'))
    add('wall', 'Gzymsy', poly(inset(OFFICE, -0.5), TOP, TOP + 0.12, D, 'band'))
    add('roof', 'Dach - attyka', poly(inset(OFFICE, 0.9), TOP + 0.12, TOP + 1.0, 'A1A Dach', 'roof'))
    K, M = 'A1A Szklo kurtynowe', 'A1A Slusarka'

    def curtain(xc, w, z0, zs, zp=None):
        """Continuous curtain-wall glazing with a mullion grid, proud of the stone."""
        if zp:
            add('win', 'Sciany kurtynowe', arched_panel(xc, w, z0, zs, zp, 0.0, K, 0.1))
        else:
            add('win', 'Sciany kurtynowe', box(xc - w / 2.0, -0.1, z0, xc + w / 2.0, 0.0, zs, K))
        for k in range(5):
            x = xc + w * (k / 4.0 - 0.5)
            add('win', 'Szprosy', box(x - 0.04, -0.17, z0, x + 0.04, -0.1, zs, M))
        z = z0
        while z <= zs + 0.01:
            add('win', 'Szprosy', box(xc - w / 2.0, -0.17, z - 0.04, xc + w / 2.0, -0.1, z + 0.04, M))
            z += 1.23

    curtain(0.0, 4.6, FL[2] + 0.1, FL[5] + 2.4, FL[5] + 3.2)
    for s in (-1, 1):
        curtain(s * 6.5, 3.6, FL[2] + 0.1, FL[5] + 2.8)
        curtain(s * 17.75, 4.2, FL[2] + 0.1, FL[5] - 0.9, FL[5] + 0.4)
    add('win', 'Sciany kurtynowe', arched_panel(0.0, 3.0, FL[1] + 0.9, FL[1] + 2.9, FL[1] + 3.35, 0.0, K))
    # entrances: door frames, glass canopies on brackets, stone surrounds, door mats
    for (xc, w, main) in ((0.0, 3.0, True), (-17.75, 2.6, False), (17.75, 2.6, False)):
        for x in (xc - w / 2.0, xc, xc + w / 2.0):
            add('win', 'Szprosy', box(x - 0.04, -0.1, 0.05, x + 0.04, 0.0, 3.2, M))
        for z in (2.3, 3.2):
            add('win', 'Szprosy', box(xc - w / 2.0, -0.1, z - 0.04, xc + w / 2.0, 0.0, z + 0.04, M))
        for x in (xc - 0.35, xc + 0.35):
            add('win', 'Szprosy', box(x - 0.03, -0.16, 1.0, x + 0.03, -0.1, 1.5, 'A1A Stal'))   # pull handles
        d = 2.2 if main else 1.8
        zc = 3.6 if main else 3.5
        add('mech', 'Zadaszenia', box(xc - w / 2.0 - 0.5, -d, zc, xc + w / 2.0 + 0.5, 0, zc + 0.05, K))
        add('mech', 'Zadaszenia', box(xc - w / 2.0 - 0.5, -d, zc - 0.1, xc + w / 2.0 + 0.5, -d + 0.08, zc + 0.08, 'A1A Stal'))
        for x in (xc - w / 2.0 - 0.4, xc + w / 2.0 + 0.4):
            add('mech', 'Zadaszenia', box(x - 0.04, -d, zc - 0.12, x + 0.04, 0, zc, 'A1A Stal'))
        pw = 0.45 if main else 0.3
        for s in (-1, 1):
            x = xc + s * (w / 2.0 + 0.2 + pw)
            add('wall', 'Gzymsy', box(x - pw, -0.2, 0, x + pw, 0, (FL[2] + 0.4) if main else FL[1] - 0.35, D))
        add('site', 'Wycieraczki', box(xc - w / 2.0, -1.3, 0.07, xc + w / 2.0, -0.05, 0.1, 'A1A Stal'))
    # tenant boards beside the main entrance
    for s in (-1, 1):
        add('mech', 'Tablice najemcow', box(s * 2.75 - 0.3, -0.26, 1.2, s * 2.75 + 0.3, -0.2, 2.3, 'A1A Stal'))
    BL = 'A1A Blacha'
    Z = TOP + 1.0
    add('mech', 'Dach - wentylacja', box(-17, 11.5, Z, 15, 14.0, Z + 1.4, BL))
    add('mech', 'Dach - wentylacja', box(-20, 8.5, Z, -15, 15.5, Z + 1.8, BL))
    add('mech', 'Dach - wentylacja', box(12, 9.0, Z, 18, 15.0, Z + 1.6, BL))
    add('mech', 'Dach - wentylacja', box(-6, 14.0, Z, -4.6, 19.0, Z + 0.9, BL))
    add('mech', 'Dach - wentylacja', box(3, 5.0, Z, 4.4, 11.5, Z + 0.9, BL))
    for x in (-12, -8, 0, 6, 22):
        add('mech', 'Dach - wentylacja', box(x, 5.5, Z, x + 2.2, 7.7, Z + 1.1, BL))
    for i in range(12):
        x = -25 + i * 4.2
        add('mech', 'Dach - panele PV', box(x, 1.8, Z, x + 3.6, 4.0, Z + 0.15, 'A1A Stal'))
    for i in range(5):
        add('mech', 'Dach - panele PV', box(4 + i * 4.2, 16.0 - i * 1.3, Z, 7.6 + i * 4.2, 18.2 - i * 1.3, Z + 0.15, 'A1A Stal'))


def back_y(x):
    """Inner line of the rear wall at a given X (centre line of the exterior wall)."""
    if x < -17.7:
        return 23.48 - 0.2
    if x <= 3.61:
        return 22.29 - 0.2
    if x <= 5.09:
        return 22.29 + (x - 3.61) * (25.77 - 22.29) / (5.09 - 3.61) - 0.25
    return 25.77 - (x - 5.09) * 0.3658 - 0.22


def build_interior(levels):
    part = type_by(WallType, '138 mm')
    door = None
    for s in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).OfClass(FamilySymbol):
        if '0915 x 2134' in Element.Name.GetValue(s):
            door = s
    if door is not None and not door.IsActive:
        door.Activate()
    doc.Regenerate()
    nw, nd, nr = 0, 0, 0
    X0, X1 = -18.4, 24.0          # corridor runs between the two end units
    YC0, YC1 = 9.6, 11.6
    front_x = [X0 + 5.3 * k for k in range(9)]
    front_x[-1] = X1
    rear_ne = [X0, -12.2, -6.0]
    core = [-6.0, -1.0, 4.0]
    rear_sw = [4.0, 9.0, 14.0, 19.0, X1]
    for f in range(len(FL)):
        h = (FL[f + 1] if f + 1 < len(FL) else TOP) - FL[f] - 0.3
        lvl = levels[f]

        def wall(a, b):
            return Wall.Create(doc, Line.CreateBound(P(a[0], a[1], FL[f]), P(b[0], b[1], FL[f])), part.Id, lvl.Id, h / F, 0.0, False, False)

        def put_door(w, x, y):
            if door is None:
                return 0
            try:
                doc.Create.NewFamilyInstance(P(x, y, FL[f]), door, w, lvl, StructuralType.NonStructural)
                return 1
            except Exception:
                return 0

        walls = []
        wf = wall((X0, YC0), (X1, YC0))            # corridor, front side
        wr = wall((X0, YC1), (X1, YC1))            # corridor, rear side
        we1 = wall((X0, 0.2), (X0, back_y(X0)))    # wall of the north-east unit
        we2 = wall((X1, 0.2), (X1, back_y(X1)))    # wall of the south-west unit
        walls += [wf, wr, we1, we2]
        for x in front_x[1:-1]:
            if f == 0 and abs(x - 0.15) < 3.0:
                continue                            # entrance hall spans two bays on the ground floor
            walls.append(wall((x, 0.2), (x, YC0)))
        for x in rear_ne[1:] + core[1:] + rear_sw[1:-1]:
            walls.append(wall((x, YC1), (x, back_y(x))))
        # north-east unit (lokal x.01), laid out after the 2.01/2.09 letting plan
        XE = -27.1
        walls.append(wall((XE, 18.1), (-22.2, 18.1)))
        walls.append(wall((-24.6, 18.1), (-24.6, back_y(-24.6))))
        wk = wall((-22.2, 16.4), (-22.2, back_y(-22.2)))
        walls.append(wk)
        walls.append(wall((-22.2, 16.4), (X0, 16.4)))
        wfr = wall((-28.9, 7.4), (X0, 7.4))        # starts at the inner face of the projecting bay
        walls.append(wfr)
        walls.append(wall((-22.8, 0.2), (-22.8, 7.4)))
        walls.append(wall((-20.6, 11.0), (X0, 11.0)))
        walls.append(wall((-20.6, 11.0), (-20.6, 14.2)))
        walls.append(wall((-20.6, 14.2), (X0, 14.2)))
        nw += len(walls)
        doc.Regenerate()
        # doors
        for k in range(len(front_x) - 1):
            nd += put_door(wf, (front_x[k] + front_x[k + 1]) / 2.0, YC0)
        for xs in (rear_ne, core, rear_sw):
            for k in range(len(xs) - 1):
                nd += put_door(wr, (xs[k] + xs[k + 1]) / 2.0, YC1)
        nd += put_door(we1, X0, 10.3)
        nd += put_door(we2, X1, 10.6)
        nd += put_door(wfr, -25.0, 7.4)
        nd += put_door(wfr, -20.8, 7.4)
        nd += put_door(wk, -22.2, 17.3)
        # rooms
        doc.Regenerate()
        num = [0]

        def room(x, y, name):
            try:
                r = doc.Create.NewRoom(lvl, UV(x / F, y / F))
                num[0] += 1
                r.Name = name
                r.Number = '%d.%02d' % (f, num[0])
                return 1
            except Exception:
                return 0

        unit = 'Lokal %d.01' % (f + 1)
        nr += room(-23.5, 12.5, unit + ' - open space')
        nr += room(-25.8, 20.5, unit + ' - gabinet 1')
        nr += room(-23.4, 20.5, unit + ' - gabinet 2')
        nr += room(-20.3, 19.8, unit + ' - sala spotkan')
        nr += room(-25.0, 3.8, unit + ' - pokoj 1')
        nr += room(-20.6, 3.8, unit + ' - pokoj 2')
        nr += room(-19.5, 12.6, unit + ' - aneks i WC')
        for k in range(len(front_x) - 1):
            xm = (front_x[k] + front_x[k + 1]) / 2.0
            if f == 0 and abs(front_x[k + 1] - 0.15) < 3.0:
                continue
            if f == 0 and abs(front_x[k] - 0.15) < 3.0:
                nr += room(0.15, 5.0, 'Hol wejsciowy')
                continue
            nr += room(xm, 5.0, ('Lokal uslugowy %d' if f == 0 else 'Biuro front %d') % (k + 1))
        nr += room(0.0, 10.6, 'Korytarz')
        for k in range(len(rear_ne) - 1):
            nr += room((rear_ne[k] + rear_ne[k + 1]) / 2.0, 16.5, 'Biuro tyl %d' % (k + 1))
        nr += room(-3.5, 16.5, 'Klatka schodowa')
        nr += room(1.5, 16.5, 'Windy i sanitariaty')
        for k in range(len(rear_sw) - 1):
            nr += room((rear_sw[k] + rear_sw[k + 1]) / 2.0, 16.0, 'Biuro tyl %d' % (k + 3))
        nr += room(29.0, 12.0, 'Lokal %d.02' % (f + 1))
    LOG.append('interior walls: %d, doors: %d, rooms: %d' % (nw, nd, nr))


def delete_class(cls, bic=None):
    old = List[ElementId]()
    col = FilteredElementCollector(doc).WhereElementIsNotElementType()
    col = col.OfCategory(bic) if bic else col.OfClass(cls)
    for e in col:
        old.Add(e.Id)
    n = old.Count
    if n:
        try:
            doc.Delete(old)
        except Exception:
            for i in old:
                try:
                    doc.Delete(i)
                except Exception:
                    pass
    return n


def run(name, fn):
    t = Transaction(doc, name)
    t.Start()
    fo = t.GetFailureHandlingOptions()
    fo.SetFailuresPreprocessor(Swallow())
    t.SetFailureHandlingOptions(fo)
    try:
        fn()
        t.Commit()
    except Exception:
        t.RollBack()
        raise


class Swallow(IFailuresPreprocessor):
    def PreprocessFailures(self, fa):
        for m in fa.GetFailureMessages():
            if m.GetSeverity() == FailureSeverity.Warning:
                fa.DeleteWarning(m)
        return FailureProcessingResult.Continue


def stage_site():
    delete_shapes('S-')
    make_materials()
    build_ground()
    build_roads()
    build_railway()
    build_barriers()
    build_context()
    build_ramp()
    build_forecourt()
    build_plants()
    flush('S-')


def stage_shell():
    make_materials()
    delete_class(None, BuiltInCategory.OST_Rooms)
    delete_class(FamilyInstance)
    delete_class(Wall)
    delete_class(Floor)
    old = List[ElementId]()
    for e in FilteredElementCollector(doc).OfClass(DirectShape):
        if e.Name.startswith('B-'):
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)
    levels = setup_levels()
    doc.Regenerate()
    build_shell(levels)
    flush('B-')


def stage_interior():
    make_materials()
    delete_class(None, BuiltInCategory.OST_Rooms)
    old = List[ElementId]()
    for e in FilteredElementCollector(doc).OfClass(FamilyInstance):
        if e.Category is not None and e.Category.Id == ElementId(BuiltInCategory.OST_Doors):
            old.Add(e.Id)
    for e in FilteredElementCollector(doc).OfClass(Wall):
        if '138' in e.Name:
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)
    levels = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name in LEVEL_NAMES]
    levels.sort(key=lambda l: l.Elevation)
    build_interior(levels)


if 'site' in STAGES:
    run('A1A site', stage_site)
if 'shell' in STAGES:
    run('A1A shell', stage_shell)
if 'interior' in STAGES:
    run('A1A interior', stage_interior)
if FAIL:
    LOG.append('skipped solids: %s' % FAIL)
print('\n'.join(LOG))
