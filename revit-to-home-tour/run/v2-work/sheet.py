import sys, glob, os, cv2, numpy as np
pat, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
files = sorted(glob.glob(pat))
tw = 640
tiles = []
for f in files:
    im = cv2.imread(f)
    if im is None:
        continue
    h = int(im.shape[0] * tw / im.shape[1])
    im = cv2.resize(im, (tw, h), interpolation=cv2.INTER_AREA)
    cv2.putText(im, os.path.splitext(os.path.basename(f))[0], (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    tiles.append(im)
th = max(t.shape[0] for t in tiles)
rows = []
for i in range(0, len(tiles), cols):
    row = [cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles[i:i + cols]]
    while len(row) < cols:
        row.append(np.full((th, tw, 3), 255, np.uint8))
    rows.append(np.hstack(row))
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(out, len(tiles))
