# I Spy AR · IYA Cohort 13 Mural

The augmented reality part of the IYA Cohort 13 "I Spy" mural.

## How the experience works

1. A visitor scans the QR code next to the mural, which opens this site in their phone's browser. Nothing to install.
2. They get an "I spy…" riddle.
3. They find the object on the mural and point their camera at it.
4. A **3D rendering of the object rises out of the wall and spins** in AR, and a button links to the page of the student who made it.
5. On to the next riddle.

**What this repo owns:** the AR web app (steps 1–4).
**What it doesn't:** the riddle text (riddle team) and the student pages (the other website team). Riddles are read live from the riddle team's Google Sheet, and student links live in [`data/objects.json`](data/objects.json). See [docs/team-handoff.md](docs/team-handoff.md).

## Tech

| Piece | What it does |
| --- | --- |
| [MindAR](https://hiukim.github.io/mind-ar-js-doc/) 1.2.5 | Image tracking: recognises parts of the mural through the camera |
| [A-Frame](https://aframe.io/) 1.5.0 | Draws the spinning 3D renderings on top of the camera feed |
| Plain HTML/CSS/JS | No build step, no npm. Edit a file, refresh the page |
| GitHub Pages | Free HTTPS hosting (phones only allow camera access over HTTPS) |

## Project layout

```
index.html               page structure: start screen, riddle card, found card, AR scene
js/app.js                game logic
css/style.css            styles
data/objects.json        ⭐ one entry per mural object: position, student, link (riddles come from the sheet)
targets/targets.mind     compiled image targets MindAR looks for (one file for all objects)
targets/source/          the source photo of each AR target, in target order (00-, 01-, ...)
models/                  ⭐ the 3D renderings, one per object: models/<id>.glb (see docs/3d-models.md)
images/workshop.svg      the illustrated workshop behind the start/end screens, in the concept's style, objects fully rendered
tools/make-workshop-svg.py  draws images/workshop.svg (edit this, then run it)
reference/               ⭐ the mural concept art and notes, the design reference for everything
tools/locate.html        mark where each object and AR target is on a photo of the wall
tools/preview-model.html check a 3D rendering: same sizing, lighting and spin as the game, plus size budgets
tools/compress-models.mjs  shrink 3D renderings for phones (npm run models)
tools/check-sizes.py     check everything players download is small enough (runs before every deploy)
package.json             asset tools only (the site itself has no build step)
tools/add-sheet-products.py  add objects.json entries for new products in the riddle sheet
docs/                    how-to guides (start with docs/how-it-works.md)
```

## Design

Everything follows the mural: see [`reference/README.md`](reference/README.md). The concept art is only a reference;
the app has its own artwork drawn in the mural's style. The start screen shows a copy of the mural's I Spy badge in front of
an illustrated workshop (arched sky window, hanging lamps, shelves of objects, the giant magnifying glass), and while you
search, a magnifying glass floats over the camera.

## Run it locally

Any static file server works. From the repo folder:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Laptop webcams work on `localhost`. To test the demo, open
[`targets/source/00-demo-card.png`](targets/source/00-demo-card.png) on one screen and point a camera at it.

## Test on a phone

Phones need HTTPS for the camera, so `http://<your-laptop-ip>:8000` won't work. Either:

- **Push to `main`.** The GitHub Action deploys to GitHub Pages in about a minute. The URL is in the repo's *Settings → Pages*.
- **Or tunnel your local server**, e.g. `npx localtunnel --port 8000` or `ngrok http 8000`.

## Common tasks

- **Understand the whole experience:** [docs/how-it-works.md](docs/how-it-works.md)
- **Test everything before the wall is painted:** [docs/testing-without-the-wall.md](docs/testing-without-the-wall.md)
- **Make or check a 3D rendering:** [docs/3d-models.md](docs/3d-models.md)
- **Compress models and keep downloads small:** [docs/compression.md](docs/compression.md)

### Asset commands

The site needs no build, but preparing assets uses [Node.js](https://nodejs.org/) 20+ (and Python 3 for the size check):

```bash
npm install          # once
npm run models       # compress every .glb in models/incoming/ into models/
npm run sizes        # check everything players download is small enough
```
- **Add or replace a mural object:** [docs/adding-an-object.md](docs/adding-an-object.md)
- **Get riddles and links from the other teams:** [docs/team-handoff.md](docs/team-handoff.md)
- **Make the QR code:** point it at the GitHub Pages URL. Add `?object=<id>` to start on one specific riddle.

## Status / to do

**What's left lives in [GitHub issues](https://github.com/sam-willi/iya-cohort13-mural-ar/issues), starting with the pinned
[Launch checklist](https://github.com/sam-willi/iya-cohort13-mural-ar/issues/15).** Comment on an issue or assign yourself to claim it.

Done so far:

- [x] Game loop: riddle → find → 3D rendering rises and spins → student link → next riddle
- [x] Lens lands on the object's exact spot; mini-map, panel and window directions, "which way" arrow
- [x] Riddles read live from the riddle team's Google Sheet; an `objects.json` entry for every product
- [x] Design matching the mural (badge, palette, workshop art); concept art kept in `reference/`
- [x] Tools: position marking, 3D model preview, model compressor, size check on every deploy
- [x] Playable now on the concept art: object positions, AR targets and backup riddles ([testing without the wall](docs/testing-without-the-wall.md))
- [x] No-camera mode: tap the object on a picture of the mural
- [x] A first 3D rendering for every object on the checklist (built from the isometric drawings; see [tools/model-gallery.html](tools/model-gallery.html))

## Contributing

Make a branch, commit, and open a pull request so someone else can look before it goes to `main`.
Everything on `main` goes live.
