import cv2, sys, os
src = r"C:\Users\USER\Downloads\endresult_example.mp4"
out = r"revit-to-home-tour\run\v2-work\ref"
cap = cv2.VideoCapture(src)
if not cap.isOpened():
    print("cannot open"); sys.exit(1)
fps = cap.get(cv2.CAP_PROP_FPS); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print("fps", fps, "frames", n, "size", w, h, "duration_s", round(n / fps, 2) if fps else None)
step = max(1, int(fps * 2))
frames = []
i = 0
while True:
    ok, f = cap.read()
    if not ok: break
    if i % step == 0:
        frames.append((i, cv2.resize(f, (480, int(480 * h / w)))))
    i += 1
print("sampled", len(frames))
import numpy as np
per = 12
for s in range(0, len(frames), per):
    chunk = frames[s:s + per]
    rows = []
    for r in range(0, len(chunk), 4):
        row = [c[1].copy() for c in chunk[r:r + 4]]
        for (idx, _), im in zip(chunk[r:r + 4], row):
            cv2.putText(im, "%.1fs" % (idx / fps), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        while len(row) < 4: row.append(np.zeros_like(row[0]))
        rows.append(np.hstack(row))
    sheet = np.vstack(rows)
    p = os.path.join(out, "sheet-%02d.jpg" % (s // per))
    cv2.imwrite(p, sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(p, sheet.shape)
