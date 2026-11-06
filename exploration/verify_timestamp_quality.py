import json
import math
from datetime import datetime, timezone

FILE_PATH = "data/extracted/Appliances.jsonl"

total_records = 0
missing_timestamps = 0
invalid_timestamps = 0

min_timestamp = None
max_timestamp = None

min_date = None
max_date = None

invalid_examples = []

print("Full Dataset Timestamp Validation")
print("=" * 60)

with open(FILE_PATH, "r", encoding="utf-8") as file:

    for line_number, line in enumerate(file, start=1):

        if not line.strip():
            continue

        total_records += 1

        try:
            review = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(review, dict):
            continue

        # Check whether timestamp is missing or null
        if "timestamp" not in review or review["timestamp"] is None:
            missing_timestamps += 1
            continue

        timestamp = review["timestamp"]

        # Boolean values are not accepted as timestamps
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
        ):
            invalid_timestamps += 1

            if len(invalid_examples) < 10:
                invalid_examples.append((line_number, timestamp))

            continue

        # Convert milliseconds to seconds
        try:
            date = datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc
            )
        except (ValueError, OSError, OverflowError):
            invalid_timestamps += 1

            if len(invalid_examples) < 10:
                invalid_examples.append((line_number, timestamp))

            continue

        # Update minimum timestamp
        if min_timestamp is None or timestamp < min_timestamp:
            min_timestamp = timestamp
            min_date = date

        # Update maximum timestamp
        if max_timestamp is None or timestamp > max_timestamp:
            max_timestamp = timestamp
            max_date = date


print("\nRESULTS")
print("=" * 60)

print("Total records:", total_records)
print("Missing timestamps:", missing_timestamps)
print("Invalid timestamps:", invalid_timestamps)

print("\nMINIMUM TIMESTAMP")
print("Raw value:", min_timestamp)
print("UTC date:", min_date)

print("\nMAXIMUM TIMESTAMP")
print("Raw value:", max_timestamp)
print("UTC date:", max_date)

if invalid_examples:
    print("\nFirst invalid examples:")
    for line_number, value in invalid_examples:
        print(f"Line {line_number}: {value}")

print("\nTimestamp validation completed.")