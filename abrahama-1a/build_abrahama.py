# Builds the Abrahama 1A office building (Gdansk) with its surroundings in the
# open "Abrahama_1A" Revit document. Run inside Revit (IronPython):
#   STAGES = ['site', 'shell', 'plans']   # optional, default = all
#   exec(open(r'<this file>').read())
# The surroundings come from OpenStreetMap (site.json, made by osm_to_site.py).
# The footprint, the garage, the ramp and every floor's walls, doors and rooms
# come from the PDF floor plans (plans.json, made by plans_to_json.py). Facades
# and storey heights are estimated from drone footage.
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
PLANS = json.load(open(os.path.join(HERE, 'plans.json')))
try:
    STAGES
except NameError:
    STAGES = ['site', 'shell', 'plans']
F = 0.3048
LOG = []

FL = [0.0, 4.6, 8.3, 12.0, 15.7, 19.4]   # ground floor + 5 upper floors
TOP = 23.1
LEVEL_NAMES = ['Parter', 'Pietro 1', 'Pietro 2', 'Pietro 3', 'Pietro 4', 'Pietro 5', 'Dach']
BASE = -3.2                       # garage floor
CX = -0.15                        # axis of the front facade, from the pier rhythm on the plans
EH = 7.0     # height of the railway embankment
# Garage ramp, read off the ground floor plan: centre lines of the two retaining
# walls. Cars enter at the south end, run north, then turn west and go under the
# slanted south-west end facade into the garage.
RAMP_IN = [(41.41, -6.55), (41.89, 2.98), (39.74, 6.25), (34.25, 8.30)]
RAMP_OUT = [(47.60, -6.87), (48.43, 9.62), (36.50, 14.05)]
RAMP_CL = [(44.5, -6.7), (45.0, 4.0), (43.0, 8.6), (35.3, 11.2)]
RAMP_POLY = RAMP_IN + list(reversed(RAMP_OUT))
# transformer station under the ground between the building end and the ramp
TRAFO = [(36.87, -2.86), (41.30, -2.86), (41.55, 2.90), (39.50, 6.00), (36.87, 7.00)]
# garage outline from the basement plan
GARAGE = [(-29.1, -4.45), (28.6, -4.45), (28.6, 5.41), (33.13, 5.41), (36.39, 14.25),
          (33.2, 15.45), (23.9, 18.85), (23.9, 23.35), (-29.1, 23.35)]


def P(x, y, z=0.0):
    return XYZ(x / F, y / F, z / F)


_seed = [20250911]


def rnd():
    _seed[0] = (_seed[0] * 1103515245 + 12345) % 2147483648
    return _seed[0] / 2147483648.0


# ---------------------------------------------------------------- materials
MATS = {}
MAT_DEF = {
    'A1A Piaskowiec': (238, 226, 190, 0),
    'A1A Piaskowiec ciemny': (222, 208, 172, 0),
    'A1A Szklo': (38, 62, 84, 0),
    'A1A Szklo kurtynowe': (30, 50, 70, 0),
    'A1A Slusarka': (96, 102, 110, 0),
    'A1A Dach': (62, 66, 72, 0),
    'A1A Blacha': (176, 182, 188, 0),
    'A1A Teren': (186, 182, 170, 0),
    'A1A Trawa': (104, 146, 70, 0),
    'A1A Trawa boisko': (88, 170, 72, 0),
    'A1A Bruk': (178, 124, 112, 0),
    'A1A Bruk jasny': (216, 204, 186, 0),
    'A1A Bruk szary': (122, 122, 126, 0),
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


def squared(pts):
    """Snap edges within 2 degrees of the axes onto the axes."""
    pts = [list(p) for p in pts]
    for it in range(3):
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            tol = 0.035 if math.hypot(dx, dy) > 3.0 else 0.13   # short edges drift more in the trace
            if abs(dx) > 1e-6 and abs(dy / dx) < tol:
                y = (a[1] + b[1]) / 2.0
                a[1] = b[1] = y
            elif abs(dy) > 1e-6 and abs(dx / dy) < tol:
                x = (a[0] + b[0]) / 2.0
                a[0] = b[0] = x
    return [(round(p[0], 3), round(p[1], 3)) for p in pts]


# footprint traced from the first floor plan, front facade on Y = 0
OFFICE = ccw(squared(PLANS['shell']))


def dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dy * t)


def in_ramp(p, m=1.0):
    if inside(p, RAMP_POLY):
        return True
    n = len(RAMP_POLY)
    return min(dist_seg(p, RAMP_POLY[i], RAMP_POLY[(i + 1) % n]) for i in range(n)) < m + 0.2


def path_s(p, line):
    """Distance along a polyline to the point closest to p."""
    best, acc, at = None, 0.0, 0.0
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (L * L)))
        d = math.hypot(p[0] - a[0] - dx * t, p[1] - a[1] - dy * t)
        if best is None or d < best:
            best, at = d, acc + L * t
        acc += L
    return at, acc


RAMP_D2 = (-0.937, 0.348)          # direction of the second leg, towards the building
RAMP_Z1 = -1.6                     # level of the landing at the bend
RAMP_ZP = -2.8                     # level at the portal in the end facade
# landing between the two legs: its edges are square to each leg so the three
# parts of the ramp are flat planes that meet without steps
RAMP_Q1 = (48.10, 2.98)
RAMP_Q2 = (41.90, 12.05)


def ramp_z(p):
    s2 = (p[0] - RAMP_IN[2][0]) * RAMP_D2[0] + (p[1] - RAMP_IN[2][1]) * RAMP_D2[1]
    if s2 > 0.05:
        return RAMP_Z1 + (RAMP_ZP - RAMP_Z1) * s2 / 5.86
    if p[1] < RAMP_IN[1][1] - 0.01:
        # strictly linear in Y so the first leg stays one flat plane
        return RAMP_Z1 * (p[1] + 6.71) / (RAMP_IN[1][1] + 6.71)
    return RAMP_Z1

def offset_line(pts, d):
    """Polyline offset to the left by d, with mitred corners."""
    n = len(pts)
    segs = []
    for i in range(n - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        segs.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    out = [segs[0][0]]
    for i in range(1, n - 1):
        (a0, a1), (b0, b1) = segs[i - 1], segs[i]
        dxa, dya = a1[0] - a0[0], a1[1] - a0[1]
        dxb, dyb = b1[0] - b0[0], b1[1] - b0[1]
        den = dxa * dyb - dya * dxb
        if abs(den) < 1e-9:
            out.append(b0)
        else:
            t = ((b0[0] - a0[0]) * dyb - (b0[1] - a0[1]) * dxb) / den
            out.append((a0[0] + dxa * t, a0[1] + dya * t))
    out.append(segs[-1][1])
    return out


def resample(pts, n):
    L = [0.0]
    for i in range(len(pts) - 1):
        L.append(L[-1] + math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
    out = []
    for k in range(n + 1):
        s = L[-1] * k / float(n)
        i = 0
        while i < len(pts) - 2 and L[i + 1] < s:
            i += 1
        t = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
        out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    return out


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
    if in_ramp(p, 0.5) or (41.0 < p[0] < 48.0 and -16.0 < p[1] < -6.0):
        return True
    if abs(p[0]) < 2.2 and GATE[1] - 1 < p[1] < 0:
        return True
    for (a, b, lim) in ROADS_NEAR:
        if abs(p[0] - a[0]) < 40 and abs(p[1] - a[1]) < 40 and dist_seg(p, a, b) < lim:
            return True
    return False


def on_plot(p):
    """Inside the fenced plot in front of the building."""
    return -56.0 < p[0] < 48.6 and fence_y(p[0]) - 0.3 < p[1] < 6.0


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
    for (name, pts, z0) in (('ramp', RAMP_POLY, BASE - 0.4), ('garage', GARAGE, BASE - 0.35)):
        cut = poly(pts, z0, 0.6, 'A1A Teren', 'cut')
        try:
            terrain = BooleanOperationsUtils.ExecuteBooleanOperation(terrain, cut, BooleanOperationsType.Difference)
        except Exception as ex:
            LOG.append('terrain cut %s failed: %s' % (name, ex))
    add('site', 'Teren', terrain)
    # roof slab of the garage where it reaches out under the forecourt
    add('site', 'Strop garazu', poly(GARAGE, -0.35, -0.01, 'A1A Beton', 'garage roof'))
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
            if on_plot(mid) or (47.0 < mid[0] < 95.0 and -62.0 < mid[1] < 14.0):
                continue              # the plot's own drives are drawn as one surface below
            add('site', 'Chodniki' if walk else 'Drogi', seg(pts[i], pts[i + 1], r['w'], 0.0, z1, mat, r['w'] * 0.35))
    for r in SITE['trams']:
        for i in range(len(r['p']) - 1):
            add('site', 'Tramwaj', seg(r['p'][i], r['p'][i + 1], 1.6, 0.06, 0.1, 'A1A Stal'))
    # Drives on the plot: one material, one level, laid out as continuous strips
    # from the left gate along the main aisle to the ramp and down to the right gate.
    M = 'A1A Bruk szary'  # drive lanes in grey pavers, bays in red: tells lanes from bays at a glance

    def strip(pts, w):
        for i in range(len(pts) - 1):
            add('site', 'Parking - jezdnie', seg(pts[i], pts[i + 1], w, 0.0, 0.056, M, w * 0.5))

    strip([(-43.9, -21.8), (-42.7, -19.1), (-40.9, -17.3), (-38.3, -15.9), (-35.0, -15.5)], 5.0)   # left gate throat
    # Two separate car parks, private on the left and public on the right: the aisle
    # stops at the entrance path on both sides, nothing drives across it.
    add('site', 'Parking - jezdnie', box(-37.0, -17.75, 0.0, -2.6, -13.25, 0.056, M))
    add('site', 'Parking - jezdnie', box(2.6, -17.75, 0.0, 47.6, -13.25, 0.056, M))
    add('site', 'Parking - jezdnie', box(-13.4, -28.6, 0.0, -8.8, -17.7, 0.056, M))                # lane inside the left block
    strip([(-32.2, -15.5), (-31.9, 3.5)], 4.5)                                                      # to the yard at the end
    add('site', 'Parking - jezdnie', box(5.5, -35.3, 0.0, 45.9, -29.3, 0.056, M))                   # second aisle
    strip([(44.4, -15.5), (43.4, -33.1), (42.4, -48.6), (42.05, -52.15)], 5.6)                      # down to the right gate


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
    """Pedestrian gate on the axis of the main entrance, after the photo from the
    offices: two broad, plain rendered pillars with flat caps and a low double
    gate of dark steel bars between them, closed."""
    gx, gy, ux, uy = GATE
    nx, ny = -uy, ux
    if ny < 0:
        nx, ny = -nx, -ny                  # n points towards the building
    for s in (-1, 1):
        c = (gx + ux * s * 1.85, gy + uy * s * 1.85)
        a = (c[0] - ux * 0.65, c[1] - uy * 0.65)
        b = (c[0] + ux * 0.65, c[1] + uy * 0.65)
        a2 = (c[0] - ux * 0.72, c[1] - uy * 0.72)
        b2 = (c[0] + ux * 0.72, c[1] + uy * 0.72)
        add('fence', 'Furtka - slupy', seg(a2, b2, 0.64, 0.0, 0.25, 'A1A Piaskowiec ciemny'))
        add('fence', 'Furtka - slupy', seg(a, b, 0.5, 0.25, 2.0, 'A1A Piaskowiec'))
        add('fence', 'Furtka - slupy', seg(a2, b2, 0.66, 2.0, 2.12, 'A1A Piaskowiec ciemny'))
        # gate leaf, closed: from the pillar to the middle, bars rising towards the middle
        h0 = (c[0] - ux * s * 0.65, c[1] - uy * s * 0.65)
        h1 = (gx + ux * s * 0.03, gy + uy * s * 0.03)
        add('fence', 'Furtka', seg(h0, h1, 0.05, 0.15, 0.22, 'A1A Stal'))
        add('fence', 'Furtka', seg(h0, h1, 0.05, 1.4, 1.47, 'A1A Stal'))
        for j in range(0, 9):
            t = j / 8.0
            x, y = h0[0] + (h1[0] - h0[0]) * t, h0[1] + (h1[1] - h0[1]) * t
            add('fence', 'Furtka', box(x - 0.022, y - 0.022, 0.15, x + 0.022, y + 0.022, 1.55 + 0.3 * math.sin(t * math.pi / 2.0), 'A1A Stal'))
        # short lengths of fence that tie the pillars back into the street fence
        e0 = (c[0] + ux * s * 0.65, c[1] + uy * s * 0.65)
        e1 = (c[0] + ux * s * 1.5, c[1] + uy * s * 1.5)
        add('fence', 'Furtka', seg(e0, e1, 0.06, 0.2, 0.28, 'A1A Stal'))
        add('fence', 'Furtka', seg(e0, e1, 0.06, 1.5, 1.58, 'A1A Stal'))
        m = 4
        for j in range(1, m + 1):
            x, y = e0[0] + (e1[0] - e0[0]) * j / float(m), e0[1] + (e1[1] - e0[1]) * j / float(m)
            add('fence', 'Furtka', box(x - 0.02, y - 0.02, 0.2, x + 0.02, y + 0.02, 1.58, 'A1A Stal'))
    lantern(gx - 2.15, gy + 2.0)           # the lamp standing just inside, next to the pillar
    # paved threshold between the street pavement and the plot
    add('site', 'Plac wejsciowy', seg((gx - nx * 3.0, gy - ny * 3.0), (gx + nx * 1.0, gy + ny * 1.0), 2.4, 0.05, 0.09, 'A1A Bruk jasny'))


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


def ramp_plane(pts, zf=None, name='Wjazd do garazu'):
    """One flat part of the ramp: plan polygon lifted onto the ramp surface."""
    zf = zf or ramp_z
    pts3 = [P(p[0], p[1], zf(p)) for p in pts]
    for attempt in (0, 1):
        try:
            add('site', name, GeometryCreationUtilities.CreateExtrusionGeometry(
                List[CurveLoop]([loop3(pts3)]), XYZ(0, 0, -1), 0.3 / F, opts('A1A Asfalt')))
            return
        except Exception:
            pts3.reverse()
    fail('ramp plane')
    LOG.append('ramp plane failed: %s' % [tuple(round(v, 2) for v in q) + (round(ramp_z(q), 3),) for q in pts])


def build_ramp():
    """Garage ramp after the ground floor plan: a straight leg down from the car
    park, a level landing at the bend, and a second leg under the end facade."""
    ramp_plane([RAMP_IN[0], RAMP_OUT[0], RAMP_Q1, RAMP_IN[1]])
    ramp_plane([RAMP_IN[1], RAMP_Q1, RAMP_OUT[1], RAMP_Q2, RAMP_IN[2]], lambda q: RAMP_Z1)

    def leg2(q):
        # one exact plane for the second leg and its run under the building
        s2 = (q[0] - RAMP_IN[2][0]) * RAMP_D2[0] + (q[1] - RAMP_IN[2][1]) * RAMP_D2[1]
        return RAMP_Z1 + (RAMP_ZP - RAMP_Z1) * s2 / 5.86

    ramp_plane([RAMP_IN[2], RAMP_Q2, RAMP_OUT[2], RAMP_IN[3]], leg2)
    inner = [(RAMP_IN[3][0] + RAMP_D2[0] * 6.0, RAMP_IN[3][1] + RAMP_D2[1] * 6.0),
             (RAMP_OUT[2][0] + RAMP_D2[0] * 6.0, RAMP_OUT[2][1] + RAMP_D2[1] * 6.0)]
    ramp_plane([RAMP_IN[3], RAMP_OUT[2], inner[1], inner[0]], leg2)     # continues under the building
    # retaining walls with mitred corners, a low parapet and a railing
    C = 'A1A Beton'
    for (line, side) in ((RAMP_IN, -1), (RAMP_OUT, 1)):
        o1 = offset_line(line, 0.0)
        o2 = offset_line(line, side * 0.3)
        mid1 = offset_line(line, side * 0.15)
        for i in range(len(line) - 1):
            quad = [o1[i], o1[i + 1], o2[i + 1], o2[i]]
            zlow = min(ramp_z(line[i]), ramp_z(line[i + 1])) - 0.6
            add('site', 'Wjazd - mury oporowe', poly(quad, zlow, 0.45, C, 'ramp wall'))
            add('site', 'Wjazd - mury oporowe', poly(quad, 0.45, 0.5, 'A1A Piaskowiec ciemny', 'ramp cap'))
            add('fence', 'Wjazd - balustrady', seg(mid1[i], mid1[i + 1], 0.05, 1.05, 1.1, 'A1A Stal'))
            Ls = math.hypot(line[i + 1][0] - line[i][0], line[i + 1][1] - line[i][1])
            nposts = max(1, int(Ls / 1.5))
            for k in range(nposts + 1):
                t = k / float(nposts)
                x = mid1[i][0] + (mid1[i + 1][0] - mid1[i][0]) * t
                y = mid1[i][1] + (mid1[i + 1][1] - mid1[i][1]) * t
                add('fence', 'Wjazd - balustrady', box(x - 0.025, y - 0.025, 0.5, x + 0.025, y + 0.025, 1.1, 'A1A Stal'))
    # portal in the slanted end facade: lintel under the ground floor, door set back
    a, b = RAMP_IN[3], RAMP_OUT[2]
    add('site', 'Wjazd do garazu', seg(a, b, 0.5, -0.45, 0.0, C))
    d0 = (a[0] + RAMP_D2[0] * 1.2, a[1] + RAMP_D2[1] * 1.2)
    d1 = (b[0] + RAMP_D2[0] * 1.2, b[1] + RAMP_D2[1] * 1.2)
    add('site', 'Wjazd do garazu', seg(d0, d1, 0.08, RAMP_ZP - 0.4, -0.45, 'A1A Blacha'))
    # approach from the car park aisle to the top of the ramp
    add('site', 'Parking - jezdnie', poly([(41.2, -13.3), (47.6, -13.3), (47.6, -6.87), (41.41, -6.55)], 0.0, 0.056, 'A1A Bruk szary', 'apron'))
    # raised planter over the transformer station, between the building end and the ramp
    planter = [(27.4, -0.15), (27.4, 5.25), (32.95, 5.25), (34.05, 8.05), (39.5, 6.05), (41.15, 3.0),
               (40.9, -4.6), (38.6, -6.2), (34.2, -6.3), (30.6, -5.0), (28.3, -2.6)]
    add('site', 'Donica nad stacja trafo', poly(planter, 0.0, 0.9, 'A1A Piaskowiec ciemny', 'planter'))
    add('site', 'Donica nad stacja trafo', poly(inset(ccw(planter), 0.3), 0.9, 1.0, 'A1A Trawa', 'planter'))
    add('site', 'Stacja transformatorowa', poly(TRAFO, BASE, -0.4, 'A1A Beton', 'trafo'))


def lantern(x, y):
    """Classic lantern lamp as seen along the entrance path."""
    add('mech', 'Latarnie', box(x - 0.07, y - 0.07, 0, x + 0.07, y + 0.07, 3.3, 'A1A Stal'))
    add('mech', 'Latarnie', box(x - 0.16, y - 0.16, 0, x + 0.16, y + 0.16, 0.5, 'A1A Stal'))
    add('mech', 'Latarnie', box(x - 0.2, y - 0.2, 3.3, x + 0.2, y + 0.2, 3.85, 'A1A Szklo'))
    add('mech', 'Latarnie', box(x - 0.26, y - 0.26, 3.85, x + 0.26, y + 0.26, 3.95, 'A1A Stal'))


def bollard(x, y):
    add('mech', 'Slupki', box(x - 0.15, y - 0.15, 0.05, x + 0.15, y + 0.15, 0.8, 'A1A Piaskowiec'))


def bay_lines(x0, y0, x1, y1, nx, ny):
    """White bay markings: a grid of nx by ny bays."""
    W = 'A1A Tynk bialy'
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / float(nx)
        add('site', 'Parking - linie', box(x - 0.05, y0, 0.06, x + 0.05, y1, 0.072, W))
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / float(ny)
        add('site', 'Parking - linie', box(x0, y - 0.05, 0.06, x1, y + 0.05, 0.072, W))


def build_forecourt():
    """Forecourt and car park after the photos taken from the offices.
    Whatever is not paved on the plot is lawn.
    Seen from the entrance looking at the street: the right-hand side (north-east,
    -X) has a block of bays stacked along the facade; the left-hand side
    (south-west, +X) has rows on two aisles with a thin grass strip between them."""
    add('site', 'Trawniki', poly([(-51.6, -4.2), (-54.9, -18.1), (-43.9, -21.8), (-3.2, -36.2), (3.3, -38.5), (39.0, -51.0),
                                  (45.1, -53.3), (47.3, -10.0), (41.0, -7.5), (-34.0, -7.5), (-40.6, -4.4)], 0.0, 0.026, 'A1A Trawa', 'plot lawn'))
    add('site', 'Plac wejsciowy', box(-34, -7.5, 0.06, 28.0, -0.02, 0.075, 'A1A Bruk jasny'))
    add('site', 'Plac wejsciowy', box(-1.6, GATE[1] + 0.8, 0.06, 1.6, -7.5, 0.085, 'A1A Bruk jasny'))
    add('site', 'Plac wejsciowy', box(-34, 0, 0.06, -29.3, 24, 0.075, 'A1A Bruk szary'))   # yard at the north-east end: a drive, not bays
    for (xa, xb) in ((-26.0, -3.0), (3.0, 26.0)):
        add('site', 'Trawniki', box(xa, -7.0, 0.075, xb, -4.6, 0.2, 'A1A Trawa boisko'))
    add('site', 'Trawniki', poly([(-29.3, 24.0), (4.5, 26.5), (36.0, 15.0), (44.0, 17.0), (0.0, 33.0), (-31.0, 45.0)], 0.0, 0.045, 'A1A Trawa', 'lawn'))
    # The entrance path is a pavement between the two car parks: a kerb and a narrow
    # lawn verge on both sides for its whole length, bollards where the aisles end.
    for s_ in (-1, 1):
        xa, xb = sorted((s_ * 1.6, s_ * 1.78))
        add('site', 'Chodnik - kraweznik', box(xa, GATE[1] + 0.8, 0.06, xb, -7.5, 0.2, 'A1A Beton'))
        xa, xb = sorted((s_ * 1.78, s_ * 2.6))
        add('site', 'Trawniki', box(xa, GATE[1] + 0.8, 0.05, xb, -7.5, 0.16, 'A1A Trawa boisko'))
    # entrance path: lanterns, stone bollards on the half next to the building
    for y in (-11.5, -21.5):
        for s in (-1, 1):
            lantern(s * 2.1, y)
    # bollards stand in a row along BOTH edges of the path where the aisles end:
    # they close the aisles off, nothing stands on the path itself
    y = -17.3
    while y < -13.6:
        for s in (-1, 1):
            bollard(s * 2.3, y)
        y += 0.9
    # row of bays in front of the building on both sides of the path
    x = -27.8                             # the first two bays by the gate stay empty
    while x < 35.6:
        if abs(x) > 3.2 and inside((x, -10.3), OWN_PARK) and not in_ramp((x, -10.3), 0.5) and rnd() < 0.35:
            car(x, -10.3, 90)
        x += 2.6
    # --- north-east side (-X), after the approved dusk picture: beyond the aisle a
    # block of bays where the cars stand side-on to the facade: two columns with a
    # drive lane between them (the lane at X = -11 stays empty)
    for xc in (-6.1, -16.1):
        for k in range(4):
            if rnd() < 0.4:
                car(xc, -19.5 - k * 2.6, 0)
    # --- south-west side (+X): rows on two aisles, a thin grass strip between them
    for (yrow, x0) in ((-20.4, 5.6), (-26.6, 5.6), (-37.6, 16.0)):
        x = x0
        while x < 35.6:
            if inside((x, yrow), OWN_PARK) and rnd() < 0.3:
                car(x, yrow, 90)
            x += 2.6
    add('site', 'Trawniki', box(4.4, -24.0, 0.06, 36.4, -23.0, 0.2, 'A1A Trawa boisko'))
    add('site', 'Trawniki', box(36.4, -27.0, 0.06, 39.4, -20.0, 0.2, 'A1A Trawa boisko'))   # island at the far end
    lantern(37.9, -23.5)


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
    if 20.0 < x < 50.0 and -66.0 < y < -42.0:
        return                            # keep the right gate and its drive in view
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
    # big clipped globes along the street half of the entrance path
    y = GATE[1] + 2.2
    while y < -21.0:
        for s in (-1, 1):
            shrub(s * 2.75, y, 0.85)
        y += 1.9
    for (x, y) in ((-24.0, -27.5), (-14.0, -31.0), (10.0, -41.0), (24.0, -45.5)):
        tree(x, y, 0.45)                  # young trees on the lawn inside the street fence
    for (x, y) in ((37.2, -30.5), (38.6, -33.0)):
        conifer(x, y, 0.8)                # conifers by the far island
    for s in (-1, 1):
        for k in range(5):
            shrub(s * (5.0 + k * 4.8), -5.8, 0.6, 0.15)
    # shrubs in the raised planter by the garage ramp
    for (x, y) in ((29.5, 1.5), (31.5, 3.6), (30.5, -1.5), (33.0, 0.5), (35.0, 3.5), (36.5, -1.0),
                   (38.5, 2.5), (38.5, -3.5), (34.5, -4.0), (32.0, -3.0), (36.8, 5.0), (39.8, -0.5)):
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
        if e.Name.startswith(prefix) or not (e.Name[:2] in ('S-', 'B-', 'P-')):
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


def basement_level():
    for l in FilteredElementCollector(doc).OfClass(Level):
        if l.Name == 'Piwnica':
            l.Elevation = BASE / F
            return l
    l = Level.Create(doc, BASE / F)
    l.Name = 'Piwnica'
    return l


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


def win_size(f, w, front, x):
    """Window width, height and sill for an opening of clear width w on floor f."""
    ww = round(max(0.6, w - 0.3) * 20) / 20.0
    if f == 0:
        return (ww, 3.1, 0.35)
    if f == 1:
        return (ww, 2.3, 0.8)
    big = w >= 3.5
    if f <= 4:
        if big:
            arched = front and 14.0 < abs(x - CX) < 22.0
            return (ww, 2.7 if (f == 4 and arched) else 3.5, 0.1)
        return (ww, 1.7, 0.95)
    if big:
        return (ww, 2.5, 0.1)
    return (ww, 1.3, 1.25)


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
    # windows: every opening between two piers on the floor plans becomes a window
    keys = ['01', '02', '03', '04', '05', '06']
    placed, bad = 0, 0
    first_window = [None]
    for f in range(len(FL)):
        on_floor = [(w, a, b) for (ff, i), (w, a, b) in SHELL.items() if ff == f]
        for o in PLANS['floors'][keys[f]].get('openings', []):
            p = o['p']
            best = None
            for (w, a, b) in on_floor:
                d = dist_seg(p, a, b)
                if best is None or d < best[0]:
                    best = (d, w, a, b)
            if best is None or best[0] > 0.7:
                continue
            d, w, a, b = best
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (L * L)
            ww, hh, ss = win_size(f, o['w'], abs(p[1]) < 0.4, p[0])
            if t * L - ww / 2.0 < 0.25 or (1 - t) * L - ww / 2.0 < 0.25:
                continue
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            try:
                inst = doc.Create.NewFamilyInstance(P(x, y, FL[f]), window_type(ww, hh), w, levels[f], StructuralType.NonStructural)
                inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(ss / F)
                placed += 1
                first_window[0] = inst
            except Exception:
                bad += 1
    # A window placed facing into the building does not cut the wall. Facing is only
    # reliable after a regeneration, so check and flip here, not while placing.
    doc.Regenerate()
    turned = 0
    for inst in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).OfClass(FamilyInstance):
        fo, wo = inst.FacingOrientation, inst.Host.Orientation
        if fo.X * wo.X + fo.Y * wo.Y < 0:
            inst.flipFacing()
            turned += 1
    LOG.append('windows: %d placed, %d failed, %d turned to face out' % (placed, bad, turned))
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

    build_facade_details()


def build_facade_details():
    n = len(OFFICE)
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
        """Continuous curtain-wall glazing with a mullion grid. On the real building
        the glass sits flush in the stone, so the panel is only 2 cm proud (enough to
        cover the slab edges) and the mullions 3 cm more."""
        if zp:
            add('win', 'Sciany kurtynowe', arched_panel(xc, w, z0, zs, zp, 0.02, K, 0.04))
        else:
            add('win', 'Sciany kurtynowe', box(xc - w / 2.0, -0.02, z0, xc + w / 2.0, 0.02, zs, K))
        for k in range(5):
            x = xc + w * (k / 4.0 - 0.5)
            add('win', 'Szprosy', box(x - 0.03, -0.05, z0, x + 0.03, -0.02, zs, M))
        z = z0
        while z <= zs + 0.01:
            add('win', 'Szprosy', box(xc - w / 2.0, -0.05, z - 0.03, xc + w / 2.0, -0.02, z + 0.03, M))
            z += 1.23

    curtain(CX, 5.6, FL[2] + 0.1, FL[5] + 2.4, FL[5] + 3.2)
    for s in (-1, 1):
        curtain(CX + s * 6.55, 4.3, FL[2] + 0.1, FL[5] + 2.8)
        curtain(CX + s * 18.0, 4.1, FL[2] + 0.1, FL[5] - 0.9, FL[5] + 0.4)
    # Central part of the front, after the photograph of the real facade: stone piers
    # between the three glazed bays stand slightly proud and carry a raised attic.
    ST = 'A1A Piaskowiec'
    for (xa, xb) in ((-9.75, -8.75), (-4.35, -2.85), (2.85, 4.35), (8.75, 9.75)):
        add('wall', 'Ryzalit srodkowy', box(CX + xa, -0.12, FL[2], CX + xb, 0.0, TOP + 0.9, ST))
    add('wall', 'Ryzalit srodkowy', box(CX - 9.75, -0.12, FL[5] + 3.3, CX + 9.75, 0.0, TOP + 0.9, ST))
    add('wall', 'Ryzalit srodkowy', box(CX - 9.75, -0.12, TOP, CX + 9.75, 0.9, TOP + 0.9, ST))
    add('wall', 'Gzymsy', box(CX - 10.05, -0.42, TOP + 0.9, CX + 10.05, 1.0, TOP + 1.05, D))
    # Entrance portal: stone infill with an arched window on the first floor and,
    # above it, the stone band that carries the name of the building.
    add('wall', 'Portal wejsciowy', box(CX - 2.95, -0.04, FL[1] + 0.55, CX + 2.95, 0.0, FL[2] - 0.3, ST))
    add('win', 'Sciany kurtynowe', arched_panel(CX, 3.0, FL[1] + 0.75, FL[1] + 1.9, FL[1] + 2.45, -0.04, K, 0.03))
    add('wall', 'Tablica z nazwa', box(CX - 2.6, -0.07, FL[1] + 2.62, CX + 2.6, -0.04, FL[1] + 3.3, D))
    # entrances: door frames, glass canopies on brackets, door mats
    for (xc, w, main) in ((CX, 3.0, True), (-19.4, 1.6, False), (19.1, 1.6, False)):
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
        add('site', 'Wycieraczki', box(xc - w / 2.0, -1.3, 0.07, xc + w / 2.0, -0.05, 0.1, 'A1A Stal'))
    # tenant boards beside the main entrance
    for s in (-1, 1):
        add('mech', 'Tablice najemcow', box(CX + s * 3.4 - 0.3, -0.26, 1.2, CX + s * 3.4 + 0.3, -0.2, 2.3, 'A1A Stal'))
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


TH_CLASSES = (0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.40)
WTYPES = {}
DTYPES = {}


def inner_wall_type(th, concrete=False):
    th = min(TH_CLASSES, key=lambda c: abs(c - th))
    key = (th, concrete)
    if key not in WTYPES:
        name = ('A1A Sciana zelbet %d' if concrete else 'A1A Sciana wewn %d') % int(round(th * 1000))
        WTYPES[key] = wall_type(name, ('200 mm',), 'A1A Beton' if concrete else 'A1A Tynk bialy', th)
    return WTYPES[key]


def door_type(w):
    w = 0.8 if w < 0.85 else 0.9 if w < 0.97 else 1.0 if w < 1.12 else 1.2
    if w in DTYPES:
        return DTYPES[w]
    base, sym = None, None
    name = 'A1A drzwi %d' % int(w * 1000)
    for s in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).OfClass(FamilySymbol):
        n = Element.Name.GetValue(s)
        if n == name:
            sym = s
        if '0915 x 2134' in n:
            base = s
    if sym is None:
        sym = base.Duplicate(name)
        for bip in (BuiltInParameter.DOOR_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM):
            p = sym.get_Parameter(bip)
            if p is not None and not p.IsReadOnly:
                p.Set(w / F)
                break
    if not sym.IsActive:
        sym.Activate()
    DTYPES[w] = sym
    return sym


def dedupe(walls):
    """Drop a wall when a thicker parallel wall covers most of it."""
    keep = []
    for i, w in enumerate(walls):
        a, b = w['a'], w['b']
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 0.2:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        drop = False
        for j, v in enumerate(walls):
            if j == i or v['th'] < w['th'] or (v['th'] == w['th'] and j > i):
                continue
            c, d = v['a'], v['b']
            Lv = math.hypot(d[0] - c[0], d[1] - c[1])
            if Lv < 0.2:
                continue
            if abs(((d[0] - c[0]) * uy - (d[1] - c[1]) * ux) / Lv) > 0.05:
                continue
            off = abs((c[0] - a[0]) * uy - (c[1] - a[1]) * ux)
            if off > (w['th'] + v['th']) / 2.0 + 0.05:
                continue
            s0, s1 = sorted(((c[0] - a[0]) * ux + (c[1] - a[1]) * uy, (d[0] - a[0]) * ux + (d[1] - a[1]) * uy))
            if min(s1, L) - max(s0, 0.0) > 0.6 * L:
                drop = True
                break
        if not drop:
            keep.append(i)
    return keep


ROOM_NAMES = {'0.1': 'Garaz', '0.10': 'Klatka schodowa', '0.12': 'Pomieszczenie techniczne',
              '0.13': 'Pomieszczenie techniczne', '0.14': 'Pomieszczenie techniczne'}


def room_name(label):
    if label in ROOM_NAMES:
        return ROOM_NAMES[label]
    if '.K.' in label:
        return 'Czesc wspolna'
    if label.startswith('0.'):
        return 'Komorka lokatorska'
    return 'Lokal'


def plan_view_for(lvl):
    """A floor plan of the level, used as the owner view of room separation lines."""
    name = 'A1A Robocze - %s' % lvl.Name
    for v in FilteredElementCollector(doc).OfClass(ViewPlan):
        if v.Name == name and not v.IsTemplate:
            return v
    pft = [x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType) if x.ViewFamily == ViewFamily.FloorPlan][0]
    v = ViewPlan.Create(doc, pft.Id, lvl.Id)
    v.Name = name
    return v


def build_plans(levels, base):
    LV = {'00': (base, BASE, 0.0), '01': (levels[0], FL[0], FL[1]), '02': (levels[1], FL[1], FL[2]),
          '03': (levels[2], FL[2], FL[3]), '04': (levels[3], FL[3], FL[4]), '05': (levels[4], FL[4], FL[5]),
          '06': (levels[5], FL[5], TOP)}
    ftype = type_by(FloorType, '300 mm')
    try:
        Floor.Create(doc, List[CurveLoop]([loop3([P(x, y, 0) for (x, y) in ccw(GARAGE)])]), ftype.Id, base.Id)
    except Exception as ex:
        LOG.append('garage slab: %s' % ex)
    stats = []
    for key in sorted(LV):
        lvl, z0, z1 = LV[key]
        fl = PLANS['floors'][key]
        h = (z1 - z0) - 0.3
        walls = fl['walls']
        made = {}
        for i in dedupe(walls):
            w = walls[i]
            a, b = w['a'], w['b']
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            if key == '00':
                if not inside(mid, GARAGE) and not inside(a, GARAGE):
                    continue                    # ramp walls outside are modelled with the site
            elif not inside(mid, OFFICE):
                continue
            try:
                wt = inner_wall_type(w['th'], concrete=(key == '00' or w['th'] >= 0.24))
                made[i] = Wall.Create(doc, Line.CreateBound(P(a[0], a[1], z0), P(b[0], b[1], z0)),
                                      wt.Id, lvl.Id, h / F, 0.0, False, False)
            except Exception:
                fail('plan wall')
        doc.Regenerate()
        nd = 0
        for d in fl['doors']:
            host = made.get(d['wall'])
            if host is None:
                continue
            try:
                doc.Create.NewFamilyInstance(P(d['p'][0], d['p'][1], z0), door_type(d['w']), host, lvl,
                                             StructuralType.NonStructural)
                nd += 1
            except Exception:
                fail('door')
        # openings without doors: room separation lines keep them open but close the rooms
        seps = fl.get('seps', [])
        if seps:
            try:
                view = plan_view_for(lvl)
                sp = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, P(0, 0, z0)))
                ca = CurveArray()
                for (a, b) in seps:
                    if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.05:
                        ca.Append(Line.CreateBound(P(a[0], a[1], z0), P(b[0], b[1], z0)))
                doc.Create.NewRoomBoundaryLines(sp, ca, view)
            except Exception as ex:
                LOG.append('separation lines %s: %s' % (key, ex))
        for c in fl['columns']:
            x, y = c['c']
            add('wall', 'Slupy', box(x - c['w'] / 2.0, y - c['h'] / 2.0, z0, x + c['w'] / 2.0, y + c['h'] / 2.0, z1 - 0.3, 'A1A Beton'))
        doc.Regenerate()
        nr = 0
        unnamed = [0]
        for r in fl['rooms']:
            x, y = r['p']
            if key == '00':
                if not inside((x, y), GARAGE):
                    continue
            elif not inside((x, y), OFFICE):
                continue
            try:
                rm = doc.Create.NewRoom(lvl, UV(x / F, y / F))
                label = r.get('label') or ''
                nn = r.get('n', 1)
                unnamed[0] += 0 if label else 1
                if key == '00' and r.get('model_area', 0) > 500:
                    rm.Number, rm.Name = '0.1', 'Garaz'
                elif label:
                    rm.Number = label if nn == 1 else '%s-%d' % (label, nn)
                    rm.Name = room_name(label)
                else:
                    rm.Number = '%s.x%d' % (key[1], unnamed[0])
                    rm.Name = 'Pomieszczenie'
                if r.get('area'):
                    cp = rm.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                    if cp is not None:
                        cp.Set('Powierzchnia wg rzutu: %.2f m2' % r['area'])
                nr += 1
            except Exception:
                fail('room')
        stats.append('%s: %d walls, %d doors, %d rooms, %d columns' % (key, len(made), nd, nr, len(fl['columns'])))
    # parking bays in the garage: painted lines and parked cars
    for b in PLANS['floors']['00'].get('bays', []):
        x, y = b['p']
        if not inside((x, y), GARAGE) or abs(x + 3.6) < 0.6 and abs(y - 4.1) < 0.6:
            continue
        ax = b['axis']
        hw, hl = 1.25, 2.5
        if ax == 'x':
            corners = [(x - hl, y - hw), (x + hl, y - hw), (x + hl, y + hw), (x - hl, y + hw)]
        else:
            corners = [(x - hw, y - hl), (x + hw, y - hl), (x + hw, y + hl), (x - hw, y + hl)]
        for k in range(4):
            add('site', 'Garaz - linie', seg(corners[k], corners[(k + 1) % 4], 0.1, BASE + 0.005, BASE + 0.02, 'A1A Tynk bialy'))
        if rnd() < 0.6:
            car(x, y, 0 if ax == 'x' else 90, BASE)
    LOG.append('plans: ' + '; '.join(stats))

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


def stage_plans():
    make_materials()
    delete_class(None, BuiltInCategory.OST_Rooms)
    old = List[ElementId]()
    for e in FilteredElementCollector(doc).OfClass(FamilyInstance):
        if e.Category is not None and e.Category.Id == ElementId(BuiltInCategory.OST_Doors):
            old.Add(e.Id)
    for e in FilteredElementCollector(doc).OfClass(Wall):
        if e.Name.startswith('A1A Sciana') or '138' in e.Name:
            old.Add(e.Id)
    for e in FilteredElementCollector(doc).OfClass(DirectShape):
        if e.Name.startswith('P-'):
            old.Add(e.Id)
    for e in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType():
        old.Add(e.Id)
    base = basement_level()
    for e in FilteredElementCollector(doc).OfClass(Floor):
        if e.LevelId == base.Id:
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)
    levels = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name in LEVEL_NAMES]
    levels.sort(key=lambda l: l.Elevation)
    build_plans(levels, base)
    flush('P-')

if 'site' in STAGES:
    run('A1A site', stage_site)
def stage_facade():
    make_materials()
    old = List[ElementId]()
    for e in FilteredElementCollector(doc).OfClass(DirectShape):
        if e.Name.startswith('B-'):
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)
    build_facade_details()
    flush('B-')


if 'facade' in STAGES:
    run('A1A facade', stage_facade)
if 'shell' in STAGES:
    run('A1A shell', stage_shell)
if 'plans' in STAGES or 'interior' in STAGES:
    run('A1A plans', stage_plans)
if FAIL:
    LOG.append('skipped solids: %s' % FAIL)
print('\n'.join(LOG))
