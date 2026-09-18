from pathlib import Path
import hashlib
import os

import yaml
import psycopg

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = ROOT / "data" / "knowledge" / "documents"

load_dotenv(ROOT / ".env")


# ============================================================
# DATABASE CONFIG
# ============================================================

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


# ============================================================
# EMBEDDING MODEL
# ============================================================

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5"
)

print(f"Loading embedding model: {MODEL_NAME}")

model = SentenceTransformer(MODEL_NAME)


# ============================================================
# MARKDOWN PARSING
# ============================================================

def parse_markdown(path: Path):
    """
    Parse Markdown files containing YAML frontmatter.

    Example:

    ---
    document_id: BILL-ACT-01
    version: 1
    category: billing
    effective_from: 2026-01-01
    ---

    # Activation Fee Policy

    ...
    """

    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(
            f"{path.name} does not contain YAML frontmatter"
        )

    parts = text.split("---", 2)

    if len(parts) < 3:
        raise ValueError(
            f"{path.name} contains invalid YAML frontmatter"
        )

    metadata = yaml.safe_load(parts[1])

    body = parts[2].strip()

    if not isinstance(metadata, dict):
        raise ValueError(
            f"{path.name} metadata must be a YAML dictionary"
        )

    if not body:
        raise ValueError(
            f"{path.name} has an empty document body"
        )

    return metadata, body


# ============================================================
# SIMPLE SECTION PARSER
# ============================================================

def split_sections(markdown_text: str):
    """
    Keep Markdown heading context.

    Returns:

    [
        ("Activation Fee Policy", "..."),
        ("When the fee applies", "..."),
        ...
    ]
    """

    sections = []

    current_heading = "Document"
    current_lines = []

    for line in markdown_text.splitlines():

        stripped = line.strip()

        if stripped.startswith("#"):

            if current_lines:

                section_text = "\n".join(
                    current_lines
                ).strip()

                if section_text:
                    sections.append(
                        (
                            current_heading,
                            section_text,
                        )
                    )

            current_heading = stripped.lstrip("#").strip()
            current_lines = []

        else:
            current_lines.append(line)

    if current_lines:

        section_text = "\n".join(
            current_lines
        ).strip()

        if section_text:
            sections.append(
                (
                    current_heading,
                    section_text,
                )
            )

    return sections


# ============================================================
# CHUNKING
# ============================================================

def chunk_words(
    text: str,
    chunk_size: int = 180,
    overlap: int = 25,
):
    """
    First RAG baseline.

    ~180 words per chunk
    25-word overlap

    Later we can replace this with tokenizer-aware chunking.
    """

    words = text.split()

    if not words:
        return []

    chunks = []

    start = 0

    while start < len(words):

        end = min(
            start + chunk_size,
            len(words),
        )

        chunk = " ".join(
            words[start:end]
        )

        chunks.append(chunk)

        if end == len(words):
            break

        start = end - overlap

    return chunks


# ============================================================
# CHUNK ID
# ============================================================

def create_chunk_id(
    document_id: str,
    version: int,
    chunk_index: int,
):
    raw = (
        f"{document_id}:"
        f"{version}:"
        f"{chunk_index}"
    )

    short_hash = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:12]

    return (
        f"{document_id}-"
        f"v{version}-"
        f"{short_hash}"
    )


# ============================================================
# DATABASE
# ============================================================

def insert_document(
    conn,
    metadata,
    path,
):

    query = """
        INSERT INTO documents (
            document_id,
            version,
            title,
            category,
            locale,
            product,
            effective_from,
            effective_to,
            source_path,
            metadata
        )
        VALUES (
            %(document_id)s,
            %(version)s,
            %(title)s,
            %(category)s,
            %(locale)s,
            %(product)s,
            %(effective_from)s,
            %(effective_to)s,
            %(source_path)s,
            %(metadata)s
        )

        ON CONFLICT (document_id, version)

        DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            locale = EXCLUDED.locale,
            product = EXCLUDED.product,
            effective_from = EXCLUDED.effective_from,
            effective_to = EXCLUDED.effective_to,
            source_path = EXCLUDED.source_path,
            metadata = EXCLUDED.metadata;
    """

    values = {
        "document_id": metadata["document_id"],
        "version": int(metadata["version"]),

        "title": metadata.get(
            "title",
            metadata["document_id"],
        ),

        "category": metadata["category"],

        "locale": metadata.get("locale"),

        "product": metadata.get("product"),

        "effective_from": metadata.get(
            "effective_from"
        ),

        "effective_to": metadata.get(
            "effective_to"
        ),

        "source_path": str(
            path.relative_to(ROOT)
        ),

        "metadata": psycopg.types.json.Jsonb(
            metadata
        ),
    }

    with conn.cursor() as cur:
        cur.execute(query, values)


def delete_existing_chunks(
    conn,
    document_id,
    version,
):
    """
    Makes ingestion safely repeatable.

    If we re-ingest a document version,
    replace its chunks instead of duplicating them.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            DELETE FROM chunks
            WHERE document_id = %s
              AND document_version = %s;
            """,
            (
                document_id,
                version,
            ),
        )


def insert_chunk(
    conn,
    chunk_id,
    document_id,
    version,
    section_title,
    chunk_index,
    content,
    embedding,
):

    query = """
        INSERT INTO chunks (
            chunk_id,
            document_id,
            document_version,
            section_title,
            chunk_index,
            content,
            embedding
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        );
    """

    with conn.cursor() as cur:

        cur.execute(
            query,
            (
                chunk_id,
                document_id,
                version,
                section_title,
                chunk_index,
                content,
                embedding,
            ),
        )


# ============================================================
# INGEST ONE DOCUMENT
# ============================================================

def ingest_document(conn, path):

    metadata, body = parse_markdown(path)

    document_id = metadata["document_id"]
    version = int(metadata["version"])

    print(
        f"\nProcessing {path.name} "
        f"({document_id} v{version})"
    )

    insert_document(
        conn,
        metadata,
        path,
    )

    delete_existing_chunks(
        conn,
        document_id,
        version,
    )

    sections = split_sections(body)

    all_chunks = []

    chunk_index = 0

    for section_title, section_text in sections:

        section_chunks = chunk_words(
            section_text
        )

        for chunk in section_chunks:

            # Include heading in embedding text
            # because heading carries useful context.

            embedding_text = f"""
            Document: {metadata.get("title", document_id)}
            Category: {metadata.get("category", "")}
            Section: {section_title}

            {chunk}
            """.strip()

            all_chunks.append(
                (
                    section_title,
                    chunk_index,
                    chunk,
                    embedding_text,
                )
            )

            chunk_index += 1

    if not all_chunks:

        raise ValueError(
            f"No chunks generated for {path.name}"
        )

    texts = [
        item[3]
        for item in all_chunks
    ]

    print(
        f"Generating {len(texts)} embeddings..."
    )

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    for item, embedding in zip(
        all_chunks,
        embeddings,
    ):

        (
            section_title,
            chunk_index,
            content,
            _,
        ) = item

        chunk_id = create_chunk_id(
            document_id,
            version,
            chunk_index,
        )

        insert_chunk(
            conn,
            chunk_id,
            document_id,
            version,
            section_title,
            chunk_index,
            content,
            embedding,
        )

    print(
        f"[PASS] {document_id}: "
        f"{len(all_chunks)} chunks"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TT&T RAG KNOWLEDGE INGESTION")
    print("=" * 70)

    markdown_files = sorted(
        KNOWLEDGE_DIR.glob("*.md")
    )

    if not markdown_files:

        raise RuntimeError(
            f"No Markdown documents found in "
            f"{KNOWLEDGE_DIR}"
        )

    print(
        f"Found {len(markdown_files)} "
        f"knowledge documents."
    )

    with psycopg.connect(
        **DB_CONFIG
    ) as conn:

        register_vector(conn)

        try:

            for path in markdown_files:

                ingest_document(
                    conn,
                    path,
                )

            conn.commit()

        except Exception:

            conn.rollback()

            print(
                "\nIngestion failed. "
                "Database transaction rolled back."
            )

            raise

    print("\n" + "=" * 70)
    print("RAG INGESTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()