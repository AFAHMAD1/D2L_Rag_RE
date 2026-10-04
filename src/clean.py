import json
import re
from collections import Counter

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
CODE_START_RE = re.compile(
    r"^\s*(import |from |def |class |for |while |if |elif |else\b|return |print\()"
    r"|\btorch\.|\bnn\.|\bd2l\.|\bnp\.\b"
    r"|^\s*[\w\.]+\s*=\s*\S"
    r"|^\s*tensor\(|^\s*array\("
)
LETTER_RATIO_THRESHOLD = 0.4


def letter_ratio(s):
    chars = [c for c in s if not c.isspace()]
    if not chars:
        return 1.0
    return sum(c.isalpha() for c in chars) / len(chars)


def remove_header(lines):
    if lines and lines[0].strip().isdigit():
        return lines[2:]
    return lines


def fix_hyphenation(lines):
    lines = list(lines)
    i = 0
    while i < len(lines) - 1:
        cur = lines[i].rstrip()
        nxt = lines[i + 1]
        nxt_first = nxt.lstrip()[:1]
        if (
            cur.endswith("-")
            and len(cur) >= 2
            and cur[-2].isalpha()
            and nxt_first.islower()
            and not CODE_START_RE.search(lines[i])
            and not CODE_START_RE.search(nxt)
        ):
            merged = cur[:-1] + nxt.lstrip()
            lines[i : i + 2] = [merged]
            continue
        i += 1
    return lines


def classify_lines(lines):
    """Tag each line as ('blank' | 'code' | 'prose', line)."""
    classified = []
    in_code_block = False
    for line in lines:
        if line.strip() == "":
            classified.append(("blank", line))
            in_code_block = False
            continue
        if CODE_START_RE.search(line):
            classified.append(("code", line))
            in_code_block = True
            continue
        if in_code_block and letter_ratio(line) < LETTER_RATIO_THRESHOLD:
            classified.append(("code", line))
            continue
        in_code_block = False
        classified.append(("prose", line))
    return classified


def clean_page_text(text, dropped_counter, page_number, dropped_examples):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = CONTROL_RE.sub("", text)

    lines = text.split("\n")
    lines = remove_header(lines)
    lines = fix_hyphenation(lines)
    classified = classify_lines(lines)

    segments = []
    para_buffer = []
    code_buffer = []

    def flush_para():
        if para_buffer:
            segments.append(" ".join(para_buffer))
            para_buffer.clear()

    def flush_code():
        if code_buffer:
            segments.append("\n".join(code_buffer))
            code_buffer.clear()

    for kind, line in classified:
        if kind == "blank":
            flush_para()
            flush_code()
        elif kind == "code":
            flush_para()
            code_buffer.append(line.rstrip())
        else:  # prose
            flush_code()
            stripped = line.strip()
            if not stripped:
                continue
            if letter_ratio(stripped) < LETTER_RATIO_THRESHOLD:
                dropped_counter[stripped] += 1
                dropped_examples.setdefault(stripped, page_number)
                continue
            para_buffer.append(stripped)

    flush_para()
    flush_code()

    result = "\n\n".join(segments)
    result = re.sub(r" {2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def main():
    with open("data/raw_pages.json", encoding="utf-8") as f:
        records = json.load(f)

    dropped_counter = Counter()
    dropped_examples = {}

    cleaned_records = []
    for record in records:
        cleaned_text = clean_page_text(
            record["text"], dropped_counter, record["page"], dropped_examples
        )
        cleaned_records.append(
            {
                "chapter": record["chapter"],
                "page": record["page"],
                "text": cleaned_text,
            }
        )

    with open("data/clean_pages.json", "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, ensure_ascii=False, indent=2)

    chars_before = sum(len(r["text"]) for r in records)
    chars_after = sum(len(r["text"]) for r in cleaned_records)
    print(f"Total characters before: {chars_before}")
    print(f"Total characters after:  {chars_after}")

    by_page = {r["page"]: r for r in records}
    cleaned_by_page = {r["page"]: r for r in cleaned_records}

    for page_number in (72, 521):
        print()
        print("=" * 20, f"BEFORE — page {page_number}", "=" * 20)
        print(by_page[page_number]["text"])
        print()
        print("=" * 20, f"AFTER — page {page_number}", "=" * 20)
        print(cleaned_by_page[page_number]["text"])

    print()
    print("=" * 20, "Top 5 most-repeated lines dropped by rule 5", "=" * 20)
    for line, count in dropped_counter.most_common(5):
        example_page = dropped_examples[line]
        print(f"  (x{count}, e.g. page {example_page}): {line!r}")


if __name__ == "__main__":
    main()
