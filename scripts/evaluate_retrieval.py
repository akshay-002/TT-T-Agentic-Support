from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean

import hybrid_retrieval as retriever


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

EVALUATION_FILE = (
    ROOT
    / "data"
    / "evaluation"
    / "cases.jsonl"
)

REPORT_DIR = ROOT / "reports"

CSV_REPORT = (
    REPORT_DIR
    / "retrieval_evaluation.csv"
)

JSON_REPORT = (
    REPORT_DIR
    / "retrieval_evaluation.json"
)


# ============================================================
# SETTINGS
# ============================================================

# Turn off all the verbose retrieval-stage printing.
retriever.DEBUG = False

TOP_K_VALUES = [1, 3, 5]


# ============================================================
# LOAD EVALUATION CASES
# ============================================================

def load_cases() -> list[dict]:

    cases = []

    with EVALUATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:
                case = json.loads(line)

            except json.JSONDecodeError as exc:

                raise ValueError(
                    f"Invalid JSON on line "
                    f"{line_number}: {exc}"
                )

            cases.append(case)

    return cases


# ============================================================
# UNIQUE DOCUMENT RESULTS
# ============================================================

def unique_document_ids(
    results,
) -> list[str]:
    """
    hybrid_search returns chunks.

    Multiple chunks may belong to the same policy document.

    For retrieval evaluation we care about policy/document
    retrieval, so duplicates are removed while preserving rank.
    """

    seen = set()
    documents = []

    for candidate in results:

        document_id = candidate.document_id

        if document_id in seen:
            continue

        seen.add(document_id)
        documents.append(document_id)

    return documents


# ============================================================
# METRICS FOR ONE CASE
# ============================================================

def recall_at_k(
    retrieved: list[str],
    expected: list[str],
    k: int,
) -> float:
    """
    Fraction of expected policy documents appearing in Top K.

    Example:

        expected = [
            "PLAN-CATALOG-01",
            "BILL-ACT-01"
        ]

        retrieved Top 3 contains only BILL-ACT-01

        Recall@3 = 1 / 2 = 0.5
    """

    if not expected:
        return 0.0

    expected_set = set(expected)

    retrieved_set = set(
        retrieved[:k]
    )

    hits = len(
        expected_set
        & retrieved_set
    )

    return hits / len(expected_set)


def hit_at_k(
    retrieved: list[str],
    expected: list[str],
    k: int,
) -> int:
    """
    Binary metric.

    1 if ANY expected policy appears in Top K.
    """

    expected_set = set(expected)

    return int(
        any(
            document_id in expected_set
            for document_id in retrieved[:k]
        )
    )


def reciprocal_rank(
    retrieved: list[str],
    expected: list[str],
) -> float:
    """
    Reciprocal rank of the first relevant document.

    Rank 1 -> 1.0
    Rank 2 -> 0.5
    Rank 3 -> 0.333...
    None   -> 0
    """

    expected_set = set(expected)

    for rank, document_id in enumerate(
        retrieved,
        start=1,
    ):

        if document_id in expected_set:

            return 1.0 / rank

    return 0.0


def all_expected_found(
    retrieved: list[str],
    expected: list[str],
    k: int,
) -> int:
    """
    Returns 1 only if ALL expected policy documents
    are found within Top K.
    """

    expected_set = set(expected)

    retrieved_set = set(
        retrieved[:k]
    )

    return int(
        expected_set.issubset(
            retrieved_set
        )
    )


# ============================================================
# EVALUATE ONE CASE
# ============================================================

def evaluate_case(
    case: dict,
) -> dict | None:

    expected = case.get(
        "expected",
        {}
    )

    expected_policy_ids = expected.get(
        "policy_ids",
        []
    )

    # --------------------------------------------------------
    # Retrieval metrics only apply when the test case
    # actually specifies expected policy evidence.
    # --------------------------------------------------------

    if not expected_policy_ids:
        return None


    question = case["question"]

    results = retriever.hybrid_search(
        question
    )

    retrieved_documents = (
        unique_document_ids(
            results
        )
    )


    result = {
        "case_id": case.get(
            "case_id"
        ),

        "group": case.get(
            "group"
        ),

        "scenario_family": case.get(
            "scenario_family"
        ),

        "question": question,

        "expected_intent": expected.get(
            "intent"
        ),

        "expected_policy_ids": (
            expected_policy_ids
        ),

        "retrieved_document_ids": (
            retrieved_documents
        ),

        "top1_document": (
            retrieved_documents[0]
            if retrieved_documents
            else None
        ),

        "mrr": reciprocal_rank(
            retrieved_documents,
            expected_policy_ids,
        ),
    }


    for k in TOP_K_VALUES:

        result[
            f"recall_at_{k}"
        ] = recall_at_k(
            retrieved_documents,
            expected_policy_ids,
            k,
        )

        result[
            f"hit_at_{k}"
        ] = hit_at_k(
            retrieved_documents,
            expected_policy_ids,
            k,
        )

        result[
            f"all_expected_at_{k}"
        ] = all_expected_found(
            retrieved_documents,
            expected_policy_ids,
            k,
        )


    return result


# ============================================================
# PRINT ONE RESULT
# ============================================================

def print_case_result(
    result: dict,
):

    expected = result[
        "expected_policy_ids"
    ]

    retrieved = result[
        "retrieved_document_ids"
    ]


    top1_pass = (
        result["hit_at_1"] == 1
    )


    status = (
        "PASS"
        if top1_pass
        else "MISS"
    )


    print("-" * 80)

    print(
        f"{result['case_id']} "
        f"[{status}]"
    )

    print(
        f"Question : "
        f"{result['question']}"
    )

    print(
        f"Expected : "
        f"{', '.join(expected)}"
    )

    print(
        f"Retrieved: "
        f"{', '.join(retrieved)}"
    )

    print(
        f"R@1={result['recall_at_1']:.2f}  "
        f"R@3={result['recall_at_3']:.2f}  "
        f"R@5={result['recall_at_5']:.2f}  "
        f"RR={result['mrr']:.3f}"
    )


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    results: list[dict],
):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    fieldnames = [
        "case_id",
        "group",
        "scenario_family",
        "expected_intent",
        "question",
        "expected_policy_ids",
        "retrieved_document_ids",
        "top1_document",
        "recall_at_1",
        "recall_at_3",
        "recall_at_5",
        "hit_at_1",
        "hit_at_3",
        "hit_at_5",
        "all_expected_at_1",
        "all_expected_at_3",
        "all_expected_at_5",
        "mrr",
    ]


    with CSV_REPORT.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()


        for result in results:

            row = result.copy()

            row["expected_policy_ids"] = (
                "|".join(
                    result[
                        "expected_policy_ids"
                    ]
                )
            )

            row[
                "retrieved_document_ids"
            ] = (
                "|".join(
                    result[
                        "retrieved_document_ids"
                    ]
                )
            )

            writer.writerow(row)


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    results: list[dict],
    summary: dict,
):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    payload = {
        "summary": summary,
        "cases": results,
    }


    with JSON_REPORT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TT&T RAG RETRIEVAL EVALUATION")
    print("=" * 80)


    cases = load_cases()


    print(
        f"\nLoaded {len(cases)} "
        f"evaluation cases."
    )


    evaluated_results = []

    skipped_cases = 0


    for index, case in enumerate(
        cases,
        start=1,
    ):

        expected_policy_ids = (
            case
            .get("expected", {})
            .get("policy_ids", [])
        )


        if not expected_policy_ids:

            skipped_cases += 1

            continue


        print(
            f"\nEvaluating "
            f"{index}/{len(cases)}: "
            f"{case.get('case_id')}"
        )


        try:

            result = evaluate_case(
                case
            )


            if result is not None:

                evaluated_results.append(
                    result
                )

                print_case_result(
                    result
                )


        except Exception as exc:

            print(
                f"[ERROR] "
                f"{case.get('case_id')}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


    if not evaluated_results:

        print(
            "\nNo cases with expected "
            "policy IDs were found."
        )

        return


    # ========================================================
    # AGGREGATE METRICS
    # ========================================================

    summary = {

        "total_cases_in_file":
            len(cases),

        "cases_evaluated":
            len(evaluated_results),

        "cases_skipped_no_policy_ids":
            skipped_cases,

        "recall_at_1":
            mean(
                r["recall_at_1"]
                for r in evaluated_results
            ),

        "recall_at_3":
            mean(
                r["recall_at_3"]
                for r in evaluated_results
            ),

        "recall_at_5":
            mean(
                r["recall_at_5"]
                for r in evaluated_results
            ),

        "hit_rate_at_1":
            mean(
                r["hit_at_1"]
                for r in evaluated_results
            ),

        "hit_rate_at_3":
            mean(
                r["hit_at_3"]
                for r in evaluated_results
            ),

        "hit_rate_at_5":
            mean(
                r["hit_at_5"]
                for r in evaluated_results
            ),

        "all_expected_at_5":
            mean(
                r["all_expected_at_5"]
                for r in evaluated_results
            ),

        "mrr":
            mean(
                r["mrr"]
                for r in evaluated_results
            ),
    }


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 80)
    print("FINAL RETRIEVAL METRICS")
    print("=" * 80)

    print(
        f"Total cases       : "
        f"{summary['total_cases_in_file']}"
    )

    print(
        f"Evaluated         : "
        f"{summary['cases_evaluated']}"
    )

    print(
        f"Skipped           : "
        f"{summary['cases_skipped_no_policy_ids']}"
    )


    print("\nDocument Recall")

    print(
        f"Recall@1          : "
        f"{summary['recall_at_1']:.3f}"
    )

    print(
        f"Recall@3          : "
        f"{summary['recall_at_3']:.3f}"
    )

    print(
        f"Recall@5          : "
        f"{summary['recall_at_5']:.3f}"
    )


    print("\nAt-Least-One Relevant Policy")

    print(
        f"Hit Rate@1        : "
        f"{summary['hit_rate_at_1']:.3f}"
    )

    print(
        f"Hit Rate@3        : "
        f"{summary['hit_rate_at_3']:.3f}"
    )

    print(
        f"Hit Rate@5        : "
        f"{summary['hit_rate_at_5']:.3f}"
    )


    print("\nMulti-policy Coverage")

    print(
        f"All Expected @5   : "
        f"{summary['all_expected_at_5']:.3f}"
    )


    print("\nRanking")

    print(
        f"MRR               : "
        f"{summary['mrr']:.3f}"
    )


    # ========================================================
    # FAILURES
    # ========================================================

    top1_failures = [
        result
        for result in evaluated_results
        if result["hit_at_1"] == 0
    ]


    print("\n")
    print("=" * 80)
    print("TOP-1 FAILURES")
    print("=" * 80)


    if not top1_failures:

        print(
            "No Top-1 retrieval failures."
        )

    else:

        for result in top1_failures:

            print(
                f"\n{result['case_id']}"
            )

            print(
                f"Question : "
                f"{result['question']}"
            )

            print(
                f"Expected : "
                f"{result['expected_policy_ids']}"
            )

            print(
                f"Retrieved: "
                f"{result['retrieved_document_ids']}"
            )


    # ========================================================
    # SAVE REPORTS
    # ========================================================

    save_csv(
        evaluated_results
    )

    save_json(
        evaluated_results,
        summary,
    )


    print("\n")
    print("=" * 80)
    print("REPORTS SAVED")
    print("=" * 80)

    print(
        f"CSV : {CSV_REPORT}"
    )

    print(
        f"JSON: {JSON_REPORT}"
    )


if __name__ == "__main__":
    main()