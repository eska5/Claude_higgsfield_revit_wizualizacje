"""Downloads the Higgsfield clips listed in hf_video_urls.json and writes the
site's video and image assets: web-sized H.264 clips, a reversed copy of every
transition, an all-keyframe copy of the day-to-dusk clip for scrubbing, stills."""
import json, os, subprocess, sys, urllib.request
import imageio_ffmpeg
import cv2
HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
RAW = os.path.join(HERE, 'klipy')
SITE = os.path.join(HERE, 'strona')
IMG = os.path.join(SITE, 'a', 'assets', 'img')
for d in [RAW] + [os.path.join(SITE, v, 'assets', k) for v in 'ab' for k in ('video', 'img')]:
    os.makedirs(d, exist_ok=True)
UNIT = {'lokal-201': '201', 'lokal-305': '305', 'lokal-412': '412', 'lokal-506': '506'}


def ff(args):
    r = subprocess.run([FF, '-y', '-loglevel', 'error'] + args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)


def enc(src, dst, extra=(), crf='22'):
    ff(['-i', src] + list(extra) + ['-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst])


urls = json.load(open(os.path.join(HERE, 'hf_video_urls.json')))
for key, url in sorted(urls.items()):
    # a key like 'b/aerial-to-p1' belongs to version B of the site, a bare key to version A
    ver, name = key.split('/') if '/' in key else ('a', key)
    VID = os.path.join(SITE, ver, 'assets', 'video')
    raw = os.path.join(RAW, key.replace('/', '-') + '.mp4')
    if not os.path.exists(raw):
        urllib.request.urlretrieve(url, raw)
    if '-to-' in name and name != 'day-to-dusk':
        a, b = name.split('-to-')
        if b in UNIT:
            fwd, back = 'in-%s' % UNIT[b], 'out-%s' % UNIT[b]
        else:
            fwd, back = name, '%s-to-%s' % (b, a)
        if not os.path.exists(os.path.join(VID, fwd + '.mp4')):
            enc(raw, os.path.join(VID, fwd + '.mp4'))
            enc(raw, os.path.join(VID, back + '.mp4'), ['-vf', 'reverse'])
            print('transition', fwd, back)
    elif name == 'day-to-dusk':
        dst = os.path.join(VID, 'day-to-dusk-scrub.mp4')
        if not os.path.exists(dst):
            ff(['-i', raw, '-an', '-vf', 'scale=1600:-2', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-g', '1', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst])
            print('scrub')
    elif name.startswith('x'):
        # a clip made from a start frame only: its tail is cross-faded into its head so it loops
        dst = os.path.join(VID, name[1:] + '.mp4')
        mark = os.path.join(RAW, key.replace('/', '-') + '.done')
        if not os.path.exists(mark):
            cap = cv2.VideoCapture(raw)
            length = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            fade = 1.0
            ff(['-i', raw, '-an', '-filter_complex',
                '[0:v]split[a][b];[a]trim=0:%.3f,setpts=PTS-STARTPTS[head];[b]trim=%.3f:%.3f,setpts=PTS-STARTPTS[body];'
                '[body][head]xfade=transition=fade:duration=%.3f:offset=%.3f[v]' % (fade, fade, length, fade, length - 2 * fade),
                '-map', '[v]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst])
            open(mark, 'w').close()
            print('crossfade loop', name[1:])
    else:
        dst = os.path.join(VID, name + '.mp4')
        if not os.path.exists(dst):
            enc(raw, dst, crf='23')
            print('loop', name)

for name in ('aerial-day', 'aerial-dusk', 'wejscie', 'cut-p1', 'cut-p2', 'cut-p3', 'cut-p4', 'lokal-201', 'lokal-305', 'lokal-412', 'lokal-506'):
    im = cv2.imread(os.path.join(HERE, 'kadry', name + '.png'))
    cv2.imwrite(os.path.join(IMG, name + '.jpg'), cv2.resize(im, (1920, 1080), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if name.startswith('lokal'):
        cv2.imwrite(os.path.join(IMG, name + '-t.jpg'), cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
for src, dst in (('b-aerial-day', 'aerial-day'), ('b-przekroj', 'przekroj'), ('b-garaz', 'garaz'), ('b-wejscie', 'wejscie')):
    im = cv2.imread(os.path.join(HERE, 'kadry', src + '.png'))
    cv2.imwrite(os.path.join(SITE, 'b', 'assets', 'img', dst + '.jpg'), cv2.resize(im, (1920, 1080), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
for src, num in (('lokal-2.01-2.09', '201'), ('lokal-3.05', '305'), ('lokal-4.12', '412'), ('lokal-5.06-5.07', '506')):
    im = cv2.imread(os.path.join(HERE, 'exports', src + '-rzut.png'))
    h, w = im.shape[:2]
    s = min(1.0, 2000.0 / w)
    cv2.imwrite(os.path.join(IMG, 'rzut-%s.png' % num), cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA))
print('media ok')
