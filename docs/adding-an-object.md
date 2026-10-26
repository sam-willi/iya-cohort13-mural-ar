# Adding mural objects and AR targets

Read [how-it-works.md](how-it-works.md) first. In short, two things go into [`data/objects.json`](../data/objects.json):

- **Targets:** parts of the wall the camera recognises, each with a position on the wall
- **Objects:** the things people hunt for, each with a position on the wall, plus the student and pop-out details

All positions are in **inches from the top-left corner of the painted area**.

## 1. Photograph the finished wall

- Photograph the whole painted wall **straight on**, in even light (no glare, no shadows). Stitch several shots if needed.
- Also take close, straight-on photos of each area you'll use as a target.

## 2. Mark positions with the tool

Open [`tools/locate.html`](../tools/locate.html), either on the live site at `/tools/locate.html` or locally:

1. Choose the wall photo and check the wall size (576 × 144 in by default).
2. **Wall edge:** drag a box around just the painted area. The tool's white grid should land on the panel seams in the
   photo. If it doesn't, redraw the edge or retake the photo straighter.
3. **Object:** drag a tight box around each object and type its product name exactly as it appears in the riddle sheet.
4. **AR target:** drag a box around each area the camera should recognise. Panel-sized boxes that overlap by about a
   third work well. They're numbered in the order you draw them.
5. Copy the result and merge its `mural`, `targets` and objects' `location`s into `objects.json`.

## 3. Compile `targets.mind`

1. Crop each target area from your close-up photos, matching the boxes you drew. Save them in `targets/source/` as `00-...`,
   `01-...`, in the **same order** as the targets.
2. Open the MindAR compiler: <https://hiukim.github.io/mind-ar-js-doc/tools/compile>
3. Upload every image from `targets/source/` **in number order**. The upload order sets each target's `index`.
4. Click *Start*, wait, then *Download*, and replace `targets/targets.mind`.

Adding or reordering any target means recompiling the whole file.

What recognises well: busy, high-contrast areas with lots of corners and texture.
What recognises badly: plain areas (sky, white gaps), smooth gradients, repeating shelf boards.

## 4. The object entry

Every product in the riddle sheet already has an entry in `objects.json`, waiting for its `location`, student and pop-out
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
  },
  "popout": {
    "image": "images/popouts/typewriter.png",
    "model": null
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
| `popout.image` | What pops out. A **transparent PNG cut-out** of just the object looks best. It's drawn as wide as the object's box. Until it exists, the lens still marks the spot |
| `popout.model` | Optional `.glb` 3D model, used instead of `image` (3D renderings are on hold for now) |
| `popout.modelScale` | Optional model size; 1 = as wide as the object's box |

An object only appears in the game once it has a riddle (from the sheet) **and** a `location`.

## 5. Test

Run the site locally (see the README), open a target image on a laptop screen, and point your phone at it.
Then test on the real wall, since lighting changes everything.
