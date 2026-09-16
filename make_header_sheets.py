from pathlib import Path

from PIL import Image, ImageDraw


root = Path(r"C:\Users\user\Desktop\New folder (11)\tmp\final_pages")
out = root.parent / "header_sheets"
out.mkdir(parents=True, exist_ok=True)
paths = sorted(root.glob("page-*.png"))

per_sheet = 18
cols = 3
crop_height = 260
label_height = 26
for sheet_no, start in enumerate(range(0, len(paths), per_sheet), 1):
    batch = paths[start:start + per_sheet]
    sample = Image.open(batch[0]).convert("RGB")
    width = sample.width
    rows = (len(batch) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * width, rows * (crop_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(batch):
        image = Image.open(path).convert("RGB")
        crop = image.crop((0, 0, image.width, crop_height))
        x = (idx % cols) * width
        y = (idx // cols) * (crop_height + label_height)
        sheet.paste(crop, (x, y + label_height))
        draw.text((x + 8, y + 5), path.stem, fill="black")
    sheet.save(out / f"headers-{sheet_no}.png", optimize=True)

print(out)
