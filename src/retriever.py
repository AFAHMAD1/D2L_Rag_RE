import os

os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
_client = chromadb.PersistentClient(path="./chroma_db")
_collection = _client.get_collection("d2l_chunks")


def retrieve(query: str, k: int = 3) -> list[dict]:
    query_embedding = _model.encode([query], normalize_embeddings=True)[0].tolist()
    results = _collection.query(query_embeddings=[query_embedding], n_results=k)

    return [
        {
            "id": results["ids"][0][i],
            "chapter": results["metadatas"][0][i]["chapter"],
            "page": results["metadatas"][0][i]["page"],
            "distance": results["distances"][0][i],
            "text": results["documents"][0][i],
        }
        for i in range(len(results["ids"][0]))
    ]
