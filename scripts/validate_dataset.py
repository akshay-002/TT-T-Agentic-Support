# scripts/validate_dataset.py

from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import json
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed.")
    print("Run: pip install pyyaml")
    sys.exit(1)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
OPERATIONAL_DIR = DATA_DIR / "operational"
KNOWLEDGE_DIR = DATA_DIR / "knowledge" / "documents"
EVALUATION_DIR = DATA_DIR / "evaluation"


# ============================================================
# POSSIBLE FILE NAMES
#
# This lets the script work even if your files are named
# slightly differently.
# ============================================================

FILE_ALIASES = {
    "customers": [
        "customers.json",
        "users.json",
    ],
    "accounts": [
        "accounts.json",
    ],
    "lines": [
        "lines.json",
        "phone_lines.json",
    ],
    "plans": [
        "plans.json",
    ],
    "subscriptions": [
        "subscriptions.json",
    ],
    "devices": [
        "devices.json",
    ],
    "invoices": [
        "invoices.json",
    ],
    "invoice_items": [
        "invoice_items.json",
        "invoice-items.json",
        "invoiceitems.json",
    ],
    "payments": [
        "payments.json",
    ],
    "usage": [
        "usage.json",
        "usage_records.json",
    ],
    "outages": [
        "outages.json",
    ],
    "tickets": [
        "support_tickets.json",
        "tickets.json",
    ],
    "connection_requests": [
        "connection_requests.json",
    ],
}


# These are expected for the core TT&T MVP.
CORE_DATASETS = {
    "accounts",
    "lines",
    "invoices",
    "invoice_items",
    "usage",
    "tickets",
}


# ============================================================
# REPORTING
# ============================================================

errors = []
warnings = []
passes = []


def passed(message):
    passes.append(message)
    print(f"[PASS] {message}")


def warning(message):
    warnings.append(message)
    print(f"[WARN] {message}")


def error(message):
    errors.append(message)
    print(f"[FAIL] {message}")


# ============================================================
# HELPERS
# ============================================================

def normalize(text):
    return text.lower().replace("-", "_").replace(" ", "_")


def find_dataset_file(dataset_name):
    """
    Search operational/ recursively for expected file names.
    """

    aliases = FILE_ALIASES.get(dataset_name, [])

    # First look for exact known names.
    for alias in aliases:
        matches = list(OPERATIONAL_DIR.rglob(alias))

        if matches:
            return matches[0]

    # Fallback: compare normalized stem names.
    target = normalize(dataset_name)

    for file in OPERATIONAL_DIR.rglob("*.json"):
        if normalize(file.stem) == target:
            return file

    return None


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError as exc:
        error(
            f"Malformed JSON: {path.relative_to(ROOT)} "
            f"(line {exc.lineno}, column {exc.colno})"
        )
        return None

    except Exception as exc:
        error(f"Could not read {path}: {exc}")
        return None


def records_from_json(data, dataset_name):
    """
    Supports:

    [
        {...},
        {...}
    ]

    or

    {
        "accounts": [...]
    }

    or

    {
        "records": [...]
    }
    """

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        possible_keys = [
            dataset_name,
            "records",
            "data",
            "items",
        ]

        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                return data[key]

        # Allow object dictionaries:
        #
        # {
        #   "USER_1001": {...},
        #   "USER_1002": {...}
        # }
        if data and all(isinstance(value, dict) for value in data.values()):
            return list(data.values())

        # Single record
        return [data]

    error(f"Unsupported JSON format for dataset '{dataset_name}'")
    return []


def first_value(record, field_names):
    for field in field_names:
        if field in record and record[field] is not None:
            return record[field]

    return None


def collect_ids(records, fields, label):
    values = []

    for index, record in enumerate(records):
        value = first_value(record, fields)

        if value is None:
            error(
                f"{label}: record #{index + 1} has no identifier "
                f"(expected one of {fields})"
            )
            continue

        values.append(str(value))

    duplicates = [
        value
        for value, count in Counter(values).items()
        if count > 1
    ]

    if duplicates:
        error(
            f"{label}: duplicate IDs found: "
            + ", ".join(duplicates[:20])
        )
    else:
        passed(f"{label}: {len(values)} unique IDs")

    return set(values)


def check_reference(
    child_records,
    child_fields,
    parent_ids,
    relationship_name,
):
    bad = []
    missing_field = []

    for index, record in enumerate(child_records):

        value = first_value(record, child_fields)

        if value is None:
            missing_field.append(index + 1)
            continue

        if str(value) not in parent_ids:
            bad.append(str(value))

    if missing_field:
        error(
            f"{relationship_name}: "
            f"{len(missing_field)} records missing reference field "
            f"{child_fields}"
        )

    if bad:
        error(
            f"{relationship_name}: invalid references found: "
            + ", ".join(sorted(set(bad))[:20])
        )

    if not bad and not missing_field:
        passed(f"{relationship_name}: all references valid")


def amount_to_cents(record, cent_fields, dollar_fields):
    """
    Supports fields like:

    total_cents = 10500

    OR

    total = 105.00
    """

    value = first_value(record, cent_fields)

    if value is not None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    value = first_value(record, dollar_fields)

    if value is not None:
        try:
            return int(
                Decimal(str(value)) * Decimal("100")
            )
        except (InvalidOperation, ValueError, TypeError):
            return None

    return None


# ============================================================
# LOAD ALL OPERATIONAL DATA
# ============================================================

print("\n" + "=" * 70)
print("TT&T SYNTHETIC DATASET VALIDATION")
print("=" * 70)

datasets = {}
dataset_paths = {}

print("\n1. Checking operational JSON files\n")

if not OPERATIONAL_DIR.exists():
    error(f"Missing directory: {OPERATIONAL_DIR}")
    sys.exit(1)


# First verify that EVERY JSON file is syntactically valid.
all_operational_json = list(OPERATIONAL_DIR.rglob("*.json"))

if not all_operational_json:
    error("No JSON files found under data/operational/")
else:
    for path in all_operational_json:
        data = load_json_file(path)

        if data is not None:
            passed(f"Valid JSON: {path.relative_to(ROOT)}")


# Load known datasets
for dataset_name in FILE_ALIASES:

    path = find_dataset_file(dataset_name)

    if path is None:
        if dataset_name in CORE_DATASETS:
            error(f"Required dataset not found: {dataset_name}")
        else:
            warning(f"Optional dataset not found: {dataset_name}")

        datasets[dataset_name] = []
        continue

    data = load_json_file(path)

    if data is None:
        datasets[dataset_name] = []
        continue

    records = records_from_json(data, dataset_name)

    datasets[dataset_name] = records
    dataset_paths[dataset_name] = path

    passed(
        f"{dataset_name}: loaded {len(records)} records "
        f"from {path.relative_to(ROOT)}"
    )


# ============================================================
# UNIQUE IDS
# ============================================================

print("\n2. Checking duplicate IDs\n")

ids = {}

id_fields = {
    "customers": ["user_id", "customer_id", "id"],
    "accounts": ["account_id", "id"],
    "lines": ["line_id", "id"],
    "plans": ["plan_id", "id"],
    "subscriptions": ["subscription_id", "id"],
    "devices": ["device_id", "id"],
    "invoices": ["invoice_id", "id"],
    "invoice_items": [
        "invoice_item_id",
        "item_id",
        "id",
    ],
    "payments": ["payment_id", "id"],
    "usage": [
        "usage_id",
        "usage_record_id",
        "id",
    ],
    "outages": ["outage_id", "incident_id", "id"],
    "tickets": ["ticket_id", "id"],
    "connection_requests": [
        "request_id",
        "connection_request_id",
        "id",
    ],
}


for dataset_name, records in datasets.items():

    if not records:
        continue

    fields = id_fields.get(dataset_name)

    if fields:
        ids[dataset_name] = collect_ids(
            records,
            fields,
            dataset_name,
        )


# ============================================================
# REFERENTIAL INTEGRITY
# ============================================================

print("\n3. Checking relationships / foreign keys\n")


# ------------------------------------------------------------
# Accounts -> Customers
# ------------------------------------------------------------

if datasets["customers"] and datasets["accounts"]:

    check_reference(
        datasets["accounts"],
        ["user_id", "customer_id"],
        ids["customers"],
        "Account -> Customer",
    )


# ------------------------------------------------------------
# Lines -> Accounts
# ------------------------------------------------------------

if datasets["lines"] and datasets["accounts"]:

    check_reference(
        datasets["lines"],
        ["account_id"],
        ids["accounts"],
        "Line -> Account",
    )


# Optional Line -> Customer check
if datasets["lines"] and datasets["customers"]:

    lines_with_user_id = [
        r
        for r in datasets["lines"]
        if first_value(r, ["user_id", "customer_id"]) is not None
    ]

    if lines_with_user_id:
        check_reference(
            lines_with_user_id,
            ["user_id", "customer_id"],
            ids["customers"],
            "Line -> Customer",
        )


# ------------------------------------------------------------
# Invoice -> Account
# ------------------------------------------------------------

if datasets["invoices"] and datasets["accounts"]:

    check_reference(
        datasets["invoices"],
        ["account_id"],
        ids["accounts"],
        "Invoice -> Account",
    )


# ------------------------------------------------------------
# Invoice Item -> Invoice
# ------------------------------------------------------------

if datasets["invoice_items"] and datasets["invoices"]:

    check_reference(
        datasets["invoice_items"],
        ["invoice_id"],
        ids["invoices"],
        "Invoice Item -> Invoice",
    )


# ------------------------------------------------------------
# Usage -> Line
# ------------------------------------------------------------

if datasets["usage"] and datasets["lines"]:

    check_reference(
        datasets["usage"],
        ["line_id"],
        ids["lines"],
        "Usage Record -> Line",
    )


# ------------------------------------------------------------
# Support Ticket -> Account
# ------------------------------------------------------------

if datasets["tickets"] and datasets["accounts"]:

    check_reference(
        datasets["tickets"],
        ["account_id"],
        ids["accounts"],
        "Support Ticket -> Account",
    )


# ============================================================
# OPTIONAL RELATIONSHIPS
# ============================================================

print("\n4. Checking optional relationships\n")


# Device -> Line
if datasets["devices"] and datasets["lines"]:

    check_reference(
        datasets["devices"],
        ["line_id"],
        ids["lines"],
        "Device -> Line",
    )


# Payment -> Invoice
if datasets["payments"] and datasets["invoices"]:

    check_reference(
        datasets["payments"],
        ["invoice_id"],
        ids["invoices"],
        "Payment -> Invoice",
    )


# Subscription -> Line
if datasets["subscriptions"] and datasets["lines"]:

    check_reference(
        datasets["subscriptions"],
        ["line_id"],
        ids["lines"],
        "Subscription -> Line",
    )


# Subscription -> Plan
if datasets["subscriptions"] and datasets["plans"]:

    check_reference(
        datasets["subscriptions"],
        ["plan_id"],
        ids["plans"],
        "Subscription -> Plan",
    )


# ============================================================
# INVOICE RECONCILIATION
# ============================================================

print("\n5. Checking invoice totals\n")

invoices = datasets["invoices"]
invoice_items = datasets["invoice_items"]

if invoices and invoice_items:

    items_by_invoice = defaultdict(list)

    for item in invoice_items:

        invoice_id = first_value(
            item,
            ["invoice_id"],
        )

        if invoice_id:
            items_by_invoice[str(invoice_id)].append(item)

    checked = 0

    for invoice in invoices:

        invoice_id = first_value(
            invoice,
            ["invoice_id", "id"],
        )

        if invoice_id is None:
            continue

        invoice_id = str(invoice_id)

        invoice_total = amount_to_cents(
            invoice,
            cent_fields=[
                "total_cents",
                "amount_due_cents",
                "invoice_total_cents",
            ],
            dollar_fields=[
                "total",
                "amount_due",
                "invoice_total",
            ],
        )

        if invoice_total is None:
            error(
                f"{invoice_id}: could not determine invoice total"
            )
            continue

        related_items = items_by_invoice.get(invoice_id, [])

        if not related_items:
            error(
                f"{invoice_id}: invoice has no invoice items"
            )
            continue

        calculated_total = 0
        item_error = False

        for item in related_items:

            value = amount_to_cents(
                item,
                cent_fields=[
                    "amount_cents",
                    "charge_cents",
                    "total_cents",
                ],
                dollar_fields=[
                    "amount",
                    "charge",
                    "total",
                ],
            )

            if value is None:
                item_error = True
                error(
                    f"{invoice_id}: invoice item has "
                    f"no readable amount: {item}"
                )
                continue

            calculated_total += value

        if item_error:
            continue

        checked += 1

        if calculated_total != invoice_total:

            error(
                f"{invoice_id}: total mismatch. "
                f"Stored={invoice_total} cents, "
                f"Calculated={calculated_total} cents"
            )

        else:

            passed(
                f"{invoice_id}: total reconciles "
                f"({invoice_total} cents)"
            )

    if checked:
        passed(f"Checked totals for {checked} invoices")


# ============================================================
# BASIC VALUE CHECKS
# ============================================================

print("\n6. Checking basic business constraints\n")


# Usage cannot be negative
for record in datasets["usage"]:

    for field in [
        "data_mb",
        "hotspot_mb",
        "voice_minutes",
        "sms_count",
    ]:

        if field in record and record[field] is not None:

            try:
                if float(record[field]) < 0:
                    error(
                        f"Negative usage found: "
                        f"{field}={record[field]}"
                    )

            except (ValueError, TypeError):
                error(
                    f"Invalid numeric usage value: "
                    f"{field}={record[field]}"
                )


# Invoice totals cannot normally be negative
for record in datasets["invoices"]:

    value = amount_to_cents(
        record,
        cent_fields=["total_cents"],
        dollar_fields=["total"],
    )

    if value is not None and value < 0:
        error(
            f"Negative invoice total found: "
            f"{first_value(record, ['invoice_id', 'id'])}"
        )


# ============================================================
# KNOWLEDGE BASE METADATA
# ============================================================

print("\n7. Checking RAG knowledge metadata\n")


REQUIRED_KNOWLEDGE_FIELDS = {
    "document_id",
    "version",
    "category",
    "effective_from",
}

RECOMMENDED_KNOWLEDGE_FIELDS = {
    "locale",
    "product",
}


def parse_markdown_frontmatter(path):

    text = path.read_text(
        encoding="utf-8",
    )

    if not text.startswith("---"):
        return None, "Missing YAML frontmatter opening '---'"

    parts = text.split("---", 2)

    if len(parts) < 3:
        return None, "Missing YAML frontmatter closing '---'"

    yaml_text = parts[1]

    try:
        metadata = yaml.safe_load(yaml_text)

    except yaml.YAMLError as exc:
        return None, f"Invalid YAML: {exc}"

    if not isinstance(metadata, dict):
        return None, "Frontmatter must be a YAML object"

    body = parts[2].strip()

    if not body:
        return None, "Knowledge document body is empty"

    return metadata, None


knowledge_files = list(
    KNOWLEDGE_DIR.rglob("*.md")
)

knowledge_ids = []
knowledge_doc_ids = set()


if not knowledge_files:

    error("No Markdown knowledge documents found")

else:

    for path in knowledge_files:

        metadata, metadata_error = (
            parse_markdown_frontmatter(path)
        )

        relative = path.relative_to(ROOT)

        if metadata_error:

            error(
                f"{relative}: {metadata_error}"
            )
            continue

        missing = (
            REQUIRED_KNOWLEDGE_FIELDS
            - set(metadata.keys())
        )

        if missing:

            error(
                f"{relative}: missing required metadata: "
                + ", ".join(sorted(missing))
            )
            continue

        recommended_missing = (
            RECOMMENDED_KNOWLEDGE_FIELDS
            - set(metadata.keys())
        )

        if recommended_missing:

            warning(
                f"{relative}: recommended metadata missing: "
                + ", ".join(sorted(recommended_missing))
            )

        document_id = str(metadata["document_id"])
        version = str(metadata["version"])

        knowledge_doc_ids.add(document_id)

        knowledge_ids.append(
            (document_id, version)
        )

        passed(
            f"{relative}: valid metadata "
            f"({document_id} v{version})"
        )


# Duplicate document_id + version
duplicates = [
    item
    for item, count in Counter(knowledge_ids).items()
    if count > 1
]

if duplicates:

    for document_id, version in duplicates:

        error(
            f"Duplicate RAG document version: "
            f"{document_id} v{version}"
        )

else:

    passed(
        "No duplicate RAG document_id/version combinations"
    )


# ============================================================
# EVALUATION JSON SYNTAX
# ============================================================

print("\n8. Checking evaluation data\n")

evaluation_files = list(
    EVALUATION_DIR.rglob("*.json")
)

if not evaluation_files:

    warning("No evaluation JSON files found")

else:

    for path in evaluation_files:

        data = load_json_file(path)

        if data is not None:

            passed(
                f"Valid evaluation JSON: "
                f"{path.relative_to(ROOT)}"
            )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)

print(f"PASS checks : {len(passes)}")
print(f"Warnings    : {len(warnings)}")
print(f"Errors      : {len(errors)}")


if warnings:

    print("\nWARNINGS")

    for item in warnings:
        print(f"  - {item}")


if errors:

    print("\nERRORS")

    for item in errors:
        print(f"  - {item}")

    print("\nOVERALL RESULT: FAIL")
    sys.exit(1)


print("\nOVERALL RESULT: PASS")
sys.exit(0)