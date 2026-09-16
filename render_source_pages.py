from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


ROOT = Path(r"C:\Users\user\Desktop\New folder (11)")
SOURCE = ROOT / "source_materials"
OUTPUT = ROOT / "tmp" / "source_renders"
OUTPUT.mkdir(parents=True, exist_ok=True)

SELECTIONS = {
    "YCT 1_work_book.pdf": [1, 2, 3, 4, 5, 10, 20, 30, 40, 45],
    "Chinese_Grade_10_Comprehensive_Workbook.pdf": [1, 2, 8, 20, 60, 100, 140, 179],
}

for filename, page_numbers in SELECTIONS.items():
    pdf = pdfium.PdfDocument(str(SOURCE / filename))
    stem = Path(filename).stem.replace(" ", "_")
    for page_number in page_numbers:
        page = pdf[page_number - 1]
        bitmap = page.render(scale=1.6)
        bitmap.to_pil().save(OUTPUT / f"{stem}_page_{page_number:03d}.png")
