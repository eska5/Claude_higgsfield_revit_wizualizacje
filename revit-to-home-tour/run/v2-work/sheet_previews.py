import cv2, os, glob, numpy as np
d = r"revit-to-home-tour\run\previews"
files = sorted(glob.glob(os.path.join(d, "*.png")))
ims = []
for f in files:
    im = cv2.imread(f)
    im = cv2.resize(im, (480, 320))
    cv2.putText(im, os.path.basename(f)[:38], (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    ims.append(im)
while len(ims) % 4: ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + 4]) for i in range(0, len(ims), 4)]
cv2.imwrite(r"revit-to-home-tour\run\v2-work\previews-sheet.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(len(files))
