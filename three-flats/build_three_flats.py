# Builds the 3-flat layout in the open "Three_Flats" Revit document.
# Run inside Revit (IronPython) via:  exec(open(r'<this file>').read())
# Design coordinates are metres, origin = inner top-left corner of the shell,
# x to the right (east), y downwards (south). Revit Y = -y.
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from System.Collections.Generic import List
import math

app = __revit__.Application
doc = [d for d in app.Documents if d.Title == 'Three_Flats'][0]
F = 0.3048
LOG = []


def P(x, y, z=0.0):
    return XYZ(x / F, -y / F, z / F)


lv1 = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == 'Level 1'][0]


def sym(fam, typ=None):
    for s in FilteredElementCollector(doc).OfClass(FamilySymbol):
        if s.FamilyName == fam and (typ is None or Element.Name.GetValue(s) == typ):
            if not s.IsActive:
                s.Activate()
                doc.Regenerate()
            return s
    raise Exception('Missing type %s / %s' % (fam, typ))


def wall_type(name):
    return [t for t in FilteredElementCollector(doc).OfClass(WallType) if Element.Name.GetValue(t) == name][0]


def ensure_100mm():
    for t in FilteredElementCollector(doc).OfClass(WallType):
        if Element.Name.GetValue(t) == 'Generic - 100mm':
            return t
    base = wall_type('Generic - 150mm')
    nt = base.Duplicate('Generic - 100mm')
    cs = nt.GetCompoundStructure()
    idx = cs.GetFirstCoreLayerIndex()
    cs.SetLayerWidth(idx, 0.1 / F)
    nt.SetCompoundStructure(cs)
    return nt


t = Transaction(doc, 'Build three flats')
t.Start()
try:
    # ---- clean previous run -------------------------------------------------
    old = List[ElementId]()
    for cls in (FamilyInstance, Wall, Floor):
        for e in FilteredElementCollector(doc).OfClass(cls).WhereElementIsNotElementType():
            old.Add(e.Id)
    for bic in (BuiltInCategory.OST_Rooms, BuiltInCategory.OST_Stairs):
        for e in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            old.Add(e.Id)
    if old.Count:
        doc.Delete(old)

    W300 = wall_type('Generic - 300mm')
    W200 = wall_type('Generic - 200mm')
    # 123 mm stud partition: the library door families fail to build in walls thinner than ~120 mm
    W100 = wall_type('Interior - 123mm Partition (1-hr)')
    H = 3.0 / F
    walls = {}

    def wall(key, wt, x0, y0, x1, y1):
        w = Wall.Create(doc, Line.CreateBound(P(x0, y0), P(x1, y1)), wt.Id, lv1.Id, H, 0, False, False)
        walls[key] = w
        return w

    # ---- exterior shell (300) -----------------------------------------------
    wall('N', W300, -0.15, -0.15, 16.95, -0.15)
    wall('E', W300, 16.95, -0.15, 16.95, 11.95)
    wall('S', W300, 16.95, 11.95, -0.15, 11.95)
    wall('W', W300, -0.15, 11.95, -0.15, -0.15)
    # ---- separating walls between flats / core (200) ------------------------
    wall('sepA', W200, 11.1, -0.15, 11.1, 11.95)
    wall('sepB', W200, -0.15, 5.1, 11.1, 5.1)
    wall('sepC', W200, 5.8, 5.1, 5.8, 11.95)
    wall('coreW', W200, 7.55, 6.65, 7.55, 11.95)
    wall('liftN', W200, 7.55, 6.65, 9.65, 6.65)
    wall('liftE', W200, 9.65, 6.65, 9.65, 8.85)
    wall('liftS', W200, 7.55, 8.85, 9.65, 8.85)
    wall('lobbyN', W200, 7.55, 10.25, 11.1, 10.25)
    # ---- partitions (100) ---------------------------------------------------
    wall('B_kit_bed', W100, 7.55, -0.15, 7.55, 3.35)
    wall('B_mid', W100, 5.85, 3.35, 11.1, 3.35)
    wall('B_liv_hall', W100, 5.85, 3.35, 5.85, 5.1)
    wall('B_hall_bath', W100, 8.85, 3.35, 8.85, 5.1)
    wall('C_bed_E', W100, 3.45, 5.1, 3.45, 8.7)
    wall('C_bath_S', W100, 3.45, 7.25, 5.8, 7.25)
    wall('C_liv_N', W100, -0.15, 8.7, 5.8, 8.7)
    wall('A_bath_E', W100, 13.25, -0.15, 13.25, 3.65)
    wall('A_bath_S', W100, 11.1, 2.65, 13.25, 2.65)
    wall('A_hall_E', W100, 12.65, 3.65, 12.65, 7.05)
    wall('A_bed_mid', W100, 12.65, 3.65, 16.95, 3.65)
    wall('A_liv_N', W100, 11.1, 7.05, 16.95, 7.05)

    # ---- floor slab ---------------------------------------------------------
    loop = CurveLoop()
    pts = [(-0.3, -0.3), (17.1, -0.3), (17.1, 12.1), (-0.3, 12.1)]
    for i in range(4):
        loop.Append(Line.CreateBound(P(*pts[i]), P(*pts[(i + 1) % 4])))
    ftype = [ft for ft in FilteredElementCollector(doc).OfClass(FloorType) if Element.Name.GetValue(ft) == 'Generic Floor - 400mm'][0]
    Floor.Create(doc, List[CurveLoop]([loop]), ftype.Id, lv1.Id)
    doc.Regenerate()

    # ---- doors / openings ---------------------------------------------------
    def door(wkey, x, y, fam, typ, swing=None):
        s = sym(fam, typ)
        d = doc.Create.NewFamilyInstance(P(x, y), s, walls[wkey], lv1, StructuralType.NonStructural)
        doc.Regenerate()
        if swing is not None:
            v = XYZ(swing[0], -swing[1], 0)
            if d.FacingOrientation.DotProduct(v) < 0:
                d.flipFacing()
        return d

    D36, D30, D28 = '36" x 84"', '30" x 80"', '28" x 84"'
    SF = 'Door-Passage-Single-Flush'
    door('sepB', 6.5, 5.1, SF, D36, (0, -1))          # Flat B entrance
    door('B_liv_hall', 5.85, 4.1, 'Door-Opening', '36" x 84"')
    door('B_mid', 8.2, 3.35, SF, D30, (0, -1))        # B bedroom (clear of the bath wall junction)
    door('B_hall_bath', 8.85, 4.0, SF, D28, (1, 0))   # B bath
    door('sepC', 5.8, 8.0, SF, D36, (-1, 0))          # Flat C entrance (clear of the living wall junction)
    door('C_bed_E', 3.45, 7.9, SF, D30, (-1, 0))      # C bedroom
    door('C_bath_S', 4.4, 7.25, SF, D28, (0, -1))     # C bath
    door('C_liv_N', 4.6, 8.7, 'Door-Opening', '60" x 84"')
    door('sepA', 11.1, 5.85, SF, D36, (1, 0))         # Flat A entrance
    door('A_bath_S', 11.9, 2.65, SF, D28, (0, -1))    # A bath
    door('A_bath_E', 13.25, 3.15, SF, D28, (1, 0))    # A bedroom 1
    door('A_hall_E', 12.65, 5.0, SF, D30, (1, 0))     # A bedroom 2
    door('A_liv_N', 11.9, 7.05, 'Door-Opening', '36" x 84"')
    door('coreW', 7.55, 11.0, SF, D36, (1, 0))        # corridor -> lobby
    door('S', 9.9, 11.95, 'Door-Passage-Double-Flush', '68" x 84"', (0, -1))  # main entrance
    door('coreW', 7.55, 7.75, 'Elevator Door-Center', '900 x 2100mm', (-1, 0))

    # ---- windows ------------------------------------------------------------
    WD = 'Window-Double-Hung-Double'

    def window(wkey, x, y, fam, typ):
        doc.Create.NewFamilyInstance(P(x, y), sym(fam, typ), walls[wkey], lv1, StructuralType.NonStructural)

    window('N', 2.0, -0.15, WD, '76" x 62"')     # B living
    window('N', 6.4, -0.15, WD, '48" x 62"')     # B kitchen
    window('N', 9.3, -0.15, WD, '60" x 62"')     # B bedroom
    window('N', 12.2, -0.15, 'Window-Double-Hung', '30" x 46"')  # A bath
    window('N', 15.0, -0.15, WD, '60" x 62"')    # A bedroom 1
    window('W', -0.15, 2.0, WD, '60" x 62"')     # B living
    window('W', -0.15, 6.9, WD, '60" x 62"')     # C bedroom
    window('W', -0.15, 10.3, WD, '60" x 62"')    # C living
    window('E', 16.95, 1.8, WD, '48" x 62"')     # A bedroom 1
    window('E', 16.95, 5.3, WD, '60" x 62"')     # A bedroom 2
    window('E', 16.95, 9.4, WD, '76" x 62"')     # A living
    window('S', 2.7, 11.95, WD, '76" x 62"')     # C living
    window('S', 14.3, 11.95, WD, '76" x 62"')    # A living
    doc.Regenerate()

    # ---- furniture ----------------------------------------------------------
    ROT = {'N': 0.0, 'W': 90.0, 'S': 180.0, 'E': -90.0, None: 0.0}

    def put(fam, typ, x0, y0, x1, y1, back=None, length=None):
        """Place a family so its footprint sits in rect (x0,y0)-(x1,y1),
        with its back against the given side of the rect (N/S/E/W)."""
        s = sym(fam, typ)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        inst = doc.Create.NewFamilyInstance(P(cx, cy), s, lv1, StructuralType.NonStructural)
        if length is not None:
            for pn in ('Length', 'Width'):
                p = inst.LookupParameter(pn)
                if p is not None and not p.IsReadOnly:
                    p.Set(length / F)
                    break
        doc.Regenerate()
        a = ROT[back]
        if a:
            ax = Line.CreateBound(P(cx, cy), P(cx, cy, 1.0))
            ElementTransformUtils.RotateElement(doc, inst.Id, ax, math.radians(a))
            doc.Regenerate()
        b = inst.get_BoundingBox(None)
        bx0, bx1 = b.Min.X * F, b.Max.X * F
        by0, by1 = -b.Max.Y * F, -b.Min.Y * F
        sx = cx - (bx0 + bx1) / 2.0
        sy = cy - (by0 + by1) / 2.0
        if back == 'N': sy = y0 - by0
        if back == 'S': sy = y1 - by1
        if back == 'W': sx = x0 - bx0
        if back == 'E': sx = x1 - bx1
        ElementTransformUtils.MoveElement(doc, inst.Id, XYZ(sx / F, -sy / F, 0))
        return inst

    BED, NT, WR, CH = 'Bed-Shaker', 'Table-Trio End', 'Tall Cabinet-Double Door w Glass', 'Vanity Cabinet-Double Door & 4 Drawer'
    BASE, CT, FR = 'Base Cabinet-Double Door & 1 Drawer', 'Counter Top', 'Refrigerator'

    # Flat B - kitchen along north wall
    put(FR, '24" x 25" RH', 6.85, 0, 7.5, 0.8, 'N')
    put(BASE, '36"', 5.9, 0, 6.85, 0.9, 'N')
    put('Dishwasher', '24"', 5.3, 0, 5.9, 1.5, 'N')
    put(BASE, '36"', 4.35, 0, 5.3, 0.9, 'N')
    put(CT, '24" Depth', 4.35, 0, 6.85, 0.9, 'N', length=2.5)
    put('Sink Kitchen-Island', '18" x 18"', 6.0, 0.02, 6.75, 0.7, 'N')
    put('Cook Top-4 Unit2', '22" x 20"', 4.5, 0.05, 5.15, 0.65)
    # Flat B - living / dining, zoned west -> east: study corner, sofa + TV, dining, kitchen
    # dining sits between kitchen and sofa, 1.2 m clear of the worktop
    put('Table-Dining Round w Chairs', '36" Diameter', 4.2, 2.0, 5.6, 3.4)
    # TV unit on the solid south wall, sofa (two 2-seaters) facing it
    put('Shelving', '72" x 12" x 72"', 1.35, 4.65, 3.2, 5.0, 'S')
    put('Banquette - Double', None, 0.8, 2.0, 2.26, 2.95, 'N')
    put('Banquette - Double', None, 2.26, 2.0, 3.72, 2.95, 'N')
    put('Table-Rectangular', '44" x 30"', 1.7, 3.25, 2.82, 4.0)
    put('Chair-Breuer', 'Chair-Breuer', 0.2, 3.35, 0.7, 3.85, 'W')
    put(NT, '500mm Diameter', 0.15, 2.25, 0.65, 2.75)
    # study corner behind the sofa, daylight from the west window
    put('Table-Rectangular', '44" x 30"', 0.15, 0, 1.3, 0.76, 'N')
    put('Chair-Breuer', 'Chair-Breuer', 0.45, 0.85, 0.95, 1.35)
    put('Shelving', '36" x 10" x 72"', 3.1, 0, 4.2, 0.3, 'N')
    # Flat B - bedroom
    put(BED, 'Queen 62" x 83"', 8.8, 0.4, 11.0, 2.6, 'E')
    put(NT, '500mm Diameter', 10.5, 0.1, 11.0, 0.6, 'E')
    put(NT, '500mm Diameter', 10.5, 2.4, 11.0, 2.9, 'E')
    put(CH, '48"', 7.6, 0.1, 8.7, 1.4, 'W')
    put(WR, '30"', 7.6, 1.5, 8.6, 2.3, 'W')
    # Flat B - hall + bath
    put(WR, '36"', 7.0, 4.0, 8.0, 5.0, 'S')
    put('Stacked Washer and Dryer', '26"x25" - Private', 8.1, 4.3, 8.8, 5.0, 'S')
    put('Shower Stall - Rectangular', '34"x32" - Private', 10.14, 3.4, 11.0, 4.21, 'N')
    put('Toilet-Domestic-3D', None, 10.0, 4.3, 11.0, 4.95, 'E')
    put('Sink Vanity-Round', '19" x 19"', 9.2, 4.4, 9.8, 5.0, 'S')

    # Flat C - bedroom
    put(BED, 'Double 56" x 78"', 0.75, 5.2, 2.25, 7.3, 'N')
    put(NT, '500mm Diameter', 0.0, 5.2, 0.5, 5.7, 'N')
    put(NT, '500mm Diameter', 2.3, 5.2, 2.8, 5.7, 'N')
    put(WR, '42"', 2.5, 5.95, 3.4, 7.05, 'E')
    put(CH, '48"', 0.2, 7.6, 1.6, 8.65, 'S')
    # Flat C - bath
    put('Shower Stall - Rectangular', '36"x36" - Private', 4.79, 5.2, 5.7, 6.11, 'N')
    put('Toilet-Domestic-3D', None, 4.7, 6.3, 5.7, 6.95, 'E')
    put('Sink Vanity-Round', '19" x 19"', 3.5, 5.5, 4.0, 6.1, 'W')
    # Flat C - kitchen along east wall
    put(FR, '24" x 25" LH', 5.0, 8.85, 5.7, 9.45, 'E')
    put(BASE, '36"', 4.8, 9.45, 5.7, 10.4, 'E')
    put(BASE, '36"', 4.8, 10.4, 5.7, 11.35, 'E')
    put(CT, '24" Depth', 4.8, 9.45, 5.7, 11.35, 'E', length=1.9)
    put('Sink Kitchen-Island', '18" x 18"', 5.0, 9.5, 5.68, 10.35, 'E')
    put('Cook Top-4 Unit2', '22" x 20"', 4.95, 10.55, 5.6, 11.2)
    # Flat C - living / dining
    put('Banquette - Double', None, 0.6, 10.8, 3.0, 11.8, 'S')
    put('Table-Rectangular', '36" x 36"', 1.35, 9.6, 2.25, 10.5)
    put('Shelving', '72" x 12" x 72"', 0.9, 8.75, 2.7, 9.1, 'N')
    put('Table-Dining Round w Chairs', '36" Diameter', 3.0, 9.9, 4.4, 11.3)

    # Flat A - bath
    put('Shower Stall - Rectangular', '36"x36" - Private', 12.29, 0, 13.2, 0.91, 'N')
    put('Toilet-Domestic-3D', None, 12.2, 1.3, 13.2, 1.9, 'E')
    put('Sink Vanity-Round', '19" x 19"', 11.2, 1.0, 11.7, 1.6, 'W')
    put('Stacked Washer and Dryer', '26"x25" - Private', 11.2, 0, 11.9, 0.7, 'W')
    # Flat A - hall
    put(WR, '36"', 11.2, 3.85, 12.1, 4.85, 'W')
    # Flat A - bedroom 1
    put(BED, 'Queen 62" x 83"', 13.3, 0.3, 15.5, 2.5, 'W')
    put(NT, '500mm Diameter', 13.3, 0.0, 13.8, 0.5, 'W')
    put(NT, '500mm Diameter', 13.3, 2.3, 13.8, 2.8, 'W')
    put(WR, '48"', 15.4, 2.6, 16.8, 3.6, 'S')
    put(CH, '48"', 14.1, 2.6, 15.4, 3.6, 'S')
    put('Table-Rectangular', '44" x 30"', 15.9, 1.2, 16.8, 2.4, 'E')
    put('Chair-Breuer', 'Chair-Breuer', 15.5, 1.55, 16.0, 2.05)
    # Flat A - bedroom 2
    put(BED, 'Double 56" x 78"', 14.2, 3.7, 15.8, 5.8, 'N')
    put(NT, '500mm Diameter', 13.6, 3.7, 14.1, 4.2, 'N')
    put(NT, '500mm Diameter', 15.9, 3.7, 16.4, 4.2, 'N')
    put(WR, '42"', 13.0, 6.0, 14.2, 7.0, 'S')
    put('Table-Rectangular', '44" x 30"', 15.2, 6.0, 16.6, 7.0, 'S')
    put('Chair-Breuer', 'Chair-Breuer', 15.65, 5.75, 16.15, 6.2)
    put(CH, '48"', 15.8, 4.45, 16.8, 5.75, 'E')
    # Flat A - kitchen along west wall
    put(FR, '24" x 25" LH', 11.2, 8.3, 12.0, 8.9, 'W')
    put(BASE, '36"', 11.2, 8.9, 12.1, 9.85, 'W')
    put('Dishwasher', '24"', 11.2, 9.85, 12.7, 10.45, 'W')
    put(BASE, '36"', 11.2, 10.45, 12.1, 11.4, 'W')
    put(CT, '24" Depth', 11.2, 8.9, 12.1, 11.4, 'W', length=2.5)
    put('Sink Kitchen-Island', '18" x 18"', 11.22, 8.95, 11.9, 9.8, 'W')
    put('Cook Top-4 Unit2', '22" x 20"', 11.3, 10.6, 11.95, 11.25)
    # Flat A - living / dining
    put('Table-Dining Round w Chairs', '36" Diameter', 12.6, 8.4, 14.0, 9.8)
    put('Banquette - Double', None, 14.0, 10.8, 16.4, 11.8, 'S')
    put('Table-Rectangular', '36" x 36"', 14.75, 9.55, 15.65, 10.45)
    put('Shelving', '72" x 12" x 72"', 14.3, 7.1, 16.1, 7.45, 'N')
    put('Chair-Breuer', 'Chair-Breuer', 16.1, 9.75, 16.6, 10.25)

    # ---- wall-hosted items: kitchen wall cupboards and bathroom mirrors ----
    def hosted(wkey, x, y, fam, typ, elev, into):
        """Place a wall-based family on wall `wkey` at (x, y), facing `into` the room."""
        inst = doc.Create.NewFamilyInstance(P(x, y, elev), sym(fam, typ), walls[wkey], lv1, StructuralType.NonStructural)
        doc.Regenerate()
        v = XYZ(into[0], -into[1], 0)
        if inst.FacingOrientation.DotProduct(v) < 0 and inst.CanFlipFacing:
            inst.flipFacing()
            doc.Regenerate()
        b = inst.get_BoundingBox(None)
        LOG.append('hosted %s %s: x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (
            fam, typ, b.Min.X * F, b.Max.X * F, -b.Max.Y * F, -b.Min.Y * F, b.Min.Z * F, b.Max.Z * F))
        return inst

    UP = 'Upper Cabinet-Double Door-Wall'
    hosted('N', 4.85, 0.0, UP, '36"', 1.45, (0, 1))            # B kitchen (window takes the rest of the wall)
    hosted('sepC', 5.7, 9.92, UP, '36"', 1.45, (-1, 0))        # C kitchen
    hosted('sepC', 5.7, 10.86, UP, '36"', 1.45, (-1, 0))
    hosted('sepA', 11.2, 9.36, UP, '36"', 1.45, (1, 0))        # A kitchen
    hosted('sepA', 11.2, 10.28, UP, '36"', 1.45, (1, 0))
    hosted('sepA', 11.2, 11.12, UP, '30"', 1.45, (1, 0))
    hosted('sepA', 11.2, 1.3, 'Mirror', '36" x 48"', 1.0, (1, 0))       # A bath, over basin
    hosted('sepB', 9.5, 5.0, 'Mirror', '36" x 48"', 1.0, (0, -1))       # B bath
    hosted('C_bed_E', 3.5, 5.8, 'Mirror', '36" x 48"', 1.0, (1, 0))     # C bath

    # ---- rooms --------------------------------------------------------------
    doc.Regenerate()
    rooms = [
        ('A.1', 'Living + kitchen', 15.2, 8.5), ('A.2', 'Bedroom 1', 14.5, 1.4), ('A.3', 'Bedroom 2', 14.0, 5.0),
        ('A.4', 'Bath', 11.9, 1.6), ('A.5', 'Hall', 12.15, 6.8),
        ('B.1', 'Living + kitchen', 3.0, 2.5), ('B.2', 'Bedroom', 9.3, 2.8), ('B.3', 'Bath', 9.6, 4.0), ('B.4', 'Hall', 7.3, 3.95),
        ('C.1', 'Living + kitchen', 3.7, 9.35), ('C.2', 'Bedroom', 1.5, 7.8), ('C.3', 'Bath', 4.0, 6.7), ('C.4', 'Hall', 4.2, 8.0),
        ('0.1', 'Shared hall', 6.7, 7.5), ('0.2', 'Lift', 8.6, 7.75), ('0.3', 'Stair', 10.3, 8.0), ('0.4', 'Entrance lobby', 9.3, 11.0),
    ]
    plan = [v for v in FilteredElementCollector(doc).OfClass(ViewPlan) if v.Name == 'Level 1' and v.ViewType == ViewType.FloorPlan][0]
    TAG_AT = {'0.3': (10.35, 6.45), 'B.1': (2.7, 1.25), 'A.4': (12.65, 2.3)}  # tags placed away from their room point (keeps stair treads clear)
    for num, name, x, y in rooms:
        r = doc.Create.NewRoom(lv1, UV(x / F, -y / F))
        r.Number = num
        r.Name = name
        try:
            tx, ty = TAG_AT.get(num, (x, y))
            doc.Create.NewRoomTag(LinkElementId(r.Id), UV(tx / F, -ty / F), plan.Id)
        except Exception as e:
            LOG.append('tag %s: %s' % (num, e))
    t.Commit()
except Exception as e:
    import traceback
    t.RollBack()
    LOG.append('ROLLED BACK: %s' % traceback.format_exc())

# ---- core stair: U-shape, 17 risers x 176 mm, 280 mm treads, 1.2 m runs ------
from Autodesk.Revit.DB.Architecture import StairsRun, StairsRunJustification, StairsLanding  # StairsEditScope lives in DB


class _QuietWarnings(IFailuresPreprocessor):
    # keep warnings in the model (they are listed below), just don't stop the commit
    def PreprocessFailures(self, fa):
        return FailureProcessingResult.Continue


lv2 = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == 'Level 2'][0]
TREAD = 0.28
scope = StairsEditScope(doc, 'Core stair')
sid = scope.Start(lv1.Id, lv2.Id)
ts = Transaction(doc, 'Stair runs')
ts.Start()
try:
    st = doc.GetElement(sid)
    st.DesiredRisersNumber = 17
    st.ActualTreadDepth = TREAD / F
    r1 = StairsRun.CreateStraightRun(doc, sid, Line.CreateBound(P(10.375, 6.75), P(10.375, 6.75 + 8 * TREAD)), StairsRunJustification.Center)
    r1.ActualRunWidth = 1.2 / F
    z = r1.TopElevation * F
    r2 = StairsRun.CreateStraightRun(doc, sid, Line.CreateBound(P(9.7, 9.55, z), P(9.7 - 7 * TREAD, 9.55, z)), StairsRunJustification.Center)
    r2.ActualRunWidth = 1.2 / F
    StairsLanding.CreateAutomaticLanding(doc, r1.Id, r2.Id)
    ts.Commit()
    scope.Commit(_QuietWarnings())
except Exception:
    import traceback
    if ts.HasStarted() and not ts.HasEnded():
        ts.RollBack()
    if scope.IsActive:
        scope.Cancel()
    LOG.append('STAIR FAILED: %s' % traceback.format_exc())

for l in LOG:
    print(l)
for w in doc.GetWarnings():
    print('WARNING:', w.GetDescriptionText())
print('walls', FilteredElementCollector(doc).OfClass(Wall).GetElementCount(),
      'instances', FilteredElementCollector(doc).OfClass(FamilyInstance).GetElementCount())
for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
    print('%s %s %.1f m2' % (r.Number, r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(), r.Area * F * F))
