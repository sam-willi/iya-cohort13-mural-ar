"""Adds an entry to data/objects.json for every product in the riddle sheet that doesn't have one yet.

Existing entries are never changed, so it's safe to run again whenever the riddle team adds products.
New entries have no position yet (`location` is null), so they stay out of the game until someone
adds their boxes to tools/wall/wall.json. Their 3D rendering goes in models/<id>.glb.

Usage (from the repo folder):
    python3 tools/add-sheet-products.py            # add missing products
    python3 tools/add-sheet-products.py --dry-run  # just list what would be added
"""
import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

OBJECTS = Path(__file__).resolve().parent.parent / "data" / "objects.json"

# Nicer names to show players, where the sheet's product name is a bit rough.
# The product name itself is kept exactly as in the sheet so the riddle still matches.
DISPLAY_NAMES = {
    "Babystroller": "Baby Stroller",
    "Juke Box": "Jukebox",
    "Car (50s)": "1950s Car",
    "Desk Lamp (Art Nouveau)": "Art Nouveau Desk Lamp",
    "Treadmill?": "Treadmill",
}


def normalize(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def display_name(product):
    if product in DISPLAY_NAMES:
        return DISPLAY_NAMES[product]
    return " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in product.split())


def main():
    dry_run = "--dry-run" in sys.argv
    data = json.loads(OBJECTS.read_text())
    sheet = data.get("riddleSheet", {})
    if not sheet.get("csvUrl"):
        sys.exit("riddleSheet.csvUrl is empty in data/objects.json")

    with urllib.request.urlopen(sheet["csvUrl"], timeout=20) as res:
        rows = list(csv.reader(io.StringIO(res.read().decode("utf-8"))))
    header, rows = rows[0], rows[1:]
    product_col = [normalize(h) for h in header].index(normalize(sheet.get("productColumn", "Products")))

    known_products = {normalize(o.get("product") or o.get("name", "")) for o in data["objects"]}
    known_ids = {o["id"] for o in data["objects"]}
    added, skipped = [], []

    for row in rows:
        product = row[product_col].strip() if product_col < len(row) else ""
        if not product or product == "?" or product.lower().startswith("example:"):
            skipped.append(product or "(blank)")
            continue
        if normalize(product) in known_products:
            continue  # already has an entry (or is a duplicate row in the sheet)
        name = display_name(product)
        base = slug(name)
        obj_id, n = base, 2
        while obj_id in known_ids:
            obj_id, n = f"{base}-{n}", n + 1
        data["objects"].append({
            "id": obj_id,
            "product": product,
            "name": name,
            "riddle": "",
            "hint": "",
            "location": None,
            "student": {"name": "", "pageUrl": ""},
        })
        known_products.add(normalize(product))
        known_ids.add(obj_id)
        added.append(f"{obj_id}  ({product})")

    print(f"{len(added)} new entries" + (" (dry run, nothing written)" if dry_run else ""))
    for line in added:
        print("  +", line)
    if skipped:
        print("Skipped sheet rows:", ", ".join(skipped))
    if added and not dry_run:
        OBJECTS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
