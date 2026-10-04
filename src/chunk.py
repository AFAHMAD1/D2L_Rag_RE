import json
import random
import statistics

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHAPTER_SHORT_NAMES = {
    "Preliminaries": "prelim",
    "Multilayer Perceptrons": "mlp",
    "Convolutional Neural Networks": "cnn",
    "Optimization Algorithms": "optim",
}

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
    keep_separator="end",
)

MIN_MERGE_LENGTH = 100
MIN_KEEP_LENGTH = 30


def merge_short_chunks(texts):
    texts = list(texts)
    merges = 0
    i = 0
    while i < len(texts):
        if len(texts[i]) < MIN_MERGE_LENGTH:
            if i == 0:
                if len(texts) > 1:
                    texts[0] = texts[0] + " " + texts[1]
                    del texts[1]
                    merges += 1
                    continue
                i += 1
            else:
                texts[i - 1] = texts[i - 1] + " " + texts[i]
                del texts[i]
                merges += 1
                continue
        else:
            i += 1
    return texts, merges


with open("data/clean_pages.json", encoding="utf-8") as f:
    pages = json.load(f)

chunks = []
total_merges = 0
total_dropped = 0
for page in pages:
    chapter_short = CHAPTER_SHORT_NAMES[page["chapter"]]
    page_chunks = splitter.split_text(page["text"])
    page_chunks, merges = merge_short_chunks(page_chunks)
    total_merges += merges

    kept = [t for t in page_chunks if len(t) >= MIN_KEEP_LENGTH]
    total_dropped += len(page_chunks) - len(kept)

    for i, chunk_text in enumerate(kept):
        chunks.append(
            {
                "id": f"{chapter_short}_p{page['page']}_c{i}",
                "chapter": page["chapter"],
                "page": page["page"],
                "text": chunk_text,
            }
        )

with open("data/chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Chunks merged: {total_merges}")
print(f"Chunks dropped (<{MIN_KEEP_LENGTH} chars after merging): {total_dropped}")

print(f"Total chunks: {len(chunks)}")
print("\nChunks per chapter:")
for chapter in CHAPTER_SHORT_NAMES:
    count = sum(1 for c in chunks if c["chapter"] == chapter)
    print(f"  {chapter}: {count}")

lengths = [len(c["text"]) for c in chunks]
print(f"\nAverage chunk length: {statistics.mean(lengths):.1f}")
print(f"Min chunk length: {min(lengths)}")
print(f"Max chunk length: {max(lengths)}")

print("\n3 random chunks:")
for c in random.sample(chunks, 3):
    print("=" * 20, c["id"], "=" * 20)
    print(c["text"])
    print()

short_chunks = [c for c in chunks if len(c["text"]) < 100]
print(f"\nChunks shorter than 100 characters: {len(short_chunks)}")
print("3 examples:")
for c in short_chunks[:3]:
    print("=" * 20, c["id"], f"({len(c['text'])} chars)", "=" * 20)
    print(c["text"])
    print()
