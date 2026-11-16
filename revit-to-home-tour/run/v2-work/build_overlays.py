"""Compute every overlay coordinate on the page from the Revit model.

Floors: each room on a level is extruded from its floor to the next floor
and drawn through the aerial camera with a depth buffer, so a floor only
keeps the pixels where it is the nearest surface. The outline of those
pixels is the hover shape.

Homes: each home's room boundary is projected at the height of the section
cut (4 ft above its floor), which is where the cut view shows the walls.

Output: overlays.json, all coordinates as percentages of the 16:9 frame.
"""
import json
import os

import cv2
import numpy as np

from proj import HERE, homes, load, project

W, H = 1920, 1080
CUT_ABOVE_FLOOR = 4.0
LEVELS = ['L2', 'L3', 'L4', 'L5']
TOPS = {'L2': 18.833, 'L3': 32.167, 'L4': 45.5, 'L5': 59.917}
OUTDOOR = ('Green Roof', 'Patio', 'Bandstand')


def to_px(cam, p):
    q = project(cam, p)
    return [q[0] * W, q[1] * H], q[2]


def faces_of(room, top):
    """Top face and side quads of one room extruded up to `top`."""
    base = room['level_elev']
    out = []
    for loop in room['loops']:
        if len(loop) < 3:
            continue
        out.append([[p[0], p[1], top] for p in loop])
        for i, a in enumerate(loop):
            b = loop[(i + 1) % len(loop)]
            out.append([[a[0], a[1], base], [b[0], b[1], base], [b[0], b[1], top], [a[0], a[1], top]])
    return out


def cam_point(cam, p):
    rel = [p[0] - cam['origin'][0], p[1] - cam['origin'][1], p[2] - cam['origin'][2]]
    bx, by, bz = cam['bx'], cam['by'], cam['bz']
    return np.array([
        rel[0] * bx[0] + rel[1] * bx[1] + rel[2] * bx[2],
        rel[0] * by[0] + rel[1] * by[1] + rel[2] * by[2],
        -(rel[0] * bz[0] + rel[1] * bz[1] + rel[2] * bz[2]),
    ])


def newell_normal(pts):
    n = np.zeros(3)
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


def cap_of(room, z):
    return [[[p[0], p[1], z] for p in loop] for loop in room['loops'] if len(loop) >= 3]


def floor_masks(cam, rooms):
    """Depth-buffered picture of which level is the nearest surface per pixel.

    Indoor rooms on L2-L5 are solid blocks carrying their level number and
    terraces are flat caps of their own level. The roof garden is a flat
    cap with label 9: it hides what is underneath without being a floor.
    """
    faces = []
    for room in rooms:
        outdoor = any(word in room['name'] for word in OUTDOOR)
        if room['level'] in LEVELS and not outdoor:
            value = LEVELS.index(room['level']) + 1
            faces += [(value, face) for face in faces_of(room, TOPS[room['level']])]
        elif room['level'] in LEVELS:
            value = LEVELS.index(room['level']) + 1
            faces += [(value, face) for face in cap_of(room, room['level_elev'] + 0.3)]
        elif room['level'].startswith('Green Roof'):
            faces += [(9, face) for face in cap_of(room, room['level_elev'] + 0.3)]
    near = -cam['cmax'][2]
    us = (np.arange(W) + 0.5) / W
    vs = (np.arange(H) + 0.5) / H
    px = cam['cmin'][0] + us * (cam['cmax'][0] - cam['cmin'][0])
    py = cam['cmin'][1] + (1.0 - vs) * (cam['cmax'][1] - cam['cmin'][1])
    grid_x, grid_y = np.meshgrid(px, py)
    depth = np.full((H, W), np.inf)
    label = np.zeros((H, W), np.uint8)
    for value, face in faces:
        cam_pts = [cam_point(cam, p) for p in face]
        normal = newell_normal(cam_pts)
        if np.linalg.norm(normal) < 1e-9:
            continue
        poly = np.array([to_px(cam, p)[0] for p in face], np.int32)
        x0, y0 = np.maximum(poly.min(axis=0), 0)
        x1, y1 = np.minimum(poly.max(axis=0), [W - 1, H - 1])
        if x1 < x0 or y1 < y0:
            continue
        mask = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.uint8)
        cv2.fillPoly(mask, [poly - [x0, y0]], 1)
        window = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        denom = normal[0] * grid_x[window] + normal[1] * grid_y[window] + normal[2] * near
        with np.errstate(divide='ignore', invalid='ignore'):
            d = float(np.dot(normal, cam_pts[0])) / denom * near
        nearer = (mask == 1) & (d > 0) & (d < depth[window])
        depth[window][nearer] = d[nearer]
        label[window][nearer] = value
    return label


def ellipse(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def floor_regions(label):
    """One clean region per level, upper levels claiming their pixels first.

    Gaps between rooms on a level (walls, planters) are closed, and pixels
    already claimed by the roof garden or a higher level are left out, so
    a lower storey cannot leak up through a gap in the one above it.
    """
    taken = cv2.morphologyEx(((label == 9) * 255).astype(np.uint8), cv2.MORPH_CLOSE, ellipse(15))
    regions = {}
    for index in reversed(range(len(LEVELS))):
        mask = ((label == index + 1) * 255).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ellipse(41))
        mask[taken > 0] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, ellipse(17))
        regions[LEVELS[index]] = mask
        taken = cv2.bitwise_or(taken, mask)
    return regions


def outlines(mask, min_area=6000):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        approx = cv2.approxPolyDP(contour, 3.0, True)
        polys.append([[round(100.0 * p[0][0] / W, 2), round(100.0 * p[0][1] / H, 2)] for p in approx])
    return polys


def centroid(poly):
    pts = np.array(poly, np.float32)
    m = cv2.moments(pts)
    if abs(m['m00']) < 1e-6:
        return [float(pts[:, 0].mean()), float(pts[:, 1].mean())]
    return [m['m10'] / m['m00'], m['m01'] / m['m00']]


def home_shapes(cam, rooms):
    result = {}
    for room in homes(rooms):
        z = room['level_elev'] + CUT_ABOVE_FLOOR
        loop = max(room['loops'], key=len)
        poly = [to_px(cam, [p[0], p[1], z])[0] for p in loop]
        cx, cy = centroid(poly)
        result[room['number']] = {
            'level': room['level'],
            'poly': [[round(100.0 * x / W, 2), round(100.0 * y / H, 2)] for x, y in poly],
            'pin': [round(100.0 * cx / W, 2), round(100.0 * cy / H, 2)],
        }
    return result


def point(cam, xyz):
    q = project(cam, xyz)
    return [round(100.0 * q[0], 2), round(100.0 * q[1], 2)]


def main():
    cams = load('cams_ht2.json')
    rooms = load('rooms.json')
    aerial = cams['HT2 - Aerial']
    label = floor_masks(aerial, rooms)
    regions = floor_regions(label)
    floors = {}
    for level in LEVELS:
        floors[level] = outlines(regions[level])
        print(level, 'pieces', len(floors[level]), 'points', sum(len(p) for p in floors[level]))
    data = {'frame': [W, H], 'floors': floors, 'homes': home_shapes(aerial, rooms)}
    with open(os.path.join(HERE, 'overlays.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f)
    cv2.imwrite(os.path.join(HERE, 'floor-label.png'), np.minimum(label, 5) * 50)
    print('homes', len(data['homes']))


if __name__ == '__main__':
    main()
