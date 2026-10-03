import chromadb
import anthropic
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode("test")
print(f"Embedding shape: {embedding.shape}")
