
import os

file_path = "C:/P05-Amazon-Reviews/data/extracted/Appliances.jsonl"

total_lines = 0

with open(file_path, "r", encoding="utf-8") as file:
    for line in file:
        if line.strip():
            total_lines += 1

print("File exists:", os.path.exists(file_path))
print("File size (GB):", round(os.path.getsize(file_path) / (1024**3), 2))
print("Total records:", total_lines)
