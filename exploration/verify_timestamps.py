import json
from datetime import datetime, timezone

FILE_PATH = "data/extracted/Appliances.jsonl"

print("Timestamp Unit Verification")
print("=" * 60)

with open(FILE_PATH, "r", encoding="utf-8") as file:

    for i, line in enumerate(file):

        if i == 5:
            break

        review = json.loads(line)
        timestamp = review.get("timestamp")

        print(f"\nRecord {i + 1}")
        print("Raw timestamp:", timestamp)

        # Interpretation 1: seconds
        try:
            date_seconds = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc
            )
            print("As seconds:     ", date_seconds)
        except (ValueError, OSError, OverflowError):
            print("As seconds:      Invalid or out of range")

        # Interpretation 2: milliseconds
        try:
            date_milliseconds = datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc
            )
            print("As milliseconds:", date_milliseconds)
        except (ValueError, OSError, OverflowError):
            print("As milliseconds: Invalid or out of range")