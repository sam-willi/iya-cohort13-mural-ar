# Working with the other teams

Riddles come **live from the riddle team's Google Sheet**. Everything else the game shows (student names, links,
3D renderings, which spot on the mural is which object) is in [`data/objects.json`](../data/objects.json).

## From the riddle team

They write riddles in the **"C13 Mural Riddle List"** Google Sheet. The app reads it every time someone opens the game,
so edits show up within a few minutes with no help from us.

| Column | Example | Notes |
| --- | --- | --- |
| Products | Typewriter | Must match the object's `product` in `objects.json` (capitals and spaces don't matter) |
| Riddle | I spy a machine with a row of round keys, … | Line breaks are kept, so write it as rhyming lines |
| Hint (optional) | Look by the window. | Add this column if you want hints; the app picks it up automatically |

Rules that keep it working:
- **Don't rename or delete the "Products" or "Riddle" headers.** The app finds the columns by name.
- **Keep each product name unique and stable.** Renaming "Juke Box" to "Jukebox" breaks the link until `objects.json` is updated too.
  If a product is listed twice, the first row with a riddle wins.
- **Blank riddles are fine.** An object only shows up in the game once it has a riddle *and* a position on the wall.
- **New products** need an entry in `objects.json` too. Run `python3 tools/add-sheet-products.py` after they're added.

### Connecting the sheet (one-time)

1. Someone with edit access opens the sheet and chooses **File → Share → Publish to web**.
2. Pick **Sheet1** and **Comma-separated values (.csv)**, then **Publish**. This makes a public, read-only copy of that one tab.
3. Paste the link it gives you into `riddleSheet.csvUrl` in [`data/objects.json`](../data/objects.json).

If the sheet can't be reached (not published, Google down, slow connection), the game quietly falls back to the
`riddle` and `hint` written in `objects.json`, so it's worth keeping a copy there for each object before launch.

Questions to settle with them:
- Is there a set order, or should the riddles be shuffled? (Right now the app shuffles.)
- Some rows are duplicates (Drone, Top Hat, Boombox) or unsure ("?", "Treadmill?"). Which ones are final?

## From the student website team

Student names and page links come **live from the profiles website**. When students edit their page there, they pick
the product they drew from a list of this repo's object `id`s. The site publishes the result at `/api/mural-objects`:

```json
{ "objects": [{ "objectId": "typewriter", "studentName": "Jordan Rivera", "pageUrl": "https://.../jordan-rivera" }] }
```

Put that URL in `profiles.url` in [`data/objects.json`](../data/objects.json). The game reads it every time someone opens it,
so a student's link works as soon as they pick their product. If the site can't be reached, the game falls back to each
object's `student` in `objects.json`, so the button is hidden for anyone without one there.

Rules that keep it working:
- **Don't rename an object's `id`.** It's how the website knows which product is whose. Renaming it unlinks that student.
- **New objects** need to be added to the website's list too (`src/lib/mural-objects.json` in that repo).

## From the mural/art team

- A high-res, straight-on photo of the finished mural, plus close-ups of each object.
- A **3D rendering of each object** (`.glb`), semi-realistic and in the mural's palette, to rise out of the wall and spin
  when it's found. Specs and a preview tool: [3d-models.md](3d-models.md).
