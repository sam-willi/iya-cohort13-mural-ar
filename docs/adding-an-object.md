# Adding mural objects and AR targets

Read [how-it-works.md](how-it-works.md) first. In short, three things go into [`data/objects.json`](../data/objects.json):

- **Targets:** parts of the wall the camera recognises, each with a position on the wall
- **Landmarks:** the real windows, used to give players directions
- **Objects:** the things people hunt for, each with a position on the wall, the student, and a 3D rendering

All positions are in **inches from the top-left corner of the painted area**.

## 1. Photograph the finished wall

- One photo of the whole painted area, **as straight on as you can**, in even light (no glare, no shadows).
- Stand well back and zoom in (the 2× lens) so the wall's edges stay straight, and use the camera's highest-resolution
  setting: the AR targets are cut from this photo, so their detail is all the camera has to go on.

## 2. Build the targets from the photo

Open [`tools/make-targets.html`](../tools/make-targets.html) in Chrome or Edge, locally (`python3 -m http.server` in the
project folder, then <http://localhost:8000/tools/make-targets.html>):

1. Choose the wall photo.
2. Drag the four blue dots onto the corners of the painted area. Check the straightened wall underneath: its white grid
   should sit exactly on the panel seams. If it doesn't, nudge the corners or retake the photo from further back.
3. Read the checks: objects that aren't inside any target, and targets that are partly window glass.
4. **Build targets** (a few minutes), then **Save into the project folder** and pick the folder with `index.html` in it.

It writes `targets/targets.mind`, one image per target in `targets/source/`, the straightened wall as
`images/mural-wall.webp` (the no-camera picture), and the new `targets` and `mural.picture` in `objects.json`. Target
boxes come from `targets` in `objects.json`, so after moving or adding targets in step 3, build again. Commit everything
it changed together: `targets.mind` and the `targets` list must stay in the same order.

## 3. Mark positions with the tool

Open [`tools/locate.html`](../tools/locate.html), either on the live site at `/tools/locate.html` or locally:

1. Choose `images/mural-wall.webp`, the straightened photo from step 2, and check the wall size (576 × 144 in by default).
2. **Wall edge:** drag a box around the whole picture (it's already cropped to the painted area). The tool's white grid
   should land on the panel seams.
3. **Object:** drag a tight box around each object and type its product name exactly as it appears in the riddle sheet.
4. **Window:** drag a box around each real window and name it the way players would say it, e.g. "the middle window".
5. **AR target:** drag a box around each area the camera should recognise. Panel-sized boxes that overlap by about a
   third work well. They're numbered in the order you draw them. Keep windows out (the tool warns you).
6. Copy the result and merge its `mural`, `targets`, `landmarks` and objects' `location`s into `objects.json`.
   If you changed any target, keep the demo card's entry (`"demo": true`) first if you still want it, then go back to step 2.

Adding, moving or reordering any target means building `targets.mind` again in step 2.

What recognises well: busy, high-contrast areas with lots of corners and texture.
What recognises badly: plain areas (sky, white gaps), smooth gradients, repeating shelf boards.

## 4. The object entry

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
| `location` | The object's box on the wall, in inches (from the marking tool). Add `"label": "on the top shelf"` to override the auto-generated "Right side of the mural: 9th panel from the left, top row" |
| `student.pageUrl` | From the website team. Leave it `""` to hide the button |
| 3D rendering | Not a field: save it as **`models/<id>.glb`** and the app finds it. Until it exists, the lens still marks the spot. Optional `popout` settings (`model`, `scale`, `rotation`) are in [3d-models.md](3d-models.md) |

An object only appears in the game once it has a riddle (from the sheet) **and** a `location`.

## 5. Test

Run the site locally (see the README), open a target image on a laptop screen, and point your phone at it.
Then test on the real wall, since lighting changes everything.
