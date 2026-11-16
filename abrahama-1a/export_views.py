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
    ('A1A 02 Wjazd do garazu', (30, -30, 30), (41, 4, -1), 0.058, 'ujecie-02-garaz'),
    ('A1A 11 Od ulicy', (4, -98, 62), (0, -14, 4), 0.058, 'ujecie-11-od-ulicy'),
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

# cut-away isometric of one floor (walls, doors and rooms of Pietro 1) and its floor plan
FLOOR_Z = 4.6
if not ONLY or 'ujecie-07-pietro-1' in ONLY:
    name = 'A1A 07 Pietro 1 - przekroj'
    v = old.get(name)
    if v is None:
        v = View3D.CreateIsometric(doc, vft.Id)
        v.Name = name
    bb = BoundingBoxXYZ()
    bb.Min = P(-31, -2, FLOOR_Z - 0.4)
    bb.Max = P(38, 28, FLOOR_Z + 2.6)
    v.SetSectionBox(bb)
    e, g = P(20, -60, 90), P(3, 11, FLOOR_Z)
    fwd = (g - e).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ).Normalize()
    v.SetOrientation(ViewOrientation3D(e, right.CrossProduct(fwd).Normalize(), fwd))
    v.DisplayStyle = DisplayStyle.Shading
    v.DetailLevel = ViewDetailLevel.Fine
    for bic in (BuiltInCategory.OST_Levels, BuiltInCategory.OST_Site, BuiltInCategory.OST_Planting,
                BuiltInCategory.OST_Entourage, BuiltInCategory.OST_SectionBox):
        try:
            v.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    made.append((v, 'ujecie-07-pietro-1'))
if not ONLY or 'rzut-pietro-1' in ONLY:
    name = 'A1A Rzut - Pietro 1'
    lvl = [l for l in FilteredElementCollector(doc).OfClass(Level) if l.Name == 'Pietro 1'][0]
    pv = None
    for x in FilteredElementCollector(doc).OfClass(ViewPlan):
        if x.Name == name:
            pv = x
    if pv is None:
        pft = [x for x in FilteredElementCollector(doc).OfClass(ViewFamilyType) if x.ViewFamily == ViewFamily.FloorPlan][0]
        pv = ViewPlan.Create(doc, pft.Id, lvl.Id)
        pv.Name = name
    pv.Scale = 100
    pv.DetailLevel = ViewDetailLevel.Medium
    for bic in (BuiltInCategory.OST_Site, BuiltInCategory.OST_Planting, BuiltInCategory.OST_Entourage,
                BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Roofs):
        try:
            pv.SetCategoryHidden(ElementId(bic), True)
        except Exception:
            pass
    cb = pv.CropBox
    cb.Min = XYZ(-33 / F, -3 / F, cb.Min.Z)
    cb.Max = XYZ(40 / F, 29 / F, cb.Max.Z)
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
    made.append((pv, 'rzut-pietro-1'))
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
