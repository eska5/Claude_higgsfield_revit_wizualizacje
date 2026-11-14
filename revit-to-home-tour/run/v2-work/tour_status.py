"""Show what a tour still needs, and rebuild the page when asked.

Usage, from this folder:
    python tour_status.py            list present and missing media
    python tour_status.py --build    rebuild overlays, data.js and web assets

Reads rooms.json for the home list, so a different building needs no edit
here as long as its homes use the same fields. Higgsfield and Revit are
never called.
"""
import os
import subprocess
import sys

from proj import HERE, homes, load

HF = os.path.join(HERE, 'hf')
STILLS = ['aerial-dawn', 'aerial-noon', 'aerial-golden', 'aerial-dusk', 'aerial-night',
          'cut-l5', 'cut-l4', 'cut-l3', 'cut-l2', 'rooftop', 'street']
CLIPS = ['hero-kling', 'loop-dawn', 'loop-noon', 'loop-golden', 'loop-night',
         'loop-cut-l5', 'loop-cut-l4', 'loop-cut-l3', 'loop-cut-l2',
         'loop-rooftop', 'loop-street',
         'to-cut-l5', 'to-cut-l4', 'to-cut-l3', 'to-cut-l2',
         'l5-to-l4', 'l4-to-l3', 'l3-to-l2',
         'fly-rooftop', 'fly-street', 'timelapse']
MODEL = ['rooms.json', 'cams_ht2.json', 'room_cams.json']


def exists(name):
    return os.path.exists(os.path.join(HF, name))


def report(title, names):
    missing = [name for name in names if not exists(name)]
    print('%s: %d/%d' % (title, len(names) - len(missing), len(names)))
    for name in missing:
        print('  missing', name)
    return missing


def expected():
    stills = [name + '.png' for name in STILLS]
    clips = [name + '.mp4' for name in CLIPS]
    rooms = []
    if os.path.exists(os.path.join(HERE, 'rooms.json')):
        for room in homes(load('rooms.json')):
            num = room['number']
            rooms += ['room-%s-a.png' % num, 'room-%s-b.png' % num,
                      'clip-in-%s.mp4' % num, 'clip-amb-%s.mp4' % num, 'clip-ambb-%s.mp4' % num]
    return stills, clips, rooms


def build():
    missing_model = [name for name in MODEL if not os.path.exists(os.path.join(HERE, name))]
    if missing_model:
        print('cannot build, model data missing:', ' '.join(missing_model))
        return 1
    steps = ['build_overlays.py', 'build_site_data.py', 'build_site_assets.py']
    for step in steps:
        print('---', step)
        result = subprocess.call([sys.executable, os.path.join(HERE, step)])
        if result != 0:
            print(step, 'failed with', result)
            return result
    return 0


def main():
    for name in MODEL:
        print('%-16s %s' % (name, 'ok' if os.path.exists(os.path.join(HERE, name)) else 'MISSING'))
    stills, clips, rooms = expected()
    if not rooms:
        print('rooms.json missing, so per-home files are not listed yet')
    missing = report('stills', stills) + report('clips', clips) + report('homes', rooms)
    print('total missing:', len(missing))
    if '--build' in sys.argv:
        return build()
    return 0


if __name__ == '__main__':
    sys.exit(main())
