import sys, cv2, numpy as np
def first(path):
    cap = cv2.VideoCapture(path); ok, f = cap.read(); return f
def align(ref, img, label):
    h, w = ref.shape[:2]
    img = cv2.resize(img, (w, h))
    orb = cv2.ORB_create(6000)
    k1, d1 = orb.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = orb.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    m = sorted(m, key=lambda x: x.distance)[:1500]
    p1 = np.float32([k1[x.queryIdx].pt for x in m]); p2 = np.float32([k2[x.trainIdx].pt for x in m])
    A, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    sx = (A[0, 0] ** 2 + A[1, 0] ** 2) ** 0.5
    print(label, 'matches', len(m), 'inliers', int(inl.sum()), 'scale %.4f' % sx, 'tx %.1f ty %.1f' % (A[0, 2], A[1, 2]), 'mean BGR ref', ref.mean(axis=(0, 1)).round(1), 'img', img.mean(axis=(0, 1)).round(1))
ref = cv2.resize(cv2.imread(sys.argv[1]), (1920, 1080))
for p in sys.argv[2:]:
    img = first(p) if p.endswith('.mp4') else cv2.imread(p)
    print(p, img.shape)
    align(ref, img, p)
