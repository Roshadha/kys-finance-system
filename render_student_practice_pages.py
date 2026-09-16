from pathlib import Path

import pypdfium2 as pdfium


root = Path(r"C:\Users\user\Desktop\New folder (11)")
pdf_path = root / "output" / "Grade_10_Chinese_Student_Practice_Workbook_No_Answers.pdf"
out = root / "tmp" / "student_practice_no_answers_pages"
out.mkdir(parents=True, exist_ok=True)

pdf = pdfium.PdfDocument(str(pdf_path))
for index in range(len(pdf)):
    page = pdf[index]
    bitmap = page.render(scale=1.7)
    bitmap.to_pil().save(out / f"page-{index + 1:03d}.png", optimize=True)

print(f"Rendered {len(pdf)} pages to {out}")
