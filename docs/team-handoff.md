# Working with the other teams

Riddles come **live from the riddle team's Google Sheet**. Everything else the game shows (student names, links,
pop-out art, which spot on the mural is which object) is in [`data/objects.json`](../data/objects.json).

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
- **Blank riddles are fine.** An object only shows up in the game once it has a riddle *and* an AR target.

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

| Column | Example |
| --- | --- |
| Object | Typewriter |
| Student name (as it should appear) | Jordan R. |
| Student page URL | https://.../students/jordan |

Questions to settle with them:
- When will the final URLs be ready? Only the QR code gets printed, not these links, so they can change any time. Just update `objects.json`.
- Do students want their full name shown, first name only, or no name at all?

## From the mural/art team

- A high-res, straight-on photo of the finished mural, plus close-ups of each object.
- Transparent PNG cut-outs of each object for the pop-out, if possible (or the original digital art).
