"""Turn the downloaded Higgsfield results into web-sized files for the v2 page.

Usage: python build_site_assets.py [--force]

Reads v2-work/hf/, writes revit-to-home-tour/run/sales-page-v2/assets/.
Existing outputs are kept unless --force is given, so the script can be
re-run after more results arrive.

What it makes:
  img/<scene>.jpg            1920x1080 stills (also used as video posters)
  img/rooms/<home>-<a|b>.jpg 1920x1080 interiors, plus -t.jpg thumbnails
  video/loop-*.mp4           ambient clips with the tail faded over the head,
                             so plain <video loop> has no visible seam
  video/<a>-to-<b>.mp4       one-shot transitions, plus reversed copies
  video/timelapse.mp4        day to night, dense keyframes for scrubbing
  video/rooms/in-<home>.mp4  dive from the plan into the home (+ out-, reversed)
  video/rooms/amb-<home>-<a|b>.mp4  forward-then-back interior move, loops cleanly
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import cv2
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'hf')
SITE = os.path.normpath(os.path.join(HERE, '..', 'sales-page-v2'))
ASSETS = os.path.join(SITE, 'assets')
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FORCE = '--force' in sys.argv

SCENE_STILLS = ['aerial-dawn', 'aerial-noon', 'aerial-golden', 'aerial-dusk', 'aerial-night',
                'cut-l5', 'cut-l4', 'cut-l3', 'cut-l2', 'rooftop', 'street']
LOOPS = {
    'hero-kling': 'loop-dusk', 'loop-dawn': 'loop-dawn', 'loop-noon': 'loop-noon',
    'loop-golden': 'loop-golden', 'loop-night': 'loop-night',
    'loop-cut-l5': 'loop-cut-l5', 'loop-cut-l4': 'loop-cut-l4',
    'loop-cut-l3': 'loop-cut-l3', 'loop-cut-l2': 'loop-cut-l2',
    'loop-rooftop': 'loop-rooftop', 'loop-street': 'loop-street',
}
TRANSITIONS = {
    'to-cut-l5': ('aerial-to-l5', 'l5-to-aerial'), 'to-cut-l4': ('aerial-to-l4', 'l4-to-aerial'),
    'to-cut-l3': ('aerial-to-l3', 'l3-to-aerial'), 'to-cut-l2': ('aerial-to-l2', 'l2-to-aerial'),
    'l5-to-l4': ('l5-to-l4', 'l4-to-l5'), 'l4-to-l3': ('l4-to-l3', 'l3-to-l4'),
    'l3-to-l2': ('l3-to-l2', 'l2-to-l3'),
    'fly-rooftop': ('aerial-to-rooftop', 'rooftop-to-aerial'),
    'fly-street': ('aerial-to-street', 'street-to-aerial'),
}
LOOP_FADE = 1.0


def stale(out, src):
    return FORCE or not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src)


def save_jpeg(src, out, width, height, quality):
    if not stale(out, src):
        return
    im = cv2.imread(src)
    im = cv2.resize(im, (width, height), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])


def duration_of(path):
    cap = cv2.VideoCapture(path)
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    cap.release()
    return frames / fps


def encode(src, out, graph, crf, gop=48):
    """Run one ffmpeg encode. `graph` is a filter_complex ending in [v]."""
    if not stale(out, src):
        return out, 'kept'
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-i', src, '-filter_complex', graph, '-map', '[v]',
           '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-g', str(gop),
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return out, 'FAILED ' + res.stderr.strip()[-300:]
    return out, '%.1f MB' % (os.path.getsize(out) / 1e6)


def scale(width, height):
    return 'scale=%d:%d:flags=lanczos,setsar=1,fps=24' % (width, height)


def graph_plain(width, height):
    return '[0:v]%s[v]' % scale(width, height)


def graph_reverse(width, height):
    return '[0:v]%s,reverse[v]' % scale(width, height)


def graph_loop(width, height, length):
    """Fade the first second in over the last second, then drop the first second."""
    body = length - LOOP_FADE
    return (
        '[0:v]%s,split[a][b];'
        '[a]trim=start=%.3f,setpts=PTS-STARTPTS[main];'
        '[b]trim=end=%.3f,setpts=PTS-STARTPTS,format=yuva420p,'
        'fade=t=in:st=0:d=%.3f:alpha=1,setpts=PTS+%.3f/TB[head];'
        '[main][head]overlay=eof_action=pass,trim=end=%.3f[v]'
    ) % (scale(width, height), LOOP_FADE, LOOP_FADE, LOOP_FADE, body - LOOP_FADE, body)


def graph_pingpong(width, height):
    return '[0:v]%s,split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0[v]' % scale(width, height)


def video_jobs():
    jobs = []
    vdir = os.path.join(ASSETS, 'video')
    rdir = os.path.join(vdir, 'rooms')

    def add(name, out, graph, crf, gop=48):
        src = os.path.join(SRC, name + '.mp4')
        if os.path.exists(src):
            jobs.append((src, out, graph, crf, gop))
        else:
            print('missing source', name)

    for name, out in LOOPS.items():
        src = os.path.join(SRC, name + '.mp4')
        if os.path.exists(src):
            add(name, os.path.join(vdir, out + '.mp4'), graph_loop(1920, 1080, duration_of(src)), 24)
        else:
            print('missing source', name)
    for name, (fwd, back) in TRANSITIONS.items():
        add(name, os.path.join(vdir, fwd + '.mp4'), graph_plain(1920, 1080), 24)
        add(name, os.path.join(vdir, back + '.mp4'), graph_reverse(1920, 1080), 24)
    add('timelapse', os.path.join(vdir, 'timelapse.mp4'), graph_plain(1600, 900), 24, gop=3)
    for f in sorted(os.listdir(SRC)):
        if not f.startswith('clip-') or not f.endswith('.mp4'):
            continue
        kind, home = f[5:-4].split('-')
        name = f[:-4]
        if kind == 'in':
            add(name, os.path.join(rdir, 'in-%s.mp4' % home), graph_plain(1280, 720), 26)
            add(name, os.path.join(rdir, 'out-%s.mp4' % home), graph_reverse(1280, 720), 26)
        elif kind == 'amb':
            add(name, os.path.join(rdir, 'amb-%s-a.mp4' % home), graph_pingpong(1280, 720), 27)
        elif kind == 'ambb':
            add(name, os.path.join(rdir, 'amb-%s-b.mp4' % home), graph_pingpong(1280, 720), 27)
    return jobs


def main():
    for sub in ('img', os.path.join('img', 'rooms'), 'video', os.path.join('video', 'rooms')):
        os.makedirs(os.path.join(ASSETS, sub), exist_ok=True)
    for name in SCENE_STILLS:
        src = os.path.join(SRC, name + '.png')
        if os.path.exists(src):
            save_jpeg(src, os.path.join(ASSETS, 'img', name + '.jpg'), 1920, 1080, 86)
        else:
            print('missing still', name)
    rooms = sorted(f for f in os.listdir(SRC) if f.startswith('room-') and f.endswith('.png'))
    for f in rooms:
        key = f[5:-4]
        src = os.path.join(SRC, f)
        save_jpeg(src, os.path.join(ASSETS, 'img', 'rooms', key + '.jpg'), 1920, 1080, 82)
        save_jpeg(src, os.path.join(ASSETS, 'img', 'rooms', key + '-t.jpg'), 480, 270, 78)
    print('stills done:', len(rooms), 'room images')
    jobs = video_jobs()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for out, note in pool.map(lambda job: encode(*job), jobs):
            if note != 'kept':
                print(os.path.relpath(out, ASSETS), note)
    total = 0
    for root, _, files in os.walk(ASSETS):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    print('assets total %.0f MB' % (total / 1e6))


if __name__ == '__main__':
    main()
