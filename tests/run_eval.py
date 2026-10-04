import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from google.genai import errors

from pipeline import DISTANCE_THRESHOLD, answer_question
from retriever import retrieve

HERE = os.path.dirname(__file__)
QUESTIONS_PATH = os.path.join(HERE, "eval_questions.json")
RESULTS_PATH = os.path.join(HERE, "eval_results.json")
PAUSE_SECONDS = 6
TOP_K = 4
SERVER_ERROR_ATTEMPTS = 3
SERVER_ERROR_WAIT_SECONDS = 20


def ask_with_retries(question):
    for attempt in range(1, SERVER_ERROR_ATTEMPTS + 1):
        try:
            return answer_question(question, TOP_K)["answer"], None
        except errors.APIError as e:
            if e.code < 500 or attempt == SERVER_ERROR_ATTEMPTS:
                return None, f"{e.code} {e.status}"
            print(f"  Server error {e.code}, retrying in {SERVER_ERROR_WAIT_SECONDS}s...")
            time.sleep(SERVER_ERROR_WAIT_SECONDS)


def expected_retrieved(expected, chapters_retrieved):
    if expected is None:
        return "n/a"
    expected_list = expected if isinstance(expected, list) else [expected]
    return "yes" if all(c in chapters_retrieved for c in expected_list) else "no"


with open(QUESTIONS_PATH, encoding="utf-8") as f:
    questions = json.load(f)

results = []
for i, item in enumerate(questions):
    if i > 0:
        time.sleep(PAUSE_SECONDS)

    retrieved = retrieve(item["question"], TOP_K)
    best_distance = min(r["distance"] for r in retrieved)
    chapters_retrieved = list(dict.fromkeys(r["chapter"] for r in retrieved))
    refused = best_distance > DISTANCE_THRESHOLD

    answer, error = ask_with_retries(item["question"])

    if error:
        status = "error"
        answer = f"ERROR: {error}"
    else:
        status = "refused" if refused else "answered"

    results.append(
        {
            "question": item["question"],
            "type": item["type"],
            "expected_chapter": item["expected_chapter"],
            "best_distance": best_distance,
            "chapters_retrieved": chapters_retrieved,
            "retrieved_expected": expected_retrieved(
                item["expected_chapter"], chapters_retrieved
            ),
            "status": status,
            "answer": answer,
        }
    )
    print(f"[{i + 1}/{len(questions)}] {item['type']}: {item['question'][:60]}")

with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print()
header = f"{'type':<11} | {'best dist':>9} | {'expected ch.':<12} | {'status':<9} | question"
print(header)
print("-" * len(header))
for r in results:
    print(
        f"{r['type']:<11} | {r['best_distance']:>9.4f} | "
        f"{r['retrieved_expected']:<12} | {r['status']:<9} | {r['question'][:60]}"
    )

print()
for question_type in ["normal", "paraphrase", "combined", "trap"]:
    subset = [r for r in results if r["type"] == question_type]
    hits = sum(1 for r in subset if r["retrieved_expected"] == "yes")
    answered = sum(1 for r in subset if r["status"] == "answered")
    scored = sum(1 for r in subset if r["retrieved_expected"] != "n/a")
    chapter_hits = f"{hits}/{scored}" if scored else "n/a"
    print(
        f"{question_type:<11}: chapter hit {chapter_hits}, "
        f"answered {answered}/{len(subset)}"
    )
