import cv2, sys, os
d = r"revit-to-home-tour\run\v2-work\revit"
for n in sys.argv[1:]:
    im = cv2.imread(os.path.join(d, n + ".png"))
    print(n, im.shape)
    s = cv2.resize(im, (1280, int(1280 * im.shape[0] / im.shape[1])), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(d, "_p_" + n + ".jpg"), s, [cv2.IMWRITE_JPEG_QUALITY, 85])
