import cv2, numpy as np, sys, os
sys.path.insert(0, r"revit-to-home-tour\run\v2-work")
from proj import load, project, homes
cams = load("cams_ht.json"); rooms = load("rooms.json")
cam = cams["HT - Cut L4"]
img = cv2.imread(r"revit-to-home-tour\run\sales-page\media\cut-l4.png")
h, w = img.shape[:2]
print("img", w, h)
for r in homes(rooms):
    if r["level"] != "L4": continue
    for loop in r["loops"][:1]:
        pts = []
        for p in loop:
            q = project(cam, [p[0], p[1], r["level_elev"] + 4.0])
            pts.append([q[0] * w, q[1] * h])
        cv2.polylines(img, [np.array(pts, np.int32)], True, (0, 0, 255), 3)
    c = project(cam, [r["loc"][0], r["loc"][1], r["level_elev"] + 4.0])
    cv2.putText(img, r["number"], (int(c[0] * w) - 20, int(c[1] * h)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 3)
cv2.imwrite(r"revit-to-home-tour\run\v2-work\check-proj-l4.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
