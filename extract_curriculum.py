from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


ROOT = Path(r"C:\Users\user\Desktop\New folder (11)\source_materials")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


notes = {}
for name in ["term note 1st  G 10.docx", "term note 2nd G 10.docx", "term note 3rd  G 10.docx"]:
    doc = Document(str(ROOT / name))
    rows = []
    for table in doc.tables:
        for row in table.rows:
            rows.append([clean(cell.text) for cell in row.cells])
    notes[name] = rows

reader = PdfReader(str(ROOT / "Chinese_Grade_10_Comprehensive_Workbook.pdf"))
lesson_pages = []
activity_counts: dict[str, int] = {}
for page_number, page in enumerate(reader.pages, start=1):
    text = clean(page.extract_text() or "")
    if "课" in text[:120] or "පාඩම" in text[:180]:
        lesson_pages.append({"page": page_number, "lead": text[:260]})
    for label in [
        "Pinyin", "අක්ෂර", "හිස්තැන්", "වාක්‍ය", "පරිවර්තනය",
        "පිළිතුරු", "රචනා", "Stroke", "Listening", "Dialogue",
    ]:
        activity_counts[label] = activity_counts.get(label, 0) + text.count(label)

print(json.dumps({"term_notes": notes, "lesson_pages": lesson_pages, "activity_counts": activity_counts}, ensure_ascii=False, indent=2))
