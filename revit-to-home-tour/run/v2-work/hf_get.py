"""Download Higgsfield results by name and write small previews.

Usage: python hf_get.py name=url [name=url ...]

Files land in v2-work/hf/. Images also get a 1280px JPEG preview in
v2-work/hf/_p/. Videos get a contact sheet of evenly spaced frames.
"""
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'hf')
PREV = os.path.join(OUT, '_p')


def fetch(url, path):
    cmd = ['curl.exe', '-s', '-L', '-o', path, '-w', '%{http_code}', url]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    return res.stdout.strip()


def preview_image(path, name):
    im = cv2.imread(path)
    if im is None:
        return 'unreadable'
    h, w = im.shape[:2]
    small = cv2.resize(im, (1280, int(1280 * h / w)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(PREV, name + '.jpg'), small, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return '%dx%d' % (w, h)


def preview_video(path, name, count=8):
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if n <= 0:
        return 'unreadable'
    picks = [int(round(i * (n - 1) / (count - 1))) for i in range(count)]
    frames = []
    for idx in picks:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        small = cv2.resize(frame, (640, int(640 * h / w)), interpolation=cv2.INTER_AREA)
        cv2.putText(small, '%.2fs' % (idx / fps if fps else 0), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        frames.append(small)
    cap.release()
    while len(frames) % 4:
        frames.append(np.zeros_like(frames[0]))
    rows = [np.hstack(frames[i:i + 4]) for i in range(0, len(frames), 4)]
    cv2.imwrite(os.path.join(PREV, name + '.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return '%dx%d %.1ffps %d frames %.2fs' % (w, h, fps, n, n / fps if fps else 0)


def main():
    os.makedirs(PREV, exist_ok=True)
    for pair in sys.argv[1:]:
        name, url = pair.split('=', 1)
        ext = os.path.splitext(url.split('?')[0])[1].lower() or '.bin'
        path = os.path.join(OUT, name + ext)
        code = fetch(url, path)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        info = preview_video(path, name) if ext in ('.mp4', '.mov', '.webm') else preview_image(path, name)
        print(name, code, '%.2f MB' % (size / 1e6), info)


if __name__ == '__main__':
    main()
