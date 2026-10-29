# 3D renderings

When a player finds an object, a **3D rendering of it rises out of the wall and spins**, like a turntable, inside the
magnifying-glass lens. This page is for whoever makes those renderings.

## What happens in the game

1. The lens lands on the object's spot on the wall.
2. The model grows out of the wall and floats in front of it.
3. It spins slowly around its vertical axis, one full turn every 6 seconds, until the player moves on.

The app sizes and centres every model automatically, so **you don't need to match the mural's scale**. The model's longest
side is fitted to about 1.3× the object's box on the wall.

## Style

Follow the artist's notes on the concept ([reference/README.md](../reference/README.md)):

- **Semi-realistic,** matching how the objects are painted on the wall.
- **The mural's palette:** warm wood browns, lamp amber, cream, sky blue, red and orange.
- It should read as **the same object** people just found on the wall, seen from all sides.

## File requirements

| | Requirement | Why |
| --- | --- | --- |
| Format | **`.glb`** (binary glTF) | One file, loads in every phone browser |
| File name | **`models/<id>.glb`**, using the object's `id` from `data/objects.json` (e.g. `models/typewriter.glb`) | The app finds it automatically |
| Orientation | **Y up, front facing +Z** (Blender's glTF export does this by default) | Upright, facing the player before it spins |
| Size on disk | **Under 1.5 MB after compression**, ideally under 1 MB (raw exports can be bigger; see below) | Players download it on phone data at the wall |
| Triangles | **Under 50,000** | Smooth spinning on older phones |
| Textures | **1024 px or smaller**; 2048 px max | Memory and download size |
| Materials | Standard PBR (base colour, roughness, metalness, normal) | Lit by the scene's warm lamp light |
| Compression | Draco mesh compression is supported; WebP textures are supported | Smaller files |
| Animation | Not needed (the app spins it) | |

Scale and position inside the file don't matter, because the app fits and centres each model.

## Checking a model before adding it

Open **[tools/preview-model.html](../tools/preview-model.html)** (also on the live site at `/tools/preview-model.html`):

- **Try a `.glb` from your computer** to see it with the game's lighting, sizing and spin, before it's even in the repo.
- Or pick an object to see the model that's already in `models/`.
- It shows **file size, triangle count and largest texture**, and flags anything over budget.

## Fixing a model that looks wrong

These optional settings go in the object's entry in `data/objects.json`:

```json
"popout": {
  "model": "models/some-other-name.glb",
  "scale": 1.6,
  "rotation": "0 90 0"
}
```

| Field | Default | Use it when |
| --- | --- | --- |
| `model` | `models/<id>.glb` | The file has a different name |
| `scale` | `1.3` | The model looks too small or big next to the painted object |
| `rotation` | `"0 0 0"` | It was exported facing the wrong way (degrees around x, y, z) |

## Compressing models

Don't worry about compression when exporting: send the full-quality `.glb`. The AR team compresses every model with
one command (`npm run models`), which often makes it several times smaller. See [compression.md](compression.md).
If a model is still over budget after that, it needs fewer triangles: use the Decimate modifier in Blender.

## The generated set

Every object on the Cohort 13 checklist has a rendering in `models/`, modelled in Blender from the students' isometric
drawings (the "Isometric Product Illustrations" Drive folder). Browse them all in
**[tools/model-gallery.html](../tools/model-gallery.html)**.

- Each object is one Python script, [`tools/models/blender/<id>.py`](../tools/models/blender/), built from shared helpers
  in [`kit.py`](../tools/models/blender/kit.py). Most open with a note on what they follow from the drawing and what was guessed.
- To change one, install [Blender](https://www.blender.org/) 5.x, edit its script, then from the repo folder run
  `blender -b -P tools/models/blender/<id>.py -- --check` and `npm run models`. `--check` also renders four views into
  `tools/models/blender/check/<id>.png` (not committed) so you can see the result without opening Blender.
- Some scripts use macOS fonts for lettering and fall back to Blender's built-in font elsewhere.
- Objects with no drawing in the folder (violin, basketball + baseball, motorcycle, bowler hat, toilet paper,
  electric fan, ice chest, treadmill, snow shovel, skateboard, exercise weights, toolbox) got a classic version until
  their drawings turn up. [`catalog.json`](../tools/models/catalog.json) flags these and the drawings that don't match
  their checklist name.
- A hand-made model from Blender or Fusion can replace any of them: just export it to `models/incoming/<id>.glb`
  and run `npm run models` as usual.

## Until a model exists

An object without a model still works. The lens lands on its spot and the "You spied it!" card appears, but nothing pops out.
