# Testing away from the wall

The game is built from a straight-on image of the **painted wall**, made from LiDAR scans ([adding-an-object.md](adding-an-object.md)),
so most of it can be tested at a desk.

## What's set up

| Piece | Where | What it is now |
| --- | --- | --- |
| Object positions | `location` in [`data/objects.json`](../data/objects.json), from [`tools/wall/wall.json`](../tools/wall/wall.json) | Measured on the painted wall for every product found on it |
| AR targets | `ar` on each object, compiled into [`targets/objects/`](../targets/objects/) | One small recognition file per object: a square of wall around it, plus two pre-tilted copies for objects high on the wall |
| Picture of the wall | [`images/mural-wall.webp`](../images/mural-wall.webp) | The scan, cropped to exactly the painted area (576 × 144 in) |
| Riddles | Riddle team's sheet, then `riddle` in `objects.json` | The sheet's riddles win. Objects the sheet hasn't covered yet use a simple backup riddle from `objects.json` |
| 3D renderings | [`models/`](../models/) | One per object ([3d-models.md](3d-models.md)) |

Products with a student drawing that weren't on the wall when it was scanned have no position, so they're left out of the
game until they're painted and added to `wall.json`.

## Test 1: no camera (any phone, anywhere)

Open the site and tap **No camera? Play on a picture of the mural**. Scroll and zoom the picture, then tap the object the
riddle describes. A wrong tap says which way to look; the right one lands the lens on it, then shows the "You spied it!"
card with the 3D rendering spinning in it.

Over the mural, two-finger pinching zooms just the artwork. Ordinary wheel/trackpad scrolling pans up, down, left,
and right; one-finger dragging pans on phones. The zoom follows the pinch midpoint, and the riddle stays fixed below.
Browser zoom outside the mural keeps its normal behavior; the corner zoom buttons also remain available.

This mode is also there for players who can't or won't use the camera at the wall.

## Test 2: the AR, pointed at a screen

1. Pick an object and open the game with `?object=<id>` so its riddle comes first, e.g. `?object=boombox`. The game only
   looks for the current riddle's object.
2. On a laptop, open [`images/mural-wall.webp`](../images/mural-wall.webp) and zoom in on that object until about 3 ft of
   wall fills the screen. That's roughly what a phone sees from 2 to 3 ft away in the hallway.
3. On your phone, tap **Start**, point it at the laptop, and tap when the magnifier glows.

Tips: turn the laptop brightness up, avoid glare, and hold the phone 30–50 cm away. The demo card works too: open
[`targets/source/00-demo-card.png`](../targets/source/00-demo-card.png) and use `?object=demo-card`.

## How it was checked

- **Simulated phone views:** 154 views rendered from the 3D scan, 0.55 to 1 m from the wall, aimed at products the way a
  player would. With only the riddle's targets loaded, the right product landed under the crosshair in 137. Level and
  downward views worked almost every time; the misses were phones tipped up more than 45° at the top row, worst in the top
  right corner (toaster, tea set, pan, espresso machine, about 3.4 m up).
- **The real game with a fake camera:** headless Chrome fed the game video rendered from the scan. The boombox and the TV
  were recognised within a second and spied; the next riddle's targets then ignored the same view, as they should.
- **Still to do before launch:** iPhone and Android at the wall, in morning, afternoon and evening light (issue #11).

## When the wall changes

Rescan the part that changed, update `wall.json`, and rebuild ([adding-an-object.md](adding-an-object.md)). Objects painted
after the scan need a box in `wall.json` before they join the game.
