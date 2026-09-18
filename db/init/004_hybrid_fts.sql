-- ============================================================
-- TT&T HYBRID FULL-TEXT SEARCH
--
-- Includes:
--   document title
--   document category
--   section title
--   chunk content
--
-- A trigger automatically builds search_vector whenever
-- a RAG chunk is inserted or updated.
-- ============================================================


-- Remove the previous FTS implementation if present.

DROP INDEX IF EXISTS idx_chunks_search_vector;

ALTER TABLE chunks
DROP COLUMN IF EXISTS search_vector;


-- ============================================================
-- SEARCH VECTOR COLUMN
-- ============================================================

ALTER TABLE chunks
ADD COLUMN search_vector tsvector;


-- ============================================================
-- FUNCTION TO GENERATE SEARCH VECTOR
-- ============================================================

CREATE OR REPLACE FUNCTION ttt_set_chunk_search_vector()
RETURNS trigger
AS $$
DECLARE
    doc_title TEXT;
    doc_category TEXT;
BEGIN

    SELECT
        title,
        category

    INTO
        doc_title,
        doc_category

    FROM documents

    WHERE
        document_id = NEW.document_id
        AND version = NEW.document_version;


    NEW.search_vector :=

        setweight(
            to_tsvector(
                'english',
                COALESCE(doc_title, '')
            ),
            'A'
        )

        ||

        setweight(
            to_tsvector(
                'english',
                COALESCE(doc_category, '')
            ),
            'A'
        )

        ||

        setweight(
            to_tsvector(
                'english',
                COALESCE(NEW.section_title, '')
            ),
            'B'
        )

        ||

        setweight(
            to_tsvector(
                'english',
                COALESCE(NEW.content, '')
            ),
            'C'
        );


    RETURN NEW;

END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- CHUNK TRIGGER
-- ============================================================

DROP TRIGGER IF EXISTS trg_chunks_search_vector
ON chunks;


CREATE TRIGGER trg_chunks_search_vector

BEFORE INSERT OR UPDATE OF
    document_id,
    document_version,
    section_title,
    content

ON chunks

FOR EACH ROW

EXECUTE FUNCTION
    ttt_set_chunk_search_vector();


-- ============================================================
-- BACKFILL EXISTING CHUNKS
-- ============================================================

UPDATE chunks c

SET search_vector =

    setweight(
        to_tsvector(
            'english',
            COALESCE(d.title, '')
        ),
        'A'
    )

    ||

    setweight(
        to_tsvector(
            'english',
            COALESCE(d.category, '')
        ),
        'A'
    )

    ||

    setweight(
        to_tsvector(
            'english',
            COALESCE(c.section_title, '')
        ),
        'B'
    )

    ||

    setweight(
        to_tsvector(
            'english',
            COALESCE(c.content, '')
        ),
        'C'
    )

FROM documents d

WHERE
    d.document_id = c.document_id
    AND d.version = c.document_version;


-- ============================================================
-- GIN INDEX
-- ============================================================

CREATE INDEX idx_chunks_search_vector
ON chunks
USING GIN(search_vector);