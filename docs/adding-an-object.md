# Adding mural objects and AR targets

Read [how-it-works.md](how-it-works.md) first. Everything about the wall comes from one straight-on image of the painted
wall, made from LiDAR scans, and lives in [`tools/wall/`](../tools/wall/):

- [`wall.json`](../tools/wall/wall.json): the panel-seam calibration, the windows, and a pixel box for every product
- [`wall-scan.webp`](../tools/wall/wall-scan.webp): the wall itself, straight on, 2.5 mm per pixel

[`build.py`](../tools/wall/build.py) turns those into the positions, windows and no-camera picture in
[`data/objects.json`](../data/objects.json), and the AR targets for each object. All positions in `objects.json` are in
**inches from the top-left corner of the painted area**.

## 1. Scan the wall (only when the painting changes)

The wall is in a hallway, so it can't be photographed straight on. Scan it instead:

1. With a LiDAR iPhone and a free scan app (Scaniverse works), walk slowly along the wall about 2 ft away: one pass at
   chest height, one with the phone held overhead and tilted up so the top row is covered. Keep ladders and people out.
2. Export the scan as USDZ (or GLB/OBJ) and flatten it into a straight-on image with Blender 5.x:
   `blender -b -P tools/wall/scan_ortho.py -- scan.usdz wall.png 2.5`
3. If you scanned in parts, merge them (it lines them up automatically; needs `pip install pillow numpy opencv-python-headless`):
   `python3 tools/wall/merge_scans.py wall-1.png wall-2.png wall-merged.png`
4. Save the result as `tools/wall/wall-scan.webp`. If the scan's left edge or the panel seams moved, update
   `calibration` in `wall.json`: the seams repeat every `panel_px` pixels, and `origin_px` is the top-left corner of the
   12 × 3 panel grid.

## 2. Mark the products and windows

In `wall.json`, each product is `"<object id>": [x, y, w, h]`, a tight box in the scan image's pixels; each window is a
named box. Find the pixel boxes by opening the scan in any image editor. A product that isn't in `products` has no
position and stays out of the game.

## 3. Build

```bash
pip install pillow numpy opencv-python-headless   # once
python3 tools/wall/build.py                       # positions, windows, picture and target images
npm install                                       # once
npm run targets                                   # compiles targets/objects/<id>.mind (about 15 min for all of them)
npm run targets -- jukebox toaster                # or just the ones you changed
```

Each object gets its own recognition file with one to three targets: a square of wall around it, plus two pre-tilted
copies if it's high on the wall. The game loads only the current riddle's file.

## 4. Test

Run `node --test`, then follow [testing-without-the-wall.md](testing-without-the-wall.md) at your desk, and finish on the
real wall, since lighting changes everything.

## The object entry

Every product in the riddle sheet already has an entry in `objects.json`, waiting for its `location`, student and 3D
art. When the riddle team adds new products to the sheet, add entries for them with:

```bash
python3 tools/add-sheet-products.py
```

It only adds missing products and never changes existing entries (`--dry-run` shows what it would add). A finished entry
looks like this:

```json
{
  "id": "typewriter",
  "product": "Typewriter",
  "name": "The Typewriter",
  "riddle": "Backup riddle, used only if the riddle sheet can't be reached",
  "hint": "",
  "location": { "x": 530, "y": 70, "w": 14, "h": 10 },
  "student": {
    "name": "Jordan R.",
    "pageUrl": "https://the-other-teams-site.example/students/jordan"
  }
}
```

| Field | Notes |
| --- | --- |
| `id` | Short, lowercase, dashes. Used in QR links: `?object=typewriter` |
| `product` | The exact name in the riddle sheet's **Products** column. The riddle and hint come from that row |
| `riddle`, `hint` | Backup copy used if the sheet can't be reached. `hint` is optional |
| `riddleSource` | Optional: set to `"local"` to use this object's `riddle` and `hint` instead of the live sheet. Omit it to resume sheet updates |
| `location` | The object's box on the wall, in inches, written by `build.py` from `wall.json`. Add `"label": "on the top shelf"` to override the auto-generated "Right side of the mural: 9th panel from the left, top row" |
| `ar` | Written by `build.py`: the object's recognition file and where each of its targets is on the wall. Don't edit by hand |
| `student.pageUrl` | From the website team. Leave it `""` to hide the button |
| 3D rendering | Not a field: save it as **`models/<id>.glb`** and the app finds it. Until it exists, the lens still marks the spot. Optional `popout` settings (`model`, `scale`, `rotation`) are in [3d-models.md](3d-models.md) |

An object only appears in the game once it has a riddle (from the sheet) **and** a `location`.
