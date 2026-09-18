# RAG corpus

Only `documents/*.md` or `sections.jsonl` should enter retrieval. There are 20 original fictional policy documents and 60 section records. `sections.jsonl` is a convenience export, not a final tokenizer-bounded chunk index. Split and count tokens with the selected encoder before embedding; all-MiniLM-L6-v2 has a default 256-word-piece limit. Include title tokens in that limit. No embeddings or vector dimensions are baked into these records.

Use the manifest for source versions, effective dates and hashes. Never ingest operational records, config, expected answers, injected test documents, or evaluation histories. Customer-specific facts belong in backend/MCP tools. Do not use the FAQ as your only task-boundary enforcement.
