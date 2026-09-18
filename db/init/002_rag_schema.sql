CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT,
    category TEXT NOT NULL,
    locale TEXT,
    product TEXT,
    effective_from DATE,
    effective_to DATE,
    source_path TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (document_id, version)
);


CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,

    document_id TEXT NOT NULL,
    document_version INTEGER NOT NULL,

    section_title TEXT,
    chunk_index INTEGER NOT NULL,

    content TEXT NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    embedding VECTOR(384) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (document_id, document_version)
        REFERENCES documents(document_id, version)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_chunks_document
ON chunks(document_id, document_version);


CREATE INDEX IF NOT EXISTS idx_documents_category
ON documents(category);