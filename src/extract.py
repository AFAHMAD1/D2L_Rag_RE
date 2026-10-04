import json

import pymupdf

CHAPTERS = [
    {"chapter": "Preliminaries", "start": 70, "end": 121},
    {"chapter": "Multilayer Perceptrons", "start": 207, "end": 246},
    {"chapter": "Convolutional Neural Networks", "start": 273, "end": 307},
    {"chapter": "Optimization Algorithms", "start": 508, "end": 586},
]

doc = pymupdf.open("data/d2l.pdf")

records = []
for chapter in CHAPTERS:
    for page_number in range(chapter["start"], chapter["end"] + 1):
        page = doc[page_number - 1]
        text = page.get_text()
        records.append(
            {"chapter": chapter["chapter"], "page": page_number, "text": text}
        )

with open("data/raw_pages.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("Pages per chapter:")
for chapter in CHAPTERS:
    count = chapter["end"] - chapter["start"] + 1
    print(f"  {chapter['chapter']}: {count} pages ({chapter['start']}-{chapter['end']})")

total_chars = sum(len(r["text"]) for r in records)
print(f"\nTotal pages extracted: {len(records)}")
print(f"Total characters: {total_chars}")
