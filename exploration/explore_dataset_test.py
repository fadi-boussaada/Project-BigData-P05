import os
import json
import csv
import re
from collections import Counter
from datetime import datetime, timezone
from matplotlib.ticker import StrMethodFormatter

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates



# ==========================================================
# 1. CONFIGURATION
# ==========================================================

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_FILE = os.path.join(
    PROJECT_DIR,
    "data",
    "extracted",
    "Appliances.jsonl"
)

RESULTS_DIR = os.path.join(
    PROJECT_DIR, "exploration", "results"
)

CHARTS_DIR = os.path.join(
    PROJECT_DIR, "exploration", "charts"
)

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")


# ==========================================================
# 2. INITIALIZE STATISTICS
# ==========================================================

total_lines = 0
empty_lines = 0
invalid_json = 0
non_object_json = 0
valid_records = 0

field_presence = Counter()
field_nulls = Counter()
field_types = {}

unique_parent_asin = set()
unique_asin = set()

product_review_counts = Counter()

rating_counts = Counter()
rating_sum = 0.0
valid_rating_count = 0
invalid_rating_count = 0

missing_parent_asin = 0
empty_text = 0
missing_timestamp = 0
invalid_timestamp = 0

year_counts = Counter()
month_counts = Counter()

earliest_date = None
latest_date = None

text_lengths = Counter()
word_counts = Counter()

text_count = 0
total_text_characters = 0
total_words = 0

short_reviews = 0

# ----------------------------------------------------------
# VERIFIED PURCHASE ANALYSIS
# ----------------------------------------------------------

verified_true = 0
verified_false = 0
verified_missing_field = 0
verified_null = 0
verified_unexpected = 0


# ----------------------------------------------------------
# HELPFUL VOTE ANALYSIS
# ----------------------------------------------------------

helpful_vote_counts = Counter()

helpful_vote_missing_field = 0
helpful_vote_null = 0
helpful_vote_negative = 0
helpful_vote_invalid_type = 0

helpful_vote_sum = 0
helpful_vote_count = 0


# ----------------------------------------------------------
# TITLE ANALYSIS
# ----------------------------------------------------------

title_missing_field = 0
title_null = 0
title_empty = 0
title_invalid_type = 0

title_count = 0
total_title_characters = 0
total_title_words = 0

title_lengths = Counter()
title_word_counts = Counter()

title_examples = []
MAX_TITLE_EXAMPLES = 10

# Regex for simple whitespace-based word counting
word_pattern = re.compile(r"\S+")


# ==========================================================
# 3. HELPER FUNCTIONS
# ==========================================================

def get_data_type(value):

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


def is_numeric(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def weighted_median(counter):

    if not counter:
        return None

    total = sum(counter.values())

    lower_position = (total - 1) // 2
    upper_position = total // 2

    cumulative = 0
    lower_value = None
    upper_value = None

    for value in sorted(counter):

        cumulative += counter[value]

        if lower_value is None and cumulative > lower_position:
            lower_value = value

        if cumulative > upper_position:
            upper_value = value
            break

    return (lower_value + upper_value) / 2


def save_csv(filename, headers, rows):

    path = os.path.join(RESULTS_DIR, filename)

    with open(path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(headers)
        writer.writerows(rows)

    print("Saved:", path)


# ==========================================================
# 4. READ THE COMPLETE DATASET
# ==========================================================

file_size_bytes = os.path.getsize(DATA_FILE)

print("=" * 60)
print("STARTING DATASET EXPLORATION")
print("=" * 60)

print(f"Dataset: {DATA_FILE}")
print(f"File size: {file_size_bytes / (1024**3):.3f} GB")

with open(DATA_FILE, "r", encoding="utf-8") as file:

    for line in file:

        total_lines += 1

        if not line.strip():
            empty_lines += 1
            continue

        try:
            record = json.loads(line)

        except json.JSONDecodeError:
            invalid_json += 1
            continue

        if not isinstance(record, dict):
            non_object_json += 1
            continue

        valid_records += 1

        # --------------------------------------------------
        # A. SCHEMA EXPLORATION
        # --------------------------------------------------

        for field, value in record.items():

            field_presence[field] += 1

            field_types.setdefault(field, Counter())

            field_types[field][get_data_type(value)] += 1

            if value is None:
                field_nulls[field] += 1

        # --------------------------------------------------
        # B. PRODUCT ANALYSIS
        # --------------------------------------------------

        parent_asin = record.get("parent_asin")
        asin = record.get("asin")

        if (
            isinstance(parent_asin, str)
            and parent_asin.strip()
        ):

            unique_parent_asin.add(parent_asin)
            product_review_counts[parent_asin] += 1

        else:
            missing_parent_asin += 1

        if isinstance(asin, str) and asin.strip():
            unique_asin.add(asin)

        # --------------------------------------------------
        # C. RATING ANALYSIS
        # --------------------------------------------------

        rating = record.get("rating")

        if is_numeric(rating) and 1 <= rating <= 5:

            rating = float(rating)

            rating_counts[rating] += 1

            rating_sum += rating
            valid_rating_count += 1

        else:
            invalid_rating_count += 1

        # --------------------------------------------------
        # D. TIMESTAMP ANALYSIS
        # --------------------------------------------------

        timestamp = record.get("timestamp")

        if timestamp is None:
            missing_timestamp += 1

        elif is_numeric(timestamp):

            try:

                review_date = datetime.fromtimestamp(
                    timestamp / 1000,
                    tz=timezone.utc
                )

                # Reject unrealistic dates from temporal statistics only
                if not (
                    datetime(2000, 1, 1, tzinfo=timezone.utc)
                    <= review_date
                    <= datetime(2024, 1, 1, tzinfo=timezone.utc)
                ):
                    invalid_timestamp += 1
                else:

                    if earliest_date is None or review_date < earliest_date:
                        earliest_date = review_date

                    if latest_date is None or review_date > latest_date:
                        latest_date = review_date

                    year_counts[review_date.year] += 1

                    month = review_date.strftime("%Y-%m")

                    month_counts[month] += 1

            except (ValueError, OverflowError, OSError):
                invalid_timestamp += 1

        else:
            invalid_timestamp += 1

        # --------------------------------------------------
        # E. TEXT ANALYSIS
        # --------------------------------------------------

        text = record.get("text")

        if not isinstance(text, str) or not text.strip():

            empty_text += 1

        else:

            text_count += 1

            character_length = len(text)

            number_of_words = len(
                word_pattern.findall(text)
            )

            text_lengths[character_length] += 1
            word_counts[number_of_words] += 1

            total_text_characters += character_length
            total_words += number_of_words

            if number_of_words <= 5:
                short_reviews += 1

        # --------------------------------------------------
        # F. VERIFIED PURCHASE ANALYSIS
        # --------------------------------------------------

        if "verified_purchase" not in record:

            verified_missing_field += 1

        else:

            verified = record["verified_purchase"]

            if verified is None:

                verified_null += 1

            elif verified is True:

                verified_true += 1

            elif verified is False:

                verified_false += 1

            else:

                verified_unexpected += 1


        # --------------------------------------------------
        # G. HELPFUL VOTE ANALYSIS
        # --------------------------------------------------

        if "helpful_vote" not in record:

            helpful_vote_missing_field += 1

        else:

            helpful_vote = record["helpful_vote"]

            if helpful_vote is None:

                helpful_vote_null += 1

            elif (
                isinstance(helpful_vote, int)
                and not isinstance(helpful_vote, bool)
            ):

                if helpful_vote < 0:

                    helpful_vote_negative += 1

                else:

                    helpful_vote_counts[helpful_vote] += 1
                    helpful_vote_sum += helpful_vote
                    helpful_vote_count += 1

            else:

                helpful_vote_invalid_type += 1


        # --------------------------------------------------
        # H. TITLE ANALYSIS
        # --------------------------------------------------

        if "title" not in record:

            title_missing_field += 1

        else:

            title = record["title"]

            if title is None:

                title_null += 1

            elif not isinstance(title, str):

                title_invalid_type += 1

            elif not title.strip():

                title_empty += 1

            else:

                title_count += 1

                character_length = len(title)

                number_of_words = len(
                    word_pattern.findall(title)
                )

                title_lengths[character_length] += 1
                title_word_counts[number_of_words] += 1

                total_title_characters += character_length
                total_title_words += number_of_words

                if len(title_examples) < MAX_TITLE_EXAMPLES:

                    title_examples.append(title)

        # --------------------------------------------------
        # I. PROGRESS
        # --------------------------------------------------

        if total_lines % 100000 == 0:

            print(
                f"Processed {total_lines:,} lines..."
            )


# ==========================================================
# 5. CALCULATE FINAL STATISTICS
# ==========================================================

print("\nDataset reading completed.")

print("\nFIELD ANALYSIS CONSISTENCY CHECK")

print(
    "Verified purchase total:",
    verified_true + verified_false
    + verified_missing_field
    + verified_null
    + verified_unexpected
)

print(
    "Helpful vote total:",
    helpful_vote_count
    + helpful_vote_missing_field
    + helpful_vote_null
    + helpful_vote_negative
    + helpful_vote_invalid_type
)

print(
    "Title total:",
    title_count
    + title_missing_field
    + title_null
    + title_empty
    + title_invalid_type
)

print("Valid JSON objects:", valid_records)

assert (
    verified_true + verified_false
    + verified_missing_field + verified_null
    + verified_unexpected
) == valid_records

assert (
    helpful_vote_count + helpful_vote_missing_field
    + helpful_vote_null + helpful_vote_negative
    + helpful_vote_invalid_type
) == valid_records

assert (
    title_count + title_missing_field
    + title_null + title_empty + title_invalid_type
) == valid_records

print("All field consistency checks passed.")

rating_average = (
    rating_sum / valid_rating_count
    if valid_rating_count else None
)

rating_median = weighted_median(rating_counts)

average_text_length = (
    total_text_characters / text_count
    if text_count else None
)

median_text_length = weighted_median(text_lengths)

average_word_count = (
    total_words / text_count
    if text_count else None
)

median_word_count = weighted_median(word_counts)

minimum_text_length = (
    min(text_lengths) if text_lengths else None
)

maximum_text_length = (
    max(text_lengths) if text_lengths else None
)

minimum_word_count = (
    min(word_counts) if word_counts else None
)

maximum_word_count = (
    max(word_counts) if word_counts else None
)

# ----------------------------------------------------------
# HELPFUL VOTE STATISTICS
# ----------------------------------------------------------

helpful_vote_average = (
    helpful_vote_sum / helpful_vote_count
    if helpful_vote_count else None
)

helpful_vote_median = weighted_median(helpful_vote_counts)

helpful_vote_minimum = (
    min(helpful_vote_counts)
    if helpful_vote_counts else None
)

helpful_vote_maximum = (
    max(helpful_vote_counts)
    if helpful_vote_counts else None
)


# ----------------------------------------------------------
# TITLE STATISTICS
# ----------------------------------------------------------

average_title_length = (
    total_title_characters / title_count
    if title_count else None
)

median_title_length = weighted_median(title_lengths)

average_title_words = (
    total_title_words / title_count
    if title_count else None
)

median_title_words = weighted_median(title_word_counts)

minimum_title_length = (
    min(title_lengths) if title_lengths else None
)

maximum_title_length = (
    max(title_lengths) if title_lengths else None

)

minimum_title_words = (
    min(title_word_counts) if title_word_counts else None
)

maximum_title_words = (
    max(title_word_counts) if title_word_counts else None
)

# ==========================================================
# 6. MISSING VALUES AND SCHEMA
# ==========================================================

schema_rows = []

all_fields = sorted(field_presence.keys())

for field in all_fields:

    present = field_presence[field]

    missing = valid_records - present

    null_count = field_nulls[field]

    non_null_missing = missing + null_count

    percentage_missing = (
        non_null_missing / valid_records * 100
        if valid_records else 0
    )

    types = ", ".join(
        f"{name}: {count}"
        for name, count in field_types[field].items()
    )

    schema_rows.append([
        field,
        types,
        present,
        missing,
        null_count,
        round(percentage_missing, 3)
    ])

save_csv(
    "schema_analysis.csv",
    [
        "field",
        "observed_types_and_counts",
        "present_count",
        "missing_field_count",
        "null_count",
        "missing_or_null_percentage"
    ],
    schema_rows
)


# ==========================================================
# 7. RATING RESULTS
# ==========================================================

rating_rows = []

for rating in sorted(rating_counts):

    count = rating_counts[rating]

    percentage = (
        count / valid_rating_count * 100
        if valid_rating_count else 0
    )

    rating_rows.append([
        rating,
        count,
        round(percentage, 3)
    ])

save_csv(
    "rating_distribution.csv",
    ["rating", "count", "percentage"],
    rating_rows
)


# ==========================================================
# 8. TEMPORAL RESULTS
# ==========================================================

save_csv(
    "yearly_reviews.csv",
    ["year", "review_count"],
    [
        [year, year_counts[year]]
        for year in sorted(year_counts)
    ]
)

save_csv(
    "monthly_reviews.csv",
    ["month", "review_count"],
    [
        [month, month_counts[month]]
        for month in sorted(month_counts)
    ]
)


# ==========================================================
# 9. PRODUCT RESULTS
# ==========================================================

top_products = product_review_counts.most_common(20)

save_csv(
    "top_20_products.csv",
    ["parent_asin", "review_count"],
    top_products
)

product_review_distribution = Counter(
    product_review_counts.values()
)

save_csv(
    "reviews_per_product_distribution.csv",
    ["reviews_per_product", "number_of_products"],
    [
        [number_of_reviews, number_of_products]
        for number_of_reviews, number_of_products
        in sorted(product_review_distribution.items())
    ]
)


# ==========================================================
# 10. TEXT RESULTS
# ==========================================================

text_rows = [
    ["text_count", text_count],
    ["empty_text_count", empty_text],
    ["short_reviews_at_most_5_words", short_reviews],
    ["total_characters", total_text_characters],
    ["total_words", total_words],
    ["average_characters", average_text_length],
    ["median_characters", median_text_length],
    ["minimum_characters", minimum_text_length],
    ["maximum_characters", maximum_text_length],
    ["average_words", average_word_count],
    ["median_words", median_word_count],
    ["minimum_words", minimum_word_count],
    ["maximum_words", maximum_word_count]
]

save_csv(
    "text_statistics.csv",
    ["metric", "value"],
    text_rows
)

# ==========================================================
# 10.1 VERIFIED PURCHASE RESULTS
# ==========================================================

verified_rows = [
    ["True", verified_true],
    ["False", verified_false],
    ["Missing field", verified_missing_field],
    ["Null", verified_null],
    ["Unexpected values", verified_unexpected]
]

save_csv(
    "verified_purchase_distribution.csv",
    ["value", "count"],
    verified_rows
)


# ==========================================================
# 10.2 HELPFUL VOTE RESULTS
# ==========================================================

helpful_vote_rows = [
    ["valid_count", helpful_vote_count],
    ["missing_field", helpful_vote_missing_field],
    ["null", helpful_vote_null],
    ["negative_values", helpful_vote_negative],
    ["invalid_type", helpful_vote_invalid_type],
    ["minimum", helpful_vote_minimum],
    ["maximum", helpful_vote_maximum],
    ["average", helpful_vote_average],
    ["median", helpful_vote_median],
    ["zero_votes", helpful_vote_counts.get(0, 0)]
]

save_csv(
    "helpful_vote_statistics.csv",
    ["metric", "value"],
    helpful_vote_rows
)

save_csv(
    "helpful_vote_distribution.csv",
    ["helpful_vote", "review_count"],
    [
        [votes, count]
        for votes, count in sorted(helpful_vote_counts.items())
    ]
)


# ==========================================================
# 10.3 TITLE RESULTS
# ==========================================================

title_rows = [
    ["valid_title_count", title_count],
    ["missing_field", title_missing_field],
    ["null", title_null],
    ["empty_or_whitespace", title_empty],
    ["invalid_type", title_invalid_type],
    ["average_characters", average_title_length],
    ["median_characters", median_title_length],
    ["minimum_characters", minimum_title_length],
    ["maximum_characters", maximum_title_length],
    ["average_words", average_title_words],
    ["median_words", median_title_words],
    ["minimum_words", minimum_title_words],
    ["maximum_words", maximum_title_words]
]

save_csv(
    "title_statistics.csv",
    ["metric", "value"],
    title_rows
)

save_csv(
    "title_examples.csv",
    ["title"],
    [[title] for title in title_examples]
)

# ==========================================================
# 11. GENERATE CHARTS
# ==========================================================

# Chart 1: Rating distribution

if rating_counts:

    ratings = sorted(rating_counts.keys())

    counts = [rating_counts[r] for r in ratings]

    plt.figure(figsize=(9, 5))

    plt.bar(
        [str(r) for r in ratings],
        counts
    )

    plt.title("Distribution of Customer Ratings")
    plt.xlabel("Rating")
    plt.ylabel("Number of Reviews")

    plt.tight_layout()

    plt.savefig(
        os.path.join(CHARTS_DIR, "rating_distribution.png"),
        dpi=150
    )

    plt.close()



# Chart 2: Monthly review volume

if month_counts:

    months = sorted(month_counts)

    monthly_dates = [
        datetime.strptime(month, "%Y-%m")
        for month in months
    ]

    monthly_values = [
        month_counts[month] for month in months
    ]

    fig, ax = plt.subplots(figsize=(15, 6))

    ax.plot(
        monthly_dates,
        monthly_values,
        linewidth=1.5
    )

    ax.set_title(
        "Monthly Review Volume (2000–2023)",
        fontsize=15,
        fontweight="bold",
        pad=15
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Reviews")

    ax.xaxis.set_major_locator(
        mdates.YearLocator()
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%Y")
    )

    ax.yaxis.set_major_formatter(
        StrMethodFormatter("{x:,.0f}")
    )

    ax.set_ylim(bottom=0)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    ax.margins(x=0.01)

    plt.tight_layout()

    plt.savefig(
        os.path.join(CHARTS_DIR, "monthly_review_volume.png"),
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()



# Chart 3: Review length distribution

if text_lengths:

    lengths = np.array(list(text_lengths.keys()))
    frequencies = np.array(list(text_lengths.values()))

    plt.figure(figsize=(10, 5))

    plt.hist(
        lengths,
        bins=40,
        weights=frequencies
    )

    plt.title("Distribution of Review Text Length")
    plt.xlabel("Characters per Review")
    plt.ylabel("Number of Reviews")

    plt.tight_layout()

    plt.savefig(
        os.path.join(CHARTS_DIR, "review_length_distribution.png"),
        dpi=150
    )

    plt.close()


# Chart 4: Top 20 products

if top_products:

    product_ids = [
        product[0] for product in top_products
    ]

    product_counts = [
        product[1] for product in top_products
    ]

    plt.figure(figsize=(11, 7))

    plt.barh(
        product_ids[::-1],
        product_counts[::-1]
    )

    plt.title("Top 20 Most Reviewed Products")
    plt.xlabel("Number of Reviews")
    plt.ylabel("Parent ASIN")

    plt.tight_layout()

    plt.savefig(
        os.path.join(CHARTS_DIR, "reviews_per_product.png"),
        dpi=150
    )

    plt.close()


# ==========================================================
# 12. SAVE COMPLETE SUMMARY
# ==========================================================

summary = {

    "dataset": {
        "name": "Amazon Reviews 2023 - Appliances",
        "format": "JSON Lines",
        "encoding": "UTF-8",
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_bytes / (1024**2), 3),
        "file_size_gb": round(file_size_bytes / (1024**3), 3)
    },

    "records": {
        "total_lines": total_lines,
        "empty_lines": empty_lines,
        "invalid_json": invalid_json,
        "non_object_json": non_object_json,
        "valid_json_objects": valid_records
    },

    "products": {
        "unique_parent_asin": len(unique_parent_asin),
        "unique_asin": len(unique_asin),
        "top_20": top_products
    },

    "ratings": {
        "valid_count": valid_rating_count,
        "invalid_count": invalid_rating_count,
        "distribution": {
            str(k): v for k, v in sorted(rating_counts.items())
        },
        "average": rating_average,
        "median": rating_median
    },

    "dates": {
        "missing_timestamp": missing_timestamp,
        "invalid_timestamp": invalid_timestamp,
        "earliest": (
            earliest_date.isoformat()
            if earliest_date else None
        ),
        "latest": (
            latest_date.isoformat()
            if latest_date else None
        ),
        "yearly_counts": {
            str(k): v for k, v in sorted(year_counts.items())
        }
    },

    "text": {
        "empty_text": empty_text,
        "valid_text_count": text_count,
        "short_reviews_at_most_5_words": short_reviews,
        "average_characters": average_text_length,
        "median_characters": median_text_length,
        "minimum_characters": minimum_text_length,
        "maximum_characters": maximum_text_length,
        "average_words": average_word_count,
        "median_words": median_word_count,
        "minimum_words": minimum_word_count,
        "maximum_words": maximum_word_count
    },

    "verified_purchase": {
        "true": verified_true,
        "false": verified_false,
        "missing_field": verified_missing_field,
        "null": verified_null,
        "unexpected": verified_unexpected
    },

    "helpful_vote": {
        "valid_count": helpful_vote_count,
        "missing_field": helpful_vote_missing_field,
        "null": helpful_vote_null,
        "negative_values": helpful_vote_negative,
        "invalid_type": helpful_vote_invalid_type,
        "zero_votes": helpful_vote_counts.get(0, 0),
        "minimum": helpful_vote_minimum,
        "maximum": helpful_vote_maximum,
        "average": helpful_vote_average,
        "median": helpful_vote_median
    },

    "title": {
        "valid_count": title_count,
        "missing_field": title_missing_field,
        "null": title_null,
        "empty": title_empty,
        "invalid_type": title_invalid_type,
        "average_characters": average_title_length,
        "median_characters": median_title_length,
        "minimum_characters": minimum_title_length,
        "maximum_characters": maximum_title_length,
        "average_words": average_title_words,
        "median_words": median_title_words,
        "minimum_words": minimum_title_words,
        "maximum_words": maximum_title_words,
        "examples": title_examples
    },

    "data_quality": {
        "missing_parent_asin": missing_parent_asin,
        "invalid_rating": invalid_rating_count,
        "missing_timestamp": missing_timestamp,
        "invalid_timestamp": invalid_timestamp,
        "empty_text": empty_text,
        "duplicate_check": "Not performed; reserved for the preparation stage."
    },

    "analysis_notes": [
        "The original dataset was not modified.",
        "Statistics were calculated using streaming JSONL reading.",
        "Timestamp values were interpreted as Unix milliseconds.",
        "Timestamp values outside 2000-01-01 to 2024-01-01 (UTC) were excluded from temporal statistics only.",
        "No data cleaning or record rejection was performed.",
        "Only syntactically valid JSON objects were included in field-level statistics."
    ]
}

summary_path = os.path.join(
    RESULTS_DIR,
    "dataset_summary.json"
)

with open(
    summary_path,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        summary,
        file,
        indent=4,
        ensure_ascii=False
    )


# ==========================================================
# 13. FINAL CONSOLE SUMMARY
# ==========================================================

print("\n" + "=" * 60)
print("EXPLORATION COMPLETED")
print("=" * 60)

print(f"Total lines: {total_lines:,}")
print(f"Valid JSON objects: {valid_records:,}")
print(f"Invalid JSON: {invalid_json:,}")
print(f"Empty lines: {empty_lines:,}")
print(f"Non-object JSON: {non_object_json:,}")

print(f"\nUnique products: {len(unique_parent_asin):,}")
print(f"Unique ASIN variants: {len(unique_asin):,}")

print("\nRATING ANALYSIS")
print("Average:", rating_average)
print("Median:", rating_median)
print("Invalid ratings:", invalid_rating_count)

print("\nDATE ANALYSIS")
print("Earliest:", earliest_date)
print("Latest:", latest_date)

print("\nTEXT ANALYSIS")
print("Empty texts:", empty_text)
print("Average characters:", average_text_length)
print("Median characters:", median_text_length)
print("Average words:", average_word_count)
print("Median words:", median_word_count)

print("\nDATA QUALITY")
print("Missing parent_asin:", missing_parent_asin)
print("Missing timestamp:", missing_timestamp)
print("Invalid timestamp:", invalid_timestamp)

print("\nVERIFIED PURCHASE ANALYSIS")
print("True:", verified_true)
print("False:", verified_false)
print("Missing field:", verified_missing_field)
print("Null:", verified_null)
print("Unexpected:", verified_unexpected)

print("\nHELPFUL VOTE ANALYSIS")
print("Valid votes:", helpful_vote_count)
print("Zero votes:", helpful_vote_counts.get(0, 0))
print("Missing field:", helpful_vote_missing_field)
print("Null:", helpful_vote_null)
print("Negative:", helpful_vote_negative)
print("Invalid type:", helpful_vote_invalid_type)
print("Minimum:", helpful_vote_minimum)
print("Maximum:", helpful_vote_maximum)
print("Average:", helpful_vote_average)
print("Median:", helpful_vote_median)

print("\nTITLE ANALYSIS")
print("Valid titles:", title_count)
print("Missing field:", title_missing_field)
print("Null:", title_null)
print("Empty:", title_empty)
print("Invalid type:", title_invalid_type)
print("Average characters:", average_title_length)
print("Median characters:", median_title_length)
print("Average words:", average_title_words)
print("Median words:", median_title_words)
print("\nResults directory:", RESULTS_DIR)
print("Charts directory:", CHARTS_DIR)

print("\nAll exploration results have been saved.")