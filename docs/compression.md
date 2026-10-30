# Keeping downloads small

Players open the game on their phones, often on mobile data, standing at the wall. Everything they download should be as
small as it can be without looking worse. This page covers what gets downloaded, how each kind of file is compressed, and
the checks that keep it that way.

## What a player downloads

| When | What | Size (compressed, as sent) | How it's kept small |
| --- | --- | --- | --- |
| Opening the page | Page, styles, code, riddle data, workshop art | ~22 KB | GitHub Pages compresses text automatically |
| | Fonts | ~90 KB | Only the weights and widths the CSS uses are requested |
| | A-Frame + MindAR (the AR engine) | ~660 KB | Served compressed by their CDNs; loads **in the background** so the start screen shows straight away |
| | Riddles from the Google Sheet | a few KB | |
| Each riddle | That object's recognition file `targets/objects/<id>.mind` | 0.2 to 1 MB | Only the current riddle's is loaded; [see below](#recognition-files-targetsobjects) |
| | That object's 3D rendering | aim for under 1 MB each | `npm run models` ([see below](#3d-renderings)) |

Only the current riddle's model and recognition file are downloaded, while the player reads the riddle, so nobody downloads all of them.

## 3D renderings

These are the biggest files by far: a raw export can easily be 5 to 20 MB. One command shrinks them all.

### One-time setup

Install [Node.js](https://nodejs.org/) 20 or newer, then in the repo folder:

```bash
npm install
```

This installs [glTF Transform](https://gltf-transform.dev/) for this project only. It isn't part of the website.

### Every time you get new renderings

1. Put the original exports in **`models/incoming/`**, named by object id from `data/objects.json`
   (e.g. `models/incoming/typewriter.glb`). This folder is never committed, so big originals stay out of git.
2. Run:

   ```bash
   npm run models
   ```

   Each file is written to `models/<id>.glb` with:
   - **Draco** geometry compression (the app is set up to decode it),
   - **WebP** textures, at most **1024 px**,
   - unused data removed, duplicate vertices merged, and meshes simplified only where it doesn't visibly change the shape.

   It prints the before and after size of each file.
3. Look at each one in **[tools/preview-model.html](../tools/preview-model.html)**. It shows the model with the game's lighting and
   spin, plus its size, triangle count and largest texture.
4. Run the size check (below), then commit the files in `models/`.

### If a model is still too big

- **Too many triangles:** decimate it in Blender (Decimate modifier), especially hidden or tiny details, then run `npm run models` again.
- **Big textures:** use one texture set per model where possible; 512 px is plenty for small objects.
- **To compress harder by hand:**
  `npx gltf-transform optimize in.glb out.glb --compress draco --texture-compress webp --texture-size 512 --simplify-ratio 0.5`

## Recognition files (`targets/objects/`)

Each object has its own file holding what the camera has learned about the wall around it: one target, or three for objects
high on the wall (a straight-on one and two pre-tilted copies). All of them together are about 27 MB, which is why the game
only ever loads the current riddle's.

- **Resolution is what makes close-up recognition work.** Targets are compiled at 600/72 pixels per inch of wall
  (`PPI` in [`tools/wall/build.py`](../tools/wall/build.py)). At half that, most simulated close-up views failed.
- **Big objects make big files.** A target is about 1.6 times the object, capped at 1.1 m, so a file tops out around 1 MB.
- After rebuilding, run the size check.

## Fonts and images

- **Fonts:** the Google Fonts link in `index.html` asks only for what the CSS uses: Libre Baskerville (regular, bold, italic),
  Noto Serif Display (900, condensed) and Oswald (500, 600). If you use a new weight in the CSS, add it to the link too.
- **Images:** the workshop scene is a 23 KB vector drawing (SVG). For any new photo-like image, use **WebP** at the size it's
  shown, with `cwebp -q 80 in.png -o out.webp`.

## The size check

```bash
npm run sizes        # or: python3 tools/check-sizes.py
```

It lists everything players download and flags anything too big. **It also runs before every deploy:** a file over a hard
limit stops the site from updating, so an oversized model can't go live by accident. Over the soft limit only gives a
warning.

| | Soft limit (warning) | Hard limit (stops the deploy) |
| --- | --- | --- |
| Each 3D model | 1.5 MB / 50,000 triangles | 4 MB / 150,000 triangles |
| Each recognition file in `targets/objects/` | 1 MB | 2 MB |
| Page, styles, code, data and art together | 300 KB | 1 MB |
| Each image | 300 KB | 2 MB |

If a deploy is stopped, the Actions tab on GitHub shows which file and why. Shrink it as above and push again.

## Test on a real phone, on mobile data

Before launch, turn off Wi-Fi and open the live site at the wall. The start screen should appear almost at once. Start should
be ready within a few seconds, and each 3D rendering should appear within a second or two of finding its object.
