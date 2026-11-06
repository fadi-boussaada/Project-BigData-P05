
import gzip
import shutil
import os

source = "data/source/Appliances.jsonl.gz"
destination = "data/extracted/Appliances.jsonl"

os.makedirs("data/extracted", exist_ok=True)

print("Starting extraction...")

with gzip.open(source, "rb") as compressed:
    with open(destination, "wb") as extracted:
        shutil.copyfileobj(compressed, extracted, length=1024 * 1024)

print("Extraction completed!")
print("Output:", destination)
print("File size:", round(os.path.getsize(destination) / (1024**3), 2), "GB")
