from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

import numpy as np
import psycopg

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer, CrossEncoder

try:
    from scripts.query_expansion import analyze_query
except ModuleNotFoundError:
    from query_expansion import analyze_query


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5",
)

RERANKER_MODEL_NAME = os.getenv(
    "RERANKER_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)


# ============================================================
# RETRIEVAL SETTINGS
# ============================================================

# Retrieve this many independently from both retrievers.
VECTOR_CANDIDATES = 20
KEYWORD_CANDIDATES = 20

# Keep this many after RRF.
RRF_TOP_K = 15

# Final answer context.
FINAL_TOP_K = 5

# Standard Reciprocal Rank Fusion constant.
RRF_K = 60


# ============================================================
# FINAL SCORE WEIGHTS
# ============================================================

# Starting values.
# Later we will tune these using the evaluation dataset.

RERANKER_WEIGHT = 0.45
RRF_WEIGHT = 0.40
METADATA_WEIGHT = 0.15


# Print every retrieval stage while developing.
DEBUG = True


# ============================================================
# MODELS
# ============================================================

print(
    f"Loading embedding model: "
    f"{EMBEDDING_MODEL_NAME}"
)

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


print(
    f"Loading reranker model: "
    f"{RERANKER_MODEL_NAME}"
)

reranker = CrossEncoder(
    RERANKER_MODEL_NAME
)


# ============================================================
# CANDIDATE DATA STRUCTURE
# ============================================================

@dataclass
class Candidate:

    chunk_id: str
    document_id: str
    document_version: int

    title: Optional[str]
    category: Optional[str]

    section_title: Optional[str]
    content: str

    vector_rank: Optional[int] = None
    vector_score: Optional[float] = None

    keyword_rank: Optional[int] = None
    keyword_score: Optional[float] = None

    rrf_rank: Optional[int] = None
    rrf_score: float = 0.0

    reranker_score: Optional[float] = None

    normalized_rrf: float = 0.0
    normalized_reranker: float = 0.0

    metadata_score: float = 0.0

    final_score: float = 0.0


# ============================================================
# QUERY EMBEDDING
# ============================================================

def embed_query(query: str) -> np.ndarray:
    """
    Convert the expanded semantic query into a dense vector.

    BGE retrieval models can benefit from a query instruction.
    """

    if "bge" in EMBEDDING_MODEL_NAME.lower():

        text = (
            "Represent this sentence for searching "
            "relevant passages: "
            + query
        )

    else:

        text = query


    embedding = embedding_model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


    return np.asarray(
        embedding,
        dtype=np.float32,
    )


# ============================================================
# VECTOR SEARCH
# ============================================================

def vector_search(
    conn,
    query_embedding: np.ndarray,
    limit: int = VECTOR_CANDIDATES,
):
    """
    Dense semantic retrieval using pgvector cosine distance.
    """

    sql = """
        SELECT
            c.chunk_id,
            c.document_id,
            c.document_version,

            d.title,
            d.category,

            c.section_title,
            c.content,

            1 - (
                c.embedding <=> %s
            ) AS similarity

        FROM chunks c

        JOIN documents d
          ON d.document_id = c.document_id
         AND d.version = c.document_version

        ORDER BY
            c.embedding <=> %s

        LIMIT %s;
    """


    with conn.cursor() as cur:

        cur.execute(
            sql,
            (
                query_embedding,
                query_embedding,
                limit,
            ),
        )

        return cur.fetchall()


# ============================================================
# POSTGRESQL FULL-TEXT SEARCH
# ============================================================

def keyword_search(
    conn,
    query: str,
    limit: int = KEYWORD_CANDIDATES,
):
    """
    Sparse / lexical retrieval using PostgreSQL FTS.

    websearch_to_tsquery supports:
        quoted phrases
        OR
        normal user-style queries
    """

    sql = """
        SELECT
            c.chunk_id,
            c.document_id,
            c.document_version,

            d.title,
            d.category,

            c.section_title,
            c.content,

            ts_rank_cd(
                c.search_vector,
                websearch_to_tsquery(
                    'english',
                    %s
                )
            ) AS lexical_score

        FROM chunks c

        JOIN documents d
          ON d.document_id = c.document_id
         AND d.version = c.document_version

        WHERE
            c.search_vector @@
            websearch_to_tsquery(
                'english',
                %s
            )

        ORDER BY
            lexical_score DESC

        LIMIT %s;
    """


    with conn.cursor() as cur:

        cur.execute(
            sql,
            (
                query,
                query,
                limit,
            ),
        )

        return cur.fetchall()


# ============================================================
# RECIPROCAL RANK FUSION
# ============================================================

def reciprocal_rank_fusion(
    vector_results,
    keyword_results,
) -> list[Candidate]:
    """
    Combine vector and keyword rankings.

    RRF uses rank positions instead of trying to directly
    compare cosine similarity and FTS scores.
    """

    candidates: dict[str, Candidate] = {}


    # --------------------------------------------------------
    # VECTOR RESULTS
    # --------------------------------------------------------

    for rank, row in enumerate(
        vector_results,
        start=1,
    ):

        (
            chunk_id,
            document_id,
            document_version,
            title,
            category,
            section_title,
            content,
            vector_score,
        ) = row


        candidate = candidates.get(
            chunk_id
        )


        if candidate is None:

            candidate = Candidate(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                title=title,
                category=category,
                section_title=section_title,
                content=content,
            )

            candidates[chunk_id] = candidate


        candidate.vector_rank = rank

        candidate.vector_score = float(
            vector_score
        )


        candidate.rrf_score += (
            1.0
            /
            (RRF_K + rank)
        )


    # --------------------------------------------------------
    # KEYWORD RESULTS
    # --------------------------------------------------------

    for rank, row in enumerate(
        keyword_results,
        start=1,
    ):

        (
            chunk_id,
            document_id,
            document_version,
            title,
            category,
            section_title,
            content,
            keyword_score,
        ) = row


        candidate = candidates.get(
            chunk_id
        )


        if candidate is None:

            candidate = Candidate(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                title=title,
                category=category,
                section_title=section_title,
                content=content,
            )

            candidates[chunk_id] = candidate


        candidate.keyword_rank = rank

        candidate.keyword_score = float(
            keyword_score
        )


        candidate.rrf_score += (
            1.0
            /
            (RRF_K + rank)
        )


    ranked = sorted(
        candidates.values(),
        key=lambda candidate: candidate.rrf_score,
        reverse=True,
    )


    ranked = ranked[:RRF_TOP_K]


    for rank, candidate in enumerate(
        ranked,
        start=1,
    ):

        candidate.rrf_rank = rank


    return ranked


# ============================================================
# RERANKER PASSAGE
# ============================================================

def make_reranker_passage(
    candidate: Candidate,
) -> str:
    """
    Give the reranker more context than only chunk content.
    """

    return f"""
Document: {candidate.title or candidate.document_id}
Category: {candidate.category or ""}
Section: {candidate.section_title or ""}

{candidate.content}
""".strip()


# ============================================================
# CROSS-ENCODER RERANKING
# ============================================================

def rerank(
    query: str,
    candidates: list[Candidate],
) -> list[Candidate]:
    """
    Score RRF candidates with the cross-encoder.

    IMPORTANT:
    We do NOT cut to Top 5 here.

    Every RRF candidate continues to final scoring so
    metadata and RRF evidence cannot be erased too early.
    """

    if not candidates:
        return []


    pairs = [
        (
            query,
            make_reranker_passage(candidate),
        )
        for candidate in candidates
    ]


    scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )


    for candidate, score in zip(
        candidates,
        scores,
    ):

        candidate.reranker_score = float(
            score
        )


    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.reranker_score
            if candidate.reranker_score is not None
            else float("-inf")
        ),
        reverse=True,
    )


# ============================================================
# SCORE NORMALIZATION
# ============================================================

def minmax_normalize(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    if maximum == minimum:
        return 1.0

    return (
        value - minimum
    ) / (
        maximum - minimum
    )


# ============================================================
# FINAL WEIGHTED SCORING
# ============================================================

def calculate_final_scores(
    candidates: list[Candidate],
    preferred_categories: list[str],
) -> list[Candidate]:
    """
    Final ranking combines:

        reranker score
        +
        RRF evidence
        +
        metadata / intent-category match
    """

    if not candidates:
        return []


    # --------------------------------------------------------
    # RERANKER RANGE
    # --------------------------------------------------------

    reranker_values = [
        candidate.reranker_score
        for candidate in candidates
        if candidate.reranker_score is not None
    ]


    reranker_min = min(
        reranker_values
    )

    reranker_max = max(
        reranker_values
    )


    # --------------------------------------------------------
    # RRF RANGE
    # --------------------------------------------------------

    rrf_values = [
        candidate.rrf_score
        for candidate in candidates
    ]


    rrf_min = min(
        rrf_values
    )

    rrf_max = max(
        rrf_values
    )


    preferred = {
        category.lower()
        for category in preferred_categories
    }


    # --------------------------------------------------------
    # CALCULATE EACH FINAL SCORE
    # --------------------------------------------------------

    for candidate in candidates:

        candidate.normalized_reranker = (
            minmax_normalize(
                candidate.reranker_score,
                reranker_min,
                reranker_max,
            )
        )


        candidate.normalized_rrf = (
            minmax_normalize(
                candidate.rrf_score,
                rrf_min,
                rrf_max,
            )
        )


        # Soft category boost.
        # This is NOT a hard filter.

        if (
            candidate.category
            and candidate.category.lower()
            in preferred
        ):

            candidate.metadata_score = 1.0

        else:

            candidate.metadata_score = 0.0


        candidate.final_score = (

            RERANKER_WEIGHT
            * candidate.normalized_reranker

            +

            RRF_WEIGHT
            * candidate.normalized_rrf

            +

            METADATA_WEIGHT
            * candidate.metadata_score
        )


    return sorted(
        candidates,
        key=lambda candidate: candidate.final_score,
        reverse=True,
    )


# ============================================================
# DEBUG: QUERY ANALYSIS
# ============================================================

def print_query_analysis(
    analysis: dict,
):

    print("\n")
    print("=" * 80)
    print("QUERY ANALYSIS")
    print("=" * 80)

    print(
        f"Intent              : "
        f"{analysis['intent']}"
    )

    print(
        f"Original query      : "
        f"{analysis['original_query']}"
    )

    print(
        f"Semantic query      : "
        f"{analysis['semantic_query']}"
    )

    print(
        f"Keyword query       : "
        f"{analysis['keyword_query']}"
    )

    print(
        f"Preferred categories: "
        f"{analysis['preferred_categories']}"
    )


# ============================================================
# DEBUG: RAW VECTOR / KEYWORD RESULTS
# ============================================================

def print_raw_results(
    vector_results,
    keyword_results,
):

    print("\n")
    print("=" * 80)
    print("VECTOR SEARCH RESULTS")
    print("=" * 80)


    if not vector_results:
        print("No vector results.")


    for rank, row in enumerate(
        vector_results,
        start=1,
    ):

        print(
            f"{rank:>2}. "
            f"{row[1]:<20} "
            f"score={float(row[7]):.4f}"
        )


    print("\n")
    print("=" * 80)
    print("KEYWORD SEARCH RESULTS")
    print("=" * 80)


    if not keyword_results:
        print("No keyword results.")


    for rank, row in enumerate(
        keyword_results,
        start=1,
    ):

        print(
            f"{rank:>2}. "
            f"{row[1]:<20} "
            f"score={float(row[7]):.4f}"
        )


# ============================================================
# DEBUG: RRF RESULTS
# ============================================================

def print_rrf_results(
    candidates: list[Candidate],
):

    print("\n")
    print("=" * 80)
    print("RRF TOP CANDIDATES")
    print("=" * 80)


    for candidate in candidates:

        print(
            f"{candidate.rrf_rank:>2}. "
            f"{candidate.document_id:<20} "
            f"vector={str(candidate.vector_rank):<5} "
            f"keyword={str(candidate.keyword_rank):<5} "
            f"rrf={candidate.rrf_score:.6f}"
        )


# ============================================================
# DEBUG: RERANKER RESULTS
# ============================================================

def print_reranker_results(
    candidates: list[Candidate],
):

    print("\n")
    print("=" * 80)
    print("RERANKER RESULTS")
    print("=" * 80)


    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):

        print(
            f"{rank:>2}. "
            f"{candidate.document_id:<20} "
            f"reranker={candidate.reranker_score:.4f} "
            f"rrf_rank={candidate.rrf_rank}"
        )


# ============================================================
# COMPLETE HYBRID RETRIEVAL PIPELINE
# ============================================================

def hybrid_search(
    query: str,
) -> list[Candidate]:

    # --------------------------------------------------------
    # 1. DOMAIN QUERY EXPANSION
    # --------------------------------------------------------

    analysis = analyze_query(
        query
    )


    if DEBUG:
        print_query_analysis(
            analysis
        )


    # --------------------------------------------------------
    # 2. SEMANTIC QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = embed_query(
        analysis["semantic_query"]
    )


    # --------------------------------------------------------
    # 3. VECTOR + KEYWORD RETRIEVAL
    # --------------------------------------------------------

    with psycopg.connect(
        **DB_CONFIG
    ) as conn:

        register_vector(
            conn
        )


        vector_results = vector_search(
            conn,
            query_embedding,
            limit=VECTOR_CANDIDATES,
        )


        keyword_results = keyword_search(
            conn,
            analysis["keyword_query"],
            limit=KEYWORD_CANDIDATES,
        )


        # If expansion accidentally gives no lexical result,
        # retry using the customer's original wording.

        if (
            not keyword_results
            and analysis["keyword_query"] != query
        ):

            keyword_results = keyword_search(
                conn,
                query,
                limit=KEYWORD_CANDIDATES,
            )


    if DEBUG:
        print_raw_results(
            vector_results,
            keyword_results,
        )


    # --------------------------------------------------------
    # 4. RECIPROCAL RANK FUSION
    # --------------------------------------------------------

    rrf_candidates = reciprocal_rank_fusion(
        vector_results,
        keyword_results,
    )


    if DEBUG:
        print_rrf_results(
            rrf_candidates
        )


    # --------------------------------------------------------
    # 5. CROSS-ENCODER RERANKING
    # --------------------------------------------------------

    reranked_candidates = rerank(
        analysis["original_query"],
        rrf_candidates,
    )


    if DEBUG:
        print_reranker_results(
            reranked_candidates
        )


    # --------------------------------------------------------
    # 6. METADATA + WEIGHTED FINAL SCORE
    # --------------------------------------------------------

    final_candidates = calculate_final_scores(
        reranked_candidates,
        analysis["preferred_categories"],
    )


    # --------------------------------------------------------
    # 7. FINAL TOP 5
    # --------------------------------------------------------

    return diversify_results(
    final_candidates,
    final_k=FINAL_TOP_K,
    max_chunks_per_document=2,
    )


# ============================================================
# FINAL RESULTS
# ============================================================

def print_results(
    query: str,
    results: list[Candidate],
):

    print("\n")
    print("=" * 80)
    print("TT&T FINAL HYBRID RAG RESULTS")
    print("=" * 80)

    print(
        f"\nQuery: {query}\n"
    )


    if not results:

        print(
            "No relevant chunks found."
        )

        return


    for rank, candidate in enumerate(
        results,
        start=1,
    ):

        print("-" * 80)

        print(
            f"FINAL RANK          : {rank}"
        )

        print(
            f"Document            : "
            f"{candidate.document_id}"
        )

        print(
            f"Title               : "
            f"{candidate.title}"
        )

        print(
            f"Category            : "
            f"{candidate.category}"
        )

        print(
            f"Section             : "
            f"{candidate.section_title}"
        )

        print(
            f"Chunk               : "
            f"{candidate.chunk_id}"
        )

        print(
            f"Vector rank         : "
            f"{candidate.vector_rank}"
        )

        if candidate.vector_score is not None:

            print(
                f"Vector similarity   : "
                f"{candidate.vector_score:.4f}"
            )


        print(
            f"Keyword rank        : "
            f"{candidate.keyword_rank}"
        )

        if candidate.keyword_score is not None:

            print(
                f"Keyword score       : "
                f"{candidate.keyword_score:.4f}"
            )


        print(
            f"RRF rank            : "
            f"{candidate.rrf_rank}"
        )

        print(
            f"RRF score           : "
            f"{candidate.rrf_score:.6f}"
        )


        if candidate.reranker_score is not None:

            print(
                f"Reranker raw score  : "
                f"{candidate.reranker_score:.4f}"
            )


        print(
            f"Normalized reranker : "
            f"{candidate.normalized_reranker:.4f}"
        )

        print(
            f"Normalized RRF      : "
            f"{candidate.normalized_rrf:.4f}"
        )

        print(
            f"Metadata score      : "
            f"{candidate.metadata_score:.4f}"
        )

        print(
            f"FINAL SCORE         : "
            f"{candidate.final_score:.4f}"
        )


        print("\nContent:\n")

        print(
            candidate.content[:1000]
        )

        print()


    print("=" * 80)


# ============================================================
# diversify_results
# ============================================================

def diversify_results(
    candidates: list[Candidate],
    final_k: int = FINAL_TOP_K,
    max_chunks_per_document: int = 2,
) -> list[Candidate]:
    """
    Prevent one document from consuming the entire final
    retrieval context.

    Keeps at most N chunks from the same document.
    """

    selected = []

    document_counts = {}

    for candidate in candidates:

        current_count = document_counts.get(
            candidate.document_id,
            0,
        )

        if current_count >= max_chunks_per_document:
            continue

        selected.append(candidate)

        document_counts[candidate.document_id] = (
            current_count + 1
        )

        if len(selected) >= final_k:
            break

    return selected



# ============================================================
# INTERACTIVE TEST
# ============================================================

def main():

    print("=" * 80)
    print("TT&T HYBRID RAG RETRIEVAL")
    print("=" * 80)

    print(
        f"\nEmbedding model : "
        f"{EMBEDDING_MODEL_NAME}"
    )

    print(
        f"Reranker model  : "
        f"{RERANKER_MODEL_NAME}"
    )

    print(
        "\nArchitecture:"
        "\nQuery Expansion"
        "\n→ BGE + PostgreSQL FTS"
        "\n→ RRF"
        "\n→ Top 15"
        "\n→ Reranker"
        "\n→ Metadata Signal"
        "\n→ Weighted Final Score"
        "\n→ Top 5"
    )


    while True:

        query = input(
            "\nEnter your question "
            "(or type exit): "
        ).strip()


        if query.lower() in {
            "exit",
            "quit",
            "q",
        }:

            break


        if not query:

            continue


        try:

            results = hybrid_search(
                query
            )


            print_results(
                query,
                results,
            )


        except Exception as exc:

            print(
                "\n[ERROR] Retrieval failed:"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()