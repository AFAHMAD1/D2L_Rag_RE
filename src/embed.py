import json
import time

import numpy as np
from sentence_transformers import SentenceTransformer

with open("data/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

texts = [c["text"] for c in chunks]
ids = [c["id"] for c in chunks]

model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

sample_texts = texts[:100]

start = time.perf_counter()
model.encode(sample_texts, batch_size=1, show_progress_bar=False)
time_batch1 = time.perf_counter() - start
print(f"100 chunks, batch_size=1:  {time_batch1:.2f}s")

start = time.perf_counter()
model.encode(sample_texts, batch_size=64, show_progress_bar=False)
time_batch64 = time.perf_counter() - start
print(f"100 chunks, batch_size=64: {time_batch64:.2f}s")

start = time.perf_counter()
embeddings = model.encode(
    texts,
    batch_size=64,
    normalize_embeddings=True,
    show_progress_bar=True,
)
total_time = time.perf_counter() - start

print(f"\nTotal chunks embedded: {len(texts)}")
print(f"Total time: {total_time:.2f}s")
print(f"Embeddings shape: {embeddings.shape}")

np.save("data/embeddings.npy", embeddings)
with open("data/embedding_ids.json", "w", encoding="utf-8") as f:
    json.dump(ids, f, ensure_ascii=False, indent=2)
