# I Spy AR · IYA Cohort 13 Mural

The augmented reality part of the IYA Cohort 13 "I Spy" mural.

## How the experience works

1. A visitor scans the QR code next to the mural, which opens this site in their phone's browser. Nothing to install.
2. They get an "I spy…" riddle.
3. They find the object on the mural and point their camera at it.
4. The object **pops out of the wall in AR**, and a button links to the page of the student who made it.
5. On to the next riddle.

**What this repo owns:** the AR web app (steps 1–4).
**What it doesn't:** the riddle text (riddle team) and the student pages (the other website team). We only store their riddles and links in [`data/objects.json`](data/objects.json).

## Tech

| Piece | What it does |
| --- | --- |
| [MindAR](https://hiukim.github.io/mind-ar-js-doc/) 1.2.5 | Image tracking: recognises parts of the mural through the camera |
| [A-Frame](https://aframe.io/) 1.5.0 | Draws the 3D pop-out on top of the camera feed |
| Plain HTML/CSS/JS | No build step, no npm. Edit a file, refresh the page |
| GitHub Pages | Free HTTPS hosting (phones only allow camera access over HTTPS) |

## Project layout

```
index.html               page structure: start screen, riddle card, found card, AR scene
js/app.js                game logic
css/style.css            styles
data/objects.json        ⭐ one entry per mural object: riddle, student, link, pop-out art
targets/targets.mind     compiled image targets MindAR looks for (one file for all objects)
targets/source/          the source photo of each object, in target order (00-, 01-, ...)
models/                  optional 3D models (.glb) to pop out instead of a flat image
images/workshop.svg      the illustrated workshop behind the start/end screens (drawn in the mural's style)
reference/               ⭐ the mural concept art and notes, the design reference for everything
docs/                    how-to guides
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

- **Add or replace a mural object:** [docs/adding-an-object.md](docs/adding-an-object.md)
- **Get riddles and links from the other teams:** [docs/team-handoff.md](docs/team-handoff.md)
- **Make the QR code:** point it at the GitHub Pages URL. Add `?object=<id>` to start on one specific riddle.

## Status / to do

- [x] Starter game loop: riddle → find → pop out → student link → next riddle
- [x] Demo target so we can test before the mural exists
- [x] Add the mural concept art as the design reference
- [ ] Make 3D renderings of the objects for the AR pop-outs
- [ ] Photograph the finished mural and crop each object
- [ ] Compile the real `targets.mind`
- [ ] Get riddles from the riddle team
- [ ] Get student page URLs from the website team
- [ ] Test at the mural in its real lighting, on iPhone and Android
- [ ] Generate and print the QR code

## Contributing

Make a branch, commit, and open a pull request so someone else can look before it goes to `main`.
Everything on `main` goes live.
