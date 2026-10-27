# Testing before the wall is painted

Until the mural is painted, the whole game runs against the **concept art**, so everything can be tested now.
When the wall is finished, the concept-art pieces get swapped for photos of the real wall (see the end of this page).

## What's set up

| Piece | Where | What it is now |
| --- | --- | --- |
| Object positions | `location` in [`data/objects.json`](../data/objects.json) | Measured on the concept art for the 69 objects visible in it |
| AR targets | `targets` in `objects.json`, compiled into [`targets/targets.mind`](../targets/targets.mind) | Target 0 is still the demo card. Targets 1 to 27 are 6 ft × 4 ft pieces of the concept art ([`targets/source/`](../targets/source/)), chosen so every object fits inside at least one |
| Test picture of the wall | [`reference/mural-concept-wall.webp`](../reference/mural-concept-wall.webp) | The concept art cropped to exactly the painted area (576 × 144 in) |
| Riddles | Riddle team's sheet, then `riddle` in `objects.json` | The sheet's riddles win. Objects the sheet hasn't covered yet use a simple backup riddle from `objects.json` |
| 3D renderings | [`models/`](../models/) | One per object ([3d-models.md](3d-models.md)) |

Seven objects aren't drawn in the concept, so they have no position and are left out of the game for now:
air purifier, comb, electric fan, fortune telling machine, smart watch, toothbrush, wireless earbuds.

## Test 1: no camera (any phone, anywhere)

Open the site and tap **No camera? Play on a picture of the mural**. Scroll and zoom the picture, then tap the object the
riddle describes. A wrong tap says which way to look; the right one lands the lens on it, then shows the "You spied it!"
card with the 3D rendering spinning in it.

This mode is also there for players who can't or won't use the camera at the wall.

## Test 2: the AR, pointed at a screen

1. On a laptop, open [`reference/mural-concept-wall.webp`](../reference/mural-concept-wall.webp) and zoom in until about
   a sixth of the mural (two panels across) fills the screen. That's roughly what a phone sees from 5 ft at the real wall.
2. On your phone, open the live site and tap **Start**.
3. Pan around the picture on the laptop while pointing the phone at it. When the answer is in view, the magnifier lands on
   it and the 3D rendering rises out of the screen.

Tips: turn the laptop brightness up, avoid glare, and hold the phone 30–50 cm away. Add `?object=<id>` to the address to
start on a specific riddle, e.g. `?object=boombox`.

This was checked with a simulated camera feed: the boombox was recognised and found within 6 seconds.

## After the wall is painted

1. **Photograph the wall** straight on, in even light, and mark every object and target with the
   [position marking tool](../tools/locate.html) (issue #8).
2. **Replace the targets**: crop the target images from the photo, compile them with the
   [MindAR compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile), and replace `targets/targets.mind`,
   `targets/source/` and `targets` in `objects.json` (issue #10). The concept-art targets won't recognise the painted wall.
3. **Replace the picture**: crop the photo to exactly the painted area, save it as a `.webp`, and point `mural.picture` in
   `objects.json` at it.
4. **Re-check the positions** from the photo (the painters will have moved things a little).
