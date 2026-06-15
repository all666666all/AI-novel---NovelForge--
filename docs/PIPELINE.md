# Writing pipeline

How NovelForge takes a story from a loose idea to a finished chapter. Every prompt
referenced below lives in [`backend/prompts/`](../backend/prompts) and can be edited at
runtime from the admin **Prompt management** screen.

## Overview

```
Project → Concept chat → Blueprint (outline) → Chapter drafts → Review & select
   ▲                                                                   │
   └──── (iterate) ── manual edit ── vector ingest ── summary ── RAG ──┘
```

| Stage | Endpoint | Prompt | Temp | Purpose |
|-------|----------|--------|:----:|---------|
| Concept chat | `POST /api/novels/{id}/concept/converse` | `concept` | 0.8 | Guide the writer through world & plot elements |
| Blueprint | `POST /api/novels/{id}/blueprint/generate` | `screenwriting` | 0.3 | Turn the concept into a structured outline |
| Chapter draft | `POST /api/writer/novels/{id}/chapters/generate` | `writing` | 0.9 | Draft chapter candidates from blueprint + memory + RAG |
| Review | `POST /api/writer/novels/{id}/chapters/evaluate` | `evaluation` | 0.3 | Critique every candidate version |
| Summary | `LLMService.get_summary` (on select/edit) | `extraction` | 0.15 | Distil the final text into a factual summary |

## Stages

### 1. Concept chat
A structured conversation (`concept` prompt + a JSON-response instruction) that helps the
writer pin down the world, characters, and premise. When the model marks the conversation
complete, the project can advance to the blueprint.

### 2. Blueprint
The parsed concept conversation is compressed into a formal blueprint (world setting,
characters, factions, per-chapter outline). It can be regenerated, patched
(`PATCH /api/novels/{id}/blueprint`), or hand-edited.

### 3. Chapter drafting
For each chapter the writer service assembles context from:

1. **Blueprint** — world frame only (chapter-level spoilers stripped out).
2. **Previous-chapter bridge** — the prior chapter's factual summary plus its last ~500 characters.
3. **RAG retrieval** (`ChapterContextService`) — embeds *title + outline summary + optional
   instructions*, then pulls the top-K chunks and summaries from the vector store
   (defaults: 5 chunks, 3 summaries).
4. **Writing prompt** (`writing`).

It generates several candidate versions (default `WRITER_CHAPTER_VERSION_COUNT = 2`) stored as
`ChapterVersion` rows. If the vector store is unavailable, it degrades gracefully to
"blueprint + summaries" mode.

### 4. Select / edit
Selecting a version (or saving a manual edit) generates a factual summary (`extraction`,
temp 0.15) and triggers `ChapterIngestionService` to chunk the text + summary and upsert them
into the vector store, replacing any stale chunks for that chapter.

### 5. Review
`evaluation` runs over the full set of candidate versions and writes a report to
`ChapterEvaluation`. Additional reviewers (multi-dimension review, self-critique, reader
simulator) provide deeper, structured feedback.

## RAG details

- **Chunking** — LangChain `RecursiveCharacterTextSplitter` (`VECTOR_CHUNK_SIZE` 480,
  `VECTOR_CHUNK_OVERLAP` 120), falling back to a built-in paragraph/punctuation splitter if
  the dependency is missing.
- **Store** — `VectorStoreService` over libsql (`VECTOR_DB_URL`, local `file:` or remote).
  Tables: `rag_chunks` (body) and `rag_summaries` (per-chapter summaries).
- **Retrieval** — prefers libsql `vector_distance_cosine`; otherwise computes cosine distance
  in Python. Query embeddings come from `LLMService.get_embedding` (OpenAI or Ollama via
  `EMBEDDING_PROVIDER`).
- **Lifecycle** — confirming/editing a chapter deletes old vectors then re-inserts; deleting a
  chapter clears its vectors so RAG never serves stale content.

## Key configuration

| Variable | Purpose |
|----------|---------|
| `OPENAI_*` | Default generation model |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | Embedding backend & model |
| `VECTOR_DB_URL` | libsql vector store (enables RAG) |
| `VECTOR_TOP_K_CHUNKS` / `VECTOR_TOP_K_SUMMARIES` | Retrieval breadth |
| `WRITER_CHAPTER_VERSION_COUNT` | Candidate versions per chapter |
