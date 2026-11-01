import json
import re
import csv

with open("data/raw/cuad/CUAD_v1/CUAD_v1.json", encoding="utf-8") as f:
    data = json.load(f)

with open("data/processed/cuad_pilot_30.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

lookup = {item["title"]: item for item in data["data"]}
pattern = re.compile(r'(?<!\d)(\d{1,2})\.\s+(?=[A-Z]|")')

print("DOCUMENT | MARKERS | SEQUENTIAL | FIRST | LAST")
print("-" * 85)

for row in rows:
    item = lookup.get(row["title"])
    context = item["paragraphs"][0].get("context", "") if item and item["paragraphs"] else ""
    matches = list(pattern.finditer(context))
    numbers = [int(m.group(1)) for m in matches]
    sequential = numbers == list(range(1, len(numbers) + 1))

    print(
        f"{row['title'][:43]:43} | "
        f"{len(numbers):7} | "
        f"{str(sequential):10} | "
        f"{numbers[0] if numbers else '-':5} | "
        f"{numbers[-1] if numbers else '-'}"
    )
