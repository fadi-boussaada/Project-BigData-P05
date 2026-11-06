import os
import json
import csv
import hashlib
from collections import Counter
from datetime import datetime, timezone
from math import isfinite

# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_DIR, "data", "extracted", "Appliances.jsonl")
RESULTS_DIR = os.path.join(PROJECT_DIR, "exploration", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

if not os.path.isfile(DATA_FILE):
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")


def save_csv(filename, headers, rows):
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print("Saved:", path)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


# ==========================================================
# COUNTERS
# ==========================================================

total_lines = empty_lines = invalid_json = non_object_json = 0
valid_records = 0

field_present = Counter()
field_null = Counter()
field_types = {}

unique_parent_asin = set()
unique_asin = set()
products_with_text = set()
reviews_per_product = Counter()

rating_counts = Counter()
valid_ratings = invalid_ratings = 0

timestamp_missing = timestamp_invalid = 0
earliest_date = latest_date = None

empty_text = usable_text = 0
verified_true = verified_false = verified_other = 0
helpful_zero = helpful_positive = helpful_invalid = 0
helpful_sum = helpful_max = 0

empty_title = 0
missing_ids = Counter()

# Exact duplicate lines only. Hashes are kept in memory for this check.
seen_hashes = set()
exact_duplicate_lines = 0

file_size_bytes = os.path.getsize(DATA_FILE)

# ==========================================================
# READ THE COMPLETE DATASET ONCE
# ==========================================================

print("Starting exploration of the complete dataset...")
print(f"File: {DATA_FILE}")
print(f"Size: {file_size_bytes / (1024 ** 3):.3f} GB")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    for line in f:
        total_lines += 1

        if not line.strip():
            empty_lines += 1
            continue

        line_hash = hashlib.sha256(line.encode("utf-8")).digest()
        if line_hash in seen_hashes:
            exact_duplicate_lines += 1
        else:
            seen_hashes.add(line_hash)

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            invalid_json += 1
            continue

        if not isinstance(record, dict):
            non_object_json += 1
            continue

        valid_records += 1

        # Schema
        for field, value in record.items():
            field_present[field] += 1
            field_types.setdefault(field, Counter())[value_type(value)] += 1
            if value is None:
                field_null[field] += 1

        # Product identifiers and review counts
        for field in ("asin", "parent_asin", "user_id"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                missing_ids[field] += 1

        parent = record.get("parent_asin")
        if isinstance(parent, str) and parent.strip():
            unique_parent_asin.add(parent)
            reviews_per_product[parent] += 1

        asin = record.get("asin")
        if isinstance(asin, str) and asin.strip():
            unique_asin.add(asin)

        # Rating (MR3)
        rating = record.get("rating")
        if is_number(rating) and isfinite(rating) and 1 <= rating <= 5:
            rating_counts[rating] += 1
            valid_ratings += 1
        else:
            invalid_ratings += 1

        # Timestamp (milliseconds since Unix epoch)
        timestamp = record.get("timestamp")
        if timestamp is None:
            timestamp_missing += 1
        elif is_number(timestamp) and isfinite(timestamp):
            try:
                review_date = datetime.fromtimestamp(
                    timestamp / 1000, tz=timezone.utc
                )
                earliest_date = min(earliest_date, review_date) if earliest_date else review_date
                latest_date = max(latest_date, review_date) if latest_date else review_date
            except (ValueError, OverflowError, OSError):
                timestamp_invalid += 1
        else:
            timestamp_invalid += 1

        # Review text (MR1 and MR2)
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            empty_text += 1
        else:
            usable_text += 1
            if isinstance(parent, str) and parent.strip():
                products_with_text.add(parent)

        # Title: only check whether it is empty
        title = record.get("title")
        if not isinstance(title, str) or not title.strip():
            empty_title += 1

        # Verified purchase
        verified = record.get("verified_purchase")
        if verified is True:
            verified_true += 1
        elif verified is False:
            verified_false += 1
        else:
            verified_other += 1

        # Helpful votes
        votes = record.get("helpful_vote")
        if isinstance(votes, int) and not isinstance(votes, bool) and votes >= 0:
            if votes == 0:
                helpful_zero += 1
            else:
                helpful_positive += 1
            helpful_sum += votes
            helpful_max = max(helpful_max, votes)
        else:
            helpful_invalid += 1

        if total_lines % 100000 == 0:
            print(f"Processed {total_lines:,} lines...")


# ==========================================================
# SAVE ONLY THE IMPORTANT RESULTS
# ==========================================================

schema_rows = []
for field in sorted(set(field_present) | set(field_null)):
    present = field_present[field]
    missing = valid_records - present
    nulls = field_null[field]
    types = ", ".join(
        f"{kind}: {count}" for kind, count in sorted(field_types[field].items())
    )
    schema_rows.append([field, types, present, missing, nulls])

save_csv(
    "schema_analysis.csv",
    ["field", "observed_types", "present_count", "missing_field_count", "null_count"],
    schema_rows,
)

save_csv(
    "rating_distribution.csv",
    ["rating", "review_count"],
    [[rating, rating_counts[rating]] for rating in sorted(rating_counts)],
)

product_distribution = Counter(reviews_per_product.values())
save_csv(
    "reviews_per_product_distribution.csv",
    ["reviews_per_product", "number_of_products"],
    [[count, product_distribution[count]] for count in sorted(product_distribution)],
)

summary = {
    "dataset": {
        "name": "Amazon Reviews 2023 - Appliances",
        "file_size_bytes": file_size_bytes,
        "file_size_gb": round(file_size_bytes / (1024 ** 3), 3),
    },
    "records": {
        "total_lines": total_lines,
        "empty_lines": empty_lines,
        "invalid_json": invalid_json,
        "non_object_json": non_object_json,
        "valid_json_objects": valid_records,
        "exact_duplicate_lines": exact_duplicate_lines,
    },
    "products": {
        "unique_parent_asin": len(unique_parent_asin),
        "unique_asin": len(unique_asin),
        "products_with_at_least_one_nonempty_text": len(products_with_text),
        "products_with_valid_parent_asin": len(reviews_per_product),
    },
    "identifiers": {
        "empty_or_missing_asin": missing_ids["asin"],
        "empty_or_missing_parent_asin": missing_ids["parent_asin"],
        "empty_or_missing_user_id": missing_ids["user_id"],
    },
    "ratings": {
        "valid_count": valid_ratings,
        "invalid_count": invalid_ratings,
        "distribution": {str(k): v for k, v in sorted(rating_counts.items())},
    },
    "timestamps_milliseconds": {
        "missing_or_null": timestamp_missing,
        "invalid_or_unconvertible": timestamp_invalid,
        "earliest_utc": earliest_date.isoformat() if earliest_date else None,
        "latest_utc": latest_date.isoformat() if latest_date else None,
    },
    "review_text": {
        "nonempty_text_count": usable_text,
        "empty_or_invalid_text_count": empty_text,
    },
    "titles": {
        "empty_or_missing_title": empty_title,
    },
    "verified_purchase": {
        "true": verified_true,
        "false": verified_false,
        "null_missing_or_unexpected": verified_other,
    },
    "helpful_votes": {
        "zero_vote_reviews": helpful_zero,
        "positive_vote_reviews": helpful_positive,
        "missing_null_or_invalid": helpful_invalid,
        "average_valid_votes": round(helpful_sum / (helpful_zero + helpful_positive), 3)
        if helpful_zero + helpful_positive else None,
        "maximum": helpful_max,
    },
    "notes": [
        "The complete extracted JSONL dataset was read in one streaming pass.",
        "Timestamp values were interpreted as Unix milliseconds and converted to UTC.",
        "No records were modified or removed.",
        "Exact duplicates mean identical raw JSONL lines; semantically equivalent records with different formatting are not detected.",
        "A nonempty review text is counted as usable here; project-specific cleaning and tokenization happen later.",
    ],
}

summary_path = os.path.join(RESULTS_DIR, "dataset_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=4, ensure_ascii=False)

print("\nEXPLORATION COMPLETED")
print(f"Valid JSON objects: {valid_records:,}")
print(f"Invalid JSON: {invalid_json:,}")
print(f"Exact duplicate lines: {exact_duplicate_lines:,}")
print(f"Products (parent_asin): {len(unique_parent_asin):,}")
print(f"Products with nonempty text: {len(products_with_text):,}")
print(f"Invalid ratings: {invalid_ratings:,}")
print(f"Missing timestamps: {timestamp_missing:,}")
print(f"Invalid timestamps: {timestamp_invalid:,}")
print(f"Empty review texts: {empty_text:,}")
print(f"Empty titles: {empty_title:,}")
print(f"Results saved in: {RESULTS_DIR}")
