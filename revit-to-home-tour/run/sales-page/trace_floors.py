from PIL import Image
import numpy as np
import json
from pathlib import Path

p = Path(__file__).parent / 'media' / 'color-mask.png'
im = Image.open(p).convert('RGB')
arr = np.array(im)
h, w = arr.shape[:2]


def mask_color(target, tol=45):
  d = np.abs(arr.astype(np.int16) - np.array(target, dtype=np.int16))
  return (d.sum(axis=2) < tol) & (d.max(axis=2) < tol)


def largest_contour_points(mask, max_pts=36):
  ys, xs = np.where(mask)
  if len(xs) < 40:
    return None
  step = max(1, len(xs) // 2500)
  pts = np.column_stack([xs[::step], ys[::step]])
  if len(pts) < 8:
    return None
  cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
  ang = np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)
  pts = pts[np.argsort(ang)]
  idx = np.linspace(0, len(pts) - 1, num=min(max_pts, len(pts)), dtype=int)
  pts = pts[idx]
  return [[round(100.0 * x / w, 2), round(100.0 * y / h, 2)] for x, y in pts]


floors = {
  'L2': (255, 0, 0),
  'L3': (0, 255, 0),
  'L4': (0, 0, 255),
  'L5': (255, 255, 0),
}

out = {}
for name, col in floors.items():
  m = mask_color(col)
  pts = largest_contour_points(m)
  out[name] = {'pixels': int(m.sum()), 'points': pts}
  print(name, out[name]['pixels'], pts is not None)

(Path(__file__).parent / 'floor-outlines.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('wrote floor-outlines.json')
