"""Project Revit model points through a perspective View3D into image coordinates.

Revit stores a perspective crop as a rectangle on the plane at distance
-cmax.z in front of the eye, in the view's own right/up axes. A model point
maps to that plane by similar triangles, then to 0..1 across the crop.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return json.load(f)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def project(cam, p):
    """Return (u, v, depth) with u, v in 0..1 from the top-left of the crop."""
    rel = sub(p, cam['origin'])
    x = dot(rel, cam['bx'])
    y = dot(rel, cam['by'])
    z = -dot(rel, cam['bz'])
    if z <= 1e-6:
        return None
    near = -cam['cmax'][2]
    px = x / z * near
    py = y / z * near
    u = (px - cam['cmin'][0]) / (cam['cmax'][0] - cam['cmin'][0])
    v = 1.0 - (py - cam['cmin'][1]) / (cam['cmax'][1] - cam['cmin'][1])
    return u, v, z


def homes(rooms):
    return sorted(
        [r for r in rooms if r['occupancy'].startswith('Residential') and r['number'] != '106'],
        key=lambda r: r['number'],
    )
