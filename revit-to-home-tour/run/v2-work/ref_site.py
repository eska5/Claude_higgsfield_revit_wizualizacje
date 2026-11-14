import cv2, os, numpy as np
src = r"C:\Users\USER\Downloads\endresult_example.mp4"
out = r"revit-to-home-tour\run\v2-work\ref"
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
i = 0
while True:
    ok, f = cap.read()
    if not ok or i > fps * 13.2: break
    if i % 10 == 0:
        crop = f[250:1280, :]
        frames.append((i, crop))
    i += 1
print(len(frames), frames[0][1].shape)
per = 8
for s in range(0, len(frames), per):
    chunk = frames[s:s + per]
    ims = []
    for idx, im in chunk:
        im = cv2.resize(im, (460, int(460 * im.shape[0] / im.shape[1])))
        cv2.putText(im, "%.2fs" % (idx / fps), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        ims.append(im)
    while len(ims) < per: ims.append(np.zeros_like(ims[0]))
    sheet = np.vstack([np.hstack(ims[:4]), np.hstack(ims[4:])])
    cv2.imwrite(os.path.join(out, "site-%02d.jpg" % (s // per)), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print("sheets", (len(frames) + per - 1) // per)
