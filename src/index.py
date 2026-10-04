import json

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

with open("data/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)
with open("data/embedding_ids.json", encoding="utf-8") as f:
    embedding_ids = json.load(f)
embeddings = np.load("data/embeddings.npy")

chunk_ids = [c["id"] for c in chunks]
assert len(chunks) == len(embeddings) == len(embedding_ids), (
    f"Count mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings, "
    f"{len(embedding_ids)} embedding ids"
)
assert chunk_ids == embedding_ids, "Chunk ids and embedding ids are out of order"
print(f"Verified {len(chunks)} chunks line up with their embeddings and ids.")

client = chromadb.PersistentClient(path="./chroma_db")

COLLECTION_NAME = "d2l_chunks"
existing = [c.name for c in client.list_collections()]
if COLLECTION_NAME in existing:
    client.delete_collection(COLLECTION_NAME)

collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)

BATCH_SIZE = 200
for start in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[start : start + BATCH_SIZE]
    batch_embeddings = embeddings[start : start + BATCH_SIZE]
    collection.add(
        ids=[c["id"] for c in batch],
        embeddings=batch_embeddings.tolist(),
        documents=[c["text"] for c in batch],
        metadatas=[{"chapter": c["chapter"], "page": c["page"]} for c in batch],
    )

print(f"Collection count: {collection.count()}")

model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
query = "What is a matrix?"
query_embedding = model.encode([query], normalize_embeddings=True)[0].tolist()

results = collection.query(query_embeddings=[query_embedding], n_results=3)

print(f"\nTop 3 results for: {query!r}\n")
for i in range(len(results["ids"][0])):
    chapter = results["metadatas"][0][i]["chapter"]
    page = results["metadatas"][0][i]["page"]
    distance = results["distances"][0][i]
    text = results["documents"][0][i][:200]
    print(f"[{chapter} p.{page}] distance={distance:.4f}")
    print(text)
    print()
