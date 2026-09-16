from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


SOURCE = Path(r"C:\Users\user\Desktop\New folder (11)\tmp\student_practice_no_answers_pages")
OUT = Path(r"C:\Users\user\Desktop\New folder (11)\tmp\workbook_whitespace_audit")
OUT.mkdir(parents=True, exist_ok=True)


def ink_bbox_and_ratio(image: Image.Image):
    gray = image.convert("L")
    # Treat near-white pixels as page background while retaining light rules/fills.
    mask = gray.point(lambda p: 255 if p < 245 else 0)
    bbox = mask.getbbox()
    ratio = sum(1 for p in mask.getdata() if p) / (mask.width * mask.height)
    return bbox, ratio


pages = sorted(SOURCE.glob("page-*.png"))
font = ImageFont.load_default()
report = []

for start in range(0, len(pages), 20):
    batch = pages[start : start + 20]
    thumb_w, thumb_h = 248, 350
    label_h, gap = 34, 12
    sheet = Image.new("RGB", (5 * (thumb_w + gap) + gap, 4 * (thumb_h + label_h + gap) + gap), "#d9dee4")
    draw = ImageDraw.Draw(sheet)

    for idx, path in enumerate(batch):
        page = Image.open(path).convert("RGB")
        bbox, ink_ratio = ink_bbox_and_ratio(page)
        page_no = start + idx + 1
        if bbox:
            used_bottom = bbox[3] / page.height
            used_top = bbox[1] / page.height
        else:
            used_bottom = used_top = 0
        report.append((page_no, ink_ratio, used_top, used_bottom))

        page.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gap + (idx % 5) * (thumb_w + gap)
        y = gap + (idx // 5) * (thumb_h + label_h + gap)
        sheet.paste(page, (x + (thumb_w - page.width) // 2, y))
        label = f"Page {page_no:03d} | ink {ink_ratio:.1%} | bottom {used_bottom:.1%}"
        draw.text((x + 5, y + thumb_h + 8), label, fill="#152f45", font=font)

    sheet.save(OUT / f"contact-{start+1:03d}-{start+len(batch):03d}.png")

with (OUT / "page_metrics.tsv").open("w", encoding="utf-8") as f:
    f.write("page\tink_ratio\tused_top\tused_bottom\n")
    for page_no, ink_ratio, used_top, used_bottom in report:
        f.write(f"{page_no}\t{ink_ratio:.6f}\t{used_top:.6f}\t{used_bottom:.6f}\n")

for row in sorted(report, key=lambda x: x[1])[:30]:
    print(f"page={row[0]:03d} ink={row[1]:.2%} top={row[2]:.2%} bottom={row[3]:.2%}")
