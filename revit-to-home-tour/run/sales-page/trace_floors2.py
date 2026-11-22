import json
from pathlib import Path

import cv2
import numpy as np

media = Path(__file__).parent / 'media'
mask_path = media / 'color-mask-2.png'
aerial_path = media / 'dusk-aerial.png'

mask_bgr = cv2.imread(str(mask_path))
if mask_bgr is None:
  raise SystemExit('missing color-mask-2.png')

h, w = mask_bgr.shape[:2]
mask_rgb = cv2.cvtColor(mask_bgr, cv2.COLOR_BGR2RGB)

# also load aerial for overlay preview
aerial = cv2.imread(str(aerial_path))
if aerial is not None and aerial.shape[:2] != (h, w):
  aerial = cv2.resize(aerial, (w, h), interpolation=cv2.INTER_AREA)

targets = {
  'L2': np.array([255, 0, 0]),
  'L3': np.array([0, 255, 0]),
  'L4': np.array([0, 0, 255]),
  'L5': np.array([255, 255, 0]),
}

# diagnose nearest pure colors
flat = mask_rgb.reshape(-1, 3)
sample = flat[::20]
print('size', w, h)


def color_mask(rgb, target, tol=55):
  diff = np.abs(rgb.astype(np.int16) - target.astype(np.int16))
  return ((diff[:, :, 0] <= tol) & (diff[:, :, 1] <= tol) & (diff[:, :, 2] <= tol)).astype(np.uint8) * 255


def largest_poly(binary):
  # clean
  kernel = np.ones((5, 5), np.uint8)
  binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
  binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
  contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  if not contours:
    return None, 0
  contour = max(contours, key=cv2.contourArea)
  area = cv2.contourArea(contour)
  if area < 800:
    return None, area
  # approximate to smooth architectural outline
  peri = cv2.arcLength(contour, True)
  approx = cv2.approxPolyDP(contour, 0.0045 * peri, True)
  if len(approx) < 4:
    approx = contour
  # simplify further if too dense
  while len(approx) > 48:
    approx = cv2.approxPolyDP(approx, 0.006 * peri, True)
    peri = cv2.arcLength(approx, True)
  pts = []
  for p in approx.reshape(-1, 2):
    pts.append([round(100.0 * p[0] / w, 2), round(100.0 * p[1] / h, 2)])
  return pts, area


out = {}
preview = aerial.copy() if aerial is not None else mask_bgr.copy()
colors_bgr = {
  'L2': (0, 0, 255),
  'L3': (0, 255, 0),
  'L4': (255, 0, 0),
  'L5': (0, 255, 255),
}

for name, target in targets.items():
  binary = color_mask(mask_rgb, target)
  pix = int((binary > 0).sum())
  pts, area = largest_poly(binary)
  out[name] = {'pixels': pix, 'area': float(area), 'points': pts}
  print(name, 'pix', pix, 'contour_area', area, 'pts', None if pts is None else len(pts))
  if pts:
    poly = np.array([[int(p[0] * w / 100.0), int(p[1] * h / 100.0)] for p in pts], dtype=np.int32)
    overlay = preview.copy()
    cv2.fillPoly(overlay, [poly], colors_bgr[name])
    preview = cv2.addWeighted(overlay, 0.35, preview, 0.65, 0)
    cv2.polylines(preview, [poly], True, (255, 255, 255), 2)

(Path(__file__).parent / 'floor-hulls.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
cv2.imwrite(str(media / 'outline-preview.png'), preview)
print('wrote floor-hulls.json and outline-preview.png')
