
import gzip
import json

file_path = "data/source/Appliances.jsonl.gz"

with gzip.open(file_path, "rt", encoding="utf-8") as file:
    for i, line in enumerate(file):
        if i == 3:
            break

        review = json.loads(line)

        print(f"\n--- REVIEW {i + 1} ---")

        for key, value in review.items():
            if key != "user_id":
                print(f"{key}: {value}")
