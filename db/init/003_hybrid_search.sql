-- ============================================================
-- TT&T Hybrid Retrieval
-- PostgreSQL full-text search support
-- ============================================================

ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    setweight(
        to_tsvector(
            'english',
            COALESCE(section_title, '')
        ),
        'A'
    )
    ||
    setweight(
        to_tsvector(
            'english',
            COALESCE(content, '')
        ),
        'B'
    )
) STORED;


CREATE INDEX IF NOT EXISTS idx_chunks_search_vector
ON chunks
USING GIN(search_vector);


CREATE INDEX IF NOT EXISTS idx_chunks_document_lookup
ON chunks(document_id, document_version);