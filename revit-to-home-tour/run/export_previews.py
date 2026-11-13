"""Export preview PNGs of named Revit views through the paired local bridge.

Read-only: Revit renders each view to an image. The model is not changed.
Run from the extension folder so the pairing module is importable:

    uv run --frozen --directory <extension> python <this file> <output folder>
"""
import base64
import os
import re
import sys
from urllib.parse import quote

import httpx

from revit_mcp.pairing import authorization_headers

VIEWS = [
    "Camera fr Above (Realistic) wo Point Cloud",
    "Camera - Exterior Street View (Real)",
    "Camera - Exterior River View",
    "At Ramp",
    "Rooftop Seating Looking toward bandstand",
    "Green Roof - By Stair 1",
    "Camera - Fifth Floor Roof Garden",
    "Loft Unit",
    "Spiral Stair Loft",
    "Unit 302 - Toward Windows",
    "Camera - Unit 304 - Toward Core",
    "Residential Lobby",
]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    base = "http://127.0.0.1:48884/revit_mcp/get_view/"
    with httpx.Client(timeout=240.0, trust_env=False, headers=authorization_headers()) as client:
        for name in VIEWS:
            try:
                res = client.get(base + quote(name, safe=""))
                if res.status_code != 200:
                    print("FAIL", name, res.status_code, res.text[:200])
                    continue
                data = base64.b64decode(res.json()["image_data"])
                path = os.path.join(out_dir, slug(name) + ".png")
                with open(path, "wb") as fh:
                    fh.write(data)
                print("OK", name, "->", os.path.basename(path), len(data))
            except Exception as exc:
                print("FAIL", name, type(exc).__name__, exc)


if __name__ == "__main__":
    main()
