import functools
import os
import time

import groq
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from groq import Groq

from retriever import retrieve

load_dotenv()

PROVIDER = "groq"  # "groq" or "gemini"
DISTANCE_THRESHOLD = 0.6
GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.8-flash"
MAX_RETRIES = 3


@functools.lru_cache(maxsize=None)
def _gemini_client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


@functools.lru_cache(maxsize=None)
def _groq_client():
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _call_with_rate_limit_retry(send, is_rate_limit):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return send()
        except Exception as e:
            if is_rate_limit(e) and attempt < MAX_RETRIES:
                wait_seconds = 2**attempt
                print(f"Rate limited, retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            raise


def call_gemini(prompt: str) -> str:
    response = _call_with_rate_limit_retry(
        lambda: _gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        ),
        is_rate_limit=lambda e: isinstance(e, errors.APIError) and e.code == 429,
    )
    return response.text


def call_groq(prompt: str) -> str:
    response = _call_with_rate_limit_retry(
        lambda: _groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        ),
        is_rate_limit=lambda e: isinstance(e, groq.APIStatusError)
        and e.status_code == 429,
    )
    return response.choices[0].message.content


def call_model(prompt: str) -> str:
    if PROVIDER == "groq":
        return call_groq(prompt)
    if PROVIDER == "gemini":
        return call_gemini(prompt)
    raise ValueError(f"Unknown PROVIDER: {PROVIDER!r}")


def build_prompt(question: str, sources: list[dict]) -> str:
    labeled_sources = "\n\n".join(
        f"[Source {i + 1}: {s['chapter']}, p.{s['page']}]\n{s['text']}"
        for i, s in enumerate(sources)
    )
    return f"""Answer the question using ONLY the sources below. \
If the sources don't contain the answer, say so clearly instead of guessing. \
Cite the sources you use in your answer like [Source 1].

{labeled_sources}

Question: {question}

Answer:"""


def answer_question(question: str, k: int = 4) -> dict:
    results = retrieve(question, k)

    best_distance = min(r["distance"] for r in results)
    if best_distance > DISTANCE_THRESHOLD:
        return {
            "answer": "I couldn't find this in the selected D2L chapters.",
            "sources": [],
        }

    prompt = build_prompt(question, results)
    answer = call_model(prompt)

    return {
        "answer": answer,
        "sources": [
            {
                "chapter": r["chapter"],
                "page": r["page"],
                "distance": r["distance"],
                "text": r["text"],
            }
            for r in results
        ],
    }


if __name__ == "__main__":
    questions = [
        "What is broadcasting in tensors?",
        "Why does dropout help prevent overfitting?",
        "What is the capital of France?",
    ]

    for i, question in enumerate(questions):
        if i > 0:
            time.sleep(2)

        result = answer_question(question)
        print("=" * 20, question, "=" * 20)
        print(result["answer"])
        print("\nSources:")
        for s in result["sources"]:
            print(f"  [{s['chapter']} p.{s['page']}] distance={s['distance']:.4f}")
        print()
