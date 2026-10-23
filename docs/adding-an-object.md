# Adding a mural object

Every object people can "spy" needs three things:

1. **A source image** of that part of the mural, used for tracking
2. **An entry in `targets/targets.mind`**, the compiled tracking file
3. **An entry in `data/objects.json`**: riddle, student, link, pop-out art

## 1. Photograph and crop

- Photograph the finished mural straight on, in even light (no glare, no shadows).
- Crop a rectangle around each object. Leave a little of the surrounding mural in: more detail means better tracking.
- Save the crops in `targets/source/` with numbered names: `00-...`, `01-...`, `02-...`.
  **The number is the object's `targetIndex`.**

What tracks well: busy, high-contrast areas with lots of corners and texture.
What tracks badly: plain areas, smooth gradients, repeating patterns, very small objects.
If an object is small, crop a bigger area around it.

## 2. Compile `targets.mind`

MindAR needs all target images compiled into **one** `.mind` file.

1. Open the MindAR compiler: <https://hiukim.github.io/mind-ar-js-doc/tools/compile>
2. Upload **every** image from `targets/source/` **in number order** (00, 01, 02, ...). The upload order sets each `targetIndex`.
3. Click *Start*, wait, then *Download*.
4. Replace `targets/targets.mind` with the downloaded file.

Adding or reordering any image means recompiling the whole file.

## 3. Add it to `data/objects.json`

```json
{
  "id": "blue-whale",
  "targetIndex": 3,
  "name": "The Blue Whale",
  "riddle": "I spy something big and blue that sings below the waves...",
  "hint": "Look near the bottom left corner.",
  "student": {
    "name": "Jordan R.",
    "pageUrl": "https://the-other-teams-site.example/students/jordan"
  },
  "popout": {
    "image": "targets/source/03-blue-whale.png",
    "model": null
  }
}
```

| Field | Notes |
| --- | --- |
| `id` | Short, lowercase, dashes. Used in QR links: `?object=blue-whale` |
| `targetIndex` | Must match the image's position in `targets.mind` |
| `riddle`, `hint` | From the riddle team. `hint` is optional |
| `student.pageUrl` | From the website team. Leave it `""` to hide the button |
| `popout.image` | Image that pops out. A **transparent PNG cut-out** of just the object looks best. Same aspect ratio as the source crop so it lines up |
| `popout.model` | Optional path to a `.glb` in `models/`. If set, it's used instead of `image` |
| `popout.modelScale` | Optional size for the model (default `0.2`). 1 = the width of the target image |

## 4. Test

Run the site locally (see the README), open your crop on a laptop screen, and point your phone or webcam at it.
Then test at the real mural, since lighting changes everything.
