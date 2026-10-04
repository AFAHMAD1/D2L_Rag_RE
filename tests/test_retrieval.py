import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retriever import retrieve

QUESTIONS = [
    "What is broadcasting in tensors?",
    "What is the ReLU activation function?",
    "Why does dropout help prevent overfitting?",
    "What does a pooling layer do in a CNN?",
    "What is the difference between SGD and minibatch SGD?",
    "How does momentum improve gradient descent?",
    "What is the capital of France?",
    "How do I bake a chocolate cake?",
]

for question in QUESTIONS:
    print("=" * 20, question, "=" * 20)
    for result in retrieve(question, k=3):
        preview = result["text"][:150].replace("\n", " ")
        print(
            f"  [{result['chapter']} p.{result['page']}] "
            f"distance={result['distance']:.4f}"
        )
        print(f"    {preview}")
    print()
