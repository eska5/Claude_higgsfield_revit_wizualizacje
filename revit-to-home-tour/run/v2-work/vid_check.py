import sys, cv2, numpy as np
name = sys.argv[1]
cap = cv2.VideoCapture('hf/%s.mp4' % name)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
frames = {}
for i in [0, n // 4, n // 2, 3 * n // 4, n - 1]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read()
    frames[i] = cv2.resize(f, (1920, 1080))
keys = sorted(frames)
a = cv2.cvtColor(frames[keys[0]], cv2.COLOR_BGR2GRAY).astype(np.float32)
for k in keys[1:]:
    b = cv2.cvtColor(frames[k], cv2.COLOR_BGR2GRAY).astype(np.float32)
    # building region only (static)
    r = (slice(250, 800), slice(600, 1400))
    (dx, dy), resp = cv2.phaseCorrelate(a[r], b[r])
    print(name, 'frame', k, 'shift px %.2f %.2f' % (dx, dy), 'resp %.2f' % resp)
hero = cv2.resize(cv2.imread('hf/aerial-dusk.png'), (1920, 1080))
print(name, 'mean abs diff first frame vs hero', float(np.mean(cv2.absdiff(hero, frames[keys[0]]))), 'last vs hero', float(np.mean(cv2.absdiff(hero, frames[keys[-1]]))))
crops = [frames[k][560:1080, 0:960] for k in [keys[0], keys[2], keys[4]]]
cv2.imwrite('hf/_p/%s-street.jpg' % name, np.hstack(crops), [cv2.IMWRITE_JPEG_QUALITY, 85])
