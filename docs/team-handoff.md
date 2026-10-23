# Working with the other teams

We store everything the game shows in [`data/objects.json`](../data/objects.json).
Here's what we need from each team. A shared spreadsheet with these columns makes copying it over easy.

## From the riddle team

| Column | Example |
| --- | --- |
| Object (what's on the mural) | Blue whale |
| Riddle | I spy something big and blue that sings below the waves... |
| Hint (optional) | Look near the bottom left corner. |

Questions to settle with them:
- Is there a set order, or should the riddles be shuffled? (Right now the app shuffles.)
- Does every object get a riddle, or only some?
- Roughly how long can a riddle be? It has to fit on a phone screen over the camera view.

## From the student website team

| Column | Example |
| --- | --- |
| Object | Blue whale |
| Student name (as it should appear) | Jordan R. |
| Student page URL | https://.../students/jordan |

Questions to settle with them:
- When will the final URLs be ready? Only the QR code gets printed, not these links, so they can change any time. Just update `objects.json`.
- Do students want their full name shown, first name only, or no name at all?

## From the mural/art team

- A high-res, straight-on photo of the finished mural, plus close-ups of each object.
- Transparent PNG cut-outs of each object for the pop-out, if possible (or the original digital art).
