# Creates the review cameras in the open "Abrahama_1A" document and exports
# them as PNG files to exports/. Run inside Revit (IronPython) with exec().
from Autodesk.Revit.DB import *
from System.Collections.Generic import List
import os, math

app = __revit__.Application
doc = [d for d in app.Documents if d.Title == 'Abrahama_1A'][0]
F = 0.3048
OUT = r'C:\Users\USER\Documents\GitHub\AdventOfCode\Claude_higgsfield_revit\abrahama-1a\exports'
if not os.path.isdir(OUT):
    os.makedirs(OUT)


def P(x, y, z):
    return XYZ(x / F, y / F, z / F)


# name, eye, target, half width of the crop (wider = wider lens), file name
CAMERAS = [
    ('A1A 01 Front z zachodu', (92, -70, 58), (6, 8, 8), 0.058, 'ujecie-01-front'),
    ('A1A 02 Wjazd do garazu', (62, -26, 24), (41, 4, -1.5), 0.058, 'ujecie-02-garaz'),
    ('A1A 11 Od ulicy', (8, -108, 68), (4, -19, 3), 0.058, 'ujecie-11-od-ulicy'),
    ('A1A 20 Dojazd do zjazdu', (26, -44, 34), (43, -13, 0), 0.058, 'ujecie-20-dojazd-zjazd'),
    ('A1A 21 Parking lewy', (34, -58, 36), (-15, -17, 0), 0.05, 'ujecie-21-parking-lewy'),
    ('A1A 22 Furtka', (7, -22, 8), (0, -37, 0.8), 0.058, 'ujecie-22-furtka'),
    ('A1A 23 Furtka od ulicy', (-5, -50, 5), (0, -36, 1.2), 0.058, 'ujecie-23-furtka-ulica'),
    ('A1A 30 Hero skos', (56, -88, 34), (4, -10, 8), 0.058, 'ujecie-30-hero-skos'),
    ('A1A 32 Wejscie z chodnika', (0.5, -33.5, 1.8), (0, -2, 7), 0.058, 'ujecie-32-wejscie-oko'),
    ('A1A 12 Brama lewa', (-62, -44, 16), (-42, -20, 1), 0.058, 'ujecie-12-brama-lewa'),
    ('A1A 13 Brama prawa', (52, -72, 16), (41, -50, 1), 0.058, 'ujecie-13-brama-prawa'),
    ('A1A 08 Jak na filmie', (74, -60, 40), (9, 5, 9), 0.05, 'ujecie-08-jak-film'),
    ('A1A 09 Wejscie i brama', (5, -60, 13), (0, -8, 7), 0.058, 'ujecie-09-wejscie'),
    ('A1A 10 Front na wprost', (0, -70, 26), (0, 0, 11), 0.058, 'ujecie-10-front-wprost'),
    ('A1A 03 Szczyt polnocny', (-86, 30, 44), (-10, 12, 9), 0.058, 'ujecie-03-szczyt'),
    ('A1A 04 Od strony torow', (30, 105, 62), (2, 10, 8), 0.058, 'ujecie-04-tory'),
    ('A1A 05 Z gory', (0, -1, 330), (0, 0, 0), 0.05, 'ujecie-05-z-gory'),
    ('A1A 06 Okolica', (190, -210, 190), (0, 20, 0), 0.058, 'ujecie-06-okolica'),
]
try:
    ONLY
except NameError:
    ONLY = None

vft = [x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType) if x.ViewFamily == ViewFamily.ThreeDimensional][0]
old = dict((v.Name, v) for v in FilteredElementCollector(doc).OfClass(View3D))
made = []
t = Transaction(doc, 'A1A cameras')
t.Start()
for (name, eye, tgt, hx, fname) in CAMERAS:
    if ONLY and fname not in ONLY:
        continue
    v = old.get(name)
    if v is None:
        v = View3D.CreatePerspective(doc, vft.Id)
        v.Name = name
    e, g = P(*eye), P(*tgt)
    fwd = (g - e).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ)
    if right.GetLength() < 1e-6:
        right = XYZ.BasisX
    right = right.Normalize()
    up = right.CrossProduct(fwd).Normalize()
    v.SetOrientation(ViewOrientation3D(e, up, fwd))
    doc.Regenerate()
    cb = v.CropBox
    cb.Min = XYZ(-hx, -hx * 9.0 / 16.0, cb.Min.Z)
    cb.Max = XYZ(hx, hx * 9.0 / 16.0, cb.Max.Z)
    v.CropBox = cb
    v.CropBoxActive = True
    v.CropBoxVisible = False
    v.DisplayStyle = DisplayStyle.Shading
    try:
        # light the model from the camera side so the visible facades are not in shade
        sun = v.SunAndShadowSettings
        sun.SunAndShadowType = SunAndShadowType.Lighting
        sun.RelativeToView = True
        sun.Azimuth = math.radians(190.0)
        sun.Altitude = math.radians(38.0)
        v.SunlightIntensity = 28
        v.ShadowIntensity = 45
    except Exception as ex:
        print('sun', ex)
    try:
        v.SetCategoryHidden(ElementId(BuiltInCategory.OST_Levels), True)   # level lines show up in 3D views
    except Exception as ex:
        print('levels', ex)
    v.DetailLevel = ViewDetailLevel.Fine
    try:
        v.SetBackground(ViewDisplayBackground.CreateGradient(Color(150, 185, 225), Color(215, 228, 240), Color(120, 140, 110)))
    except Exception:
        pass
    made.append((v, fname))

# cut-away isometrics of single floors and their floor plans
CUTS = [('A1A 07 Pietro 1 - przekroj', 4.6, 'ujecie-07-pietro-1', (20, -60, 90)),
        ('A1A 14 Garaz - przekroj', -3.2, 'ujecie-14-garaz', (20, -62, 80)),
        ('A1A 15 Parter - przekroj', 0.0, 'ujecie-15-parter', (24, -62, 84)),
        ('A1A 16 Pietro 2 - przekroj', 8.3, 'ujecie-16-pietro-2', (20, -60, 90)),
        ('A1A 17 Pietro 3 - przekroj', 12.0, 'ujecie-17-pietro-3', (20, -60, 94)),
        ('A1A 18 Pietro 4 - przekroj', 15.7, 'ujecie-18-pietro-4', (20, -60, 98)),
        ('A1A 19 Pietro 5 - przekroj', 19.4, 'ujecie-19-pietro-5', (20, -60, 102))]
for (name, z, fname, eye) in CUTS:
    if ONLY and fname not in ONLY:
        continue
    v = old.get(name)
    if v is None:
        v = View3D.CreateIsometric(doc, vft.Id)
        v.Name = name
    bb = BoundingBoxXYZ()
    bb.Min = P(-31, -6 if z < 0 else -2, z - 0.4)
    bb.Max = P(50 if z <= 0 else 38, 28, z + (2.4 if z < 0 else 2.6))
    v.SetSectionBox(bb)
    e, g = P(*eye), P(5, 10, z)
    fwd = (g - e).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ).Normalize()
    v.SetOrientation(ViewOrientation3D(e, right.CrossProduct(fwd).Normalize(), fwd))
    v.DisplayStyle = DisplayStyle.Shading
    v.DetailLevel = ViewDetailLevel.Fine
    hide = [BuiltInCategory.OST_Levels, BuiltInCategory.OST_RoomSeparationLines, BuiltInCategory.OST_SectionBox]
    if z >= 0:
        hide += [BuiltInCategory.OST_Site, BuiltInCategory.OST_Planting, BuiltInCategory.OST_Entourage]
    for bic in hide:
        try:
            v.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    made.append((v, fname))

# the whole building opened along the front: every floor and the garage seen at an angle
if not ONLY or 'ujecie-31-przekroj-skos' in ONLY:
    name = 'A1A 31 Przekroj skos'
    v = old.get(name)
    if v is None:
        v = View3D.CreateIsometric(doc, vft.Id)
        v.Name = name
    bb = BoundingBoxXYZ()
    bb.Min = P(-31, 3.2, -3.6)
    bb.Max = P(50, 28, 23.6)
    v.SetSectionBox(bb)
    e, g = P(58, -78, 50), P(4, 12, 8)
    fwd = (g - e).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ).Normalize()
    v.SetOrientation(ViewOrientation3D(e, right.CrossProduct(fwd).Normalize(), fwd))
    v.DisplayStyle = DisplayStyle.Shading
    v.DetailLevel = ViewDetailLevel.Fine
    for bic in (BuiltInCategory.OST_Levels, BuiltInCategory.OST_RoomSeparationLines, BuiltInCategory.OST_SectionBox,
                BuiltInCategory.OST_Planting, BuiltInCategory.OST_Entourage):
        try:
            v.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    made.append((v, 'ujecie-31-przekroj-skos'))

PLANS_V = [('A1A Rzut - Piwnica', 'Piwnica', 'rzut-piwnica', (-33, -8, 52, 27)),
           ('A1A Rzut - Parter', 'Parter', 'rzut-parter', (-33, -17, 52, 29)),
           ('A1A Rzut - Pietro 1', 'Pietro 1', 'rzut-pietro-1', (-33, -3, 40, 29)),
           ('A1A Rzut - Pietro 2', 'Pietro 2', 'rzut-pietro-2', (-33, -3, 40, 29)),
           ('A1A Rzut - Pietro 3', 'Pietro 3', 'rzut-pietro-3', (-33, -3, 40, 29)),
           ('A1A Rzut - Pietro 4', 'Pietro 4', 'rzut-pietro-4', (-33, -3, 40, 29)),
           ('A1A Rzut - Pietro 5', 'Pietro 5', 'rzut-pietro-5', (-33, -3, 40, 29))]
pft = [x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType) if x.ViewFamily == ViewFamily.FloorPlan][0]
for (name, lname, fname, crop) in PLANS_V:
    if ONLY and fname not in ONLY:
        continue
    lvl = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == lname][0]
    pv = None
    for x in FilteredElementCollector(doc).OfClass(ViewPlan):
        if x.Name == name:
            pv = x
    if pv is None:
        pv = ViewPlan.Create(doc, pft.Id, lvl.Id)
        pv.Name = name
    pv.Scale = 100
    pv.DetailLevel = ViewDetailLevel.Medium
    for bic in (BuiltInCategory.OST_Site, BuiltInCategory.OST_Planting, BuiltInCategory.OST_Roofs,
                BuiltInCategory.OST_RoomSeparationLines):
        try:
            pv.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    if lname != 'Piwnica':
        try:
            pv.SetCategoryHidden(ElementId(BuiltInCategory.OST_Entourage), True)
        except Exception:
            pass
    cb = pv.CropBox
    cb.Min = XYZ(crop[0] / F, crop[1] / F, cb.Min.Z)
    cb.Max = XYZ(crop[2] / F, crop[3] / F, cb.Max.Z)
    pv.CropBox = cb
    pv.CropBoxActive = True
    pv.CropBoxVisible = False
    doc.Regenerate()
    tagged = set()
    for tg in FilteredElementCollector(doc, pv.Id).OfCategory(BuiltInCategory.OST_RoomTags):
        try:
            tagged.add(tg.Room.Id)
        except Exception:
            pass
    for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms):
        if r.LevelId == lvl.Id and r.Area > 0 and r.Id not in tagged:
            try:
                pt = r.Location.Point
                doc.Create.NewRoomTag(LinkElementId(r.Id), UV(pt.X, pt.Y), pv.Id)
            except Exception as ex:
                print('tag', ex)
    made.append((pv, fname))
# the units that go on the website: a plan and a cut-away of each
import json
PL = json.load(open(os.path.join(os.path.dirname(OUT), 'plans.json')))
UNITS = [('02', ['2.01/2.09'], 'Pietro 1', 4.6, 'lokal-2.01-2.09'),
         ('03', ['3.05', '3.05B'], 'Pietro 2', 8.3, 'lokal-3.05'),
         ('04', ['4.12'], 'Pietro 3', 12.0, 'lokal-4.12'),
         ('05', ['5.06/5.07'], 'Pietro 4', 15.7, 'lokal-5.06-5.07')]
for (key, labels, lname, z, fname) in UNITS:
    if ONLY and fname not in ONLY:
        continue
    bbs = [PL['floors'][key]['units'][l]['bbox'] for l in labels if l in PL['floors'][key]['units']]
    if not bbs:
        print('no unit', labels)
        continue
    x0, y0 = min(b[0] for b in bbs), min(b[1] for b in bbs)
    x1, y1 = max(b[2] for b in bbs), max(b[3] for b in bbs)
    lvl = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == lname][0]
    name = 'A1A Lokal %s - rzut' % fname[6:]
    pv = None
    for x in FilteredElementCollector(doc).OfClass(ViewPlan):
        if x.Name == name:
            pv = x
    if pv is None:
        pv = ViewPlan.Create(doc, pft.Id, lvl.Id)
        pv.Name = name
    pv.Scale = 50
    pv.DetailLevel = ViewDetailLevel.Medium
    for bic in (BuiltInCategory.OST_Site, BuiltInCategory.OST_Planting, BuiltInCategory.OST_Roofs, BuiltInCategory.OST_Entourage,
                BuiltInCategory.OST_RoomSeparationLines):
        try:
            pv.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    cb = pv.CropBox
    cb.Min = XYZ((x0 - 1.3) / F, (y0 - 1.3) / F, cb.Min.Z)
    cb.Max = XYZ((x1 + 1.3) / F, (y1 + 1.3) / F, cb.Max.Z)
    pv.CropBox = cb
    pv.CropBoxActive = True
    pv.CropBoxVisible = False
    doc.Regenerate()
    tagged = set()
    for tg in FilteredElementCollector(doc, pv.Id).OfCategory(BuiltInCategory.OST_RoomTags):
        try:
            tagged.add(tg.Room.Id)
        except Exception:
            pass
    for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms):
        if r.LevelId == lvl.Id and r.Area > 0 and r.Id not in tagged:
            pt = r.Location.Point
            if x0 - 0.5 < pt.X * F < x1 + 0.5 and y0 - 0.5 < pt.Y * F < y1 + 0.5:
                try:
                    doc.Create.NewRoomTag(LinkElementId(r.Id), UV(pt.X, pt.Y), pv.Id)
                except Exception as ex:
                    print('tag', ex)
    made.append((pv, fname + '-rzut'))
    name = 'A1A Lokal %s - 3D' % fname[6:]
    v3 = old.get(name)
    if v3 is None:
        v3 = View3D.CreateIsometric(doc, vft.Id)
        v3.Name = name
    bb = BoundingBoxXYZ()
    bb.Min = P(x0 - 0.7, y0 - 0.7, z - 0.35)
    bb.Max = P(x1 + 0.7, y1 + 0.7, z + 2.7)
    v3.SetSectionBox(bb)
    e, g = P((x0 + x1) / 2.0 + 6.0, y0 - 22.0, z + 34.0), P((x0 + x1) / 2.0, (y0 + y1) / 2.0, z)
    fwd = (g - e).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ).Normalize()
    v3.SetOrientation(ViewOrientation3D(e, right.CrossProduct(fwd).Normalize(), fwd))
    v3.DisplayStyle = DisplayStyle.Shading
    v3.DetailLevel = ViewDetailLevel.Fine
    for bic in (BuiltInCategory.OST_Levels, BuiltInCategory.OST_RoomSeparationLines, BuiltInCategory.OST_SectionBox, BuiltInCategory.OST_Site,
                BuiltInCategory.OST_Planting, BuiltInCategory.OST_Entourage):
        try:
            v3.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    made.append((v3, fname + '-3d'))
t.Commit()

for (v, fname) in made:
    o = ImageExportOptions()
    o.ExportRange = ExportRange.SetOfViews
    o.SetViewsAndSheets(List[ElementId]([v.Id]))
    o.FilePath = os.path.join(OUT, 'tmp')
    o.ZoomType = ZoomFitType.FitToPage
    o.FitDirection = FitDirectionType.Horizontal
    o.PixelSize = 2560
    o.HLRandWFViewsFileType = ImageFileType.PNG
    o.ShadowViewsFileType = ImageFileType.PNG
    o.ImageResolution = ImageResolution.DPI_150
    doc.ExportImage(o)
    for n in os.listdir(OUT):
        if n.startswith('tmp') and n.lower().endswith('.png'):
            dst = os.path.join(OUT, fname + '.png')
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(os.path.join(OUT, n), dst)
print('exported', [f for (_, f) in made])
