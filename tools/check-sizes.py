"""Checks that everything players download stays small enough for phones at the wall.

Runs automatically before every deploy (.github/workflows/pages.yml). A file over a hard limit stops the
deploy; one over the soft limit just gets a warning. Run it yourself with:  npm run sizes
(or  python3 tools/check-sizes.py). Budgets and how to fix things: docs/compression.md
"""
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MB = 1024 * 1024

# (soft limit, hard limit)
MODEL_BYTES = (1.5 * MB, 4 * MB)
MODEL_TRIANGLES = (50_000, 150_000)
TARGETS_BYTES = (6 * MB, 15 * MB)
FIRST_LOAD_BYTES = (300 * 1024, 1 * MB)  # our own files loaded before the start button works
IMAGE_BYTES = (300 * 1024, 2 * MB)

FIRST_LOAD = ["index.html", "css/style.css", "js/app.js", "js/lamps.js", "js/mural-zoom.js", "js/popout.js", "data/objects.json", "images/workshop.svg"]

in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
problems = {"warning": 0, "error": 0}


def size(n):
    return f"{n / MB:.1f} MB" if n >= MB else f"{round(n / 1024)} KB"


def check(path, value, limits, label, fmt=size):
    soft, hard = limits
    level = "error" if value > hard else "warning" if value > soft else None
    status = {"error": "TOO BIG", "warning": "large", None: "ok"}[level]
    print(f"  {status:8} {fmt(value):>10}  {label}")
    if level:
        problems[level] += 1
        limit = hard if level == "error" else soft
        message = f"{label} is {fmt(value)}, over the {fmt(limit)} {'limit' if level == 'error' else 'budget'}. See docs/compression.md"
        if in_ci:
            print(f"::{level} file={path}::{message}")


def glb_triangles(path):
    """Counts triangles from a .glb's JSON (works for Draco-compressed files too)."""
    data = path.read_bytes()
    magic, _, _ = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        return 0
    chunk_len, chunk_type = struct.unpack_from("<I4s", data, 12)
    gltf = json.loads(data[20:20 + chunk_len])
    accessors = gltf.get("accessors", [])
    triangles = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            if "indices" in prim:
                triangles += accessors[prim["indices"]]["count"] // 3
            elif "POSITION" in prim.get("attributes", {}):
                triangles += accessors[prim["attributes"]["POSITION"]]["count"] // 3
    return triangles


def main():
    print("First load (our files; A-Frame and MindAR come from their own fast CDNs)")
    first = sum((ROOT / f).stat().st_size for f in FIRST_LOAD if (ROOT / f).exists())
    check("index.html", first, FIRST_LOAD_BYTES, "page, styles, code, data and art together")

    print("\nRecognition file")
    mind = ROOT / "targets" / "targets.mind"
    if mind.exists():
        check("targets/targets.mind", mind.stat().st_size, TARGETS_BYTES, "targets/targets.mind")

    print("\n3D renderings (each downloads only when its riddle comes up)")
    models = sorted((ROOT / "models").glob("*.glb"))
    if not models:
        print("  none yet")
    for m in models:
        rel = m.relative_to(ROOT).as_posix()
        check(rel, m.stat().st_size, MODEL_BYTES, rel)
        check(rel, glb_triangles(m), MODEL_TRIANGLES, f"{rel} triangles", fmt=lambda n: f"{n:,}")

    print("\nImages")
    for img in sorted((ROOT / "images").rglob("*")):
        if img.is_file():
            rel = img.relative_to(ROOT).as_posix()
            check(rel, img.stat().st_size, IMAGE_BYTES, rel)

    print(f"\n{problems['error']} too big, {problems['warning']} large")
    sys.exit(1 if problems["error"] else 0)


if __name__ == "__main__":
    main()
