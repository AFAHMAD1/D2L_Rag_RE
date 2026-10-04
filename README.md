# Ask D2L — RAG Chat over Dive into Deep Learning

Ask D2L is a retrieval-augmented chat app that answers questions about four chapters of the free textbook [*Dive into Deep Learning*](https://d2l.ai) (Preliminaries, Multilayer Perceptrons, Convolutional Neural Networks, Optimization Algorithms). Questions are embedded and matched against chunks of the book stored in ChromaDB. The best passages go to an LLM, which writes an answer that cites the page numbers it used. Questions the book can't answer are refused instead of guessed.

![Ask D2L screenshot](docs/screenshot.png)

## Features

- **Chat UI**: a lightweight HTML/CSS/JS frontend served by FastAPI.
- **Cited answers with page sources**: each answer references `[Source N]` entries with chapter and page.
- **Math rendering**: LaTeX in answers is rendered with KaTeX, and Markdown with marked.
- **Off-topic guard**: if the closest chunk is farther than a distance threshold (0.6), the app refuses without calling the LLM.
- **Anti-hallucination prompt**: the model must answer using only the retrieved sources and say so when they don't contain the answer.

## How it works

```
PDF -> extract -> clean -> chunk -> embed -> ChromaDB -> retrieve -> LLM -> FastAPI -> frontend
```

| Step | What it does | Tool |
|------|--------------|------|
| Extract | Reads only the selected page ranges (exercise sections excluded) | PyMuPDF |
| Clean | Removes running headers, fixes hyphenation, drops code and control characters | Python (`src/clean.py`) |
| Chunk | Splits text into ~500-character chunks with 50 overlap, merging tiny ones | LangChain `RecursiveCharacterTextSplitter` |
| Embed | Turns each chunk into a vector | `all-MiniLM-L6-v2` (sentence-transformers) |
| Index | Stores vectors with chapter/page metadata | ChromaDB |
| Retrieve | Top-k nearest chunks for the question, plus distance check | ChromaDB + `src/retriever.py` |
| Generate | Answers from the retrieved sources only | Groq `openai/gpt-oss-120b` |
| Serve | `POST /ask`, `GET /health`, static frontend | FastAPI + uvicorn |
| UI | Chat interface | HTML / CSS / JavaScript |

## Tech stack

Python 3.12, PyMuPDF, LangChain text splitters, sentence-transformers (`all-MiniLM-L6-v2`), ChromaDB, Groq (`openai/gpt-oss-120b`, with Gemini as an alternative provider), FastAPI, uvicorn, KaTeX, marked.

## Setup

```bash
# 1. Clone
git clone https://github.com/AFAHMAD1/D2L_Rag_RE.git
cd D2L_Rag_RE

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Dependencies
pip install -r requirements.txt
```

4. Download the D2L PDF from [d2l.ai](https://d2l.ai) and save it as `data/d2l.pdf`.
5. Create your environment file and add your key(s):
   ```bash
   cp .env.example .env        # Windows: copy .env.example .env
   ```
   Set `GROQ_API_KEY` (required) and optionally `GEMINI_API_KEY`.
6. Run the pipeline scripts in order, from the project root:
   ```bash
   python src/extract.py
   python src/clean.py
   python src/chunk.py
   python src/embed.py
   python src/index.py
   ```
7. Start the server:
   ```bash
   uvicorn api:app --port 8000
   ```
8. Open <http://localhost:8000>.

## Evaluation

`tests/run_eval.py` runs 20 questions from `tests/eval_questions.json` (12 normal, 3 paraphrased, 2 combined cross-chapter, 3 off-topic "traps") and writes `tests/eval_results.json`.

| Result | Outcome |
|--------|---------|
| Correct chapter retrieved | **19 / 20** (16 of 17 in-scope questions, plus all 3 trap questions handled correctly) |
| Normal questions | 12 / 12 retrieved the expected chapter |
| Paraphrased questions | 3 / 3 |
| Combined questions | 1 / 2 (the miss: only Optimization was retrieved for a Preliminaries + Optimization question) |
| Trap questions | 3 / 3 not answered from outside knowledge: 1 refused by the distance threshold, 2 declined by the LLM ("sources do not contain...") |
| Hallucinations | 0 |

Results with the Gemini provider are kept in `tests/eval_results_gemini.json`.

## Problems solved during development

- **Words glued together** (`pypdf` output): switched extraction to PyMuPDF.
- **Running headers** polluting chunks: detected and stripped in the cleaning step.
- **Very short chunks** with little meaning: merged into neighbors after splitting.
- **Gemini free-tier rate limit**: moved generation to Groq (`gpt-oss-120b`); Gemini remains selectable.
- **Exercise sections** crowding out real content in retrieval: excluded by choosing page ranges that stop before them in `src/extract.py`.

## Limitations & future work

- **Combined questions**: multi-topic questions can miss a chapter; query decomposition would retrieve for each part.
- **Follow-up questions**: each question is independent; chat history would allow "what about X?" turns.
- **Greetings / small talk**: "hi" is treated as a question and refused; it needs explicit handling.
- **Streaming**: answers arrive all at once; token streaming would feel faster.

## Project structure

```
.
├── api.py                  # FastAPI app (/ask, /health, serves frontend)
├── requirements.txt
├── .env.example
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── src/
│   ├── extract.py          # PDF -> raw_pages.json
│   ├── clean.py            # raw -> clean_pages.json
│   ├── chunk.py            # clean pages -> chunks.json
│   ├── embed.py            # chunks -> embeddings
│   ├── index.py            # embeddings -> ChromaDB
│   ├── retriever.py        # vector search
│   └── pipeline.py         # prompt, LLM call, refusal logic
├── tests/
│   ├── eval_questions.json
│   ├── run_eval.py
│   ├── eval_results.json
│   ├── eval_results_gemini.json
│   └── test_retrieval.py
├── data/                   # d2l.pdf (not committed) and intermediate JSON
└── docs/
    └── screenshot.png
```
