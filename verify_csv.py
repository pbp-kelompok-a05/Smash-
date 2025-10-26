import csv

with open("padel_posts_dataset_refined.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

    print(f"✓ Total rows: {len(rows)}")
    print(f"✓ Columns: {list(rows[0].keys())}")
    print(f'✓ First title: {rows[0]["title"][:50]}...')
    print(f'✓ Has newlines in selftext: {chr(10) in rows[0]["selftext"]}')
    print(f'✓ First author: {rows[0]["author"]}')

    # Check for empty authors
    empty_authors = sum(1 for row in rows if not row["author"].strip())
    print(f"✓ Empty authors: {empty_authors}")
