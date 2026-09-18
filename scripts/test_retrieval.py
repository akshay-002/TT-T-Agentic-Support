from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


# IMPORTANT:
# This must match the model you used in ingest_knowledge.py
# MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


def search_knowledge(query: str, top_k: int = 5):
    """
    Embed the query and retrieve the most similar
    RAG chunks from PostgreSQL using cosine distance.
    """

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
    )

    with psycopg.connect(**DB_CONFIG) as conn:
        register_vector(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.chunk_id,
                    c.document_id,
                    c.section_title,
                    c.content,
                    1 - (c.embedding <=> %s) AS similarity
                FROM chunks c
                ORDER BY c.embedding <=> %s
                LIMIT %s;
                """,
                (
                    query_embedding,
                    query_embedding,
                    top_k,
                ),
            )

            return cur.fetchall()


def main():
    print("=" * 70)
    print("TT&T RAG RETRIEVAL TEST")
    print("=" * 70)

    query = input("\nEnter your question: ").strip()

    if not query:
        print("No query entered.")
        return

    results = search_knowledge(
        query=query,
        top_k=5,
    )

    print("\nTop retrieval results:\n")

    for rank, row in enumerate(results, start=1):
        (
            chunk_id,
            document_id,
            section_title,
            content,
            similarity,
        ) = row

        print("-" * 70)
        print(f"Rank       : {rank}")
        print(f"Document   : {document_id}")
        print(f"Chunk      : {chunk_id}")
        print(f"Section    : {section_title}")
        print(f"Similarity : {similarity:.4f}")
        print()
        print(content[:700])

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()