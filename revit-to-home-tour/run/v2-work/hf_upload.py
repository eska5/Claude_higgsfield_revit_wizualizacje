"""PUT local files into Higgsfield upload slots.

Usage: python hf_upload.py <slots output file> name=path [name=path ...]

The slots file is the saved text of a media_upload call. Each given file
takes the next unused slot. The mapping name -> media id is kept in
media_ids.json so later steps can refer to uploads by name.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, 'media_ids.json')
USED = os.path.join(HERE, 'slots_used.json')


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)


def parse_slots(path):
    text = open(path, encoding='utf-8').read()
    pattern = re.compile(r"- ([0-9a-f-]{36}): Upload the file using: curl -X PUT -H \"Content-Type: ([^\"]+)\" --data-binary @(\S+) '([^']+)'")
    return [{'id': m.group(1), 'ctype': m.group(2), 'slot': m.group(3), 'url': m.group(4)} for m in pattern.finditer(text)]


def put(url, ctype, path):
    """Upload with curl; the upload host rejects Python's default client."""
    cmd = ['curl.exe', '-s', '-o', 'NUL', '-w', '%{http_code}', '-X', 'PUT',
           '-H', 'Content-Type: ' + ctype, '--data-binary', '@' + path, url]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    code = res.stdout.strip()
    return (int(code) if code.isdigit() else 0), res.stderr.strip()[:300]


def main():
    slots = parse_slots(sys.argv[1])
    used = read_json(USED, [])
    registry = read_json(REGISTRY, {})
    free = [s for s in slots if s['id'] not in used]
    print('slots', len(slots), 'free', len(free))
    done = []
    for pair in sys.argv[2:]:
        name, path = pair.split('=', 1)
        if not free:
            print('NO SLOT LEFT for', name)
            continue
        slot = free[0]
        status, detail = put(slot['url'], slot['ctype'], path)
        print(name, slot['id'], status, detail)
        if status == 200:
            free.pop(0)
            used.append(slot['id'])
            registry[name] = slot['id']
            done.append(slot['id'])
        write_json(USED, used)
        write_json(REGISTRY, registry)
    print('CONFIRM', json.dumps(done))


if __name__ == '__main__':
    main()
