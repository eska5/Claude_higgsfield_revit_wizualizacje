"""Draw the model-derived overlays on a picture so alignment can be judged.

Usage: python check_overlay.py <image> <out.jpg> floors|L2|L3|L4|L5
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COLORS = {'L2': (80, 200, 255), 'L3': (120, 255, 120), 'L4': (255, 180, 80), 'L5': (255, 100, 255)}


def main():
    src, out, what = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(os.path.join(HERE, 'overlays.json'), encoding='utf-8') as f:
        data = json.load(f)
    im = cv2.imread(src)
    h, w = im.shape[:2]
    scale = 1920.0 / w
    im = cv2.resize(im, (1920, int(h * scale)), interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]

    def px(poly):
        return np.array([[p[0] * w / 100.0, p[1] * h / 100.0] for p in poly], np.int32)

    if what == 'floors':
        for level, polys in data['floors'].items():
            for poly in polys:
                cv2.polylines(im, [px(poly)], True, COLORS[level], 3)
    else:
        for num, home in data['homes'].items():
            if home['level'] != what:
                continue
            cv2.polylines(im, [px(home['poly'])], True, (0, 0, 255), 3)
            cx, cy = int(home['pin'][0] * w / 100.0), int(home['pin'][1] * h / 100.0)
            cv2.circle(im, (cx, cy), 20, (255, 255, 255), -1)
            cv2.putText(im, num, (cx - 17, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(out, w, h)


if __name__ == '__main__':
    main()
