import json
from pathlib import Path

import cv2
import numpy as np

media = Path(__file__).parent / 'media'
dusk = cv2.imread(str(media / 'dusk-aerial.png'))
dh, dw = dusk.shape[:2]

# Fitted to dusk-aerial.png (1344x752). Main Snowdon block only.
out = {
  'L5': [
    [36.5, 27.0], [44.0, 24.8], [54.5, 27.5], [64.0, 31.5], [70.5, 35.5],
    [71.8, 40.5], [68.5, 43.8], [58.5, 40.5], [48.0, 36.8], [39.5, 33.2], [36.8, 30.0]
  ],
  'L4': [
    [35.5, 33.0], [43.0, 30.5], [54.0, 33.2], [64.0, 37.5], [71.0, 42.0],
    [72.5, 47.5], [69.0, 51.5], [58.0, 48.0], [47.0, 43.8], [38.5, 39.5], [35.8, 36.0]
  ],
  'L3': [
    [34.5, 39.5], [42.2, 36.8], [53.5, 39.5], [64.0, 44.5], [71.2, 49.5],
    [72.8, 55.5], [69.0, 60.0], [57.5, 56.0], [46.0, 51.2], [37.5, 46.5], [34.8, 42.5]
  ],
  'L2': [
    [33.8, 46.5], [41.5, 43.5], [53.0, 46.5], [64.0, 52.0], [71.5, 57.5],
    [73.0, 64.0], [69.0, 68.5], [57.0, 64.0], [45.0, 58.8], [36.5, 53.5], [34.0, 49.5]
  ],
}

preview = dusk.copy()
fills = {
  'L2': (255, 170, 40),
  'L3': (60, 220, 140),
  'L4': (60, 190, 255),
  'L5': (190, 120, 255),
}

for lvl in ['L5', 'L4', 'L3', 'L2']:
  pct = out[lvl]
  ip = np.array([[int(p[0] * dw / 100.0), int(p[1] * dh / 100.0)] for p in pct], dtype=np.int32)
  overlay = preview.copy()
  cv2.fillPoly(overlay, [ip], fills[lvl])
  preview = cv2.addWeighted(overlay, 0.25, preview, 0.75, 0)
  cv2.polylines(preview, [ip], True, (255, 255, 255), 2, cv2.LINE_AA)

(Path(__file__).parent / 'floor-hulls.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
cv2.imwrite(str(media / 'outline-preview.png'), preview)
print('ok', dw, dh)
